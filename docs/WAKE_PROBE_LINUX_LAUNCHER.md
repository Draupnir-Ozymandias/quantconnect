# Isolated Linux clock-only diagnostic launcher

Implementation only: not deployed and no native run performed. The immutable
measurement design remains in `WAKE_PROBE_PREREGISTRATION.md`; its plan hash is
unchanged. This launcher does not authorize an experiment replay or a public
collector change.

`infra.stream.recorder_wake_launch` requires explicit `--execute`, Linux root,
the fixed `/opt/qcrl-stream/venv/bin/python`, and a new canonical stage matching
`/var/lib/qcrl-stream/recorder-wake-[A-Za-z0-9]+`. Run it from that stage's clean,
qcrl-owned `source` checkout. The qcrl-readable `execution-freeze.json` must be a
regular, hash-checked artifact matching the exact Git commit, tracked source
inventory, runtime and plan. Generate it using `freeze(commit)` and the existing
exclusive `publish` helper after source-freezing. Never reuse evidence or units.
There must be over four GiB free. These requirements are checked before launch.

The launcher claims the stage exclusively, creates private qcrl evidence, and
starts a test unit followed serially by one clock probe. Both have the fixed
75% CPU / 512 MiB / 32-task / 240-second bounds, no-new-privileges, read-only
source and protected home/system. Collector environment files are inaccessible.
The test unit permits numeric localhost for existing socket fixtures; the probe
permits no IP network and only AF_UNIX sockets. No recorder/cohort is started.

The worker publishes identity/context readiness and waits at most 15 seconds.
The launcher independently binds its running unit/PID/cgroup using the existing
Linux reader, then publishes a hash-linked release. Measurement chooses its
epoch only after release; context reads and artifact writes are outside the
timing series. Missing timer-slack/clocksource/pressure reads remain explicit
unknowns. Required resource/identity failures refuse measurement. Final context,
result hashes and readiness/release links are retained. The worker checks source,
runtime and plan against the freeze before measurement.

Worker control/result publication is exclusive, durable and capped at 256 KiB
including the actual JSON formatting and artifact hash. A SIGTERM during the
timing series is treated as a probe fault, retaining unknown remaining rows if
the process has time to publish; SIGKILL, host loss or a failure before that
handler is installed may leave only readiness/context/journals. Partial evidence
must not be represented as a completed timing series.

Unit journals/properties are captured before private cleanup. Failure handling
is confined to the fresh private prefix; no public timer/service is stopped,
restarted, reset or restored. Source/runtime/public state are checked again,
and drift fails closed rather than being automatically repaired. An exact file
inventory seals retained originating evidence. Stage claims and all artifacts
remain available on failure, with no retries or deletions.

An exit-success and `complete` launch result are mechanics checks only. Native
origin verification and performance acceptance remain false pending independent
audit of bytes, unit restrictions/lifetime, live binding, source/runtime and the
full fixed population. No new timing threshold is selected by this launcher.

Next gate: source-freeze, then independently verify the private native envelope
before a separately authorized single finite Ohio execution. Do not substitute
this implementation for the prior failed counter smoke or six-case cohort.

Offline verification: 1,018 regression tests passed in 43.558 seconds in the
established Python 3.14.6 / websockets 15.0.1 environment. After adding one further
existing-evidence preflight case, all 44 focused counter/scheduler/wake/launcher
tests passed. Python 3.9 syntax parsing passed for the launcher, worker and tests;
actual Linux runtime and effective systemd restrictions remain unverified.
The plan hash remains
`a1a96146eb5b518a5717f3ed44f90c4f895ecfad41955966fdfc89fb115a951e`.
