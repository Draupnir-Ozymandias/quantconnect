# Packed-worker + pinned-observer combined-cost declaration

This distinct experiment follows the rejected packed-worker/original-observer
cohort. It does not rewrite either predecessor rejection or promote the finite
reader-component speedup to full performance acceptance.

## Frozen controls and intervention

Nine cases in three rotated rounds: control/pacing/full, pacing/full/control,
full/control/pacing. Each case retains six 4-second 500/s and 1-second 3,000/s
phases, 30 seconds and 30,000 deterministic raw deliveries; no sockets. Packed
worker representation, generator, operation sequence, inline validation and
post-window partition validation remain unchanged. Wall calls stay 4/7/11 per
step; full takes two same-thread CPU stamps per step. No diagnostic downsampling.

Only full observer reader acquisition changes to the source-bound pinned adapter.
Its explicit expected worker identity and before/after path/identity checks,
bounded reads, descriptor ownership and retained failed attempts remain mandatory.
First pin/open cost stays inside the first acquisition bracket and observer CPU
window. Descriptor cleanup is inside that window before acknowledgment; cleanup
receipt persistence and snapshot serialization are afterward. Control/pacing keep
the same absolute observer wake schedule without constructing a counter reader.
The 100-ms observer grid and skip/no-catch-up rules are unchanged.

Worker/observer quotas stay 100%/25%; test prerequisite quota 75%; each unit
512 MiB, 32 tasks, 120 seconds, same sandbox settings. Resource accounting retains
whole actor timed process CPU and summed sampled Linux process-lifetime high-water
RSS maxima; no current-RSS or collection-window peak claim, no shared-page dedup.

## Unchanged acceptance and integrity

CPU ratio <=1.05 and RSS ratio <=1.10 against the same round's control. Each of
12 individual phase windows retains added p99 <=1 ms and worst <=5 ms. All
absolute attainment/lateness, CPU-clock brackets, native required counters,
identity/reset, raw population and encoded-sideband bounds remain. No pooling,
retry/replay, resource adjustment or retrospective threshold change. Known failures
reject; missing required evidence is inconclusive, retaining known failures.

The 32 MiB sideband basis remains canonical worker core without raws plus observer
core; duplicate packed-wrapper serialization is excluded. The pinned observer core
now includes method and cleanup metadata, which is included in that basis.
The cleanup artifact links through acknowledgment and final core; errors, remaining
owned handles, method drift or an out-of-window close cannot pass verification.

## Separate machinery and source freeze

New cost/trial/launcher/auditor schemas use private
`/var/lib/qcrl-stream/receive-loop-pinnedcost-<suffix>` stages and
`qcrl-pinnedcost-<suffix>` units. Fixture-only and predecessor modules remain
unchanged. Production staging requires live bindings; fixtures cannot count as
real cohort evidence. The declaration binds policy, both adapter methods, exact
source bytes and the prior rejection audit. All execution/combined-benchmark,
cost-acceptance, public-rollout and order flags remain false until separate work.

Launcher requires explicit execution, clean qcrl-owned private Git source, matching
declaration, four GiB free, no adopted evidence/units and unchanged public service
prerequisites. It seals live PID/boot/cgroup links before collection, captures actual
properties before retiring only its units, preserves failures and never restores
or changes public collectors automatically.

Independent audit requires originating inventory byte anchor and source commit,
checks exact artifact population before/after analysis, frozen input/source links,
ordered raws, packed core, cleanup/acknowledgment, live unit limits/security/windows,
counter and CPU intervals, then applies unchanged paired gates. A pass advances
only to a separately declared validity workload, not recorder or trading approval.

## Pending execution gates

Offline correctness/fault verification, saved declaration and source snapshot,
commit/source-freeze, and fresh native production-machinery smoke precede a
separately authorized finite cohort. The prior native adapter smoke verifies its
tested behavior, not the newly declared production path or this experiment's cost.

Declaration-time offline verification: **912 local regression tests passed**,
including 31 dedicated cost/trial/launcher/auditor tests. No combined-cost cohort
had been executed when this source-bound specification was saved.
