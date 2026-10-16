# QCRL Project Status

**As of:** 2026-10-16 (engineering update; historical inventory below is September 23)
**Repository:** `Draupnir-Ozymandias/quantconnect` / `polymarket-martingale`  
**QuantConnect project:** 33239307  
**Current research decision:** Hold feature optimization; preserve the locked
2026Q4 prospective baseline while building execution infrastructure separately.

## October 16 recorder cohort result

The one approved Cohort02 completed six cases / **360,000 ordered frames**. Full
archive/completion/closure/native unit binding and all 208 origin-file byte checks
pass. All 13 units exited successfully; installed Linux readiness passed 1,177
(total: 1,176 pass plus one declared skip) in 201.118 s under 1-GiB readiness only.
Producer/recorder limits remained 512 MiB; all other budgets/thresholds unchanged.

**Application acceptance fails:** nine UTC brackets exceed 1 ms (worst 5.210600 ms).
Five cases fail and steady-1 is unknown. **39 RSS read brackets >5 ms** leave
resource coverage unknown, despite no explicit wait-target misses among 597 wait
receipts. All nine CPU windows and append/durability gates pass; worst durable
144.319336 ms. Inclusive CPU/sampled RSS do not establish incremental observer
cost or continuous/high-water RSS peaks (MemoryPeak absent for all 13 units).

[Full result, every unknown and evidence anchors](docs/RECORDER_COHORT_V2_RESULT_20261016.md).
Exact candidate 4926d62 / freeze 6428a09a...; independent audit complete=true,
verdict=fail. Public/source/runtime state matched at stop; no scoped unit running.
Original OOM/historical evidence and failed verdicts remain unchanged. Stop after
this approved cohort/audit: no replay, extra smoke/cohort, tuning, rollout, merge,
QC sync or orders. The preparation/historical chronology below is superseded by
this result; no unused native approval remains.

## October 15 recorder engineering history

Offline memory diagnosis/revision is complete. The 60,000-frame audit fixture
peaks above 512 MiB even alone; final suite RSS remains elevated after GC.
The [new executable packet](docs/RECORDER_COHORT_READINESS_V2_APPROVAL_20261015.md)
proposes **1-GiB readiness only**, preserving 512-MiB producer/recorder limits and
all budgets. Candidate 4926d62 / v2 freeze 6428a09a...: all 1,177 revised offline
tests pass in 154.120 s; all 520 selected source files reconstruct from the bundle.
No new staging/native unit/remote inspection occurred. Fresh read-only host checks
and new approval remain required; no native pass or headroom guarantee is claimed.

The approved successor cohort attempt **failed at native readiness**: the single
prerequisite unit was memory-cgroup OOM-killed under the unchanged 512-MiB limit
at 148.369297 s. Zero case units started. Frozen independent audit reports an
incomplete failed launch with all six case outcomes unavailable; evidence byte
integrity verifies. No replay, extra smoke or limit/threshold change followed.
Source/runtime/public context remains unchanged; no scoped unit runs, while the
stopped test unit retains its failed state. Exact active test/allocation and memory
peak are unknown. Local 1,169-test success does not substitute for native readiness.
Incremental overhead/continuous peak remain unknown; no new credit gate was added.
See [result](docs/RECORDER_PERSISTENCE_COHORT_RESULT_20261015.md) and [handoff](docs/HANDOFF.md).
Both native attempts and the revised packet execution are now recorded; see October 16 result above.

The prospectively frozen successor Linux recorder smoke **passes bounded
compatibility** after 1,156 readiness tests (1,155 pass, one declared version skip).
All 68 ordered frames, archive/completion integrity, verified closure and unchanged
2-s durability/resource gates pass; worst durability upper 0.183876711 s and zero
missed observer slots. Inclusive 60-s CPU upper fraction is 0.0048931556; sampled
RSS max 27,553,792 bytes. The one-second persistence reserve is not a guarantee.

Stopped after the single approved successor run. Public collectors and historical
failed f045b061... evidence/verdict remain unchanged. Incremental observer overhead,
continuous RSS peak, credit balance and producer internal sleep retries remain
unknown; original cohort host-context gates remain open. No replay, extra run,
six-case cohort, production/budget acceptance, orders, merge or QC sync authorized.
See [handoff](docs/HANDOFF.md), [successor result](docs/RECORDER_PERSISTENCE_SMOKE_RESULT_20261015.md)
and [preserved failed result](docs/RECORDER_ABSOLUTE_SMOKE_RESULT_20261015.md).

