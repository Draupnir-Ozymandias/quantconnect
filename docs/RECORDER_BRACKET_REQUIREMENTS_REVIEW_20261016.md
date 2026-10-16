# UTC and RSS bracket requirements — offline claim review

**Recommendation: prospectively narrow the scientific claims before another
observer optimization.** The existing evidence supports finite localhost
retention/completion findings and component measurements. It does not support
the original combined application-budget pass. This document is a review, not
a replacement declaration, threshold change, implementation or run approval.
The four latest UTC failures remain a separate blocker to that original claim.

## Origin and rationale

The [minimum-useful-recorder draft](MINIMUM_USEFUL_RESEARCH_RECORDER.md) explicitly
calls its absolute budgets prospective design assumptions for one-second-binned
descriptive research. It describes <=1-ms local UTC brackets as a bound on local
sampling precision, not global clock accuracy. It provides no derivation tying
1 ms to a permitted bin-assignment error or a downstream estimator's tolerance.
One millisecond is 0.1% of a second; that ratio alone is not a sufficiency proof.

The [application preregistration](RECORDER_APPLICATION_BUDGET_PREREGISTRATION.md)
copies this UTC budget and requires it for **every** required witness, without
percentile exemption. It introduces <=5-ms resource read brackets and <=50-ms RSS
start lateness alongside the one-second current-RSS schedule. The 5-ms ceiling
limits an observation's elapsed sweep and counter-endpoint uncertainty. The
reviewed declarations do not derive it from a bound on memory's rate of change,
RSS numerical error, OOM probability or the one-second research estimator.

These exact numbers are design choices. They are nevertheless binding acceptance
requirements in the frozen experiments. Changing the claim in a future contract
cannot turn any existing failure or unknown into a pass under the old contract.

## What the UTC bracket establishes

`CompletionWitnesses.application_return` takes a monotonic stamp, obtains and
formats UTC, then takes another monotonic stamp. The wall bracket includes Python
clock validation/ownership work and any intervening descheduling, not merely the
wall-clock call. Its measured width bounds the elapsed enclosure of this local
UTC observation. The callback runs immediately after library `recv()` returns;
the handoff before its first stamp is not independently bounded by this bracket.
It does not enclose the library's internal receipt, NIC arrival or exchange event.

A <=1-ms width does **not** prove UTC is within 1 ms of true UTC, permit subtraction
of clocks across hosts, or establish venue latency. Cross-site alignment needs
separate clock-offset/uncertainty evidence. Even a narrow interval can straddle a
one-second boundary. Bin eligibility needs an explicit interval/uncertainty and
boundary rule; using a formatted point or assuming midpoint error is insufficient.

Downstream dependencies:

- The frozen every-witness UTC gate, per-phase/per-case timing verdict and combined
  application verdict depend directly on the 1-ms ceiling.
- Any claim of uniformly <=1-ms local timestamp acquisition precision depends on
  it. Unambiguous UTC-bin allocation requires additional boundary/clock reasoning;
  passing this gate alone never established all such allocations.
- Ordered raw-byte retention, archive/hash linkage, successful covering fsync
  watermarks and finite completion do not require this numeric ceiling.
- Append/durable elapsed calculations use monotonic endpoints and preserve the
  wide UTC bracket's elapsed work. They remain separately interpretable when
  linkage/clock checks pass. Their start is the recorded observation stamp; do
  not extend their bound to unmeasured pre-stamp delivery or library-internal time.
  Do not discard wide-bracket rows to improve their full-population percentiles.

## What the RSS bracket establishes

`LinuxReader.read(rss=True)` brackets an entire transaction: cgroup path/identity
guards, two fresh ancestry/controller snapshots, two membership checks, per-actor
identity/status acquisition, CPU and memory counters and validation. Its 5-ms
ceiling bounds that whole sweep's elapsed time. It is not a bound on a single
VmRSS file read or on the numerical error of the returned sum.

VmRSS values from different processes are read sequentially. Even with stable
membership and a <=5-ms bracket, their sum is a bounded-time sweep, not proof of
an atomic simultaneous unit-RSS value. The existing current-VmRSS definition also
differs from cgroup memory accounting and lifetime/high-water measures. One-second
sampling misses inter-sample peaks at any bracket width. Under the existing
start-lateness and width limits the admitted sweep ends no later than 55 ms after
its target; that is not an exact integer-second snapshot.

Downstream dependencies:

- The claim that **every required slot** has an admissible, <=5-ms current-VmRSS
  observation below 80% of the memory limit requires every slot to pass. Wide
  sweeps remain retained observations but leave that gate unknown. Low values
  elsewhere and no observed OOM cannot fill missing admissible coverage.
- The resource and combined verdicts inherit these unknowns. Independent archive
  validity and UTC qualification do not depend on RSS bracket compliance.
