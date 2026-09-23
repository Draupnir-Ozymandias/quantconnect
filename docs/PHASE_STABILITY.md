# Market-phase sequence stability

The phase-stability analyzer compares one predeclared early, middle, and late
book sequence from the same market. It is deterministic, offline, and
content-addressed. Missing phases are rejected rather than imputed.

Run the checked-in September 15 example with:

```bash
./synch.sh evidence phase-stability \
  execution_truth/specs/phase_stability_daily_20260915.json
```

For each phase and outcome, the result reports best-price, spread, midpoint,
top-size, and full displayed-depth ranges; first-to-last observed midpoint
displacement; missing best-side counts; distinct exchange-book and normalized
snapshot counts; polling-gap bounds; and execution-metadata consistency.
Cross-phase output compares the first observed two-sided midpoint in each phase.
If a phase is one-sided, its midpoint and displacement remain null.

The September 15 capture contains 12 observations per phase. Early and middle
were two-sided at a one-cent spread throughout their capture windows. Late was
one-sided throughout: Up had no displayed best bid and Down had no displayed
best ask. Execution metadata was stable within every phase. Requested five-second
polling produced observed acquisition gaps of roughly 5.53–5.68 seconds.

These are public displayed-book descriptions, not executable fill evidence.
Three phases from one market do not establish cross-market stability. The
Binance noon-Eastern contract remains incompatible with the Coinbase
midnight-UTC QCRL signal, and the result does not establish queue position,
latency, fills, settlement, or profitability.

The follow-on analyzer retains complete and partial markets separately. See
[CROSS_MARKET_PHASES.md](CROSS_MARKET_PHASES.md).
