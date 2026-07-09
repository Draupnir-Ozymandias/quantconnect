# QCRL_ARCHITECTURE.md

# QuantConnect Research Laboratory (QCRL)

**Version:** 2.1

**Author:** Eric Bucher

**Project Status:** Active Research

---

# Vision

QCRL is **not** an automated trading bot.

It is a quantitative research laboratory whose purpose is to discover statistically robust trading behaviors through systematic experimentation.

The objective is to identify **stable parameter regions**, **repeatable market behaviors**, and **risk characteristics**, rather than simply maximize historical profit.

Optimization is viewed as a source of experimental evidence—not as an endpoint.

---

# Core Philosophy

Traditional optimization asks:

> Which parameter combination produced the most profit?

QCRL asks:

> Why did it perform well?
>
> Is the result repeatable?
>
> Is the surrounding parameter space also successful?
>
> Would we trust this strategy on unseen market data?

Robustness is valued over peak performance.

A broad plateau is preferable to a sharp spike.

---

# Guiding Principles

1. Never optimize for profit alone.
2. Favor robustness over maximum return.
3. Penalize catastrophic tail risk.
4. Every optimization run becomes permanent research data.
5. Every experiment should be reproducible.
6. Discovery is more important than confirmation.
7. Every metric should help explain *why* a strategy behaves the way it does.

---

# Current Architecture

```
Optimization Engine
        │
        ▼
StatsTracker
        │
        ▼
ResearchReport
        │
        ▼
Object Store
        │
        ▼
Research Notebook
        │
        ▼
ResearchTools
```

---

# Optimization Engine

Responsible for:

* Loading market data
* Executing entry models
* Executing filter models
* Executing staking models
* Recording statistics
* Producing Research Reports

---

# Entry Models

Current:

* Candle Streak (Follow)
* Candle Streak (Reverse)

Future:

* Momentum
* Mean Reversion
* Volatility Expansion
* Breakout
* Session Bias
* Composite Models

---

# Filter Models

Current:

* EMA Trend

Planned:

* SMA
* VWAP
* ATR
* ADX
* RSI
* MACD
* Volume Filters
* Volatility Filters
* Regime Detection
* Composite Filters

---

# Stake Models

Current

* Flat
* Martingale

Future

* Kelly
* Fractional Kelly
* Fixed Fraction
* ATR Position Sizing
* Volatility Scaling
* Dynamic Recovery

---

# StatsTracker

Purpose

Capture everything that occurs during execution.

Current metrics include

* Trades
* Wins
* Losses
* Win Rate
* Drawdown
* Recovery Depth
* Max Wager
* Execution Rate
* Filter Rate
* Signal Statistics
* Regime Statistics

Future

* Equity Curve Statistics
* Rolling Drawdowns
* Recovery Time
* Distribution Analysis
* Trade Duration
* Expectancy
* Profit Factor
* Sharpe
* Sortino

---

# Research Report

Each optimization produces a permanent JSON report.

Reports contain

## Configuration

* Experiment metadata
* Parameters
* Models
* Timeframe
* Market
* Laboratory Version

## Performance

* Profit
* Trades
* Win Rate

## Risk

* Drawdown
* Recovery Depth
* Tail Risk
* Ruin

## Analytics

* Signal statistics
* Execution statistics
* Wager statistics

## Scores

* Risk Adjusted Score
* Tail Risk Score
* Survival Score

---

# Object Store

The Object Store serves as the permanent experimental database.

Every optimization is preserved.

Optimization results are never discarded.

Historical experiments become research evidence.

---

# ResearchTools

ResearchTools is the analysis engine of QCRL.

It operates on completed experiments rather than live trades.

Current functionality

* Load Reports
* Flatten Reports
* Ranking
* Filtering
* Candidate Summary
* Parameter Neighborhood
* Plateau Analysis
* Plateau Discovery
* Heatmaps
* Correlation Dashboard
* Experiment Dashboard

Planned

* Audit Database
* Compare()
* Cluster Analysis
* Consensus Parameters
* Strategy Archetypes
* Discovery Layer

---

# Research Cohorts

A fundamental design principle.

Analysis should never mix unrelated experiments.

Examples

Correct

* BTC
* 2025
* 1 Hour
* Martingale
* Candle Streak

Incorrect

* Mixing daily with 5-minute data
* Mixing 2024 with 2026
* Mixing different entry models

All advanced analysis should operate on explicitly selected cohorts.

---

# Plateau Philosophy

The best parameter is rarely the highest point.

Instead we seek

* Stable neighborhoods
* Low variance
* Consistent profitability
* Robust recovery
* Low tail risk

A strategy surrounded by other successful strategies is preferred over an isolated optimum.

---

# Discovery Layer

The long-term objective.

Rather than asking

"Which EMA is best?"

QCRL should discover

* Parameter families
* Stable regions
* Behavioral clusters
* Market archetypes

Possible classifications include

* Sniper
* Swing
* Scalper
* Firehose
* Robust
* Fragile
* Lottery

The Discovery Layer transforms optimization into knowledge.

---

# Experiment Metadata

Every experiment should record

* Laboratory Version
* Generated Timestamp
* Experiment ID
* Experiment Group
* Experiment Name
* Experiment Notes
* Experiment Tags
* Experiment Year
* Asset
* Timeframe
* Strategy Family

This enables filtering, auditing, comparison, and reproducibility.

---

# Development Roadmap

## Completed

* Optimization Engine
* Entry Models
* Filter Models
* Stake Models
* StatsTracker
* Report Models
* Results Database
* Research Report
* Research Dashboard
* Heatmaps
* Plateau Analysis
* Correlation Dashboard

---

## Current

* Research Cohorts
* Audit Database
* Experiment Registry

---

## Next

* Compare()
* Cluster Analysis
* Consensus Parameters
* Discovery Layer

---

## Future

* Cross-Asset Analysis
* Cross-Timeframe Analysis
* Monte Carlo Validation
* Walk-Forward Validation
* Multi-Coin Consensus
* Strategy Evolution
* Adaptive Parameter Selection
* Machine Learning Ranking

---

# Long-Term Goal

QCRL is intended to evolve from an optimization framework into a quantitative research platform.

The laboratory should eventually answer questions such as:

* Which parameter regions remain stable across multiple years?
* Which strategies survive changing market regimes?
* Which models generalize instead of overfitting?
* Which behaviors persist across assets and timeframes?
* What characteristics define a truly robust trading strategy?

The final objective is not merely to optimize strategies, but to discover repeatable market structure through disciplined experimentation.