## Executive Summary

QCRL is currently a reproducible research laboratory for a synthetic binary
BTC direction strategy. It is not yet a Polymarket trading system. The engine
generates a direction from completed Coinbase BTCUSD bars, applies an optional
eligibility filter, simulates flat or martingale wagers in an internal bankroll,
and exports versioned QCRL metrics through QuantConnect.

The strongest surviving signal is an unfiltered, flat-sized reversal after two
same-direction daily candles. It passed a 32-quarter historical persistence
gate over 2018–2025 but did not confirm in the locked January–August 2026
sample. The combined evidence classification is `forward_degraded`, so no
indicator, regime filter, directional restriction, or sizing optimization is
currently authorized.

The next engineering phase should define executable Polymarket timing and
market mechanics without changing the signal or opening the prospective Q4
evidence.


## October 14 — Offline absolute observer integration and successor preregistration

Absolute waiting is integrated into the isolated recorder's in-unit CPU/RSS
observer through explicit prepare/consume wrappers. The receive path, producer
pacing, segmented writer, completion witnesses, public collectors and original
recorder declaration remain unchanged. Legacy consume defaults to its old observer.
The original recorder plan is still c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade.

New observer policy hash:
`bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f`.
Source-bound declaration:
`41187030fbf5825311b03c0558bd137b104b7d692078a11777b7bf4242931e15`.
Private offline receipt: `.qcrl/reviews/recorder-absolute-offline-20261014/`.
It uses the shared epoch's ceiling integer nanoseconds, fixed integer-second RSS
slots and 50-ms pre-boundary CPU lead (an explicit successor to the old 2-ms
lead). Budgets stay unchanged; the enclosing CPU delta is not normalized or
subtracted to remove the larger lead. Every endpoint gets at most one absolute
wait. Past/equal targets and >50-ms late wakes cause no read/catch-up, retain
unknowns and continue original slots. Wait/clock faults and KeyboardInterrupt
stop the observer with its prefix; ordinary read faults retain their unknown slot
without retry. Capacity/overflow remains 184 slots. Wait receipts and case/source
bindings are checked before the unchanged resource gates; known failures survive
missing evidence. No native-origin or acceptance flag is promoted.

Prospective test: one 68-occurrence, 1-Hz real-loopback compatibility run spanning
one complete 60-second CPU window, then stop for independent review. This is not
a shortened acceptance case. Only after a separate approval may the original
six serial 60,000-occurrence cases / 360,000 total run with unchanged workload,
corpus, resource limits and application budgets. No tuning or replacement.
See `docs/RECORDER_ABSOLUTE_BUDGET_PREREGISTRATION.md` for the full declaration,
missed-slot rules, bounds, stopping conditions and remaining implementation gates.

Offline verification uses injected clocks/syscalls/readers and recorder wiring;
no new native wait, Linux unit, capture, infrastructure, credential operation or
QC sync. The 68-at-1-Hz transport, native launcher routing, fresh committed
source/runtime/dependency envelope and independent launch/origin audit still need
implementation and review before requesting native authorization. Old launchers
must not be reused to claim this path ran. Earlier frozen evidence and verdicts
remain unchanged; audit each against its originating revision.


Verification: all 1,114 offline tests passed in 78.738 seconds on Intel macOS /
Python 3.14.6 with numeric-localhost fixtures permitted. All 21 new integration
and fault tests pass, including real WebSocket/recorder completion wiring with
injected syscalls/resources/Linux context. Four changed/new Python files compile
with local Python 3.8.2. This is not installed Python 3.9/Linux or native recorder
validation. No new native experiment or acceptance result exists.

## October 14 — Frozen two-run comparison completed, one unknown

Renewed direct approval covered corrected cb23c4c / execution freeze
`7c0ddaf5f697493302fd6791a64aacc68618d391a2a80c3bfd3a8dca198c3f55`.
Fresh exact source/runtime/public preflight passed. Linux Python 3.9.25 regression
passed: 1,093 discovered in 105.935 seconds, 1,092 pass and one declared skip.
The two fixed serial AB/BA units then completed once, without fatal wait or
transport faults. No tuning, catch-up, replay or additional measurement occurred.

Independent native audit
`c2a6b59f07563fbf10f8184fd09494d89f0400e6bc9917bf1337ced04a466f4d`
checks the observed host/transfer, all 23 retained evidence files, source/runtime,
readiness/release/live identities, actual limits, serialized lifetimes, journal
and receipt equality, independent timing/float/rational arithmetic and cleanup.
Private receipt: `.qcrl/reviews/wait-comparison-native-20261014LupusCompare02/`.
All private units are inactive; public/environment/source/runtime unchanged.
Original declarations, compatibility smoke and failed first readiness evidence
remain untouched. All producer/freeze authority flags remain false.

