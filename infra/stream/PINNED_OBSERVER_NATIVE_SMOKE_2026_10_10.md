# Integrated pinned-observer native smoke — October 10

**Passed the native integration correctness gate; not combined-cost acceptance.**
Source was frozen locally at `5578508d6a5183cfaba87259071607be33db5008` and
cloned into fresh Ohio stage `/var/lib/qcrl-stream/receive-loop-pinned-4SNPZows`.
No GitHub push, cost cohort or deployed collector update occurred.

29 native Linux component/lifecycle tests passed. One full-lane eight-message
fixture used two dedicated qcrl worker/observer units, with unchanged 100%/25%
CPU quotas, 512 MiB, 32 tasks, 120 seconds and security properties. Both live
PID/boot/cgroup receipts were sealed before collection. Both units exited
successfully; only those private units were stopped.

Independent offline verification matched exact population/bytes for 24
originating artifact, driver and result files and checked 41 source hashes. It
verified eight ordered raw occurrences, packed-wrapper/canonical-core linkage,
CPU pairs, native required counters, actual unit commands/security/quotas,
distinct PIDs, live cgroup bindings, acquisition ordering and unit CPU-window
enclosure. The pinned reader closed before the observer CPU window ended;
the cleanup artifact was persisted afterward and linked by the acknowledgment.
The final observer core carried the same cleanup payload. No cleanup errors or
remaining owned handles were reported by the source-bound implementation.

The inventory byte SHA-256, independently obtained from Ohio, is
`344ea82584a85492e78c0910bc270473894081a35cf90303acb2ae14d1f7bd2a`.
Original evidence, source Git bundle, driver and independent receipt/verifier
are preserved under `.qcrl/reviews/pinned-observer-smoke-20261010-cNbZiEWn/`.
The independent receipt is `offline-verification.json`. Origin bytes were
checked before and after analysis; no evidence was rewritten or replayed.

Public checkout/configuration/service states matched before and after: checkout
`4dd60ba168180243f8600860330dc1afc4816ff4`, environment hash
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`,
daily timer active and stream pilot/observer inactive. No infrastructure change,
trades, credentials or QuantConnect synchronization occurred.

## Next gate

Declare a separate combined-cost experiment for the packed worker plus pinned
observer. Explicitly retain first-pin acquisition cost and descriptor cleanup
inside the observer CPU window, with snapshot persistence outside. Keep cadence,
per-step CPU coverage, rotations, quotas and acceptance thresholds unchanged.
Source-freeze a dedicated production trial/launcher/auditor before any separately
authorized finite cohort. The component speedup and this tiny correctness smoke
do not replace the unchanged combined CPU/RSS/tail gates. Real PID reuse remains
unforced, and the existing rejected cohorts remain immutable.
