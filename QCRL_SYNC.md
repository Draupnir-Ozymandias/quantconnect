# QCRL Sync Log

**Updated:** 2026-09-07
**Latest checkpoint:** 2026-09-07 QuantConnect Push Preflight
**QCRL baseline:** 2.2.0  
**Status:** Active research

---

> **Chronological provenance, not current truth.** This file is append-only and
> preserves the terminology, schemas, plans, and conclusions that existed at
> each checkpoint. Older sections headed “current” are historical snapshots.
> Use [`QCRL_PROJECT_STATUS.md`](QCRL_PROJECT_STATUS.md) for the current verdict
> and [`docs/README.md`](docs/README.md) for the documentation map.

## Navigation

- Integration and campaign-runner foundation: lines/sections beginning
  `2026-08-07 integration checkpoint` through `API Boundary`
- Architecture/discovery specification: `Workstream A`, `Methodology Boundary`,
  `Engine-to-Discovery Data Contract`, and `Workstream B`
- Research checkpoints: the dated blocks under `Current Handoff State`
- Durable campaign and synthesis summary:
  [`docs/CAMPAIGN_REGISTRY.md`](docs/CAMPAIGN_REGISTRY.md)
- Current decisions and closed hypotheses:
  [`docs/DECISION_LOG.md`](docs/DECISION_LOG.md) and
  [`docs/HYPOTHESIS_REGISTRY.md`](docs/HYPOTHESIS_REGISTRY.md)

Proposed Consensus, Cluster, Archetype, and Confidence engines below are design
notes unless the current architecture/status explicitly identifies an
implementation. They are not part of the present execution path.

## Purpose

This file synchronizes the two QCRL workstreams without merging their responsibilities.

- **Workstream A — Architecture / Engine** owns how experiments are defined, executed, validated, normalized, persisted, retrieved, and audited.
- **Workstream B — Analysis / Discovery** owns what valid experiment records mean across years, parameter regions, strategy families, and behavioral cohorts.

The architectural boundary remains:

> **Architecture determines where trustworthy experiments live.  
> Discovery determines what trustworthy experiments mean.**

## 2026-08-07 integration checkpoint

- The local project is now a real checkout of
  `Draupnir-Ozymandias/quantconnect`, with QuantConnect project `33239307`
  configured as the execution environment.
- Commit `564fc93` establishes the guarded `synch.sh` workflow, local test
  suite, `.gitignore`, and removal of obsolete duplicate source artifacts.
- The first named LEAN CLI cloud backtest compiled and completed successfully:
  `QCRL-2.2.0-CLI-Baseline-2024-Flat`, backtest
  `1c52783e44f28744737a541ecbe6829b`.
- The run created the canonical ObjectStore report
  `BTCUSD_1d_candle_streak_flat_20260807T170817Z_0300ddfb718e.json`.
- LEAN reported zero orders and zero standard portfolio performance because
  QCRL simulates its bankroll internally. Therefore LEAN's built-in portfolio
  optimization objectives are not valid QCRL objectives.
- CLI backtests now receive the Git commit, Git branch, and campaign ID as
  runtime provenance. Methodology, look-ahead, and validation status are also
  normalized into each new record.
- Direct cloud ObjectStore download is unavailable under the current
  QuantConnect license. Retrieval remains available inside QuantConnect through
  `ExperimentStore` and `ResearchTools`.

The resulting architecture target was a QCRL campaign runner that submits parameter
sets through the CLI/API, reads QCRL-native report metrics, validates expected
runs and pairs, and ranks multi-parameter campaigns without relying on LEAN's
standard portfolio statistics.

### Campaign runner implementation

The first campaign-runner layer is now implemented locally:

- `qcrl_campaign.py` expands version-controlled manifests into deterministic
  cases and submits them sequentially through `lean cloud backtest`.
- Campaign execution requires a clean Git tree and injects the commit, branch,
  and campaign ID into every run.
- `.qcrl/campaigns/{campaign_id}/state.json` provides resumable status; per-run
  CLI output is retained locally under the same ignored campaign directory.
- QCRL metrics are published as LEAN custom summary statistics, providing an
  API-readable result channel independent of ObjectStore downloads.
- The collector authenticates with `QC_USER_ID` and `QC_API_TOKEN`, reads each
  backtest through `/backtests/read`, and stores only parsed QCRL metrics in
  local campaign state.
- Validation checks expected cases, failures, missing metrics, flat/martingale
  pair completeness, signal-sequence invariants, and the declared objective.
- `campaigns/btcusd_1d_baseline_2022_2025.json` defines the first eight-run
  clean control campaign.

The cloud integration gate passed on 2026-08-07:

```text
case_id: 2022-flat-a2347e32
backtest_id: 959c6f2af8eb4844493cef66b907f56f
trades: 71
wins: 33
losses: 38
win_rate: 46.478873%
net_profit: -50
max_drawdown: 150
max_loss_streak: 6
risk_adjusted_score: -0.04730368968779565
tail_risk_score: 178
```

Cloud compilation, deterministic naming, provenance parameters, canonical
ObjectStore persistence, QCRL custom summary statistics, backtest-ID capture,
and resumable state all passed. QuantConnect's terminal table wraps long custom
statistics, so CLI parsing is treated only as a preview. The case remains
`completed` until the API collector receives the full required metric set.

The complete eight-run control campaign subsequently passed collection and
validation:

```text
expected cases: 8
failed: 0
incomplete: 0
uncollected: 0
pair issues: 0
QCRL metrics per case: 22
```

One submission encountered QuantConnect's `Too many backtest requests` API
throttle. Manual retry completed the campaign without duplicate successful
runs. As of 2026-08-08, the runner enforces a 30-second minimum interval between
submission start times and automatically retries recognized rate limits with
exponential delays of 30, 60, 120, and 240 seconds, capped at 300 seconds.
Throttle events and policy values are persisted in campaign state; each retry
is appended to the case log. Non-rate-limit failures continue to stop the
campaign immediately.

### Split cohort rankings

As of 2026-08-08, campaign validation no longer combines flat and martingale
runs into one leaderboard. Ranking definitions are explicit in the campaign
manifest and are evaluated only against matching cohorts.

The flat signal cohort uses:

```text
flat_profit_drawdown = net_profit / (1 + max_drawdown)
```

The martingale capital cohort uses the existing recovery-aware QCRL score:

```text
martingale_recovery_risk = risk_adjusted_score
```

The clean control rankings are:

```text
Flat signal
1. 2025  score  2.35294117647
2. 2024  score  1.14754098361
3. 2023  score  0
4. 2022  score -0.331125827815

Martingale capital
1. 2024  score 0.397350993377
2. 2023  score 0.357615894040
3. 2025  score 0.187566988210
4. 2022  score 0.074711342540
```

Campaign state now stores a deterministic case-set hash separately from the
full manifest hash. Analysis-only or operational manifest revisions preserve
collected runs when the case set is identical. Parameter changes are rejected
and require a new campaign ID.

### Paired capital comparison

Campaign validation now emits both a human-readable paired report and the
structured local artifact:

```text
.qcrl/campaigns/{campaign_id}/paired_comparison.json
```

Artifact schema:

```text
qcrl.paired_comparison.v1
```

The clean control comparison is:

```text
Year  Flat PnL  Martingale PnL  Profit Delta  DD Multiple  Wager Multiple  Label
2022       -50             330          +380          4.20            64  recovery-dependent-profit
2023         0             270          +270          1.67            16  recovery-dependent-profit
2024        70             300          +230          2.50            16  signal-supported-profit-amplification
2025       120             350          +230          6.20            32  signal-supported-profit-amplification
```

Every paired artifact retains the baseline and comparison case IDs, group
dimensions, invariant status, signal outcome, cohort-specific scores, capital
deltas, drawdown amplification, maximum-wager multiple, recovery depth, and
descriptive interpretation labels. The artifact is local and derived entirely
from collected campaign state, making it the immediate input contract for the
Stability Engine without another cloud execution.

---

# Workstream A — Architecture / Engine

**Owner:** QCRL Architecture / Results thread

## Responsibilities

- Core simulation engine
- Entry models
- Filter models
- Stake models
- RiskTracker
- StatsTracker
- ResearchReport
- Runtime metadata generation
- Deterministic experiment identity
- Unique run identity
- Results Database
- ObjectStore persistence
- ExperimentStore
- ResearchTools v2
- Experiment retrieval
- Record normalization
- Record validation
- Legacy migration
- Storage compaction and export

## Current baseline

QCRL 2.2.0 is the clean methodological baseline.

Completed:

- EMA filter timing corrected to remove current-bar look-ahead.
- Entry, filter, and stake behavior are isolated.
- Flat and martingale runs can be paired against the same signal sequence.
- Metadata is generated from resolved runtime parameters.
- `experiment_id` is deterministic for a resolved experiment configuration.
- `run_id` is unique for every execution.
- FINREV was removed from the baseline project and archived separately.
- Plotting is disabled or throttled during optimization.
- Invalid month-end dates are corrected transparently.
- Each new run saves one canonical full report.
- Normalized experiment records are reconstructed during retrieval.
- Save failures are reported truthfully.
- Legacy reports remain loadable.
- ResearchTools v2 supports selection, filtering, ranking, comparison, source separation, latest-run retrieval, deduplication, duplicate detection, summaries, dashboards, and export.

## Canonical storage

```text
qcrl/v2/experiments/{coin}/{timeframe}/{year}/{run_id}.json
```

New runs no longer require a second normalized-record file.

`ExperimentStore` reconstructs the normalized record from the canonical report.

## Storage constraint

QuantConnect ObjectStore has a finite file-count allowance. QCRL currently uses one file per new run. Campaign compaction remains planned before another large optimization program.

---

# Methodology Boundary

## Clean evidence

Discovery should treat QCRL 2.2.0 and later records as the beginning of the clean evidence corpus, provided they pass record validation.

Expected characteristics:

```text
record_source = v2
lab_version = QCRL-2.2.0 or later
EMA filtering = prior-state / look-ahead-free
metadata = generated from runtime configuration
persistence = canonical report
```

## Historical evidence

The earlier legacy corpus remains valuable for:

- architecture history
- regression testing
- migration testing
- hypothesis generation
- comparison with corrected methodology

However, pre-2.2 EMA-filter experiments used current-bar information when evaluating the same bar. They must not be combined with clean records in stability, consensus, clustering, archetype, or confidence calculations.

Until explicit methodology labels are added to every record, Discovery should treat:

```text
record_source = legacy
```

as historical-only by default.

## FINREV

FINREV is not part of the QCRL 2.2.0 baseline.

FINREV records and source code should remain isolated from baseline Discovery cohorts unless a separate FINREV research program is intentionally defined.

---

# Engine-to-Discovery Data Contract

Discovery consumes normalized experiment dictionaries.

Preferred access:

```python
from experiment_store import ExperimentStore
from research_tools import ResearchTools

store = ExperimentStore(qb.ObjectStore)
tools = ResearchTools(store=store)

records = tools.load(refresh=True)
```

Preferred clean starting cohort:

```python
clean_v2 = tools.select(
    record_source="v2",
    lab_version="QCRL-2.2.0"
)

clean_v2 = tools.dedupe(clean_v2)
```

Discovery must not depend on:

- ObjectStore key construction
- JSON file locations
- legacy migration rules
- report normalization logic
- metadata generation internals
- persistence implementation
- campaign compaction implementation

## Current normalized fields

The clean record contract includes, or is expected to include, these categories.

### Identity and provenance

```text
run_id
experiment_id
configuration_hash
generated_at_utc
completed_at_algorithm_time
lab_version
engine_version
git_commit
git_branch
campaign_id
methodology_version
lookahead_status
record_status
schema_version
record_source
experiment_group
experiment_family
experiment_name
experiment_notes
experiment_tags
```

### Cohort dimensions

```text
coin
timeframe
year
start
end
entry_model
filter_model
stake_mode
streak_length
streak_mode
ema_fast
ema_slow
base_wager
bankroll
multiplier
max_steps
```

### Performance

```text
initial_bankroll
final_bankroll
net_profit
trades
wins
losses
win_rate
```

### Risk and recovery

```text
ruined
ruin_time
ruin_reason
max_drawdown
max_single_wager
max_win_streak
max_loss_streak
average_recovery_depth
max_recovery_depth
```

### Signal and execution analytics

```text
bars_seen
signals_generated
signals_executed
execution_rate
filter_rate
executed_win_rate
total_wagered
average_wager
up_signals
down_signals
up_executed
down_executed
regime_stats
loss-sequence / recovery-depth distribution
```

### Scores

```text
survival_score
risk_adjusted_score
tail_risk_score
```

## Planned record-contract additions

Discovery should not assume these fields exist yet:

```text
signal_configuration_hash
signal_experiment_id
capital_configuration_hash
comparison_pair_id

final_loss_step
terminal_loss_streak
open_loss_exposure
next_required_wager
completed_recovery_cycles

validation_flags
configuration_warnings
configuration_adjustments
```

Workstream A owns adding and normalizing those fields.

---

# First Clean Control Experiment

Configuration:

```text
Coin: BTCUSD
Period: 2025
Timeframe: 1d
Entry: candle_streak
Streak length: 2
Streak mode: reverse
Filter: EMA trend 5/10
Base wager: 10
```

## Flat result

```text
Trades: 58
Wins: 35
Losses: 23
Win rate: 60.34%
Net profit: 120
Max drawdown: 50
Max single wager: 10
Ruined: False
Final loss step: 0
```

## Martingale result

```text
Trades: 58
Wins: 35
Losses: 23
Win rate: 60.34%
Net profit: 350
Max drawdown: 310
Max single wager: 320
Total wagered: 1490
Ruined: False
Final loss step: 0
```

## Pair invariant

The flat and martingale runs produced identical:

```text
trades
wins
losses
win_rate
signals_generated
signals_executed
up/down execution counts
win/loss streaks
loss-sequence distribution
```

