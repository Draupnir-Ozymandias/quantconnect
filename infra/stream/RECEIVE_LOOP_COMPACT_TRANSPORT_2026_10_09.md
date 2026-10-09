# Compact buffer isolated transport verification — 2026-10-09

## Scope and decision

The closure-free compact model was committed and pushed as `b9f6f0d` before
this work. The new `receive_loop_compact_transport.py` adapter connects only
to numeric localhost using the declared websockets 15.0.1 source and method
bindings. It is not connected to the recorder, Linux cohort launcher, public
collector, or any trading path. The earlier six-case overhead rejection stands.

The adapter delegates the unchanged native receive loop and event processor;
it reuses the reference instance-only socket/gate/assembler proxies with the
compact buffer. Installation occurs inside receiver-thread entry, before the
parent loop including its handshake reads. No native loop is copied, thread ID
is not cached, and no native operation runs while the telemetry lock is held.
Native queue, read-size, encoding and observation limits remain unchanged.

Each buffer can claim only one connection, including after a failed attempt.
Snapshots require the receiver thread to have exited, one parent entry/exit,
and a recorded connector outcome. `complete_observation` describes observation
coverage, not handshake success, fill quality or profitability. The explicit
`connection_outcome` and `connection_error_type` distinguish failed handshakes
from successful connections. Installation may be verified while observation
is incomplete after a clock/budget fault; neither is an overhead acceptance.

## Evidence format

The new schema is `qcrl.receive_loop_compact_sideband.transport.v1`.
It binds the transport, compact buffer and reference proxy source bytes,
retains the original compact implementation binding, and includes receiver
lifecycle and connection outcome fields. Its scanner checks source/scope,
lifecycle values, the canonical artifact hash, and the full encoded bound.
It uses an explicitly in-memory structural projection to the independent model
and reference ordering checks. No projected artifact is persisted or passed off
as reference/cohort evidence. Existing model/reference files and validators
are unchanged.

Flags remain `benchmark_performed=false`, `overhead_acceptance_established=false`,
`public_rollout_authorized=false`, `wire_arrival_measured=false`, and
`orders_authorized=false`. `recorder_integration_verified=false` is explicit.

## Verification

Ten new isolated tests cover:

- Fragmented UTF-8, duplicate text, binary data, ping/control events, application
  receive timeout, orderly close, and observation before the first native read.
- Snapshot rejection while the receiver is running, one-connection enforcement,
  source/method mismatch and URI rejection before claim/network, and rejection
  of model buffers by the transport connector and transport buffers by the old
  reference connector.
- Clock failure and read-budget exhaustion without changing raw delivery;
  flow-budget exhaustion without deadlocking native pause/drain/resume.
- Real queue backpressure and shutdown releasing the blocked native gate,
  with closed-assembler resume recorded separately from normal drain recovery.
- Native parent-loop error delegation exactly once, unsupported installation
  preserving native objects, and native dispatch error identity despite an
  observer-end failure.
- A real aborted TCP/WebSocket handshake, failed pre-receiver connection claim,
  source/scope/lifecycle tampering and encoded-budget failure retaining buffers.

The complete local suite passed: **659 tests** on Python 3.14.6.
The Linux candidate/model/reference/comparator suite passed: **42 tests** on
Python 3.9.25, websockets 15.0.1, in a fresh temporary checkout on Ohio.
Linux/local adapter and test bytes were compared by SHA-256, not inferred from
the Git branch. A final source-binding tightening was rechecked on both systems.

Final verified adapter SHA-256:
`bbeac033953746120df52cbf450a09eb877ecd1f0bb6e2fe49e5a4ac14d324c5`.
Final verified test SHA-256:
`ff3bf4643c368d9b7017a400d2dd09f2b81cf2b1c89d7a995a56778cc1c666db`.

The deployed collector configuration was not changed:
`/etc/qcrl-stream.env` SHA-256 remains
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Stream pilot and observer timers were inactive; the daily collector timer was
active. No deployment, timer change, public capture, quota change, new cohort,
credential use, trading, or QuantConnect sync was performed.

## Next gate

Integrate this candidate into a separate, isolated recorder lane and verify raw
archive/occurrence/sideband linkage and recorder failure paths. Only after that
should a new source-frozen, separately preregistered bounded overhead cohort be
considered. Do not retrofit the rejected cohort or reuse its acceptance result
for this different implementation. The modeled CPU/allocation improvement is
motivation for testing, not proof of receive-path tail or full-recorder gains.
