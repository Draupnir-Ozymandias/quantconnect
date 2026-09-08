# QCRL Documentation Map

This directory separates current state, durable decisions, reproducible
evidence, and operating procedure. It prevents a chronological research log
from becoming an accidental second source of truth.

## Document ownership

| Question | Authoritative document |
|---|---|
| What is true now? | [`QCRL_PROJECT_STATUS.md`](../QCRL_PROJECT_STATUS.md) |
| What is the intended system design? | [`QCRL_ARCHITECTURE.md`](../QCRL_ARCHITECTURE.md) |
| What happened, and when? | [`QCRL_SYNC.md`](../QCRL_SYNC.md) |
| Which campaigns exist and what did they establish? | [`CAMPAIGN_REGISTRY.md`](CAMPAIGN_REGISTRY.md) |
| Which decisions govern current work? | [`DECISION_LOG.md`](DECISION_LOG.md) |
| Which ideas failed, remain open, or are locked? | [`HYPOTHESIS_REGISTRY.md`](HYPOTHESIS_REGISTRY.md) |
| What contracts join engine, runner, and discovery? | [`SCHEMA_CONTRACTS.md`](SCHEMA_CONTRACTS.md) |
| What defines read-only Polymarket execution truth? | [`EXECUTION_TRUTH.md`](EXECUTION_TRUTH.md) |
| How are hypothetical taker fills estimated? | [`TAKER_REPLAY.md`](TAKER_REPLAY.md) |
| How does an operator synchronize and run research? | [`OPERATOR_WORKFLOW.md`](OPERATOR_WORKFLOW.md) |
| How are experiments declared? | Versioned JSON under [`campaigns/`](../campaigns/) and [`syntheses/`](../syntheses/) |

`README.md` is the entry point, not a research ledger. Generated `.qcrl/`
artifacts are reproducible local evidence, not version-controlled declarations.

## Update rules

1. Update `QCRL_PROJECT_STATUS.md` when the current conclusion, inventory,
   version state, guardrails, or next step changes.
2. Append a dated block to `QCRL_SYNC.md`; never rewrite history merely because
   a later experiment changed the conclusion.
3. Add or update a campaign registry row whenever a manifest is added,
   completed, invalidated, or superseded.
4. Record a decision when evidence changes what work is authorized. Record a
   hypothesis before testing it and close it explicitly afterward.
5. Update schema contracts in the same commit as a contract change. Producers,
   consumers, compatibility behavior, and tests must all be named.
6. Keep prospective declarations immutable after lock. A correction requires a
   new manifest and a documented invalidation; it must not silently replace the
   original.

## Status vocabulary

- **accepted** — governs current work.
- **supported** — passed its declared evidence gate but is not deployment
  authorization.
- **hold** — evidence is insufficient or conflicting; do not optimize from it.
- **rejected** — failed its declared gate.
- **closed** — rejected and unavailable for tuning without genuinely new,
  independent evidence.
- **inconclusive** — adequately framed but insufficiently resolved.
- **locked** — declaration is immutable until its stated evaluation condition.
- **superseded** — retained for provenance but replaced by a named successor.

## Documentation ambiguity register

| Former ambiguity | Resolution |
|---|---|
| QCRL 2.2.0, 2.3.0, and 2.4.0 are all described as active | They are manifest-pinned evidence versions: baseline, directional, and temporal respectively. There is no single normalized manual default yet. |
| `config.py` defaults to EMA 5/10 while the surviving candidate is unfiltered | The default is legacy/manual convenience. A versioned manifest, never `config.py`, defines reproducible candidate configuration. |
| Historical sync sections name report v5 / record v4 | Those are dated snapshots. Current contracts are report v6 / record v5. |
| Architecture listed dashboards, clustering, and discovery concepts as completed/current | Only owned, executable, tested modules are now listed as verified; prototypes and proposals are labeled separately. |
| README, status, and sync all contained result summaries | Status owns the current verdict, the campaign registry owns the evidence index, README examples are historical/operator context, and sync owns chronology. |
| “Polymarket martingale” suggests a deployable trading system | QCRL currently models synthetic BTC binary outcomes; no Polymarket execution path exists, and martingale is closed. |

## Documentation review checklist

- Numerical claims point to a manifest/synthesis and derived evidence location.
- Historical, post-hoc, and prospective evidence are not conflated.
- “Current” appears only in documents whose ownership permits it.
- Candidate configuration is not inferred from `config.py` manual defaults.
- Implemented components are not mixed with proposals.
- No documentation change modifies campaign parameters or evidence artifacts.