Only capital-dependent metrics changed.

This validates the intended separation:

> **Flat staking measures directional signal performance.  
> Martingale measures the capital-recovery transformation applied to that same sequence.**

---

# Baseline Validation Campaign

Completed on 2026-08-08:

```text
BTCUSD 1d
Candle streak reverse
EMA trend 5/10

2022 flat / martingale
2023 flat / martingale
2024 flat / martingale
2025 flat / martingale
```

All four yearly pairs passed the stake-isolation invariants and were collected
through the QuantConnect API before Stability Engine analysis began.

## Pair validation requirements

For each flat/martingale pair, these fields must match:

```text
trades
wins
losses
win_rate
signals_generated
signals_executed
up_signals
down_signals
up_executed
down_executed
max_win_streak
max_loss_streak
win_streak_histogram
loss_streak_histogram
```

These fields may differ:

```text
net_profit
final_bankroll
total_wagered
average_wager
max_single_wager
max_drawdown
risk_adjusted_score
```

Any violation of the first list is an Engine/record-contract issue and must be returned to Workstream A before Discovery analysis continues.

---

# Workstream B — Analysis / Discovery

**Owner:** QCRL Analysis / Discovery thread

## Owned engines

- Stability Engine
- Consensus Engine
- Cluster Engine
- Archetype Engine
- Confidence Engine

## Core rule

Discovery operates only on explicitly selected, methodologically compatible cohorts.

Do not mix records merely because they share high-level labels.

At minimum, cohort selection must consider:

```text
methodology generation
asset
timeframe
entry model
entry parameters
filter model
filter parameters
stake mode
date/year structure
```

---

# Stability Engine

## Purpose

Measure whether a strategy behavior remains consistent across independent samples rather than merely producing one attractive result.

## Implemented interface

```text
discovery/stability_engine.py
```

Suggested interface:

```python
class StabilityEngine:
    def analyze(self, paired_artifact):
        ...
```

## First clean analysis

Use the BTCUSD 1d, candle-streak-reverse, EMA 5/10 yearly matrix.

Analyze flat and martingale separately.

### Flat stability asks

- Is win rate above 50% across years?
- Is flat net profit consistently positive?
- How variable are trade count and execution rate?
- Is directional performance concentrated in UP or DOWN trades?
- Does one year dominate the aggregate result?
- Are loss-streak distributions stable?
- Is the signal repeatable without recovery sizing?

### Martingale stability asks

- Does every year survive?
- How variable are max drawdown and max wager?
- How deep are recovery sequences?
- How often does martingale outperform flat?
- Is apparent profitability dependent on ending at loss step zero?
- Does capital exposure grow faster than profit?
- Is the capital transformation stable even when flat signal quality weakens?

## Recommended initial outputs

```text
group_key
run_count
years_present
years_expected
coverage_ratio

mean_win_rate
std_win_rate
min_win_rate
max_win_rate

profitable_years
surviving_years
profit_consistency_ratio
survival_ratio

mean_net_profit
std_net_profit
coefficient_of_variation

mean_max_drawdown
worst_max_drawdown
mean_max_loss_streak
worst_max_loss_streak

stability_score
risk_penalty
coverage_penalty
final_score

warnings
supporting_run_ids
```

## Stability Engine v1 result

Implemented in:

```text
discovery/stability_engine.py
```

Command:

```bash
./synch.sh campaign stability campaigns/btcusd_1d_baseline_2022_2025.json
```

Artifact:

```text
.qcrl/campaigns/btcusd-1d-baseline-2022-2025-v1/stability_report.json
schema_version = qcrl.stability_report.v1
score_version = qcrl.stability_score.v1
```

Clean control result:

```text
evidence_status: validation_cohort_complete
coverage: 4 / 4 (100%)

flat_signal.stability_score: 59.3411
flat_signal.risk_penalty: 41.7188
flat_signal.final_score: 34.5847
flat_signal.classification: fragile

martingale_capital.stability_score: 75.5977
martingale_capital.risk_penalty: 73.2000
martingale_capital.final_score: 20.2602
martingale_capital.classification: fragile
```

Flat component weights:

```text
30% profitable-year ratio
20% non-negative-year ratio
25% win-rate consistency
15% years at or above 50% win rate
10% profit-balance score
```

Martingale component weights:

```text
25% survival ratio
20% profitable-year ratio
20% drawdown-amplification consistency
20% wager-escalation consistency
15% recovery-depth consistency
```

The final score applies explicit coverage and risk penalties. Every threshold,
supporting run ID, supporting case ID, warning, and intermediate statistic is
retained in the JSON report. The v1 classifications are research-fragility
labels, not predictions or deployment approvals.

Current warnings:

```text
flat_profit_not_consistent_across_samples
flat_win_rate_regime_variation
martingale_profit_depends_on_recovery_sizing
martingale_extreme_wager_escalation
martingale_substantial_drawdown_amplification
terminal_loss_exposure_metrics_unavailable
validation_cohort_not_universal_evidence
```

## Comparative interpretation v1 result

Phase B6 is implemented inside the Stability Engine as:

```text
interpretation_version = qcrl.comparative_interpretation.v1
scope = research_progression_not_live_trading_authorization
```

The interpretation reports separate signal and capital-recovery dispositions,
recovery dependence, risk amplification, evidence confidence, and a single
advancement gate. The gate has three possible decisions:

```text
advance -> advance_to_parameter_neighborhood_validation
hold    -> expand validation before advancement
reject  -> reject the current signal+sizing pair
```

Baseline verdict:

```text
advancement_gate.decision: reject
signal_stability.disposition: reject
capital_recovery_stability.disposition: reject
evidence_confidence: moderate (75.0)
recovery_dependence: high (50%)
risk_amplification: extreme
next_action: redesign_signal_and_reject_current_recovery_sizing
```

Blockers:

```text
flat_signal_fragile
flat_profit_inconsistent
martingale_capital_fragile
profit_recovery_dependent
extreme_wager_escalation
substantial_drawdown_amplification
```

This rejects the tested configuration, not the QCRL research program. The next
campaign should test redesigned directional hypotheses under flat sizing first.
Recovery sizing must not be optimized until a signal passes the flat-signal
advancement gate.

---

# Consensus Engine

## Purpose

Identify parameters or behaviors supported by multiple valid experiments.

Consensus is not majority voting over arbitrary runs. It must operate within compatible cohorts and account for evidence quality.

## Responsibilities

- Find parameter values supported across multiple years.
- Separate signal consensus from staking consensus.
- Weight clean and sufficiently sampled evidence more heavily.
- Detect when apparent agreement comes from duplicated or overlapping records.
- Report disagreement rather than forcing a consensus.
- Preserve minority but high-quality stable regions for further inspection.

## Guardrail

Flat-stake evidence should establish directional signal consensus before martingale evidence is used to recommend recovery sizing.

---

# Cluster Engine

## Purpose

Group experiments by observed behavior rather than by manually assigned labels.

## Candidate feature families

### Signal behavior

```text
win_rate
execution_rate
filter_rate
trade_count
up/down balance
up/down win-rate spread
```

### Risk behavior

```text
max_drawdown
max_loss_streak
max_recovery_depth
max_single_wager
tail_risk_score
ruin
```

### Capital behavior

```text
net_profit
average_wager
total_wagered
profit-to-drawdown ratio
profit-to-capital-wagered ratio
```

### Stability behavior

```text
cross-year variance
survival consistency
profit consistency
parameter-neighborhood stability
```

## Guardrails

- Normalize features before clustering.
- Do not allow identifiers or timestamps to become clustering features.
- Do not mix historical and clean methodology.
- Prefer separate flat and martingale clustering initially.
- Treat ruin as a major categorical or penalty feature.
- Retain cluster-supporting run IDs and feature summaries.

---

# Archetype Engine

## Purpose

Translate behavioral clusters into interpretable strategy archetypes.

Initial candidate archetypes:

```text
Robust
Fragile
Sniper
Firehose
Scalper
Swing
Lottery
Recovery-Dependent
Signal-Positive
Signal-Weak
Tail-Risk Dominated
Capital-Inefficient
```

Archetypes must be derived from measurable behaviors, not assigned from names or profits alone.

Example:

```text
Recovery-Dependent
- flat signal weak or inconsistent
- martingale profitable
- high wager escalation
- high drawdown relative to flat
- no or few ruin events in observed sample
```

---

# Confidence Engine

## Purpose

Estimate how much trust should be placed in a Discovery conclusion.

Confidence is an evidence-quality score, not another profitability score.

## Candidate confidence dimensions

```text
methodology quality
record validity
sample size
number of independent years
cohort completeness
flat/martingale pair completeness
survival consistency
parameter-neighborhood support
cross-year stability
duplicate control
tail-risk severity
terminal-sequence completeness
out-of-sample evidence
```

## Mandatory confidence penalties

- legacy methodology
- one-year evidence
- very low trade count
- missing paired baseline
- incomplete years
- ruin
- high terminal open exposure
- isolated parameter spike
- duplicate-heavy evidence
- inconsistent metadata
- mixed cohorts

## Rule

A high-profit experiment may receive low confidence.

A modest-profit but repeatedly stable experiment may receive high confidence.

---

# Discovery Guardrails

1. Do not mix legacy and QCRL 2.2.0 evidence.
2. Do not mix flat and martingale results in one undifferentiated score.
3. Do not infer signal quality from martingale profit.
4. Do not rank by net profit alone.
5. Do not claim stability from one year.
6. Do not interpret a completed recovery cycle as proof of predictive edge.
7. Do not ignore terminal loss exposure.
8. Do not mix assets, timeframes, entry families, or filter families without an explicit cross-cohort analysis.
9. Do not allow duplicates to increase evidence weight.
10. Preserve supporting `run_id` values for every conclusion.
11. Return warnings and insufficient-evidence states instead of forcing a score.
12. Treat the 2022–2025 matrix as a validation cohort, not yet a universal conclusion.

---

# Immediate Discovery Work Plan

## Phase B1 — Stability Engine scaffold — completed

Create:

```text
discovery/
    __init__.py
    stability_engine.py
```

Build against a plain list of normalized records.

No direct ObjectStore access.

## Phase B2 — Cohort builder — completed

Define a repeatable selection for:

```text
BTCUSD
1d
candle_streak
streak_length = 2
streak_mode = reverse
ema_fast = 5
ema_slow = 10
years = 2022–2025
```

Split into:

```text
flat cohort
martingale cohort
paired cohort
```

## Phase B3 — Validation report — completed

Before scoring stability, report:

```text
expected years
present years
missing years
duplicate configurations
flat/martingale pair completeness
pair invariant violations
methodology mismatches
record warnings
```

## Phase B4 — Flat stability score — implemented in v1

Score directional evidence without recovery sizing.

## Phase B5 — Martingale stability score — implemented in v1

Score capital transformation, survival, recovery depth, drawdown, and wager escalation.

## Phase B6 — Comparative interpretation — completed

Produce a paired conclusion such as:

```text
signal stability
capital-recovery stability
recovery dependence
risk amplification
evidence confidence
```

---

# Requests Back to Workstream A

Discovery may request these additions, but Workstream A owns implementation:

1. `signal_configuration_hash`
2. `signal_experiment_id`
3. `comparison_pair_id`
4. `final_loss_step`
5. `open_loss_exposure`
6. `next_required_wager`
7. `completed_recovery_cycles`
8. explicit methodology labels
9. explicit record-validation status
10. UP/DOWN win rates in normalized records
11. campaign identifiers and expected-run counts
12. campaign compaction before large optimization programs

Discovery should continue with available fields and treat missing planned fields as explicit limitations.

---

# API Boundary

Current safe usage:

```python
records = tools.load(refresh=True)

clean = tools.select(
    records,
    record_source="v2",
    lab_version="QCRL-2.2.0"
)

clean = tools.dedupe(clean)

cohort = tools.select(
    clean,
    coin="BTCUSD",
    timeframe="1d",
    entry_model="candle_streak",
    streak_length=2,
    streak_mode="reverse",
    ema_fast=5,
    ema_slow=10
)

flat = tools.select(cohort, stake_mode="flat")
martingale = tools.select(cohort, stake_mode="martingale")
```

Discovery engines should accept `flat`, `martingale`, or another explicit record list as input.

---

# Current Handoff State

## 2026-08-08 directional signal campaign sync

QCRL 2.3.0 introduces three lookahead-free directional generators while
preserving the existing candle-streak implementation:

```text
ema_trend          5 / 10
macd_trend         12 / 26 / 9
rsi_mean_reversion 14, oversold 30, overbought 70
```

Each generator returns `up`, `down`, or `None` from prior-bar indicator state,
then ingests the current bar. This is the same decision/update ordering as the
validated candle-streak and EMA-filter baseline.

Two direction-independent eligibility gates are implemented for later use:

```text
adx_strength   period 14, threshold 25
atr_volatility period 14, eligible range [1%, 10%)
```

Stage 1 manifest:

```text
campaigns/btcusd_1d_directional_stage1_2022_2025.json
4 signal generators x 4 yearly cohorts = 16 cases
stake_mode = flat
filter_model = none
```

ADX and ATR are intentionally excluded from Stage 1. Stage 2 may apply one
gate at a time only to generators that survive cross-year signal analysis.
Composite filters and recovery sizing remain gated.

Directional Cohort Engine v1:

```text
input:  qcrl.directional_cohort.v1
output: qcrl.directional_cohort_report.v1
score:  qcrl.directional_cohort_score.v2
```

Score weights are embedded in every report:

```text
30% profitable-sample ratio
20% non-negative-sample ratio
25% win-rate consistency
15% samples at or above 50% win rate
10% profit balance
```

The risk penalty weights worst drawdown in base wagers and worst loss streak
equally. Coverage multiplies the post-risk score. Stable begins at 70, mixed at
50, and lower scores are fragile; all thresholds and weights are serialized.

