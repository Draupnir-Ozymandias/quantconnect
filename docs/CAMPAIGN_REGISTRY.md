# QCRL Campaign Registry

**As of:** 2026-09-06  
**Scope:** version-controlled declarations; conclusions are summarized from the
canonical status and derived `.qcrl/` evidence.

Thirteen completed campaign families contain 160 collected cases. The remaining
one-case prospective campaign is locked and pending by design.

| Campaign | Version | Cases | Evidence role | Status | Principal conclusion |
|---|---:|---:|---|---|---|
| `btcusd-1d-baseline-2022-2025-v1` | 2.2.0 | 8 | historical control | complete | Flat and martingale baseline fragile; martingale closed. |
| `btcusd-1d-directional-stage1-2022-2025-v1` | 2.3.0 | 16 | historical screen | complete | Candle streak alone advanced; EMA, MACD, and RSI rejected. |
| `btcusd-1d-candle-streak-neighborhood-2022-2025-v1` | 2.3.0 | 24 | historical neighborhood | complete | Length 2 selected; 1/3 supportive, 4 deteriorated, 5/6 sparse. |
| `btcusd-1d-candle-streak-stage2-gates-2022-2025-v1` | 2.3.0 | 12 | historical gate screen | complete | ADX rejected; ATR required attribution before interpretation. |
| `btcusd-1d-atr-gate-attribution-2022-2025-v1` | 2.3.0 | 20 | historical attribution | complete | Apparent ATR benefit was warmup exclusion, not an active bound. |
| `btcusd-1d-atr-signal-telemetry-2022-2025-v1` | 2.3.0 | 4 | historical telemetry | complete | Recorded 660 prior-state ATR observations; supplied test bounds. |
| `btcusd-1d-atr-active-bounds-2022-2025-v1` | 2.3.0 | 24 | historical isolated screen | complete | All four active ATR bounds underperformed warmup-only control. |
| `btcusd-1d-candle-streak-side-attribution-2022-2025-v1` | 2.3.0 | 4 | historical attribution | complete | DOWN led in 2022–2025; not sufficient for restriction. |
| `btcusd-1d-candle-streak-side-stress-2018-2021-v1` | 2.3.0 | 4 | historical regime stress | complete | UP led in 2018–2021; static side restriction rejected. |
| `btcusd-1d-candle-streak-roc-regime-attribution-2018-2025-v1` | 2.3.0 | 8 | historical observer | complete | Trend alignment supported only 5/8 years; rejected. |
| `btcusd-1d-candle-streak-roc-regime-forward-2026-v1` | 2.3.0 | 1 | locked forward hypothesis | complete | Nonpositive ROC advantage failed; no ROC gate approved. |
| `btcusd-1d-candle-streak-temporal-audit-2018-2025-v1` | 2.4.0 | 32 | predeclared historical audit | complete | Historical persistence gate passed 25/32 quarters. |
| `btcusd-1d-candle-streak-forward-diagnostic-2026-v1` | 2.4.0 | 3 | post-hoc forward diagnostic | complete | Localized degradation; cannot promote a feature or reverse verdict. |
| `btcusd-1d-candle-streak-prospective-2026q4-v1` | 2.4.0 | 1 | prospective forward baseline | **locked / pending** | Do not run partially or modify; evaluate only after 2026-12-31. |

## Synthesis registry

| Synthesis | Inputs | Result |
|---|---|---|
| `btcusd-1d-candle-streak-cross-regime-sides-v1` | 2018–2021 and 2022–2025 side campaigns | Side leadership flips; retain both directions. |
| `btcusd-1d-candle-streak-historical-forward-bridge-v1` | temporal audit and January–August 2026 forward evidence | `forward_degraded`; hold feature optimization. |
| `btcusd-1d-candle-streak-forward-diagnostic-2026-v1` | three post-hoc 2026 segments | Q1 carried most loss; later recovery is diagnostic only. |

## Evidence locations and lifecycle

Declarations live in `campaigns/` and `syntheses/`. Resumable state, API metrics,
reports, hashes, and logs live under ignored `.qcrl/campaigns/{campaign_id}/`
and `.qcrl/syntheses/`. A completed conclusion requires:

1. every expected case completed and collected;
2. the authoritative source/provenance checks passed;
3. pair or cohort invariants passed where declared;
4. the versioned analyzer produced its evidence and report artifacts; and
5. the status, decision, and hypothesis documents were reconciled.

The count in this registry is the expanded case count, not merely the number of
`variants` entries in a manifest; matrix dimensions can multiply each variant.

