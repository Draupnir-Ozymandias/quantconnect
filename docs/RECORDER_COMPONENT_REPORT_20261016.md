# Retained recorder evidence — component report and one descriptive question

**Original application-budget verdict: FAIL.** This retrospective report adds no
combined acceptance badge. Cohort02's nine UTC failures and 39 RSS coverage
unknowns, and RssCpu01's four UTC failures and eight RSS unknowns, remain unchanged.
The [component-evidence contract](RECORDER_COMPONENT_EVIDENCE_DRAFT_V1.md) is a
draft only; producing this report does not adopt, execute or validate that draft.

## Original component observations

The frozen [Cohort02 audit/result](RECORDER_COHORT_V2_RESULT_20261016.md) establishes
360,000 exact ordered synthetic text occurrences, verified archive/completion
linkage and closure, valid stimulus, and observed append/durability bounds within
their original limits for every case/phase. Maximum append p99 is 0.392515 ms,
worst append 20.759482 ms, worst successful durable-watermark bound 144.319336 ms.
These start at the recorded monotonic observation stamp, not network arrival.

| Original case | Frames | UTC rows >1 ms | RSS slots unqualified | Complete CPU windows | Largest CPU upper bound (% effective quota) |
| --- | ---: | ---: | ---: | ---: | ---: |
| steady-0 | 60,000 | 1 | 1 | 2 | 23.336840 |
| mixed-0 | 60,000 | 3 | 11 | 1 | 35.582940 |
| mixed-1 | 60,000 | 2 | 8 | 1 | 34.598036 |
| steady-1 | 60,000 | 0 | 3 | 2 | 23.857136 |
| steady-2 | 60,000 | 1 | 5 | 2 | 23.923758 |
| mixed-2 | 60,000 | 2 | 11 | 1 | 35.386949 |

All nine CPU windows separately satisfy their original admissibility/budget
checks. This does not establish every-slot RSS compliance: resource qualification
remains unknown, despite low observed values. Incremental observer overhead and
continuous/high-water RSS remain unknown. No host-credit/event-cause inference.

The separate [RssCpu01 result](RECORDER_RSS_CPU_VALIDATION_RESULT_20261016.md)
retains 60,000 verified frames, passing append/durability and its one admissible
CPU window, but overall fail. Its source/instrumentation identity is different;
it is **not pooled into** the descriptive population below. Original origin
flags and separate observed-origin attestations are preserved.

## Concrete question and population

**Do one-second local timestamp-observation counts resolve the declared ten-second
burst in each retained mixed case, and how much bin-boundary ambiguity remains?**

This asks about coarse counting of recorder observations, a concrete downstream
descriptive use of the preserved intervals. It is not a question about market
quote-update intensity or whether real-market bursts occur. The synthetic corpus
contains duplicate text, malformed/unknown frames and PONGs; all are occurrences
in this count, not deduplicated venue events.

Population: exactly mixed-0, mixed-1 and mixed-2 from original Cohort02, 60,000
occurrences each, **180,000 total**. Their declared low/burst/tail phases are
10 s at 500/s, 10 s at 3,000/s and 50 s at 500/s. Each case uses its own original
shared native monotonic epoch. No pooling of performance gates, boot/domain
subtraction, UTC alignment, resampling, smoothing, tolerance or outlier exclusion.
This question/method was stated before the new calculation, but the source data
were already observed: this is retrospective exploratory description, not a new
preregistered or causal experiment.

## Method and uncertainty

Use each completion witness's `[returned.before, returned.after]` as a closed
enclosure of the callback's UTC-acquisition operation in the local monotonic
domain. The counted event is **local timestamp acquisition for that occurrence**.
It is not the exact `recv()` return, library receipt, kernel arrival or source
event. No unmeasured pre-stamp handoff is assumed bounded.

Bins are half-open `[epoch+k, epoch+k+1)`. For each bin, the lower count includes
intervals wholly within it; the upper count includes intervals intersecting it.
An interval ending exactly at a boundary is potentially in the following bin.
Use exact rational representations of the retained JSON numeric clock values;
do not invent additional timestamp precision or assign a midpoint. Every frame
remains included, including all seven original wide-UTC rows in these three cases.
Their original failed qualification is retained separately.

The arithmetic does not model unknown absolute UTC offset or establish calendar
bin accuracy. The retained monotonic order/domain and interval linkage are the
assumptions that make this particular within-case question answerable.

## Answer: the coarse burst is resolved; one occurrence has ambiguous bin membership