Score v2 adds evidence floors before any terminal `advance` or `reject`:

```text
minimum total trades: 100
minimum trades in every yearly sample: 20
```

Below either floor, the disposition is `hold` with an explicit sparse-evidence
warning. This protects the exploratory long-streak tail from small-sample win
rates.

Command:

```bash
./synch.sh campaign directional campaigns/btcusd_1d_directional_stage1_2022_2025.json
```

Completed Stage 1 verdict:

```text
candle_streak       54.81  mixed    hold    +490  4/4 profitable
rsi_mean_reversion  40.67  fragile  reject   +70  3/4 profitable
macd_trend           12.41  fragile  reject  -250  2/4 profitable
ema_trend             7.38  fragile  reject  -410  0/4 profitable
```

Candle streak is held because its cross-year consistency is credible but its
worst drawdown reached 15 base wagers. RSI is rejected at the tested defaults
because win rate and trade frequency varied sharply by year. MACD and EMA are
rejected at their tested defaults because their aggregate signal economics are
negative.

The analyzer's campaign-level next action is:

```text
run_parameter_neighborhood_validation
```

The next campaign should vary candle-streak length under flat sizing with no
filter. ADX and ATR remain gated until that neighborhood evidence is resolved.

## Candle-streak neighborhood campaign

Manifest:

```text
campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json
```

Design:

```text
BTCUSD 1d
2022, 2023, 2024, 2025
entry_model = candle_streak
streak_mode = reverse
streak_length = 1, 2, 3, 4, 5, 6
stake_mode = flat
filter_model = none
24 cases
```

Lengths 1–3 are the core local neighborhood around the current length-2 result.
Lengths 4–6 test the exploratory tail hypothesis that longer streaks may have a
higher conditional reversal rate. The design does not assume monotonicity.
Longer streaks are rarer, and continued streaks create overlapping signal
windows, so raw trade count overstates independent episode count. That
limitation is serialized into the directional evidence and report.

## 2026-09-05 neighborhood result and Stage 2 handoff

All 24 neighborhood cases were collected through the QuantConnect API and
passed validation. The core result is not monotonic: length 2 had the strongest
final score among the sufficiently sampled values, while lengths 1 and 3 both
provided positive two-sided neighborhood support. Length 4 deteriorated and
lengths 5–6 were too sparse for selection.

The versioned `qcrl.directional_neighborhood_interpretation.v1` contract now
records the predeclared candidate, core and tail values, supporting neighbors,
tail exclusions, blockers, and the region-level next action. It selects
`streak_length=2` for isolated eligibility-gate testing; this selection is a
research-progression decision, not live authorization.

Campaign evidence provenance is now explicit:

```text
lean_cli terminal metrics -> completed (preview only)
quantconnect_api metrics + collected_at_utc -> collected (authoritative)
```

Directional artifacts reject terminal-only evidence. Legacy collected state
with an API collection timestamp is migrated in memory to the explicit API
source and persisted on the next validation or directional-analysis command.

The next manifest is:

```text
campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json
length 2 x [none, adx_strength, atr_volatility] x 4 years = 12 cases
stake_mode = flat
```

It tests each gate independently against the unfiltered control and validates
that generated UP/DOWN signal counts are unchanged. Composite gates, parameter
optimization, and recovery sizing remain gated.

## 2026-09-05 Stage 2 result and attribution gate

The 12-case Stage 2 campaign is fully API-collected and valid. The versioned
`qcrl.single_gate_interpretation.v1` layer compares each gate with the
same-year unfiltered control under predeclared evidence thresholds.

```text
ATR: advance | profit delta +70 | weighted win-rate delta +0.69 pp
             | trade retention 95.79% | improved years 3/4
ADX: reject  | profit delta -280 | weighted win-rate delta -0.20 pp
             | trade retention 45.43% | improved years 0/4
```

ATR did not increase worst drawdown, but its final cohort score remained nearly
equal to the control because win-rate consistency was slightly lower. The gate
therefore advances only to attribution and parameter-neighborhood research.

The default ATR profile removed 29 of 689 control trades. The report/API
contract distinguishes indicator warmup from active gate rejection with:

```text
QCRL Filter Not Ready
QCRL Filter Rejected
```

The 20-case attribution campaign is fully API-collected and valid. Warmup-only,
lower-only, upper-only, and default-band profiles produced identical outcomes
in every year. Across 2022–2025, each ATR profile recorded 29 not-ready skips
and zero bound-rejected signals. The versioned
`qcrl.gate_attribution_interpretation.v1` verdict therefore classifies all
three bound profiles as `no_incremental_effect` and blocks threshold tuning.
The apparent +70 aggregate profit and +0.69 percentage-point weighted win-rate
change are attributable entirely to excluding signals during ATR warmup.

Signal-time ATR telemetry is now part of the canonical report/API surface:

```text
QCRL Filter Value Count
QCRL Filter Value Min
QCRL Filter Value P10
QCRL Filter Value P25
QCRL Filter Value P50
QCRL Filter Value P75
QCRL Filter Value P90
QCRL Filter Value Max
```

The values are prior-state ATR percentages captured only when a directional
signal is generated, preserving lookahead-free decision ordering. The telemetry
campaign completed 4/4 with 660 usable values. The pooled observed envelope was
1.90%–8.50%; annual medians ranged from 3.21% to 5.02%, demonstrating meaningful
regime-dependent selectivity for any absolute threshold.

The predeclared active-bound screen is
`btcusd_1d_atr_active_bounds_2022_2025.json`. Its 24 cases compare warmup-only
with lower bounds 2.5% and 3.0% and upper bounds 5.0% and 6.0%, retaining an
unfiltered control in each year. The attribution engine now evaluates active
components incrementally against warmup-only rather than allowing the warmup
effect to leak into candidate decisions. Lower and upper components remain
isolated. Because these thresholds were selected from 2022–2025 telemetry,
same-period results are exploratory; any survivor requires out-of-sample
validation. Broad optimization remains gated.

The screen completed 24/24 with authoritative API metrics and no pair issues.
Every active bound underperformed warmup-only in aggregate:

```text
lower 2.5%: profit -140 | weighted win rate -0.78 pp | rejected 54
lower 3.0%: profit -160 | weighted win rate -0.40 pp | rejected 140
upper 5.0%: profit -110 | weighted win rate -0.07 pp | rejected 121
upper 6.0%: profit  -40 | weighted win rate -0.04 pp | rejected 42
```

The attribution verdict is `reject_tested_active_gate_bounds`. No absolute ATR
bound, combined ATR band, or ATR threshold optimizer advances from this branch.

Directional-side attribution is the next isolated signal diagnostic. The
four-case `btcusd_1d_candle_streak_side_attribution_2022_2025.json` campaign
keeps the length-2 reverse signal, no filter, and flat sizing fixed while each
run exports separate UP and DOWN trades, wins, losses, win rate, net profit,
drawdown, and loss streak. UP denotes a bullish reversal forecast after a red
streak; DOWN denotes a bearish reversal forecast after a green streak.

The `qcrl.side_attribution_interpretation.v1` analyzer enforces annual
accounting conservation between side metrics and total run results, then emits
`two_sided`, `up_dominant`, `down_dominant`, `unresolved`, or
`no_supported_side`. A direction selected from the same 2022–2025 evidence
cannot advance without out-of-sample validation. Side-specific drawdown is an
independent side equity-curve statistic, not an additive decomposition of the
combined portfolio drawdown.

The completed 2022–2025 attribution verdict was `down_dominant`:

```text
UP:   reject    | profit +60  | weighted win rate 50.85% | profitable 1/4
DOWN: supported | profit +430 | weighted win rate 56.38% | profitable 3/4
```

The relationship reversed in 2024, when UP earned +170 and DOWN lost 80, so
DOWN dominance is not assumed universal. The next four-case manifest,
`btcusd_1d_candle_streak_side_stress_2018_2021.json`, predeclares DOWN as the
hypothesis under `evidence_role=historical_regime_stress`. It treats 2018–2021
as a materially different early-adoption market regime, not an IID extension
or conventional forward holdout. QuantConnect documents Coinbase crypto data
from January 2015, while the first integration case remains the definitive
access and data-quality check for this project.

Canonical storage contracts are extended to preserve every active directional,
gate, and observational-regime parameter:

```text
qcrl.research_report.v5
qcrl.experiment_record.v4
```

The existing QCRL 2.2.0 baseline campaign remains reproducible because its
manifest pins `lab_version=QCRL-2.2.0` and the legacy model path is unchanged.

## 2026-09-06 cross-regime side synthesis

Files created or changed:

- `discovery/cross_regime_side_engine.py`
- `qcrl_synthesis.py`
- `syntheses/btcusd_1d_candle_streak_cross_regime_sides.json`
- `qcrl_campaign.py`, `synch.sh`, `README.md`, and this sync log
- deterministic engine and command-parser tests

The `qcrl.cross_regime_side_evidence.v1` input contract consumes two or more
completed `qcrl.side_attribution_interpretation.v1` reports. Before pooling, it
requires identical signal parameters, unique regime labels, non-overlapping
period labels, both directional sides, and matching campaign evidence hashes.
The analyzer emits `qcrl.cross_regime_side_report.v1`; the new command is:

```bash
./synch.sh campaign synthesize syntheses/btcusd_1d_candle_streak_cross_regime_sides.json
```

No QuantConnect backtest is required. The source campaigns remain authoritative
and the ignored `.qcrl/syntheses/` output is a reproducible local derivative.

The completed synthesis found:

```text
2018–2021: UP dominant
2022–2025: DOWN dominant
pooled UP:   +600 | 54.66% | 644 trades | profitable 5/8
pooled DOWN: +550 | 53.91% | 703 trades | profitable 5/8
combined:  +1,150 | 54.27% | 1,347 trades | profitable 7/8
```

The directional leadership flip rejects a static UP-only or DOWN-only rule.
Both directions remain in the daily signal. The next coding target is to define
small, predeclared hypotheses using information known before the signal that
might explain the era-dependent leadership; the historical labels themselves
must not become features. This result does not establish stationarity, a regime
classifier, cost-adjusted profitability, or live-trading authorization.

Tests completed: 71 deterministic unit tests, Python compilation, diff
whitespace validation, and a successful synthesis against both authoritative
local campaign reports.

## 2026-09-06 prior-state regime bridge

The first regime hypothesis is now declared and runnable. `regime_models.py`
adds an observational `roc_sign` model whose state at a signal is computed only
from closes completed before the signal bar. Its default campaign lookback is
20 daily bars and its predeclared boundary is zero percent. The observer is
architecturally separate from the filter layer and cannot change eligibility,
sizing, or the two-sided signal.

`StatsTracker` and the v5/v4 report contracts attribute trades, wins, losses,
and realized wager profit to UP/DOWN × positive/nonpositive/not-ready cells.
Eighteen scalar cell metrics are exported through QuantConnect's result API.
Configuration identity includes regime parameters only when an observer is
active, preserving the identity of existing no-observer experiments.

The new `qcrl.regime_attribution_interpretation.v1` path verifies annual
accounting conservation before testing one predeclared hypothesis:

```text
aligned: UP in positive 20-day drift + DOWN in nonpositive 20-day drift
counter: UP in nonpositive drift + DOWN in positive drift
minimum regime-ready ratio: 85% in every annual sample
minimum active-cell evidence: 50 pooled trades per cell
minimum pooled aligned win-rate edge: +2 percentage points
minimum annual directional support: 6 of 8 years
```

The campaign
`btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json` contains eight
flat, unfiltered annual cases spanning 2018–2025. It measures all existing
trades rather than applying a gate. If the declared hypothesis is supported,
the only permitted advancement is a new forward gate-validation design that
does not reuse 2018–2025 for confirmation. If rejected, the unfiltered
two-sided signal remains intact and this ROC-alignment explanation closes.

Files changed or created: `regime_models.py`, algorithm configuration and
execution wiring, stats/report/metadata contracts, campaign collection and
manifest validation, directional interpretation and output, the versioned
campaign declaration, architecture/readme/sync documentation, and deterministic
tests. No new request is imposed on Workstream A beyond preserving v5/v4
schema compatibility. Tests completed: 77 deterministic unit tests, manifest
expansion, metric-map parity, Python compilation, and whitespace validation.

Next coding target: none until the 2018 integration case confirms QuantConnect
compilation, API metric visibility, and regime accounting on real bars.

## 2026-09-06 ROC regime result and forward declaration

The 2018–2025 attribution campaign completed 8/8 with authoritative API
metrics, exact side/regime accounting, 94.36% regime readiness, and adequate
evidence in all four active cells. The predeclared trend-alignment hypothesis
was correctly rejected because its positive edge appeared in five of eight
years rather than the required six:

```text
aligned: +630 | 56.98% | 451 trades
counter: +520 | 53.17% | 820 trades
pooled aligned edge: +3.81 percentage points
annual support: 5/8
```

No lookback or threshold optimization follows. A distinct post-hoc observation
from the locked discovery report is now recorded as a new hypothesis:

```text
nonpositive 20-day state: +950 | 58.06% | 589 trades
positive 20-day state:    +200 | 51.47% | 682 trades
UP nonpositive edge over positive:   +3.26 percentage points
DOWN nonpositive edge over positive: +10.90 percentage points
```

`btcusd_1d_candle_streak_roc_regime_forward_2026.json` freezes the observer and
tests this state effect only on January 1 through August 31, 2026. The new
`qcrl.regime_state_validation_interpretation.v1` gate requires complete
forward coverage, 85% readiness, 30 pooled trades in each regime, 10 trades in
each side/regime cell, a +2-point pooled edge, greater favored-state profit,
and positive edges on both UP and DOWN. It cannot pass on aggregate improvement
driven by one direction alone.

A supported single partial-year result advances only to additional frozen
forward observation. A rejected result closes the ROC state-gate hypothesis
and retains the unfiltered signal. An undersized result extends the observation
window without changing parameters. Tests completed: 81 deterministic unit
tests, forward-manifest expansion, Python compilation, and whitespace checks.

