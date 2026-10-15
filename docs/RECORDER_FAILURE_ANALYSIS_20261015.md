# Offline diagnosis of the failed October 15 recorder smoke

The frozen verdict remains **fail**. Durability scheduling provides insufficient
margin for the full persistence path, and producer drain handling does not
correctly distinguish expected closure from premature termination. This review
uses retained bytes and deterministic local tests. It proposes successor changes;
no runtime implementation, threshold, historical audit or native evidence is
modified, and no new execution is authorized.

## Durability: two one-second waits consume the two-second budget

`CompletionStreamLog` flushes after 64 pending records, on a non-frame record, or
when an append observes at least one second since the **end of the last sync**.
The receive loop checks `sync_if_due()` on timeout, but can request another whole
one-second receive while data is pending. It does not cap that receive at the sync
deadline. A frame just before the one-second threshold can therefore postpone the
next check by nearly another second. Heartbeat writes sometimes trigger a sync,
but are not a deadline guarantee. The record-count threshold does not protect a
1-Hz case.

The measured bound starts at application-return `before` and ends at successful
file `fsync` completion. It includes classification/encoding/write, gzip flush,
file flush, scheduling delay and `fsync`. `sync_begin` is recorded **after both
flushes**; the barrier's begin/end interval measures the file `fsync` witness,
not the full persistence path. `last_sync` is updated just after that witness.

Retained completion witnesses show the following (seconds, common host monotonic
clock; sequences are zero-based corpus occurrences):

| Sequence | Previous barrier end | Application-return before | Covering barrier begin | Covering barrier end | Return-to-durable upper bound |
| --- | --- | --- | --- | --- | --- |
| 9 | 1011320.522563234 | 1011320.522648485 | 1011322.520688876 | 1011322.523315777 | 2.000667291926220 |
| 44 | 1011355.522243295 | 1011355.522324648 | 1011357.520785222 | 1011357.522876628 | 2.000551979988813 |

The previous barriers cover ordinals 13 and 52, respectively, excluding failed
frame ordinals 14 and 53. Their covering barriers reach ordinals 16 and 55. In both
cases the next frame arrives just before the one-second check would become due;
the covering barrier occurs after a further frame. Before the covering `fsync`
starts, 1.998040391 s / 1.998460574 s of the 2-s budget is already used. The file
`fsync` witness alone then takes 2.626901 ms / 2.091406 ms. This establishes why
the measured bounds fail; separate gzip/file flush costs and the precise OS
scheduling contribution cannot be recovered from these witnesses.

The nominal worst wait is almost `1 s + 1 s`, leaving essentially **zero** budget
for the remaining path. The problem is structural, not evidence for a new latency
tolerance. A deterministic reproduction places a frame immediately after a sync,
a second at 0.999999 s, another full receive wait and only 1 ms of combined
flush/`fsync` cost. Its return-to-durable bound is 2.000998 s and the unchanged
2-s gate fails. A separate test exercises the actual collector loop's full timeout
with pending data, without native waits or sockets.

### Proposed persistence successor

Keep the 2-s durable limit, 64-record cap, one-second sync eligibility and measured
return-to-successful-`fsync` boundary. Change the isolated recorder's scheduling:

1. Check pending sync eligibility before each potentially blocking receive, using
   a fresh monotonic reading after intervening work such as heartbeat writes.
2. If pending data exists, cap receive timeout at `last_sync + 1 s`, as well as the
   capture/lifecycle deadline and existing one-second receive cap. If already due,
   sync before receiving. Do not round an expired deadline up to a positive timeout.
3. Keep append-side count/time checks and timeout-side sync checks; propagate
   gzip-flush, file-flush and `fsync` faults once, retaining prefixes and witnesses.
   Do not retry failed persistence operations or subtract them from the bound.

This removes the *second* avoidable one-second receive wait, providing roughly
one second for classification/write, dispatch and persistence rather than zero.
It cannot guarantee a hard 2-s bound under arbitrary scheduler or storage stalls.
A successor must test a frame arriving just before the deadline, timeout at the
boundary, continuously arriving frames, the 63/64-record boundary, heartbeat
interference, capture closure, and stalls/faults in each persistence stage. The
actual witness/evaluator remains authoritative even when an injected stall exceeds
the proposed reserve. No new diagnostic subsystem or observer is needed.

This changes receive/persistence scheduling beyond the prior observer-only scope.
It needs a new prospective declaration/source identity and a new reviewed freeze;
the original source-bound parent cannot simply be relabeled as unchanged. Keep
public collectors and legacy paths untouched. These changes are **proposed, not
yet wired into the collector**.

## Drain: exception type alone has no lifecycle context

