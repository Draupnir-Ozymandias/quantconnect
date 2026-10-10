# Packed validity prototype — offline only

The October 10 v1 cost rejection is unchanged. Its source, plan, evidence,
thresholds and report remain frozen. This prototype has no launcher integration,
deployment command or performance-acceptance authority.

## First change: representation, not diagnostic sampling

`infra/stream/receive_loop_validity_packed.py` retains numeric observations in
preallocated `array('d')` columns rather than allocating a `ProducerSample` and
two `CpuStamp` objects for every full-lane step. Raw occurrences still use a
bounded reference list and the original deterministic preparation operation.
Per-step prepare/sink closures and hot-path partition/CPU-result dictionaries
are also removed. This does not eliminate all allocations: Python clocks return
numbers, preparation builds JSON, and counter observation is unchanged because
this core is not integrated with an observer.

Wall calls remain 4/7/11 per step for control/pacing/full, plus initialization;
full still takes two thread CPU samples per step. It preserves the individual
pacing boundaries and CPU-pair enclosures rather than silently sampling fewer
events. Full numeric payload is 14 columns x 8 bytes x capacity (3,360,000 bytes
at 30,000 steps), excluding array headers, raw references and raw strings.
This is a storage calculation, not measured RSS or an accepted memory ratio.

Inline checks retain finite observations, monotonic order, thread identity,
capacity, CPU reset/enclosure and exact native exception propagation. Global
wall ordering is checked more strictly than the original CPU-stamp path.
Partition construction and its conservation check now occur after collection,
using the original independent `verify_core` verifier. This deliberately shifts
validation timing: a post-close validation failure cannot become valid evidence,
but it is not an identical hot-path failure instant. Serialization and hashing
remain after close. Native calls are not retried, failed instances cannot replay,
and delivered raw prefixes survive post-send CPU failure.

## Correctness evidence and limits

Tests compare exact original and packed canonical reports using the same injected
clock traces for all three lanes. They check exact clock/CPU/sleep call counts,
bounded packed storage, execution barriers, overflow before native operations,
prepare/sleep/CPU faults, retained deliveries, clock regression, nonfinite values,
thread change, CPU reset, partial reports and rehashed tampering/authority claims.
The versioned wrapper labels results prototype-only, cost-unverified and
execution-unauthorized; `verify_prototype` rejects contrary claims.

Verification on October 10: all **805 local regression tests passed**, including
13 packed-prototype tests. The targeted original-worker/prototype set passed
21 tests. No Linux performance experiment was run for this prototype.

These deterministic comparisons are not Linux cost measurements or universal
proof of semantic equivalence under every fault. No real-time throughput,
RSS-ratio or low-perturbation claim is made. No EC2 action, new cohort,
infrastructure change or QuantConnect sync is part of this step.

## Next experiment, not yet preregistered

First review whether post-close partition validation is acceptable, and whether
the full per-step CPU coverage should remain mandatory. Keep observer identity
checks and independent live bindings intact. Then add source-bound isolated
lifecycle integration and native smoke tests before separately declaring a new
cost experiment. Its plan must explicitly identify representation/validation
changes, fixed comparisons and resource method; source-freeze before execution.
Do not alter v1 thresholds or rerun the rejected cohort in search of a pass.

The next isolated fixture integration is documented in
`docs/RECEIVE_LOOP_VALIDITY_PACKED_LIFECYCLE.md`. It remains eight-message-only
and does not provide native unit or cost acceptance.
