# Finite Ohio wake diagnostic — audited, incomplete

On October 12 the single clock-only run used source
`1e44033591e9231c293e047919e9c41d2195471a` and unchanged plan
`a1a96146eb5b518a5717f3ed44f90c4f895ecfad41955966fdfc89fb115a951e`.
Linux tests ran 1,019 successfully (one skipped). Independent source/runtime,
native unit/PID/cgroup, byte-inventory, fixed-target arithmetic and contextual
chronology checks passed.

All 12 rows were retained: 11 observed and one already-missed 50-ms target. The
miss followed a 59.21-ms-late 60-second wake. The second 60-second wake was
60.05 ms late. No target was retried, caught up or shifted. The worker/launcher
failed closed; measurement completeness and performance acceptance remain false.

Both cycles showed approximately timeout-proportional lateness: about 1 ms for
1 second, 5 ms for 5 seconds and 59–60 ms for 60 seconds. A post-hoc hypothesis
is the combination of upstream Python 3.9's POSIX select-based sleep and upstream
Linux's timeout-relative select slack. The latter can allow 0.1% of timeout,
capped at 100 ms, for the ordinary nice case. It does not make 50-us process
timer slack a 50-us upper bound. This is an inference from sources and the
measurements, not proof about the exact distribution-patched runtime or an
exclusive causal explanation. [CPython 3.9.25 source](https://github.com/python/cpython/blob/v3.9.25/Modules/timemodule.c),
[Linux 6.18 source](https://github.com/torvalds/linux/blob/v6.18/fs/select.c).

The native process recorded 50,000-ns timer slack, Nice=0 unit context and
`arch_sys_counter`; kernel release was `6.18.51-120.163.amzn2023.aarch64`.
Endpoint pressure snapshots are not a continuous contention trace. There was
no installed-binary syscall trace, exact kernel-source audit or credit-balance
measurement. Do not fit tail probabilities to this 11-observation mixed grid.

Evidence and independent report are retained under
`.qcrl/reviews/wake-native-20261012-pXnHwCVg/`, with remote evidence at
`/var/lib/qcrl-stream/recorder-wake-JSjERVov`.
The externally rechecked origin seal SHA-256 is
`635450857aec739725077073aeabfda761f27d96c4952b144bf980b42030b48f`;
original inventory SHA-256 is
`7a594c51bd9bb86dfc28569b856bbd2f4d8c434c4a3d13da6d38e045db05fc1d`.
Local/origin archive SHA-256 matched. The full ignored report discloses the
pre-measurement helper invocation failure and an independent-auditor schema
correction; neither changed measured evidence nor replayed the run.

Public source/configuration/checked services and all resource/timing limits
remained unchanged. No trades, credentials, new infrastructure, GitHub push or
QuantConnect sync. The failed private unit record and evidence remain retained.

Recommended next step: offline absolute-monotonic wait adapter and fault tests,
then a separately declared implementation comparison if warranted. Do not
upgrade the runtime, change timer slack or repair earlier verdicts retrospectively.
