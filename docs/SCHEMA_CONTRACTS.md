# QCRL Schema Contracts

**As of:** 2026-09-08

## Contract matrix

| Contract | Current version | Primary producer | Primary consumers | Persistence |
|---|---|---|---|---|
| Research report | `qcrl.research_report.v6` | `report_models.py` / algorithm | ObjectStore, API summary publication | canonical run artifact |
| Experiment record | `qcrl.experiment_record.v5` | `ResearchReport.to_record()` | `ExperimentStore`, `ResearchTools`, discovery | normalized research row |
| Campaign manifest | `qcrl.campaign.v1` | human-authored JSON | `qcrl_campaign.py`, `synch.sh` | version controlled |
| Campaign state | `qcrl.campaign_state.v1` | `qcrl_campaign.py` | runner, collector, validator, analyzers | ignored `.qcrl/` state |
| Methodology | `qcrl.methodology.lookahead_free.v1` | runtime metadata | validators and analysts | embedded in report/record |
| Synthesis specifications | type-specific `*.v1` schemas | human-authored JSON | `qcrl_synthesis.py`, specialized engines | version controlled |
| Polymarket market contract | `qcrl.polymarket_market_contract.v3` | `execution_truth/contracts.py` | order-book normalization; timing/replay layers | derived, content-addressed observation |
| Polymarket order book | `qcrl.polymarket_order_book.v1` | `execution_truth/contracts.py` | future replay and shadow-decision layers | derived, content-addressed observation |
| Polymarket raw bundle | `qcrl.polymarket_raw_bundle.v1` | `execution_truth/acquisition.py` | offline normalization and audit | content-addressed raw observation |
| Polymarket normalized bundle | `qcrl.polymarket_normalized_bundle.v2` | `execution_truth/bundle.py` | timing/replay layers | derived, content-addressed observation |
| Polymarket raw/normalized book sequence | `qcrl.polymarket_raw_book_sequence.v1` / `qcrl.polymarket_book_sequence.v1` | `execution_truth/book_sequence.py` | temporal sensitivity and audit | ignored raw capture / derived content-addressed summary |
| Polymarket raw slug resolution | `qcrl.polymarket_raw_slug_resolution.v1` | `execution_truth/acquisition.py` | operator market selection and audit | ignored or deliberately promoted raw observation |
| Polymarket raw discovery | `qcrl.polymarket_raw_discovery.v1` | `execution_truth/acquisition.py` | discovery normalization and audit | content-addressed raw observation |
| Polymarket discovery spec/result | `qcrl.polymarket_discovery_spec.v1` / `qcrl.polymarket_discovery_result.v1` | human declaration / `execution_truth/discovery.py` | market-contract acquisition and audit | versioned declaration / derived evidence |
| Directional source contract/bar | `qcrl.directional_source_contract.v1` / `qcrl.directional_source_bar.v1` | human declaration / future data adapter | boundary signal materialization | versioned declaration / hashed observation |
| Candle-streak signal spec/decision | `qcrl.candle_streak_signal_spec.v1` / `qcrl.directional_signal_decision.v1` | human declaration / `execution_truth/signal_adapter.py` | signal intent and audit | versioned declaration / derived evidence |
| Directional signal intent | `qcrl.directional_signal_intent.v2` | `execution_truth/signal_adapter.py` | market binding and replay | content-addressed decision input |
| Polymarket binding policy/result | `qcrl.polymarket_binding_policy.v2` / `qcrl.polymarket_binding_result.v2` | human declaration / `execution_truth/binding.py` | replay and shadow-decision layers | versioned declaration / derived evidence |
| Polymarket live evidence inventory | `qcrl.polymarket_live_evidence_inventory.v1` | deliberate operator promotion | regression tests and audit | version controlled |
| Taker replay request/policy/result | `qcrl.taker_replay_request.v1` / `qcrl.taker_replay_policy.v1` / `qcrl.taker_replay_result.v2` | local declaration / `execution_truth/taker_replay.py` | offline mechanics audit | hashed result; output to stdout |
| Taker replay example | `qcrl.taker_replay_example.v1` | versioned JSON specification | `qcrl_execution_truth.py` | version controlled |
| Latency sensitivity policy/result/example | `qcrl.latency_sensitivity_policy.v1` / `qcrl.latency_sensitivity_result.v1` / `qcrl.latency_sensitivity_example.v1` | versioned declaration / `execution_truth/latency_sensitivity.py` | execution-truth audit | declaration versioned; result printed and hashed |

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

