# Versioned cross-site public-stream diagnostics

`execution_truth.stream_cross_site` emits `qcrl.stream_cross_site.v1` reports.
It is an **offline** comparison, not collection, trading, inventory promotion,
an execution simulator, or proof of one-way network latency.

```bash
python3 -m execution_truth.stream_cross_site \
  .qcrl/reviews/two-site-936cdd98/ohio \
  .qcrl/reviews/two-site-936cdd98/ireland \
  --output .qcrl/reviews/two-site-936cdd98/cross-site-v1.json
```

Output creation is exclusive: choose a new output path for another run. Source
artifacts are never changed. Downloaded directories must include the plan,
preflight, health, source bundles, checkpoints, results and finalized streams.
Independently compare S3 object bytes with the downloaded cache before reporting
replication success; this analyzer verifies evidence integrity, not S3 replication.

## Evidence and eligibility

The analyzer independently rechecks cohort health, immutable capture/final-result
links, raw-reclassified stream chains and manifests, source terms and identity,
and checkpoint evidence. Both sites must have identical locked plans, deployed
source, service units, resource settings and declared input-file hashes, with
distinct instance identities. Hashes provide integrity links, not signatures or
proof of an artifact's origin. A corrupt stream or mismatched source fails closed.

Incomplete lifecycle/checkpoint results remain incomplete in the report.
Missing finalized streams produce explicit ineligible comparisons; verified
finalized partial captures can still support descriptive timing analysis without
being promoted to completed lifecycles. Reports bind each source result, manifest,
final stream record, header specification and observer preflight, plus the analysis
policy and final report hash.

## Measurements and boundaries

- Receipt age uses the immediate socket UTC timestamp, not the later timestamp
  after classification/logging. Missing socket timestamps are rejected rather than
  silently substituted. Missing/invalid exchange timestamps remain counted.
- Exact-event fingerprints hash canonical selected-event JSON. Timing uses only
  payloads occurring **once in each entire stream**, with both receipts inside the
  intersection of selected-receipt ranges. Repeated payloads outside that overlap
  still disqualify a timing pair. Duplicate multiplicities are counted separately.
- Positive `left_minus_right_socket_receipt_seconds` means the right observer
  recorded the matching payload earlier. With Ohio left and Ireland right,
  positive means Ireland earlier. Negative values are retained.
- Unmatched occurrences do not prove message loss: initial snapshots, connection
  gaps, subscription timing and per-connection state can differ. No sequence number
  or ordered duplicate pairing is invented, and no books are merged.
- Per-site gaps, recovery to both book baselines, timestamp regressions, receipt-age
  tails and wall-minus-monotonic consistency remain visible. Chrony preflight
  evidence is retained; timestamps are not corrected. Cross-host clock accuracy
  and geographical causality remain unproven.
- Cgroup counters cover the whole service. Missing/reset counters are unknown,
  not zero. Do not sum overlapping market-window deltas. Event observations are
  correlated and are not independent market trials.

Memory is bounded by one pair of streams at a time, at most one million selected
events per stream, and ten thousand profiling samples; existing stream verifier
and freshness grouping budgets also apply. Quantiles use linear interpolation.
There is no profitability, fill, queue-position or uninterrupted-coverage verdict.

For changed analysis semantics, introduce a new schema/policy version and retain
prior reports. The collector revision can remain unchanged when only this offline
analyzer changes, which preserves the prospective experiment's runtime policy.

The existing socket-named fields measure application delivery after `recv()`,
not wire arrival. See the [receive-path contract](RECEIVE_PATH_TELEMETRY.md) for
the separate, not-yet-integrated measurement foundation; existing reports are
not rewritten or promoted to queue-wait or network-latency evidence.
