# Native validity-probe cost cohort — October 10, 2026

## Verdict

**Reject under the unchanged v1 cost gates.** Collection and independent
origin/resource verification succeeded; this is not an incomplete capture or
an inconclusive evidence result. There are 31 paired threshold failures and no
inconclusive reasons. No retry, replay, threshold adjustment or public rollout
occurred. This synthetic result is not recorder-overhead, exchange-fill or
profitability evidence.

## Freeze and execution

- Source commit: `d769b7929f8bd242a7d7ddc27a760c91be5186e6`, pushed before execution.
- Plan SHA-256: `590e270d3766437712cdfbff588278287f1126bb442f0e8959c350e5f7b04235`.
- Preregistration file SHA-256: `50ca620173d5fed810b1fcbbca8e54885adf770a32c7ba3872db29131ac6eca1`.
- Fresh Ohio stage: `/var/lib/qcrl-stream/receive-loop-validity-NRLdaftG`.
- Linux prerequisite: 792 tests ran successfully, one skipped.
- All nine cases completed: three rounds, rotated control/pacing/full order,
  30 seconds and 30,000 ordered synthetic deliveries per case. No sockets.
- Worker CPU quota 100%; observer 25%; test unit 75%. Each retained its
  fixed 512 MiB, 32-task, 120-second limits and sandbox settings.

The independently obtained originating inventory byte SHA-256 is
`c87be342d895b8b870472f97f29620a57977a03bbaa0a9b58d0eef7fa4d13908`.
Local preserved evidence, source Git bundle and independent audit are under
`.qcrl/reviews/validity-cost-cohort-20261010-MeHlIexy/`.
The audit receipt is `independent-audit.json`, audit SHA-256
`17d5d12509fb4a535ed90fd2d6da273fdb9833a3cb11ea6e30d4641cddbd236b`.

## Independent verification

The offline versioned auditor matched exact population and bytes for 170
originating evidence files, checked the manifest's frozen source/input hashes,
verified 270,000 ordered raw occurrences and all required full-lane CPU pairs
and counter records, and verified 19 distinct originating units (one test unit
plus nine worker/observer pairs). Checks included live PID/boot/cgroup bindings
sealed before collection, marker linkage, commands, quotas, security settings,
unit ordering, collection-window enclosure and process/whole-unit CPU bounds.
Origin bytes were checked again after analysis.

Every case passed its absolute completeness, phase-attainment, lateness,
clock-bracket and counter-availability gates. Rejection came from paired costs
and phase-tail regressions, not missing identities or lost deliveries.

## Paired costs

Ratios are against the same round's control. Added tails below are the largest
individual phase-window differences within that comparison, **not pooled
percentiles**. The auditor evaluates each of the 12 phase windows separately.

| Round (zero-based) | Lane | CPU ratio | RSS ratio | Largest added p99 | Largest added worst |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | pacing | 1.544 | 1.084 | 1.964 ms | 8.460 ms |
| 0 | full | 1.966 | 1.344 | 4.622 ms | 24.584 ms |
| 1 | pacing | 1.266 | 1.085 | 0.931 ms | 4.244 ms |
| 1 | full | 1.643 | 1.342 | 3.076 ms | 17.683 ms |
| 2 | pacing | 1.352 | 1.086 | 11.411 ms | 17.801 ms |
| 2 | full | 1.876 | 1.349 | 4.407 ms | 19.493 ms |

Fixed limits: CPU ratio <= 1.05; RSS ratio <= 1.10; added phase p99 <= 1 ms;
added phase worst <= 5 ms. All six CPU comparisons failed. Full-lane RSS
failed in all three rounds; pacing RSS passed. Pacing round 1 passed its tail
comparisons but still failed CPU.

RSS is the sum of two actors' sampled Linux process-lifetime high-water maxima,
without shared-page deduplication. It is not current RSS or a collection-window
peak. CPU is measured inside declared actor windows, including common samples;
snapshot serialization/analysis are outside. Shared-host scheduling remains a
limitation: tail associations do not establish a specific scheduling cause.

## Public state and next step

Before and after public state matched exactly: checkout
`4dd60ba168180243f8600860330dc1afc4816ff4`, environment hash
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`,
daily collector timer active, stream pilot and observer services inactive.
Only cohort-owned units were stopped. No infrastructure/resource changes,
trades, Polymarket credentials or QuantConnect synchronization were involved.

Recommended next step: offline design of a lower-allocation, lower-clock-call
validity probe and isolated correctness/fault tests. Explicitly distinguish
reduced diagnostic coverage from equivalent semantics. Then separately version,
preregister and source-freeze a new cost experiment; do not replay this cohort
in search of a pass or relax v1 thresholds retrospectively. The current probe is
not accepted as low-perturbation instrumentation for the intended workload.
