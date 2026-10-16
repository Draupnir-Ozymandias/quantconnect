# Cohort02 result — collection complete; application acceptance fails

**The one approved six-case cohort completed, and its independent audit verdict
is fail.** All 360,000 ordered occurrences, archive bytes, completion links,
verified closure and native unit bindings pass. Nine application-return UTC
brackets exceed the unchanged 1-ms limit. Resource coverage remains unknown
because 39 RSS read brackets exceed 5 ms. Five cases fail and steady-1 is unknown;
no case passes overall. No thresholds, evidence or verdicts were repaired.

## Identity, scope and native readiness

Candidate `4926d62faab552af8a3c8e3fe964dc16052e4773` (520 selected files), v2 freeze
`6428a09a34633987a353c32beeca340be535b33c1e11aa897f291d37a4da434b`, approval packet
`dcce731de610681470fb773e3ed95be1d47329b9bc0905fa0b7cfdb3ad3399e2`.
The user approved the [exact packet](RECORDER_COHORT_READINESS_V2_APPROVAL_20261015.md)
with “please continue.” One controller, PID 1516839, was submitted at
**2026-10-16 03:04:26.911235 UTC**. Complete collection was observed at 03:24:48 UTC.
Stage: `/var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort02`.

Exactly one readiness plus six serial producer/recorder pairs ran: 13 units,
all successful exits. Order: steady-0, mixed-0, mixed-1, steady-1, steady-2, mixed-2.
Every case has exactly 60,000 frames. Steady: 120 s at 500/s. Mixed: 10 s at 500/s,
10 s at 3,000/s, 50 s at 500/s. No runtime/closure or preservation error, retry,
replay, replacement, tuning, extra smoke/case/cohort, public capture or rollout.

The prospective **1-GiB readiness-only envelope passed** on installed Linux
Python 3.9.25/aarch64: **1,177 total, 1,176 pass plus the one declared skip, in
201.118 s**. PID 1516872, unit lifetime 202.476770 s, whole-unit CPU 142.162724 s.
These are native readiness observations, distinct from the earlier 1,177 passing
Intel macOS/Python 3.14.6 offline tests in 154.120 s and the offline audit below.
MemoryPeak is unavailable; successful bounded completion does not establish a
continuous/high-water RSS peak or guarantee future suite margin. The original
512-MiB OOM attempt remains failed with its original declaration and evidence.

All twelve case units retain **512 MiB**, CPU 75%, TasksMax 32, RuntimeMax 240 s.
Readiness changes only its memory allowance; CPU/tasks/240-s ceiling remain.
Original plan hash `eca23ef82ac9ca72a816a9580483a35657df364ea081f7772f8e5c0477b1fa6b`,
50-ms CPU pre-read lead, missed-target handling, 1-s persistence reserve and all
budgets/denominators remain unchanged. The reserve remains prospective, not a
guarantee. Historical smoke/cohort results are unchanged.

## Completeness, timing and stimulus

The exact candidate's frozen auditor ran **offline on the retained native bytes**,
after safe extraction, origin-inventory/control verification and source checkout
verification. It returned complete=true, verdict=fail, application_budget_pass=false.
Every archive has 60,000 ordered exact corpus frames, correct footer, zero gaps,
full occurrence/completion linkage and verified closure. All phase stimulus gates
pass with 100% attainment: steady denominator 60,000; mixed 5,000/30,000/25,000.
All producer start/call bounds satisfy the unchanged 50-ms gates.

All values below are **milliseconds**, evaluated over full case denominators.
Every declared case and phase passes append p99 <=100 ms, append worst <=1,000 ms,
and durable worst <=2,000 ms. The maximum phase/case append p99 is
0.392515 ms; worst append 20.759482 ms, worst durable 144.319336 ms.
The UTC gate remains <=1 ms for every row, without a percentile exemption.

| Case | Append p99 ms | Append worst ms | Durable worst ms | UTC bracket worst ms | Case verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| steady-0 | 0.294841 | 19.784103 | 136.780011 | 3.343150 | fail |
| mixed-0 | 0.314853 | 19.064181 | 139.807726 | 4.449055 | fail |
| mixed-1 | 0.313138 | 20.759482 | 135.306168 | 1.358457 | fail |
| steady-1 | 0.303776 | 20.349205 | 144.319336 | 0.977791 | unknown |
| steady-2 | 0.311178 | 20.142758 | 137.519462 | 5.210600 | fail |
| mixed-2 | 0.341782 | 20.718246 | 136.824120 | 2.080684 | fail |

