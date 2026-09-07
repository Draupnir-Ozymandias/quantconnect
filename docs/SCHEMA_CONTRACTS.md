# QCRL Schema Contracts

**As of:** 2026-09-07

## Contract matrix

| Contract | Current version | Primary producer | Primary consumers | Persistence |
|---|---|---|---|---|
| Research report | `qcrl.research_report.v6` | `report_models.py` / algorithm | ObjectStore, API summary publication | canonical run artifact |
| Experiment record | `qcrl.experiment_record.v5` | `ResearchReport.to_record()` | `ExperimentStore`, `ResearchTools`, discovery | normalized research row |
| Campaign manifest | `qcrl.campaign.v1` | human-authored JSON | `qcrl_campaign.py`, `synch.sh` | version controlled |
| Campaign state | `qcrl.campaign_state.v1` | `qcrl_campaign.py` | runner, collector, validator, analyzers | ignored `.qcrl/` state |
| Methodology | `qcrl.methodology.lookahead_free.v1` | runtime metadata | validators and analysts | embedded in report/record |
| Synthesis specifications | type-specific `*.v1` schemas | human-authored JSON | `qcrl_synthesis.py`, specialized engines | version controlled |
| Polymarket market contract | `qcrl.polymarket_market_contract.v2` | `execution_truth/contracts.py` | order-book normalization; future timing/replay layers | derived, content-addressed observation |
| Polymarket order book | `qcrl.polymarket_order_book.v1` | `execution_truth/contracts.py` | future replay and shadow-decision layers | derived, content-addressed observation |
| Polymarket raw bundle | `qcrl.polymarket_raw_bundle.v1` | `execution_truth/acquisition.py` | offline normalization and audit | content-addressed raw observation |
| Polymarket normalized bundle | `qcrl.polymarket_normalized_bundle.v1` | `execution_truth/bundle.py` | future timing/replay layers | derived, content-addressed observation |
| Polymarket raw discovery | `qcrl.polymarket_raw_discovery.v1` | `execution_truth/acquisition.py` | discovery normalization and audit | content-addressed raw observation |
| Polymarket discovery spec/result | `qcrl.polymarket_discovery_spec.v1` / `qcrl.polymarket_discovery_result.v1` | human declaration / `execution_truth/discovery.py` | market-contract acquisition and audit | versioned declaration / derived evidence |
| Directional signal intent | `qcrl.directional_signal_intent.v1` | future signal adapter | market binding and replay | content-addressed decision input |
| Polymarket binding policy/result | `qcrl.polymarket_binding_policy.v1` / `qcrl.polymarket_binding_result.v1` | human declaration / `execution_truth/binding.py` | replay and shadow-decision layers | versioned declaration / derived evidence |
| Polymarket live evidence inventory | `qcrl.polymarket_live_evidence_inventory.v1` | deliberate operator promotion | regression tests and audit | version controlled |

The QCRL engine version and schema versions are different concerns. The clean
baseline pins engine 2.2.0, most directional campaigns pin 2.3.0, and temporal
campaigns pin 2.4.0; all can produce the current report/record contracts when
run with current code. Completed evidence retains its manifest-pinned version.

## Polymarket execution-truth contracts

The market contract reconciles Gamma identity, market terms, status, and
outcome-token pairs with the current CLOB market-information response. The
order-book contract binds full depth to a market contract and independently
checks condition ID, token ID, tick size, and minimum order size. Both retain
canonical source hashes and normalized artifact hashes.

These contracts are deliberately pure and read-only. The current producer
accepts already-acquired mappings. The separate acquisition adapter contains
public GET requests but no credentials, signing, or order path. Checked-in
fixtures are derived from public documentation and test compatibility only.
They are not live market evidence. Market contract v1 is superseded because it
conflated Gamma `startDate` with `eventStartTime`; no reader supports v1. See
`docs/EXECUTION_TRUTH.md` for acquisition and evidence requirements.

Raw discovery records the separately hashed series and event observations used
to identify a target interval. The discovery result requires one and only one
market to match explicit series, event time, asset, duration, TWAP, resolution,
outcome, and orderability fields. Slug and title text are not contract inputs.

A signal intent declares identity, asset, source timeframe, direction,
availability time, target interval, and methodology version. Binding requires
exact market-window and policy agreement, a post-observation decision within
the declared entry window, an orderable market, and an unambiguous outcome
token. Expected incompatibility is retained as a hashed result with rejection
reasons. A daily signal therefore cannot silently bind to a five-minute market.

The live evidence inventory declares every promoted raw path, artifact schema
and hash, exact capture time, evidence role, limitations, and normalized hash
where applicable. Verification fails on an undeclared/missing artifact, path
escape, schema/hash/time drift, or an offline replay failure. The inventory's
daily-series finding is compatibility evidence, not signal research evidence.

## Research report contract

The report is the complete per-run research object. It contains configuration,
performance, risk, analytics, scores, metadata, validation facts, and optional
telemetry. It is persisted to QuantConnect ObjectStore and selected metrics are
published as custom backtest summary statistics for API retrieval.

LEAN portfolio statistics are not substitutes: the current research algorithm
simulates an internal binary bankroll and submits no portfolio orders.

## Experiment record contract

The normalized record flattens report content for comparison and discovery.
Consumers must use typed/current fields when available and tolerate missing
legacy optional fields. They must not silently reinterpret missing provenance
as local or unauthoritative evidence.

Current provenance expectations include Git commit/branch, campaign ID,
methodology and validation identity, and API collection source/timestamp.
Twenty-four early baseline/Stage-1 cases predate explicit `metrics_source` but
retain API collection timestamps; this documented legacy exception does not
generalize to new campaigns.

## Campaign contract

A manifest declares project, parameters, matrix/variants, deterministic case
naming, scoring/cohort rules, submission policy, evidence role, and limitations
as applicable. Expansion creates stable case IDs. State records execution,
backtest IDs, attempts, rate-limit events, collection, metrics, and validation.

The manifest is the experiment declaration; state is execution history. A
change to scientific parameters requires a new manifest/campaign ID, not an
edit that obscures previously collected evidence.

## Synthesis contract

Synthesis specs name immutable campaign inputs and predeclared cross-campaign
rules. Generated evidence and human-readable JSON reports are stored under
`.qcrl/syntheses/`. Each specialized schema is independent and must be versioned
when its interpretation changes.

## Compatibility rules

1. Writers emit only the current contract version.
2. Readers either support a named older version explicitly or fail clearly;
   no best-effort semantic guessing.
3. Adding an optional field requires a documented default and a test.
4. Renaming, removing, changing units, or changing meaning requires a schema
   version increment and migration/compatibility test.
5. Engine-version differences remain manifest facts and must not be normalized
   away.
6. Historical v4/v5 references in `QCRL_SYNC.md` describe snapshots at that
   date; they do not override the matrix above.

## Known version inconsistency

`config.py` still identifies manual runs as QCRL 2.3.0 and selects the legacy
EMA 5/10 filter. Temporal declarations use 2.4.0 and the surviving research
candidate uses `filter_model=none`. Until normalized in a separate code change,
manual defaults must never be used to infer the candidate or reproduce a
campaign. Use the versioned manifest.
