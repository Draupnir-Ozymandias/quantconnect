# QCRL Polymarket Execution Truth

**As of:** 2026-09-07
**Status:** read-only contract kernel implemented; network acquisition pending

## Purpose

This lane determines whether a QCRL signal could be mapped to an identifiable
Polymarket market and observable order book after the signal became available.
It does not authorize orders, credentials, strategy changes, or reinterpretation
of research results.

The historical Polymarket scripts outside this repository are archaeological
evidence only. They may supply failure cases or fixture ideas, but they are not
an architecture or an authoritative resolution source.

## Implemented boundary

`execution_truth/contracts.py` implements two pure-Python normalization
contracts:

- `qcrl.polymarket_market_contract.v1` joins Gamma market identity, terms, and
  state to CLOB V2 outcomes, constraints, and fee parameters.
- `qcrl.polymarket_order_book.v1` binds a full-depth CLOB book to one validated
  market outcome.

Both contracts preserve canonical hashes of their raw source payloads and hash
their normalized output. They perform no network access and mutate no input.

The normalizers fail closed when:

- Gamma and CLOB disagree about token IDs or outcome labels;
- the binary market does not expose exactly two unique outcomes;
- resolution source, description, or start/end terms are absent;
- a book names a foreign condition or token;
- book tick/minimum-size constraints disagree with the market contract;
- a book contains duplicate price levels or is crossed/locked; or
- required timestamps, decimals, booleans, or hashes are malformed or absent.

## Evidence classes

The checked-in JSON under `tests/fixtures/polymarket/` is a deterministic,
documentation-derived fixture. It proves parser behavior only. It is explicitly
not a captured live market and cannot support claims about availability,
liquidity, fees, fills, or resolution.

A future live fixture must preserve the complete unmodified responses from:

1. Gamma market detail;
2. CLOB V2 market information;
3. both outcome-token order books; and
4. any market-specific resolution terms or reference-price source.

Every response must have an observation timestamp, endpoint identity, and
SHA-256 digest. Normalized artifacts are derived evidence and never replace the
raw responses.

## Architectural invariants

1. Signal time, observation time, decision time, hypothetical submission time,
   exchange time, and resolution time are different facts.
2. Token ordering and slug grammar carry no semantic authority.
3. Outcome direction must be established by explicit source agreement.
4. Gamma metadata, CLOB constraints, books, and resolution are independently
   observed and reconciled.
5. Decimal values remain decimal strings at the contract boundary.
6. No incomplete or contradictory observation becomes an eligible decision.
7. Execution-truth work remains independent of the locked 2026Q4 evidence lane.

## Next vertical slice

Build an unauthenticated acquisition adapter with injected transport and clock,
capture one complete current BTC Up/Down market bundle, and replay that bundle
offline through these contracts. The adapter must contain no credential,
signing, balance, position, or order endpoint.
