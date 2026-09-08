# Snapshot taker replay v1

`execution_truth/taker_replay.py` provides
`replay_taker_buy(raw_bundle, request, policy)`. It verifies and normalizes the
raw bundle, then estimates a hypothetical BUY against the chosen token's asks.
Every result is labeled `snapshot_mechanics_only` and explicitly leaves strategy
eligibility unevaluated. Each invocation is independent; repeated calls do not
reserve liquidity or maintain a portfolio.

## Inputs and accounting

The request declares token ID, gross shares, limit price, FAK or FOK, available
cash including fees, and hypothetical execution time. Monetary inputs are
decimal strings. Policy declares maximum ages for Gamma/CLOB metadata, book
observation, and exchange timestamp separately. A timestamp after the replay
time is rejected. The replay does not read the current clock.

Asks are consumed in ascending price order up to the limit. FAK keeps available
partial fills and cancels the remainder. FOK produces zero fills and zero fees
unless the entire quantity fits both displayed depth and the cash budget.
Requested quantity must meet the market minimum and use at most six decimal
places. An individual partial match may be smaller than the requested minimum.
This quantity is shares, not the cash-amount argument of an SDK market-buy call.

The supported fee curve is exponent 1, using the captured rate:

```text
estimated fee = shares × captured fee rate × price × (1 − price)
estimated cash required = shares × price + estimated fee
```

The formula and five-decimal fee precision follow the official
[fee documentation](https://docs.polymarket.com/trading/fees). This replay
declares `ROUND_HALF_UP` once per aggregated price level. Individual maker
matches are unavailable in aggregate books, so rounding and cash-equivalent
accounting are model assumptions, not exact wallet debits or received-token
settlement. Captured legacy base-fee basis points are not added to the curve.
Unknown fee enablement, contradictory disabled-fee metadata, and unsupported
curve exponents produce a rejection. No fee parameters are inferred from the
market category.

FAK/FOK semantics follow the official
[order lifecycle](https://docs.polymarket.com/concepts/order-lifecycle).

## What the snapshots establish

The model assumes displayed depth remains available through the hypothetical
execution time, within the declared freshness bounds. It cannot reconstruct
competing orders, cancellation, maker queues, hidden liquidity, latency paths,
actual settlement, or profitability. Delay-enabled markets and nonzero order
age constraints require a temporal model and are rejected here.

The daily capture for market `4293892` omits CLOB `itode`. Market contract v2
currently defaults that absence to false. Replay rechecks the raw response and
returns `unknown_taker_delay_state`; absence cannot establish zero delay. The
five-minute capture explicitly sets the flag true and also cannot support this
immediate execution model. Existing raw observations and schemas are preserved.

## Runnable examples

From the project directory:

```bash
./synch.sh evidence replay execution_truth/specs/synthetic_taker_replay.json
./synch.sh evidence replay execution_truth/specs/daily_taker_replay.json
```

Both commands run entirely offline and print deterministic JSON; neither writes
evidence nor contacts an API. Bundle paths are resolved relative to the example
file. The synthetic example uses a documentation-derived fixture, distinct
from the three captured artifacts under `evidence/polymarket/live/`.

| Synthetic case | Requested | Limit | Result | Estimated cash including fees |
|---|---:|---:|---|---:|
| Full FAK | 100 shares | 0.50 | 100 shares filled | 51.75 |
| Partial FAK | 150 shares | 0.50 | 100 filled, 50 canceled | 51.75 |
| All-or-nothing FOK | 150 shares | 0.50 | Unfilled | 0 |
| Below ask | 100 shares | 0.49 | Unfilled | 0 |

The live daily example returns four rejections with
`unknown_taker_delay_state`. These are expected evidence-completeness results.
No artificial signal is attached to either example, and daily series 41
remains incompatible with the current QCRL signal.

Results hash the raw bundle, normalized market and selected snapshot, request,
policy, matched levels, costs, reasons, and limitations. Rejected results and
unfilled orders retain zero expenditure. Decimal calculations use a fixed
local precision to keep replay independent of the caller's decimal context.