Next: synchronize the declaration and execute the single 2026 forward case.

## Workstream A exports

- QCRL 2.2.0 validated baseline reports
- QCRL 2.3.0 directional signal engine
- normalized record dictionaries
- deterministic experiment identity
- unique run identity
- dynamic metadata
- deduplicated retrieval
- flat/martingale control records
- completed 2022–2025 validation matrix
- paired comparison artifact
- Stability Engine v1 report

## Workstream B current state

```text
Stability Engine v1 implemented
Comparative interpretation v1 implemented
Current signal+sizing pair rejected
Directional Stage 1 campaign completed: 16/16 collected
Directional Cohort Engine v1 implemented
Candle streak held; RSI, MACD, and EMA defaults rejected
Candle-streak lengths 1–6 neighborhood campaign complete (24/24 API-collected)
Length 2 selected with two-sided core-neighborhood support
Stage 2 complete: ATR advanced provisionally; ADX default rejected
ATR attribution complete: 20/20 API-collected, all bounds inert
Attribution-aware verdict v1 implemented
ATR telemetry complete: 4/4 API-collected, 660 signal-time values
Active ATR bound screen complete: 24/24 API-collected, all candidates rejected
Attribution candidates are judged incrementally against warmup-only
Directional-side result: DOWN supported, UP rejected over 2022–2025
Earlier-regime stress complete: UP supported, DOWN held over 2018–2021
Cross-regime side synthesis v1 implemented
Directional leadership flips by era; static side restriction rejected
Both directions retained in the daily signal
ROC-sign observer and regime-attribution verdict implemented
2018–2025 trend-alignment hypothesis rejected at 5/8 supporting years
Post-hoc nonpositive-state advantage isolated and labeled discovery-only
Frozen January–August 2026 forward-validation campaign rejected
Quarterly temporal-persistence gate declared across 2018Q1–2025Q4
Next: synchronize and execute the 2018Q1 boundary-integration case
```

## 2026-09-06 quarterly temporal-persistence gate

The locked January–August 2026 ROC-state hypothesis was rejected. All evidence
and sample-size checks passed, but the nonpositive state produced no pooled
win-rate or profit advantage; UP contradicted the hypothesis while DOWN alone
supported it. This closes that feature path without re-tuning the observer.

The next gate asks a more fundamental question: whether the untouched,
two-sided length-2 daily reversal signal is temporally persistent enough to
deserve more feature engineering. The new campaign declares 32 non-overlapping
quarters from 2018Q1 through 2025Q4. Each LEAN run begins two daily bars before
its evaluation quarter so entry memory crosses the artificial boundary, while
the algorithm explicitly excludes those seed bars from statistics, signals,
risk, and profit.

`qcrl.temporal_audit.v1` requires authoritative API collection and verifies
flat-payout accounting before `qcrl.temporal_stability_report.v1` measures
quarterly profitability, weighted win rate, dispersion, 29 rolling four-quarter
windows, maximum loss streak, break-even constant friction, and top-four profit
concentration. All thresholds are frozen in the manifest before collection.
`bars_seen` is also exported as an API metric so the first cloud case can verify
that pre-evaluation seed bars do not leak into the scored quarter.
The v6/v5 report contracts add `evaluation_start`; existing experiments retain
their identity when it equals the engine start.

Files created or changed: temporal campaign declaration, temporal artifact and
stability engines, campaign/manifest routing, algorithm evaluation boundary,
metadata/report contracts, tests, and research documentation. No new Workstream
A request exists beyond preserving the additive v6/v5 date field. Tests
completed: 88 deterministic tests, 32-case manifest expansion, Python
compilation, and whitespace validation.

Next coding target: none until the first 2018Q1 cloud case confirms the seeded
quarter boundary and authoritative metric collection.

## 2026-09-06 historical-forward bridge and prospective lock

The 2018–2025 temporal campaign completed 32/32 with authoritative API
evidence and exact calendar-quarter bar counts. The untouched signal passed
every predeclared historical gate: 25/32 profitable quarters, 54.22% weighted
win rate over 1,352 trades, +1,140 flat-wager profit, 27/29 positive rolling
four-quarter windows, 8.43% aggregate break-even friction, 6.13% quarterly
win-rate dispersion, and 32.85% top-four positive-profit concentration.

`qcrl.temporal_bridge_report.v1` now adjudicates that history against the
locked January–August 2026 sample. Its result is `forward_degraded` and
`hold_feature_optimization`: the forward sample had 130 trades, 46.92% wins,
and -80 profit, a -7.29 percentage-point change. It failed the declared
positive-profit, 52% minimum forward win-rate, and three-point maximum decline
checks. The approximate two-sided comparison p-value is descriptive only and
does not override these evidence gates.

Two follow-ups are now architecturally separated. A three-case campaign splits
the already-observed 2026 period into Q1, Q2, and July–August solely to localize
the degradation; it is permanently labeled post-hoc diagnostic evidence. A
separate 2026Q4 baseline was locked on September 6 before its October 1 start.
It must not be run partially or modified and becomes evaluable only after
December 31. Neither path authorizes indicator, regime, or parameter search.

Files created or changed: temporal bridge engine and synthesis routing,
versioned synthesis specification, diagnostic and prospective campaign
declarations, deterministic tests, and research documentation. No algorithm
logic or QCRL metric schema changed. Tests completed: 93 deterministic tests,
both new manifest expansions, synthesis execution, Python compilation, and
whitespace validation.

Next coding target: none until the three post-hoc 2026 diagnostic cases are
collected; the prospective Q4 declaration remains frozen.

## 2026-09-06 forward-degradation localization result

The post-hoc diagnostic campaign completed 3/3 with authoritative API evidence
and exact boundary bar counts. Q1 produced -120 at 38.46% over 52 trades, Q2
produced -20 at 47.92% over 48 trades, and July–August produced +50 at 58.62%
over 29 trades. Q1 losses were symmetric across UP and DOWN (-60 each); Q2 was
mixed (UP -40, DOWN +20); both sides were positive in July–August (UP +20,
DOWN +30).

`qcrl.forward_diagnostic_report.v1` records the increasing win-rate and profit
path as `early_2026_loss_concentration_with_later_recovery`, but fixes its role
as post-hoc localization. The normalized segment total differs from the locked
January–August run by one trade, one win, and 10 profit because each segment
receives the declared two-bar boundary seed; this is within the predeclared
three-trade reconciliation tolerance. The decision remains
`diagnostic_only_hold_feature_optimization`.

Files created or changed: forward diagnostic evidence engine, synthesis
builder and specification, deterministic tests, and result documentation. No
algorithm, campaign parameters, prospective Q4 declaration, or metric schema
changed. Tests completed: 96 deterministic tests, authoritative synthesis,
Python compilation, and whitespace validation.

Next coding target: none. Preserve the locked 2026Q4 prospective baseline
without partial execution or parameter changes until after December 31, 2026.

## 2026-09-06 canonical project status report

`QCRL_PROJECT_STATUS.md` now provides the canonical consolidated snapshot of
the repository: versions, modules, execution path, 160 collected campaign
cases, research progression and rejection rates, filter and regime findings,
historical/forward evidence, assumptions, known gaps, guardrails, and the next
execution-infrastructure phase. It explicitly records the 2.3.0 default versus
2.4.0 temporal-manifest mismatch and the legacy EMA manual default so neither
can be mistaken for the current unfiltered research candidate.

Files changed: the new status report plus navigation links in `README.md` and
`QCRL_ARCHITECTURE.md`. No source code, manifests, evidence, or tests changed.
All numerical claims were reconciled against the stored campaign and synthesis
artifacts. Next documentation action: fork the current task into a dedicated
documentation task only if requested, using this report as its source of truth.

## 2026-09-06 documentation architecture

The repository now assigns one authoritative document to each information
class. `QCRL_PROJECT_STATUS.md` remains the sole mutable current-state report;
this sync log remains append-only provenance. `docs/` adds a campaign and
synthesis registry, durable decision log, hypothesis/closure registry, schema
contract matrix, exact operator workflow, and documentation ownership rules.

The audit explicitly reconciled four recurring ambiguities: engine 2.3.0 versus
temporal manifest 2.4.0, the legacy EMA manual default versus the unfiltered
candidate, historical report/record schemas versus current v6/v5 contracts,
and implemented modules versus proposed discovery engines or notebook
prototypes. Root navigation now identifies older README result narratives and
older “current” sync sections as historical snapshots.

Files created or changed: documentation only. No research algorithm, test,
campaign parameter, synthesis declaration, collected evidence, schema, or
locked 2026Q4 declaration changed. Validation: deterministic tests, manifest
expansion audit, Markdown link audit, and whitespace validation.

Next documentation target: keep the registries synchronized with every new
declaration and verdict. Next engineering target remains the independent,
read-only Polymarket execution-truth foundation.

## 2026-09-07 QuantConnect push preflight

Inspection of the installed LEAN CLI established that cloud push already
selects only `.py`, `.cs`, `.ipynb`, `.css`, and `.html` source files.
Markdown documentation was never part of the QuantConnect upload set; the
earlier 64,000-character rejection came from an eligible source file rather
than the documentation layer.

`./synch.sh push-plan` now provides a read-only inventory of tracked eligible
files and their character counts without contacting QuantConnect. The guarded
`push` path runs the same preflight before confirmation and refuses locally if
any eligible file exceeds QuantConnect's 64,000-character per-file limit. This
currently catches a material margin risk: `qcrl_campaign.py` is less than 400
characters below the limit.

Files changed: synchronization guard, operator documentation, status, sync log,
and one deterministic sync-contract test. No algorithm behavior, campaign,
synthesis, evidence, schema, or prospective declaration changed. Tests
completed: 97 deterministic tests, shell syntax, and whitespace validation.

Next engineering target: the independent, read-only Polymarket execution-truth
foundation.

## 2026-09-07 execution-truth contract kernel

The first greenfield Polymarket execution-truth slice adds pure, credential-free
normalizers for two new contracts:
`qcrl.polymarket_market_contract.v1` and
`qcrl.polymarket_order_book.v1`. The market contract reconciles Gamma identity,
terms, state, and outcome-token pairs with CLOB V2 market constraints and fee
parameters. The book contract binds full depth to that validated market and
fails on identity, token, tick-size, minimum-size, duplicate-price, or crossed-
book drift. Both preserve canonical source and normalized-artifact hashes.

Files created or changed: `execution_truth/`, deterministic documentation-
derived JSON fixtures, execution-truth contract tests, schema/status/
architecture documentation, and this sync record. No signal algorithm,
campaign, synthesis, collected evidence, report/record schema, or locked 2026Q4
declaration changed.

Interfaces added: `normalize_market_contract()` and `normalize_order_book()`.
Record fields consumed: none; this lane remains independent of research records.
Assumptions introduced: current public Gamma and CLOB V2 responses must agree
explicitly; token order and slug grammar have no semantic authority; decimal
values remain strings at the evidence boundary. Limitations: fixtures are
documentation-derived, not live observations; no HTTP acquisition, signal-time
binding, replay, fill, or resolution reconciliation exists yet. New requests
for Workstream A: none. Tests completed: 107 deterministic tests passing.

Next coding target: an unauthenticated acquisition adapter with injected
transport and clock, followed by one immutable current BTC Up/Down market bundle
and offline replay through the new contracts.

## 2026-09-07 public acquisition and live contract correction

The public-only acquisition boundary is now implemented with an injectable
transport and clock, fixed Gamma/CLOB GET routes, per-response timestamps and
hashes, and no credential, signing, account, position, or order capability. Raw
bundles are content-addressed and refuse conflicting overwrite; offline replay
revalidates the bundle and both outcome books before producing a normalized
bundle.

A live probe of Gamma market `4309046` exposed and corrected a material timing
assumption. Gamma `startDate` reflected an earlier market lifecycle time, not
the five-minute outcome window. `eventStartTime` named the actual
`20:50:00Z`–`20:55:00Z` interval. Market contract v1 is therefore superseded by
`qcrl.polymarket_market_contract.v2`, which preserves both values separately and
uses only `event_start_at_utc` for the outcome window. Live terms also establish
Chainlink BTC/USD 60-second TWAP as the resolution source and equality as an Up
outcome; Coinbase is not resolution truth.

The first complete live raw bundle is stored locally under ignored
`.qcrl/execution_truth/raw/` with SHA-256
`a9c40ee7c38a6dad0f3482b4c0c9676dd4865bc26f7042f713b080bf141fc912`.
Its normalized bundle hash is
`bd7b59542b8b93d94c7525b255d567ba09e5175e6a3e6b287940663c86d3a6a6`.
The raw file is immutable locally but is not yet Git-synchronized.

Files created or changed: acquisition and bundle modules, contract v2,
deterministic fixtures/tests, execution-truth/status/schema/architecture
documentation, and this sync record. Interfaces added:
`PublicPolymarketAcquirer.acquire_market_bundle()`, `normalize_bundle()`, and
`store_raw_bundle()`. Record fields consumed: none. Assumptions introduced:
Gamma and CLOB public endpoints are independently observed evidence; only an
explicit event-start field may anchor the outcome interval. Limitations: market
ID discovery is not yet contract-driven, the live bundle is ignored local
state, and no signal binding, fill replay, or settlement reconciliation exists.
New requests for Workstream A: none. Tests completed: 114 deterministic tests.

Next coding target: contract-driven discovery, a deliberate durable live-fixture
workflow, and the signal-to-market timing/eligibility contract.

## 2026-09-07 contract-driven discovery and signal binding

Public discovery now starts from an explicit numeric series ID and selects the
unique event whose declared half-open interval contains the target time. The
normalizer then requires exact series membership, recurrence, asset, duration,
TWAP configuration, resolution source, binary outcomes, event times, and
orderability before returning one market. Slugs and titles are never selection
inputs. A live public probe validated series `10684`, event `978977`, and market
`4310537` for the declared `21:35Z`–`21:40Z` BTC five-minute interval.

