# RssCpu01 result — October 16, 2026

**Diagnostic useful; application acceptance failed. Stop after this attempt.** The one approved mixed case completed and the frozen independent audit returned complete=true, verdict=fail, application_budget_pass=false. Auxiliary coverage is complete: 73 linked RSS CPU/wall observations, no CPU clock/linkage unknown or CPU-greater-than-wall anomaly. Eight wide RSS brackets have paired thread CPU values. No threshold was changed and no CPU time was subtracted.

## Exact attempt and readiness

- Candidate `eb13a5136ae5a4f88a2987706cf46a5d874f2054`, 528 selected source files. Freeze `babeecedfe2ac3f4d3f2c86cd2d952f8f28745feeff5f48f03511c2e3ff5caee`.
- One controller PID 1588005, submitted 15:36:48.252682 UTC. Plan `455cf599c150eb08cab9840103a3a114900dc0524289c82d700c67b215379e96`; RSS CPU policy `6eb2509c03a390c53d3fdc31124177403638d700e1e4922ee8ce015e7cf81ee5`.
- Stage `/var/lib/qcrl-stream/recorder-persistence-20261016LupusRssCpu01`; one `mixed-0` pair, 60,000 unchanged ordered synthetic frames: 5,000 / 30,000 / 25,000 at 500/s / 3,000/s / 500/s. Every phase attained 100% of its declared send starts.
- Installed Linux/aarch64 Python 3.9.25 readiness: **1,194 total, 1,193 pass plus one declared skip, 204.935 s**. Whole unit lifetime 206.290835 s, CPU 144.470556 s, PID 1588038, MemoryMax 1 GiB, RuntimeMax 240 s. This is distinct from the Mac offline tests in the preparation packet.
- Exactly three successful units, exit status 0. Producer PID 1591112: CPU 28.557019 s / lifetime 122.261630 s. Recorder PID 1591121: CPU 20.699270 s / lifetime 93.158354 s. Both retain MemoryMax 512 MiB, CPU 75%, TasksMax 32, RuntimeMax 240 s and original isolation.
- Complete archive order/bytes/footer/gaps, per-occurrence completion, verified recorder completion plus producer closure, actual command/PID/unit/limits/chronology and all original component gates audited. No extra case, replay, replacement, tuning, resource change, public capture or six-case controller.

## Paired RSS observations and interpretation

The declared epoch is MONOTONIC `1100952.829342066` s, projected UTC `2026-10-16T15:40:36.203768Z`. Times below are seconds after that monotonic epoch; widths and CPU are milliseconds. All eight bad widths are still resource_sample unknowns under the unchanged 5-ms wall gate. Seven fall in the 3,000/s burst; slot 24 is in the 500/s tail.

| Slot | Phase | t start | Wall ms | Thread CPU ms | CPU / wall % | Start lateness ms |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 12 | 1 | 12.000329 | 15.941445 | 3.496335 | 21.932 | 0.329233 |
| 13 | 1 | 13.000171 | 10.061475 | 3.729929 | 37.071 | 0.171497 |
| 14 | 1 | 14.000162 | 14.419406 | 4.373308 | 30.329 | 0.161787 |
| 15 | 1 | 15.000172 | 19.519640 | 5.580687 | 28.590 | 0.172460 |
| 17 | 1 | 17.000172 | 6.747730 | 3.347018 | 49.602 | 0.171773 |
| 18 | 1 | 18.001046 | 6.531977 | 3.012961 | 46.126 | 1.046094 |
| 19 | 1 | 19.000431 | 10.872480 | 3.806943 | 35.014 | 0.431073 |
| 24 | 2 | 24.000241 | 11.010825 | 4.033206 | 36.629 | 0.240551 |

All 72 scheduled RSS samples (slots 0–71) and the initial monitor RSS sample have valid sample/witness hashes, matching case/policy/owner and one observer thread, with observed CPU endpoints. The actual source makes two CPU endpoint attempts per completed enabled RSS read: 146 for these 73 observations. The two CPU pre-reads are uninstrumented. Closure occurred 70.013974856 s after epoch, so the unchanged coverage rule requires through slot 71, all present. All 74 absolute wait receipts were observed, with no explicit slot error/missed target. Maximum read-start lateness over all RSS rows was 2.534900 ms, inside 50 ms. Empty missed_slots does not repair inadmissible widths.

The wide-bracket thread CPU values are 3.012961–5.580687 ms alongside 6.531977–19.519640 ms wall widths, or 21.932–49.602% of wall time. This measurement is useful: it distinguishes a substantial amount of reader-thread execution from a larger elapsed interval. The separation supports scheduling/blocking within the bracket; it does not identify GIL versus OS preemption versus I/O, or measure exact off-CPU duration. The CPU scope is inside the wall endpoints and omits head/tail clock/validation work. No difference was used as a corrected width, reported as exact waiting time, or used for acceptance.

Slot 15 also records **5.580687 ms of reader-thread CPU**, already more than the unchanged 5-ms wall limit, within a 19.519640-ms wall bracket. Active work matters in this observation as well as the larger wall/CPU separation. This is not an intrinsic-cost minimum, a guarantee, or evidence that the added instrumentation alone caused the cost.

Available contention context uses existing observations only. Counter windows below are the outer envelope of the nearest resource bracket wholly before/after the event. CPU snapshots occur somewhere inside those endpoints; positive deltas locate throttling within the roughly two-second surrounding window, not within the bad read. Windows overlap and must not be summed. `Sync` counts overlapping recorded flush/fsync barriers, not measured disk service time.

