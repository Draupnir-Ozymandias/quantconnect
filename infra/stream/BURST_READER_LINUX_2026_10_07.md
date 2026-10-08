# Separate-quota localhost burst comparison — October 7, 2026

This is a finite synthetic mechanics diagnostic, never public collection,
trading, execution/fill evidence, inventory promotion or QuantConnect sync.
The operator approved temporary-space housekeeping followed by the longer
producer-quota-isolated comparison. Existing public observer/daily policies,
timers, CPU/memory limits and environments are unchanged.

## Recoverable temporary-space housekeeping

Four explicitly inventoried old transfer-copy directories were moved from
the nearly full 921 MiB `/tmp` tmpfs to
`/var/lib/qcrl-stream/retained-review-transfers-20261007-2MJvh0/`.
No evidence was discarded. Every regular file's SHA-256 was checked before
and after the move; relative-path-sorted inventory hashes matched:

| Preserved directory | Inventory SHA-256 |
| --- | --- |
| `qcrl-freshness-cohort-audit-jXRCdQ` | `273ccd1a5c413eab25ba9bddc0aebdeb9e92d30bc2b728c3c8c6bf0651895ac1` |
| `qcrl-receive-cohort-review-q0EEIW` | `c403dccdbba2ba04a7241b768470e7a362728d8f878c1ea98f238a5fefbc7f62` |
| `qcrl-s3-review-1pkmlb3f` | `ac6b49e65f1787a8dfdd1325904f8ec8026e1633ef47f3f8a46f64b743a8d236` |
| `qcrl-s3-repeat-review-qlxlneag` | `37145095c021b196cf0219f589999168ae608b3e4d6c98fcf3eba3d9165e2e75` |

`/tmp` then had 921 MiB free; the real data volume had 15 GiB free.
Original collector evidence and prior local reviews were untouched.

## Initial fixture failure is retained, not a completed comparison

Source `3b83cfe` declared the v1 workload. Two cases completed: bare and receive,
each 30,000 messages. The first full-recorder case retained 28,840 frames,
then correctly triggered `pong_timeout` about 30 seconds after connection.
The synthetic fixture omitted PONG and incorrectly assumed the timeout started
at first PING. The producer failed when the recorder closed its socket;
the consumer's subsequent reconnect failed because the producer had terminated.
This is a fixture/protocol failure, NOT evidence of OOM or EC2 capacity failure.
The finite launcher stopped rather than retrying or claiming nine complete cases.

V1 artifacts, sealed partial segments, manifest and failed unit journals/properties
remain at `/var/lib/qcrl-stream/reader-burst-20261007-Wvi5yJ/`.
Its partial recorder lacks a finalized session and complete producer/delivery
artifacts; do not promote it to a verified full stream or a three-mode ranking.
V1 receive observations included unknown receive-v2 markers during bursts;
unknown telemetry is not evidence of changed or missing raw message bodies.

## Corrected prospectively versioned fixture

Source `4dd60ba` declares policy `qcrl.burst_reader_policy.v2`, documented in
[the burst protocol](../../docs/BURST_READER_COMPARISON.md).
It schedules identical synthetic PONG control frames in all three modes, one
at the end of each five-second cycle, replacing six of the 30,000 messages.
Controls are not genuine network acknowledgments. No public collector or
watchdog code changed. The v2 declaration and output directory are fresh;
v1 was not overwritten, resumed or silently reclassified.

All 507 tests passed locally. Linux's corrected-fixture suite passed all 507
with one expected Python-version inventory skip in 34.944 seconds; its finite
75%-CPU / 512 MiB / 32-task test unit ran 35.348 seconds and used 23.910 CPU-seconds.
Comparison producer/consumer groups have separate 100% / 75%-of-one-CPU quotas,
each 512 MiB / 32 tasks / 120-second maximum. Physical cores and host resources
remain shared. Quota configuration and process/cgroup identities must be checked
from retained unit properties, not inferred solely from distinct process IDs.

V2 evidence root:
`/var/lib/qcrl-stream/reader-burst-20261007-v2-Wvi5yJ/`.
Local ignored review root: `.qcrl/reviews/burst-reader-20261007-Wvi5yJ/`.

## Independent verification and results

All nine v2 cases completed at their declared frame bound. No automatic retries,
OOM, storage-bound or recorder reconnect occurred in the completed v2 cases.
All 157 originating files matched the Ohio SHA-256 inventory and exact file set
after direct SSH streaming/extraction. No intermediate EC2 package was
made. All 270,000 retained raw bodies matched their producer hashes and ordered
probe identities (six scheduled PONG positions per case checked separately).
All 90,000 full-recorder frames additionally matched the verified sealed archives.
Deadline schedules, per-phase attained rates, delivery timing statistics,
separate process/boot/cgroup identities and actual 100%/75% CPU, 512 MiB, 32-task,
120-second unit configurations and successful exits were independently checked.

