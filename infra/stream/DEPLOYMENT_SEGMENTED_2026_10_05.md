# Segmented observer deployment — 2026-10-05

Deployed source: `319e0a97a87498ef037302278fd9dfa967b8c569` in the separate
`/opt/qcrl-stream` checkout on `i-039c11d5ea49cf413`, region `us-east-2`.
No instance replacement, disk expansion, DNS/IP pinning, IAM change,
CloudFormation stack update, QuantConnect push or trading action occurred.
The daily timer remains active and its stream-prefix exclusions are preserved.

## Verification

- 376 local tests pass; all 43 promoted evidence artifacts verify.
- EC2 Python 3.9 suite: 376 tests run, one explicitly version-specific stdlib
  inventory check skipped, no failures.
- The 35-second smoke under 75% CPU / 512 MiB service limits passed: 22,724
  received frames, both outcome books, two PONGs, one connection and no gaps.
- Four compressed segments and a final manifest verified: 22,731 rows,
  31,124,483 uncompressed bytes versus 4,046,651 compressed bytes (about 87%
  reduction for this sample). Compression savings are not a guaranteed ratio.
- The smoke is a mid-market diagnostic, not a completed lifecycle. The full-window
  test remains the prospective pilot below. No continuous delivery claim is made.

## Prospective pilot

Declaration schema `qcrl.btc_5m_rolling_pilot.v2`, plan hash:
`b37b70155999535dc2bd37f16218da9d1cdf4fbddf5e3d46d91e0198c987aae3`.
Declared at 22:04:50 UTC, before all three market starts: 22:10, 22:15 and
22:20 UTC (6:10, 6:15 and 6:20 p.m. Eastern). The final trading window ends
at 6:25 p.m.; its actual end-plus-120-second checkpoint is due around 6:27.
Final health verification and replication can take additional time.

The observer service was confirmed active/running; previous environments and
all earlier failed cohorts are retained. New runtime objects use:

`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/pilot-b37b70155999535dc2bd37f16218da9d1cdf4fbddf5e3d46d91e0198c987aae3/`

This deployment fixes the earlier six-market cohort's structural failures:
segment rotation rather than single-file exhaustion, explicit total budgets
with reserved terminal-summary space, sealed-only S3 uploads, final/post-close
checkpoints after reader failures, and reread evidence-based cohort health.
An incomplete cohort or any replication failure now causes a nonzero service
exit rather than a misleading green completion. A pending settlement remains
pending, not a failed prediction or inferred final payout.

See [the capture contract](../../docs/SEGMENTED_STREAM_CAPTURE.md) for budgets,
integrity chains, failure semantics and the unpublished-tail durability tradeoff.