All nine row violations are retained below (zero-based sequence, declared phase).
The auditor's 22 failure entries consist of these nine row failures plus 13
case/phase aggregate UTC-gate entries; they are not 22 independent bad rows.

| Case | Sequence | Phase | UTC bracket ms |
| --- | ---: | ---: | ---: |
| steady-0 | 24584 | 0 | 3.343150020 |
| mixed-0 | 1320 | 0 | 1.146995928 |
| mixed-0 | 14021 | 1 | 2.148268977 |
| mixed-0 | 43496 | 2 | 4.449054832 |
| mixed-1 | 14586 | 1 | 1.358456910 |
| mixed-1 | 56373 | 2 | 1.347478945 |
| steady-2 | 50423 | 0 | 5.210600095 |
| mixed-2 | 7952 | 1 | 2.080684062 |
| mixed-2 | 27712 | 1 | 2.036238089 |

## Inclusive cost and resource admissibility

All **nine complete 60-s CPU windows** are admissible and below the unchanged
70%-of-effective-quota bound. The maximum upper fraction is **35.582940% of
quota**, not percent of a whole CPU core. All retained current RSS values are below
80% of 512 MiB; maximum admissible timed sample is **93,057,024 bytes
(88.746094 MiB)**. This does not establish memory coverage at invalid observations
or any continuous peak.

| Case | Complete CPU windows | Maximum CPU quota fraction | Maximum retained RSS MiB | Inadmissible RSS reads |
| --- | ---: | ---: | ---: | ---: |
| steady-0 | 2 | 23.336840% | 88.468750 | 1 |
| mixed-0 | 1 | 35.582940% | 88.242188 | 11 |
| mixed-1 | 1 | 34.598036% | 88.382812 | 8 |
| steady-1 | 2 | 23.857136% | 88.363281 | 3 |
| steady-2 | 2 | 23.923758% | 88.746094 | 5 |
| mixed-2 | 1 | 35.386949% | 88.238281 | 11 |

Cost is **inclusive recorder-unit accounting**, without subtraction of observer
work. The archive retains initial samples, publication/close costs in whole-unit
exit counters, cgroup memory/events, throttling and separate producer costs.
Whole consumer CPU totals sum to 132.163074 s; producer totals to
175.120533 s. These totals include startup/publication/verification and are
not substituted for the declared per-window gate. Readiness CPU is separate.

| Case | Whole recorder CPU s | Whole producer CPU s | Recorder throttle-count delta | Recorder throttled microseconds delta |
| --- | ---: | ---: | ---: | ---: |
| steady-0 | 23.308845 | 29.893437 | 0 | 0 |
| mixed-0 | 20.379503 | 28.578793 | 11 | 55099 |
| mixed-1 | 19.930808 | 28.014575 | 8 | 36902 |
| steady-1 | 24.048331 | 30.227153 | 0 | 0 |
| steady-2 | 24.028214 | 30.124767 | 1 | 20492 |
| mixed-2 | 20.467373 | 28.281808 | 12 | 77917 |

The boundary review finds **597 observed wait receipts**, 582 recorded RSS rows,
zero explicit wait-target misses and no explicit slot error fields. However,
**39 RSS reads have brackets >5 ms** (maximum 19.535399 ms), with read starts still
inside the 50-ms allowance. These are the auditor's resource-sample unknowns.
The frozen `missed_slots` list is empty because it records explicit slot errors;
that empty list does **not** mean valid resource coverage or an overall zero-miss
pass. Its bytes and classification remain unchanged. Native absolute waits do not
by themselves make the full reader path admissible.

Every resource unknown is listed here; slots are case-relative integer seconds.
All are `resource_sample:SLOT` entries prefixed by the corresponding case in the
full audit. The separate boundary review retains each width and start lateness.

