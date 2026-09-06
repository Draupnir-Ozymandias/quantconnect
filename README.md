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

Terminal summary metrics are a preview only. A finished LEAN run remains
`completed` with `metrics_source=lean_cli`; it becomes `collected` only after a
successful `/backtests/read` response records `metrics_source=quantconnect_api`
and `collected_at_utc`. Directional analysis refuses evidence without that API
provenance.

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

The completed neighborhood selected length 2 for the next research gate. It
was the strongest well-sampled core value and had positive, sufficiently
sampled support on both sides from lengths 1 and 3. Length 4 deteriorated;
lengths 5 and 6 were too sparse to support selection. This does not establish a
monotonic relationship between streak length and reversal probability.

### Directional signal Stage 2

Stage 2 keeps the selected length-2 signal and flat sizing fixed, then tests
one eligibility gate at a time against an unfiltered yearly control:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json
./synch.sh campaign directional campaigns/btcusd_1d_candle_streak_stage2_gates_2022_2025.json
```

The 12 cases compare `none`, `adx_strength`, and `atr_volatility` across
2022–2025. Generated-signal counts must remain identical within each yearly
trio; executed trades may differ because filtering is the factor under test.
EMA and composite filters, filter-parameter optimization, and recovery sizing
remain outside this campaign.

Stage 2 completed with 12/12 authoritative API results and no pair issues. The
versioned `qcrl.single_gate_interpretation.v1` comparison selected ATR and
rejected ADX at the tested defaults. Relative to the unfiltered control, ATR
added 70 units of aggregate profit, improved weighted win rate by 0.69
percentage points, retained 95.79% of trades, improved profit in three of four
years, and did not increase worst drawdown. ADX lost 280 units relative to the
control and retained only 45.43% of trades.

The follow-up attribution campaign is:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_atr_gate_attribution_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_atr_gate_attribution_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_atr_gate_attribution_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_atr_gate_attribution_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_atr_gate_attribution_2022_2025.json
./synch.sh campaign directional campaigns/btcusd_1d_atr_gate_attribution_2022_2025.json
```

Its 20 cases separate the unfiltered control, ATR warmup only, lower bound
only, upper bound only, and the default 1%–10% band across all four years. The
completed attribution verdict found all three bound profiles exactly identical
to the warmup-only diagnostic. ATR skipped 29 signals while not ready and zero
signals because of its bounds. The apparent Stage 2 improvement is therefore a
warmup exclusion effect, not evidence for the 1%–10% volatility gate; threshold
tuning is blocked.

The next four-case campaign observes the prior-state ATR percentage only when
the length-2 signal fires. Its 0%–100% band is deliberately nonrestrictive:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_atr_signal_telemetry_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_atr_signal_telemetry_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_atr_signal_telemetry_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_atr_signal_telemetry_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_atr_signal_telemetry_2022_2025.json
```

The telemetry campaign completed 4/4 with 660 usable signal observations. ATR
percentages ranged from 1.90% to 8.50%, while annual medians ranged from 3.21%
to 5.02%. This confirms that the old 1%–10% band was outside the observed range
and that absolute ATR thresholds have materially different selectivity between
years.

The next exploratory campaign tests two lower bounds and two upper bounds
independently. Every active threshold is compared with the same-year
warmup-only diagnostic, preventing the warmup effect from entering its verdict:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_atr_active_bounds_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_atr_active_bounds_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_atr_active_bounds_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_atr_active_bounds_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_atr_active_bounds_2022_2025.json
./synch.sh campaign directional campaigns/btcusd_1d_atr_active_bounds_2022_2025.json
```

The 24 cases cover unfiltered control, warmup-only, lower bounds of 2.5% and
3.0%, and upper bounds of 5.0% and 6.0% across 2022–2025. Lower and upper bounds
remain isolated; combined bands and broad optimization are still gated. Since
the thresholds were selected from telemetry over these same years, this is an
exploratory screen rather than out-of-sample confirmation.

The completed screen rejected every active bound relative to warmup-only:

```text
lower 2.5%: profit -140 | weighted win rate -0.78 pp | 54 rejected signals
lower 3.0%: profit -160 | weighted win rate -0.40 pp | 140 rejected signals
upper 5.0%: profit -110 | weighted win rate -0.07 pp | 121 rejected signals
upper 6.0%: profit  -40 | weighted win rate -0.04 pp | 42 rejected signals
```

No absolute ATR bound advances. Combined ATR bands and ATR threshold
optimization are closed unless new independent evidence justifies reopening
the hypothesis.

### Candle-streak directional-side attribution

