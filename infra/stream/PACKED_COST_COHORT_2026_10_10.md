# Packed validity-cost cohort — October 10, 2026

## Verdict

**Reject under the unchanged cost gates.** All nine cases completed and origin
and resources were independently verified. There are 11 threshold failures and
no inconclusive reasons. The earlier v1 rejection remains intact; no replay,
threshold adjustment, resource change or public rollout occurred.

## Freeze and verified evidence

- Code freeze: `7f6602a84e6f1ae2069a55678e048777a39b4591`, previously pushed
  and passed the separate native eight-message smoke.
- Plan SHA-256: `dfd19d6179100ff5de298f8a2b79bb4eea68a6217a66190712fb27260c8b121a`.
- Declaration file SHA-256: `3645be4e83014eb91b35b0a7b16c004dcb50e5073e6baa0fae013cb40e50325d`.
- Fresh Ohio stage: `/var/lib/qcrl-stream/receive-loop-packed-xcpuwfvo`.
- Linux prerequisite: 845 tests ran successfully, one skipped.
- Independent inventory byte anchor, obtained directly from Ohio:
  `b670a45edfada42ce8685a3a2e97efae54f6d082ef44da9b5490805943b719fc`.
- Local immutable evidence and audit receipt:
  `.qcrl/reviews/packed-cost-cohort-20261010-dSUeZ3hj/`.
- Independent audit SHA-256:
  `dff05667c263e859566d1d334c48446ebda6f8a866411a5c2ee12f884dfc06e5`.

The versioned offline auditor matched exact bytes/population for 179 evidence
files before and after analysis, verified the frozen source/input links, 270,000
ordered raw occurrences, packed-wrapper/canonical-core equality, native counters
and CPU pairs, and 19 distinct units. Live PID/boot/cgroup links, commands,
quotas/security properties, ordering and resource-window enclosure were verified.
Snapshots were outside the timed collection windows; no missing data was treated
as zero or as successful evidence.

## Fixed paired comparisons

Each ratio compares against its own round's control. Tail columns show the
largest individual phase-window additions, not pooled percentiles. Every one of
the 12 phase windows is separately gated.

| Round (zero-based) | Lane | CPU ratio | RSS ratio | Largest added p99 | Largest added worst |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | pacing | 1.039 | 1.014 | 0.039 ms | 3.679 ms |
| 0 | full | 1.274 | 1.046 | 31.319 ms | 37.156 ms |
| 1 | pacing | 1.006 | 1.016 | 0.379 ms | 2.769 ms |
| 1 | full | 1.280 | 1.044 | 1.407 ms | 5.357 ms |
| 2 | pacing | 0.978 | 1.014 | 2.673 ms | 4.923 ms |
| 2 | full | 1.380 | 1.043 | 2.274 ms | 5.394 ms |

Limits remain CPU <=1.05, sampled RSS <=1.10, phase added p99 <=1 ms and added
worst <=5 ms. All pacing CPU comparisons and all six RSS comparisons passed.
Full CPU failed in all three rounds. Each full comparison failed a phase p99
and worst gate; pacing round 2 failed one phase p99 gate. Full round 0 also
failed the absolute <=1 ms inline CPU-stamp enclosure gate: one bracket was
26.294 ms wide, at sequence 13917's ending stamp. No brackets exceeded 1 ms
in the other two full cases. All other absolute case gates passed.

## What changed, and what remains unresolved

Relative costs are lower than the previous cohort: pacing CPU ratios were
1.266–1.544 previously versus 0.978–1.039 here; full CPU ratios were 1.643–1.966
versus 1.274–1.380 here; full RSS ratios were 1.342–1.349 versus 1.043–1.046.
This is descriptive evidence consistent with lower allocation/validation cost,
not a randomized cross-experiment causal estimate. Host timing and baseline
measurements differ between the two cohorts. A pacing subcomparison passing is
not acceptance of the rejected full experiment.

Both actor paths contribute to full CPU cost. Observed full observer CPU was
0.225–0.228 s, versus 0.050–0.059 s for control observers; full worker CPU was
2.196–2.329 s versus 1.778–1.938 s for control workers. These are measured actor
totals, not isolation of individual helper-call costs. Sampled worker cgroup
throttled-period and throttled-usec counters did not increase in any full case.
That does not exclude CPU-credit, shared-host or scheduling effects, nor explain
the wide clock bracket causally. RSS remains summed sampled process-lifetime
high-water, not current RSS or a collection-window peak.

## Public state and recommended next step

Before/after public state matched: checkout
`4dd60ba168180243f8600860330dc1afc4816ff4`, environment hash
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`,
daily timer active, pilot/observer inactive. Only cohort-owned units were stopped.
No trades, Polymarket credentials, infrastructure changes or QuantConnect sync.

Next: offline component-cost attribution for CPU stamps/validation and the
counter reader. If reducing cadence is necessary, explicitly declare the lost
per-step or per-100-ms diagnostic coverage in a new experiment before execution.
Do not silently downsample, upgrade resources to seek a pass, relax the fixed
gates, or replay this cohort. Packed full instrumentation remains unaccepted.
