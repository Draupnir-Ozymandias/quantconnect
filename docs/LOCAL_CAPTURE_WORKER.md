# Local capture worker

`protocol-capture-retry` is the network-capable entry point intended for a
local OS scheduler such as macOS `launchd`. It preserves the locked protocol's
schedule and deadline, retries only `AcquisitionError` transport failures, and
never retries contract, market-term, identity, or timing violations.

Preview without networking:

```bash
./synch.sh evidence protocol-capture-retry \
  execution_truth/protocols/<future-protocol>.json <capture-id>
```

Execute within the declared window:

```bash
./synch.sh evidence protocol-capture-retry \
  execution_truth/protocols/<future-protocol>.json <capture-id> \
  --max-attempts 4 --initial-backoff-seconds 5 \
  --max-backoff-seconds 30 --execute
```

Backoff is exponential and capped. The worker refuses a sleep that would cross
the capture's start deadline, writes capture state only after a complete
sequence, prints a hashed attempt report, and exits nonzero if it does not
collect. The report belongs in the scheduler's stdout/stderr log; it is not
promoted as market evidence.

The repository includes an inert launchd template at
`ops/launchd/com.qcrl.capture.template.plist`. It deliberately has no calendar
trigger and is not installed. For a future locked cohort, copy it outside the
repository, replace every placeholder (including `__PYTHON__`) with absolute
paths/values, add a `StartCalendarInterval`, and load it only after confirming
that the process has ordinary host DNS/network access. Schedule it at the
locked target; the declared tolerance absorbs bounded dispatch jitter, and the
protocol remains the authority on actual eligibility.

This worker reduces transient failures. It cannot overcome a sandbox that
categorically denies networking, guarantee hard-real-time dispatch, repair a
missed historical window, or authorize evidence promotion.

Generate three unique one-date jobs for a newly locked protocol with:

```bash
python3 ops/launchd/generate_capture_jobs.py \
  execution_truth/protocols/<future-protocol>.json
```

The generator rejects protocols after any target has arrived, uses the exact
current Python interpreter, includes the calendar year to prevent annual
recurrence, wraps execution in `caffeinate -dimsu` for the complete capture,
and never loads the jobs. Installation remains an explicit operator action
through `launchctl bootstrap gui/<uid> <absolute-plist>`.

`caffeinate` prevents sleep after launchd starts the job; it does not wake a Mac
that is already asleep. A host wake event or an operator guarantee that the Mac
will be awake is still required before each target.