The new binding layer hashes and joins a versioned directional signal intent,
market contract, timing policy, and decision time. Malformed evidence fails as
a contract error; normal incompatibility produces a deterministic ineligible
result with explicit reasons. Most importantly, the contract rejects the QCRL
daily target interval against the observed five-minute market. This repository
does not assume daily behavior is fractal or executable at a lower horizon.

Files created or changed: public acquisition, discovery and binding modules;
contract hash verification; deterministic series/event fixtures and tests;
execution-truth, schema, status, architecture documentation; and this sync
record. Interfaces added: `acquire_series_event()`, `normalize_discovery()`, and
`bind_signal_to_market()`. Record fields consumed: none; signal intent is a new
execution boundary, not a reinterpretation of research records. Assumptions
introduced: target intervals are half-open, series IDs are explicit config, and
only exact market fields authorize binding. Limitations: the validated series
is five-minute and incompatible with the current daily candidate; live evidence
is still ignored local state; the LEAN callback does not yet emit a live-timely
intent; replay, fills, and settlement remain absent. New requests for Workstream
A: none. Tests completed: 135 deterministic tests passing.

Next coding target: durable live-evidence promotion, exact-horizon discovery,
and a boundary-time signal adapter before execution replay.

## 2026-09-07 durable evidence and daily-series compatibility

The execution-truth operator now separates ephemeral public capture from
deliberate durable promotion. `./synch.sh evidence` captures discovery or full
market/book bundles into ignored local state, promotes only explicitly selected
artifacts into content-addressed Git storage, and verifies the complete tracked
inventory offline. The deterministic suite replays every promoted artifact.

Three live artifacts are now durable: the original Chainlink five-minute
market bundle, a discovery capture for daily series `41`, and a complete bundle
for daily market `4293892`. The daily event covered
`2026-09-07T16:00:00Z`–`2026-09-08T16:00:00Z`. It resolves from Binance
BTC/USDT one-minute candle closes, not Coinbase BTCUSD, and equal closes settle
50/50 rather than being skipped. The inventory therefore records the candidate
as incompatible with the current QCRL signal; daily recurrence is not treated
as sufficient equivalence.

Files created or changed: durable public evidence and inventory, evidence CLI
and sync routing, bundle/discovery verification, deterministic tests, status,
architecture, contracts, workflow, decision log, execution-truth documentation,
and this sync record. Interfaces added: `store_raw_discovery()`,
`promote_raw_evidence()`, `verify_raw_discovery()`, and
`verify_live_evidence_inventory()`. Record fields consumed: none. Assumptions
introduced: promotion is explicit; every durable artifact must be inventoried;
daily horizon alone does not establish source/window/settlement equivalence.
Limitations found: QCRL's daily consolidator anchor is not explicit, series 41
uses a different feed and tie rule, and no execution replay exists. New requests
for Workstream A: none; any aligned Binance/noon research must be separately
authorized and declared. Tests completed: 138 deterministic tests passing.

Next coding target: an explicit QCRL source/bar-anchor contract and boundary-time
signal adapter, followed by replay only for a genuinely compatible declaration.

## 2026-09-07 source contract and boundary-time signal adapter

The current research input is now a versioned execution boundary: Coinbase
BTCUSD minute trade bars consolidated into 86,400-second bars anchored at
midnight UTC, with open/close direction and tied bars skipped. The UTC anchor is
documented LEAN behavior for crypto daily time-period consolidators; it is no
longer an unresolved assumption.

The pure boundary adapter validates the source contract and each aligned,
contiguous completed bar, reproduces length-2 candle-streak reversal semantics,
and emits an intent for the next UTC day only when the streak exists and the
latest bar was available by the boundary. Every source bar, non-emission
decision, and intent dependency is hashed. Intent and binding contracts advance
to v2 so binding policy must approve the exact source-contract hash. V1 is
superseded rather than silently reinterpreted.

The adapter was tested against the durable daily market `4293892`: the QCRL
intent targets midnight UTC to midnight UTC and is rejected against the
market's noon-Eastern interval. This machine-enforces D-014 independently of
titles or slugs.

Files created or changed: source and signal modules/specifications, binding v2,
deterministic signal/binding tests, live evidence finding, schema/status/
architecture/decision/execution documentation, and this sync record. Interfaces
added: `normalize_source_contract()`, `normalize_source_bar()`, and
`materialize_boundary_signal()`. Record fields consumed: none. Assumptions
introduced: official LEAN crypto daily consolidation ends at midnight UTC;
signals target the next equal-duration interval. Limitations found: no live
data process invokes the adapter, and no compatible Polymarket daily contract
has been observed. New requests for Workstream A: none. Tests completed: 148
deterministic tests passing.

Next coding target: deterministic execution replay against durable books,
starting with taker price, depth, fees, partial fill, and no-fill truth.

## 2026-09-07 QuantConnect module-name compatibility correction

QuantConnect correctly refused the first cloud push of the boundary adapter
because `execution_truth/signal.py` conflicted with Python's standard-library
`signal` module. No cloud files were overwritten. The module is renamed to
`execution_truth/signal_adapter.py`; package imports and current contract
documentation were updated without changing schemas or behavior. The full
deterministic suite, import compilation, whitespace validation, and cloud
source-size preflight were rerun before synchronization.

The local push preflight now also rejects tracked Python filenames that shadow
standard-library modules, and a deterministic repository invariant test guards
the same rule. Tests completed: 149 deterministic tests passing.

## 2026-09-08 snapshot taker replay

Added `replay_taker_buy(raw_bundle, request, policy)` and an offline
`./synch.sh evidence replay <example>` command. The kernel revalidates raw
evidence and estimates BUY execution against sorted asks under price, quantity,
cash, and freshness constraints. FAK retains partial fills; FOK cancels all
candidate fills when full quantity cannot be funded or matched. Fee estimates
use the captured exponent-1 rate and a declared per-level half-up five-decimal
cash-equivalent model. Every result is hashed and labeled mechanics-only.

The live daily capture omits CLOB `itode`, although market contract v2 defaults
that omission to false. Replay checks the raw payload and rejects this case as
`unknown_taker_delay_state`. The five-minute capture explicitly enables delay.
Neither establishes immediately executable liquidity. A separate synthetic
fixture demonstrates full, partial, FOK-canceled, and nonmarketable orders;
captured evidence and research decisions remain unchanged.

Files created or changed: taker replay module, package exports, evidence CLI,
two runnable specifications, synthetic fixture, tests, schema/status/
architecture/operator documentation, replay guide, and this record. Interfaces
added: `replay_taker_buy()`. Record fields consumed: none. Assumptions introduced:
frozen displayed depth, six-decimal shares, cash-equivalent fees rounded once
per price level; no actual matching, latency, or settlement claim. Limitations:
aggregate depth lacks maker match detail, supported fee exponent is 1, unknown
or enabled delays require more evidence, and replay does not evaluate signal
eligibility. New requests for Workstream A: none. Tests completed: 168 tests.

Next coding target: explicit unknown metadata and documented delay semantics,
then timestamped book sequences for temporal execution replay.

## 2026-09-08 — Preserve unknown execution metadata

Continued the snapshot-replay follow-up by checking the official CLOB market
info reference. It defines `itode` as delay enablement and `oas` as minimum
order age; it supplies neither omitted-field defaults nor a crypto matching
delay duration. No zero-delay assumption is authorized by that evidence.

Market contract v3 replaces absent/null execution fields with explicit unknowns
and rejects malformed booleans or order-age values. This includes Gamma
`acceptingOrders` / `feesEnabled` and CLOB `itode` / `oas`. Replay result v2
consumes those normalized values and rejects unknown order age, unknown order
acceptance, and the previously blocked unknown delay or fee state. An explicit
nonzero minimum age remains unsupported by snapshot mechanics. Minimum age
and exchange matching delay are not interchangeable.

The daily raw capture omits both `itode` and `oas`; the five-minute raw capture
enables delay but also omits `oas`. Neither has been modified or supplemented
with later observations. Normalized bundle v2 embeds market v3. Inventory
derived hashes were deliberately regenerated:

- Daily `4293892`: prior `2d5f3b97685fe124191592c1175d15a71140909c4f34ed13231a872e25b58460`;
  current `8b11f8a53e03f29cb803c8c12ad3fb5b7920b00e32c2b774265dfdd7a9cc87fc`.
- Five-minute `4309046`: prior `bd7b59542b8b93d94c7525b255d567ba09e5175e6a3e6b287940663c86d3a6a6`;
  current `2958d62063a64c2d543ef42d391ea331bbb75e04c009b5efcc8a90d1553d46fa`.

Raw hashes remain unchanged. Old normalized contracts are superseded and must
be regenerated from raw input, not relabeled. Requests, policies, raw evidence,
research schemas, and the locked 2026Q4 campaign are unchanged.

Files changed: execution contract/bundle/replay modules; contract, acquisition,
and replay tests; live evidence inventory; current status/schema/execution/
replay documentation; this record. Engine interfaces added: none. Record fields
consumed: none. Assumptions introduced: missing and null normalize to unknown;
raw hashes retain the distinction. Limitations: delay semantics remain
unresolved, and no new market observation, order, fill, or settlement is claimed.
New requests for Workstream A: none. Tests completed: 176 deterministic tests;
all three live artifacts verify; daily replay explicitly rejects both missing
timing fields. See `docs/TAKER_REPLAY.md` for authoritative source links.

Next coding target: bounded read-only timestamped-book recording with metadata
gaps preserved; then temporal sensitivity analysis separating assumed latency
from exchange timing supported by evidence. No live-order path is authorized.

## 2026-09-08 — Bounded timestamped-book recorder

Added a finite public recorder for temporal liquidity observations. Each sample
is a complete raw market bundle: Gamma metadata, CLOB market metadata, and both
outcome books, each with its own observation time and payload hash. Refreshing
metadata on every sample prevents a later delay/order-age response from being
attached retroactively to an earlier book.

Raw schema `qcrl.polymarket_raw_book_sequence.v1` records capture bounds and all
complete bundles. Derived schema `qcrl.polymarket_book_sequence.v1` verifies
every nested raw/normalized hash, strictly increasing acquisition times, and
stable market/token identity, then emits compact metadata and top-of-book
summaries. Identical payloads remain distinct timed observations. Storage and
promotion are content-addressed; live inventory verification now supports
declared sequence artifacts. No live sequence was promoted in this change.

The CLI adds `evidence capture-sequence` and offline `evidence inspect-sequence`.
Capture is bounded before networking to 2–120 samples, 1–60 integer seconds
between complete samples, and at most one hour of scheduled pauses. Five
samples therefore make twenty public GETs. Any failed response aborts without
storing a partial artifact. Requested interval plus network duration is the
actual cadence; no fixed-frequency or continuous-liquidity claim is made.

Files created: `execution_truth/book_sequence.py`, `tests/test_book_sequence.py`,
and `docs/BOOK_SEQUENCE.md`. Files changed: execution package exports,
acquisition/bundle storage and inventory support, evidence CLI, schema/operator/
execution/replay documentation, architecture/status/map, and this record.
Interfaces added: `PublicPolymarketAcquirer.acquire_book_sequence()`,
`normalize_book_sequence()`, `store_raw_book_sequence()`, `capture-sequence`,
and `inspect-sequence`. Record fields consumed: none. Assumptions introduced:
the interval is a pause between complete samples; state and constraints may
change while identity/outcome mapping may not. Limitations: polling misses
intervening states and proves no queue, latency, match, fill, or settlement.
New requests for Workstream A: none. Tests completed: 184 deterministic tests.
The three existing live artifacts still verify; no credentials or orders used.

Next coding target: sequence-based latency sensitivity using only an observed
book at or after hypothetical arrival, with polling uncertainty explicit and
exchange delay remaining unknown unless supported by contemporaneous evidence.

## 2026-09-08 — Auditable slug-to-market resolution

Added public slug resolution so sequence capture no longer requires a manually
copied numeric market ID. The official Gamma API distinguishes event-slug and
market-slug endpoints. Because a normal Polymarket URL is `/event/<slug>`, the
operator default is event. Event resolution proceeds only when the response
contains exactly one market; it rejects a multi-market event instead of making
a semantic choice. `--kind market` selects the distinct direct market route.

Raw schema `qcrl.polymarket_raw_slug_resolution.v1` preserves the exact slug,
reference kind, endpoint response, observation time, payload hash, resolved
numeric market ID, and whole-artifact hash. Verification checks endpoint,
parameters, response slug, candidate cardinality, numeric identity, chronology,
and hashes. Storage, explicit promotion, and live inventory verification support
the artifact. No slug lookup is treated as QCRL source/window compatibility.

The CLI adds `evidence resolve-slug` and `evidence capture-sequence-slug`. The
latter stores a complete resolution artifact, prints the ID, and then begins the
existing bounded sequence. If sequence acquisition later fails, the complete
resolution may remain locally; no partial sequence is stored.

Files created: `tests/test_slug_resolution.py`. Files changed: acquisition,
discovery verification, bundle storage/promotion/inventory support, package
exports, evidence CLI, book-sequence/schema/operator/execution documentation,
architecture/status, and this record. Interfaces added:
`PublicPolymarketAcquirer.resolve_market_slug()`,
`verify_raw_slug_resolution()`, `store_raw_slug_resolution()`, `resolve-slug`,
and `capture-sequence-slug`. Record fields consumed: none. Assumptions: the
operator explicitly distinguishes event versus market slug; `/event/` is the
CLI default. Limitations: single-market cardinality does not prove strategy
compatibility or execution. New requests for Workstream A: none. Tests completed:
192 deterministic tests. No credentials, orders, or live evidence promotion.