Transport is complete but scientific comparison completeness remains false:
23 observed cells, one unknown. Run-zero absolute 50-ms target was already
8.892023 ms late before invocation, following select's 58.771055-ms-late
60-second return. No absolute request was made for that cell; no replacement.
The paired 50-ms median is null. All 12 select internal retry counts remain
unknown. All 20 declared context-file observations succeeded; 16 structured
ancestry nulls retain absent root limit/disabled child cpuset files, not invented
numeric limits. Endpoint context cannot identify per-target host/signal/scheduler
causes. Quiet regression identities and RPM signature/reproducible-build limits
remain explicit in the full audit.

At 60 seconds, select lateness was 58.771055 / 60.099649 ms and absolute was
0.136841 / 0.131331 ms; paired median absolute-minus-select = -59.301266 ms.
These are descriptive serial samples with host/time confounding, no tail,
significance, exclusive-causality, recorder-acceptance or trading conclusion.
Recorder application compatibility and its budget cohort remain unfinished.
The finite comparison authorization is consumed; further native execution needs
separate approval. No new diagnostic layer, main merge or QC sync.

Full observations, identities and every unknown are documented in
[native comparison audit](docs/WAIT_COMPARISON_NATIVE_AUDIT_2026_10_14.md).

## October 14 — Comparison readiness stopped; offline test correction

Direct operator approval covered frozen b7db2c2, one Linux readiness unit and the
conditional AB/BA pair. Exact live preflight passed. Linux regression failed:
1,079 entries / 105.799 seconds, 1,077 pass, one existing skip, one import error.
Python 3.9 rejected the new test's static nested-block depth; 15 new tests never
loaded. No comparison worker, measurement, retry, replay or tuning occurred.
All 24 planned cells and their clocks/baselines/brackets/context remain unavailable;
select internal retries remain unknown. Failed unit retained with MainPID 0;
comparison units absent, public/environment/source/runtime unchanged.

The eight-file native inventory and observed host/transfer/failure/cleanup audit
are retained privately at .qcrl/reviews/wait-comparison-native-20261014LupusCompare01/.
Audit 353a9e1fa414aa8a77bf562ada0aa34bb5ff332c61d367f8d20bc055ac1af5e6
verifies failed-gate origin only, not successful comparison origin/acceptance.
Original declarations, freezes and evidence remain immutable. Offline correction
replaces nested test mocks with ExitStack; production code is unchanged. Local
Python 3.8.2 compiler checks and 15 focused tests pass; corrected Linux validation
is pending. A fresh candidate seal and approval are required before native execution.

## October 12 engineering continuation

Intel macOS migration receipt pins source `f05d5dd73b4f146f5698f58aa4c94dd6ccc480a4`:
598 retained evidence files; no jobs, secrets or cloud-sync authorization imported.
The operator reports all 1,034 bootstrap tests passed on Python 3.14.6. The
migration is curated, not a complete historical evidence copy.

Latest independently audited Linux wake diagnostic retained 11 observed targets
and one missed target; 60-second wakes were approximately 59–60 ms late.
Measurement completeness and acceptance remain false. Select-related slack is a
post-hoc mechanism hypothesis, not installed-runtime causal proof. The earlier
counter smoke missed its final deadline before a counter read; its failure and
original 50-ms budget remain unchanged. See `docs/COUNTER_WAKE_DIAGNOSTICS.md`
and `docs/WAKE_PROBE_NATIVE_AUDIT_2026_10_12.md` for frozen evidence identities.

