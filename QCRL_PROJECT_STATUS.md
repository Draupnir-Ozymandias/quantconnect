# QCRL Project Status

**As of:** 2026-09-07
**Repository:** `Draupnir-Ozymandias/quantconnect` / `polymarket-martingale`  
**QuantConnect project:** 33239307  
**Current research decision:** Hold feature optimization; preserve the locked
2026Q4 prospective baseline while building execution infrastructure separately.

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
| Execution-truth schemas | market v2; book, bundles, discovery, signal intent, and binding v1 |
| Test suite | 135 deterministic tests passing |

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
  read-only upload plan and preflight enforcement of the 64,000-character limit
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
- Local Git, GitHub, and QuantConnect were synchronized at the time of this
  report.

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
   can now be acquired and normalized. One live bundle is stored as ignored
   local evidence; checked-in fixtures remain documentation-derived rather than
   durable live evidence. No trade, fill, or settlement data is ingested.
2. No bid/ask spread, entry price, market depth, partial fill, no-fill, dynamic
   fee, or latency model exists.
3. The signal/market binding contract now separates availability, observation,
   decision, target, and cutoff times, but the research callback still evaluates
   a completed bar while notionally assigning the forecast to that bar's opening
   interval. A live signal adapter must emit prior-state intent at the boundary.
4. QCRL uses its own synthetic bankroll and submits no LEAN portfolio orders;
   standard LEAN portfolio statistics are not strategy objectives here.
5. Polymarket is not implemented as a LEAN brokerage or execution adapter.
6. Manual defaults still select EMA 5/10 and QCRL 2.3.0, while the current
   candidate is unfiltered and temporal manifests use 2.4.0.
7. The estimated 8.43% friction capacity assumes constant cost per wager and
   cannot be translated directly into expected Polymarket profitability.
8. The 2026Q4 prospective sample is future evidence and must not be run
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
immutable local raw storage, offline normalization, and signal binding are
implemented; remaining work is:

1. Promote selected irreplaceable live bundles into an explicit
   Git-synchronized fixture workflow.
2. Determine whether an exact daily BTC Up/Down market series exists; do not
   bind the daily research signal to the validated five-minute series.
3. Build a boundary-time signal adapter from prior completed bars.
4. Build a replay-only execution model for maker/taker prices, fees, partial
   fills, no fills, and settlement.
5. Add shadow decisions and reconciliation before any authenticated order path.

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
- `docs/OPERATOR_WORKFLOW.md` — exact Git, GitHub, QuantConnect, and campaign flow
- `campaigns/` — immutable experiment declarations
- `syntheses/` — versioned cross-campaign analysis declarations
- `.qcrl/campaigns/` — ignored local campaign state and derived evidence
- `.qcrl/syntheses/` — ignored reproducible synthesis outputs
