# Independent Binance resolution-source reconciliation

The resolution-source lane acquires the exact public Binance BTCUSDT
one-minute candles opening at each market's declared start and end boundaries.
It validates the requested millisecond window, returned open time, returned
close time, payload hash, symbol, interval, market identity, and 24-hour event
duration before comparing the two close prices.

Capture one market only after it has ended:

```bash
./synch.sh evidence capture-binance-resolution \
  <market-id> <event-start-utc> <event-end-utc>
```

Reproduce the checked-in five-market comparison with:

```bash
./synch.sh evidence binance-settlement-cohort \
  execution_truth/specs/binance_settlement_cohort_daily_20260915_20260930.json
```

The deterministic cohort hash is
`df71f644be525d92122a2aaa46d8c30fdd18df3c9aa5ac5af2a86c5734a4f693`.

| Market ending | Start close | End close | Calculated | Platform | Verdict |
|---|---:|---:|---|---|---|
| September 15 | 78,558.01 | 76,457.61 | Down | Down | match |
| September 18 | 76,764.23 | 80,705.44 | Up | Up | match |
| September 20 | 81,624.88 | 80,869.54 | Down | Down | match |
| September 22 | 85,910.99 | 86,420.26 | Up | Up | match |
| September 30 | 83,112.00 | 84,160.25 | Up | Up | match |

All five platform outcomes agree with the independently fetched public candle
comparison. This is resolution consistency, not signal accuracy. The API
observations were made later, do not prove what data was available at the
original resolution instant, and do not audit Polymarket's internal oracle
procedure. They establish no order, fill, redemption, or profitability.
