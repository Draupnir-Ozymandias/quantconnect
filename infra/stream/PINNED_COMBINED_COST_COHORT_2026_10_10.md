# Combined pinned-observer cost cohort: verified rejection

The frozen nine-case experiment completed and its independent audit returned
**reject**: 17 known gate failures, no inconclusive reasons. Evidence integrity
passed. No threshold, workload, cadence or resource limit was changed or tuned.

## Provenance

Source: `c8ee27ef3b499a14b355ac3fc6037a7a7d12457d`.
Plan: `9787ab2826359ecb96b30cdedb7972d1125dab3b8cd29b97ef4e1b7dd5aa4388`.
Ohio stage: `/var/lib/qcrl-stream/receive-loop-pinnedcost-dZSVtvYL`.
Local review: `.qcrl/reviews/pinned-combined-cost-cohort-20261010-uMV2rhVh`.
Independent origin inventory byte anchor:
`5d41c08996ba349652e7199ee316a237cf664a9464cbf8158819bd15e373c785`.
Audit: `114cf478b0e649258edd3980d6986a7c15399f256efc9ba7cd3de7f4dd6fb48b`.

The Linux prerequisite suite ran 912 tests in 93.261 seconds, OK with one skip,
inside its 75%-CPU/512-MiB/32-task/120-second private unit. Nine real cases
completed in the declared order, totaling 270,000 ordered raw occurrences.
The audit checked 188 originating files before and after analysis, 19 distinct
unit PIDs, actual commands/limits/security, boot/cgroup/identity and live binding
links, native counter/CPU windows, packed rows and cleanup/ACK/core linkage.
All 40 combined source hashes matched the preserved committed snapshot; saved
preregistration bytes matched the earlier freeze. Offline receipts and immutable
origin files remain in the review directory.

## Paired results

Ratios compare combined worker plus observer cost to the same round's control.
CPU limit remains 1.05; sampled lifetime-high-water RSS limit remains 1.10.

| Round | Pacing CPU | Full CPU | Pacing RSS | Full RSS |
| --- | ---: | ---: | ---: | ---: |
| 0 | 1.0754 | 1.2747 | 1.0137 | 1.0427 |
| 1 | 1.1503 | 1.4584 | 1.0118 | 1.0403 |
| 2 | 1.0653 | 1.3285 | 1.0132 | 1.0422 |

All six CPU comparisons fail; all six RSS comparisons pass. Ten individual
phase-window latency comparisons fail the unchanged added-p99 <=1 ms / added-worst
<=5 ms gates. One full round-1 inline CPU stamp has a 2.163-ms wall bracket,
exceeding the 1-ms limit. No missing required evidence makes this inconclusive.

Full observer timed CPU is 0.1683/0.1710/0.1702 seconds. Full worker timed CPU
is 2.2557/2.3208/2.3625 seconds. The observer values are lower than the prior
original-reader cohort's approximately 0.225–0.228 seconds, but those are separate
cohorts, not a contemporaneous causal A/B estimate. The component improvement
does not rescue the unchanged combined acceptance gates. Pacing failures also
show that the pinned reader alone cannot explain this run's rejection.

## Boundaries and next step

Public checkout, environment hash and service states remained unchanged. Only
private units were retired, after evidence capture. No replay, public stream
capture, exchange credential use, infrastructure change, QuantConnect sync or
trade occurred. Source and evidence remain retained on Ohio and locally.

Do not promote this adapter to an accepted recorder probe, relax the thresholds,
or repeat until a lucky pass. Next: a finite offline worker-side operation-cost
diagnostic, separating fixed CPU-stamp, pacing and validation costs while keeping
the rejected evidence immutable. Any resulting intervention needs its own source
freeze and declared experiment; hardware scaling is not established as the remedy.
