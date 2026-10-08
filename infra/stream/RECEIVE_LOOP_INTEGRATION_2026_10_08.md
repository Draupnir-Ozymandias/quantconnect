# Private recorder/sideband integration — October 8, 2026

## Outcome

**Private unit-fixture integration and independent validation pass.** No timed
overhead comparison, finite benchmark cohort, public capture or deployment was
started. Instrumentation remains diagnostic-only, with performance acceptance
explicitly unestablished.

`infra/stream/receive_loop_lane.py` provides a numeric-localhost fixture API and
an independent archive/sideband verifier. It does not provide a producer, schedule,
cgroup launcher or CLI campaign selector. The fixture uses the original recorder
under a private scoped single-pass writer and diagnostic 128-marker variant.
Production collector files and receive-policy declarations are unchanged.

## Integration design

`DiagnosticSocket` inherits `ObservedSocket.recv`, `queue_snapshot`, `send` and
`close` rather than duplicating or changing their delivery logic. Tests assert
method identity for delivery, queue and close. Only diagnostic construction and
the tracked callback parent are new.

The probe's private parent-extension accepts a `ClientConnection` subclass while
requiring the native constructor, receive loop and close method to remain
inherited unchanged. The diagnostic parent observes the frame for the v3 tracker
and then delegates once to the native callback. Probe dispatch brackets enclose
that tracking work. There are no global library-class changes or new threads.

The original prototype's source hash changes because of this narrowly scoped
parent-extension. Its earlier report and hash remain historical at commit
`5235d03`; they are not rewritten to claim this integration already existed.

## Independent verification

Verification does not trust `complete_observation` or a matching JSON hash alone.
It independently checks:

- Exact envelope/sideband/read/flow field sets, source implementation hashes,
  explicit non-trading/non-benchmark flags, encoded byte limits and population caps.
- Contiguous read iterations, one receiver-thread identity per connection, finite
  monotonic ordering, gate/read outcomes and returned byte counts.
- Contiguous, nonoverlapping dispatch frame ranges; protocol/non-frame callbacks
  are not counted as application messages.
- Pause/resume operation order, native >16 / ≤4 rules, closed-assembler release
  context and callback intervals. It does not force a cross-thread total order.
- Full sealed archive verification, row-chain recheck, exact final record/spec
  binding, private receive-v7/128-marker fixture identity and connection populations.
- For each known raw delivery, first and last receive-marker ordinals locate their
  independently scanned dispatch ranges. Both marker clock brackets must lie
  inside the corresponding callback dispatch bounds. Fragmented messages can
  legitimately span ranges.
- The complete sideband cannot omit frame callbacks already observed in archived
  alignment counters. Extra control/close callbacks after the last application
  delivery are not misclassified as additional raw deliveries.

Frame-range lookup uses precomputed range ends and binary search, not a
frames-by-reads nested enumeration. Queue samples and clocks still do not prove
wire arrival or a message wholly contained in one socket read.

The result retains separate counts for linked, unknown, incomplete-sideband and
timing-ineligible markers. Archive integrity can pass while attribution remains
unavailable. Full fixture attribution requires every delivery to be linked,
complete sidebands and the existing first/last local timing-eligibility checks.
This is not a performance or public-rollout acceptance decision.

## Unit-fixture and tamper results

The short real localhost fixture records five application deliveries: duplicate
book text, a fragmented book message, price text and a text PONG. All five raw
deliveries are preserved and all five markers bind to dispatch ranges.

With an injected observer-clock failure, the same five deliveries still form a
valid sealed archive. The sideband is incomplete, all five markers are classified
as unavailable for sideband attribution, and `attribution_available` is false.
The receive tracker and raw stream are not disabled by the probe-only fault.

Tests reject rehashed frame-range gaps, wrong archive bindings, markers outside
dispatch brackets, contradictory completeness, boolean ordinals, fabricated
resume transitions, extra payload fields, duplicate/excess connections and a
parent that replaces the native receive loop. Rehashing malformed data does not
make it valid evidence.

Final local full suite: **599 tests passed**, 18.603 seconds.
Final Linux/Python 3.9 checks: **36 tests passed**, 1.128 seconds—seven contract,
twenty-one prototype and eight integration tests. Linux tests ran in a fresh
temporary checkout, not the public collector checkout.

Only finite unit fixtures were exercised. Temporary fixture archives are not
market evidence or a benchmark cohort. No CPU, memory or tail-overhead conclusion
is drawn from unit-test runtimes.

## Source bindings

Private integration/verifier SHA-256:
`8605602728044a554621e7dd9767caf04ab0e03d52b42844bf20a43d2e208e63`

Extended prototype SHA-256:
`546dbeb7d7c49fa3ae8cd00d879d11ade672ca69507cfc1a7aafbaa0681bb7e4`

Integration tests SHA-256:
`886f089820a6fb50247809cf547d375846d6b18501c8bc0b3f23f5aa9638e888`

The source-pinned [observation contract](../../docs/RECEIVE_LOOP_OBSERVATION.md)
and four pinned websockets 15.0.1 files remain unchanged.

## Next gate

Prospectively declare a finite **baseline versus instrumented overhead cohort**
before running it. Both lanes must use the same frozen corpus, single-pass writer,
diagnostic 128-marker v3 policy, quotas, memory/tasks/runtime, durability and
application delivery logic. Keep case order, acceptance thresholds, measurement
boundaries and post-measurement sideband serialization/audits explicit.

Require complete original bytes, raw/marker/dispatch integrity, no sideband loss,
timing-eligibility denominators and acceptable CPU/memory/tail impact before
interpreting gate or read durations. Keep profiling context separate from
event-specific causal claims. No hardware upgrade, public implementation change,
credentials, trades or QuantConnect synchronization occurred or is authorized
by this unit-fixture result.
