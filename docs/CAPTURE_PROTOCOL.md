# Predeclared phase-capture protocol

The capture-protocol layer prevents convenient, post-hoc choices about when an
order-book sequence is observed. A version-controlled declaration locks one
exact market slug, resolution source, event interval, early/middle/late start
times, start tolerances, sample counts, and polling intervals before capture.

It remains an unauthenticated, public, read-only evidence process. It contains
no credentials, order submission, background daemon, automatic retry, or
promotion step.

## Contracts

Protocol schema `qcrl.book_sequence_capture_protocol.v1` requires exactly one
chronological capture in each third of the declared market window:

- `early`: first third;
- `middle`: second third;
- `late`: final third.

Every capture must be scheduled after `locked_at_utc`. Its start tolerance is
bounded to 0–1,800 seconds, and its declared polling schedule must finish
before market close even when started at the end of the tolerance. The existing
sequence bounds still apply: 2–120 samples, 1–60 second sleeps, and at most one
hour of scheduled pauses.

Mutable local progress uses `qcrl.book_sequence_capture_state.v1` beneath
`.qcrl/execution_truth/capture_protocols/<protocol-id>/state.json`. The state is
hashed and bound to the exact protocol hash. Changing a locked declaration
causes state validation to fail instead of silently reusing earlier captures.

## Locked September 11 protocol

The first declaration is
[`btc_daily_phase_capture_20260911.json`](../execution_truth/protocols/btc_daily_phase_capture_20260911.json).
It targets the daily market resolving September 10 16:00 UTC through September
11 16:00 UTC. Each phase captures 12 complete bundles separated by five-second
sleeps. The three start windows are:

| Capture | Start UTC | Deadline UTC | New York time (EDT) |
|---|---|---|---|
| `early` | 2026-09-10 17:00 | 17:10 | Sep 10, 1:00–1:10 PM |
| `middle` | 2026-09-11 04:00 | 04:10 | Sep 11, 12:00–12:10 AM |
| `late` | 2026-09-11 15:00 | 15:10 | Sep 11, 11:00–11:10 AM |

Inspect current eligibility without networking:

```bash
./synch.sh evidence protocol-status \
  execution_truth/protocols/btc_daily_phase_capture_20260911.json
```

Preview one capture without networking:

```bash
./synch.sh evidence protocol-capture \
  execution_truth/protocols/btc_daily_phase_capture_20260911.json early
```

Only inside the declared window, execute it explicitly:

```bash
./synch.sh evidence protocol-capture \
  execution_truth/protocols/btc_daily_phase_capture_20260911.json early --execute
```

Substitute `middle` and `late` at their respective times. Execution first
resolves the exact market slug and compares the returned event start, end, and
resolution source with the locked declaration. A mismatch fails before the
sequence requests. A complete capture stores both the contemporaneous slug
resolution and sequence, then atomically records their paths and raw/normalized
hashes in local state. An incomplete acquisition is not recorded as collected.

Starting too early, starting after the deadline, rerunning a collected phase,
changing the declaration, or observing different market terms all fail closed.
A missed phase stays `missed`; do not edit its timestamp or widen its tolerance.
A future protocol is a new file and new protocol ID.

## Evidence boundary and next gate

These three sequences remain one-market evidence. They can reveal whether
displayed spread, depth, price, metadata, and polling gaps differ across that
market's life, but cannot establish cross-market stability. They are not
automatically promoted into Git. After completion, inspect all paths and hashes,
then decide explicitly whether to promote and inventory the six raw artifacts.

The daily contract uses Binance BTC/USDT and a noon-Eastern boundary. It remains
incompatible with the frozen Coinbase BTCUSD midnight-UTC signal. This protocol
must not be used to reinterpret or optimize the research signal.

Only after complete, verified phase evidence exists should QCRL add a
cross-sequence descriptive analyzer. Missing phases must be reported as missing,
not imputed.
