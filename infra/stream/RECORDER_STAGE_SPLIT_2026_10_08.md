# Checkpointed recorder-stage costs — October 8, 2026

## Result

Version 2 completed and passed independent audit on Ohio. All 15 measurement
checkpoints and separate verification receipts are present. All **19 workers**
passed under the original **75% CPU / 512 MiB / 32 tasks / 120 seconds per worker**
limits. No deadline extension was used. Public collector code and settings stayed
unchanged; no public captures, credentials, trades, or QuantConnect sync occurred.

The measurement service finished in **56.368191 seconds**, using **37.762621 CPU
seconds** including preparation and checkpoint publication. Its 15 timed stages
accounted for 32.054708332 CPU seconds and 48.777172593 wall seconds in total.
Those totals describe sequential repeated benchmark operations, not the cost of
one end-to-end recorder run. Heavy stream verification occurred in separate
processes after measurement working data was released.

## Fixed source and protocol

See [Version 2 protocol](../../docs/RECORDER_STAGE_SPLIT.md). Version 1 and its
[incomplete Linux attempts](RECORDER_STAGE_REPLAY_2026_10_08.md) remain intact.

Frozen diagnostic source:
`1c0fd4660677031ffa6fb6971607592661ad5ad0`

Remote checkout:
`/var/lib/qcrl-stream/recorder-stage-split-20261008-b2ZO5P/source`

The input remains `0-recorder-v3/stream` from the already audited matched
localhost cohort: **30,000 frames / 30,024 records / 108,626,309 uncompressed
bytes**. It is one retained timing trajectory replayed unpaced, not three new
observations or a public-stream latency experiment. Three repetitions rotate
the five measurement stages. Component implementations are unchanged from
Version 1; Version 2 changes the diagnostic lifecycle and checkpoint durability.

Preparation validates the input with no retained measurement lists, binding its
exact files and implementation bytes. Measurement checks that binding, prepares
identical compressor inputs outside timers, and seals explicitly unverified
timing/output-hash checkpoints after each stage. Separate stage workers stream
the comparisons and validate each real durable archive. Finalization rechecks
all bindings and publishes a verified report only with all 15 receipts.

## Component measurements

Seconds per replay, median of three repetitions. CPU and wall medians are
computed independently. Wall ranges are retained because three repeats do not
justify a precise storage-latency claim.

| Stage | Median CPU | Median wall | Wall range |
| --- | ---: | ---: | ---: |
| Encoding/hashing | 2.811884 | 3.740586 | 3.685999–3.827378 |
| Freshness replay | 2.098330 | 2.772396 | 2.719909–3.039365 |
| Pre-encoded gzip/file writes, no fsync | 0.817558 | 1.128824 | 1.095228–2.620367 |
| Same synthetic sink with fsync | 0.848606 | 1.926382 | 1.924550–3.997775 |
| Real durable segmented writer | 4.034224 | 5.399541 | 5.386141–5.512732 |

Encoding/hashing is the largest **separated CPU component** measured here. This
supports testing an encoding optimization first, not calling it a proven cause
of live receive-age tails. Do not interpret its ratio to writer CPU as an exact
percentage of total production cost: these are overlapping diagnostic operations.

The two synthetic compression controls show similar CPU usage and different
median wall time with fsync. However, the no-fsync second round took 2.620367
seconds, longer than the corresponding fsync round's 1.924550 seconds. Shared
host scheduling, cache, memory pressure and filesystem variability were not
isolated. There is no justified precise per-fsync latency estimate or conclusion
that EBS, DNS, networking or hardware caused the public-stream gaps.

All stages replay the original clocks and data. The real writer includes replay
UTC parsing, row-digest comparison, encoding, hashing, compression, byte quotas,
fsync, sealing and manifests; it excludes socket/receive instrumentation,
classification, watchdogs, profiling and freshness processing. Freshness replay
also includes routing, transient state-constructor defaults at lookup, and
snapshot-equality checks. Its callback known/unknown mixture is inherited from
the source. It is not a pure production `observe` measurement.

