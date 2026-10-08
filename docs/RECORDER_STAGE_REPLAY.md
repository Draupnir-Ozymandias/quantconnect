# Recorder-stage replay, version 1

This is an offline component benchmark, not a collector, deployment, fill model,
or measurement of socket delay. It follows the matched receive-recovery cohort.
It accepts only sealed, independently verifiable stream-v7 archives whose receive
contract declares `localhost.burst`. No networking or credentials are used.

The fixed input for the first Linux run is the previously audited
`0-recorder-v3/stream` from `reader-burst-matched-20261008-GL20pl`: 30,000 frames,
30,024 total records, 108,626,309 uncompressed bytes. This is one retained timing
trajectory, not three independently emitted workloads. Three repetitions rotate
the five stages; input parsing, preparation, and output verification are outside
stage timers. Both process CPU and elapsed wall time are reported.

| Stage | Timed work | Verification outside timer |
| --- | --- | --- |
| encode_hash | Canonical row hash and ordinary JSON-line encoding; original digest/link checks | Encoded-byte count; hashes also checked during the loop |
| freshness | Actual `ConnectionFreshness.observe` and original scheduled snapshots, including equality checks | All original freshness snapshots must reproduce exactly |
| gzip_write | Pre-encoded rows, level-1 gzip, matching segment/flush cadence, file writes, no fsync | Decompressed bytes must equal every original encoded row |
| gzip_write_fsync | Same synthetic sink, with file fsync at each flush and seal | Same full byte comparison; fsync calls retained |
| durable_log | Unmodified `SegmentedStreamLog`: encoding, hashing, compression, quotas, fsync, sealing and manifests | Original row identities and complete archive verification must match |

The compression sinks deliberately have **no stream manifest** and are not valid
collector evidence. The durable stage does not include the socket, receive
instrumentation, classification, watchdog, profiling, or freshness processing.
Its replay clock parses retained UTC stamps and it checks each resulting row
digest; these are diagnostic overheads, not the original live clock cost.

The input has already been observed: page-cache warmth, source-specific freshness
states, callback known/unknown mix, and flush timing are held fixed. Components
are not additive or mutually exclusive. Do not subtract stage medians from the
full recorder's earlier CPU totals or infer wire/network latency from them.
In particular, unknown callbacks may reduce freshness work in this input.

The harness caps input at 192 MiB / 40,000 records / 32 segments, requires a fresh
output directory, binds all input files and execution-truth Python source files
by SHA-256, and checks that those bytes remain unchanged. Report completion is
published only after all stages and output checks pass. Failures preserve partial
outputs. Linux diagnostics use a separate frozen checkout and finite protected
systemd service; public checkouts, timer settings, and configuration remain unchanged.

```bash
python infra/stream/recorder_stage_replay.py VERIFIED_SYNTHETIC_STREAM FRESH_OUTPUT_DIRECTORY
```

Next, use this component evidence to choose a prospectively fixed, loopback-only
paired ablation. Retain the real recorder as the reference and never promote an
ablated sink as valid public capture evidence. No public optimization is justified
by this benchmark alone.
