# Pinned-reader native smoke — October 10, 2026

**Passed the tested live-acquisition gate, not a performance gate.**
Local source freeze `9c1c02987ade3096cc02fc8ad98e2037fdf8b560` was cloned into
fresh private Ohio stage `/var/lib/qcrl-stream/receive-loop-pinned-IyR5ANXO`.
No GitHub push, public checkout change or real cost cohort occurred.

24 native Linux tests passed. One dedicated qcrl unit used the unchanged
100% CPU, 512 MiB, 32-task, 120-second sandbox limits. A live PID/boot/cgroup
receipt was sealed before releasing the finite acquisition smoke.

The reader successfully acquired two live /proc/cgroup-v2 samples through pinned
descriptors. All required counters were present; usage increased after bounded
CPU work and interval/identity validation passed. Successful finish closed the
saved descriptors, checked before any descriptor reuse. An owned disposable
child process was sampled while alive, terminated and reaped, then rejected on
the next acquisition despite pinned handles. Its failure could not become a
complete reader report. No collector process was stopped or reconfigured.

Independent offline verification matched exact bytes/population for eight
originating artifact/script/result files, checked eight source hashes against
the freeze, and verified actual unit identity, command, working directory,
limits/security, live binding and acquisition lifetime enclosure. The originating
inventory byte SHA-256, obtained directly from Ohio, is
`2735e351083332e4495d0a80b9ff49d2e3461222d867a82d087e7ad3fbc1d52f`.
Receipts, original evidence, source Git bundle and verifier are retained under
`.qcrl/reviews/pinned-native-smoke-20261010-NdNXEQ8z/`.

Before/after public state matched: checkout
`4dd60ba168180243f8600860330dc1afc4816ff4`, environment hash
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`,
daily timer active and stream pilot/observer inactive. Only the owned child and
private smoke unit were stopped. No infrastructure change, trade, credentials,
QuantConnect sync, replay or threshold adjustment occurred.

## Limits and next work

This establishes fresh live reads, process-exit refusal and cleanup in this
Linux setup. It does not exercise real PID reuse, cgroup migration/deletion,
all Linux file-replacement races, or performance under the declared workload.
Fixture tests for those modeled identity/path changes are not equivalent to
native verification. The prototype's acceptance flags remain false.

Next: additional isolated lifecycle faults, followed by a separately source-bound
original-versus-pinned reader comparison. Do not integrate into the cost cohort
merely because this correctness smoke passed; the repeated path/fstat checks
may offset the avoided open/close calls. Public rollout remains unauthorized.
