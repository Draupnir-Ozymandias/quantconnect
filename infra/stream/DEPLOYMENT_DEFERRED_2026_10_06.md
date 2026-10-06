# Deferral-only profiling deployment — October 6, 2026

Observer `/opt/qcrl-stream` is pinned to pushed commit
`a25be8177ff4f6b8422e0f6182ec4d1cbea125f3`. Implementation is `d60d9e8`; the
subsequent commit isolates the synthetic worker-ordering test from host temporary
disk capacity. No production free-space guard was relaxed.

## Verification and retained abandoned declaration

Local full suite: 408 tests pass. EC2 Python 3.9: 408 tests run, one
version-specific test skipped, no failures after the test-only correction.
`git diff --check` passes.

The initial EC2 run exposed the ordering test's use of `/tmp`, a 921 MiB tmpfs,
against the production 1 GiB minimum-free-space guard. Actual observer storage
had 17 GiB free. The initially installed waiting plan
`a6600d0e86ef8b8759265b3e4bae40fd2d73c923a3b79d9bd6a26b26d70f9dc6`
was stopped before its first observation window and before creating any capture
directories. Its declaration/runtime prefix and environment were retained;
it was not replayed. A fresh future plan was installed only after confirming
the corrected full EC2 suite passed.

## Active replacement declaration

Schema: `qcrl.btc_5m_rolling_pilot.v4`.
Declared: `2026-10-06T18:36:20.779455Z`.
Plan hash:
`5b5d51b6697f09924a364ba76e6b26edb68301b2e0fa0b673929000b2a734a6d`.

| Start epoch | Start UTC | Start Eastern |
| --- | --- | --- |
| 1791312300 | 18:45 | 2:45 p.m. |
| 1791312600 | 18:50 | 2:50 p.m. |
| 1791312900 | 18:55 | 2:55 p.m. |

Final trading window ends at 3:00 p.m. Eastern; last end-plus-120-second
checkpoint is due about 3:02. Sequential deferred verification, health rereads
and final S3 replication take additional time. No completed result is asserted.

The service was confirmed active/running, with existing CPUQuota=75% and
MemoryMax=512 MiB. The daily timer remains active and `/opt/qcrl` remains
`da280f59684dd4bc80e314b31e23154d620de721`.

Runtime S3 prefix:
`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/pilot-5b5d51b6697f09924a364ba76e6b26edb68301b2e0fa0b673929000b2a734a6d/`.

Only verification scheduling changes in this prospective cohort. Profiling
remains active; fixed two-second reconnect pauses, three connection attempts,
source/terms review, two workers and all frame/byte/spool limits are unchanged.
The implemented watchdog/equal-jitter policy is **absent from this declaration**
and inactive. It will require a separate later prospective rollout after review.

No new wire smoke was needed for this orchestration-only intervention; the
previous profiled wire smoke remains the compatibility baseline. Synthetic
tests exercised successful/failed worker deferral, independent actual-boundary
checkpoints, immutable result links and controller ordering on both runtimes.
No instance, disk, budget, IAM, firewall, credential, QuantConnect, trading or
recurring-schedule changes occurred. Every previous evidence cohort is retained.

Next review: verify final artifacts and S3 bytes, then compare socket-return age,
reconnects and service-wide CPU throttling. Changed time-of-day/activity and
upstream behavior prevent attributing any before/after difference solely to
verification deferral. Multi-timeframe expansion remains gated on that review.