Next coding target remains sequence-based latency sensitivity after a small
public integration capture from a currently open single-market event.

## 2026-09-09 — Promoted temporal evidence and latency sensitivity

Promoted two exact public slug resolutions and their bounded five-sample book
sequences into the durable live evidence ledger. The 15-minute market is
`4364938`, with normalized sequence hash
`bf31ec40cc144879dc2cfd34a683d5f991aca78dd1989702dd2be8cb7d1310a9`;
the daily market is `4338480`, with normalized sequence hash
`2db13fc463dc78e266b17b66280d78cb15410e34af47b438ba7c505f83494604`.
Inventory verification now covers seven content-addressed raw artifacts. The
15-minute market uses a Chainlink BTC/USD 60-second TWAP and the daily market
uses Binance BTC/USDT with a non-midnight-UTC window, so neither observation is
silently treated as compatible with the frozen Coinbase daily research lane.

Added deterministic sequence-based latency sensitivity. A versioned policy
declares unique increasing integer latency assumptions and a maximum acceptable
observation lag. For each hypothetical arrival, the engine selects only the
first requested-token book observed at or after that arrival, preserves the
prior observation and polling bracket, and runs the existing guarded taker
mechanics on the selected observation. It never interpolates an unseen book or
equates an assumed latency with measured exchange behavior. Both live examples
exercise the selection path but their nested replays reject: the 15-minute
market requires temporal delay handling and lacks minimum-order-age evidence;
the daily market lacks both delay-state and minimum-order-age evidence.

Files created: `execution_truth/latency_sensitivity.py`,
`tests/test_latency_sensitivity.py`, `docs/LATENCY_SENSITIVITY.md`, two live
latency specifications, and four promoted raw evidence artifacts. Files changed:
execution package exports, evidence CLI, live inventory, schema/operator/book/
execution documentation, architecture/status, and this record. Interface added:
`evaluate_latency_sensitivity()` and `evidence latency`. Record fields consumed:
raw sequence sample and per-book observation times, token IDs, and normalized
market/replay fields. Assumptions introduced: declared latency is relative to
the request decision time, and the first later observation is the only admissible
proxy. Limitations: five polls do not estimate latency distributions, continuous
liquidity, queue state, matching, fills, or settlement. New requests for
Workstream A: none. Tests completed: 200 deterministic tests; all seven live
artifacts verify; both live latency outputs are deterministic.

Next coding target: collect repeated predeclared sequences across market phases,
then add descriptive cross-sequence stability analysis without tuning the
latency grid to these two small captures. No credentials or order path is
authorized.

## 2026-09-09 — Predeclared market-phase capture protocol

Added a versioned early/middle/late capture protocol so temporal evidence is no
longer selected at convenient post-hoc times. Protocol v1 binds one exact slug,
event window, resolution source, evidence role, lock time, and three ordered
phase captures. Each capture has an exact UTC start, bounded start tolerance,
sample count, and interval. Phase labels must fall in their corresponding third
of the market window, and the complete allowed schedule must end before market
close. A missed capture is reported as `missed` and cannot be retimed under the
same protocol.

Local state v1 is hashed and bound to the exact protocol hash. Execution is
explicit per phase and first re-resolves the market slug. Event start, end, and
resolution source must exactly match the locked declaration before any sequence
requests. Only a complete sequence stores the contemporaneous resolution and
sequence and atomically records their paths and raw/normalized hashes. Status
and dry-run commands make no network requests; `--execute` is required for the
bounded public acquisition. Nothing is promoted automatically.

The first locked protocol targets the September 11, 2026 daily BTC market. It
declares 12 five-second samples at 17:00 UTC September 10, 04:00 UTC September
11, and 15:00 UTC September 11, each with a ten-minute start tolerance. This is
a Binance noon-Eastern compatibility audit and remains incompatible with the
frozen Coinbase midnight-UTC QCRL signal. It is one-market evidence, not a
cross-market stability sample.

Files created: `execution_truth/capture_protocol.py`,
`tests/test_capture_protocol.py`, `docs/CAPTURE_PROTOCOL.md`, and
`execution_truth/protocols/btc_daily_phase_capture_20260911.json`. Files changed:
execution package exports, evidence CLI, schema/book/operator/execution docs,
architecture/status/map, and this record. Interfaces added:
`validate_capture_protocol()`, `capture_protocol_status()`,
`execute_protocol_capture()`, `protocol-status`, and `protocol-capture`. Record
fields consumed: exact slug kind, event bounds, resolution source, phase start,
tolerance, sample count, and polling interval. Assumptions introduced: thirds of
the market duration define early/middle/late; a ten-minute operator window is
acceptable for the locked daily audit. Limitations: no waiting daemon, retries,
automatic promotion, continuous book, cross-market inference, queue, fill, or
settlement. New requests for Workstream A: none. Tests completed: 207
deterministic tests; the protocol status and dry run contact no public endpoint.

Next target: complete the three declared captures. Only then add descriptive
cross-sequence spread, depth, displacement, metadata, and polling-gap analysis,
with missing phases retained rather than imputed.

## 2026-09-16 — Promoted complete daily phase evidence and stability analysis

Deliberately promoted the September 15 market's three predeclared slug
resolutions and three 12-sample book sequences. The live evidence inventory now
declares 13 artifacts and replays all of them offline. Added deterministic
early/middle/late description for price, spread, midpoint, top size, displayed
depth, book changes, execution metadata, polling gaps, and cross-phase midpoint
displacement. Missing phases are rejected; one-sided books retain null
spread/midpoint results rather than being imputed.

Files created or changed: six promoted raw artifacts, live inventory,
`execution_truth/phase_stability.py`, a September 15 phase-stability spec,
tests, CLI/package exports, phase-stability documentation, schema/operator/
capture/execution documentation, project status, and this record. Interface
added: `analyze_phase_sequences()` and `evidence phase-stability`. Record fields
consumed: normalized full book depth, best sides, exchange hashes, snapshot
hashes, acquisition times, capture bounds, sample cadence, identity, and
execution metadata. Assumptions introduced: none beyond descriptive use of the
first available two-sided midpoint as a phase anchor. Limitations: one complete
market does not establish cross-market stability; displayed depth is not fill
evidence; polling gaps are not latency; Binance noon-Eastern remains incompatible
with the Coinbase midnight-UTC signal. New requests for Workstream A: none.
Tests completed: 209 deterministic tests; all 13 promoted artifacts replay
offline. Next coding target: repeat the locked protocol across independent
markets before any cross-market claim,
then apply the fixed latency grid per phase without tuning it to these captures.

## 2026-09-16 — Fixed-grid phase latency and multi-date BTC locks

Reconciled the phase-capture record: September 11 collected early and missed
middle/late; September 13 collected early/late and missed middle; September 15
is the first complete promoted early/middle/late market. Missing phases remain
missing and were not retimed or imputed.

Applied the existing `[0, 1, 5, 10, 15, 20]` second latency grid and six-second
maximum observation lag independently to all three September 15 sequences. All
eighteen rows selected an observed book within policy, while every nested replay
rejected `unknown_taker_delay_state` and `unknown_minimum_order_age`. Result
hashes are `d861eba79e...98b` early, `56e3ffb50c...b0c` middle, and
`c074674d45...e08` late. Up asks were stable within each short capture at 0.58,
0.21, and 0.001 respectively; this is market-phase displacement, not measured
latency or fill evidence.

Locked three additional BTC daily protocols ending September 18, 20, and 22.
They hold the asset, Binance source, noon-Eastern daily window, relative phase
times, ten-minute tolerance, twelve samples, and five-second interval constant
while varying market date across weekday and weekend conditions. A second asset
is intentionally excluded from this cohort and would require a separate
declaration.

Files created or changed: three latency specifications, three capture protocols,
latency regression coverage, status/architecture/sync, and latency/capture/
operator documentation. Interfaces added: none. Record fields consumed: the
three promoted September 15 sequences. Assumptions introduced: none beyond the
already locked latency and capture policies. Limitations: replay timing metadata
remains unknown; one complete plus three prospective markets cannot yet support
a cross-market verdict. New requests for Workstream A: none. Tests completed:
210 deterministic tests; all 13 promoted artifacts verify offline.

Next target: execute the nine prospectively scheduled phase captures, preserve
misses, promote complete evidence deliberately, and only then implement a
cross-market descriptive aggregate.

## 2026-09-23 — Promoted multi-date evidence and cross-market phase analysis

Reconciled the locked September 18, 20, and 22 protocols without retiming or
imputation. September 18 completed early, middle, and late. September 20 and 22
each completed early and late while middle remained missed. Deliberately
promoted all 14 valid raw artifacts—seven exact slug resolutions and seven
12-sample sequences—rather than selecting only complete markets. The durable
inventory now declares and replays 27 artifacts offline.

Added a coverage-aware cross-market phase analyzer and a versioned specification
covering September 15–22. It requires exact phase keys, explicit `null` misses,
at least two complete distinct markets, matching daily duration/source/outcome
shape, and actual capture placement within the declared phase. Partial markets
contribute only observed phase aggregates; complete early-to-middle-to-late
paths are reported separately. The deterministic result hash is
`e3bdac21b4cbc44aeddbfc8b0357d15368b6d3489a0feb4210f63fc6b743d5bf`.

All four early observations were two-sided, with Up first midpoints from 0.495
to 0.575 and spreads from 0.01 to 0.02. Only two middle cells exist; both had a
0.01 spread, but their Up anchors diverged at 0.205 and 0.735. Late state was
heterogeneous: two markets were one-sided, two retained both sides, and three
of four were one-sided or at a directional extreme. Displayed depth varied by
more than an order of magnitude. One September 18 late polling gap was
1007.056607 seconds; the artifact is retained but labeled degraded cadence.

Files created or changed: 14 promoted raw artifacts, live inventory,
`execution_truth/cross_market_phase.py`, the four-market specification, tests,
CLI/package exports, cross-market documentation, schema/operator/capture/
execution/phase documentation, architecture/status, and this record. Interface
added: `analyze_cross_market_phases()` and `evidence cross-market-phases`.
Record fields consumed: normalized market identity and contract terms, capture
and sample times, requested cadence, execution metadata, full displayed depth,
best sides, spreads, and midpoints. Assumption introduced: a sequence receives a
cadence warning when its maximum polling gap exceeds twice its requested
interval; the warning does not exclude evidence. Limitations: two complete
markets do not establish stability; partial phases remain partial; directional
extremes are not signal evidence; Binance noon-Eastern remains incompatible
with QCRL's Coinbase midnight-UTC lane; public books do not establish fills,
settlement, or profitability. New requests for Workstream A: none. Tests
completed: 214 deterministic tests; all 27 promoted artifacts verify offline.

Next coding target: version a batch application of the unchanged latency grid
over every observed phase, then add public settlement evidence and terminal
market reconciliation without credentials or orders.

## 2026-09-23 — Cohort latency batch, settlement join, and scheduler audit

Applied one versioned request template and the unchanged six-point latency grid
to every observed phase in the four-market cohort. Ten sequences produced 60
assumed-arrival rows. All 60 selected a qualifying observed book, while all 60
nested mechanics results rejected unknown taker-delay state and minimum order
age. Six rows also rejected stale exchange-book timestamps: three in September
18 late and three in September 20 early. The deterministic batch hash is
`e86e727cf6b49b5bbff8aef219f92390dd44aea4c0e2897ebcc8dac318e086f6`.

Added read-only public settlement acquisition, strict Gamma/CLOB identity and
payout normalization, content-addressed storage/promotion, and latest-book
reconciliation. Four resolved artifacts expand the durable inventory to 31.
Platform winners were Down, Up, Down, and Up for September 15, 18, 20, and 22.
Each latest observed book favored the eventual platform winner; September 22
was only 0.755/0.245, demonstrating that direction agreement is not necessarily
terminal pricing. The deterministic cohort hash is
`0bc2068a79d7bde0dcfcc7938f2f186d1efac4fb9086ac986df3cb5b5af012cc`.
This is platform payout evidence, not independent Binance candle verification,
signal accuracy, fill, wallet credit, redemption, or profitability evidence.

Audited the two missed middle captures. September 20's task was scheduled for
04:00 UTC but began at 04:14:23, beyond the locked 04:10 deadline; the protocol
correctly rejected it before networking. September 22 began at 04:09:47, but
the default shell sandbox could not resolve `gamma-api.polymarket.com`, and no
network-enabled retry occurred before the window closed. Identical elevated
commands succeeded for other phases. The failures therefore reflect scheduler
dispatch latency and sandbox networking, not evidence that Polymarket DNS was
down. Future strict captures require a preauthorized network path and a local
OS scheduler or dedicated recorder; retrospective windows remain unchanged.

Files created or changed: latency batch and settlement modules, two versioned
specifications, four promoted settlement artifacts, live inventory, acquisition/
storage/CLI/package exports, tests, latency/settlement documentation, schema/
operator/capture/execution documentation, architecture/status, and this record.
Interfaces added: `evaluate_latency_phase_batch()`, `normalize_settlement()`,
`reconcile_settlement()`, `reconcile_settlement_cohort()`,
`capture-settlement`, `latency-batch`, and `settlement-cohort`. Record fields
consumed: observed sequence identity/timing/books, Gamma resolution/orderability/
payout fields, and CLOB condition/outcome/token mapping. Assumptions introduced:
latest reference price uses midpoint when two-sided and the available best side
when one-sided; it is descriptive only. Limitations: public settlement is not
independent source verification, and agent schedules are not hard real-time.
New requests for Workstream A: none. Tests completed: 221 deterministic tests;
all 31 promoted artifacts verify offline.

Next coding target: independently reconcile the declared Binance one-minute
candle closes, then replace agent-scheduled strict captures with a
network-preauthorized local recorder before locking another cohort.

## 2026-09-23 — Independent resolution source and local capture worker

