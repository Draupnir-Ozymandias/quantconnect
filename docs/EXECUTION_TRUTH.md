# QCRL Polymarket Execution Truth

**As of:** 2026-09-07
**Status:** public acquisition, explicit discovery, signal binding, immutable
local storage, and offline normalization implemented

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

- `qcrl.polymarket_market_contract.v2` joins Gamma market identity, terms, and
  state to CLOB V2 outcomes, constraints, and fee parameters.
- `qcrl.polymarket_order_book.v1` binds a full-depth CLOB book to one validated
  market outcome.
- `qcrl.polymarket_raw_bundle.v1` preserves separately timed raw Gamma, CLOB
  market-information, and two-book observations.
- `qcrl.polymarket_normalized_bundle.v1` verifies and replays those observations
  offline.

All contracts preserve canonical hashes of their raw source payloads and hash
their normalized output. Normalization performs no network access and mutates
no input.

`execution_truth/acquisition.py` provides the only network boundary. It exposes
fixed public GET routes, accepts injected transport and clock implementations,
and has no credential, signing, balance, position, or order capability.
`execution_truth/bundle.py` stores verified raw bundles under content-addressed,
no-overwrite filenames and replays them offline.

`execution_truth/discovery.py` verifies a human-authored discovery specification
against one explicitly identified Gamma series and the unique event whose
declared half-open interval contains the target time. Selection then requires
exact asset, duration, TWAP, resolution-source, outcomes, event-time, and
orderability agreement. Neither titles nor slugs participate in selection.

`execution_truth/binding.py` joins one versioned directional signal intent to
one market contract under a versioned timing policy. It distinguishes malformed
evidence (contract error) from an expected ineligibility decision (structured
rejection reasons), and maps Up or Down only through an explicit outcome label
and token ID.

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

A live fixture preserves the complete unmodified responses from:

1. Gamma market detail;
2. CLOB V2 market information;
3. both outcome-token order books; and
4. any market-specific resolution terms or reference-price source.

Every response must have an observation timestamp, endpoint identity, and
SHA-256 digest. Normalized artifacts are derived evidence and never replace the
raw responses.

The first live bundle was captured on 2026-09-07 for Gamma market `4309046`:

- market: `btc-updown-5m-1788814200`;
- actual event interval: `2026-09-07T20:50:00Z` through `20:55:00Z`;
- resolution: Chainlink BTC/USD 60-second TWAP; equality resolves Up;
- raw bundle SHA-256:
  `a9c40ee7c38a6dad0f3482b4c0c9676dd4865bc26f7042f713b080bf141fc912`;
- normalized bundle SHA-256:
  `bd7b59542b8b93d94c7525b255d567ba09e5175e6a3e6b287940663c86d3a6a6`.

The raw file is currently local ignored evidence under
`.qcrl/execution_truth/raw/`. Its hash is durable, but the file is not yet a
Git-synchronized fixture.

## Superseded timing assumption

Market contract v1 treated Gamma `startDate` as the outcome-window start. A
live response disproved that interpretation: its `startDate` preceded the
five-minute market by many hours, while `eventStartTime` exactly named the
outcome window. Version 2 preserves both fields separately and only
`event_start_at_utc` may anchor outcome timing. Version 1 must not be consumed.

## Discovery probe and timeframe boundary

A public probe on 2026-09-07 validated series `10684` without reading a slug or
title. For target `2026-09-07T21:36:50Z`, explicit series membership and event
times selected event `978977` (`21:35:00Z`–`21:40:00Z`) and market `4310537`.
Its declared configuration was BTC, five minutes, Chainlink BTC/USD 60-second
TWAP, with Up and Down outcomes.

This proves the discovery mechanism, not signal compatibility. A QCRL daily
signal targeting a daily interval fails the binding contract against this
five-minute market with `target_window_mismatch`. No fractal or cross-timeframe
equivalence is assumed. We must either discover an exactly compatible market
horizon or separately research and version a five-minute signal before any
execution replay can claim relevance.

The present LEAN callback also computes a decision when the consolidated target
bar closes, even though the entry model uses prior-bar state. A live signal
producer must materialize that prior-state decision at the target boundary;
the research callback itself is not evidence of timely executability.

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

Promote selected irreplaceable live observations into a deliberate,
Git-synchronized fixture workflow; identify whether an exact daily BTC market
contract exists; and build offline replay for compatible signals only. Replay
must model observable price, depth, fees, entry delay, partial/no fill, and
settlement before shadow execution is considered.