The producer drain currently appends the name of any receive exception when its
stop flag is unset, then returns. It records no closure timestamp, close handshake
or completed-send watermark. `ConnectionClosedOK` after all sends is consequently
reported in the same way as `ConnectionClosedOK` before the final send. Normal
WebSocket close status alone does not prove that the workload completed.

The retained producer has 68 complete sends, eight `PING` controls and
`control_errors=['ConnectionClosedOK']`. The recorder independently has all 68
ordered frames, `frame_limit`, a complete intact archive/completion report, no
reconnect and no capture error. Thus normal teardown is consistent with the
observations. The drain exception's exact ordering relative to the final send and
capture-closed publication is **unknown**, since no event timestamp was recorded.
It cannot be retrospectively certified as expected closure or excused by this
analysis. The frozen auditor correctly retains its declared failure.

Code ordering explains the ambiguity: the recorder closes its WebSocket inside
the collector, then finishes its footer/archive, returns to `consume`, and only
then publishes `capture-closed.json`. The producer may receive the normal close
before seeing that marker. Additionally, `consume` publishes this marker in
`finally` even after a capture/storage failure; the marker means capture stopped,
not capture succeeded. The producer currently checks its existence only, without
validating its hash/case, and does not explicitly report a missing marker at the
bounded drain deadline.

There is also an independent masking race: if `stopped` becomes set while
`conn.recv()` is in progress, a subsequently raised unexpected exception is
suppressed by `if not stopped.is_set()`. Neither a normal-close blanket exception
handler nor that stop flag is a sufficient success criterion.

### Proposed drain successor

Use the existing producer result/control artifacts to retain one bounded terminal
receive event with type, monotonic time and actual handshake close codes. Retain
the exact completed-send count and final successful send bracket, without changing
payloads, order, workload pacing or limits. No new diagnostic layer is required.

Classify a normal close as a **candidate expected close** only if the complete
scheduled send population finished by that event's timestamp. Closure before the
last completed send, abnormal closure, unexpected control traffic, receive faults,
a live drain thread after its join bound, or a missing closure/recorder completion
witness must remain failure or unavailable evidence. Do not suppress an unexpected
exception merely because a stop flag was set concurrently. A close concurrent
with a final send whose successful end is not yet witnessed cannot be certified.

Reconcile the candidate with the case/hash-bound existing capture-closed marker
and successful recorder summary/completion/archive evidence within existing
bounded deadlines. A marker can arrive after normal transport closure; record
the close once and wait only for the existing lifecycle evidence. Its mere
presence is insufficient: require `frame_limit`, exact population, no recorder
error/reconnect and verified completion linkage. Failure/absence never becomes
success because the close codes are normal. Do not reconnect, retransmit, extend
unit/drain limits or replay the case. Final classification can be performed by
the prospective offline auditor against the paired producer/consumer artifacts.

A successor must change the producer witness and audit contract together, with a
new source/plan identity. The failed evidence and original strict audit stay
unchanged; no blanket `except ConnectionClosedOK: pass` fix is proposed.

## Deterministic verification and preservation

`tests/test_recorder_failure_boundaries.py` adds 14 tests of the existing paths:
near/exact/over-one-second sync eligibility, 63/64 records, empty pending state,
full receive timeout, all three persistence-stage faults without retry, exact 2-s
threshold, normal close after all sends versus premature normal close, abnormal
close/read fault, timeout, unexpected control preservation, stop-during-receive
masking, unsigned capture-marker adoption, missing-marker timeout and marker
publication after recorder failure. Real WebSocket exception classes are injected
without connecting; thread interleavings and clocks are deterministic. These are
regression reproductions of the frozen shortcomings, not assertions that a future
fix has been integrated or validated on Linux.

The [original result](RECORDER_ABSOLUTE_SMOKE_RESULT_20261015.md), execution freeze
`f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`, origin inventory,
archive and independent failed audit remain unchanged. Runtime implementation and
the original recorder declaration/2-s threshold are unchanged. Added test inventory
means any future execution still requires a new source freeze/readiness population.
No native replay, new smoke, cohort, resource change or public collector operation
was performed. This diagnosis establishes scheduling/lifecycle defects; it does
not establish performance of the proposed successors.

Offline diagnosis verification: all **1,142 tests passed in 89.878 seconds** on
Intel macOS / Python 3.14.6, including the 14 deterministic boundary/fault tests.
Retained native inventory/archive/failed audit hashes and original c9207f...
recorder declaration reverified unchanged. Private offline log/receipt:
`.qcrl/reviews/recorder-failure-analysis-offline-20261015/`. This is local offline
verification, not Linux/native validation of the proposed changes.
