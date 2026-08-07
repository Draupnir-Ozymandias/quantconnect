# QuantConnect Research Laboratory

QCRL is a research platform for testing whether signal, filter, and capital-management behavior remains stable across experiments. It is not a live trading bot.

The current clean methodological baseline is **QCRL 2.2.0**. See [QCRL_SYNC.md](QCRL_SYNC.md) for the current engine/discovery boundary and research roadmap.

## Source-of-truth workflow

The local Git checkout is the source of truth. QuantConnect Cloud is the remote compilation, data, backtesting, optimization, and ObjectStore environment.

```text
local branch -> tests -> commit -> QuantConnect push/backtest -> canonical report
```

Do not edit the same files locally and in the QuantConnect web IDE at the same time. Commit local work before synchronizing in either direction.

## Synchronization

Use the guarded synchronization script from the project directory:

```bash
./synch.sh status
./synch.sh test
./synch.sh pull
./synch.sh push
./synch.sh backtest
```

- `status` is the default and makes no changes.
- `pull` requires a clean tree and creates a recovery branch before contacting QuantConnect.
- `push` requires a clean tree and interactive confirmation because local files replace their cloud counterparts.
- `backtest` does not implicitly push local changes.
- `backtest` injects the current Git commit, branch, and optional
  `QCRL_CAMPAIGN_ID` into the experiment record.

Run `./synch.sh help` for the complete command summary.

## Local tests

The platform-independent model and persistence tests do not require QuantConnect or Docker:

```bash
./synch.sh test
```

Cloud compilation and the clean BTCUSD control matrix remain the integration-validation layer.

QCRL tracks performance in its own simulated bankroll and intentionally submits
no portfolio orders. LEAN's standard portfolio statistics are therefore not
valid optimization objectives for this project. The next development layer is
a QCRL-aware campaign runner that evaluates canonical report metrics across an
arbitrary parameter search space.
