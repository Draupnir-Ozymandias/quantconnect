# Compact receive-loop overhead cohort — independent audit

## Outcome

The approved one-shot cohort completed all six cases, without worker failures,
preservation errors, retries or policy changes. Independent origin/resource
verification passed. **Performance acceptance is inconclusive, not established.**
One producer phase missed its fixed attainment gate; nine receive records had
wide clock brackets; several individual pair tail ratios exceeded the fixed
5% allowance. Neither completion nor improved CPU ratios rescues these gates.
The earlier reference rejection remains unchanged. No public rollout follows.

## Frozen source and originating evidence

- Pushed execution source: `42a9c9079f83334bda2c23e89cb39174bd76f08a`.
- Preregistration: `c909b91e94413bc2f5a0bcc34f14b328bd4ed76d5258cde6168d05e4db224e8e`.
- Ohio stage: `/var/lib/qcrl-stream/receive-loop-compact-raqfGhbd`.
- Inventory FILE SHA-256, obtained directly from Ohio before download:
  `b2a86fd46efc50b36368a5cd67824fa8ee609a093b2154d3e31c4124859d1974`.
- Local immutable download:
  `.qcrl/reviews/compact-overhead-cohort-20261009-hqscZWk3/origin/`.
- Independent audit: sibling `audit.json`, payload SHA-256
  `f9cb0e6c9b2f488606a05850a26c3206ffafeb1348773f884ca5647c25c550f9`.

All **232 originating evidence files** matched the externally anchored inventory,
rechecked after analysis. All **13 test/worker units** passed identity, boot,
cgroup, quota/security, exit, ordering and measured-window verification.
The frozen Linux regression gate passed **709 tests, one expected skip**, in
71.011 seconds. Tests preceded all measurements.

Exactly six 30-second/30,000-delivery cases ran in the declared alternating order,
with separate producer/consumer processes and cgroups. CPU quotas remained
100%/75%; memory/task/runtime bounds remained 512 MiB/32/120 seconds. The
original six-cycle 500/3,000-message/s workload, encoding, marker/queue bounds
and timing windows were unchanged. No archive audits ran during measurement.

All **180,000 raw deliveries** were independently verified against producer
occurrences and sealed archives. All **90,000 instrumented deliveries** linked
to complete compact dispatch sidebands. No recovery/overflow failures occurred.
Raw preservation and dispatch linkage do not imply complete timing eligibility.

## Individual paired ratios

Candidate divided by baseline; no pooled/median rescue. CPU, both p99 measures
and worst delivery upper bound must each be at most 1.05 in every pair;
sampled RSS must be at most 1.10.

| Pair | CPU | Sampled RSS | p99 500/s | p99 3,000/s | Worst upper bound |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 1.02864 | 1.03321 | 1.04517 | 1.07744 | 1.07922 |
| 1 | 1.01023 | 1.03302 | 0.99464 | 0.93202 | 1.07884 |
| 2 | 1.03460 | 1.03265 | 1.01385 | 1.04835 | 1.05342 |

CPU and sampled RSS met all pairwise limits. Pair 0 burst p99 and all three
worst-bound ratios exceeded their limits. These are descriptive results of this
cohort, not valid overhead acceptance given the producer-validity limitation.
Bounds begin before producer serialization/send; they are not network latency.
Low-rate windows can include previous burst backlog. Sampled RSS is not a
continuous peak-memory measurement.

## Explicit validity limitations

Pair 0 baseline, cycle 2's 3,000/s phase attained **2,967.6302/s (98.9210%)**,
below the preregistered 99% minimum. This produces the formal `inconclusive`
metric gate, despite other explicit rejection reasons. Maximum producer deadline
lateness across cases was 13.6322 ms, within the unchanged 50 ms limit.

Timing-eligible records by case:

| Pair | Baseline | Instrumented |
| --- | ---: | ---: |
| 0 | 29,997 / 30,000 | 29,998 / 30,000 |
| 1 | 30,000 / 30,000 | 29,999 / 30,000 |
| 2 | 29,997 / 30,000 | 30,000 / 30,000 |

All nine ineligible records report `wide_clock_bracket`. The 1 ms bracket and
100% eligibility requirements remain unchanged; records are not silently
discarded or reclassified. Presence in both lanes does not establish causality
or prove the compact instrumentation harmless. The shared host's scheduling
and producer validity require separate investigation.

The pure performance subreport retains `resource_and_origin_gate=not_verified`
because that function does not audit units/origin. The enclosing independent
audit correctly records that gate as `verified`; its advancement remains
`inconclusive`. No acceptance claims were written into originating artifacts.

## Preservation and next step

