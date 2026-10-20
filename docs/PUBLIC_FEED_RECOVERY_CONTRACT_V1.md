# Prospective public-feed recovery contract v1 — offline implementation

**Historical application FAIL and every original threshold remain unchanged.**
V5 remains an interrupted recording with unverified/censored coverage. Recovery
cannot repair that recording, reconstruct missed messages or establish venue
completeness. No new market/window, approval packet, deployment or public capture
is created by this contract.

The opt-in contract identity is `qcrl.public_acquisition_recovery.v1`, payload SHA:
`437621e12790da88843eb418b649af6a00972566b21a86d94e11a43b266c6f04`.
Its hash is pinned literally in a regression test. This is a prospective method
identity, not a source/runtime freeze or execution authorization. The expired v5
plan, policy hashes, retained bytes and reports remain unchanged. The existing
worker/operator still validate the one-attempt v5 plan and reject a recovery spec;
a new packet and explicit prospective declaration must wire this opt-in path.

## Reuse and ownership

`recorder_public_capture.collect(..., recovery_policy=policy())` uses the existing
segmented writer, persistence schedule, completion witnesses, storage guard,
verified TLS requirements, heartbeat, stop ownership, process guards and pre-close
publication callback. Omitted policy keeps one attempt. A policy/spec mismatch
fails before connecting. Recovery requires the existing `stream_plan` resilient
spec, including its three-connection limit and exact `stream_resilience.POLICY`.

The existing `DataWatchdog` controls initial-book, selected-data-silence and stale
flow faults. Existing `retry_delay` supplies equal jitter. Existing book-level
validators and millisecond timestamp parser qualify bootstrap snapshots. No
receive-path instrumentation, alternate observer, replay service or diagnostic
framework is added. Extra JSON/level validation and lifecycle writes occur after
the original application-return bracket; their CPU, allocation and persistence
cost remain inclusive and unquantified. The transport exception-origin wrapper adds a Python call/return before the
existing return observation; it adds no clock inside that bracket and is not
assumed timing-neutral. New epoch begin/end clock reads occur in connection
control outside the bracket. No overhead is subtracted or assumed negligible. Original UTC/RSS brackets and acceptance limits stay authoritative.

Only the acquisition thread chooses recovery, cancels/reads the old interrupt,
closes the old socket, waits, opens the next socket and sends the full subscription.
A second socket cannot overlap a predecessor. A failed or guard-interrupted retry
close is fatal, is not attempted again, and preserves earlier receive faults.
Emergency interruption never establishes normal completion. The final epoch can
prove scheduled acquisition ownership using its original interrupt receipt;
that does not erase earlier faults or establish gap-free coverage. Cleanup close
return is reported separately and never proves graceful peer closure.

## Connection epochs, resubscription and fresh books

An epoch is one numbered connect attempt (1–3), including failed handshakes. Its
retained fields include attempt/subscription times, per-asset qualifying book
receipts, eligibility boundary, last return boundary, end, reason and ownership.
Every incoming text witness and archive row carries that connection number. Hash
linked `connection_epoch` and final `recovery_end` records bind the lifecycle to
the same archive as the text population; publication retains this metadata.

Each successful handshake sends the complete original market subscription.
A successful send is not a subscription acknowledgement. Heartbeat state and
watchdog/book state reset for each epoch. Old books, deltas and prior eligibility
never bootstrap another connection.

Eligibility starts only **after** receiving a structurally valid full `book`
snapshot for **each selected asset on that connection**. Both sides must be
arrays with valid price/size levels under the existing book contract; empty sides
are allowed. The market/asset must match. Each snapshot must have a valid CLOB
millisecond timestamp with nominal delivery age between 0 and 5 seconds; neither
missing/invalid timestamps, future timestamps nor stale books qualify. At bootstrap
completion both qualifying receipts must also be no more than 5 monotonic seconds
old. This is nominal clock-based bootstrap evidence, not an independent statement
of exchange-state freshness or maintained order-book accuracy.

PONG, trade, delta, unknown and creation metadata do not satisfy the book gate.
Bootstrap texts stay in the raw population; the triggering text is excluded from
the separate eligible population. Eligibility is local post-bootstrap observation,
not continuously verified book state. Existing stale-flow/data-silence watchdogs
remain conservative controls, not proof of every intervening state.

## Gaps, silence and count eligibility

Every transport/watchdog failure records a connection gap and its reason. The
conservative availability end is the last returned text's original **before**
endpoint, or subscription/attempt time if no text returned. Scheduled normal end
uses its ownership-proven endpoint. Thus a quiet interval immediately before a
fault is not silently declared covered merely because the socket once opened.

The offline report exposes raw acquisition windows and their explicit unavailable
complement, and separate book-eligible windows and their ineligible complement,
from first attempt through the common planned deadline. These include initial
connection/bootstrap, failed attempts, close/backoff, resubscription/bootstrap
and any terminal remainder. Gap boundaries remain conservative; detection time
is not asserted to be the instant feed loss began. Gaps never close retroactively.

The primary descriptive population remains **every linked incoming text once**:
no de-duplication, batch expansion, replay, heartbeat filtering or exclusion of
accepted creation notices. Identical deliveries after reconnect are distinct
observations; reconnects provide no missing-message recovery guarantee.

