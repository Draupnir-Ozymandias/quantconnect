# QCRL Schema Contracts

**As of:** 2026-09-06

## Contract matrix

| Contract | Current version | Primary producer | Primary consumers | Persistence |
|---|---|---|---|---|
| Research report | `qcrl.research_report.v6` | `report_models.py` / algorithm | ObjectStore, API summary publication | canonical run artifact |
| Experiment record | `qcrl.experiment_record.v5` | `ResearchReport.to_record()` | `ExperimentStore`, `ResearchTools`, discovery | normalized research row |
| Campaign manifest | `qcrl.campaign.v1` | human-authored JSON | `qcrl_campaign.py`, `synch.sh` | version controlled |
| Campaign state | `qcrl.campaign_state.v1` | `qcrl_campaign.py` | runner, collector, validator, analyzers | ignored `.qcrl/` state |
| Methodology | `qcrl.methodology.lookahead_free.v1` | runtime metadata | validators and analysts | embedded in report/record |
| Synthesis specifications | type-specific `*.v1` schemas | human-authored JSON | `qcrl_synthesis.py`, specialized engines | version controlled |

The QCRL engine version and schema versions are different concerns. The clean
baseline pins engine 2.2.0, most directional campaigns pin 2.3.0, and temporal
campaigns pin 2.4.0; all can produce the current report/record contracts when
run with current code. Completed evidence retains its manifest-pinned version.

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

