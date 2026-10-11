# Minimum useful research recorder contract — draft v1

Identity: `qcrl.minimum_useful_research_recorder.draft.v1`.
Status: proposed design, not executable declaration, acceptance or rollout.
The companion machine-readable draft is
`execution_truth/specs/minimum_useful_research_recorder_draft.json`.

## Purpose and non-goals

Support reproducible, one-second-binned descriptive research on one locked BTC
five-minute market's two outcome tokens. Preserve subsecond observations, but do
not assert subsecond physical lead/lag, profitable entries, fills or queue rank.
One-second bins are an initial analytic scope, not a chosen trading strategy.
Daily, 15-minute and other assets require separate terms/timeframe declarations.

This contract answers "is the recording usable for this research question?".
It does not replace the frozen 5%-overhead probe contract, change any rejection,
relax the delayed-binding freshness policy, or authorize orders. No existing
collector is accepted merely because its code has some required capabilities.

## Non-negotiable evidence

- Pin market/condition/token IDs, explicit start/end and settlement terms, exact
  source/dependency versions, runtime, observer/boot clock domain and capture plan.
- Retain every supported text message returned by the library unchanged, including
  duplicates, batched arrays and malformed/unknown payloads. No filtering of raw
  evidence for cleaner statistics. Binary/oversized/quota/error paths remain
  explicit unsupported/partial failures; no promise of all network bytes.
- Keep ordinal/raw hashes, row/segment chains, exclusive publication, immutable
  manifests and an independent verification pass. A local hash is not a signature.
- Preserve subscription, reconnect/gap/close, both-token initial book witnesses,
  clock anomalies and terminal status. No carrying book validity across gaps.
- Bound storage, encoded record size, workers and process resources. Budget stops
  preserve prefixes and fail lifecycle acceptance; no deletion to regain health.
- Separate capture completion, archive verification and remote replication.
  Heavy verification/analytics run after capture workers, not on their read path.

Open-socket time and two book witnesses do not prove venue completeness. Gaps and
unknown fields stay in denominators and eligibility decisions, not silently omitted.

## Timing and durability boundaries

Record application-return UTC with monotonic bracketing before classification.
Keep source timestamps unmodified, typed by event; unknown/future/invalid source
times remain unknown. Book last-change age is not interchangeably message age.
Neither timestamp interpretation nor clock alignment is inferred from a field name.

Append-completion means the compressed writer accepted the complete encoded row,
not externally readable bytes or durable disk. A separate bounded receipt must
link that completion to the raw ordinal/hash and local clock domain. Successful
fsync watermarks bind the highest fully written ordinal covered by the barrier,
with barrier entry/return brackets. Visibility/sealing/S3 publish times are separate.

Never subtract monotonic clocks across hosts or boots. Compare UTC across sites
only with an independently retained clock-offset/uncertainty bound. Wide/overlapping
clock brackets are interval evidence, not guessed exact points. Unknown precision
can limit research eligibility without invalidating otherwise intact raw archives.

Power loss can discard unsynced data. A fsync cadence requests durability, not a
guaranteed maximum completion latency. After an abrupt exit, bytes past the last
verified durable watermark and missing final manifests remain uncertain/partial.
Do not weaken the existing sync cadence merely to meet a performance target.

## Proposed absolute application budgets

These are prospective design assumptions for one-second descriptive research,
not exchange rules, fitted thresholds or proof of strategy sufficiency. Publish
them unchanged with the source/input freeze before measuring the actual recorder.

| Metric | Proposed limit | Reason / measurement |
| --- | --- | --- |
| Return to append-completion upper bound | p99 <=100 ms; worst <=1 s | 10% of a one-second bin at p99; retain every outlier |
| Return to successful durable-watermark upper bound | worst <=2 s | Existing one-second requested sync cadence plus one-second completion allowance; must be observed, not assumed |
| Declared local UTC bracket | width <=1 ms for timing-qualified rows | Bound local sampling precision, not global clock accuracy |
| Localhost delivery fidelity | Every injected supported occurrence retained once per delivered occurrence, in FIFO order | Duplicates remain separate occurrences; no unexplained loss |
| Combined recorder CPU | <=70% of effective declared quota in each complete non-overlapping 60-s window | Preserve 30% nominal headroom; include writer/control actors, not offline audit |
| Resident memory | Every retained 1-s current-RSS sample <=80% of unit memory limit | Headroom target; report coverage, gaps and lifetime high-water separately |
| Archive/verification | Exact occurrence/byte/source matches; no missing required receipts | Integrity gate, not a percentile |

Clock-eligible timing rows and all-raw population counts are separate. Performance
acceptance requires a completion witness for every supported occurrence; failed,
missing or ineligible witnesses cannot improve p99 by exclusion. They make the
corresponding timing gate failed or unknown, with all known failures retained.
Use nearest-rank percentiles per declared lifecycle and per low/burst phase, not
pooled medians. A missing denominator, quota, actor binding or clock field is unknown.

The CPU denominator is elapsed window time times declared effective quota in core
units. Actor allocations, ancestry/shared cgroups, instance credit policy and
concurrency must be pinned; never count shared groups twice or mistake quotas for
guaranteed host capacity. One-second RSS samples are not continuous peaks. Budget
pass also requires no resource-limit/OOM exit or observation overflow; quota-
throttling counters are disclosed, not proof of event-specific causality.

An internal library queue setting is a flow threshold, not a hard record cap.
Report measured queue/lag witnesses if present; an absent internal queue metric
does not become zero. No new asynchronous queue is needed for initial testing.
If one is later added, its explicit cap, overflow and crash semantics need a new
design review. End-to-end completion lag tests remain mandatory either way.

## Research eligibility and outcomes

Keep distinct outcomes: archive verified (possibly with gaps), application-budget
pass/fail/unknown, and eligible descriptive windows. A gap, unsupported message,
unknown clock or missing initial book invalidates dependent intervals, not the
entire historical archive. A close market snapshot does not repair intervening gaps.
State reconstruction requires its own reconciliation contract before book-derived
feature conclusions. This recorder alone does not create a trusted order book.

No venue-to-host network latency, continuous delivery, execution safety, strategy
profit or authenticity claim follows from any of these outcomes. Source-age
observations remain descriptive until source timestamp semantics and clocks are
established. This design adds no new entry-freshness threshold or live signal lane.

## Small finite validation and stopping rule

1. Offline witness/lifecycle tests: append failure, fsync failure, crash prefix,
   reconnect, duplicate messages, clock faults, terminal quotas and observer failure.
2. Freeze an actual-recorder localhost test with existing 500/s low and 3,000/s
   burst rates, representative retained payloads and enough fixed repeats for
   complete 60-s windows. Declare corpus hashes, ordering, quotas, durability and
   witness coverage before execution. It is not the no-socket producer experiment.
3. Independently verify origin/source/occurrences and the application gates.
   Failures stay immutable; changes require a different experiment identity.
4. If the actual recorder meets this scope, stop optimizing detailed probe cost
   as a prerequisite to descriptive research. Consider a small locked public
   cohort only after separate review and authorization.

At most one implementation/test cycle is the initial timebox. If it fails, review
which research question the failure actually blocks before another optimization.
Migration or split-process logging is a measured alternative, not a default next
task. This draft has no launch commands, capture calendar or execution authority.