The absolute-monotonic adapter has passed one bounded native interface smoke;
recorder integration and scheduling performance remain unverified. The active
prospective successor `docs/ABSOLUTE_SELECT_COMPARISON_V2.md` resolves select's
runtime-retry mismatch with one application call and unknown internal retry count;
v1's declaration/hash remain retained. V2 now has injected collection, pair
lifecycle, independent structural/arithmetic evaluation and bounded exclusive
publication, with both plan hashes pinned literally. The separate finite
compatibility declaration, tracked source/runtime envelope validation and injected
bounded-lifecycle rehearsal are now offline-tested (`docs/WAIT_EXECUTION_PREPARATION.md`).
The compatibility worker and production adapters now have offline fault coverage,
including bounded helper/control/journal handling and scoped lifecycle failure
retention. Authorized read-only Session Manager runtime/ABI/signal inspection
and official distribution select binary/source review are complete. Full execution
freeze `8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`
binds the original 488-file 2cb6880 candidate. Official package payload, installed
RPM-manifest hashes and source/spec/43-patch review support provenance; no independent
RPM signature verification or reproducible build was performed. Select's runtime
EINTR retries match v2's disclosure; their internal count remains unknown.
The operator subsequently authorized one finite attempt. Exact-source/live-runtime
preflight passed; Linux regression discovered 1,078 tests in 105.240 seconds,
with 1,077 passing and one existing Python 3.10+ guard skipped. The conditional
select/absolute compatibility unit observed both declared waits successfully.
A separate offline audit verified origin, byte hashes, readiness/release identity,
actual properties/resource context, valid brackets and successful completion.
Both private units are stopped and public/source/runtime state remains unchanged.
Native audit `c5f7e48f1dc97f38966a0d5c7dcd51761cf2f1f5644c09b446c018bb85f3a0cb`
verifies this finite interface compatibility only. No performance improvement,
causal scheduling conclusion, replay, comparison advancement or recorder acceptance.
See `docs/HANDOFF.md` for private receipts and limits. The single-attempt permission
is consumed; further native execution requires separate authorization.
Mac offline tests and Python 3.9 syntax checks remain distinct from these Linux results.
Recorder application compatibility and its six-case budget cohort remain blocked;
no prior verdict is repaired.

Signal research and the locked Q4 lane retain their existing guardrails. No
capture, infrastructure provisioning, credential import or QuantConnect sync is
part of this continuation. The dated September inventory/test count below is
historical and must not be read as the current engineering inventory.

## October 14 comparison transport preparation

The original 2cb6880 freeze cannot execute the comparison: its native driver supports
only tests/compatibility. A separate two-run transport, frozen-regression gate and
offline retained-evidence auditor are now implemented and fault-tested locally.
Scientific v2 hash/geometry and all prior Python implementation bytes are unchanged;
original declarations/evidence remain preserved. See
`docs/WAIT_COMPARISON_NATIVE_PREPARATION.md` for publication, interruption and
unavailable-cell semantics. No new diagnostic acquisition layer or tuning.
No comparison unit or Linux validation of this new source has run. The new execution
source is sealed as b7db2c2 (491 files), full freeze
f1339e0b54b84703368fc39efdfeb7c470ce4220bbb15d6df8284e46c0036f61.
All 1,093 local offline tests pass; direct authorization of this new execution
revision is pending before staging or Linux validation.
Current native validation remains the single compatibility smoke described above.

## Version and Contract State

| Concern | Current state |
|---|---|
| Preserved clean baseline | QCRL 2.2.0 |
| Default engine version in `config.py` | QCRL 2.3.0 |
| Latest temporal campaign version | QCRL 2.4.0 |
| Research report schema | `qcrl.research_report.v6` |
| Normalized record schema | `qcrl.experiment_record.v5` |
| Campaign manifest/state | `qcrl.campaign.v1` / `qcrl.campaign_state.v1` |
| Methodology | `qcrl.methodology.lookahead_free.v1` |
| Execution-truth schemas | market v3; normalized bundle, signal intent, binding, and replay result v2; source, source bar, signal decision, book, raw bundle, raw/normalized book sequence, raw slug resolution, discovery, live inventory, latency policy/result/batch, phase-capture protocol/state/status/worker report, phase stability, cross-market phase, platform settlement, and Binance resolution/reconciliation contracts v1 |
| Snapshot taker replay | result v2; request / policy / example v1; mechanics-only |
| Test suite | 235 deterministic tests passing |

Versioning is functional but not yet fully normalized: temporal manifests pin
2.4.0 while the manual default remains 2.3.0. Historical manifests explicitly
pin their own versions, so this does not alter completed evidence.

## Implemented Architecture

### Algorithm path

```text
QuantConnect BTCUSD minute data
  -> timeframe consolidator (5m / 15m / 1h / 1d)
  -> prior-state entry decision
  -> prior-state eligibility-filter decision
  -> observational regime capture
  -> synthetic binary outcome from bar open/close
  -> stake and risk accounting
  -> statistics, metadata, canonical report, ObjectStore/API metrics
```

Pre-evaluation seed bars can initialize state without entering signals,
statistics, risk, or profit. This is used to preserve two-bar signal memory at
quarter boundaries.

### Entry models