Plan hash:
`b44e0172899975bde70e4b08fe77d36f307b996155e4a74b53cd70d4bd0e5cad`.
Independent audit hash:
`28db5997ea62e107ef14c3b55b2a37f4acfd90161e9a2c597ba8c55fe15d110a`.
Audit schema `qcrl.burst_reader_independent_audit.v1`; its v2 source declaration,
raw producer/delivery artifacts, unit properties, journals and local audit script
remain retained. Evidence is diagnostic and was not uploaded/promoted as live S3
market evidence. Hashes do not constitute origin signatures.

Timing is producer-application-begin to application-delivery upper bound,
including serialization/send, NOT wire latency. Values are the median of three
individual run p99s, not pooled independent message trials:

| Workload phase | Bare reader | Receive instrumentation | Full recorder |
| --- | ---: | ---: | ---: |
| 500 target messages/sec | 0.725 ms | 0.785 ms | 493.179 ms |
| 3,000 target messages/sec | 0.813 ms | 36.327 ms | 522.246 ms |
| Largest delivery upper bound, all runs | 8.755 ms | 61.803 ms | 578.469 ms |
| Median measured consumer-process CPU / 30-sec case | 4.129 sec | 9.143 sec | 15.111 sec |
| Largest sampled queue depth | 30 | 90 | 91 |

All nine producers attained approximately 999.98 messages/sec over the mixed
schedule; the slowest individual burst attained 2,999.967 messages/sec. Largest
deadline lateness was 8.956/14.890/13.477 ms for bare/receive/recorder; largest
send calls were 4.703/5.494/8.692 ms. These measurements constrain pacing claims,
not claims about real exchange emission or network buffering. The 500-rate
phase statistic includes residual backlog after the previous burst: it is NOT
a standalone steady 500-rate experiment or a per-message overhead estimate.
Process CPU excludes post-loop raw publication/verification but includes client
handshake/close and background receive threads. Shared host competition remains.

## Callback coverage is incomplete, raw integrity is not

No application-delivery timestamp was missing. Receive-v2 marker observations
were unknown for 42,849/90,000 receive-mode messages (47.61%) and 83,369/90,000
recorder-mode messages (92.63%). The bounded marker policy must not invent
callback timings after saturation. Queue sampling is per delivered message,
not continuous queue-duration coverage. These are instrumentation-coverage
limits, not missing raw messages or proof of data loss. The producer-to-delivery
measurements above do not depend on missing callback markers.

Interpretation: this longer burst workload demonstrates substantial recorder
tail/backlog cost relative to the two lighter modes under unchanged consumer
quota. It still did NOT reproduce the live five-to-twelve-second age problem;
the maximum observed upper bound was about 0.58 seconds. No particular recorder
stage, upstream fault or resource upgrade is causally established. Source samples,
synthetic controls, one reader, shared host and fixed limited burst shape bound
the conclusion. No resources were upgraded or new public markets collected.

The follow-up offline coverage audit confirms EVERY unknown record's reason was
`pending_marker_budget`. All three recorder cases exhausted the bounded prefix
during the first burst, around synthetic elapsed 4.44–4.49 seconds; none regained
known callback markers later in that connection. Receive-mode exhaustion occurred
in the first burst for one run and the fifth burst for two runs, also without
later recovery. Thus unknown counts include long periods after transient overflow,
not just messages delivered while a queue is deep. This is the deliberate v2
fail-closed behavior, not a safe reason to fabricate timestamps or force reconnect.

Coverage/partial-fixture audit hash:
`d08a33847275137118f05287586f5deca3cdf5e5fcaacf6d8dd873125ce500e0`.
It also independently matched all 51 retained v1 source files and checked the
partial recorder's ten sealed segment links, 28,865 row hashes and contiguous
28,840 probe-frame prefix. The manifest explicitly lacks session end; the sole
recorded gap reason is `pong_timeout`. This remains an incomplete fixture run,
not a finalized stream or evidence of complete producer delivery.

## Postflight and next step

Ohio public observer remained inactive and clean at `4dd60ba`; daily source
remained `da280f59684dd4bc80e314b31e23154d620de721`, with its timer active.
Observer environment SHA-256 remained
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Temporary space remained 921 MiB free, real data volume about 14 GiB free.
Completed v2 evidence occupies about 667 MiB. Both completed v2 and failed v1
roots are preserved locally and on the data volume; no public configuration,
daily timer or Ireland instance was changed.

Next high-value work: a versioned, bounded receive-marker correlation/recovery
contract that regains known measurements only at a provable alignment boundary,
then separately declared recorder-stage controls for encoding/hashing, freshness
bookkeeping and storage. Keep raw preservation and explicit unknown coverage,
avoid silently raising the marker budget or stripping safeguards, and do not infer
a node upgrade from the aggregate comparison. No further benchmark or telemetry
policy change was launched by this record.
