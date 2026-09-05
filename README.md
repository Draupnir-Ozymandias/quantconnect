# QuantConnect Research Laboratory

QCRL is a research platform for testing whether signal, filter, and capital-management behavior remains stable across experiments. It is not a live trading bot.

The validated methodological baseline is **QCRL 2.2.0**. The active directional
research engine is **QCRL 2.3.0**. See [QCRL_SYNC.md](QCRL_SYNC.md) for the
current engine/discovery boundary and research roadmap.

## Source-of-truth workflow

The local Git checkout is the source of truth. QuantConnect Cloud is the remote compilation, data, backtesting, optimization, and ObjectStore environment.

```text
local branch -> tests -> commit -> QuantConnect push/backtest -> canonical report
```

Do not edit the same files locally and in the QuantConnect web IDE at the same time. Commit local work before synchronizing in either direction.

## Synchronization

Use the guarded synchronization script from the project directory:

```bash
./synch.sh status
./synch.sh test
./synch.sh pull
./synch.sh push
./synch.sh backtest
```

- `status` is the default and makes no changes.
- `pull` requires a clean tree and creates a recovery branch before contacting QuantConnect.
- `push` requires a clean tree and interactive confirmation because local files replace their cloud counterparts.
- `backtest` does not implicitly push local changes.
- `backtest` injects the current Git commit, branch, and optional
  `QCRL_CAMPAIGN_ID` into the experiment record.

Run `./synch.sh help` for the complete command summary.

## Local tests

The platform-independent model and persistence tests do not require QuantConnect or Docker:

```bash
./synch.sh test
```

Cloud compilation and the clean BTCUSD control matrix remain the integration-validation layer.

QCRL tracks performance in its own simulated bankroll and intentionally submits
no portfolio orders. LEAN's standard portfolio statistics are therefore not
valid optimization objectives for this project. The next development layer is
a QCRL-aware campaign runner that evaluates canonical report metrics across an
arbitrary parameter search space.

## QCRL campaigns

Campaign manifests are version-controlled JSON files under `campaigns/`. The
first manifest defines the eight-run BTCUSD 2022–2025 flat/martingale control
matrix.

```bash
./synch.sh campaign plan campaigns/btcusd_1d_baseline_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_baseline_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_baseline_2022_2025.json --execute
./synch.sh campaign status campaigns/btcusd_1d_baseline_2022_2025.json
```

`run` is a dry run unless `--execute` is present. Executed campaigns require a
clean Git tree, run sequentially, and resume without repeating completed cases.
By default, submission start times are separated by at least 30 seconds. A
recognized QuantConnect rate limit is retried automatically after 30, 60, 120,
and 240 seconds; other compilation or runtime failures stop immediately. Use
`--limit 1` for an integration check and `--retry-failed` only after retries are
exhausted or an ordinary failure is corrected. Local state and logs live under
the ignored `.qcrl/` directory.

Campaigns can override the defaults without changing runner code:

```json
"submission_policy": {
  "min_interval_seconds": 30,
  "max_rate_retries": 4,
  "initial_backoff_seconds": 30,
  "max_backoff_seconds": 300
}
```

For a one-time override, use `--min-interval-seconds` or
`--max-rate-retries`. Rate-limit events, retry counts, and the policy used are
recorded in campaign state and per-attempt output is appended to the case log.

The algorithm publishes QCRL-native metrics as custom backtest summary
statistics. To retrieve them through the QuantConnect API, copy `.env.example`
to `.env`, enter the API credentials issued by QuantConnect, load them into the
shell, and collect the results:

```bash
set -a
source .env
set +a
./synch.sh campaign collect campaigns/btcusd_1d_baseline_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_baseline_2022_2025.json
```

Validation checks run completeness, native-objective availability, and the
flat/martingale signal-sequence invariants before producing a ranking.

Rankings are declared as separate cohorts in the campaign manifest. The clean
control campaign uses:

- `flat_profit_drawdown`: `net_profit / (1 + max_drawdown)`, with a ruin
  penalty. This measures signal economics without recovery-depth penalties.
- `martingale_recovery_risk`: the QCRL risk-adjusted score, which includes
  drawdown and recovery depth and applies the engine's ruin penalty.

Changing ranking, display, or submission configuration is accepted as an
analysis-only manifest revision when the deterministic case set is unchanged.
Changing any expanded parameter set requires a new `campaign_id`; existing run
state cannot silently migrate to different experiments.

### Directional signal Stage 1