| Slot | Wake ms | Wait-to-reader ms | Counter window t | Δnr_throttled / Δthrottled µs | Sync |
| ---: | ---: | ---: | --- | --- | ---: |
| 12 | 0.215083 | 0.114149 | 11.000492–13.010233 | 4 / 6001 | 1 |
| 13 | 0.084850 | 0.086646 | 12.000329–14.014581 | 3 / 10346 | 0 |
| 14 | 0.091018 | 0.070768 | 13.000171–15.019692 | 6 / 34564 | 0 |
| 15 | 0.092065 | 0.080394 | 14.000162–16.004590 | 11 / 55198 | 1 |
| 17 | 0.091355 | 0.080417 | 16.000192–18.007578 | 6 / 8072 | 1 |
| 18 | 0.963132 | 0.082961 | 17.000172–19.011304 | 6 / 27418 | 0 |
| 19 | 0.331093 | 0.099979 | 18.001046–20.003158 | 3 / 23018 | 1 |
| 24 | 0.097938 | 0.142612 | 23.000194–25.003245 | 0 / 0 | 0 |

Four bad brackets overlap a persistence barrier and four do not. Seven surrounding windows show throttle increments; slot 24 shows zero. Throttling and persistence overlap cannot explain every event, and neither correlation establishes cause. Over the retained consumer cost samples, nr_throttled increased by 30 and throttled_usec by 127,576; these are unit/counter context, not event-specific delay attribution. Every sampled memory.events counter is zero. Shared collectors/host scheduling, GIL and I/O contributions remain unisolated. Host process inventories are only before/after snapshots. Operator progress queries observed readiness at 15:38:09 and 15:39:43 UTC, then a producer-only state at 15:42:09 after recorder exit; no added host query was made during recorder measurement. Existing controller/producer/public activity remains part of the shared-host context.

## Unchanged application verdict and every UTC failure

All original append/durability gates pass. Case append p99 0.328768 ms, worst 20.424363 ms; worst durability 137.460926 ms. Maximum phase append p99 0.343251 ms. All timing groups use their complete 5,000 / 30,000 / 25,000 and 60,000 denominators.

Four unique UTC rows exceed 1 ms, all phase 1. The six audit failure entries are these four plus case/phase aggregate duplicates, not six independent bad rows. The CPU instrumentation does not instrument or resolve this UTC clock/formatting bracket.

| Sequence | t start | UTC width ms | Observed UTC |
| ---: | ---: | ---: | --- |
| 7236 | 10.747788 | 1.172455 | 2026-10-16T15:40:46.951540Z |
| 11693 | 12.234049 | 1.943665 | 2026-10-16T15:40:48.437801Z |
| 12410 | 12.470253 | 1.459714 | 2026-10-16T15:40:48.674008Z |
| 24142 | 16.381386 | 1.894590 | 2026-10-16T15:40:52.587014Z |

The one complete [0,60] cgroup CPU window passes: upper **36.100538% of effective quota**, under 70%. Max admissible sampled current RSS is **92,704,768 bytes (88.410156 MiB)**, within the unchanged 80%-of-512-MiB budget for those admissible observations. Eight inadmissible RSS widths still leave resource acceptance **unknown**. The known UTC failures preserve overall **fail**.

Both additional CPU timing calls and their validation count inside the authoritative RSS wall bracket. Thread identification is before it; witness hashing and increased publication are after it and can affect subsequent scheduling/inclusive resources. Whole-unit CPU is retained above. **Incremental observer overhead remains unknown**: this single instrumented case has no paired control. It is not calibrated by comparing unrelated historical runs. MemoryPeak is unavailable for all three units; continuous/high-water RSS remains unknown. Producer relative-sleep internal retry count remains unknown as prospectively disclosed.

## Integrity, origin and stop

All **43 originating files / 36,788,158 bytes** verify against the originating inventory. Safe extraction validated 45 regular relative archive members; five control files were restored from the exact preapproved transport bytes and matched the native inventory. Native, CloudShell-decoded and downloaded archive byte anchors all match. The independent audit ran offline on Intel macOS against the exact frozen candidate checkout; original native-origin authority flags remain false, with separate operator-observed origin receipt rather than promoting self-attestation.

- Outcome: 10,933,856 bytes, SHA-256 `1b077a9745ada5742ac4962e7bc1d5653c0f08faa4b58ea5ac7151a11e560b18`.
- Origin inventory file SHA-256 `7d4d047a25e1d5b28370b45fdd98def0d3993e8515eb97fbef48a1a04e85036b`.
- Post-stop checks file SHA-256 `657ab2e8472da6be832fd023ed291105403aee63f16844e3468d7031069109cf`.
- Frozen independent audit SHA-256 `c115ad33d1c95cfc1f9eb215d7ee882a99a0ad23cea5b3d73d0f63cd8ec8ffb8`.
- Separate observed-origin receipt payload SHA-256 `4e0b275662ae8e6b8665f72ddbc50b3ee631a70b8e3e4f6d37ea1b1cb8ea6432`.

Post-stop source/runtime/public checks match and no scoped unit remains. Public collector state, source/environment and limits are unchanged. Dated prelaunch credit mode is standard; latest available balance was 576 at 15:21 UTC. Continuous credit balance/credit-related delay remains unknown; no new minimum gate was invented.

Private retained evidence and full 73-row auxiliary report: `.qcrl/reviews/recorder-rss-cpu-validation-20261016LupusRssCpu01/`. The native sealed-evidence screenshot predates the offline audit and proves collection/packaging state only. Cohort02 and original OOM evidence/verdicts remain byte-identical and failed. **Authorization is spent. No further run, diagnostic framework, resource change, replay or six-case cohort follows.**
