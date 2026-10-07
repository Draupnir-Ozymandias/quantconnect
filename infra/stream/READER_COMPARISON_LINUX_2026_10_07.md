# Paced three-mode Linux reader comparison — October 7, 2026

The operator authorized the finite localhost comparison after the offline
backpressure audit. The runner/protocol/tests were committed and pushed as
`b09a13655e87e1873a4ceae823e3f13de098ac61`. Only the idle Ohio observer checkout
was fast-forwarded. No public capture, old-plan replay, account endpoint,
credential, trading, resource/IAM/infrastructure change or QuantConnect sync ran.

## Protocol and verification

See [the fixed v1 protocol](../../docs/PACED_READER_COMPARISON.md). The frozen
corpus contains the first both-token book message and first 64 selected updates
from the earlier verified 4:35 p.m. market, with synthetic probe timestamps and
sequence identities. It is a small workload sample, not live emission evidence.
Target rates were 100/500/1,000 messages per second for two seconds each, with
three rotating-order rounds and bare/receive/full-recorder modes: 27 cases.

Local tests: all 504 passed. Linux Python 3.9.25 / websockets 15.0.1: all 504
passed in 32.706 seconds with one expected Python-version inventory skip. The
Linux test unit consumed 22.320 CPU-seconds and ran 33.139 seconds.

Both Linux units used qcrl user/group, 512 MiB, 75% of one CPU, 32 tasks,
protected system/home, private tmp and no new privileges. Tests had a 120-second
runtime cap; the comparison had 240 seconds and the existing writable observer
evidence namespace. The comparison finished successfully in 68.437 seconds,
using 26.988 CPU-seconds, with no automatic retry or recurring timer. Producer
and consumer shared the same process/cgroup. The bare mode also sampled delivery
clock/queue; CPU measurements include handshake/close and shared-process work.

All 28,800 messages passed the runner's exact sent/received sequence checks.
The Linux artifacts were retrieved and locally checked for declaration/corpus,
source-file and case/producer/delivery hashes, complete case coverage, timing
recomputation and recorder integrity. All 9,600 full-recorder raw messages were
independently checked from sealed archives, including sequence/probe identities.
Bare/receive raw bodies were not independently persisted; their raw equality was
checked in-run and hash-bound in the case reports. Keep that verification-scope
distinction visible. No receive marker or application-delivery stamp was missing.

## Results

Values below are the median of three individual run p99 values, in milliseconds,
for producer-application-begin to application-delivery upper bounds. They include
serialization/send work and are not wire latency or isolated consumer overhead.

| Target messages/second | Bare reader | Receive instrumentation | Full recorder |
| --- | ---: | ---: | ---: |
| 100 | 0.779 | 0.839 | 1.011 |
| 500 | 0.621 | 1.036 | 1.861 |
| 1,000 | 0.547 | 0.710 | 17.557 |

Producer rates were near target in all cases; one full-recorder 1,000-target
round attained 990.029 messages/second rather than 1,000. All lateness and
send-call measurements remain retained. Median whole-process measured CPU time
for the two-second 1,000-target cases was 0.550 / 0.928 / 1.536 seconds for
bare/receive/recorder respectively. Maximum sampled queue depths at that rate
were 9 / 13 / 26. No marker saturation occurred. The largest observed delivery
upper bound was 47.697 ms in a bare run; full-recorder maximum was 33.098 ms.
Do not confuse median p99 comparisons with a claim that recorder latency was
larger for every message or that mode ratios are calibrated causal CPU costs.

Interpretation: the full recorder adds measurable work and, at the high paced
rate, additional queue/tail delay. This two-second corpus did NOT reproduce the
five-to-twelve-second live timestamp-age problem. Producer pacing, shared CPU,
small corpus selection, no simultaneous market readers, localhost transport and
short duration limit attribution. Local macOS results are retained separately,
not pooled or substituted for capped Linux findings.

## Evidence and operational state

Linux source artifacts remain under
`/var/lib/qcrl-stream/reader-comparison-linux-20261007-vDV2YH/result/`.
Local diagnostics and independent audit are retained in ignored
`.qcrl/reviews/reader-comparison-20261007-vDV2YH/`.
Linux comparison hash:
`a4ac051601dc7e2be531596ed52573a0d998926f4422ac5250e4feb796a294f0`.
Independent local audit hash:
`ea9caf6922e2e120d4c08756f708483b1e22fb98051c53edef4fc0a0b10bd460`.

Packaging into `/tmp` failed after the successful comparison: the 921 MiB tmpfs
was full, while the real data volume had 16 GiB free. The complete archive was
then streamed directly over strict SSH and verified locally. No result was
deleted or rerun. Only this comparison's incomplete 1,978,368-byte package was
recoverably moved to its existing evidence directory as
`retained-partial-package.tar`; its SHA-256 remained
`9349fe408c83cc7463cbaf1f60130d39663254bb3dca3423f98060346a0cd190`.
The partial package is not complete evidence. Prior temporary review copies
remain untouched. `/tmp` still had only about 1.9 MiB free: explicitly review
and preserve/relocate completed transfer copies before more diagnostic runs.
This is temporary-filesystem housekeeping, not evidence that EBS needs expansion.

Postflight found observer checkout clean at `b09a136`, daily source unchanged
at `da280f59684dd4bc80e314b31e23154d620de721`, daily timer active, and observer
inactive after its prior successful cohort. Observer environment SHA-256 stayed
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.

## Recommended next step

After temporary-file housekeeping, declare a longer burst-shaped localhost
control with producer CPU isolated from the consumer's unchanged quota. Measure
attained pacing and send blocking again, and isolate recorder encoding/hashing,
freshness bookkeeping and storage stages before proposing code/resource changes.
Use archived arrival patterns only as synthetic workload shapes, not as known
exchange emission histories. No such follow-up is launched by this record.
