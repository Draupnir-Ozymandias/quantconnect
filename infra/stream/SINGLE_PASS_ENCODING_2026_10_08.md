# Paired single-pass encoding audit — October 8, 2026

## Verdict

**Promising diagnostic candidate; hold public rollout.** All three paired runs
used less consumer CPU with the candidate. Median CPU fell **5.58%**, and median
delivery-tail statistics improved. However, one candidate burst tail regressed,
the worst delivery delay stayed near **1.1 seconds**, and callback timing remained
unknown for approximately **59%** of candidate messages. This does not solve
receive-backlog observability or establish a cause of earlier public-stream gaps.

All six cases completed under the original limits. Public collector code and
configuration were unchanged. No public capture, credentials, orders, infrastructure
update, resource-limit increase, or QuantConnect sync occurred.

## Frozen comparison

See [the prospective protocol](../../docs/SINGLE_PASS_ENCODING_PAIR.md).
Frozen source: `faeef8e18d205863e9987c64979c4f2059755c78`.

Remote diagnostic source:
`/var/lib/qcrl-stream/encoding-pair-20261008-S4YPPz/source`

The candidate lives only in `infra/stream`: it serializes the unhashed row once
canonically, hashes those bytes and appends the hash field. Its JSON is compact
with the hash field last. Production `SegmentedStreamLog` remains untouched.
Tests prove decoded-row/hash equality under fixed clocks and compare append-method
ASTs: every branch other than encoding is identical. Quotas, reserve checks,
flush/fsync cadence, sealing, manifests, profiling and exclusivity remain intact.
Physical byte counts and segment boundaries can differ under the same numeric caps.

Three pairs used reference/candidate, candidate/reference, reference/candidate
order. Each case used the same frozen corpus, receive-v3, six 500/3,000-message/s
cycles, 30 seconds and 30,000 messages, including six scheduled synthetic PONGs.
Producer and consumer were separate processes/cgroups on the same shared Ohio
host, without CPU affinity. Producer CPU quota was 100%, consumer 75%; each had
512 MiB, 32 tasks and a 120-second cap. Verification waited until all measurements
finished and then ran offline locally. No competing audit workload ran during capture.

## Performance and coverage

CPU and p99 values are medians of three individual run statistics, not pooled
message percentiles. Producer-phase grouping follows target emission phase;
the 500-message/s phases include backlog carried over from preceding bursts.
Coverage below combines all 90,000 messages per lane.

| Metric | Reference | Single pass |
| --- | ---: | ---: |
| Median consumer CPU seconds | 17.442360 | 16.469506 |
| Median 500-phase delivery p99, ms | 809.516 | 577.073 |
| Median 3,000-phase delivery p99, ms | 867.230 | 625.903 |
| Worst delivery upper bound across three runs, ms | 1,124.608 | 1,116.933 |
| Known callback fraction, combined | 37.8500% | 40.6244% |
| Timing-eligible callback fraction, combined | 37.8489% | 40.6244% |
| Unknown receive records | 55,935 | 53,438 |
| Verified recovery generations | 73 | 66 |
| Median uncompressed bytes | 109,491,518 | 105,774,022 |
| Median compressed bytes | 12,511,521 | 12,400,733 |

Median p99s improved 28.71% in the 500 phase and 27.83% in the burst phase.
Median uncompressed storage fell 3.40%; compressed storage fell only 0.89%.
These are observations of the combined single-serialization/compact-format
candidate, not an isolated attribution to either change.

The individual burst p99s are important:

| Pair | Reference, ms | Candidate, ms |
| --- | ---: | ---: |
| 0 | 867.230 | 1,096.496 |
| 1 | 1,067.634 | 625.423 |
| 2 | 835.940 | 625.903 |

The candidate is not uniformly tail-better. All three CPU comparisons improved,
but the median hides the first candidate's regression. Three pairs do not provide
a general latency guarantee or distinguish scheduler/cache/order effects.

All cases delivered the complete 30,000-message fixture and preserved every raw
body. Unknown callback timing is **not missing raw market data**. Sampled library
queue depth reached 91 in both lanes: `max_queue=16` is the pinned library's
high-water backpressure setting, not a hard cap on all frames parsed from a batch.
Library backpressure remained frequent in both lanes.

Overall producer attainment was 999.9795–999.9816 messages/s, consistent with the
1,000-message/s average schedule. The lowest individual burst attainment was
2,997.4139 messages/s; the largest producer deadline lateness was 21.443 ms.
Producer begin precedes serialization and send, so these delivery upper bounds
are **not wire latency** or exchange-side timing.

## Retained profiling observations

All six cases retained eight in-capture profile samples. Cgroup counter deltas
showed quota throttling in every case: reference 118–122 throttled periods,
candidate 92–106. Recorded `throttled_usec` deltas were approximately 2.15–2.18
million for reference and 1.66–1.88 million for candidate. These are cgroup
counters, not per-message delays or proof of a network cause.

The largest retained append wall interval was 83.909 ms; the largest retained
fsync interval was 30.231 ms. Their overlap, coarse sample windows and incomplete
final-close sampling prevent summing stages or assigning a specific delivery
tail to one fsync. The observations support investigating accumulated backlog
under the fixed quota, not weakening durability or claiming hardware failure.

Profile-summary hash:
`b49a7c1691ad3f173635a007a575a6f3379f1362833e84539ee539edc010b681`

## Verification, provenance and preserved state

Local suite: **541 tests passed**, 17.254 seconds.
Linux suite: **541 tests**, 44.903 seconds, passing with one expected
Python-version inventory skip. Thirteen measured/test workers completed successfully.

Remote evidence:
`/var/lib/qcrl-stream/encoding-pair-20261008-S4YPPz/evidence`

Fresh ignored local review:
`.qcrl/reviews/encoding-pair-linux-20261008-pjHhwA/`

Independent audit verified the exact originating SHA-256 set and bytes of all
**229 files**, **180,000 raw/probe/heartbeat deliveries**, **180,144 logical rows**,
all six full versioned archives, **139 recovery generations**, and every row's
declared physical representation and canonical digest. It compared archived
receive records directly with saved application records and independently
recomputed phase percentiles, unknown counts and paired summaries. Worker PIDs,
same-boot cgroup identities, configured resource limits and successful exits
were checked against saved systemd properties.

Generic case reports and encoding-verification receipts were derived locally
after originating-byte verification; they are not claimed as originating EC2
files. These synthetic artifacts were not uploaded to S3. Streaming trials have
different clocks and probe contents: cross-encoder logical equality is established
by fixed-clock tests, not equality of independent live-run hashes.

Independent audit hash:
`d5159323ed9368f5e013ad9a9f7d096a340be2fc446cb26617c8bae9dfa00771`

Audit script hash:
`182f851866a03ccc51ea7bc10971d814945130e70906a2b78c0c4d0d05d7f345`

Public stream checkout stayed at
`4dd60ba168180243f8600860330dc1afc4816ff4`, and `/etc/qcrl-stream.env` stayed at
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
The daily collector timer remained active and the stream pilot inactive.
Fetching Git objects did not advance the public checkout.

## Next acceptance gate

Run a **separately declared order-reversed confirmation cohort** with the same
workload, limits and candidate. Reversing the three pair orders complements this
cohort's imbalance without rewriting it. Keep cohort-level results separate and
retain all existing profiling/recovery evidence. Require reproducible CPU benefit,
no consistent tail regression and explicit accounting for still-unknown callback
timing before considering any public implementation change.

Do not increase quotas, expand public collection or declare the remaining
multi-second live problem solved from these synthetic medians.