- The same 5-ms requirement applies to the reads enclosing complete 60-s CPU
  windows. A bad endpoint can make its CPU window unknown; bad RSS slots elsewhere
  do not erase separately admissible windows. All nine original cohort CPU
  windows and the latest run's one complete window were admissible and passed.
- For monotone cumulative usage and valid identity/enclosure, conservatism of an
  enclosing CPU delta follows from boundary enclosure, not mathematically from
  the number 5 ms. The width controls temporal looseness and is still mandatory
  under the frozen gate. No interpolation, subtraction or CPU-gate change is
  proposed here.
- Continuous RSS peak, incremental observer overhead, physical memory safety and
  event-specific contention attribution were never established by these brackets.

## Essential guarantees versus implementation choices

| Essential to the intended evidence | Chosen implementation or scope |
| --- | --- |
| Explicit event/measurement boundaries and honest uncertainty, with monotonic order and clock-domain provenance | 1-ms UTC / 5-ms resource ceilings, and requiring every observation to satisfy them for a combined pass |
| Exact raw occurrence ordering, full denominators, immutable evidence and independent linkage | Formatting UTC text inside the critical bracket, Python callback structure and in-memory sideband representation |
| Explicit actor population, fresh measurements, identity/race rejection and declared RSS semantics | One large Python reader combining ancestry checks, RSS and CPU/memory counters in one transaction |
| Inclusive resource accounting and honest missed/unknown observations | Same-process Python observer thread, current sweep schedule and chosen resource headroom targets |
| Independent acceptance/eligibility rules stated before new evidence | Treating archive validity, timing precision and resource qualification as one all-required application result |

An implementation choice can be changed only prospectively. Moving checks outside
the bracket would change its meaning; switching to cgroup memory or a high-water
counter would change the measure. Neither is an equivalent repair of original RSS.

## Recommended prospective scope

Recommend a new, separately reviewed **component/descriptive evidence contract**,
not a relaxed pass for the existing experiment. Its proposed conclusions should be:

1. Exact ordered retention and verified completion for the declared finite
   synthetic localhost workloads, with original source/runtime/archive bindings.
2. Full-population monotonic append and successful-watermark elapsed bounds from
   their recorded observation boundary, with the existing budgets reported
   separately and every outlier retained.
3. UTC observations with their actual brackets and all precision failures; any
   eventual binned analysis must declare its clock assumptions and ambiguous-bin
   treatment before use. No assertion that every frame is UTC-bin eligible.
4. Inclusive CPU bounds for independently admissible complete windows, resource
   exits/counters and current-RSS sweep observations with complete slot coverage
   accounting. Do not assert every-slot qualified RSS compliance, a continuous
   peak bound, incremental-overhead acceptance or unobserved memory headroom.

Keep 1-ms/5-ms qualification labels and all original failures/unknowns visible;
do not exclude ineligible data from the raw or performance denominators. The new
claim's narrower coverage is a material scientific scope change that needs its
own prospective identity. It is **not adopted or executable by this review**.
No automatic public capture, research-window eligibility, sustained 3,000/s
capacity, reconstructed-book validity, cross-site causal lead/lag or trading
conclusion follows. Existing synthetic traffic is not a venue distribution.

If a named downstream question actually requires uniform local precision and
every-slot qualified resource coverage, preserve the original limits and pursue
a materially different acquisition architecture: a small bounded native
measurement path, deferred formatting/publication, and separately specified RSS
and counter transactions with enclosing membership/identity proof. Count all its
actors/work in the recorder budget. First define its event boundary, freshness,
race/closure and overflow semantics and equivalent or explicitly different
measures; changing a bracket's contents needs a new measurement identity. A
native helper or separate process alone is not evidence that wall scheduling
tails meet either ceiling. The full authoritative intervals must still pass.

There is currently no derived downstream need that justifies choosing that larger
redesign over the narrower claim. The latest quota optimization saves only about
0.060 ms inside the offline native-shaped validation path, versus native wide
reads of 6.532–19.520 ms; it supplies no basis for another run by itself.

## Historical outcomes and scope of this review

[Cohort02](RECORDER_COHORT_V2_RESULT_20261016.md): 360,000 ordered frames and
completion verified, nine wide UTC rows, 39 inadmissible RSS reads, overall fail.
[RssCpu01](RECORDER_RSS_CPU_VALIDATION_RESULT_20261016.md): 60,000 verified frames,
four wide UTC rows (7236/11693/12410/24142), eight inadmissible RSS reads, overall
fail. Both retain passing append/durability component observations; resource
qualification is incomplete. Continuous RSS peak and incremental observer cost
remain unknown. No verdict, threshold, evaluator, implementation, frozen source,
evidence or native authorization changed. This review used only local source and
retained documentation; no new test, benchmark, remote access or native run.
