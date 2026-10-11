# Measurement overhead: prior art and a practical stopping rule

Research review, 2026-10-10. Recommendations are proposals, not revised acceptance
policy or deployment authority. All historical rejections remain valid.

## We are not inventing this problem

Google's [Dapper (2010)](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/)
uses sampling and limited common-library instrumentation to make production
tracing useful at low overhead. Exhaustive internal observations are not the
default requirement for a useful production monitor.

[A Survey of Runtime Monitoring Instrumentation Techniques (2017)](https://arxiv.org/abs/1708.07229)
organizes approaches along a synchronous/asynchronous spectrum, relevant to
separating receipt evidence from costly diagnostic analysis.

[Tales of the Tail (2014)](https://research.google/pubs/tales-of-the-tail-hardware-os-and-application-level-sources-of-tail-latency/)
studies scheduling, background interference and hardware/OS/application sources
of tail latency. It documents throughput/energy/tail tradeoffs; tail observations
do not uniquely identify a Python callback or quota as their cause.

Directly relevant Polymarket work exists too:

- [Polymarket Latency Toolkit](https://github.com/freakspace/polymarket-latency)
  describes simultaneous socket-pool comparisons, exact-event arrivals, gaps and
  freshness. Its README separates book age from other event-age distributions.
  Reported numbers and clock/timestamp interpretations are author claims, not
  independently verified measurements we can adopt.
- [poly-book](https://github.com/weiminglong/poly-book) describes Rust ingestion,
  durable logging, replay and integrity analysis. This is an architectural
  reference, not grounds for wholesale migration or trusting microbenchmarks.
- [OpenMarket (2026 preprint)](https://arxiv.org/abs/2607.26245) releases paired
  Polymarket/Binance data and reports a null out-of-sample forecasting result.
  Its abstract retains clock-offset ambiguity rather than equating source-time
  differences with proven physical latency. We reviewed the abstract and metadata,
  not independently its dataset or full pipeline.

No external code was installed or run; external trading helpers remain out of
scope. No uniqueness claim is warranted.

## What our rejection actually means

The 5% combined-CPU budget in `RECEIVE_LOOP_VALIDITY_COST.md` is a prospective
engineering budget for a synthetic instrumentation experiment. It is not a venue
requirement, universal published standard, trading-safety limit or evidence that
the project is unusable. This remains a no-socket synthetic workload, not the
actual live recorder or an execution strategy.

Latest full/control CPU deltas: 0.5224, 0.7832 and 0.6263 CPU-seconds per
30-second/30,000-event case. That is 17.4, 26.1 and 20.9 microseconds of aggregate
actor CPU per event, or approximately 1.74, 2.61 and 2.09 percentage points of one
core averaged across the nominal window. These are combined actor equivalents,
not instantaneous utilization or worker-only service time. They neither rule out
burst pressure nor identify causes of the observed latency-tail regressions.

Thus 27–46% relative overhead does not mean using 27–46% more of the entire
machine. Tail failures and one wide inline clock bracket remain real. Their
strategy-level significance has not been established by this synthetic gate.

## Recommended stopping rule

Timebox one worker-component diagnostic and one application-budget design review.
Do not automatically enter another optimize/freeze/cloud-cohort loop. Evaluate
existing ingestion/measurement designs before adding bespoke infrastructure.

Keep two purposes explicitly separate:

1. Research recorder: preserve raw events, receipt order, bounded queues, loss/gap
   markers, clock semantics and durable evidence; heavy analysis can be offline.
   This supports descriptive research without asserting unperturbed physical
   latency or realistic fills.
2. Diagnostic lane: obtain detailed CPU/pacing/counter observations when needed,
   disclosing perturbation. Sampling changes coverage and requires a new contract;
   do not silently downsample the old evidence.

"Good enough" means the actual recorder meets a declared application budget at
expected and burst loads: bounded queues, detectable loss, acceptable receipt-to-
availability tails, durability, sustainable resource/cost headroom, and uncertainty
small enough for the research question. Five-minute expiry does not imply that
seconds-old data are acceptable for entry decisions. Sub-millisecond strategies
need a different budget from seconds-scale or end-of-window studies.

Choose absolute budgets before new measurements, grounded in decision tolerance,
not by widening a threshold until old observations pass. A practical recorder
contract may differ from a strict low-perturbation probe contract: label it
separately, preserve the 5% rejection and narrow the claims. We need not optimize
forever to answer a different question.

## Finite local worker diagnostic

`infra.stream.receive_loop_worker_components` compares rotated batches of native/
validated wall stamps, CPU pairs, JSON preparation, native `sleep(0)`, and unchanged
packed control/pacing/full steps with no-op or native-zero sleep. Construction and
core materialization/verification are outside batch timing. Failures retain prior
rows and the failed lane, with no replay. Sources and platform are recorded.
This identifies candidate costs, not an additive causal decomposition: allocation,
scheduling and interactions differ. No fixed-rate workload, observer, socket,
Linux cost acceptance or rollout is measured.
