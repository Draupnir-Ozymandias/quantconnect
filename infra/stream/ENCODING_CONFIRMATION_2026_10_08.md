# Order-reversed encoding confirmation — October 8, 2026

## Verdict

**CPU benefit confirmed; hold public rollout.** The candidate used less consumer
CPU in all three confirmation pairs, complementing all three original pairs.
Confirmation median CPU fell **5.17%**, versus **5.58%** in the first cohort.
The large burst-tail improvement did not reproduce: confirmation median burst
p99 improved only **2.57%**, versus **27.83%** originally. Each cohort contains
one candidate burst regression. Approximately **60%** of confirmation candidate
callback timings remain unknown, despite complete raw-message preservation.

These are separate, small synthetic cohorts, not a latency guarantee or proof
of the cause of public-stream gaps. No public deployment is justified yet.

## Frozen design and actual order

See [the prospective protocol](../../docs/ENCODING_CONFIRMATION.md) and
[the unchanged first-cohort report](SINGLE_PASS_ENCODING_2026_10_08.md).
Confirmation source: `106cb00694dea6883f3ca7c05296adfd1983220c`.
The comparison verified identical corpus and every original implementation-file
hash. Only cohort identity, wrapper/launcher inventory and pair order changed.

Saved monotonic worker start/exit timestamps establish candidate/reference,
reference/candidate, candidate/reference order. They complement the original
reference/candidate, candidate/reference, reference/candidate sequence.
All measurements preceded offline verification; no concurrent audit was run.

Each case retained the six-cycle, 30-second, 30,000-message localhost fixture
with 500/3,000-message/s phases. Separate producer/consumer processes retained
100%/75% CPU quotas, 512 MiB, 32 tasks and 120-second limits. The shared Ohio
host had no CPU affinity or exclusive scheduling guarantee. Public stream
code, configuration, durability and limits were untouched.

## Confirmation results

CPU, p99 and storage are medians of three individual run statistics, not pooled
percentiles. Known/eligible fractions and unknown counts combine 90,000 messages
per lane. Phase labels follow target producer emission; low-rate phases can
include preceding burst backlog. Delivery bounds begin before producer
serialization/send: they are not wire latency or exchange timing.

| Metric | Reference | Single pass |
| --- | ---: | ---: |
| Median consumer CPU seconds | 17.485486 | 16.581760 |
| Median 500-phase delivery p99, ms | 766.695 | 605.850 |
| Median 3,000-phase delivery p99, ms | 869.400 | 847.016 |
| Worst delivery upper bound, ms | 1,062.730 | 966.865 |
| Known and timing-eligible callback fraction | 36.7800% | 39.7533% |
| Unknown receive records | 56,898 | 54,222 |
| Verified recovery generations | 56 | 63 |
| Median uncompressed bytes | 108,803,110 | 105,708,044 |
| Median compressed bytes | 12,435,403 | 12,381,186 |

Median low-rate p99 improved 20.98%. Median storage fell 2.84% uncompressed,
0.44% compressed. These observations concern the combined serialization and
physical-format candidate, not an isolated attribution to either change.

| Pair | First lane | CPU reduction | Reference burst p99, ms | Candidate burst p99, ms |
| --- | --- | ---: | ---: | ---: |
| 0 | Candidate | 4.93% | 869.400 | 942.652 |
| 1 | Reference | 5.62% | 993.108 | 847.016 |
| 2 | Candidate | 3.85% | 809.098 | 759.647 |

Pair 0's candidate burst p99 worsened 8.43%. The original regression occurred
with the reference first, so reversing order alone did not eliminate instability.
Do not pool the two cohorts to conceal their different median tail effects.

All six cases preserved every raw delivery. Unknown callback timing is not lost
raw data. Sampled library queue depth again reached 91; pinned-library
`max_queue=16` is a high-water backpressure setting, not a hard parsed-batch cap.
The lowest producer burst attainment was 2,989.4993 messages/s; largest producer
deadline lateness was 30.817 ms. Scheduler, producer and recovery effects remain
limitations, not evidence of a network cause.

## Verification and provenance

Local suite: **544 tests passed**, 17.812 seconds.
Linux suite: **544 tests**, 47.067 seconds, passing with one expected
Python-version inventory skip. All thirteen measurement/test workers succeeded.

Remote root: `/var/lib/qcrl-stream/encoding-confirmation-20261008-KmFMIa`.
Fresh ignored local review:
`.qcrl/reviews/encoding-confirmation-linux-20261008-EYGSh8/`.

Independent audit verified exact originating bytes and SHA-256 inventory for
**225 files**, **180,000 raw deliveries**, **180,144 logical rows**, all six
complete archives and **119 recovery generations**. It checked raw/probe/heartbeat
identity, canonical row digests and physical representation, archived versus
saved receive records, independently recomputed phase statistics, successful
worker exits and configured systemd/cgroup limits.

The audit adapter binds the original audit's exact bytes and changes only its
cohort import, expected test count and result schema label. Generic case reports
and encoding-verification receipts were derived locally after byte verification;
they are not originating EC2 files. This cohort was not uploaded to S3.

Audit SHA-256:
`f9e58e5e77c47b0d7ca19ba6ed8fc57c3fae42c8aa0a38e1191bfc53413f0f8f`

Adapter SHA-256:
`1cb5f99b0f1cf5668f95c55130671bb1680faa3d370af2adc26b93e0e2ec3dbb`

Bound original audit script SHA-256:
`182f851866a03ccc51ea7bc10971d814945130e70906a2b78c0c4d0d05d7f345`

Separate-cohort comparison SHA-256:
`400cf372e6429f30b9c4a8770f05f31a24f2660db9d55182e56d01a707212f6c`

Comparison script SHA-256:
`59b5a2c50005f03509583ccd502d7b89a20cbc8a05018c5c495353b09da019de`

Public checkout remained `4dd60ba168180243f8600860330dc1afc4816ff4`;
`/etc/qcrl-stream.env` remained
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily collection stayed active; the stream observer stayed inactive. No credentials,
trades, public captures, infrastructure updates, quota increases or QuantConnect
synchronization were performed.

## Next high-value step

Build a bounded, versioned **batch/marker-pressure attribution analyzer using
existing traces**, before further captures or public deployment. Match observed
queue-depth/overflow counters, retained receive markers, recovery reasons and
known/unknown transitions; report missing evidence explicitly. Comparing queue
depth 91 with marker retention 64 does not by itself prove a causal mechanism.
The analyzer should explain the residual observability limit without relaxing
freshness, inventing callback timestamps or weakening durability.
