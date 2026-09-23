# Cross-market phase analysis

The cross-market phase analyzer compares aligned early, middle, and late public
book sequences across multiple locked markets. It is deterministic, offline,
content-addressed, and descriptive only.

Run the September cohort with:

```bash
./synch.sh evidence cross-market-phases \
  execution_truth/specs/cross_market_phase_daily_20260915_20260922.json
```

The specification declares all three phase keys for every market. A missed
phase is written as `null`; omitting the key is invalid. Partial markets
contribute only their observed phase cells. The analyzer requires at least two
complete markets before producing complete early-to-middle-to-late paths and
never imputes a missing phase or book side.

## September 15–22 evidence

The result hash is
`e3bdac21b4cbc44aeddbfc8b0357d15368b6d3489a0feb4210f63fc6b743d5bf`.
Coverage is 10 observed sequences across four markets:

| Market ending | Early | Middle | Late | Coverage |
|---|---:|---:|---:|---|
| September 15 | observed | observed | observed | complete |
| September 18 | observed | observed | observed | complete; late cadence degraded |
| September 20 | observed | missed | observed | partial |
| September 22 | observed | missed | observed | partial |

Early evidence is the most consistent structural observation. All four books
were two-sided, Up's first midpoint ranged from 0.495 to 0.575, spreads ranged
from 0.01 to 0.02, and the short-window midpoint displacement ranged from
-0.01 to +0.01. Displayed depth was not stable in magnitude: Up displayed bid
depth ranged from about 23,916 to 326,274 shares across the cohort.

Middle evidence is thin. Both complete markets were two-sided at a 0.01
spread, but Up's first midpoint was 0.205 in one and 0.735 in the other. Phase
therefore describes time remaining, not a predictable price level or side.

Late evidence is heterogeneous. Two of four markets were one-sided throughout
their samples; the other two retained both sides. Three of four were either
one-sided or already at an observed midpoint of at most 0.05 or at least 0.95.
The remaining market was still repricing materially, with Up moving from 0.805
to 0.755 during the sequence. Observed two-sided late spreads ranged from 0.006
to 0.03.

One September 18 late polling gap was 1007.056607 seconds rather than roughly
five seconds. The artifact remains evidence of two valid observations, but the
sequence is marked as degraded cadence and cannot be interpreted as a nominal
one-minute trajectory. Every other sequence had maximum gaps below 5.71 seconds.

Execution metadata was stable within every observed sequence and consistent
with the prior finding: orders and fees were enabled, while taker-delay state
and minimum order age remained unknown. Any subsequent fixed-grid replay must
therefore retain fail-closed mechanics unless separate evidence resolves those
fields; public books alone cannot justify a fill or profitability claim.

## Interpretation boundary

The evidence supports a narrow descriptive claim: these daily markets tended
to begin with balanced, tight two-sided books and became more polarized near
resolution. It does not establish stable liquidity magnitude, a tradeable phase
rule, a fill model, or a compatible QCRL signal. Two complete markets are too
few for a stability verdict, and the Binance noon-Eastern terms remain
incompatible with the Coinbase midnight-UTC research lane.
