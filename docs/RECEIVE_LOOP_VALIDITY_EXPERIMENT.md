# Receive-loop validity experiment — design draft

Status: offline design only, not a preregistration, executable launcher or grant
of remote execution. The reference rejection and compact inconclusive verdict
remain intact. No existing workers, recorder, validators or evidence are edited.

## Question

Can we locate producer deadline misses and wide sampling brackets sufficiently
well to design a valid overhead comparison, without mistaking elapsed time for
CPU consumption or collector backpressure for scheduler causality?

The completed compact cohort already records producer begin, send-start and
send-end. Preparation-versus-send timing therefore does not require new probes.
Its missing boundary is between **previous send return and next producer begin**:
that includes list bookkeeping, pacing calculations, intentional sleep and any
interruption. Across six cases, the largest inter-begin gaps are 10.12–13.70 ms;
97.80–99.73% of each gap lies in this unresolved interval. Selected maxima are
descriptive, not representative estimates or causal evidence.

## Minimal new observations

| Unknown | Proposed observation | What remains unproven |
| --- | --- | --- |
| Pacing versus bookkeeping | Monotonic boundaries before pacing, before sleep and after sleep; requested sleep duration; retain existing preparation/send boundaries | Why sleep or bookkeeping took longer |
| Running versus not running | Same-thread CPU-time deltas alongside selected elapsed brackets, with both acquisition orders declared | Low CPU does not distinguish blocking, GIL wait, quota throttling or descheduling |
| Quota pressure | Separately bounded observer samples actual worker cgroup CPU counters, if supported, with read start/end, PID/boot/path binding and counter deltas | A counter increase inside a sample interval is not an event-specific cause |
| Host pressure | Bracketed host CPU counter samples, including steal if exposed | Host aggregates do not attribute a particular worker pause |

Do not claim a scheduler trace from aggregate counters. True runnable-versus-
blocked attribution would require a separate, explicitly reviewed scheduler
tracing design; it is outside this first minimal experiment. Missing cgroup
fields, permissions or platform support must remain unavailable, never zero.

## Observation-cost gate before a cohort

Build separate bounded diagnostic machinery and synthetic/fault tests first.
Preallocate event storage, refuse overflow and avoid synchronous disk writes
inside timing paths. Persist observations after collection. Declare every added
clock call, sampling rate, record/byte bound and observer resource quota.

Compare the proposed observer/probes against a no-added-probe diagnostic control
on numeric localhost. Separate schemas and stages are required; this is not a
replay of either completed cohort. Preserve both outcomes, including failures.
The observer itself can perturb the host and must be included in the cost review.
No silent sample filtering, dynamic sample rate, resource increase or stopping
public collectors to improve a result.

Before execution, freeze source/input inventories and a finite case order,
limits, missing-data handling and observation-cost acceptance policy. Do not
choose those limits from the experiment's results. This draft intentionally
does not invent an accepted cost threshold or authorize a launch.

## Verification requirements

- Unit tests: pacing arithmetic, exact interval partition, absolute deadlines,
  clock acquisition ordering, counter deltas/resets, bounds and unavailable data.
- Fault tests: oversleep, slow preparation/send, counter read failure, process
  exit/PID change, negative/reset counters and probe overflow. Known injected
  delays verify localization, not real scheduler causality.
- Linux smoke tests: native cgroup schema/path/permissions and same-thread clock
  semantics, independent of a real workload run.
- Offline analyzer: source/boot/PID/cgroup bindings, exact raw occurrences,
  interval conservation, explicit timing eligibility and unknown denominators;
  preserve original artifacts and audit their bytes before and after analysis.

Success would justify a separately preregistered validity experiment, not
acceptance of compact instrumentation or public deployment. Keep the original
1 ms clock and 100% eligibility gates unchanged for the completed cohort.

## Immediate next implementation

