# Recorder-stage replay audit — October 8, 2026

## Outcome

The version-1 offline harness and its correctness checks are implemented and
tested. **The Linux cost study is incomplete: no Linux cost ranking is available.**
Both bounded Linux attempts reached their runtime deadlines while verifying
archives. Neither published a completed report. Preserve this distinction:
writing complete archives does not make a benchmark complete.

There were no public captures, trades, credential use, public collector
deployments, QuantConnect synchronization, infrastructure changes, or changes to
public collector limits. Only the second ephemeral diagnostic's deadline changed.

## Protocol and source

See [the fixed component protocol](../../docs/RECORDER_STAGE_REPLAY.md).
Measured code was frozen at `a587f0d3c416e3463b1aaabf5e793e54c2e5e609` in:

`/var/lib/qcrl-stream/recorder-stage-replay-20261008-MTAKS6/source`

The input was the previously independently audited matched-cohort
`0-recorder-v3/stream`: 30,000 frames, 30,024 records, 108,626,309 uncompressed
bytes. The same input trajectory was replayed; these are not new independent
market observations. The input and every execution-truth Python file are bound
by the declaration:

`afa4777b743cf9d79fa123952c355ed67a4afd475d3dbd2fe3c693f50c51fd57`

The five stages are encoding/hashing, freshness bookkeeping, pre-encoded
gzip/file writes without fsync, the same synthetic sink with fsync, and the real
durable segmented writer. Three repetitions rotate their order. Stage timers
exclude input preparation and post-stage verification; component costs are not
additive and cannot establish socket-delay causality.

## Verification and bounded failures

All **529 tests passed locally**, in 15.716 seconds after granting localhost
socket permission. An initial sandboxed suite was blocked from binding loopback
in 18 existing WebSocket tests; this was not a code regression. Linux ran 529
tests in 42.421 seconds, passing with one expected Python-version inventory skip.
Linux tests used 75% CPU, 512 MiB, 32 tasks and a 120-second deadline.

A developmental macOS smoke replay completed all 15 stage runs and its output
checks. Its code was still being finalized and it was not an isolated frozen
measurement; its timings are not a Linux ranking or a production recommendation.

| Linux attempt | Deadline | Result | Total service CPU | Retained complete writer outputs |
| --- | --- | --- | --- | --- |
| `qcrl-stage-replay-20261008-MTAKS6` | 120 seconds | timeout, SIGTERM / status 15 | 87.854555 seconds | One durable archive; two synthetic compression outputs |
| `qcrl-stage-replay-extended-20261008-MTAKS6` | 300 seconds | timeout, SIGTERM / status 15 | 220.195285 seconds | Three durable archives; six synthetic compression outputs |

Both used the same source bytes and declaration, separate fresh output roots,
75% CPU, 512 MiB and 32 tasks. Both were stopped by their declared deadline,
not reported as OOM failures. Sampled second-run `MemoryCurrent` approached
536 million bytes (535,781,376 bytes, approximately 511 MiB), close to the
512-MiB cgroup cap. This is cgroup memory, not measured Python heap or RSS;
it does not prove a collector memory problem. No claim about swap or exclusive
host isolation is made.

The service CPU numbers include preparation and heavy offline validation. They
are **not** stage CPU measurements. Version 1 holds decoded records and encoded
bytes while validating each full output. It stores stage timings only in the
final report; that report was never published. Do not reconstruct a cost table
from elapsed time, file timestamps, archive completion, or the macOS smoke.

## Independent audit of preserved outputs

Remote evidence remains at:

`/var/lib/qcrl-stream/recorder-stage-replay-20261008-MTAKS6/evidence`

Both attempts, their declarations, test logs, unit properties, collector
before/after state, and an originating SHA-256 file inventory were downloaded
into the fresh ignored local review directory:

`.qcrl/reviews/recorder-stage-replay-linux-20261008-KJNVW1/`

The independent local audit verified:

- The exact originating set and SHA-256 bytes of all **227 files**.
- Identical bound input and implementation bytes across both attempts.
- **360,288 decompressed record comparisons** against the original source,
  across four durable archives and eight explicitly non-archive compression sinks.
- The full versioned stream verification of all four durable archives equals
  the original source verification, including receive recovery and freshness.
- Both timeout results, deadlines, CPU/memory/task caps and absent final reports.
- Passing Linux test logs and unchanged public collector state.

These are repeated comparisons of the same retained records, not 360,288 unique
market messages. The synthetic compression sinks have no manifests and cannot
be promoted as collector evidence. These diagnostic files were not uploaded to
S3; this audit verifies originating **EC2 filesystem bytes**, not S3 objects.

Independent audit hash:
`dee6557288c54c0f7ff8ca429c2b9a4ac79e225f5f13e440841e07ab0f20a6b5`

Audit script hash:
`5095b7bd6c1094c68af860ea9bf9d1540a97376659f57d9c8122c11875ff3884`

## Public collector state and next action

The deployed stream checkout stayed at
`4dd60ba168180243f8600860330dc1afc4816ff4`, clean before diagnostics.
`/etc/qcrl-stream.env` stayed at SHA-256
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
The daily collector timer remained active and the stream pilot inactive.
Fetching Git objects did not fast-forward the public checkout.

**Next: checkpointed, separate measurement and verification phases.**
Freeze a version-2 protocol that persists each completed stage's timing outside
its timer, explicitly labels those checkpoints unverified, and performs heavy
archive audits in a separate process after releasing measurement working data.
Publish a completed benchmark only after all checkpoints and outputs validate.
Keep the workload and public safeguards unchanged; do not keep extending the
deadline or upgrade infrastructure to compensate for diagnostic design.

After a valid Linux cost ranking, choose one prospectively fixed loopback-only
paired ablation with the genuine full recorder as reference. Version 1 does not
justify changing the deployed recorder, its durability, or its freshness policy.
