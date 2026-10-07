# Receive-path telemetry contract v1

Implemented: `execution_truth.receive_path`, the pinned opt-in
`execution_truth.receive_adapter.ObservedSocket`, and versioned recorder/pilot
integration with independent archive validation. Legacy declarations, watchdogs,
defaults, archives and EC2 checkouts remain unchanged. Declaring a contract does
not launch a collection or claim that any measurement was taken.

## Versioned artifacts

- `qcrl.receive_path_contract.v1`: binds the exact source plan, market-specific
  stream specification, observer/boot monotonic clock domain and fixed policy.
- `qcrl.bracketed_clock.v1`: samples monotonic, UTC, then monotonic, retaining
  both endpoints rather than guessing an instantaneous paired timestamp.
- `qcrl.receive_path_delivery.v1`: binds connection, FIFO occurrence, frame
  span, fragment count, complete raw-message hash, receiver observations,
  application delivery and optional adapter-measured diagnostics.

Policy and artifacts use SHA-256 integrity links. Hashes are not signatures or
authentication. `validate_contract` rejects policy changes even if rehashed;
`validate_delivery` independently checks schema, authority, stream/contract binding,
message type/hash, fragment provenance, clock domains and elapsed calculations.
The segmented archive verifier supplies the retained raw message and header
contract for every v4 frame, independently checking its telemetry binding.

The clock domain must identify one observer and boot. Monotonic seconds must
never be subtracted across hosts or reboots. Source stream-spec binding prevents
parallel markets on the same observer from sharing occurrence identities.

## Measurement boundaries

The proposed receiver boundary is the library's data-frame callback entry before
assembler processing. The delivery boundary is immediately after the application's
`recv()` returns, before classification. Neither is packet/kernel arrival.

