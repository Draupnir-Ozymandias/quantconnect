# QCRL Sync Log

**Updated:** 2026-07-30  
**Sync version:** 2026-07-30 Discovery Handoff  
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

methodology_version
lookahead_status
record_status
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

In progress:

```text
BTCUSD 1d
Candle streak reverse
EMA trend 5/10

2022 flat / martingale
2023 flat / martingale
2024 flat / martingale
2025 flat / martingale
```

The 2025 pair passed the stake-isolation invariants.

The remaining pairs should be validated before the first formal cross-year Stability Engine conclusion.

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

## First coding target

```text
discovery/stability_engine.py
```

Suggested interface:

```python
class StabilityEngine:
    def analyze(self, records, group_by=None):
        pass

    def score_group(self, records):
        pass
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

## Phase B1 — Stability Engine scaffold

Create:

```text
discovery/
    __init__.py
    stability_engine.py
```

Build against a plain list of normalized records.

No direct ObjectStore access.

## Phase B2 — Cohort builder

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

## Phase B3 — Validation report

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

## Phase B4 — Flat stability score

Score directional evidence without recovery sizing.

## Phase B5 — Martingale stability score

Score capital transformation, survival, recovery depth, drawdown, and wager escalation.

## Phase B6 — Comparative interpretation

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

## Workstream A exports

- QCRL 2.2.0 clean canonical reports
- normalized record dictionaries
- deterministic experiment identity
- unique run identity
- dynamic metadata
- deduplicated retrieval
- flat/martingale control records
- ongoing 2022–2025 validation matrix

## Workstream B begins with

```text
discovery/stability_engine.py
```

against the clean BTCUSD 1d yearly matrix.

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

> QCRL 2.2.0 now produces clean, runtime-identified, retrievable experiment evidence; the Discovery workstream should begin by measuring cross-year flat-signal stability and then separately measuring the martingale capital-recovery transformation applied to the same paired outcome sequences.
