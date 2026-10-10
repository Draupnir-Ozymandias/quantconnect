# Validity probe-cost protocol v1

Offline declaration only: `infra.stream.receive_loop_validity_cost`.
No worker, launcher or cohort exists yet. No execution authority is implied.
The native smoke establishes compatibility only; the prior compact cohort
remains inconclusive and the original reference cohort remains rejected.

## Fixed comparison

Nine cases: three rounds with control/pacing/full, pacing/full/control,
full/control/pacing ordering. Each case retains the six-cycle 4 seconds at
500/s plus 1 second at 3,000/s workload: 30 seconds and 30,000 occurrences.
All lanes use identical separately source-frozen deterministic preparation and
an in-memory sink, **not WebSockets or the actual recorder**. Generator and sink
must be implemented and bound by a separate implementation receipt before any
execution; the declaration's historical machinery flags must not be relabeled.

Control retains four monotonic calls per step. Pacing uses the isolated adapter
with seven calls plus initialization. Full additionally brackets each step with
two CPU stamps and observes worker cgroup counters at fixed 100 ms intervals.
The added stamps must sit outside the exact saved producer boundaries, with
thread/PID/boot bindings. No receiver-clock probe is silently added.

Every lane has a separate 25%-CPU observer unit; control/pacing use the same
wake schedule without proc reads. Workers retain 100% CPU. Each unit retains
512 MiB, 32 tasks and a 120-second limit; no affinity or shared cgroups. Observer
misses are retained, not compressed into a catch-up sampling burst. Observation
sampling runs for the declared worker window, including collection close.

Preallocated row limits: 30,000 producer and CPU-pair references; 512 counter
attempts. Counter inputs are bounded to 4,096 bytes per file; serialized sideband
limit is 32 MiB per case. Overflow is failure, not sample eviction. The receipt
must enumerate actual clocks/callbacks, byte/record counts and all failures.

## Acceptance budgets

These are prospective engineering budgets, **not fitted overhead conclusions**:
combined worker-plus-observer timed CPU <=1.05 and summed sampled RSS maxima
<=1.10 versus that round's control, for both added-probe lanes in every round.
Each phase's nearest-rank p99 begin lateness may add at most 1 ms; worst begin
lateness may add at most 5 ms. Additive tail budgets avoid dividing by a zero
lateness baseline. There is no median/pooled rescue.

All occurrences and diagnostic rows must survive. Full-lane CPU stamp brackets
must be <=1 ms; counter read brackets <=5 ms. All four declared cgroup CPU
counters must be available, with stable boot/PID/process-start/dedicated-cgroup
identity and no resets. Producer phase attainment remains >=99%, maximum
deadline lateness <=50 ms; observer lateness must also be <=50 ms. Requirements
that do not apply to a control lane must not be invented as observations there.

Missing platform fields, unidentified units or zero CPU/RSS control denominators
are inconclusive. Known loss/overflow/reset/resource or threshold failures reject.
When both unknowns and failures occur, retain both lists and never return pass.
Sampled RSS is not a continuous peak estimate. Counter deltas, including zero,
cannot establish event-specific throttling or absence of scheduler pressure.

CPU windows must include observer activity and worker close/durability; do not
subtract baseline costs post hoc. Snapshot serialization, verification and
analysis are outside collection. Independent audits must anchor exact source,
inputs, origin bytes, occurrences, cgroups/limits, operation counts, exits and
ordering. Failed or partial lifecycles do not count as complete cases.

## Preparation and authority

`python -m infra.stream.receive_loop_validity_cost --output /fresh/preregistration.json`
creates an exclusive durable source-bound declaration. Validation rehashes
policy and all declared sources. Later implementation sources and deterministic
input identity must be separately frozen, never retrofitted into this artifact.

Before launching: commit/source-freeze; implement workers/observer/launcher and
independent auditor; fault-test them; perform Linux verification; bind actual
input/source receipts; then obtain explicit finite-run approval. Public collector
state must stay unchanged. No retries, retuning, replay or confirmation within
this cohort. A pass permits only a separately declared validity workload—not
acceptance of the recorder, public deployment, trading or profitability claims.
