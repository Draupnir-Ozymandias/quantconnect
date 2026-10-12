# Offline counter wake and scheduling diagnostics

This is a descriptive offline lane, not a scheduler repair, deployment, new
capture, performance acceptance or retrospective change to a frozen experiment.
`infra/stream/recorder_counter_diagnostics.py::describe` reads the hashed v1
schedule and endpoints. It refuses changed policy, endpoint hashes, endpoint
population or authority flags, and does not mutate the input. It performs no
clock reads, sleeps, filesystem access, networking or native execution.

## October 12 native evidence

The frozen smoke source was `41904e5ad8959116cf6b930248769bd7b2114dc6`.
Its independently verified origin inventory hash was
`b55db75ec8e08db4ba6b2aae489ee4767e48dfc202e5e020097aeaf84e10e604`.
The source schedule hash is
`01032543cd60ef32429187221d9035ff43e07e5ec87376ae1e711911c6656f52`.
The retained local review is
`.qcrl/reviews/counter-native-smoke-20261012-YWdUTQYU/`.

| Quantity | First endpoint | Final endpoint |
| --- | ---: | ---: |
| Wake relative to target | +4.991236 ms | +57.973565 ms |
| Excess over fixed 50-ms lateness ceiling | 0 ms | 7.973565 ms |
| Wake to guard start | 0.027988 ms | Not read |
| Pre-read guard envelope | 2.496326 ms | Not read |
| Narrow counter bracket | 0.009558 ms | Not read |
| Post-read guard envelope | 1.905086 ms | Not read |
| Total guard/read envelope | 4.410970 ms | Not read |
| Counter enclosure margin | 42.474892 ms before boundary | Unknown |

The final endpoint was refused **before** any counter or guard read. Therefore
its missed wake deadline was not caused by that endpoint's counter-read cost.
This does not rule out earlier work, scheduling contention or other influences.
The data does not identify the cause of the wake lateness. The narrow first read
does not prove a complete CPU window or repeated-descriptor freshness.

## Limits of the existing evidence

Wake lateness is `wake - fixed_target`, not a measured `time.sleep` overshoot.
The v1 record omits the immediate pre-sleep timestamp, actual requested sleep
duration and immediate sleep-return timestamp. Its single wake read also cannot
separate timer expiry, runnable-to-running delay and interpreter resumption.
Neither kernel timer slack, CPU-credit exhaustion, GIL effects nor a specific
clock/host fault can be inferred from this one failure. Those quantities were
not isolated or measured here. Origin verification comes from the separate
native audit, not from this pure analyzer or its content hashes alone.

## Deterministic coverage

Injected clocks reproduce the observed two-wake shape as a fixture (not native
evidence), distinguish wake lateness from guard/read cost, and exercise final
wakes just inside/outside the fixed ceiling and early returns. The existing
schedule tests also cover missed readiness, missed slots, clock regression,
probe exceptions, slow reads, reset counters and guarded reads crossing a fixed
boundary despite an on-time wake. No retry, catch-up, adjusted epoch or policy
relaxation is introduced. These fixtures do not model actual kernel scheduling.

## Recommended next gate

Preregister a separate finite, clock-only native diagnostic before executing it.
Keep the completed smoke and six-case cohort unchanged. Prospectively retain
each fixed target, clock before the sleep request, requested duration, clock
immediately after return, and a bounded clock-call baseline. Record runtime,
clock implementation/resolution, read-only timer-slack and clocksource context,
unit limits and contemporaneous host resource context when available. Declare
the interval grid, number of observations, artifact bounds, deadline-miss
handling and single-run stopping rule before looking at results.

Even that diagnostic should report wake distributions and missing observations,
not promise to distinguish kernel expiry from run-queue delay without additional
tracing. Do not install instrumentation, change timer slack/priority/resources,
or launch it under this offline authorization. Choose any scheduling change only
after reviewing separately frozen evidence; do not rescue prior results by
increasing the existing 50-ms allowance.

## Offline verification

The established Python 3.14.6 / websockets 15.0.1 environment passed 1,003
regression tests in 42.500 seconds. After adding one further injected sleep-error
case, all 29 focused counter, scheduler and timing-diagnostic tests passed.
Python 3.9 syntax parsing passed for the new files; this is not a Linux runtime
verification of the new analyzer. The initial default-interpreter suite attempt
lacked websockets; the successful regression run used the existing
`.qcrl/receive-path-venv` environment with localhost-test permission.
