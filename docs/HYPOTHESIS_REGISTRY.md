# QCRL Hypothesis Registry

This registry prevents rejected ideas from returning as undocumented parameter
tuning. A hypothesis is judged against its declared gate, not against the best
result found after inspection.

| ID | Hypothesis | Evidence | Verdict | State |
|---|---|---|---|---|
| H-001 | EMA trend is a robust default directional generator. | Stage 1: -410, profitable 0/4 years. | failed | closed |
| H-002 | MACD trend is a robust default directional generator. | Stage 1: -250, profitable 2/4 years. | failed | closed |
| H-003 | RSI mean reversion is sufficiently stable to advance. | Stage 1: +70, profitable 3/4 but fragile. | failed | closed |
| H-004 | Reversal quality rises monotonically with longer candle streaks. | Length 4 deteriorated; lengths 5/6 sparse. | failed | closed |
| H-005 | ADX 14/25 improves the length-2 signal. | -280 delta; improved 0/4 years. | failed | closed |
| H-006 | ATR 14 with 1–10% bounds improves the signal. | Apparent gain fully attributable to warmup. | no active effect | closed |
| H-007 | A telemetry-selected ATR bound improves warmup-only control. | Bounds 2.5%, 3%, 5%, and 6% all underperformed. | failed 0/4 | closed |
| H-008 | Restricting the signal to DOWN generalizes across eras. | DOWN led 2022–2025; UP led 2018–2021. | failed | closed |
| H-009 | Restricting the signal to UP generalizes across eras. | Both sides profitable in only 5/8 years; leadership flips. | failed | closed |
| H-010 | Prior 20-day ROC trend alignment is stable across years. | Supported 5/8 versus required 6/8. | failed | closed |
| H-011 | Nonpositive prior 20-day ROC improves January–August 2026 results. | Favored and comparison states both 50% after readiness. | failed | closed |
| H-012 | The untouched length-2 signal persists across 2018–2025 quarters. | All predeclared gates passed; 25/32 profitable. | passed | supported |
| H-013 | Historical persistence confirms in January–August 2026. | 46.92%, -80, -7.29 percentage-point change. | failed | closed |
| H-014 | The untouched candidate provides positive prospective 2026Q4 evidence. | No evidence may be read before the window completes. | unresolved | **locked** |

## Reopening rule

A closed hypothesis may not be revived by changing a threshold, choosing a
favorable subperiod, or renaming the same idea. Reopening requires all of:

1. a materially new causal rationale or independent data source;
2. a new versioned hypothesis ID and predeclared acceptance gate;
3. a clean separation from data used to generate the new rationale;
4. explicit linkage to the closed predecessor; and
5. a decision-log entry authorizing the new test.

Sparse evidence is not proof of failure, but it is also not permission to
select. Lengths 5 and 6 remain non-candidates unless a new sampling design is
declared without mining the existing tail results.