Every burst-second bin has **at least 2,986 certain observations**; every low-rate
bin has **at most 514 possible observations**. These count bounds are separated
in all three cases. This directly describes the retained recordings; there is
no confidence interval, generalized capacity claim or new acceptance test.

Ranges below give the lowest lower count through the highest upper count across
bins in that phase. They are not statistical confidence intervals.

| Case | Low-start bins 0–9 | Burst bins 10–19 | Low-tail bins 20–69 | Single-bin intervals / all occurrences |
| --- | ---: | ---: | ---: | ---: |
| mixed-0 | 499–501 | 2,990–3,010 | 496–504 | 59,999 / 60,000 |
| mixed-1 | 500–500 | 2,994–3,006 | 500–500 | 60,000 / 60,000 |
| mixed-2 | 500–500 | 2,986–3,006 | 497–514 | 60,000 / 60,000 |

**179,999 / 180,000** intervals fall wholly in one bin. The remaining occurrence
is mixed-0 sequence **43496**, enclosing epoch+36.996048987 to +37.000498042 s.
Its original UTC width is 4.449055 ms, still a failed <=1-ms qualification. Bin 36
has count **[496,497]** and bin 37 **[503,504]**; the one occurrence belongs to one
of those bins, not both. Upper counts across bins therefore do not sum to the
population. Six other original wide-UTC rows are wholly inside coarse bins;
that fact does not repair their original precision failures.

Preserve the tail: mixed-2 sequence **59999** is observed at epoch+70.001427490 to
+70.001457611 s, entirely in bin 70, after the planned `[0,70)` workload interval.
It is included in the 60,000 denominator and the report's bin 70, not dropped.
Mixed-2's `[10,20)` bins contain 29,986 observations, rather than the 30,000
scheduled burst occurrences; ordered later observations are retained. Do not
conflate producer schedule assignment, observation-bin assignment and frame loss.

This answers the chosen local coarse-count question. The retained synthetic
evidence cannot answer how often real BTC markets exhibit such bursts, reconstruct
a trusted book, identify venue-to-host latency or certify memory coverage. A
real-market descriptive question would require suitable retained market data
and its own eligibility assessment; no public capture is authorized here.

## Verification, provenance and reproduction

This is a one-off offline calculation, not a new diagnostic service or acceptance
implementation. Rechecked the original Cohort02 outcome archive, frozen audit,
origin-inventory byte anchor and **all 208 originating files / 218,570,554 bytes**.
Case/completion payload hashes, complete frame populations, sequence/connection,
clock-domain binding and monotonic order were checked before interval counting.
The original frozen audit supplies archive/raw/linkage/component findings; it
was not rerun under current successor sources or edited.

Boundary arithmetic checks cover contained intervals, exact upper/lower edges,
regression, negative offsets, NaN/infinity, bool and over-wide intervals. An
independent direct containment/intersection scan agrees with the floor-based
bin calculation for every intended and observed tail bin. Population identities
check certain+ambiguous=60,000 per case, and possible sums account for the sole
straddling occurrence. Original wide-row sequence lists match the frozen audit.
The RssCpu01 archive/audit anchors also reverify; its native evidence was not rerun.

Private retained script and full per-bin/component output:
`.qcrl/reviews/recorder-component-report-20261016/{report.py,report.json}`.
The script reads local retained evidence only; it does not invoke a launcher or
the draft contract. Local Python 3.14.6 computation is distinct from the original
Linux/aarch64 collection. No new native readiness, collection or performance run.

- Cohort02 outcome SHA-256: `51609e2ecca1b155d0ea3a631b3961ee46b207489be49504dc0840782ce71b64`.
- Frozen audit SHA-256: `c9296f31e5c89efb3071f883cdf15ff54f3ae1bbace64e70c01f2f1488f67618`.
- Origin inventory SHA-256: `69dfa0dfff98f2ca085cb1150ee1d4c9212b6810360a3797230e83afafca9847`.
- Report script SHA-256: `bc1b65c25797abf966b097a3fdecedad733dfa9341da521ffa743930a5dbfa3d`.
- Derived report SHA-256: `5646dfb1d2883f6d86c24e1e38b12f8e97ff5ac3f9d6da283dfeec9cf73d9110`.

No original threshold, failed verdict, measurement semantics, bracket, frozen
source/runtime or evidence changed. No combined badge, observer implementation,
native rerun, new cohort, infrastructure/public change or execution authority.
