# Profiling observer deployment — October 6, 2026

Observer checkout `/opt/qcrl-stream`, EC2 `i-039c11d5ea49cf413`, us-east-2,
was clean/inactive before deployment and is pinned to pushed code commit
`15917731ed96222f2d0575db51bc1f6fff29639b`.

The separate daily checkout remains
`da280f59684dd4bc80e314b31e23154d620de721`; `qcrl-collector.timer` remains active.
No CloudFormation, IAM, firewall, disk, instance-type, credential or QuantConnect
changes occurred. Previous pilot/evidence and the old observer environment were
preserved by `--replace-plan`. The service is finite and does not restart/recur.

## Verification before launch

- Local suite: 396 tests pass, including 12 freshness and 8 profiling tests.
- EC2 Python 3.9 suite: 396 tests run, one version-specific test skipped,
  no failures.
- `git diff --check` passes. Reviewed code was committed and pushed before
  fetching/pinning it on EC2.
- Profiled public smoke under CPUQuota=75% and MemoryMax=512 MiB passed:
  23,520 frames, both token books, three PONGs, one connection, no recorded gaps.
- Five compressed segments and final manifest verified: 23,535 rows,
  4,587,630 compressed bytes and 35,347,176 uncompressed bytes.
- Eight profile samples; all 23,520 socket-return monotonic timestamps preceded
  or equaled their row recording timestamps. RSS and cgroup CPU counters were
  available, with no unavailable labels.
- RSS increased from 26,501,120 to 28,532,736 bytes during sampled operation;
  process CPU increased from 0.2 to 4.4 seconds. The sampled throttled-period
  counter stayed at 1 and throttled microseconds stayed at 5,375; the initial
  sample already included startup activity.
- Largest sampled append 13.23 ms, fsync 9.21 ms, seal 6.59 ms. These are smoke
  diagnostics only, not sustained-capacity or causal conclusions.

The smoke requested 35 seconds of collection; its row envelope spanned about
40 seconds and transient-unit runtime was 42.37 seconds, including close and
verification overhead. Recorder duration checks are not a hard real-time deadline.
It is a mid-market partial observation, not a completed lifecycle.

Retained local smoke:
`/var/lib/qcrl-stream/profile-smoke-1791294767/.qcrl/execution_truth/streams/smoke-1791294767/stream`.
Its isolated replication destination:
`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/ec2-smokes/profile-smoke-1791294767/`.
Upload command success does not itself prove byte-for-byte S3 identity.

## Prospective profiling cohort

Plan schema `qcrl.btc_5m_rolling_pilot.v3`, declared at
`2026-10-06T13:54:30.121581Z`, before all selected windows:

`503b3a19f5cca712d25b142c1c2f0f4f8f7eb52f45be1a195daee04ed952c97a`.

| Start epoch | Start UTC | Start Eastern |
| --- | --- | --- |
| 1791295200 | 14:00 | 10:00 a.m. |
| 1791295500 | 14:05 | 10:05 a.m. |
| 1791295800 | 14:10 | 10:10 a.m. |

Last market ends at 10:15 a.m. Eastern. Its end-plus-120-second checkpoint is
due around 10:17; verification and final replication take additional time.
The service was confirmed active/running with existing 75% CPU / 512 MiB bounds.
No completed cohort result is asserted in this deployment record.

Runtime prefix:
`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/pilot-503b3a19f5cca712d25b142c1c2f0f4f8f7eb52f45be1a195daee04ed952c97a/`.

Next review: verify retained manifests and S3 bytes; compare socket-return age
with row receipt age; correlate tails with timing windows, resource deltas and
service-wide CPU throttling. Do not attribute delays from aggregate CPU alone,
double-count shared counters, or treat a snapshot as recovery of missing events.
Multi-timeframe collection remains gated on this review.
