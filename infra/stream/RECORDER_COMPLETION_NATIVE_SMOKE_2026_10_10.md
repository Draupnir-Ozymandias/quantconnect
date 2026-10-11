# Recorder completion witnesses: native Linux smoke

## Result

Functional compatibility smoke passed on Ohio Linux ARM64 / Python 3.9.25,
using frozen source `e4b28b7d26fb2203984957f8b142b00ffbc00dae`.
All **53 prerequisite tests passed**. The finite injected transport retained
**68 messages** and **six successful data-file sync barriers**, with actual
native UTC/monotonic clocks, gzip/file I/O and file sync calls. Duplicate raw
messages remain distinct FIFO occurrences. Collection stopped at the frame
limit; this was not a complete public-market lifecycle.

The transport made no network connection. Two serial private systemd units used
75% CPU quota, 512 MiB memory, 32 tasks and a 120-second runtime limit. No public
collector source, environment, service state, resource limit or infrastructure
changed. No credentials, orders or QuantConnect sync were involved.

## Independent evidence audit

Corrected native stage:
`/var/lib/qcrl-stream/recorder-completion-fSyi2J2F`.
Local review:
`.qcrl/reviews/completion-native-smoke-20261010-3QiMDGqT`.

The offline audit verified all 13 originating files against the inventory anchored
through strict SSH, and six implementation-source hashes against the committed
snapshot. It independently checked archive/manifest/sideband linkage, raw input
population and ordering, duplicate preservation, clock enclosure, successful
covering watermarks, native unit properties and commands, and PID/timestamps
within the unit lifetime. Files were rechecked after verification.

Origin inventory SHA-256:
`1bf3dedc56b0bf06a84d9f1a11bee9fae81c98da6d7cdaf7764311ac60781321`.
Offline verification receipt SHA-256:
`831adaea012ebab4514de5af0f412e83a0f67f8a92f9c7af3834a227201c65a0`.

## Preserved pre-collection harness failure

The first smoke worker failed with `ModuleNotFoundError: execution_truth` before
collection because its script directory, rather than the staged checkout, was
on Python's import path. Its 53 prerequisite tests had passed. The failed stage
`/var/lib/qcrl-stream/recorder-completion-0E8qRMtb` was retained; seven originating
files were independently verified and no recording archive was present.

The corrected worker explicitly adds its working checkout to the import path.
It ran in a fresh stage, without reusing or replaying a recording or changing
the frozen implementation. Failed evidence remains under
`.qcrl/reviews/completion-native-smoke-20261010-JhNhr2F0`.

## Limitations and next gate

This establishes compatibility and tested linkage, not performance acceptance.
The injected transport and short recording do not represent public socket load,
burst behavior, sustained resource budgets, crash-tail recovery or replication.
The process-reported cgroup matches its unit name, but an independent live cgroup
binding was not observed. Post-collection sideband publication cannot recover an
unpersisted witness tail after a real process/host crash.

Application budgets were not evaluated; performance acceptance and order authority
remain false. Previous probe-cost rejections and frozen policies remain unchanged.
The next gate is a separately preregistered actual-recorder localhost
application-budget experiment, with frozen input, timing, resource observations
and explicit pass/fail/unknown handling—not another public capture or an automatic
deployment.
