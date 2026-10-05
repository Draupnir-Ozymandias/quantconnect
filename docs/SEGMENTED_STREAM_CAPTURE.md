# Segmented public stream capture — 2026-10-05

This replaces the rolling observer's v2 single-file stream plan with opt-in
`qcrl.public_market_stream_spec.v3`. Archived NDJSON evidence is unchanged and
remains verifiable. Legacy single-file CLI mode is retained.

## Why

The six-market pilot `86fd6c8...` discovered every market before opening, but
all six exhausted a 128 MiB file limit after roughly 98,000 frames. All six
retained prefixes verified and matched their S3 copies byte-for-byte; none had
a closing footer or final/post-close checkpoints. The service nevertheless
reported success because it did not aggregate case failures.

## Storage and integrity

Each stream uses an exclusive directory. Rows keep the existing ordinal/hash
chain, raw text, local UTC/monotonic receipt time and explicit connection gaps.
At an 8 MiB uncompressed segment boundary, the recorder seals a level-1 gzip
file and publishes a hashed descriptor. Descriptors bind compressed-byte hashes,
row counts, uncompressed sizes, ordinal ranges, row-chain endpoints and the
previous segment descriptor. A final manifest binds the sealed set and footer
presence. Files are never overwritten or deleted.

Sealing uses `.partial` files followed by immutable `.gz` files and descriptors.
S3 replication excludes `.partial`; an active segment's newest tail remains
local until sealed. Shutdown seals a retained prefix even after exceptions.
Abrupt process/host loss can leave an unpublished partial segment. Verification
reports missing manifests/footers rather than treating a prefix as complete.
Transient S3 publication ordering can also produce incomplete directory copies;
only a verified final manifest and complete referenced segment set are final.

Budgets are explicit: 1,000,000 received frames, 1 GiB uncompressed rows,
256 MiB compressed data per market, 4 MiB encoded-record/footer reserve,
2 GiB cohort spool and 1 GiB minimum free disk. Two-worker compressed-budget
reserve is checked before each dispatch. Quota stops preserve a terminal partial
summary when possible and remain unhealthy. Rotation is not an unbounded log.

The previous 64-record/one-second fsync policy remains, with immediate sync for
control boundaries, sealed files/descriptors and the manifest. Power loss can
lose the last unsynced batch. No completeness or latency guarantee is inferred.
Decompression verification enforces per-row and per-segment size bounds.

## Failure-aware lifecycle and health

Rolling declarations use `qcrl.btc_5m_rolling_pilot.v2`. Daily signal
contracts, strategies, account access, network endpoints and disk provisioning
are not changed.

After initial market discovery succeeds, final public metadata is attempted
regardless of recorder success. A separate bounded wait reaches actual market
end plus 120 seconds before the post-close checkpoint. Failed GETs are retained
as failures; a returned pending settlement is not relabeled resolved. Missed or
undiscoverable markets remain explicitly missing rather than guessed/backfilled.

`health.json` counts only verified lifecycle-ended streams with manifests,
pre-open headers, end-plus-30-second footers, correct source/token mapping,
both book baselines on every connection and valid final/post-close artifacts.
Reconnections remain visible; lifecycle completion is not continuous delivery.
Any incomplete case or replication failure makes the service exit nonzero.
Recovered upload failures remain visible and require review, not a silent green.
Health aggregation rereads retained evidence instead of trusting summary labels.

## Interface

```bash
python qcrl_execution_truth.py market-stream CURRENT_RAW_BUNDLE.json --segmented
python qcrl_execution_truth.py market-stream CURRENT_RAW_BUNDLE.json --segmented \
  --execute --output .qcrl/execution_truth/streams/UNIQUE_DIRECTORY
python qcrl_execution_truth.py verify-stream .qcrl/execution_truth/streams/UNIQUE_DIRECTORY
```

The rolling service and smoke use segmented storage automatically. Legacy
NDJSON verification still accepts a file path. Replacing an inactive service
plan uses the installer's explicit `--replace-plan` and preserves its previous
environment; old cohorts are never replayed. The daily sync exclusions remain.

No disk expansion, IP pinning, TLS weakening, Polymarket credentials or trading
is part of this change. Prospective full-window validation on EC2 is still
required; local integrity tests alone do not establish feed reliability.