Added a public Binance resolution-source lane that requests exactly one
BTCUSDT one-minute kline at each market's declared start and end boundaries.
The offline contract verifies request parameters, millisecond open/close times,
payload hashes, source, symbol, interval, market ID, and the exact 24-hour
window before deriving Up, Down, or Split. Four content-addressed artifacts
expand the durable inventory to 35. Their calculated outcomes are Down, Up,
Down, and Up for September 15, 18, 20, and 22, matching all four platform
payout records. The deterministic cohort hash is
`abb31376d2b1afd7152cb34e6521104005528393c72675e533ceb6a7f88d31e5`.

Added a local capture worker for future OS-scheduled protocols. It retries only
transient `AcquisitionError` failures with bounded exponential backoff, refuses
to sleep past the locked start deadline, preserves atomic capture state, and
returns a hashed attempt report. Contract, identity, term-drift, and timing
errors remain immediately fatal. An inert launchd template is checked in but
has no calendar trigger and was not installed; no future protocol or schedule
was activated.

Files created or changed: Binance acquisition/normalization/reconciliation,
capture worker, CLI/package/storage/inventory integration, one versioned cohort
specification, four promoted raw artifacts, two focused test modules, launchd
template, resolution/worker documentation, schema/operator/capture/settlement
documentation, architecture/status, and this record. Interfaces added:
`PublicBinanceAcquirer`, `normalize_resolution_candles()`,
`reconcile_binance_settlement()`, `reconcile_binance_cohort()`,
`run_capture_with_retries()`, `capture-binance-resolution`,
`binance-settlement-cohort`, and `protocol-capture-retry`. Record fields
consumed: exact event boundaries, Binance kline open/close timestamps and close
price, platform winner, market ID, and capture deadline. Assumptions introduced:
the named final one-minute candles are represented by klines opening exactly at
the two declared boundaries. Limitations: later public API observations do not
prove original-time availability or audit Polymarket's internal oracle; local
retry cannot overcome categorical host network denial or hard scheduler delay.
New requests for Workstream A: none. Tests completed: 232 deterministic tests;
all 35 promoted artifacts verify offline.

Next coding target: do not tune signals from these observations. Before another
prospective cohort, declare dates first, instantiate network-preauthorized local
schedules from the inert template, and perform a dry-run/network smoke test.
The next execution-truth analysis should then quantify terminal-price path and
resolution timing only if it can be declared before capture.

The first direct QC synchronization attempt for this commit returned HTTP 413
because LEAN CLI recursively included the repository-only Python test suite in
the project upload. `synch.sh` now constructs an ephemeral project containing
`config.json` and tracked runtime/research source while excluding `tests/`.
The upload plan and actual push consume the same file selector; failed staging
is retained for inspection, while successful staging is removed. GitHub remains
the authoritative home of the complete 232-test suite.

A first staging implementation placed the temporary project beneath the real
workspace. LEAN normalized that nested path and temporarily used it as the
cloud project name while updating the files. The corrected stage is an isolated
temporary LEAN root with a symlink to the existing `lean.json`; its sole project
directory is named exactly `polymarket-martingale`, so the corrective push
restores and preserves the canonical cloud name. The normalized local staging
directory created by the first attempt was removed.

## 2026-09-23 — First network-preauthorized prospective capture

Public discovery found exact daily markets for September 24 and 25. September
24 had already opened and was excluded. Locked
`btc-daily-phase-capture-20260925-v1` at 20:56:07 UTC on September 23, before
the September 24 16:00 UTC event start. Gamma reported market ID `4883052`, the
expected 24-hour interval, and the unchanged Binance BTC/USDT resolution
source. The protocol preserves 12 samples at five-second intervals and the
fixed 17:00/04:00/15:00 UTC early/middle/late geometry.

Added a repository-only launchd generator that rejects late generation,
produces unique per-protocol/per-phase labels, includes Year/Month/Day to avoid
annual recurrence, calls the deadline-aware retry worker with absolute paths,
and leaves installation explicit. Operations and tests are excluded from the
QC runtime staging payload but remain in GitHub. Files created or changed: one
locked protocol, generator/package files, generator and sync tests, capture and
worker documentation, status, sync selector, and this record. Tests completed:
235 deterministic tests. New requests for Workstream A: none.

Next operational gate: generate and validate the three local jobs, prove public
DNS/HTTPS from the launchd GUI domain, then bootstrap and inventory the jobs.
Subsequent cohort markets may be locked only before their event windows and
must not be selected from September 25 results.

Completed that gate. The one-shot launchd smoke job exited 0, resolved the exact
slug to market `4883052`, and wrote a content-addressed local artifact with an
empty stderr log. It was then unloaded. The early, middle, and late jobs were
bootstrapped into GUI domain 501; all report zero runs and the expected absolute
paths. Production jobs are wrapped in `caffeinate -dimsu` so the host remains
awake throughout polling and status persistence. Because caffeinate cannot wake
an already sleeping Mac, explicit wake coverage remains the last host-level
prerequisite.

## Synchronization rule

At the end of each Discovery coding session, append a dated sync block containing:

```text
files created or changed
engine interfaces added
record fields consumed
assumptions introduced
limitations found
new requests for Workstream A
tests completed
next coding target
```

---

# One-Sentence State

> Historical QCRL evidence supported the untouched daily signal, locked forward
> evidence degraded it, feature optimization is on hold, and the next independent
> lane is read-only Polymarket execution-truth infrastructure while 2026Q4 remains
> locked.

## 2026-10-12 — Intel migration continuation and finite wait comparison

Read repository workflow, migration receipt and frozen native diagnostic/prototype
records on clean branch `codex/lupus-development` at `f05d5dd`. Added the v1
absolute/select finite comparison declaration, an offline integer target expander
and focused tests; updated current engineering status and prototype navigation.
No engine interface or prior evidence/measurement plan changed. No record fields
consumed from live data. The comparison measures inclusive lateness and assumes
no exclusive causal explanation; AB/BA ordering leaves host/time confounding.
All historical evidence stays frozen and requires its originating source checkout.
New requests for Workstream A: none. Twelve focused local tests passed; Python 3.9
syntax checks passed. Full local regression verification is recorded in the new
preregistration document. No native binding/sleep, captures, infrastructure,
credentials, remote sync, commit or push performed.

Next coding target: implement offline-injected select/absolute collection,
unknown/stop handling, bounded exclusive publication and independent evaluation,
then separately verify native compatibility and freeze the execution envelope
before requesting any Linux run. This declaration does not unlock the recorder
application cohort or reopen Q4 signal research.

## 2026-10-13 — Wait-comparison pre-integration contract review

Pinned the literal v1 declaration hash in a regression test and repaired both
absolute-adapter exception paths to bound the complete name/message to 160
characters. Added long-name/message, two-fault and hash/no-retry fixtures. No
engine interfaces or frozen evidence changed. Fourteen focused offline tests
passed on Intel macOS / Python 3.14.6; Python 3.9 syntax checks passed. The prior
full-suite result predates this repair. No new Workstream A requests.

Disclosed upstream Python 3.9 select's automatic EINTR retry behavior in the
preregistration and handoff. Installed Linux behavior remains unverified; v1's
single-request/no-concealed-EINTR gate is unresolved and requires prospective
resolution before native execution. No changed protocol hash, successor, native
integration, capture, infrastructure, credentials or cloud sync in this review.

## 2026-10-13 — Prospective v2 retry disclosure and offline comparison

Declared `absolute-select-finite-v2` with predecessor linkage and literal hash
pin. Preserved v1's hash, geometry/budgets and historical evidence. One application
select call can include unknown runtime retries; exposed exceptions/errno stop
attempts without application resubmission. Added injected select wait/finite
collector and serial publication-before-next-run lifecycle, independent
population/arithmetic/authority validation, exact rational descriptive pairs/
medians and bounded exclusive run/summary publication. Updated handoff, current
status and schema documentation. No engine interface or live input fields added;
new Workstream A requests: none. Thirty focused tests passed; full offline suite
and Python 3.9 syntax checks are recorded in the v2 document.

Limitations: installed Linux select retry/signal semantics and native ABI/symbol
compatibility remain unverified; exclusive publication is not atomic/fsync proof.
Native process-timeout/journal retention requires the future bounded launcher.
Next target: finite compatibility declaration, source/runtime envelope and offline
launcher lifecycle tests. No native integration/run, captures, credentials,
infrastructure, main merge or QuantConnect sync performed.

## 2026-10-13 — Finite compatibility declaration and offline envelope rehearsal

Added a separate pinned two-wait compatibility protocol, broad bounded tracked
source hashing and pure runtime/ABI/review-hash freeze validation. Added injected
private lifecycle rehearsal and unit specifications without a worker entrypoint
or command executor. Tests cover source selection/symlink/size/metadata refusals,
serial readiness/binding/release/completion and scoped cleanup on faults/drift.
Updated handoff, project status and schema documentation. No engine interfaces,
live fields or Workstream A requests. Thirty-eight focused local tests passed;
full regression and Python 3.9 syntax checks are recorded in the preparation doc.

Declared metadata does not prove installed Linux behavior or native origin. No
actual runtime receipt/freeze was generated. Production workers, bounded context/
journal/control adapters and timeout/host-loss retention remain next offline
work. No native binding/sleep/unit execution, infrastructure, credentials,
capture, main merge, QC sync or frozen-evidence mutation performed.

## Compatibility worker and bounded production adapters — offline continuation

Implemented the declared compatibility worker, retained unknown/setup/fatal arm
slots, guarded native source/runtime and readiness/release gates, and bounded
exclusive durable control/result publication. Implemented production adapters
for fresh scoped stages, fixed test/compatibility commands, bounded helpers,
effective properties and live PID/boot/cgroup binding, scoped cleanup, partial
journals and byte-hashed origin inventories. No new diagnostic layer or engine
interface; no new Workstream A requests. Scientific plan hashes are unchanged.

Fixed a concrete validation gap allowing fatal collector errors alongside observed
rows, and a concrete select-module portability case requiring reviewed builtin vs
extension binary identity. Fifty-two focused tests and all 1,077 offline tests
passed (72.618 seconds for the full suite). New Python files pass Python 3.9 syntax
parsing. Offline subprocess fixtures test cap/timeout/nonzero behavior; ABI/runtime
observations are mocked. Source-only sealing uses the clean committed implementation.
Installed Linux review/runtime freeze requires read-only remote authorization;
compatibility execution needs separate approval. No native smoke, comparison,
credentials, infrastructure, main merge or QC sync.

## 2026-10-14 — Read-only SSH authorization and access prerequisite

Operator authorized read-only EC2 SSH inspection. Local metadata checks found the
documented key absent, no SSH-agent identities/configuration and no existing pin
for the historical host address. No remote/AWS call or infrastructure/access-rule
change occurred; the older default AWS profile was not used. Requested the
approved connection method. Rechecked the existing 2cb6880 source-only receipt;
source and evidence remain frozen, Linux runtime review is still pending.
Updated handoff only; no code changes or new tests needed. Native compatibility
and comparison execution remain separately gated. No new diagnostic layer.

## 2026-10-14 — Authorized dedicated Lupus SSH key generation

Generated the operator-approved fresh key outside Git, verified permissions and
recorded only its public fingerprint in the handoff. A strict noninteractive SSH
check reached the provided host but refused its unknown ED25519 host key; no
remote command ran and no pin was bypassed. Public-key installation/trusted pin
handoff requires an existing authenticated path from the original Mac. No AWS
legacy credential use, infrastructure change, native experiment or source/evidence
modification. Documentation-only continuation; no regression rerun needed.


## 2026-10-14 — Read-only Linux provenance and source/runtime freeze

Operator approved the existing AdministratorAccess console session solely for
Session Manager runtime/source inspection after the automatic review gate.
Observed Linux aarch64/glibc 2.34/Python 3.9.25, LP64 timespec offsets 0/8,
monotonic clock metadata, existing handlers and clock_nanosleep symbol/signature
without calling a wait. Installed binary hashes matched RPM manifests and final
rechecks; public services/boot identity stayed unchanged. No remote writes,
package installation, key installation, infrastructure or service changes.

Locally verified official release repository checksums, exact source/binary RPMs
and official select payload equality to installed bytes. Matching SRPM spec and
43 declared patches leave selectmodule.c unchanged; source confirms disclosed
EINTR signal check and recomputed-timeout retry. No independent RPM signature
verification or reproducible build claim; no causal scheduling conclusion.

Private review `.qcrl/reviews/wait-runtime-20261014-jlwy2fu9/` retains inputs,
observation/review and execution freeze. Full freeze
`8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`
binds unchanged 488-file source candidate 2cb688039f1b0c0bf4bae4f783902759aa263aef.
Original source-only receipt, declarations and scientific evidence are preserved.
Local 1,078 tests/53 focused checks remain Mac offline evidence. No native unit,
Linux regression or compatibility wait ran. Ready for separate authorization of
fresh private staging/preflight, one bounded Linux regression unit and conditional
single two-wait compatibility unit; no retry/replay or comparison advancement.
All native/compatibility/acceptance/order authority flags remain false.


## 2026-10-14 — Single authorized Linux compatibility attempt completed

Operator authorized private staging, bounded Linux regression and the conditional
single two-wait compatibility smoke. Fresh private stage recorder-wait-20261014Lupus01
bound exact candidate 2cb6880 and full freeze 8fd4a9557b16; no credentials imported,
packages installed, infrastructure or public collectors changed. Live preflight passed.

Linux regression: 1,078 discovered in 105.240 seconds; 1,077 passed and one existing
Python 3.10+ stdlib-module-inventory test skipped on Python 3.9.25. Then select and
absolute returned code 0 at the declared epoch+50/100 ms targets with valid brackets,
no errors and zero application retries. Select internal retry count stays unknown.
Both private units stopped; public/environment/source/runtime state unchanged.
No retry, replay, signals or AB/BA comparison. No performance or causal conclusion.

