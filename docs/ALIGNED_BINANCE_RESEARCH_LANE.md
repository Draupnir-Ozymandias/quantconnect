# Aligned Binance/noon-Eastern research lane

Declared 2026-10-04. Status: declared, not executed. No trading authorization.

The machine-readable declaration is
`execution_truth/specs/binance_noon_eastern_research_lane.json`. It deliberately
uses a new schema, `qcrl.aligned_research_lane_spec.v1`, not the existing UTC-only
directional source contract. Validation pins the bytes and verified settlement
artifact of the September 22 market as a terms authority. That historical
example establishes semantics, not compatibility of every future market.

## What is aligned

Source is Binance spot BTCUSDT. Compare **closes of one-minute candles whose
open times equal consecutive local calendar noons** in `America/New_York`.
This is close-to-close direction, not the open versus close of a conventional
daily OHLC candle. The captured market explicitly names those candle closes;
higher final close means Up, lower means Down, equality settles 50/50.

The initial research candidate remains length-2 candle-streak reversal, no
filters, both directions, no sizing. History uses the most recent non-tied
completed intervals, preserving the existing skip-ties convention without
changing the market's separate split-settlement rule. Ties, missing candles,
availability failures, and non-signals must be recorded separately, not
silently counted as wins or losses. A missing exact candle rejects the input:
no nearest candle, Coinbase fallback, or interpolation.

Coinbase results do **not** transfer. H-013 remains closed, H-014's prospective
2026Q4 declaration remains untouched, and no new confirmatory hypothesis is
opened by this engineering declaration. Historical exploration in this lane
must be labeled independently; the evaluation window and acceptance gate are
explicitly unset. No optimization is declared.

## Availability is part of the contract

Binance identifies a kline by its opening time and returns both close price and
close time. See the [official Spot market-data documentation](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market).
The candle starting at 12:00 spans that minute. Its finalized close must not
be used as an input to a decision at 12:00:00.

For a target starting at noon, the latest prior direction uses that noon's
candle close. The earliest planned decision is therefore **12:01 local**, and
only after actual observation of the finalized candle. This is a lower bound,
not a latency assumption or guarantee. Historical retrieval cannot prove the
price was observed at that earliest time. A future adapter must record candle
completion, actual observation, and decision times separately.

The current signal-intent/binding contracts require availability by the target
start. They cannot represent this delayed decision correctly. They must not be
reused by changing timestamps or claiming early availability. A separate
versioned delayed-decision contract is an activation prerequisite.

## Calendar boundaries and DST

Use local calendar noons, not a constant UTC offset or repeated 86,400-second
steps. Summer noon is 16:00 UTC; winter noon is 17:00 UTC. A window crossing
the clock change can span 23 or 25 elapsed hours. The planner retains the actual
duration but does not assert that a corresponding Polymarket contract exists.
Each market's explicit start/end, instrument, resolution terms, and ties must
match independently; series ID or slug is insufficient.

Existing daily source, binding, and Binance reconciliation adapters assume
fixed 24-hour windows. They remain unchanged and are not activated by this
declaration, including for ordinary 24-hour days in the new lane.

## Offline operator checks

Verify declaration and pinned authority:

```bash
./synch.sh evidence research-lane execution_truth/specs/binance_noon_eastern_research_lane.json
```

Plan one target ending at local noon (example is illustrative, not a schedule):

```bash
./synch.sh evidence research-lane execution_truth/specs/binance_noon_eastern_research_lane.json \
  --target-end-date 2026-11-01
```

The plan outputs hashed UTC boundaries, actual duration, latest input candle
opening time, and earliest decision lower bound. It emits no signal, fetches
no candles, changes no collector schedule, and submits no orders.

## Next engineering step

Build a separately versioned, offline close-to-close source adapter using
hash-verified exact boundary candles. Test gaps, ties, calendar/DST windows,
observed availability, and the delayed decision before acquiring a historical
dataset or declaring a confirmatory campaign. Settlement, paper direction
accuracy, and executable returns remain distinct evidence layers. Unknown
execution fields and the new metadata-revalidation gate still apply to any
later mechanics or trading path.