Public source stayed `4dd60ba168180243f8600860330dc1afc4816ff4`; environment SHA-256
stayed `33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily collector timer remained active; pilot/observer services remained inactive.
Only this launcher's private transient units were cleaned up. Original remote
and downloaded evidence is retained. No trading, credentials, infrastructure
changes or QuantConnect sync occurred.

Recommended next work is **offline attribution of the producer shortfall and
wide-bracket intervals using this preserved evidence**, distinguishing known
clock-window facts from unobservable scheduler causes. Then define a separately
versioned validity experiment if needed. Do not replay this cohort, relax its
limits, pool away failures or deploy the candidate as accepted instrumentation.

## Offline follow-up before handoff

The exact originating file population/bytes were verified again before and
after this read-only attribution. The retained script and exclusive output are
`offline_attribution.py` and `offline_attribution.json` alongside `audit.json`.
Attribution payload SHA-256:
`0a4115d026fc520659d2266c2098b2602e55c0d993aa5759ac2d82915a604368`.
No frozen source, origin artifact, acceptance threshold or audit verdict changed.

The nine wide records comprise **five application-delivery sampling brackets**
and **four receiver-observation sampling brackets**. Offending individual bracket
widths range from **1.4457 to 25.2958 ms**. Seven records belong to the scheduled
3,000/s phase and two to the scheduled 500/s phase; eight of nine retain a true
backpressure flag. They occur in both lanes (six baseline, three instrumented).
This is a small descriptive count, not a controlled association or an overhead
comparison. Queue depth/backpressure are application observations, not evidence
of a known kernel bottleneck or exact socket-arrival time.

For the invalid pair 0 baseline burst, the target first-to-last span was
0.9996667 seconds and observed span was 1.0105707 seconds. First/last producer
lateness was 0.0872/10.9912 ms: the **10.9040 ms increase in endpoint lateness**
accounts algebraically for the attainment shortfall. This does not mean the
entire phase ran at a uniformly slower rate. Delivery index 14907 followed a
12.6967 ms inter-begin gap, of which 12.6604 ms followed the preceding send's
return. An earlier index 12121 followed an 8.5891 ms gap, with 8.5306 ms inside
the preceding send interval. Thus delays are present both within send calls and
outside them; the evidence cannot reduce the shortfall to one send-call cause.
All 30,000 phase/case deliveries were ultimately retained.

The bracket sample encloses monotonic-before, a synthetic fixture UTC function,
and monotonic-after. Wide samples identify long elapsed sampling intervals;
they are **not evidence of a UTC clock jump**. The existing evidence lacks
event-aligned scheduler/run-queue traces, cgroup throttling counters, host CPU
steal and instance credit history. Unit CPU totals and configured quotas cannot
attribute individual pauses to throttling, GIL contention, scheduling or host
pressure. Any of those explanations remains a hypothesis.

The next worthwhile step is a separately declared **validity-focused local Linux
experiment**, with producer serialization/send separation and bounded,
event-aligned scheduling/throttling observations. Freeze its observation cost
and resource policy before execution; do not retrofit this failed cohort or
increase resources merely to obtain a pass. That experiment is not started or
authorized by this offline review. Work stops here for the evening.

## October 10: additional offline producer decomposition

The original inventory was rechecked before and after analyzing all six saved
producer records. `producer_decomposition.py` and its exclusive JSON output sit
beside the prior offline artifacts; payload SHA-256:
`64c9b14d06d39091bd6826bc349b71bf007be73a4095d322ba626be7e0aba305`.
All **179,994 adjacent producer intervals** partitioned exactly, within 1 ns
floating-point tolerance, into previous preparation, previous send and elapsed
time between send return and next begin. No worker was executed.

Each case's largest inter-begin interval was **10.12–13.70 ms**, with
**97.80–99.73%** in the between-send-and-next-begin component. This component
includes bookkeeping and intentional pacing sleep as well as possible pauses;
it is not a direct measure of scheduler delay. Two selected maxima belonged to
the 500/s phase and four to 3,000/s. Preparation nearest-rank p99 was
0.3568–0.3702 ms; send p99 was 0.1169–0.1245 ms, while individual maxima reached
10.0960/10.1144 ms respectively. Percentiles here are descriptive and do not
replace the frozen acceptance estimator or rescue the inconclusive verdict.

The next probe should therefore split **pacing/bookkeeping boundaries**, rather
than duplicate preparation/send timestamps already present. See the separate
[validity design draft](../../docs/RECEIVE_LOOP_VALIDITY_EXPERIMENT.md).
Same-thread CPU deltas and bracketed cgroup counters may narrow explanations,
but cannot alone prove event-specific scheduling or throttling causality.
