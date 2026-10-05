# Delayed-decision signal contract

Implemented 2026-10-05. Offline diagnostic only; no binding or orders.

`execution_truth/delayed_signal.py` consumes the verified aligned-lane declaration,
a hash-verified boundary dataset, a target ending on a specified local Eastern
date, and an explicit timezone-qualified decision timestamp. It regenerates the
source audit rather than trusting a supplied summary or hand-edited source record.

The input must end exactly at the target's starting noon boundary. Future
boundary candles or a different target raise a contract error. Any missing date
in the declared history prevents emission, even if the trailing pair looks usable.
Only complete history permits the existing skip-ties convention: compare the
two most recent non-tied source directions and reverse an identical pair.
Insufficient non-tied history or mixed directions produces no intent.

## Time contract

The target remains its original local-noon-to-local-noon window; it is not
shifted to make the decision appear timely. The latest input candle completes
one minute after target start. All provided input observations, including ties,
must actually be recorded by the explicit decision time. Availability is the
latest recorded retrieval time across that history, not an assumed publication
time or a backdated noon timestamp. A decision at or after target end rejects.
Calendar planning preserves actual 23/24/25-hour target durations.

These are diagnostic timing checks, not an approved maximum entry-delay policy.
An emission late within the window is not permission to trade. Historical
retrieval remains historical retrieval; it cannot establish original live
availability. Synthetic evidence classification remains visible in the intent.

## Separate versioned outputs

`qcrl.delayed_directional_signal_decision.v1` records the declaration, dataset,
source-audit and boundary-plan hashes, explicit target/decision/availability
times, all non-emission reasons, and an optional intent. Expected timing and
strategy rejections are data; malformed input and target mismatch are errors.

`qcrl.delayed_directional_signal_intent.v1` additionally pins the selected source
record hashes and declared signal configuration. It records decision delay,
actual target duration, and direction. It explicitly sets original-boundary
availability unproven, legacy-binding compatibility false, and orders
unauthorized. Decisions and intents have their own content hashes.

This is not `qcrl.directional_signal_intent.v2`: the existing binder rejects
the new schema. No Coinbase contract, methodology, locked campaign, replay gate,
or unresolved `oas` interpretation changes.

## Operator interface

```bash
./synch.sh evidence delayed-signal \
  execution_truth/specs/binance_noon_eastern_research_lane.json \
  /absolute/path/to/boundary-dataset.json \
  --target-end-date YYYY-MM-DD \
  --decision-at-utc TIMEZONE-QUALIFIED-ISO-TIMESTAMP
```

Output is hashed JSON on stdout. The dataset argument is the raw dataset object,
not an entire assembly envelope. No acquisition or persistence occurs.

The current retained September sample must not be forced to emit a historical
intent by rewriting retrieval times or removing gaps. Tests use explicitly
synthetic contiguous histories to exercise the contract honestly.

The separate delayed-binding/freshness diagnostic policy is implemented; see
`DELAYED_BINDING_FRESHNESS.md`. It requires explicit target terms and timing
limits while retaining unknown-field restrictions. It is opt-in, not implied
by this signal contract. Neither an emission
nor a support reply establishes actual order acceptance, fills, or profitability.
