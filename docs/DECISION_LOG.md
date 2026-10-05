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
| D-014 | Do not map the current QCRL daily signal to Polymarket daily series 41. | accepted | durable public discovery, market bundle, and source contract | Coinbase/Binance feeds, midnight-UTC/noon-Eastern anchors, and tie semantics are not equivalent; retain the capture for mechanics only and require a new aligned research declaration before reconsideration. |
| D-015 | Materialize the current candidate only at the next UTC daily boundary from completed Coinbase bars. | accepted | QCRL source contract and boundary adapter | Late or malformed bars fail closed; emitted intent names its source contract and cannot bind under an unapproved source policy. |
| D-016 | Permit an authenticated CLOB probe only through a mechanically GET-only transport. | accepted | fixed-route probe contract and credential-redaction tests | No wallet signing, order submission, cancellation, heartbeat, raw account persistence, or inference from missing fields. |
| D-017 | Record October 3 CLOB documentation semantics in a versioned interpretation sidecar. | accepted 2026-10-03 | current official schema/lifecycle review; `CLOB_SCHEMA_REVIEW.md` | Explicit current-documentation declaration permits absent `itode` to mean false for post-review observations; historical evidence and replay gates stay unchanged, and `oas` scope/defaults remain unresolved. |
| D-018 | Audit phase execution metadata offline without relaxing replay constraints. | accepted 2026-10-04 | pinned five-market metadata audit; `BATCH_METADATA_AUDIT.md` | Retain both unknown execution fields and missing phases; four observed tick-grid differences motivate a separate fail-closed mechanics policy, not fill or trading claims. |
| D-019 | Reject unchanged replay requests after any observed execution-metadata change, including finer tick grids. | accepted 2026-10-04 | D-018; `TICK_GRID_REVALIDATION.md` | Separate opt-in two-observation guard requires a newly reviewed request; no repricing, order submission, or relaxation of existing replay gates. |
| D-020 | Declare a separate Binance BTCUSDT/noon-Eastern close-to-close research lane, without transferring Coinbase evidence. | accepted 2026-10-04 | pinned September 22 terms; `ALIGNED_BINANCE_RESEARCH_LANE.md` | Retain length-2 reversal without filters; honor finalized minute-close availability and calendar/DST boundaries. New source and delayed-decision contracts required; no campaign, hypothesis reopening, collector change, or orders activated. |
| D-021 | Derive aligned source intervals only from verified exact, adjacent calendar-noon candles with recorded retrieval times. | accepted 2026-10-04 | D-020; `BINANCE_CALENDAR_SOURCE_ADAPTER.md` | Preserve gaps and split ties, reject unfinished or mismatched candles, and never backdate availability. Source records do not emit signals or establish historical executability. |
| D-022 | Assemble retained Binance evidence with complete source provenance and explicit missing boundaries. | accepted 2026-10-05 | pinned five-artifact assembly; `RETAINED_BINANCE_DATASET.md` | Ten of seventeen boundaries produce seven adjacent comparisons, not signal success rates. Reject conflicting shared candles and duplicate sources; no gap bridging, new acquisition, or evaluation activation. |
| D-023 | Represent post-boundary diagnostic decisions with a separate schema and actual observation times. | accepted 2026-10-05 | aligned lane and synthetic contract tests; `DELAYED_DECISION_SIGNAL.md` | Preserve the original target window; no emission before input completion/observation, across gaps, or after expiry. Legacy binding remains incompatible; no maximum entry-delay policy or orders approved. |
| D-024 | Add opt-in delayed diagnostic binding with explicit terms and independent source freshness. | accepted 2026-10-05 | reproduced decisions and synthetic binding tests; `DELAYED_BINDING_FRESHNESS.md` | Provisional 300-second entry, 30-second intent, 5-second metadata and 2-second book limits; unknown execution fields still block. No live terms approval, acquisition, revalidation shortcut, or orders. |
| D-025 | Restore BTC five-minute observation as the next priority; retain daily as a separate comparison lane. | accepted 2026-10-05 | user scope correction; `FIVE_MINUTE_STREAM_LANE.md` | Bounded public recorder first, then live verification and rolling cohort/service. Preserve raw frames and gaps; no daily-signal transfer, credentials, order actions, or deployment activated by implementation. |

## Decision discipline

Verification update, 2026-10-05 (D-025): isolated `websockets==15.0.1` runtime
and a 25-second public BTC 5m smoke passed; both token books and two PONGs were
retained in a verified chain. Two future markets passed exact terms/interval
discovery. Add a separate bounded six-market EC2 pilot with explicit quota/gap
reporting and encrypted S3 replication, not an indefinitely restarting service.
Deployment remains pending AWS access; no daily service or stack was changed.

- A decision may cite multiple hypotheses, campaigns, or syntheses, but must
  state an operational consequence.
- New contradictory evidence changes a decision through a new dated log entry;
  the prior decision remains visible.
- `supported` describes an evidence gate, not trading authorization.
- Decisions cannot promote post-hoc analysis to prospective evidence.
- A closed decision is reopened only under the rules in
  `HYPOTHESIS_REGISTRY.md`, with a new ID and independent declaration.