A source contract declares venue, instrument, input resolution, price
semantics, exact duration, UTC anchor, and tie policy. The current declaration
is Coinbase BTCUSD minute trades consolidated into 86,400-second bars anchored
at midnight UTC. Source bars are individually hashed and must be aligned,
contiguous, complete, and no earlier than their end time.

The candle-streak adapter consumes only those completed bars. It emits a hashed
decision at the next boundary, including an intent only when sufficient prior
non-tied directions form the declared streak. A signal intent declares
identity, asset, source timeframe, direction,
availability time, target interval, and methodology version. Binding requires
exact market-window and policy agreement, a post-observation decision within
the declared entry window, an orderable market, and an unambiguous outcome
token. Intent/binding v2 additionally requires the exact source-contract hash
approved by policy. Expected incompatibility is retained as a hashed result
with rejection reasons. V1 intent/binding artifacts are superseded and cannot
be consumed.

The live evidence inventory declares every promoted raw path, artifact schema
and hash, exact capture time, evidence role, limitations, and normalized hash
where applicable. Verification fails on an undeclared/missing artifact, path
escape, schema/hash/time drift, or an offline replay failure. The inventory's
daily-series finding is compatibility evidence, not signal research evidence.

Replay consumes a complete raw bundle and revalidates it before choosing one
token book. Requests name share quantity, cash budget, limit, FAK/FOK, and
hypothetical timestamp. Policy fixes freshness bounds and depth/fee assumptions.
Results include input hashes, per-level matches, cost estimates, rejection and
no-fill reasons, and `strategy_eligibility_evaluated=false`. Market v3 replaces
v2's execution-field defaults with explicit unknowns for missing/null `itode`,
`oas`, `acceptingOrders`, and `feesEnabled`. Malformed values are errors, not
coerced booleans or integers. Replay result v2 rejects unknown minimum order
age as well as unknown delay. Normalized bundle v2 embeds market v3; derive it
again from raw evidence rather than consuming old normalized contracts.
See [TAKER_REPLAY.md](TAKER_REPLAY.md) for rules and migration boundaries.

A raw book sequence is a bounded list of complete raw market bundles. It keeps
every repeated response as an independently timed observation. Its derived
summary requires stable market/outcome identity and strictly increasing sample
acquisition times, while allowing state, constraints, and books to change.
Bounds are 2–120 samples, integer 1–60 second sleeps, and no more than one hour
of scheduled pauses. See [BOOK_SEQUENCE.md](BOOK_SEQUENCE.md).

Latency sensitivity treats the taker request's hypothetical timestamp as its
decision reference, adds declared integer delays, and selects only the first
requested-token book observed at or after each arrival. It reports post-arrival
observation lag and polling bracket, applies a maximum lag, and delegates
mechanics to fail-closed taker replay at the selected observation time. It never
interpolates or carries a prior book forward. An evaluated row may contain a
rejected mechanics result. See
[LATENCY_SENSITIVITY.md](LATENCY_SENSITIVITY.md).

Slug resolution is an exact, hashed lookup rather than semantic discovery.
Event and market slugs use their distinct official Gamma endpoints. An event
must contain exactly one market; multi-market selection is rejected. The
artifact preserves the requested slug, reference kind, endpoint response,
observation time, payload hash, and resolved numeric market ID. It does not
assert source/timeframe compatibility or strategy eligibility.

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
