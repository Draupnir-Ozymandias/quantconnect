# Compact candidate workers

Separate module: `infra.stream.receive_loop_compact_trial`. The original
reference worker, launcher and audit are unchanged. This worker validates the
compact preregistration and a new implementation receipt binding worker,
launcher, auditor, tests and documentation bytes. Original policy flags stay
offline; the separate receipt records implemented machinery, not execution
authority or performance acceptance.

Producer uses the same frozen corpus, absolute pacing, synthetic PONG schedule
and fixed six-case pair order. Baseline remains ObservedSocket; instrumented
uses the frozen CompactDiagnosticSocket. The thin transport boundary translates
native disconnects, not idle timeouts. Both keep single-pass durability and
scoped v3 cap128. A worker claims its case exclusively before connect; failure
never grants replay. Worker CLI producer/consumer requires explicit --execute.

Timed window remains before connect through recorder return, close and receiver
join. Raw deliveries are persisted outside it BEFORE sideband snapshot; snapshot
failure cannot discard them. Measurement and explicit failure receipts preserve
partial evidence. Verification refuses any worker with a failure receipt.
Candidate measurement schema is distinct from the rejected reference schema.

Offline verification independently replays archive integrity, exact raw
occurrences, physical single-pass encoding, delivery-window and producer order,
v3 recovery, compact dispatch/clock linkage and sampled RSS. The unchanged pure
pairwise gates never establish origin/resource acceptance on their own.

Roles are stage, produce, consume, verify and evaluate. Stage is exclusive and
does not execute; evaluate verifies all six cases without reading cached audits.
It remains inconclusive until the independent origin/resource audit succeeds.
Tiny localhost test workloads are explicitly test-only overrides; they are not
accepted cohorts and do not establish overhead acceptance.