- Fixed UP/DOWN bias
- Previous-candle continuation
- Previous-candle reversal
- Candle-streak continuation or reversal
- EMA trend
- MACD trend
- RSI mean reversion

### Eligibility filters

- None
- EMA trend alignment
- ADX trend strength
- ATR volatility bounds

### Observational regime models

- None
- Prior-return sign (`roc_sign`) with configurable lookback and threshold

Regime models record context only. They cannot approve, reject, or resize a
trade.

### Sizing and risk

- Flat stake
- Martingale stake with configurable multiplier
- Bankroll, drawdown, ruin, recovery depth, wager escalation, and streak
  tracking

### Research and orchestration

- Guarded Git/QuantConnect synchronization through `synch.sh`, including a
  read-only upload plan, per-file enforcement of the 64,000-character limit,
  and a runtime-only staging tree that excludes repository tests from QC
- Resumable, rate-aware QuantConnect API campaign runner
- Authoritative API collection and provenance checks
- Cohort ranking and paired flat/martingale validation
- Stability, directional-cohort, gate-attribution, side-attribution,
  temporal-persistence, cross-regime, historical-forward, and diagnostic
  synthesis engines
- Versioned JSON evidence and report contracts under ignored `.qcrl/` state

## Operational Status

- 13 completed campaign families contain 160 collected cases.
- No current campaign case is failed or incomplete.
- 136 newer cases explicitly record `metrics_source=quantconnect_api`.
- 24 early baseline/Stage-1 cases predate that field but retain API collection
  timestamps and completed validation artifacts.
- One 2026Q4 prospective case is pending by design and must remain unexecuted
  until its evaluation window is complete.
- Local Git remains authoritative; GitHub and QuantConnect synchronization is
  performed only from committed, tested state.
- The durable live inventory declares and verifies 35 artifacts. September 15
  and 18 have complete promoted early/middle/late evidence; September 20 and 22
  retain promoted early/late evidence with middle explicitly missing.
- The coverage-aware cross-market analyzer uses 10 sequences across four
  markets, preserves partial cells without imputation, and flags one degraded
  September 18 late-capture cadence.
- The fixed latency batch covers all 10 sequences and 60 assumed arrivals. All
  rows select a book, all mechanics reject unknown delay/order-age state, and
  six rows additionally reject stale exchange-book timestamps.
- Four public settlement records report two Up and two Down winners. Each
  latest observed book favored the eventual platform winner, without implying
  signal accuracy or fills.
- Eight exact Binance one-minute boundary candles independently reproduce all
  four platform outcomes (4 matches, 0 mismatches). This supports public-source
  consistency, not an audit of Polymarket's internal oracle process.
- A local capture worker now provides bounded, deadline-aware retries for
  transient acquisition failures. Contract and timing failures remain
  non-retryable.
- The September 25 daily market is locked prospectively as the first member of
  the next cohort. Its three one-date launchd declarations are generated from
  the versioned protocol and loaded. A launchd GUI-domain network smoke resolved
  the exact market with exit code 0. The jobs use `caffeinate` during execution;
  explicit host wake coverage remains required before each target.

## Research Findings

### Baseline signal and capital recovery

The original 2022–2025 EMA-filtered flat/martingale baseline rejected the
signal+sizing pair:

- Flat final stability score: 34.58, classified fragile.
- Martingale final stability score: 20.26, classified fragile.
- Recovery dependence: high.
- Risk amplification: extreme.
- Martingale sizing is rejected and remains closed to optimization.

### Directional generator screen

| Generator | Aggregate profit | Profitable years | Decision |
|---|---:|---:|---|
| Candle streak | +490 | 4/4 | Hold for neighborhood validation |
| RSI mean reversion | +70 | 3/4 | Reject as fragile |
| MACD trend | -250 | 2/4 | Reject |
| EMA trend | -410 | 0/4 | Reject |

One of four tested generators survived to follow-up (25%). This is a research
progression rate, not a prediction-accuracy statistic.

### Candle-streak length neighborhood

- Length 2 was the strongest sufficiently sampled core candidate.
- Lengths 1 and 3 supplied positive two-sided neighborhood support.
- Length 4 deteriorated.
- Lengths 5 and 6 were too sparse for selection.
- Longer streaks were not monotonically more predictive.

The selected generator is therefore:

```text
BTCUSD / 1d / candle_streak / length=2 / reverse / both sides / flat $10
```

### Filter results

