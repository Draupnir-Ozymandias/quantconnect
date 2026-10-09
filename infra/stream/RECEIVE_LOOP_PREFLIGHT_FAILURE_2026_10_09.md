# Frozen cohort attempt — October 9, 2026

Outcome: **regression-test gate failed; all six measurement cases unstarted**.
No overhead result exists. No retries or parameter changes were performed.

Auditor and execution source frozen/pushed at
`5c8cfbb3813e71d23eaf47ed88c81453871b9923`.
Original preregistration remains
`39f4bfccec57910fec0adad1be3fdec16dd8a67d5f7d7f1abe04c7cd224739bb`.

Dedicated Ohio stage:
`/var/lib/qcrl-stream/receive-loop-overhead-fFRlFQpx`.
Exact Git bundle, original declaration and corpus file bytes were matched before
launch. The stage/source checkout was created by root. The restrictive parent
directory required root to enter it; execution used sudo without widening access.

The launcher ran the complete regression suite as qcrl under the original 75% CPU,
512 MiB, 32-task and 120-second limits. It completed **633 tests in 44.982 seconds**,
with one failure and one expected Python-version skip. The failing test was
`SyncContractTests.test_push_plan_excludes_markdown_and_preflights_source`.

## Cause confirmed

Source and `.git` are root:root, mode 755. Running read-only `git ls-files main.py`
as qcrl reports Git's **dubious ownership** guard. The QC upload-plan command then
prints zero eligible tracked files, so its regression assertion requiring main.py
fails. This is a private staging ownership mistake, not a strategy, Polymarket,
network or measured instrumentation failure. No QuantConnect API was contacted.

The correct future preparation is a **qcrl-owned dedicated checkout**, readable
by the root launcher. Do not weaken global Git trust, skip the regression test,
chown the public checkout, or mutate this claimed attempt. A proposed fresh
attempt must retain the frozen workload, thresholds, quotas and source checks.

## Failure evidence audit

Saved test unit Result=exit-code, ExecMainStatus=1; CPUQuotaPerSecUSec=750ms,
MemoryMax=536870912, TasksMax=32 and RuntimeMaxUSec=2min. Launch result contains
`completed=[]`, `measurement_complete=false`, no preservation errors and no
acceptance claim. No producer/consumer measurement unit was started.

Downloaded preserved evidence into fresh ignored local review:
`.qcrl/reviews/receive-loop-failed-launch-20261009-vM8Kpg/origin`.
Independently obtained originating inventory **file-byte SHA-256** over pinned SSH:
`01a85125ac3b253a1152ae5fdedfab8c777b189ac85519048392e653e921cac0`.

The independent verifier matched exactly all **seven originating evidence files**,
their populations/bytes, internal inventory hash and outer/inner launcher metadata.
The full auditor correctly rejected advancement because the cohort is incomplete.
The inventory anchor was re-read from Ohio afterward and remained unchanged.
All original remote evidence remains retained; no source/evidence deletion or replay.

Public configuration and commit stayed unchanged before/after and on final recheck:

- Public source: `4dd60ba168180243f8600860330dc1afc4816ff4`.
- Environment hash: `33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
- Daily timer active; stream pilot and observer inactive.

No public collector, infrastructure, quotas, credentials, trades or QuantConnect
synchronization changed. Next: obtain approval for a fresh correctly owned stage;
preserve this failed attempt and do not pool it into later measurement statistics.
