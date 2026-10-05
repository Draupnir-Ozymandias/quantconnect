# Offline Binance calendar source adapter

Implemented 2026-10-04 for the separately declared aligned research lane.
This is a source adapter, not a signal generator, backtest, or trading runner.

`execution_truth/binance_source.py` accepts the verified lane declaration and a
hashed boundary-candle dataset. It produces close-to-close source records only
for adjacent local calendar dates with both exact noon candles present. It does
not consolidate ordinary daily OHLC or consume the frozen Coinbase source schema.

## Dataset contract

`qcrl.binance_boundary_dataset.v1` has these required fields:

- `declaration_sha256`: hash returned by the research-lane verifier
- `evidence_role`: `historical_retrieval` (the only supported role in v1)
- `evidence_class`: `synthetic_fixture` or `captured_public_observation`
- `first_boundary_local_date` / `last_boundary_local_date`: inclusive,
  canonical YYYY-MM-DD dates, spanning 2–10,000 boundary dates
- `observations`: calendar-ordered list; each entry has `boundary_local_date`
  and `observation`
- `dataset_sha256`: canonical payload hash of the entire dataset without this field

Each observation retains the existing public Binance evidence shape:
`endpoint`, `params`, `observed_at_utc`, `payload`, and `payload_sha256`.
The locked endpoint is `https://data-api.binance.vision/api/v3/klines`.
Parameters must request BTCUSDT/1m, limit 1, startTime equal to that local
noon's UTC millisecond timestamp, and endTime equal to startTime + 59,999.
The payload must contain exactly one kline with those opening/closing times.
Close must be finite and positive. `payload_sha256` hashes the raw payload.

The adapter verifies both payload and dataset hashes. This proves internal
integrity, not that a user-supplied provenance label is authentic. Synthetic
input classification remains explicit in the audit.

## Availability and gaps

Observation timestamps must be timezone-qualified and no earlier than the
candle's exclusive end (noon + 60 seconds). Each record's observed availability
is the later of its two actual retrieval timestamps. It is never rewritten to
noon or candle completion. `original_boundary_availability_proven` is always
false: a later REST retrieval does not establish what was observable then.

Missing dates, including range edges and an entirely empty observation list,
remain explicit audit data. The audit marks `complete=false` and lists affected
source pairs. It may still retain independently complete adjacent pairs, but
never produces a record spanning a gap. A downstream signal consumer must not
treat separated runs as contiguous history or skip a missing candle as a tie.

Equal closes produce a `tie` source direction and `Split` market-comparison
outcome. The source adapter does not discard ties. Signal-history skipping is
a separate future consumer operation under the declared policy. It does not
change the 50/50 settlement rule or establish a payout for a hypothetical order.

Local calendar noons use `America/New_York`; UTC offsets and elapsed durations
are derived independently for each date. Tests cover ordinary 24-hour days,
23/25-hour DST windows, and winter 17:00 UTC noons. These records do not assert
that a corresponding market exists or bypass existing fixed-duration binding.

## Outputs and command

`qcrl.binance_calendar_source_audit.v1` pins the declaration and raw dataset
hashes, records coverage, retains normalized boundary candles and their raw
observation hashes, and lists source records and unavailable pairs.
Each `qcrl.binance_calendar_source_record.v1` pins the same inputs plus both
boundary-observation hashes, explicit interval/duration, closes, direction,
completion, and observed-availability time. Audit and records are hashed.

```bash
./synch.sh evidence research-source \
  execution_truth/specs/binance_noon_eastern_research_lane.json \
  /absolute/path/to/boundary-dataset.json
```

Output is JSON on stdout. No acquisition, automatic persistence, collector
change, signal emission, market binding, optimization, or orders occur.
The tests exercise this interface using explicitly synthetic datasets.

## Next gate

The auditable offline assembly path from retained public Binance evidence is
implemented; see `RETAINED_BINANCE_DATASET.md`. It preserves source-artifact
provenance and exposes the sparse coverage. Next is a separately versioned
delayed-decision signal contract. Do not launch a historical or prospective
campaign merely because source normalization passes. Evaluation windows and
acceptance gates remain unset; Coinbase results and locked QCRL declarations
remain unchanged. Unknown execution fields and metadata revalidation remain
independent restrictions on any later execution path.
