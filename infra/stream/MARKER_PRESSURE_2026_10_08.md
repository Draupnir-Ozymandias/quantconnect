# Retained-cohort marker-pressure findings — October 8, 2026

## Verdict

**The missing callback timestamps are explained by the bounded marker policy,
not missing archived raw deliveries. The cause of accumulated backlog remains
unresolved.** All unknown-timing deliveries in these twelve synthetic cases
belong to verified `pending_marker_budget` episodes. All 258 episodes eventually
closed at exact occurrence-counter recovery fences.

Approximately 75% of unknown deliveries had sampled library depth **at or below
64**. Once overflow disables marker retention, lowering sampled depth below the
cap does not restore timing: v3 requires no retained markers, no incomplete
fragment and exact observed/delivered occurrence equality. This is an intentional
fail-closed policy, not a reason to invent timestamps or declare shallow queues
fresh. A closing fence itself remains an unknown delivery.

## Analyzer and verification

The [versioned offline analyzer](../../docs/STREAM_MARKER_PRESSURE.md) verifies
each full sealed archive, rechecks its chain on the analysis pass and independently
validates the complete raw/delivery occurrence trajectory. It records overflow
episodes, retained prefixes, unknown populations, exact fences, subsequent known
deliveries, joint sampled pressure cells and between-delivery callback-counter
increments. These increments are **not observed socket-read batch boundaries**.

Every originating file in both cohorts was checked against its original SHA-256
inventory before analysis: 229 files in the first, 225 in confirmation. All twelve
new report digests were checked, and their unknown counts and recovery generations
matched the prior independently audited cases. All **360,000 archived raw
deliveries** were scanned; original cohort evidence was not altered.

Local full suite: **549 tests passed**, 18.080 seconds. All five new analyzer
tests also passed on Linux/Python 3.9 in an isolated temporary checkout, 0.267
seconds. Tests include repeated identical payloads, open episodes, fragmentation,
tampering, missing occurrences, budgets, and immediate re-overflow after recovery.
The Linux test checkout did not advance or modify public collectors.

## Separate cohort results

Each row combines three 30,000-delivery cases within its original lane/cohort.
No timings or cohort performance metrics were pooled across cohorts. Missing
queue samples remain separate and are not classified as shallow queues.

| Cohort/lane | Known | Unknown | Closed episodes | Unknown depth ≤64 | Unknown depth missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| First / reference | 34,065 | 55,935 | 73 | 41,966 (75.03%) | 2 |
| First / single pass | 36,562 | 53,438 | 66 | 39,931 (74.72%) | 0 |
| Confirmation / reference | 33,102 | 56,898 | 56 | 42,484 (74.67%) | 16 |
| Confirmation / single pass | 35,778 | 54,222 | 63 | 40,527 (74.74%) | 4 |

Largest single episode: **3,443 unknown deliveries**, confirmation reference
pair 2. Every case reached sampled library depth 91; between-delivery observed
message/frame increments reached 88–89. These observations support testing marker
retention under callback bursts, but cannot equate one increment with one parsed
transport batch or establish the cause of a specific overflow.

No known marker was fragmented in these synthetic traces. That does not prove
unknown messages were unfragmented; their per-message fragment counts were not
retained. Unknown timing cannot be reconstructed from aggregate frame counters.

First subsequent known delivery was observed after 70/73 reference and 64/66
candidate first-cohort fences, and 53/56 reference and 61/63 candidate confirmation
fences. The remaining ten fences have no subsequent known delivery within their
archives. Do not infer unrecorded resumption beyond that boundary. No episode
was still draining at its terminal delivery.

## Provenance and preserved state

Completed reports and summary:
`.qcrl/reviews/marker-pressure-final-20261008-SvRPW0/`.

Summary SHA-256:
`edea8a70465cd98bd8ae997979d47148bb2799666a4a2589b5b4e81116b30acb`

Analyzer SHA-256:
`502a861322750d0fbf60bf059e32d2dcecba31cf14bc5df00c3ba1cfef7e5074`

Tests SHA-256:
`03c732e3442ecc0cda718f4da7f94860952a87a6de65447d3185e84bb030c62e`

The preliminary review at `.qcrl/reviews/marker-pressure-20261008-IVjUeX/`
was interrupted after discovering that immediate re-overflow could hide the
first known delivery after a prior fence. It remains preserved, is incomplete,
and is not used for these findings. The corrected attribution is tested explicitly;
all twelve cases were rescanned into the fresh final directory.

Original [first-cohort](SINGLE_PASS_ENCODING_2026_10_08.md) and
[confirmation](ENCODING_CONFIRMATION_2026_10_08.md) audits retain their source,
byte inventories, fixed quotas and performance conclusions. New reports are
derived local artifacts, not originating EC2 or S3 capture files. Public stream
checkout, configuration and resources were not changed. No new public or
synthetic capture, trading, credentials or QuantConnect sync occurred.

## Next high-value gate

Declare a **diagnostic-only marker-cap sensitivity experiment** before changing
retention semantics: compare the current 64-marker policy with a separately
versioned bounded larger cap under the same fixed loopback workload and resource
limits. Keep candidate encoding fixed; measure timing coverage, overflow episodes,
CPU/memory and delivery tails. A larger cap is not a change to library queue size
and cannot be assumed to eliminate backlog or improve public-market freshness.

Historical unknown timestamps remain unknown. The experiment needs new prospective
callback observations; existing counter traces cannot establish its timing results.
Continue holding public rollout until explicit acceptance criteria are met.
