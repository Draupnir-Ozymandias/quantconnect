# QCRL Polymarket Execution Truth

**As of:** 2026-09-08
**Status:** public acquisition, explicit discovery, signal binding, durable live
evidence, offline normalization, and snapshot taker mechanics implemented

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

- `qcrl.polymarket_market_contract.v3` joins Gamma market identity, terms, and
  state to CLOB V2 outcomes, constraints, and fee parameters.
- `qcrl.polymarket_order_book.v1` binds a full-depth CLOB book to one validated
  market outcome.
- `qcrl.polymarket_raw_bundle.v1` preserves separately timed raw Gamma, CLOB
  market-information, and two-book observations.
- `qcrl.polymarket_normalized_bundle.v2` verifies and replays those observations
  offline.

All contracts preserve canonical hashes of their raw source payloads and hash
their normalized output. Normalization performs no network access and mutates
no input.

`execution_truth/acquisition.py` provides the only network boundary. It exposes
fixed public GET routes, accepts injected transport and clock implementations,
and has no credential, signing, balance, position, or order capability.
`execution_truth/bundle.py` stores verified raw bundles and discovery records
under content-addressed, no-overwrite filenames, replays them offline, and
checks that every promoted live artifact agrees with its inventory declaration.
`qcrl_execution_truth.py` and `./synch.sh evidence` provide the operator boundary
for capture, deliberate promotion, and complete inventory verification.

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

`execution_truth/signal_adapter.py` makes the research source and signal boundary
explicit. The current source contract is Coinbase BTCUSD minute trade bars
consolidated into 86,400-second bars anchored at midnight UTC. This anchor is
the documented LEAN behavior for crypto daily time-period consolidators. The
adapter uses only completed, contiguous, source-bound bars and emits the
length-2 reversal intent for the next UTC interval. Late input fails closed.

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
  `2958d62063a64c2d543ef42d391ea331bbb75e04c009b5efcc8a90d1553d46fa`
  (normalized bundle v2 / market contract v3).

The raw file has now been deliberately promoted to
`evidence/polymarket/live/raw/` and is Git-synchronized. Its inventory retains
its mechanics-only role and five-minute incompatibility limitation.

## Superseded timing assumption

Market contract v1 treated Gamma `startDate` as the outcome-window start. A
live response disproved that interpretation: its `startDate` preceded the
five-minute market by many hours, while `eventStartTime` exactly named the
outcome window. Version 2 preserves both fields separately and only
`event_start_at_utc` may anchor outcome timing. Version 3 retains that correction
and replaces inferred execution-field defaults with unknowns. Versions 1 and 2
must not be consumed as current market contracts; regenerate from raw evidence.

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

## Daily-series compatibility finding

Series `41` is an active BTC Up/Down series with recurrence `daily`. A public
capture for target `2026-09-07T22:30:00Z` selected event `976673` and market
`4293892`, whose explicit outcome interval was
`2026-09-07T16:00:00Z`–`2026-09-08T16:00:00Z` (noon Eastern to noon Eastern).
The complete market and both outcome books were captured and normalized.

This is a horizon match but not a signal-contract match:

- resolution uses Binance BTC/USDT one-minute candle closes, while QCRL was
  researched on Coinbase BTCUSD;
- the Polymarket interval is explicitly noon-to-noon Eastern, while QCRL's
  crypto daily consolidator is midnight-to-midnight UTC; and
- equal daily closes settle 50/50, while QCRL skips tied bars.

The durable inventory therefore records
`incompatible_with_current_qcrl_signal`. This does not reject the market as an
execution-mechanics fixture; it rejects any claim that existing QCRL results
can be transferred to it without a new aligned research lane.

## Durable evidence workflow

Public captures land in ignored local state. Promotion is an explicit second
step, followed by whole-inventory replay:

```bash
./synch.sh evidence capture-discovery <series-id> <target-utc>
./synch.sh evidence capture-market <market-id>
./synch.sh evidence promote .qcrl/execution_truth/raw/<artifact>.json
./synch.sh evidence verify
```

The tracked inventory currently declares three artifacts: the original
five-minute bundle, the daily-series discovery record, and the daily market
bundle. Tests replay all three on every deterministic suite run.

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

## Snapshot taker mechanics

`replay_taker_buy()` now estimates BUY/FAK/FOK execution against captured asks,
including limit price, available depth, fee estimates, and a cash budget.
Freshness and exchange timestamps are checked independently. Every output is
mechanics-only. See [TAKER_REPLAY.md](TAKER_REPLAY.md) for assumptions, schemas,
sample commands, and the missing-delay-field finding in the daily capture.

## Next vertical slice

Unknown execution metadata is preserved explicitly in market contract v3; the
API reference supplies no omitted-field default. A bounded read-only recorder
now captures complete, independently timed market/book bundles and derives a
hashed sequence summary without inferring missing intervals. See
[BOOK_SEQUENCE.md](BOOK_SEQUENCE.md). Exact event/market slug resolution is
also public, hashed, and fails on ambiguous multi-market events. Sequence-based
latency sensitivity now selects only observed books at or after hypothetical
arrival, reports polling uncertainty, and preserves snapshot replay's timing
rejections. See [LATENCY_SENSITIVITY.md](LATENCY_SENSITIVITY.md). Repeated
predeclared temporal observations, settlement, and
signal-to-execution integration remain subsequent work. Any Binance
noon-to-noon research lane requires a separate declaration.
