# Capped Linux receive-path v2 checks — October 7, 2026

The operator authorized the bounded Linux v2 checks and one finite public smoke.
Only Ohio's idle, clean `/opt/qcrl-stream` checkout was fast-forwarded to
`8cb4fd05a30ec5ead0996c209c9b36735d9a50c5`. No existing capture declaration,
environment file, permanent service unit, daily source, schedule or resource cap
was changed. Dublin was not updated or used for another capture. No credentials,
orders, IAM/infrastructure change or QuantConnect synchronization was involved.

## Linux verification under unchanged limits

Three finite transient units used User/Group qcrl, 512 MiB memory, 75% of one CPU,
32 tasks, no new privileges, protected system/home and private tmp; only the
existing `/var/lib/qcrl-stream` namespace was writable. They were not enabled
as recurring services or restarted. Time limits were 120 seconds for tests,
90 seconds for offline/localhost diagnostics and 120 seconds for the public
smoke including discovery, close and verification.

- Capped Python 3.9.25 suite: 477 tests passed in 24.000 seconds, with one
  explicit platform-specific skip. Real websockets 15.0.1 tests ran. Whole-unit
  CPU time was 18.206 seconds.
- All 15 deterministic recorder/archive schedules verified. Of 1,208 delivered
  messages, 731 retained timing and 477 remained unknown; raw messages matched
  the archives exactly. This matches the local v2 outcome, not live coverage.
- The finite three-round Linux localhost diagnostic preserved all 3,600 raw
  messages and validated emitted metadata. Small 543-byte instrumented bursts
  retained timing for 123, 89 and 89 of 300 messages; remaining messages were
  unknown with `pending_marker_budget`. All three 2,079-byte instrumented bursts
  retained timing for all 300 messages. Thus 1,201/1,800 instrumented messages
  had timing, not full burst coverage. Median observed/bare batch ratios were
  6.11x/6.38x. The small-message ratio mixes active and unavailable telemetry.
  Different scheduling/workloads make these unsuitable as controlled v1/v2
  improvement estimates, calibrated CPU cost or recorder-overhead estimates.

Linux experiment hash:
`897e83a9577ed8a0454ad53832a039e7ee14e8004d4bfa88695f2bf6e136933f`.
Loopback report hash:
`12ffbf3d3918fd5b59175f90649174b0554de31952db7940d2e7e928d0edc756`.
The offline/localhost unit consumed 2.077 CPU-seconds and exited successfully.

## Single public smoke: verified evidence, failed connectivity acceptance

The smoke ran once on BTC market `5376966`, slug
`btc-updown-5m-1791385500`, whose trading window began 15:05 UTC. The transient
unit started at 15:06:11 UTC and exited with status 1 at 15:07:04 UTC. It retained
a complete sealed archive/report, not an exception or partial publication.

The declared capture budget was 35 seconds. First/last retained application
delivery timestamps were 15:06:12.703342 and 15:06:47.191080 UTC. The session
footer was recorded at 15:06:52.227799 UTC, after the bounded socket-close phase;
whole-unit runtime also includes discovery and offline archive verification.
This is a partial-lifecycle connectivity smoke, not a complete-market observation.

| Observed result | Ohio v2 |
| --- | --- |
| Retained raw messages | 27,419 |
| Connections / explicit gaps | 2 / 1 |
| Text PONG replies | 2 |
| Initial token books | Both tokens on both connections |
| Available / timing-eligible records | 27,419 / 27,419 |
| Unknown / saturated draining records | 0 / 0 |
| Sealed segments | 12 |
| Compressed / uncompressed stream bytes | 12,547,192 / 93,403,010 |
| Whole-unit CPU time, including verification | 21.012 s |
| Maximum sampled process RSS during capture | 29,904,896 B |
| Sampled cgroup throttled-time increment | 246,132 µs |
| Maximum sampled library queue / marker depth | 39 / 39 |
| Backpressure-true delivery samples | 12,723 |

The unchanged smoke acceptance requires exactly ONE connection. It failed that
criterion, although both books, two heartbeat replies and full telemetry were
present. `passed=false` and the failed unit status are preserved; no criterion
was relaxed and no rerun was made.

At 15:06:24.730712 UTC, connection 1 recorded
`ConnectionClosedError:rcvd_code=1013:sent_code=1013`. Connection 2 subscribed at
15:06:27.092158 UTC; its first book was recorded at 15:06:27.212429 UTC. Reset
records discarded zero markers/fragments and had no prior telemetry-disable
reason. The observed reconnect was a received public-stream close, not marker
overflow or a telemetry-driven restart. These records do NOT establish why
the remote endpoint closed, a geographical cause, or a v2-induced failure.

The callback-to-delivery upper bound had p50/p99/max
2.991/11.821/32.343 ms. Reader time outside recv had p99/max 2.871/26.515 ms.
These are local receipt/processing diagnostics, not wire latency, pure queue
wait, exchange timing or proof of cross-host accuracy. Sampled RSS is not peak
cgroup memory; CPU totals include verification. This run did not saturate v2,
so it cannot establish live drain-before-unknown performance under saturation.

## Preservation and independent checks

Both completed evidence groups were uploaded with AES256 to the Ohio bucket
`qcrl-collector-artifactbucket-icipysa9venc`, without deletion:

- `runtime/streams/receive-v2-linux-ohio-20261007-a/`
- `runtime/streams/receive-v2-smoke-ohio-20261007-a/`

Each prefix was freshly downloaded from its originating S3 objects into a
separate remote directory. Those bytes and the original source files were then
retrieved over strictly verified SSH into fresh ignored review directory
`.qcrl/reviews/receive-v2-linux-smoke-20261007-D1LsOd/`.
All 106 files matched exactly: 77 offline/localhost and 29 public-smoke files.
Local verification independently checked source-file hashes, declarations,
report hashes, every synthetic and public stream's specification, sealed
segment chains/bytes, footer, raw messages and receive-record integrity.
No evidence-inventory promotion occurred; failed evidence remains retained.

Public report hash:
`e0f7aec4ed187fd06e978f13b997a3638c8236748884e51f2d18a95cfb62741a`.
Independent local audit hash:
`baa6f0bf12d7a18a02fc7b99d8be3978f90d90d016a46ea84f4bb514d36123fa`.

Ohio daily source stayed at `da280f59684dd4bc80e314b31e23154d620de721` and its
timer remained active. Observer environment SHA-256 remained
`d5c9a6459ce8e1acc8f7ef7cee624f633a980c9d1d7542795d6e429ee27fb545`.
Dublin's original automatic-stop timer was independently confirmed active for
October 8 at 20:17:44 UTC. Disk still had 17 GiB available. No resource increase,
retry-to-pass loop, replay, reset of failure status or additional cohort followed.

## Recommended next step

Keep the connectivity smoke failed and the instrumentation/retention evidence
separate. Build a versioned offline receive-path phase/gap analyzer that can
handle stream v5, report normal/draining/unknown timing coverage and explicit
gaps, and preserve censoring/clock/resource limitations. Test it against the
v2 matrix and this recovered-1013 archive before proposing another small,
prospectively locked observer cohort. Do not substitute v5 timestamps into the
existing cross-site v1 analysis or buy resources on this single run's evidence.
