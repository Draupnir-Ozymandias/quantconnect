# Receive-path EC2 smoke — October 7, 2026

The operator authorized bounded EC2 smokes. Only the inactive, clean public
observer checkouts in Ohio and Ireland were fast-forwarded to pinned source
`3c10c83664f45205419b5d0955391e7a47f544bb`. Daily `/opt/qcrl`, observer environment
files, pilot declarations, permanent service units, resource settings and timers
were not changed. No credentials, orders, jurisdiction workaround, infrastructure
change or QuantConnect synchronization was involved.

Both Python 3.9.25 observers ran 462 tests successfully with one explicit
platform-specific skip; real websockets 15.0.1 tests ran. The first Ohio test
invocation incorrectly supplied unittest's explicit top-level option, breaking a
sibling fixture import. The established checkout-local discovery command passed;
no source fix or suppressed test was needed.

## Finite public captures

Each transient unit used User/Group qcrl, 512 MiB memory, 75% of one CPU,
32 tasks, no new privileges, private tmp, protected system/home, and only
`/var/lib/qcrl-stream` writable. Capture duration was 35 seconds, with a
120-second total process safety limit including discovery and verification.
Restart/replay was not enabled. Both units exited successfully.

Both discovered BTC market `5375327`, slug `btc-updown-5m-1791382800`.
These independently started partial-lifecycle smokes are NOT a prospectively
locked cross-site timing comparison or complete market captures.

| Observed result | Ohio | Ireland |
| --- | --- | --- |
| Unit start UTC | 14:21:23 | 14:21:41 |
| Unit completion UTC | 14:22:12 | 14:22:24 |
| Retained raw messages | 22,457 | 21,412 |
| Connections / gaps | 1 / 0 | 1 / 0 |
| Text PONG replies | 3 | 3 |
| Initial books | Both tokens | Both tokens |
| Available / timing-eligible delivery records | 22,457 / 22,457 | 21,412 / 21,412 |
| Unavailable telemetry | 0 | 0 |
| Compressed stream bytes | 10,345,614 | 9,930,292 |
| Uncompressed stream bytes | 77,136,421 | 73,713,400 |
| Whole-unit CPU time, including offline verification | 17.548 s | 15.735 s |
| Maximum sampled process RSS during capture | 30,089,216 B | 29,691,904 B |
| Sampled cgroup throttled-time increment | 312,011 µs | 93,067 µs |

RSS is a sampled process metric, not peak cgroup memory. CPU totals include
verification and cannot be interpreted as instrumentation-only overhead. The
old socket-named timestamp remains after adapter work; it must not be substituted
for the new bracketed application-delivery boundary.

The local callback-to-delivery upper bound had p50/p99/max of
1.664/12.618/31.641 ms in Ohio and 1.406/10.453/33.037 ms in Ireland. These
include library assembly, local queueing, reader scheduling and observer work:
they are not pure queue wait, wire latency or a regional advantage estimate.
Reader time outside recv had p99 2.870/2.769 ms and max 25.236/27.587 ms.

Maximum sampled library frame queue depths were 40 and 41, despite configured
high-water mark 16. The high-water mark initiates flow control; it is not a strict
frame/message cap, and one parsed network read can contain a burst. Corresponding
pending-marker depths reached 40 and 41. Backpressure was sampled true at 6,559
and 5,872 deliveries. These are point samples, not event-level causal proof.

## Capped Linux localhost burst diagnostic

After the Ohio public capture completed, one finite benchmark ran under the same
CPU/memory/task caps, using three alternating rounds, 300 messages per batch and
two sizes. All 3,600 raw messages remained unchanged; all emitted metadata
validated. However, each 543-byte instrumented burst retained timing markers for
only 25 of 300 messages before `pending_marker_budget` disabled attribution for
the remainder of that connection. All three 2,079-byte instrumented batches
retained timing for all 300 messages. Thus only 975/1,800 instrumented messages
had timing coverage overall. Process success is NOT full-telemetry success.

Median observed/bare batch ratios were 3.27x and 5.10x. The small-message ratio
mixes active and disabled telemetry and is not a full-observer overhead estimate.
Neither ratio measures whole-recorder cost or network latency. Retain the fixed
64-marker policy: do not silently raise it or reconnect merely because attribution
is unavailable. This finding limits readiness for a larger capture.

Loopback report hash:
`0c42a81f8ab42695deee0d192d64e516399b0063496f387d69141050e11d9b1e`.

## Preservation and independent verification

Evidence and report were uploaded with AES256 to each observer's own bucket:

- Ohio: `runtime/streams/receive-smoke-ohio-20261007-a/` in
  `qcrl-collector-artifactbucket-icipysa9venc`.
- Ireland: `runtime/streams/receive-smoke-ireland-20261007-a/` in
  `qcrl-ireland-observer-artifactbucket-y5psgiphmqe1`.

Each originating S3 prefix was downloaded into a fresh remote directory; both
source files and those downloaded object bytes were retrieved over strictly
verified SSH into fresh ignored local review directory
`.qcrl/reviews/receive-ec2-smokes-20261007-8tUcuW/`. All 49 files matched exactly
(26 Ohio, including loopback, and 23 Ireland). Original evidence was retained.
Local verification independently checked the raw bundle, exact regenerated
stream specification, source declaration, report hashes, segmented bytes/chains,
footer, delivery bindings and counts. No evidence-inventory promotion occurred.

Ohio smoke report:
`e26ae2399452c4ee42f6603273b1f1c2266a4e856dd59855ca7368191b405197`.
Ireland smoke report:
`96c1201c10606602a469fa8eba44b294fa3b9cb5c34e001929cd8d70e5f7e24a`.
Local independently generated audit:
`192273180ff812e5813f700660769314c1214fc9a6353ae3c2b44b0265d0dd40`.

Ohio daily timer remained active, with daily checkout still at
`da280f59684dd4bc80e314b31e23154d620de721`. Ireland's original automatic-stop
timer remained active for October 8 at 20:17:44 UTC. Nothing was restarted,
replayed, deleted or promoted, and no further captures were scheduled.

## Next decision

Live smoke mechanics passed on both Linux observers; full burst attribution did
not. Before a larger synchronized cohort, reproduce bounded marker overflow in
a deterministic recorder-level burst test and assess the cost/coverage tradeoff
under unchanged limits. Any revised observation policy must be separately
versioned and validated; do not turn unavailable measurements into estimates or
claim that more CPU, memory or a larger queue has been proven necessary.
