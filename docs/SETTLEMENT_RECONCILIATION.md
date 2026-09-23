# Public settlement reconciliation

Settlement evidence captures the post-resolution Gamma market payload and the
matching CLOB condition/token map through public GET endpoints. The offline
contract reconciles market identity, condition ID, outcome labels, token IDs,
closed/orderable state, resolution status, and the platform payout vector.

Capture one resolved market with:

```bash
./synch.sh evidence capture-settlement <market-id>
```

Reproduce the checked-in cohort reconciliation with:

```bash
./synch.sh evidence settlement-cohort \
  execution_truth/specs/settlement_cohort_daily_20260915_20260922.json
```

The deterministic cohort hash is
`0bc2068a79d7bde0dcfcc7938f2f186d1efac4fb9086ac986df3cb5b5af012cc`.
Platform-reported winners were:

| Market ending | Winner | Latest observed reference prices | Direction consistent |
|---|---|---|---:|
| September 15 | Down | Up 0.001 / Down 0.999 | yes |
| September 18 | Up | Up 0.999 / Down 0.001 | yes |
| September 20 | Down | Up 0.014 / Down 0.986 | yes |
| September 22 | Up | Up 0.755 / Down 0.245 | yes |

The last observed book direction agreed with the eventual platform winner in
all four markets. This is expected descriptive market behavior, not a signal
accuracy result: the observations were late-phase books and were not generated
from QCRL decisions. September 22 also demonstrates that an aligned direction
does not imply a near-terminal price.

This layer verifies Polymarket's reported payout state and joins it to prior
public evidence. Independent public Binance candle comparison is now a separate
contract documented in [BINANCE_RESOLUTION.md](BINANCE_RESOLUTION.md). Neither
layer proves a trade fill, wallet credit or redemption, or profit.
