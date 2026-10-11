# Finite local worker-component diagnostic

Completed locally on macOS/Python 3.14.6, three rotated rounds of 14 lanes,
500 operations per batch. No cloud access, sockets, observer or paced cohort.
All 916 local regressions passed, including four new barrier/rotation/fault tests.

Review: `.qcrl/reviews/worker-components-20261010-97MSBMI3`.
Diagnostic hash: `2fc59f6d677be6456653661b95688e32c887e52fd6296ec24c8b797bf5f7088c`.
File hash: `53e03e73c0e16a6289594bf95216f14e221ebf96cd1ad896e8abe18198eb47af`.
Six exact source files were archived and independently checked against the saved
diagnostic's source hashes. The preservation receipt verifies both the outer
saved-artifact hash and inner diagnostic hash. An initial checker included the
outer persistence hash in the inner payload and refused it; the checker was
corrected to verify the two layers separately. No diagnostic was replayed.

## CPU microseconds per operation, ranges across three batches

| Operation | CPU µs |
| --- | ---: |
| Empty callback | 0.020–0.026 |
| Four native wall calls | 0.162–0.164 |
| Four wall calls with numeric validation | 0.346–0.388 |
| Seven wall calls with numeric validation | 0.552–0.676 |
| Native CPU pair acquisition | 0.382–0.460 |
| Packed CPU pair acquisition/storage | 1.022–1.058 |
| Deterministic JSON preparation | 1.580–1.622 |
| Native sleep(0) | 0.160–0.162 |
| Packed control, no-op sleep | 2.292–2.342 |
| Packed pacing, no-op sleep | 2.654–3.030 |
| Packed full, no-op sleep | 3.948–4.346 |
| Packed control, native sleep(0) | 2.444–2.796 |
| Packed pacing, native sleep(0) | 2.802–3.006 |
| Packed full, native sleep(0) | 4.078–4.224 |

Core batches preserve the original implementation, verified ordered raws and
CPU pairs. Construction and core materialization/verification are outside batch
timing. The `*_yield` labels mean a native zero-duration sleep call, not a proven
scheduler yield; its semantics and cost are platform-specific. There are no future
deadlines and therefore no fixed-rate pacing or realistic burst pressure.

## Interpretation and stopping point

Acquisition, storage, numeric validation and JSON preparation all consume CPU.
This helps identify investigation candidates; costs are not an additive causal
profile and cannot be extrapolated from Mac/Python 3.14 to Linux/Python 3.9.
In particular, approximately 4-µs local unpaced full steps do not explain the
Ohio experiment's 17–26-µs incremental aggregate CPU per event. No production
adapter or frozen threshold was changed, and no acceptance claim follows.

Recommended next work is the application-budget and prior-art review described
in `docs/MEASUREMENT_OVERHEAD_REVIEW.md`, not another automatic cloud run. Separate
useful research recording from detailed diagnostic coverage, choose absolute
budgets from decision tolerance, preserve the rejected strict probe contract,
and determine whether existing public ingestion/data tooling can reduce bespoke
work. A new recorder budget requires an explicit prospective specification.