Retained local evidence: .qcrl/reviews/wait-compatibility-native-20261014Lupus01/.
All twelve native files match origin inventory 2770fc0c1313cb65f70770212f5d0076014961d8c673788c3b30ea70593e8da7.
Result a8927bd009b4218869a1fa91dd3b357017f963c5d97f1df427e9beefa03dcc0a;
separate offline native audit c5f7e48f1dc97f38966a0d5c7dcd51761cf2f1f5644c09b446c018bb85f3a0cb
checks origin, byte hashes, live process/unit envelope, readiness/release and bracket
arithmetic. Verdict: native origin and finite interface compatibility verified;
performance, recorder acceptance, comparison execution and orders remain false.
Existing producer/freeze flags, plans and historical evidence were not rewritten.
The one-smoke authorization is consumed; further native execution needs a separate
approval. No concrete failure requires a new diagnostic layer or protocol change.


## 2026-10-14 — Offline native transport for unchanged comparison v2

Relayed two-run continuation prompted readiness review. Original frozen candidate
2cb6880 has no comparison entrypoint; implemented a separate bounded transport and
retained-byte auditor offline. All original Python files and scientific plan hashes
remain unchanged. New source requires its own freeze/direct native authorization.
No comparison, new Linux test unit or extra compatibility smoke ran.

Controller preserves AB/BA ordering, cumulative integer targets, 16 baseline pairs,
75% CPU/512 MiB/32 tasks/240 seconds, denied comparison IP access, fatal cancellation,
nonfatal missed-target continuation and no replay/tuning. Original production
helpers and bounded context snapshots are reused; no diagnostic acquisition layer.
Fault tests cover gates/publication/cleanup and rehashed byte/identity/unknown loss.
Transport-only KeyboardInterrupt conversion retains earlier rows at wait/clock
boundaries without handler changes or retries. Escaping interrupts/kills before
publication leave explicit unavailable cells, not invented epochs/success rows.
Exact native regression population must be 1,093 with the existing Python 3.10+
inventory skip; extra skips or missing tests stop before measurement. Source seal
and final local verification are recorded after the implementation milestone.

Final candidate local verification: all 1,093 offline tests passed in 90.520 seconds;
68 focused tests and Python 3.9 syntax checks pass. The seven-file diff preserves
every prior Python byte and all three frozen declaration hashes. No new native
unit or comparison result. Seal the exact implementation revision before requesting
direct authorization of this new execution source.


## 2026-10-14 — New comparison execution candidate sealed

Candidate b7db2c25d8550b3f75d3324846f45b2ad4c3503d, 491 selected files verified
against exact Git bytes; all previous Python files and plan hashes unchanged.
Full freeze f1339e0b54b84703368fc39efdfeb7c470ce4220bbb15d6df8284e46c0036f61
reuses the reviewed runtime and original native compatibility prerequisite.
Private receipt .qcrl/reviews/wait-comparison-source-b7db2c25d855/; local verifier
4bb24cc655edafd303d91ef1608785f91165e9ab2f38ba52aaff3e6c4e335b2c records
1,093 offline tests/68 focused tests/Python 3.9 syntax, with no new Linux/native
validation or execution authorization. Later receipt docs do not replace this
source candidate. Direct approval of the exact new freeze is pending. No new
remote stage, unit, comparison result, tuning, replay or extra compatibility smoke.


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


## October 15 — Prospective recorder smoke transport

The next target is exactly one native recorder compatibility smoke, not another
isolated timing comparison. The smoke-only controller has one readiness-regression
unit, one producer and one recorder; no cohort route. It sends original corpus
occurrences 0..67 at epoch+j seconds, frame limit 68/capture limit 180 seconds,
20-second epoch lead and 100-ms readiness margin. Separate live PID/cgroup bindings,
fixed commands/limits, one capture per unit and scoped cleanup are audited offline.
Every unit retains CPU 75%, memory 512 MiB, 32 tasks and 240 seconds; numeric IPv4
localhost only. See [exact smoke preparation](RECORDER_ABSOLUTE_SMOKE_PREPARATION.md).

The 2-ms to 50-ms CPU pre-read lead **changes measurement timing** despite unchanged
budgets. Prospective observer policy remains bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f;
new smoke plan is e3b86ea5be1482c7352552459ab14df365789f12b74e37c746adcdb1b529321d.
The producer adds an explicit injected transmitter; its legacy default is unchanged.
This changes its source-bound declaration prospectively. The October 14 declaration
41187030fbf5825311b03c0558bd137b104b7d692078a11777b7bf4242931e15 and private receipt remain
historical frozen identities, not the new candidate. No earlier unknown or result
is repaired; original recorder c9207f... declaration and absolute-wait code stay fixed.

Read-only Session Manager inspection on October 15 observed the existing Linux
Python 3.9.25/aarch64/glibc 2.34 runtime, unchanged boot and public collector/hash
context, and byte-hashed all 60 installed websockets 15.0.1 distribution files.
The EC2 console showed t4g.small/two vCPUs/standard credit mode. The instance role
denied credit-description API access; no IAM change. Console observation is
retained honestly as console evidence, not substituted raw API output. Credit
balance remains unknown. The original cohort host-context gates still apply later.
Private preparation receipts: `.qcrl/reviews/recorder-smoke-preparation-20261015/`.

Offline fixtures exercise full synthetic archives, byte anchors, ordered corpus,
completion/durability linkage, binding/release/lifetime/limit and rehashed wait
faults, failed readiness/cleanup, missing slots with known budget failure, extra
files/symlinks and incomplete launches. They do not establish Linux/native results.
The post-run review must cover archive integrity, completeness, missed slots,
inclusive recorder CPU/RSS/read brackets/throttling/memory events and separate
producer resources. Incremental observer overhead remains unknown from one run.
Any required unknown blocks progression. Stop after this smoke for independent
review and a separate six-case authorization decision. No units have started.

Implementation verification and exact candidate/freeze receipt follow below once
sealed; request approval only for that immutable packet. No main merge, QC sync,
credentials import, infrastructure change or native execution is authorized here.

Verification: all 1,128 offline tests passed in 85.018 seconds on Intel macOS /
Python 3.14.6, including the 14 new transport/audit tests and existing localhost
fixtures. New transport/auditor/tests compile with local Python 3.8.2. Fresh
read-only wait-runtime bytes exactly match the earlier frozen comparison envelope;
that observation is not execution of the new recorder path. Installed Linux
readiness tests and native recorder measurements remain unrun. New source-bound
observer declaration: 0f3a9b8494804f792d5778a0388d787cb2bc52a5de7fd4bc1cdb60738ded6bf1.


## Frozen approval packet — October 15

Implementation candidate: `81fc2ba00fc5cae35316b3661dbb2ec6044f666b` (500 selected source files).
Execution freeze: `f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`.
Private preparation verification receipt:
`3f15daf0206e50663d3174ce78218c48132f496cd7bd894e1068ec3ff1774d1e`.
These bind the implementation candidate, not later documentation-only HEADs.
The original three native audit payload hashes still verify unchanged.

Prepared private transport packet `stage-packet.tar.gz`: 119,716 bytes,
SHA-256 `f974a66a733218802f53afc31fa1f31ca9335557fbe20c33ad4c74fc28c6164f`.
It contains the incremental Git bundle (prerequisite frozen cb23c4c), exact freeze,
reviewed select source/review and dated host context. No credential or evidence
archive is included. Source is not yet staged remotely; no new candidate code,
readiness unit or recorder unit has executed on Linux. After approval, stage into
one fresh private directory, verify packet/commit/all source/runtime bindings
before starting units, and reject any existing evidence/claim/unit namespace.
Do not overwrite or execute in an old comparison/evidence directory. The transport
bundle and controls must reconstruct the candidate exactly; stop on any mismatch.

Proposed stage: `/var/lib/qcrl-stream/recorder-absolute-20261015LupusSmoke01`.
After separately approved staging and gate checks, the one controller invocation is:

```sh
/opt/qcrl-stream/venv/bin/python -B -m infra.stream.recorder_absolute_smoke --root /var/lib/qcrl-stream/recorder-absolute-20261015LupusSmoke01 --execute
```

Run it as root from that stage's `source` directory through the authorized existing
Session Manager connection. Expected readiness population: **1,128 tests, 1,127
passing and one existing Python-version skip**, within its separate 240-second
unit. Those are prospective Linux counts, not observed Linux results. Any other
population, failure, drift, effective-limit/binding/readiness fault or retention
failure stops progression and preserves the attempt without replay. Then only
the declared producer/recorder pair: 68 occurrences at 1 Hz over offsets 0..67,
20-second original epoch lead, frame limit 68/capture limit 180 seconds, fixed
75% CPU/512 MiB/32 tasks/240 seconds per unit, 50-ms CPU pre-read policy.

Stop after one smoke. Independently transfer/verify the external origin inventory
anchor, audit completeness, ordered archive/durability, actual wait/read/missed-slot
coverage, inclusive observer/recorder cost and every unknown. Incremental observer
overhead and host credit balance are explicitly unknown. The console's dated
standard-credit observation does not replace the original six-case cohort's raw
host-context gates. No isolated timing run, tuning, replay, cohort, public-service
change, infrastructure provisioning, main merge or QC synchronization is included.
**Await the user's approval of this exact packet before staging/execution.**


## October 15 — Authorized single recorder smoke completed; audit failed; stop

Executed once under freeze f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93
with exact candidate 81fc2ba and fresh source/runtime/public preflight. Linux
readiness: 1,128 tests in 109.029 s, 1,127 passing plus the declared existing skip.
The fixed 68-at-1-Hz recorder smoke completed. Independent byte/origin inventory,
unit binding, ordered archive and completion checks pass; zero missed observer
slots, one complete 60-second CPU window and resource gates pass. Compatibility
fails: sequence 9/44 durable upper bounds 2.000667292/2.000551980 s exceed 2 s;
producer drain retains ConnectionClosedOK. Frozen thresholds/code/evidence stay
unchanged. Inclusive resource cost is documented without claiming incremental
observer overhead, continuous RSS peak or long-run acceptance. All scoped units
are gone; public collector/source/environment context is unchanged. No retries,
replay, tuning, extra runs, resource changes or six-case cohort. Historical native
audit hashes reverified unchanged. See docs/RECORDER_ABSOLUTE_SMOKE_RESULT_20261015.md
and the current HANDOFF for full anchors, unknowns and private evidence location.
Native work stopped after this single smoke; no cohort or further run authorized.


## October 15 — Offline durability/drain diagnosis; successor fixes proposed

Retained native timestamps and code show nearly two seconds of receive/sync
scheduling before the persistence path completes, leaving insufficient margin
under the unchanged 2-s durability bound. Producer drain treats normal close after
all sends like premature normal close, and may suppress faults after a concurrent
stop. Capture-closed presence alone neither binds the case nor proves success.
The retained exception ordering is unknown; original compatibility fail remains.
Fourteen deterministic tests reproduce boundaries, all persistence-stage faults,
closure/timeout/control/stop races and failed/missing capture markers. Full offline
suite: 1,142 passing in 89.878 s on Intel macOS/Python 3.14.6. Original declaration,
native inventory/archive and failed audit hashes reverify unchanged. Proposed
successors cap pending receive waits at sync deadlines and reconcile terminal
close events with completed sends and verified recorder lifecycle evidence. No
runtime fix is wired in, no thresholds changed, and no native replay or cohort
ran. A successor needs a new prospective identity/freeze before any execution.
See docs/RECORDER_FAILURE_ANALYSIS_20261015.md and current docs/HANDOFF.md.


## October 15 — Persistence/closure successor implemented offline

New isolated runtime lane/worker implement deadline-aware persistence with an
explicit one-second prospective reserve within the unchanged two-second bound,
and closure requires all planned sends plus verified recorder completion/archive.
Normal closure alone cannot pass; faults remain across concurrent stop. Atomic
exclusive control publication prevents partial consumer.json adoption and retains
partial writes/collisions. Original runtime/declaration/observer, failed native
run and thresholds are unchanged. New finite smoke/controller/auditor routes only
to the successor and has no cohort path. Fourteen successor tests cover actual
localhost workers/collector/completion, boundary/fault/stop/publication cases and
controller command/readiness/cleanup paths. All 1,156 offline tests passed in
77.706 s on Intel macOS/Python 3.14.6; focused tests also pass after the final
successor/observer declaration-label clarification. Python 3.9 syntax parses;
no installed Linux successor validation. Prospective Linux gate is 1,156 total,
1,155 passing plus the declared one existing version skip. A newly committed
candidate/freeze packet is required for one separately approved 68-at-1-Hz smoke.
No native staging/run, replay, cohort, resource change or public operation occurred.
See docs/RECORDER_PERSISTENCE_SMOKE_PREPARATION.md and current docs/HANDOFF.md.


## October 15 — Successor approval packet frozen offline; execution pending

Candidate 371fa03c3d2622d784128b9359c3ab730f082cf2, 509 selected files;
freeze 3338edbfc19048fa39787d86cc70abebd458318b4a79abd816c531f2fad3ca4f;
preparation receipt 3e30514f0bbda19bbca22826756738f4b19c2a625543c934988b39ee634235b4.
Private 107,692-byte stage packet SHA-256:
7987395433a724ad16adf5f843cd31fb8017547c5e6ebefe8deb77f982adc26f.
Fresh predecessor-only offline reconstruction verified every selected candidate
file from the transport bundle. Runtime binding uses the previous October 15
observed installed envelope; a fresh read-only exact source/runtime/public check
remains mandatory before any units. Proposed stage is recorder-absolute-
20261015LupusPersistence01. One separately approved 68-at-1-Hz smoke only, after
1,156 Linux tests with 1,155 pass/one declared skip, original limits/epoch/grid,
explicit one-second prospective persistence reserve and verified completion-bound
closure. Stop afterward; no replay/cohort/resource/public-service change. No
successor staging or Linux/native execution has occurred. See current HANDOFF.
