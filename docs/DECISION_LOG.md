# QCRL Decision Log

This is the durable record of decisions that constrain current development.
Research measurements belong in evidence; this log records what those
measurements authorize.

| ID | Decision | State | Evidence | Consequence |
|---|---|---|---|---|
| D-001 | Local Git is source of truth; QuantConnect is execution/data infrastructure. | accepted | guarded sync integration | Test, commit, and inspect `push-plan` before cloud push; avoid dual editing. |
| D-002 | QuantConnect API metrics are authoritative for campaign collection. | accepted | campaign runner integration | CLI tables are preview only; validate collected custom metrics. |
| D-003 | Analyze signal quality separately from capital recovery. | accepted | baseline paired cohorts | Flat and martingale results cannot be pooled. |
| D-004 | Do not optimize or deploy martingale sizing. | closed | 2022–2025 baseline stability | Extreme risk amplification and recovery dependence. |
| D-005 | Retain unfiltered, flat, length-2 candle-streak reversal as the research candidate. | hold | Stage 1 and neighborhood | Candidate may be audited, not treated as deployment-ready. |
| D-006 | Approve no active eligibility filter. | accepted | ADX and ATR campaigns | EMA is legacy default; ADX and tested ATR bounds are rejected. |
| D-007 | Retain both UP and DOWN forecasts. | accepted | cross-regime side synthesis | Era-dependent leadership invalidates a universal side restriction. |
| D-008 | Approve no prior-return ROC regime gate. | accepted | attribution and forward campaigns | Both declared ROC hypotheses failed. |
| D-009 | Historical temporal persistence is supported. | supported | 32-quarter audit | Permits forward comparison, not live authorization. |
| D-010 | Forward evidence degraded the candidate; freeze feature optimization. | accepted | historical-forward bridge | Build execution truth instead of searching for a rescue filter. |
| D-011 | Treat 2026 segment analysis as post-hoc diagnostics only. | accepted | forward diagnostic synthesis | It cannot reverse D-010 or select a regime. |
| D-012 | Preserve the 2026Q4 prospective declaration unchanged and unexecuted until complete. | locked | prospective manifest locked 2026-09-06 | No partial run, parameter edit, or retrospective relabeling. |
| D-013 | Build read-only Polymarket execution truth as the next engineering lane. | accepted | known-gap audit | Define timing/market contracts, fixtures, replay, and reconciliation before credentials or orders. |

## Decision discipline

- A decision may cite multiple hypotheses, campaigns, or syntheses, but must
  state an operational consequence.
- New contradictory evidence changes a decision through a new dated log entry;
  the prior decision remains visible.
- `supported` describes an evidence gate, not trading authorization.
- Decisions cannot promote post-hoc analysis to prospective evidence.
- A closed decision is reopened only under the rules in
  `HYPOTHESIS_REGISTRY.md`, with a new ID and independent declaration.