Implement and test a pure interval/counter model first, then a separate bounded
probe adapter. Only after reviewing the adapter's own cost and Linux behavior
should we freeze and approve a finite remote diagnostic run.

## Implemented offline model — October 10

Separate module: `infra.stream.receive_loop_validity`; tests:
`tests/test_receive_loop_validity.py`. Neither is imported by the frozen
recorder/workers. The module performs no clock sampling, file reads, socket
operations, thread creation or execution.

`ProducerSample` partitions bookkeeping, pacing calculation, sleep entry,
actual sleep, wake-to-begin, preparation and send. Absolute requested sleep
binds to its declared decision timestamp; negative sleep excess is preserved,
not clamped. All observations must be finite, ordered and interval-conserving.

`SampleBuffer` preallocates references to immutable samples, enforces contiguous
sequence/exact saved adjacent boundaries, and latches invalid-input/overflow
failure while preserving the valid prefix. Empty, failed or overflowed buffers
cannot report complete. Finish is single-use. Sample construction/validation
still has allocation and compute cost: this is **not** a proven low-cost adapter,
thread-safe buffer or measured hot-path implementation.

`CpuStamp` models the acquisition order monotonic-before, same-thread CPU,
monotonic-after. It returns elapsed bounds, not a CPU-utilization point estimate.
Thread changes and CPU resets are unavailable. `CounterSample` binds boot, PID,
process start identity and cgroup; missing fields remain `None`, and any counter
reset/read failure/identity change prevents a successful delta comparison.
Known zero is distinct from missing. Counter intervals do not prove that a
particular event was throttled. Native acquisition/parsing is not implemented.

**21 dedicated model/fault tests passed. All 730 local regression tests passed**
with socket access. The first sandboxed regression attempt was interrupted after
existing localhost fixtures failed to bind; this was not a completed test pass.
Python 3.9 syntax parsing passed, but **Linux runtime verification has not run**
for this new module. No remote capture, deployment, Git push or QC sync occurred.

Next: implement a separate bounded clock/pacing adapter and counter reader,
fault-test native-operation preservation and finish semantics, then Linux smoke
verification. A separately frozen observation-cost protocol must precede any
real diagnostic cohort.

## Isolated native adapter — October 10

Separate module `infra.stream.receive_loop_validity_probe` provides explicitly
constructed adapters; no collector imports, observer thread, CLI or launcher
is added. `PacingProbe` owns a **new synthetic producer algorithm**, not a
transparent patch of the frozen producer. It adds seven monotonic calls per
step (plus one initialization stamp), and records exact pacing/sleep/prepare/send
boundaries. The injected sleep/prepare/send callbacks run once each on success.
Native exceptions are re-raised unchanged; clock faults fail the diagnostic
step and prohibit retry. This adapter does not promise native continuation after
an observation failure. Overflow is refused before extra native operations.
It is single-thread-owned; immutable row construction and validation add cost.

`cpu_stamp` explicitly acquires thread identity, wall-before, thread CPU,
wall-after. This helper is separate and **not automatically inserted** into
the pacing step or original receiver clock sample. Its cost and placement need
a declared measurement protocol before integration.

`CounterReader` makes explicit, bounded cgroup-v2 reads without creating a
sampling loop. Maximum capacity is 1,024 attempts; each file read is bounded
to 4,096 bytes. It checks boot/PID/start-time/cgroup identity before and after
the counter read, refuses counter paths outside the declared mount or through
symlinks, and retains failed attempts as unknown. Supported CPU counters are
usage, periods, throttled periods and throttled microseconds; absent fields
remain absent. Counters describe the **whole cgroup**, not just the named PID.
Only a separately verified dedicated worker cgroup can bind those aggregates
to a worker experiment. Other cgroup layouts are unavailable, not guessed.

Successful reading does not mean every counter exists or that a counter delta
explains a particular pause. PID reuse between identity checks, process/thread
lifecycle and file-reading races cannot be ruled out universally by this
adapter. No host CPU/steal reader or scheduler trace has been implemented.

