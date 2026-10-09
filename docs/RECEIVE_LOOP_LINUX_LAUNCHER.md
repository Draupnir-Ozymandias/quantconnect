# Finite Linux receive-loop launcher

`infra.stream.receive_loop_launch` implements the six-case sequential launcher
against the unchanged overhead preregistration. **Building it is not execution
authorization; no cohort has run and overhead remains unknown.**

Run only from a clean, committed dedicated
`/var/lib/qcrl-stream/receive-loop-overhead-ALPHANUMERIC/source` checkout. Its parent
must be canonical, nonsymlink and never previously launched. Place the original
byte-valid declaration in parent `preregistration.json` and frozen corpus in
`input-corpus.json`; both and the source must be readable by the qcrl account.
The fixed interpreter is `/opt/qcrl-stream/venv/bin/python`. The source inventory
binds the launcher, its tests and this document separately from the original plan
and private worker implementation. No public checkout is fetched or changed.

An explicit `--execute` is required; without it no preflight command runs. Even
with it, preflight requires Linux root, clean tracked source, existing interpreter,
more than four GiB free, correct corpus/plan sources, active daily collector timer
and inactive public stream pilot/observer services. Transitional or unavailable
service state aborts. It never starts, stops or restores those public services.
Preflight also refuses any existing transient units with the proposed launch
prefix, so failure cleanup cannot adopt an older launch's units.

The launcher exclusively claims the parent directory and creates fresh qcrl-owned
evidence. It saves before/after public configuration hash, public commit and service
states, source commit, boot identity and launcher source inventory. First run the
complete regression suite in its own transient unit. Only after success, stage the
private trial implementation and launch pairs baseline/instrumented,
instrumented/baseline, baseline/instrumented. Each producer becomes ready before
its consumer starts; both finish, have properties/journals captured and are stopped
before the next pair/lane begins. There are no retries or warm-up captures.

Every producer uses CPUQuota=100%; consumer and test units use 75%. All units retain
MemoryMax=512M, TasksMax=32, RuntimeMaxSec=120, qcrl user/group, separate cgroups,
RemainAfterExit, NoNewPrivileges, PrivateTmp, ProtectSystem=strict and ProtectHome.
Writable system paths are limited to the new evidence directory; private /tmp is
available for unit fixtures. Existing hardware, quotas and collectors are unchanged.
The consumer independently rejects same-cgroup or unknown-boot execution.

The launcher does **not** invoke archive verification or performance evaluation
during measurements. Successful case completion means unit success and finished
artifacts, not integrity or performance acceptance. After all cases, snapshot exact
originating evidence bytes in a separately hashed inventory; copied launcher claim
and manifest are included. The inventory is a hash binding, not a signature or
proof that its files have been independently downloaded/verified.

On failure, do not retry: retain every completed/partial file, capture available
private-unit properties and journals, and stop only transient units bearing this
dedicated launch's prefix. Missing capture/cleanup/public-state checks are explicit
preservation errors, never successful completion. Record completed case identities,
failure and preservation diagnostics. Public-state drift is reported, never repaired
automatically. No evidence is deleted. A partial inventory or launch failure is not
an acceptable cohort; inspect before proposing a separately versioned experiment.

Future authorized invocation, from that dedicated source checkout:

```bash
sudo /opt/qcrl-stream/venv/bin/python -m infra.stream.receive_loop_launch \
  --root /var/lib/qcrl-stream/receive-loop-overhead-ALPHANUMERIC --execute
```

The launcher never claims `overhead_acceptance_established`. Its result states
`resource_and_origin_audit_performed=false`. Still required before any advancement:
independent originating-byte verification, parsing actual unit order/exits and
configured resource limits, unchanged public-state verification, and the offline
archive/dispatch/performance audit. Test and source-freeze that auditor before
deciding to run the Linux cohort. No Polymarket credentials, trades, infrastructure
deployment, S3 writes or QuantConnect synchronization are involved.
