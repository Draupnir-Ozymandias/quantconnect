# Marker-cap sensitivity audit — October 8, 2026

## Verdict

**Observability improved; advancement gate failed. Keep diagnostic-only.**
The 128-marker lane retained eligible callback timing for every one of its
90,000 deliveries, with zero overflows. The 64-marker lane retained eligible
timing for 41.30%. However, low-rate p99, burst p99 and worst delivery upper bound
were worse with 128 markers in **all three pairs**, including the reversed pair.
This fails the preregistered no-tail-regression gates. Do not run a confirmation
or deploy this variant merely because coverage reached 100%.

The result distinguishes timestamp visibility from low latency. It does not
establish the cause of live-stream gaps or a general causal latency penalty for
larger caps. All raw deliveries were preserved in both lanes.

## Frozen prospective experiment

See [the preregistered protocol](../../docs/MARKER_CAP_PAIR.md).
Source: `20864012a2eb0272d40206e71a7ed7c77621984d`.
Actual worker timestamps verified 64/128, 128/64, 64/128 ordering and completed
first-lane exits before second-lane starts. Both declarations bind identical
source inventories and corpus; their policies differ only in marker cap.

Single-pass encoding was fixed in both lanes. The unchanged workload used six
500/3,000-message/s cycles, 30 seconds, 30,000 messages per case and six scheduled
synthetic text PONGs. Producer/consumer CPU quotas remained 100%/75%; each retained
512 MiB, 32 tasks and a 120-second limit. Library high-water remained 16.
Freshness, overflow/recovery semantics, numeric caps other than retained markers,
durability, segment policy and process isolation were unchanged.

The 128 cap is a **scoped diagnostic v3-shaped variant**, not a new production
contract. Its common-shape validation helper uses the same temporary cap. Tests
prove the normal production validator rejects the variant outside explicit
diagnostic scope and that scope exit restores the original policies.

No audits ran during measurement. The Ohio host was shared, with no exclusive
core or scheduling guarantee. The six finite captures were not restarted or
replayed. Earlier cohorts were neither rewritten nor pooled into this one.

## Performance and coverage

CPU, phase p99 and storage are medians of three individual run statistics,
not pooled message percentiles. Coverage/counts combine 90,000 deliveries within
each lane. Producer phases follow target emission; low-rate phases can retain
earlier burst backlog. Delivery upper bounds start before producer serialization
and send; these are not exchange or wire latency measurements.

| Metric | 64 markers | 128 markers |
| --- | ---: | ---: |
| Median consumer CPU, seconds | 16.523371 | 16.227411 |
| Median low-rate delivery p99, ms | 575.837 | 731.774 |
| Median burst delivery p99, ms | 658.072 | 821.394 |
| Worst delivery upper bound across runs, ms | 797.001 | 917.133 |
| Known callback records | 37,174 | 90,000 |
| Locally timing-eligible records | 37,172 | 90,000 |
| Timing-eligible coverage | 41.3022% | 100% |
| Unknown callback records | 52,826 | 0 |
| Closed overflow/recovery episodes | 80 | 0 |
| Open episodes | 0 | 0 |
| Median uncompressed bytes | 106,225,500 | 105,118,378 |
| Median compressed bytes | 12,445,697 | 14,469,329 |

Median CPU fell 1.79%, but median low-rate p99 increased 27.08% and burst p99
24.82%. CPU was lower in every pair; it does not substitute for the failed tail
gates. Median compressed storage increased 16.26%, despite uncompressed storage
falling 1.04%. Changed telemetry contents differ between policies, so these are
whole-lane observations, not an isolated allocation or serialization cost estimate.

| Pair / first lane | Low-rate p99, 64→128 ms | Burst p99, 64→128 ms | Worst upper bound, 64→128 ms |
| --- | ---: | ---: | ---: |
| 0 / 64 | 556.010 → 674.853 | 599.392 → 719.426 | 628.954 → 743.139 |
| 1 / 128 | 575.837 → 764.927 | 658.072 → 869.754 | 697.338 → 917.133 |
| 2 / 64 | 658.464 → 731.774 | 758.463 → 821.394 | 797.001 → 869.303 |

Sampled library queue depth reached 91 in every case. Sampled backpressure
remained common: 19,258–19,587 deliveries per 64-marker case and 19,804–19,988
per 128-marker case. Removing marker overflow did not remove library backlog.
The high-water setting is not a hard parsed-batch capacity.

All cases retained eight in-capture RSS samples. Maximum retained RSS was
approximately 154–155 MB in both lanes, well below the configured 512 MiB cap.
Those sparse samples do not prove lifetime peak memory. Saved systemd properties
did not expose MemoryPeak; that field remains explicitly unknown. All thirteen
measurement/test workers exited successfully under verified configured limits.

Overall producer attainment was 999.9791–999.9813 messages/s. Minimum individual
burst attainment was 2,998.4582 messages/s; maximum producer deadline lateness
17.765 ms. Producer and scheduler effects remain limitations of this small cohort.

## Independent audit and provenance

Local suite: **555 tests passed**, 18.193 seconds.
Linux suite: **555 tests**, 49.873 seconds, passing with one expected
Python-version inventory skip.

Remote root: `/var/lib/qcrl-stream/marker-cap-20261008-vq9sZu`.
Fresh ignored local review: `.qcrl/reviews/marker-cap-linux-20261008-dwJ721/`.

Audit verified exact originating bytes of **223 files**, **180,000 raw deliveries**,
**180,144 logical rows**, every canonical digest and compact physical representation,
all six complete archives, all **80 recovery fences**, raw/probe/heartbeat identity,
archived versus saved receive records, source/corpus bindings, recomputed phase
statistics, actual worker order and resource/exit properties. Originating bytes
were rechecked after pressure analysis. No synthetic evidence was uploaded to S3.

The audit adapter byte-binds the unchanged original independent audit and applies
explicit lane/import, fixed-format, scoped-validation, test-count and schema
transformations. Ordinary validators remain unchanged. Generic case reports and
encoding-verification receipts were derived locally; pressure reports and gate
evaluation are outside the originating evidence tree.

Audit SHA-256:
`9b08704388c1ef2336ff8238bc4c0f2bea198774042a86589921b1ccc24bb39a`

Audit adapter SHA-256:
`30d8825564a696244d7431ab40946521b727892cec563df66d4b45de1ad40d5e`

Bound original audit script SHA-256:
`182f851866a03ccc51ea7bc10971d814945130e70906a2b78c0c4d0d05d7f345`

Gate evaluation SHA-256:
`269c84b367d86305834725080780001b76d77bc13c64822a0af64f9d3ae23fc5`

Evaluation script SHA-256:
`f2881ea91cceb9d1c8ae8fcfbb7c8f2f9960e24df61ab961569fbad2b539385e`

Public checkout remained `4dd60ba168180243f8600860330dc1afc4816ff4`;
`/etc/qcrl-stream.env` remained
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily collection remained active and the public stream pilot inactive.
No public capture, credentials, trades, infrastructure change, quota increase,
public deployment or QuantConnect synchronization occurred.

## Next high-value step

Use the **fully timed existing 128-marker traces** for a bounded producer-to-callback
versus callback-to-delivery decomposition. Keep producer send/deadline context,
clock brackets, eligibility and phase populations explicit. Compare per-message
paired intervals, not sums of independently computed percentiles. Profiling and
quota samples can provide context, not event-specific causal attribution.

This needs an offline analyzer, not another cap increase or capture. It should
locate where the observed upper bounds accumulate before deciding what to change.
Keep all historical unknown timestamps unknown and public rollout on hold.