Probe tests cover native return/exception identity, no retries, every clock
boundary fault, nonfinite/regressed clocks, cross-thread use, adjacent interval
continuity, overflow/finish, exact CPU acquisition order, proc names containing
parentheses, missing/malformed/duplicate counters, permission failures,
identity change, symlinks and input byte limits. The fixtures use temporary
files; they do not establish real Linux proc/cgroup behavior or observation cost.

Next gate remains fresh isolated Linux smoke verification and an independently
reviewed probe-cost protocol. No probe was attached to a deployed collector,
and no real workload cohort, remote deployment, Git push or QC sync occurred.

Final verification: **14 dedicated adapter tests and all 744 local regression
tests passed**. Python 3.9 syntax parsing passed; native Linux smoke verification
and measured probe-cost acceptance remain outstanding.

## Native Linux smoke completed — October 10

Fresh isolated directory on Ohio: `/tmp/qcrl-validity-smoke-9jusbRI8`.
The frozen repository archive and the separate candidate files were copied
there; no deployed checkout or configuration was edited. **35 model/probe
tests passed** on Linux aarch64 / Python 3.9.25.

The explicitly gated `infra.stream.receive_loop_validity_smoke --execute` ran
three synthetic paced callback steps (no socket), acquired same-thread CPU
brackets and two native cgroup-v2 CPU samples, and checked completion/identity.
All three tested module hashes matched local source. Smoke receipt is retained
at `.qcrl/reviews/validity-linux-smoke-20261010-FNG5Z8JS/smoke.json`, with verified
payload SHA-256 `9022503d0d1cb6493f8aa2ab3f23821dcea753cb6d8d7387a27f6a9753544f97`.

Counter scope was `/user.slice/user-1000.slice/session-520.scope`, the SSH
session cgroup, **not a dedicated worker unit**. Its 968-usec usage delta and
zero throttling deltas verify parsing/acquisition, not worker cost, absence of
host pressure or behavior under the future 75% consumer quota. The three-step
smoke has no overhead-control lane; no acceptance ratio follows.

Public checkout stayed `4dd60ba168180243f8600860330dc1afc4816ff4`; environment
hash stayed `33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily timer remained active, pilot/observer services inactive. No instance,
collector, resource or timer changes occurred. Temporary smoke source and
local receipts are retained, not installed or deployed.

Two additional local smoke tests verify explicit-execution and Linux barriers
before counter-reader construction. The remaining substantive gate is a frozen
finite **probe-cost comparison** with independent unit/resource and occurrence
verification. Native smoke success does not authorize that comparison by itself.

After adding the smoke entry point/barrier tests, **all 746 local regression
tests passed**. Changes remain local and uncommitted; no GitHub or QC sync.

## Probe-cost declaration prepared — October 10

The separate [v1 cost protocol](RECEIVE_LOOP_VALIDITY_COST.md) fixes nine cases,
three lanes, resources, observation bounds and prospective acceptance budgets.
`infra.stream.receive_loop_validity_cost` declares/validates source and policy
bytes, without workers, launcher or execution authority. Five tamper/determinism
tests passed; **all 751 local regression tests passed**.

Exclusive declaration:
`.qcrl/reviews/validity-cost-prereg-20261010-IQv1fA4D/preregistration.json`.
Plan SHA-256:
`590e270d3766437712cdfbff588278287f1126bb442f0e8959c350e5f7b04235`.
All 11 source files retained in sibling `source-snapshot.tar` independently
matched the declaration. Source bytes are preserved, but a **Git commit/source
freeze is still pending**. No new remote work occurred in this declaration step.

Next: commit/source-freeze, then build the separate finite workers, observer,
launcher and auditor with input/source receipts. These are not yet implemented;
their existence, Linux verification and explicit run approval must precede any
real probe-cost cohort. A declaration is not an executable campaign.