| Filter test | Finding | Decision |
|---|---|---|
| ADX 14 / 25 | -280 profit delta; -0.20 percentage-point win-rate delta; improved 0/4 years | Reject |
| ATR 14 / 1–10% | Apparent +70 and +0.69 points came entirely from warmup exclusions | No active effect |
| ATR lower bound 2.5% | -140 versus warmup-only | Reject |
| ATR lower bound 3.0% | -160 versus warmup-only | Reject |
| ATR upper bound 5.0% | -110 versus warmup-only | Reject |
| ATR upper bound 6.0% | -40 versus warmup-only | Reject |

ATR telemetry covered 660 signal-time observations with a pooled prior-state
range of 1.90%–8.50%, but every tested active bound underperformed the
warmup-only comparator. Zero active eligibility filters are approved.

EMA 5/10 remains a legacy baseline/default configuration, not an approved
current filter. Manual runs are therefore potentially misleading unless they
use a versioned manifest.

### Directional-side findings

```text
2018–2021: UP dominant
2022–2025: DOWN dominant

pooled UP:   +600 | 54.66% | 644 trades | profitable 5/8 years
pooled DOWN: +550 | 53.91% | 703 trades | profitable 5/8 years
combined:  +1,150 | 54.27% | 1,347 trades | profitable 7/8 years
```

Leadership changes by era. Static UP-only and DOWN-only restrictions are both
rejected; the signal retains both directions.

### Prior-state ROC regime hypotheses

The 20-day return-sign observer was tested without filtering trades.

1. Trend alignment produced a +3.81-point pooled edge but supported only five
   of eight years versus the required six: rejected.
2. A post-hoc nonpositive-state advantage was locked for January–August 2026.
   All evidence-size checks passed, but the favored and comparison states both
   produced 50% win rates and zero profit after readiness. UP contradicted the
   hypothesis while DOWN supported it: rejected.

No ROC regime gate is approved. Regime-hypothesis success rate: 0/2.

### Historical temporal persistence

The untouched length-2 signal passed all predeclared 2018–2025 quarterly gates:

| Metric | Result |
|---|---:|
| Profitable quarters | 25/32 (78.13%) |
| Trades / wins | 1,352 / 733 |
| Weighted win rate | 54.22% |
| Aggregate flat profit | +1,140 |
| Positive rolling four-quarter windows | 27/29 (93.10%) |
| Quarterly win-rate standard deviation | 6.13% |
| Maximum quarterly drawdown | 130 |
| Maximum loss streak | 8 |
| Estimated aggregate break-even friction | 8.43% of base wager |
| Top-four positive-profit concentration | 32.85% |

At 2.5% constant friction, aggregate profit remained +802 and 23/32 quarters
remained profitable. This friction model is hypothetical and is not a substitute
for actual Polymarket quotes and fills.

### Locked forward evidence

January–August 2026 produced:

```text
130 trades | 61 wins | 46.92% | -80 profit
historical-to-forward win-rate change: -7.29 percentage points
approximate two-sided p-value: 0.111 (descriptive only)
```

The bridge verdict is `forward_degraded / hold_feature_optimization`. Historical
persistence passed, but forward profit, the 52% minimum forward win rate, and
the maximum tolerated three-point decline all failed.

Post-hoc localization found:

| Segment | Trades | Win rate | Profit |
|---|---:|---:|---:|
| 2026 Q1 | 52 | 38.46% | -120 |
| 2026 Q2 | 48 | 47.92% | -20 |
| July–August | 29 | 58.62% | +50 |

The improvement is interesting but cannot reverse the forward verdict because
the segments were defined after observing the aggregate. The normalized
segments differ from the original run by one trade, one win, and 10 profit due
to explicit boundary-state seeding.

## Success and Failure Summary

| Research question | Advanced | Rejected / unresolved |
|---|---:|---:|
| Initial directional generators | 1/4 | 3/4 |
| Active ATR bounds | 0/4 | 4/4 |
| Default ADX gate | 0/1 | 1/1 |
| Universal side restrictions | 0/2 | 2/2 |
| ROC regime hypotheses | 0/2 | 2/2 |
| Historical temporal gate | 1/1 | 0/1 |
| Locked forward confirmation | 0/1 | 1/1 |
| Martingale capital policy | 0/1 | 1/1 |

The project has succeeded operationally and methodologically more often than it
has succeeded at finding tradable rules. That is a healthy research outcome:
weak explanations and dangerous sizing have been rejected before deployment.

## Core Assumptions