The compressed synthetic sinks report 501 file-fsync calls when enabled, zero
when disabled. They have no stream manifests and are not valid collector
archives. The real writer has additional descriptor/manifest durability work.
No hash, quota or durability safeguard was removed from that reference writer.

## Tests and independent evidence audit

Local suite: **535 tests passed**, 15.309 seconds.
Linux suite: **535 tests**, 44.522 seconds, passing with one expected
Python-version inventory skip. The tests cover missing receipts, interrupted
checkpoints, changed input/output bytes, re-signed incorrect summaries, invalid
timings, exclusive publication and overlapping phase identities.

Remote evidence:
`/var/lib/qcrl-stream/recorder-stage-split-20261008-b2ZO5P/evidence`

Fresh ignored local review directory:
`.qcrl/reviews/recorder-stage-split-linux-20261008-ooe2ES/`

The independent local audit verified:

- The exact originating file set and SHA-256 bytes of all **238 files**.
- Bound source/implementation bytes and the prepared original stream verification.
- **270,216 decompressed record comparisons** across three durable archives and
  six synthetic compression outputs, preserving every original encoded record.
- Full versioned verification of all three durable archives, matching the source.
- Every checkpoint, receipt and final report hash, all 15 cases and their ordering.
- Independently recomputed component medians and timing totals, consistent with
  the measured worker's total systemd CPU usage and process lifetime.
- Recorded live process PIDs and `/proc/self/cgroup` paths against each worker's
  saved PID, unit identity, slice and resource-limit properties; distinct
  preparation, measurement and verification processes on the same recorded boot.
- Passing Linux test logs and unchanged public collector head/environment hashes.

On this systemd version, full properties after worker exit expose
`ControlGroupId`, `Slice` and `Id` but omit the retired `ControlGroup` path.
The independent auditor initially rejected that schema mismatch, then compared
the recorded live unified-cgroup path with `/Slice/Id` and the saved PID and
positive group ID. This is not a claim of exclusive CPU cores or externally
attested intraprocess timings. No peak RSS or swap conclusion is made.

The comparisons repeat one source archive; they are not 270,216 unique market
messages. The audit checks originating EC2 filesystem bytes, not S3 objects;
these synthetic diagnostic artifacts were not uploaded to S3.

Prepared artifact hash:
`8779aa4a67a4e16fa1d5942d7bd7b7ece7022a3ff4fbb956f302f070ac3d1084`

Verified report hash:
`c21bb5ff70276d5cbd6d74bc90df4baf9ba315aa7d4e07452671577746bdd44a`

Independent audit hash:
`4ae5707242cf2abfc47cc4e6701493f263e7b009d1262140657ff8e7536c0d76`

Audit script hash:
`433a599fff4556f5716be750e6794946fabcd624287b74eb794fdd722c6527ae`

## Public state and next experiment

The deployed stream checkout stayed at
`4dd60ba168180243f8600860330dc1afc4816ff4`. Fetching Git objects did not advance
that checkout. `/etc/qcrl-stream.env` stayed at SHA-256
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
The daily collector timer remained active and the stream pilot inactive.

**Next: a prospectively fixed paired localhost single-pass encoding experiment.**
The current writer serializes the row once canonically to hash it, then again to
write its JSON line. Test a candidate that reuses serialization work while
preserving logical record content and hashes, byte quotas, fsync cadence, segment
sealing, manifests and complete verification. Compare the unchanged real recorder
against the candidate under the same producer/consumer bounds, measuring CPU,
delivery tails and receive-marker coverage. Independently verify all raw messages,
record identities and recovery trajectories. Declare the candidate's physical
JSON representation explicitly; compressed file bytes need not be identical.

No public rollout, hardware upgrade or weakened durability is authorized by this
offline component ranking alone. A validated paired streaming improvement is the
next acceptance gate.