The pinned [websockets 15.0.1 implementation](https://github.com/python-websockets/websockets/blob/15.0.1/src/websockets/sync/connection.py)
has a receiver thread and assembler; the documented
[client factory and frame-buffer setting](https://websockets.readthedocs.io/en/15.0.1/reference/sync/client.html)
are respected by the pinned adapter. Do not replace the assembler, disable
flow control, or represent `max_queue=16` as a strict message-depth cap.

For observation bracket `[r_before, r_after]` and delivery `[d_before, d_after]`,
the local elapsed range is `[d_before-r_after, d_after-r_before]`. Wide brackets
(over the prospectively declared 1 ms diagnostic limit) and overlapping brackets
remain explicit, with `timing_eligible=false`; negative lower bounds are retained,
not silently clipped. Impossible reversed observations fail validation. UTC is
not corrected. This eligibility flag concerns local sampling precision only,
not clock accuracy across hosts, order acceptance, fills or profitability.

First-fragment-to-delivery and last-fragment-to-delivery intervals are separate.
The former can include fragmentation/reassembly time. The latter still includes
library processing, buffering, decoding and application scheduling; it is **not
pure queue wait** or network latency.

## Bounded sideband tracker

`ReceivePathTracker` records metadata, not another copy of the payload stream:
incremental hashing, at most 64 completed-message markers, at most 64 fragments
per observed message, and at most 262,144 message bytes. These are telemetry
budgets, not new transport limits. Overflow disables sideband attribution until
the next connection; the adapter preserves the actual stream and records
the resulting unavailable reason. No guessed match or automatic recovery occurs.

Text and binary types are distinct. UTF-8 code points can span fragments.
Protocol ping/pong/close frames do not consume application-message IDs; a text
`PONG` is an ordinary text message. Duplicate payloads retain distinct FIFO
occurrences. A mismatch disables attribution instead of searching ahead by hash.
Connection transitions report abandoned pending markers and partial fragments,
reset occurrence counters and reject late callbacks from a retired connection.
Same-boot monotonic chronology is retained across reconnects; a new boot requires
a new clock domain/tracker, not silently resetting a backwards clock.
Internal locking protects metadata across receiver and consumer threads. This
does not establish that a future adapter's callback/assembler locks are safe.

`pending_marker_depth` is metadata occupancy, **not library queue depth**.
`library_queue_depth`, `library_backpressure_active` and
`reader_loop_stall_seconds` default to unknown. Explicit adapter observations
are accepted only with validated numeric/boolean types. They are not inferred
from metadata occupancy, CPU throttling, message age, or `recv()` wait time.
These external diagnostics remain context, not independently proven causes.

## Safe integration sequence

1. Add an opt-in adapter pinned to websockets 15.0.1. Observe callback entry,
   application delivery, actual queue/backpressure state and reader-loop phases;
   document the exact sampling point and units for each external diagnostic.
   Use stable callback/factory surfaces where possible; explicitly test any
   version-specific internals. Cast library opcode enums to contract integers.
2. Test the real dependency with local loopback, fragmented UTF-8, identical
   messages, interleaved protocol controls, idle timeouts, overflow, reconnect
   races and shutdown. Validate thread ordering without placing metadata locks
   around potentially blocking assembler operations. Measure observer overhead.
3. Add an explicitly versioned opt-in stream/pilot policy and archive verifier;
   bind every delivery to its retained raw frame/message. Do not retrofit v1
   telemetry onto older socket-named timestamps or enable it by default.
4. Run a bounded smoke after those tests pass, then declare a prospective shared
   comparison. Keep region, compute, library flow control and watchdog/retry
   policy unchanged. Separately authorize deployment and new captures.

Steps 1–3 are implemented and tested locally. Step 4 still requires a separately
authorized EC2 smoke; no wire timing or production readiness is claimed.

## Foundation verification — October 7, 2026

All 446 repository tests passed, including 19 receive-path tests covering clock
ordering, wide/overlapping brackets, invalid clock domains and values, rehashed
semantic tampering, parallel-market bindings, duplicate FIFO occurrences,
fragmented UTF-8, binary/text distinctions, control frames, reconnects, backwards
clocks, missing markers, mismatches and bounded sideband overflow.

A synthetic, non-networked smoke independently validated generated delivery
artifacts for fragmented and duplicated UTF-8 messages, with explicit unknown
queue metrics. It is retained in ignored
`.qcrl/reviews/receive-path-smoke-20261007-mOcnge/smoke.json`, report hash
`0a6734852c30d6720119596cf476bd2bedbde70651cef7bd910479ca2a0c9160`.
This is **not** a real library/loopback or live Polymarket smoke. No collector was
restarted, deployed or reconfigured, no new markets were scheduled, and no
GitHub/QuantConnect synchronization was performed. Changes remain uncommitted.

## Adapter and real-library loopback verification — October 7, 2026

`ObservedSocket` is explicitly instantiated; no existing connector imports or
enables it by default. It requires exactly websockets 15.0.1 before connecting,
accepts only the public market WebSocket endpoint or local loopback, disables
proxy auto-detection, and retains the original 16-frame high-water setting,
262,144-byte message cap, no WebSocket compression and no automatic protocol
keepalive. It does not provide credentials or trading interfaces.

The adapter uses the documented connection factory with a **version-specific
`process_event` override**, observes frames before calling the parent handler,
and never holds metadata locks across parent receive/event/close operations.
Receiver callback errors disable telemetry, not parent protocol processing.
There is one application reader; competing calls are rejected without disturbing
the first reader. Idle timeouts remain timeouts and do not consume markers.
Application-side telemetry errors return the unchanged raw message with a
separate `qcrl.receive_adapter_failure.v1` record, independently validated by
`validate_adapter_failure`; they do not invent timing intervals.

Real queue diagnostics use **version-specific assembler internals** under its
mutex: `frames.qsize()` and `paused`. The mutex is released before taking the
metadata lock. Queue depth is sampled after the delivery clock bracket and before
consuming its marker; it is a point observation, not peak depth or an event-level
residency measurement. Closed-assembler depth is unknown because its queue can
contain an EOF sentinel. Backpressure remains measured library state.

`reader_loop_stall_seconds` measures monotonic time outside `recv()` since the
previous successful return or timeout. It includes observer/caller work, excludes
the intervening blocking receive, and is **not** proof of a frozen reader. Its
first value is unknown. This diagnostic's historical field name is retained.

All **458 repository tests passed** in the isolated ignored
`.qcrl/receive-path-venv` runtime with the real pinned dependency. Twelve adapter
tests include ten real localhost tests for fragmentation, UTF-8, duplicate/binary
messages, protocol controls, idle and partial-fragment timeouts, real backpressure
and draining, telemetry overflow, callback/application errors, reader concurrency,
reconnect races and shutdown. Localhost sockets required the approved network
sandbox override; no external service was contacted. Without the optional
dependency, the real-library tests are explicitly skipped, not claimed passed.

Finite throughput smoke:

```bash
.qcrl/receive-path-venv/bin/python infra/stream/receive_path_loopback.py \
  --output .qcrl/reviews/receive-path-loopback-NEW.json
```

Default limits are three rounds, 300 identical messages per batch and two payload
sizes, with baseline/observed order alternating. Output creation is exclusive.
The script validates all observed delivery records after the timed batches,
binds the source files/runtime, and never contacts Polymarket or AWS.

Final retained run: `.qcrl/reviews/receive-path-loopback-20261007-validated.json`.
Report hash: `3ca78c364e29663e368e097d79ffa31b99be830e06ca6e0a02409f3ecd39180b`.
All 3,600 messages were unchanged; all 1,800 instrumented messages had available,
timing-eligible metadata, with no unavailable reasons in that run.

| Local batch, 300 messages | Bare receive median | Observed median | Ratio |
| --- | --- | --- | --- |
| 543-byte payload | 6.460 ms | 18.334 ms | 2.84x |
| 2,079-byte payload | 7.529 ms | 22.014 ms | 2.92x |

Earlier retained runs showed 2.21–2.96x ratios. Do not cherry-pick the fastest run.
These are localhost batch throughput diagnostics on macOS/Python 3.14.6, including
receiver/reader work and scheduling—not calibrated CPU cost, complete recorder
overhead, network latency, EC2 performance or a deployment acceptance threshold.
They show that instrumentation can perturb the measurement and must remain opt-in.

## Recorder/archive integration — October 7, 2026

The opt-in stream schema is `qcrl.public_market_stream_spec.v4`; the prospective
pilot schema is `qcrl.btc_5m_rolling_pilot.v5`. Enable with `--receive-path`,
`--profile` and `--defer-verification`; `--resilient` remains an independent
choice, not a silently changed watchdog/retry policy. Without the new flag,
all previous schema choices and collector behavior are preserved.

The v4 specification binds the source plan hash and fixed receive policy. The
session header separately retains the contract bound to the complete spec hash,
avoiding circular hashes. The default clock domain is a unique per-capture UUID:
an isolated domain within one process/observer boot, never reused across captures.
This is not proof of machine identity. Tests may explicitly supply a domain.

Every retained text frame has unchanged `raw_text` plus a delivery or failure
record. Reconnect reset records retain discarded marker/fragment counts. Archive
verification checks contract/policy/raw-message hashes, connection resets,
occurrence order, fragment spans, local clock chronology and footer totals.
Unknown telemetry stays unknown and cannot resume mid-connection. Available,
unavailable and locally timing-eligible counts are reported separately from
lifecycle completion. A quota footer may omit a received frame that could not be
written; such an archive fails complete v4 verification rather than claiming it
was retained. Existing v3 freshness/cross-site analyzers reject v4 inputs: no
automatic substitution of the new measurement boundary is permitted.

Local verification includes a real localhost subscription → book/PONG recording
→ sealed gzip archive → independent verification, offline reconnect/unknown
fixtures, and seven semantically tampered archives with recomputed integrity
hashes. These are local mechanics tests, not Polymarket captures or EC2 evidence.
All 462 repository tests passed in the pinned local runtime after integration;
the real-library tests ran rather than being skipped.

Next: bounded EC2 smoke covering Linux/Python 3.9 behavior and complete-recorder
storage/processing overhead, before any prospective shared comparison. No EC2
configuration or capture schedule was changed by this integration.