- Coinbase BTCUSD bars proxy the underlying event.
- Markets are treated as 24/7 calendar markets.
- A direction is formed only from prior completed bars.
- Binary outcomes pay `+wager` for a win and `-wager` for a loss.
- Tied bars are skipped.
- Flat research uses a $10 wager and a $100,000 synthetic bankroll.
- Historical streak signals overlap and are not independent observations.
- Aggregated annual/quarterly metrics do not fully describe serial dependence.
- Side-specific drawdowns are independent diagnostic curves and are not
  additive.
- Warmup and pre-evaluation seed periods must remain outside scored evidence.
- Historical, post-hoc, and prospective evidence roles are not interchangeable.

## Known Gaps and Risks

1. Public Polymarket series/event discovery, market metadata, and order books
   can now be acquired, promoted, inventoried, and replayed. Twenty-seven live
   raw artifacts are durable local evidence, including complete September 15
   and 18 cohorts and partial September 20 and 22 cohorts. No trade, fill, or
   settlement data is ingested.
2. Snapshot BUY/FAK/FOK replay now estimates entry prices, depth consumption,
   fees, partial fills, and no fills. Actual matches, temporal liquidity,
   latency paths, and wallet settlement remain unmodeled. The daily capture
   omits delay and minimum-age fields, so its replay is rejected pending explicit
   evidence. Market v3 preserves unknowns and rejects malformed execution flags;
   the five-minute capture also lacks order-age evidence.
3. The signal/market binding contract now separates availability, observation,
   decision, target, and cutoff times. A pure boundary adapter now materializes
   the next UTC-day intent from prior completed bars, but no live data process
   invokes it yet.
4. Bounded public book-sequence capture now records 2–120 complete market
   bundles, with independently timed metadata and both books. It remains a
   polling record—not continuous liquidity, delay, fill, or settlement evidence.
   Exact event/market slug resolution is hashed; ambiguous events are rejected.
5. Sequence-based latency sensitivity maps declared hypothetical arrival times
   to the first observed book at or after arrival and exposes polling uncertainty.
   The fixed grid has been applied to all three September 15 phases; all eighteen
   mechanics rows reject unknown delay and minimum-age state rather than claiming
   fills. These observations do not calibrate a latency distribution.
   The batch extension applies the same grid to 10 sequences: all 60 mechanics
   rows reject unknown delay/order-age state, and six also flag stale exchange
   timestamps.
6. September 11 captured only early; September 13 captured early and late; both
   missed phases remain missing. September 15 and 18 are complete promoted phase
   cohorts. September 20 and 22 captured early and late but missed middle; all
   valid observations are promoted and the misses remain explicit.
7. Cross-market description now covers four aligned markets and 10 sequences.
   All four early books were two-sided with tight spreads, while late state was
   heterogeneous: two were one-sided, two remained two-sided, and three of four
   were one-sided or priced at a directional extreme. Displayed depth varied by
   more than an order of magnitude, so liquidity magnitude is not stable.
8. One September 18 late polling gap was 1007.056607 seconds. The artifact is
   retained as degraded-cadence evidence and is not treated as a one-minute
   trajectory. All other sequence maxima were below 5.71 seconds.
9. The scheduler produced two different middle-phase failures: September 20
   dispatched after the locked deadline, while September 22 ran inside the
   window but the default sandbox denied DNS. Codex scheduled tasks are not a
   hard real-time capture service; strict future timing requires a preauthorized
   network path and a local OS scheduler or dedicated recorder.
10. Platform settlement reconciliation is implemented for all four markets,
   and exact public Binance boundary candles independently match all four payout
   directions. This does not audit Polymarket's internal oracle or observe
   wallet redemption.
11. QCRL uses its own synthetic bankroll and submits no LEAN portfolio orders;
   standard LEAN portfolio statistics are not strategy objectives here.
12. Polymarket is not implemented as a LEAN brokerage or execution adapter.
13. Manual defaults still select EMA 5/10 and QCRL 2.3.0, while the current
   candidate is unfiltered and temporal manifests use 2.4.0.
14. The estimated 8.43% friction capacity assumes constant cost per wager and
   cannot be translated directly into expected Polymarket profitability.
15. The 2026Q4 prospective sample is future evidence and must not be run
   partially or modified after its October 1 start.

## Current Guardrails

- Do not optimize indicators, filters, regimes, sides, or martingale settings.
- Do not reinterpret the post-hoc 2026 recovery as a tradable regime.
- Do not run or modify the prospective Q4 campaign before completion.
- Do not place orders or add credentials during the next infrastructure phase.
- Continue requiring clean Git state, versioned manifests, authoritative API
  collection, evidence hashes, and explicit evidence roles.

