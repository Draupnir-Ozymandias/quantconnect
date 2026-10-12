# Finite clock-only wake diagnostic — prospective v1 plan

Status: offline-tested prototype; **not deployed or run natively**. This document
declares the measurement design, not permission to change public collectors,
infrastructure, trading credentials, unit limits or previous verdicts. Native
execution requires a frozen source inventory and a separately verified private
launcher. No launcher or CLI is introduced in this revision.

Plan SHA-256:
`a1a96146eb5b518a5717f3ed44f90c4f895ecfad41955966fdfc89fb115a951e`.
The hash covers `PLAN` in `infra/stream/recorder_wake_probe.py`; source files must
also be frozen before execution. Merely reproducing a plan hash is not proof of
native origin or source identity.

## Question and design

Can immediate clock observations around a finite series of relative sleep
requests describe where a fixed-target wake misses its deadline? This is idle,
clock-only instrumentation, not a CPU-counter or recorder performance test.

Measure 16 adjacent monotonic-clock pairs as an inclusive clock-call baseline.
Then choose one monotonic epoch. The interval grid is 50 ms, 100 ms, 500 ms,
1 second, 5 seconds and 60 seconds, in that order, repeated twice. These span
short and long waits and include the original window duration; they are not a
search for a passing scheduling configuration. All 12 targets are cumulative
offsets from the single epoch, ending at 133.3 seconds. Do not shift the epoch,
adapt the grid, reschedule skipped slots or replay the run after inspecting it.

For each target retain the pre-request clock, requested duration, immediate
return clock, signed target lateness, request-to-return duration and the excess
of that observed duration over the requested sleep. This last quantity includes
clock-call and interpreter overhead: **it does not isolate kernel sleep
overshoot**. The probe records values above the old 50-ms ceiling rather than
using that ceiling as a success gate. The old scheduler policy is unchanged.

Already-missed targets are recorded unknown without sleeping/catching up. Early
returns are recorded unknown without retry. Sleep or clock faults stop further
attempts; all remaining declared rows are retained unknown. Baseline/epoch faults
abort before target measurement. No successful rows are substituted for failures.

## Prospective native envelope

One private Ohio Linux diagnostic run, with the existing fixed diagnostic unit
limits: 75% CPU, 512 MiB memory, 32 tasks and a 240-second runtime ceiling.
Retain the effective unit properties, process/cgroup identity and source/runtime
inventory. No network or public recorder workload. Record public collector
source/configuration/service state before and after without changing it.

Before/after contextual snapshots should retain runtime and monotonic clock
implementation/resolution, the probe process's read-only timer-slack setting,
kernel clocksource, effective cgroup quota/statistics and available host pressure
context. Missing context remains explicitly missing. Do not change timer slack,
clocksource, affinity, priority, CPU mode, instance size or resource limits.
No tracing installation is authorized by this plan.

Artifact bound: 16 baseline pairs, 12 target rows, bounded error strings and one
result object capped at 256 KiB before publication. Publication should be outside
the timing series, exclusive and byte-hashed. Retain partial evidence and unit
journals on timeout/failure. These publication/context requirements belong to the
future native launcher, not the offline injected-clock prototype.

## Analysis and stopping rule

Report every target and unknown row, signed wake/request-excess values and their
finite-sample minimum/median/maximum; do not fit a distribution, estimate rare
tail probabilities from 12 observations or select new thresholds from results.
Baseline durations are descriptive; never subtract them to repair lateness.
Verify originating bytes and native identity independently before describing
any result as native. This pure prototype always marks native verification,
performance acceptance, kernel-overshoot isolation and trading authority false.

Stop after the one declared run or its first fatal failure/timeout. Do not replay
to obtain a preferred result. Findings may motivate a new declared experiment;
they cannot rescue the failed CPU-window smoke or the prior six-case cohort.

## Offline validation

Injected-clock tests cover fixed targets/population, the 57.973565-ms late-wake
fixture, early returns, already-missed targets, sleep exceptions, regressing and
nonfinite clocks, explicit execution gating, result hashes and authority flags.
They establish control-flow behavior, not actual Linux scheduling behavior.

The complete offline regression suite passed 1,011 tests in 41.571 seconds in
the established Python 3.14.6 / websockets 15.0.1 environment. The focused
counter/scheduler/diagnostic/wake suites passed 36 tests. Python 3.9 syntax
parsing passed for the new probe and tests; native runtime behavior remains
unverified. Original collector, scheduler and scientific budget files were not
modified.