The next campaign decomposes the surviving unfiltered length-2 reversal signal
without changing its trades:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_candle_streak_side_attribution_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_side_attribution_2022_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_side_attribution_2022_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_candle_streak_side_attribution_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_candle_streak_side_attribution_2022_2025.json
./synch.sh campaign directional campaigns/btcusd_1d_candle_streak_side_attribution_2022_2025.json
```

Each of the four annual runs exports trades, wins, losses, win rate, flat net
profit, side-specific drawdown, and side-specific loss streak for both UP and
DOWN forecasts. Here, UP means predicting a bullish reversal after a red
streak; DOWN means predicting a bearish reversal after a green streak. The
versioned verdict distinguishes two-sided support from side dominance or
unstable evidence. Any same-period side restriction requires out-of-sample
validation. Side drawdown is measured on each side's independent flat-profit
curve and is not a decomposition of portfolio drawdown.

The 2022–2025 result was `down_dominant`: DOWN produced +430 at a 56.38%
weighted win rate and was profitable in three of four years; UP produced +60 at
50.85% and was profitable only in 2024. Because 2024 reversed the relationship,
the result is not treated as universal.

The follow-up tests the predeclared DOWN hypothesis in the structurally earlier
2018–2021 Bitcoin market:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_candle_streak_side_stress_2018_2021.json
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_side_stress_2018_2021.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_side_stress_2018_2021.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_candle_streak_side_stress_2018_2021.json
./synch.sh campaign validate campaigns/btcusd_1d_candle_streak_side_stress_2018_2021.json
./synch.sh campaign directional campaigns/btcusd_1d_candle_streak_side_stress_2018_2021.json
```

This is explicitly a historical-regime stress test, not conventional forward
out-of-sample validation. QuantConnect documents Coinbase crypto coverage from
January 2015, but the one-case integration run remains the authoritative check
for project access and usable bars.

The two completed eras can be combined without launching another backtest:

```bash
./synch.sh campaign synthesize syntheses/btcusd_1d_candle_streak_cross_regime_sides.json
```

The versioned cross-regime analyzer first verifies identical signal parameters,
non-overlapping periods, matching evidence revisions, and complete UP/DOWN
attribution. The 2018–2021 `up_dominant` result and 2022–2025 `down_dominant`
result constitute a leadership flip. Pooled descriptive accounting is +600 UP
and +550 DOWN, with +1,150 combined over 1,347 trades and seven profitable
annual samples out of eight. The decision is `retain_both_directions`: neither
side may be statically removed, and the leadership flip is evidence for a
future prior-state regime hypothesis—not itself a tradable classifier.

Synthesis artifacts are written under
`.qcrl/syntheses/btcusd-1d-candle-streak-cross-regime-sides-v1/` and remain
local, reproducible derivatives of the authoritative campaign evidence.

### Prior-state regime bridge

The first explanatory hypothesis uses the sign of BTC's return over the 20
completed daily bars preceding each signal. The regime model is observational:
it records context but cannot approve, reject, or resize a trade. Positive
prior return paired with an UP reversal and nonpositive prior return paired
with a DOWN reversal are predeclared as trend-aligned cells; the other two
cells are the counter-trend comparison.

```bash
./synch.sh campaign plan campaigns/btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json --execute --limit 1
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json
./synch.sh campaign directional campaigns/btcusd_1d_candle_streak_roc_regime_attribution_2018_2025.json
```

The eight annual cases cover 2018–2025 with the same unfiltered, flat-sized,
two-sided signal. The versioned verdict requires at least 85% regime-ready
trades in every year, 50 pooled trades in every active side/regime cell, a
two-percentage-point aligned win-rate edge, and positive alignment in at least
six of eight years. These thresholds and the 20-day/zero-return boundary are
declared before collection. A supported result would justify only a genuinely
forward gate-validation design; it would not authorize applying the gate to
the same discovery period.

The trend-alignment hypothesis was rejected: its pooled edge was +3.81
percentage points, but only five of eight years supported it against a required
six. A different pattern observed after that verdict—therefore explicitly
post-hoc—was that both forecast sides performed better in nonpositive 20-day
return states. The untouched January–August 2026 window tests that new
hypothesis without changing the observer or signal:

```bash
./synch.sh campaign plan campaigns/btcusd_1d_candle_streak_roc_regime_forward_2026.json
./synch.sh campaign run campaigns/btcusd_1d_candle_streak_roc_regime_forward_2026.json --execute
./synch.sh campaign collect campaigns/btcusd_1d_candle_streak_roc_regime_forward_2026.json
./synch.sh campaign validate campaigns/btcusd_1d_candle_streak_roc_regime_forward_2026.json
./synch.sh campaign directional campaigns/btcusd_1d_candle_streak_roc_regime_forward_2026.json
```

The forward verdict requires 85% readiness, at least 30 trades in each pooled
regime, at least 10 trades in every active side/regime cell, a minimum
two-percentage-point nonpositive-state win-rate advantage, greater
nonpositive-state profit, and a positive advantage independently for both UP
and DOWN. One supported partial-year result is corroboration, not completion;
the frozen hypothesis would still require additional forward evidence.

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