The first QCRL 2.3.0 signal campaign is a factor-isolated screen:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_directional_stage1_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_directional_stage1_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_directional_stage1_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_directional_stage1_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_directional_stage1_2022_2025.json
```

It contains 16 cases: four yearly cohorts for each of `candle_streak`,
`ema_trend`, `macd_trend`, and `rsi_mean_reversion`. Every case uses flat
sizing and `filter_model=none`, so this stage measures the directional
generator without recovery sizing or eligibility-filter assistance.

The new ADX-strength and ATR-volatility filters are available in the engine,
but they are reserved for Stage 2. Only Stage 1 generators with credible
cross-year evidence should receive one gate at a time. Composite filters and
recovery sizing remain out of scope.

After collection and validation, run the versioned cross-year analyzer:

```bash
./synch.sh campaign directional campaigns/btcusd_1d_directional_stage1_2022_2025.json
```

It writes two ignored, reproducible artifacts:

```text
.qcrl/campaigns/{campaign_id}/directional_cohort.json
.qcrl/campaigns/{campaign_id}/directional_cohort_report.json
```

The `qcrl.directional_cohort_report.v1` result groups runs by signal generator,
measures coverage, profit consistency, win-rate consistency, trade-frequency
variation, drawdown, and loss streaks, then emits `advance`, `hold`, or `reject`.
The completed Stage 1 campaign holds candle streak for parameter-neighborhood
validation and rejects the tested RSI, MACD, and EMA defaults. A hold does not
authorize filter testing; it requires the prescribed neighborhood campaign.

### Candle-streak neighborhood

The next campaign tests whether the length-2 reversal result belongs to a
stable parameter region:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json
./synch.sh campaign directional campaigns/btcusd_1d_candle_streak_neighborhood_2022_2025.json
```

This is a 24-case campaign: reversal lengths 1–6 across 2022–2025, with flat
sizing and no filter. Lengths 1–3 are the core neighborhood; lengths 4–6 are
an exploratory tail. The score-v2 analyzer requires at least 100 aggregate
trades and at least 20 trades in every yearly sample before it can advance or
reject a cohort. Sparse cohorts are held for more evidence regardless of their
headline win rate.

Signals generated by continuing long streaks use overlapping windows, so they
are not fully independent observations. The report records this limitation.

When `pair_comparison` is present, validation also writes a structured artifact
to `.qcrl/campaigns/{campaign_id}/paired_comparison.json`. Each pair contains:

```text
signal invariants and supporting case IDs
flat and martingale outcomes
profit and drawdown deltas
drawdown amplification
maximum-wager multiple of the base wager
maximum recovery depth
descriptive capital-transform and risk-amplification labels
```

The labels are descriptive rather than recommendations. In particular,
`recovery-dependent-profit` means martingale produced a profit while the paired
flat signal was neutral or negative. This artifact is the input boundary for
the Stability Engine; it does not require another backtest or ObjectStore read.

## Stability Engine

Run stability analysis after campaign validation:

```bash
./synch.sh campaign stability campaigns/btcusd_1d_baseline_2022_2025.json
```

The pure-Python engine in `discovery/stability_engine.py` reads only the paired
artifact and writes:

```text
.qcrl/campaigns/{campaign_id}/stability_report.json
```

The versioned `qcrl.stability_report.v1` contract reports coverage, descriptive
statistics, cross-sample consistency, risk penalties, warnings, and all
supporting run and case IDs. Flat-signal and martingale-capital evidence are
scored independently.

Flat stability combines profitable-year consistency, non-negative years,
win-rate consistency, years at or above 50%, and profit balance. Its risk
penalty uses worst drawdown measured in base wagers and worst loss streak.
Martingale stability combines survival, profit consistency, and consistency of
drawdown amplification, wager escalation, and recovery depth. Its risk penalty
uses worst drawdown amplification, worst wager multiple, recovery depth, and
the share of recovery-dependent years.

The final score is:

```text
stability_score × coverage_ratio × (1 - risk_penalty)
```

Thresholds and score versions are embedded in every report. These scores rank
research fragility; they are not estimates of future returns or universal
confidence claims.

### Comparative interpretation gate

The same stability report includes a versioned
`qcrl.comparative_interpretation.v1` decision layer. It keeps signal stability
separate from capital-recovery stability, classifies recovery dependence and
risk amplification, grades evidence confidence, and emits one research gate:

```text
advance  strong enough for parameter-neighborhood validation
hold     incomplete or mixed evidence; expand validation first
reject   current signal+sizing pair fails the research gate
```

This is a research-progression decision, not live-trading authorization. For
the completed 2022–2025 baseline the decision is `reject`: both components are
fragile, recovery dependence is high, and risk amplification is extreme. The
prescribed next action is to redesign the directional signal and reject the
current recovery-sizing policy rather than optimize its parameters.
