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

## QCRL campaigns

Campaign manifests are version-controlled JSON files under `campaigns/`. The
first manifest defines the eight-run BTCUSD 2022–2025 flat/martingale control
matrix.

```bash
./synch.sh campaign plan campaigns/btcusd_1d_baseline_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_baseline_2022_2025.json
./synch.sh campaign run campaigns/btcusd_1d_baseline_2022_2025.json --execute
./synch.sh campaign status campaigns/btcusd_1d_baseline_2022_2025.json
```

`run` is a dry run unless `--execute` is present. Executed campaigns require a
clean Git tree, run sequentially, and resume without repeating completed cases.
By default, submission start times are separated by at least 30 seconds. A
recognized QuantConnect rate limit is retried automatically after 30, 60, 120,
and 240 seconds; other compilation or runtime failures stop immediately. Use
`--limit 1` for an integration check and `--retry-failed` only after retries are
exhausted or an ordinary failure is corrected. Local state and logs live under
the ignored `.qcrl/` directory.

Campaigns can override the defaults without changing runner code:

```json
"submission_policy": {
  "min_interval_seconds": 30,
  "max_rate_retries": 4,
  "initial_backoff_seconds": 30,
  "max_backoff_seconds": 300
}
```

For a one-time override, use `--min-interval-seconds` or
`--max-rate-retries`. Rate-limit events, retry counts, and the policy used are
recorded in campaign state and per-attempt output is appended to the case log.

The algorithm publishes QCRL-native metrics as custom backtest summary
statistics. To retrieve them through the QuantConnect API, copy `.env.example`
to `.env`, enter the API credentials issued by QuantConnect, load them into the
shell, and collect the results:

```bash
set -a
source .env
set +a
./synch.sh campaign collect campaigns/btcusd_1d_baseline_2022_2025.json
./synch.sh campaign validate campaigns/btcusd_1d_baseline_2022_2025.json
```

Validation checks run completeness, native-objective availability, and the
flat/martingale signal-sequence invariants before producing a ranking.

Rankings are declared as separate cohorts in the campaign manifest. The clean
control campaign uses:

- `flat_profit_drawdown`: `net_profit / (1 + max_drawdown)`, with a ruin
  penalty. This measures signal economics without recovery-depth penalties.
- `martingale_recovery_risk`: the QCRL risk-adjusted score, which includes
  drawdown and recovery depth and applies the engine's ruin penalty.

Changing ranking, display, or submission configuration is accepted as an
analysis-only manifest revision when the deterministic case set is unchanged.
Changing any expanded parameter set requires a new `campaign_id`; existing run
state cannot silently migrate to different experiments.

When `pair_comparison` is present, validation also writes a structured artifact
to `.qcrl/campaigns/{campaign_id}/paired_comparison.json`. Each pair contains:

```text
signal invariants and supporting case IDs
flat and martingale outcomes
profit and drawdown deltas
drawdown amplification
maximum-wager multiple of the base wager
maximum recovery depth
descriptive capital-transform and risk-amplification labels
```

The labels are descriptive rather than recommendations. In particular,
`recovery-dependent-profit` means martingale produced a profit while the paired
flat signal was neutral or negative. This artifact is the input boundary for
the Stability Engine; it does not require another backtest or ObjectStore read.