| Case | Every inadmissible/unknown RSS slot | Largest bracket ms |
| --- | --- | ---: |
| steady-0 | 76 | 5.111065 |
| mixed-0 | 3, 10, 11, 12, 13, 14, 15, 17, 18, 19, 22 | 19.535399 |
| mixed-1 | 10, 11, 12, 13, 15, 17, 18, 38 | 11.453563 |
| steady-1 | 25, 38, 78 | 19.092548 |
| steady-2 | 4, 57, 65, 66, 68 | 15.453753 |
| mixed-2 | 11, 12, 13, 15, 16, 17, 18, 19, 38, 54, 55 | 14.546445 |

Additional unresolved context/claims: incremental observer overhead was not
measured; continuous recorder/producer/readiness RSS peaks are unproven; all
13 systemd MemoryPeak fields are absent and process high-water RSS is unavailable;
producer sleep's internal retry count remains unknown under its declared runtime
policy; shared-host/public-collector and credit effects remain unisolated;
continuous credit balance is unknown. These are not silently passed from inclusive
CPU or sampled RSS, and no new acceptance gates/minimums are invented. The active
test/allocation in the historical OOM remains unknown. The cause of the UTC/reader
bracket delays is not established by these counters; no causal tuning is claimed.

## Host context and preservation

Read-only pre-staging checks verified original source, installed runtime/dependency
bytes, live boot and public state, plus absence of the Cohort02 stage/units.
Host MemAvailable was **1,230,979,072 bytes**, no swap; disk free 6,689,808,384 bytes.
This was a snapshot, not reserved headroom. Raw EC2/credit API responses at
**2026-10-16 02:54:25 UTC** confirm Ohio t4g.small/standard mode. Latest returned
CPUCreditBalance: **576 at 02:49 UTC**; no minimum or continuous-balance claim.
Fresh observations supplement the unchanged dated frozen host control.

Controller before/after and independent post-stop checks match exact source,
runtime and public state: qcrl-collector.timer active, observer/pilot services
inactive, public HEAD 4dd60ba168180243f8600860330dc1afc4816ff4 and environment hash
33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca. No scoped unit
was running at preservation. No public/IAM/infrastructure/credential change,
main merge, QuantConnect sync or orders occurred. These are dated post-stop
observations, not a claim of continuous later host health.

## Integrity, transfer and final stopping point

Private evidence: `.qcrl/reviews/recorder-cohort-native-20261015LupusCohort02/`.
Origin inventory: **208 files, 218,570,554 bytes**, all independently byte-verified.
The 209 regular relative transport members omit only five byte-identical approved
controls, reconstructed from the frozen prep packet and checked against the
original inventory. No originating evidence or authority flag was rewritten.

The existing Session Manager client copied the sealed archive read-only into
CloudShell after all units stopped. A browser-session interruption delayed local
download; the same retained archive was later rehashed/downloaded and verified
again on the Mac. It did not repeat any experiment or alter native evidence.
Raw evidence and controls remain private, outside GitHub.

- Outcome: **65,739,818 bytes**, SHA-256 `51609e2ecca1b155d0ea3a631b3961ee46b207489be49504dc0840782ce71b64`.
- Origin inventory file SHA-256: `69dfa0dfff98f2ca085cb1150ee1d4c9212b6810360a3797230e83afafca9847`.
- Independent frozen audit file SHA-256: `c9296f31e5c89efb3071f883cdf15ff54f3ae1bbace64e70c01f2f1488f67618`.
- Post-stop checks file SHA-256: `e3aa187ab5002e9344e930686a5e12a181c5e15b4a37be2fe962ff5d99f3b5e4`.
- Raw prelaunch API file SHA-256: `09083646b4406b3ff71d22f1aee72d265a2e3034185c94ca72c3b4f030a7a90c`.
- Boundary review file SHA-256: `7bfffe4d2864fa16e53e09baadfbb25adde3cd3bc7f91db5a241bf2f9a16dcfa`.
- Separate observed-origin review payload: `91924019f6e8d4686aa0e5c90409ec5a633b6ce5f6734a7f39c604abfadba816`.

The independent auditor retains native_origin_verified=false and requires an
external observed-origin attestation; the separate operator review binds the
Session Manager observations and byte anchors without promoting authority flags.
The complete machine audit and boundary review retain every failure and unknown.

**Stop after this approved cohort and audit.** The failed application verdict and
resource unknowns remain. No replay, replacement, extra smoke/cohort, threshold
relaxation, tuning, rollout or subsequent native experiment is authorized.
