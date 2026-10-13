# Finite absolute/select scheduling comparison — v1

Declared October 12, 2026, before any new native results. Offline preparation
only; native execution is not authorized. The machine-readable protocol is
`infra/stream/recorder_wait_comparison.py::PLAN`; its canonical payload hash is
`a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`.
Changes require a new experiment identity, retaining this declaration.
Execution-source and runtime freezing remain separate outstanding gates.

## Question and estimand

Does a single CLOCK_MONOTONIC/TIMER_ABSTIME clock_nanosleep request show less
inclusive target lateness than an explicit select.select([], [], [], timeout)
request in the same unchanged Linux runtime? The select reference is explicit:
Python 3.14 macOS time.sleep is not the old Linux Python 3.9 reference. This
compares implementations, not the exact installed time.sleep binary or an
exclusive cause of the previous failure. No causal claim about select slack,
rare tails, recorder acceptance, fills or profitability follows from this grid.

## Fixed population and ordering

Exactly two serial private clock-only runs, once each, with no concurrent workers:

| Run | First block | Second block | Targets | Final offset |
| --- | --- | --- | ---: | ---: |
| 0 | select | absolute | 12 | 133.3 seconds |
| 1 | absolute | select | 12 | 133.3 seconds |

Each block uses intervals 50 ms, 100 ms, 500 ms, 1 s, 5 s, 60 s in that order.
Use 16 adjacent integer monotonic_ns baseline pairs, then one epoch per run.
Every target is epoch plus cumulative integer nanoseconds; the second block
continues that epoch. No reset between blocks, per-target epoch, rounding through
floating point, adaptive delay, retries, catch-up, substituted rows or replay.
Each arm therefore has two observations at each interval. AB/BA balances block
position but does not randomize or remove host/time confounding.

The separate runs keep the existing 240-second per-unit ceiling; one combined
266.6-second series would exceed it. Run 1 starts only after run 0 has completed
and published, with a fresh baseline and epoch. Record the actual between-run gap;
add no tuned cooldown or unrelated work. Late/missed slots in run 0 still permit
run 1 if there was no fatal fault; keep every unknown in the comparison.

## Request and fault contract

Use the existing absolute adapter unchanged. For select, record monotonic_ns
immediately before the request and after return; compute positive remaining
nanoseconds from the fixed target and convert that duration to float seconds
only at the select interface. Retain the exact float integer ratio and its
signed conversion error. No automatic syscall retry wrapper may conceal EINTR;
any runtime retry behavior must be disclosed before execution. No time.sleep
fallback or native syscall substitution is permitted.

Retain run/block/arm/ordinal, interval, target, inclusive before/after bracket,
remaining duration, attempted flag, exact request representation, return/error,
signed lateness, zero retries and all unknown reasons. All errors have a
160-character maximum. Past/equal targets are unknown with no wait and the
remaining fixed slots continue. EINTR, other syscall/exception faults, early
return, invalid clock/return value or clock regression stop attempts in that run
and cancel run 1 if it has not started. Retain all remaining planned rows unknown;
baseline/epoch failures retain a failure receipt with targets explicitly
uninstantiated. Preserve partial artifacts and journals on timeout. Each wait is
bounded by 60 seconds; no busy spin or clock-baseline subtraction.

## Native gates and artifact envelope

Before measurement, independently verify Linux glibc LP64 aarch64/x86_64 ABI,
64-bit long/pointer, timespec size AND field offsets, CLOCK_MONOTONIC identity,
clock implementation/resolution and libc clock_nanosleep symbol/signature.
A mocked FFI test or successful local Mac suite is not native compatibility.
Any compatibility sleep needs its own finite declaration and authorization;
it is not implicitly permitted by this document.

Implement and offline-test the collector, select wrapper, lifecycle/partial
publication, bounded validator and independent evaluator before source freeze.
Freeze exact source inventory, declaration hash, Python/glibc/kernel versions,
select reference and dependency bytes in the native envelope. Independently
verify origin bytes and actual unit/PID/cgroup identity afterward. Hashes alone
prove content consistency, not native origin.

Use the existing private diagnostic limits per unit: CPU 75%, memory 512 MiB,
32 tasks, runtime 240 seconds. No external/loopback recorder workload or network
in the measurement worker. Preserve timer slack, Nice, affinity, clocksource,
instance, runtime and public collector configuration. Retain read-only before/
after timer-slack, cgroup/pressure context and public service/source/config
identity; missing context remains missing. Context snapshots are not continuous
contention observations. Do not install tracing or change controls.

At most 16 baseline pairs and 12 target rows per run; one result <=256 KiB per
run, plus a combined summary <=256 KiB. Validate size before exclusive publication
outside the timed series, and retain byte hashes. Context/journal collection
requires separately bounded launcher implementation before any execution.
No worker or launcher is added by this preparation.

## Predeclared analysis and stopping

Report all 24 planned cells, unknown counts by arm/interval, exact signed lateness
and descriptive minimum/median/maximum for observed cells. For each interval,
report absolute minus select lateness for each matching repeat (run index), and
the median of the two differences only if both pairs are complete. Report actual
requested duration too, since earlier lateness can shorten the next fixed wait.
Do not pool interval scales, exclude inconvenient unknowns, impute, fit tail
probabilities, estimate significance or choose a new threshold after measurement.
Missing either member makes that pair unknown; any missing pair makes the overall
comparison incomplete. Directional improvement is descriptive only and cannot
unlock the recorder cohort or revise the original 50-ms budget.

Stop after these two runs, or the first fatal fault/timeout. No preferred-result
replay. Native compatibility, performance acceptance and trading authority remain
false until their separate gates; this experiment has no acceptance threshold.

## Offline preparation

The declaration expander reads no clock, sleeps nowhere, binds no libc and exposes
no native runner. Tests cover both fixed orders, all integer targets, exact
133.3-second bounds, timestamp/index refusal, range overflow, declaration hashes,
copy isolation and false authority flags. Existing absolute-adapter fault tests
retain interrupted, early, missed and regressing-clock behavior. Collector fault
and evaluator tests remain outstanding because those components do not exist yet.

Verification on Intel macOS / Python 3.14.6: all 1,037 offline regression tests
passed in 92.808 seconds, including localhost fixtures. The initial restricted
sandbox attempt could not bind localhost sockets and was stopped; the complete
rerun with localhost permission passed. All 12 focused comparison/absolute-wait
tests passed, and the two new Python files passed Python 3.9 syntax parsing.
These results establish local offline behavior only; Linux/native validation
and actual scheduling improvement remain unverified. No frozen evidence changed.
