# Retained Binance boundary dataset assembly

Date: 2026-10-05. Scope: offline source-data verification, not signal evaluation.

`execution_truth/binance_dataset.py` assembles the five retained Binance
resolution-candle artifacts declared in
`execution_truth/specs/binance_boundary_assembly_retained_20260914_20260930.json`.
The declaration pins the aligned research lane, each source file's byte hash,
market identity, and the inclusive calendar range. Assembly also verifies every
source's artifact and payload hashes using the existing resolution normalizer.

Every selected boundary must be noon in `America/New_York`. The resulting
dataset retains raw observations, original retrieval times, a source manifest,
and references connecting each candle to its source artifact, file hash,
observation key, and observation hash. Shared dates with identical payloads
retain all references and use the latest recorded retrieval conservatively.
Different payloads at the same boundary reject assembly; no revision is chosen.
Repeated identical source artifacts also reject.

The original raw evidence and inventory are not modified. Output is derived,
content-addressed local state, with a nested dataset and calendar-source audit.

## Observed coverage

The September 14–30 range contains 17 expected local-noon boundaries:

- 10 observed boundaries from five source artifacts
- 7 missing dates: September 16, 23, 24, 25, 26, 27, and 28
- 7 independently complete adjacent source intervals
- 9 unavailable adjacent pairs; no interval spans a missing date
- Source directions: 5 up, 2 down, 0 ties

Seven intervals exceed the five original resolution checks because some
independently retained boundaries also form neighboring calendar pairs. These
are valid source comparisons, not newly observed Polymarket settlements.
Direction counts are **not signal wins, success rates, or strategy performance**.
The dataset is incomplete and unsuitable for continuous candle-streak history.
Later retrieval timestamps do not prove original-time availability.

## Reproduction

```bash
./synch.sh evidence research-dataset \
  execution_truth/specs/binance_boundary_assembly_retained_20260914_20260930.json \
  --output-directory .qcrl/execution_truth/datasets
```

Without the output option, the command prints JSON and writes nothing.
With it, an identical existing artifact is reused, and conflicting content is
never overwritten. No network calls or collector changes occur.

Current assembly hash:
`50149fcd0881cbad6f0e373b7737a2420b9e9c4f87f16024e779bb58b07dc600`.

## Next gate

The retained sample exercises provenance and gaps but cannot establish the
length-2 strategy's aligned-lane performance. Next, define and test a separate
delayed-decision signal contract on synthetic contiguous history before
declaring broader acquisition or evaluation. Never bridge these gaps or borrow
Coinbase observations to fill them. Evaluation windows, acceptance gates, and
unknown execution semantics remain unchanged.