## Recommended Next Development

Continue the read-only Polymarket execution-truth foundation while keeping
signal research frozen. Public acquisition, explicit contract-driven discovery,
immutable local raw storage, offline normalization, source contracts, boundary
signal materialization, and signal binding are implemented. Live promotion and
inventory verification are also implemented.
Daily series `41` exists but is incompatible with the current signal because
its Binance BTC/USDT feed, noon-Eastern anchor, and tie settlement differ.
Remaining work is:

1. Complete the locked September 25 early/middle/late capture without manual
   retiming; verify, promote, and analyze it only after all three phases close.
2. Lock additional published markets before their event windows, preserving the
   same geometry and treating any miss as missing evidence.
3. Decide whether to authorize a separate Binance noon-to-noon research lane;
   do not retrofit the historical Coinbase evidence.
4. Connect the boundary adapter to a read-only live data process.
5. Add shadow decisions before any authenticated order path.

The Q4 evidence lane and execution-infrastructure lane must remain independent.

## Canonical References

- `README.md` — operator workflow and campaign commands
- `QCRL_ARCHITECTURE.md` — architecture and roadmap
- `QCRL_SYNC.md` — chronological research and synchronization record
- `docs/README.md` — documentation ownership and update rules
- `docs/CAMPAIGN_REGISTRY.md` — campaign and synthesis evidence ledger
- `docs/DECISION_LOG.md` — decisions that govern current work
- `docs/HYPOTHESIS_REGISTRY.md` — supported, failed, closed, and locked ideas
- `docs/SCHEMA_CONTRACTS.md` — producer/consumer compatibility contracts
- `docs/EXECUTION_TRUTH.md` — Polymarket observation boundary and invariants
- `docs/BOOK_SEQUENCE.md` — bounded book-sequence capture and evidence meaning
- `docs/LATENCY_SENSITIVITY.md` — observed-book latency selection and limits
- `docs/CAPTURE_PROTOCOL.md` — locked phase timing and resumable capture state
- `docs/PHASE_STABILITY.md` — within-market early/middle/late description
- `docs/CROSS_MARKET_PHASES.md` — coverage-aware cross-market phase description
- `docs/LATENCY_BATCH.md` — fixed-grid mechanics across all observed phases
- `docs/SETTLEMENT_RECONCILIATION.md` — public payout and latest-book reconciliation
- `docs/OPERATOR_WORKFLOW.md` — exact Git, GitHub, QuantConnect, and campaign flow
- `campaigns/` — immutable experiment declarations
- `syntheses/` — versioned cross-campaign analysis declarations
- `.qcrl/campaigns/` — ignored local campaign state and derived evidence
- `.qcrl/syntheses/` — ignored reproducible synthesis outputs

Corrected local regression: all 1,093 tests passed in 97.249 seconds on Intel
macOS/Python 3.14.6 with existing numeric-localhost fixtures permitted. Fifteen
focused fault tests pass; Python 3.8.2 compilation reproduces the original nested
block failure and accepts the corrected files. No corrected Linux unit ran.

## Corrected offline execution candidate sealed — October 14

Exact candidate `cb23c4c2b6b2d7de76435bd6397415f4550e4727` contains only the
fault-test context-manager refactor and status updates relative to failed b7db.
All production Python and scientific plan hashes remain unchanged. Its 491-file
inventory matches exact Git blobs and retains the reviewed runtime and original
compatibility prerequisite. Full freeze:
`7c0ddaf5f697493302fd6791a64aacc68618d391a2a80c3bfd3a8dca198c3f55`.
Private controls: `.qcrl/reviews/wait-comparison-source-cb23c4c2b6b2/`.
Verification: `a445c94f0eb50f88821954d4ce3fb9ec07a447879ee8fb3b54708f3fe10c6db8`.
Later receipt-documentation HEAD does not replace this execution source.

Ready offline for a new operator-approved, fresh-stage Linux readiness attempt,
conditional on the unchanged source/runtime/public gates. Expected Linux population
remains 1,093 discovered, one existing skip. Only after a successful gate may the
unchanged two AB/BA runs execute once. No corrected source was staged or run on
Linux; no resumption, retry, replay, extra measurement or recorder cohort is
currently authorized. Original failed stage/receipts remain untouched. All freeze
and producer authority flags remain false; the failed gate demonstrates no
scientific comparison or acceptance. Obtain approval before any further native
unit, rather than reusing the failed attempt's permission.
