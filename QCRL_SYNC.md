# QCRL Sync Log

**Updated:** 2026-08-08
**Sync version:** 2026-08-08 Campaign Throttling Foundation
**QCRL baseline:** 2.2.0  
**Status:** Active research

---

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
score:  qcrl.directional_cohort_score.v1
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

Canonical storage contracts are extended to preserve every active directional
and gate parameter:

```text
qcrl.research_report.v4
qcrl.experiment_record.v3
```

The existing QCRL 2.2.0 baseline campaign remains reproducible because its
manifest pins `lab_version=QCRL-2.2.0` and the legacy model path is unchanged.

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
Next: flat/no-filter candle-streak parameter-neighborhood validation
```

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

> QCRL 2.3.0 now grades directional generators with a versioned cross-year cohort engine; candle-streak reversal is held for flat/no-filter parameter-neighborhood validation, while the tested RSI, MACD, and EMA defaults are rejected and all eligibility gates remain withheld.