All 60 one-second rows retain original interval-aware lower/upper archival counts,
wide-bracket labels, ambiguity and unplaced handling. A separate eligible count
uses only occurrences whose **entire return interval lies strictly inside** one
fresh-book epoch window. Bootstrap/boundary texts remain in raw counts. This is
an explicit inclusion rule, not a claim that boundary texts were never received.
No eligible/raw populations are silently combined.

A bin wholly inside a verified local acquisition window may say
`observed_zero_archived_texts` when its archived upper count is zero. It means
observed local silence, not zero venue events. A bin touching an availability
boundary or gap is `unavailable_or_boundary`; zero retained texts there imply
unknown activity. Book eligibility is a separate column, so connected-but-waiting
for books is distinguishable from disconnected acquisition. All feed-activity
upper bounds and full-minute feed population remain null; no combined acceptance
badge or reconnect-based full-coverage claim is produced.

The reporter reuses completion/segment verification, compares final lifecycle
markers/footer with the result, replays book qualification from linked raw frames
and original delivery stamps, and checks connection/clock chronology. Corrupt or
missing linkage raises a fault instead of fabricating coverage. A future outer
reporter must still independently bind consumer/checkpoint, case, source/runtime,
domain and epoch. The method report explicitly has no new study-plan identity;
the reference hash names its inherited counting method only, not expired v5
execution authority. A missing final marker or completion may leave only partial
bytes and unresolved counts.

## Retry, runtime and storage bounds

- At most **three attempts / two retries total**, not a resettable streak counter.
  Recoverable failures are transport-origin OSError/premature WebSocket closure
  (including `ConnectionClosedOK`) and the four declared watchdog reasons.
  Certificate verification, foreign bindings, binary/oversize, clock/linkage,
  archive/storage faults, cancellation and fired/error interrupt receipts are
  fatal. An archive OSError cannot be mistaken for a transport failure.
- Existing equal jitter gives waits of **1–2 seconds**, then **2–4 seconds**;
  no third retry occurs. Waits are clipped to the original acquisition deadline,
  with persistence and reserve checks. Full subscription and fresh books are
  required again. No unit/controller/metadata retry is implied.
- One original M0+65-second stop deadline and **90-second total acquisition
  process guard**, never renewed on retry. The first readiness cutoff remains
  before M0−1 and at most ten seconds; subsequent opens/subscriptions get at most
  ten seconds clipped to the common deadline. Ordinary recv waits retain the
  persistence deadline cap. A fired process guard can terminate before graceful
  publication; neither retries nor storage reserves guarantee publication.
- Each cleanup close remains bounded by five seconds; retry close is also capped
  by the existing total acquisition guard. Final pre-close publication precedes
  final close. The unit ceiling remains 240 seconds; CPUQuota 75%, MemoryMax
  512 MiB and TasksMax 32 are unchanged. No background retry queue exists.
- **60,000 texts total**, one completion population/segmented archive across all
  epochs; 262,144-byte frame cap and queue 16 per current socket. Existing
  1 GiB uncompressed / 256 MiB compressed archive limits, private 1 GiB spool,
  64 MiB auxiliary / 32 MiB completion bounds, disk reserve, terminal reserve,
  file-count and symlink checks remain. Epoch/control lists are bounded by three
  attempts. Storage exhaustion is fatal; no eviction, rollover or overwrite.

## Local validation and next gate

The local regression suite exercises actual recorder, writer, completion and
reporter paths, including real localhost WebSocket resubscription and real blocked
socket I/O interrupted by the existing emergency guard. Deterministic tests cover
normal stop, premature normal/abnormal closure, retry exhaustion and clipped waits,
subscription/PING faults, all-book reset, malformed/stale/future/missing books,
clock/storage/linkage faults, deadline/close races and post-cancel fired-state
retention. Original single-attempt and stop/publication regressions also remain.

Full offline suite checkpoint: **1,271 tests passed in 172.800 seconds**. After
final report identity/boundary-only additions, **22 focused recovery tests passed
in 4.099 seconds**. Python 3.9 grammar accepts changed sources locally; this is
not execution under Python 3.9. Logs and local validation receipt:
`.qcrl/reviews/public-recovery-offline/`.

These are Intel macOS/Python 3.14.6 offline/local-loopback tests, **not Linux/TLS/public-feed
validation or resource acceptance**. Independent UTC accuracy, continuous RSS
peak, incremental observer overhead and underlying v5 disconnect cause remain
unknown. No SSH, infrastructure change, public subscription or native run is
needed for this work. Before a public proposal, a new source/runtime-bound packet
must explicitly declare this retry/eligibility contract and its exact target;
prior v5 approval cannot authorize it. Do not repeat a six-case cohort or add a
standalone observer experiment on the strength of these local results.

## Subsequent v6 integration — October 20

The [new v6 packet](PUBLIC_FEED_COUNTS_SUCCESSOR_V6.md) wires this opt-in policy
through an explicit controller/metadata/consumer/report version selection. The
v5 default and historical recordings remain unchanged. This integration note
does not grant staging or execution approval or change the recovery policy hash.
