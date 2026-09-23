# Cross-market fixed-grid latency batch

The latency batch applies one unchanged request shape, replay policy, and
latency grid to every observed phase in the September 15–22 cohort. It derives
each market's Up token from verified identity and anchors the hypothetical
decision to that sequence's capture start. Missing phases remain missing.

Run it offline with:

```bash
./synch.sh evidence latency-batch \
  execution_truth/specs/latency_batch_daily_20260915_20260922.json
```

The deterministic batch hash is
`e86e727cf6b49b5bbff8aef219f92390dd44aea4c0e2897ebcc8dac318e086f6`.
Ten observed phase sequences produce 60 rows from the fixed
`[0, 1, 5, 10, 15, 20]` second grid. All 60 rows select an admissible observed
book, and all 60 nested mechanics results reject both
`unknown_taker_delay_state` and `unknown_minimum_order_age`. Six rows also
reject `exchange_book_stale`: three in September 18 late and three in
September 20 early.

The September 18 late sequence retains its separate degraded-cadence warning.
The batch neither calibrates its grid to these markets nor converts successful
book selection into fill evidence. It establishes that the public timing fields
are still insufficient for executable replay across the cohort.
