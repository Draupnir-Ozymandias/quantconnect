# Isolated recorder completion witnesses — prototype v1

Implemented offline under `infra.stream.recorder_completion` and
`infra.stream.recorder_completion_lane`. No public CLI, timer, deployment, capture
or performance acceptance is added. The minimum-useful-recorder document remains
a draft; this implements boundary evidence, not its acceptance evaluator.

## Preserved reference

The legacy recorder and segmented writer are unchanged byte-for-byte. The isolated
lane refuses drift from these exact reference hashes:

- `execution_truth/market_stream.py`:
  `3fdce54db2c3596175afdc2403ac0a140f8f99db1e43a78c72c750cc90694a47`
- `execution_truth/stream_segments.py`:
  `ed3245df20a4d6cd3fdc21481d576aeb5c135d093b876a6cb09949af4791462c`

The prototype subclasses the segmented writer and uses a separately named copy
of the collector entry point, adding only explicit witness hooks and guards.
Tests compare collector and writer-method ASTs to the reference after stripping
only the declared hooks. There are no global monkeypatches in the implementation.
Native socket/write/flush/fsync calls, errors, quotas, cadence, gzip, manifests,
classification and close ordering remain the reference behavior. Default public
connector use is refused; an offline injected connector is required.

This separation is deliberate: the first implementation added optional hooks
to the reference files, and the full suite correctly rejected that change through
frozen source/AST checks. Those changes were removed, not accommodated by modifying
any reference pin. Experimental modules live outside the frozen execution-truth
module inventory. The full suite must pass again before this prototype is frozen.

## Boundaries and sideband

The observer acquires monotonic/UTC/monotonic immediately after application
`recv()` returns, before unpacking/classification. The supplied clocks must be
the same clock callables used by the recorder. Caller-supplied observer/boot domain
and runtime/PID/thread metadata are retained; they are not independently verified
Linux identity or clock accuracy. Thread changes and regressing/nonfinite clocks
disable observation.

For each frame, retain FIFO occurrence, connection, eventual archive ordinal/hash,
return bracket and the monotonic observation after compressed `writer.write`
returns. Raw equality is checked while linking that occurrence; duplicate messages
stay separate. Completion means writer acceptance, not flush or readable/durable
bytes. Control records have no invented application-return stamp.

After writer/file flush, bracket the actual file `fsync` call. Only a successful
return yields a cumulative highest-written-ordinal/hash watermark. Sealing's file
sync is observed too; descriptor/manifest/directory syncs are not relabeled data
watermarks. Flush/write/sync errors remain failures, not synthetic success or
retries. The original collector may perform its own finally-close operation;
the observer never clears an earlier failure if that close later succeeds.

Witnesses are bounded to 65,536 frame links, 65,536 successful barriers and 32 MiB
encoded sideband. These are retention/output bounds, not a proved heap/RSS peak.
Budget/observer faults disable observation, not transport or raw recording. Failed
or unfinished barriers, unlinked returns and retained completed prefixes remain
explicit. A sideband exceeding its encoded cap is refused, not silently truncated.

Publication is a separate, exclusive post-collection JSON artifact. It cannot be
inside a row that purports to know its own future completion. The snapshot binds
policy, source bytes, stream-spec hash, clock domain and final manifest bytes.
Missing footer/manifest or observer faults cannot produce a complete snapshot.
A real crash loses in-memory witness tails; no recoverable live sideband or
power-loss watermark journal is implemented yet.

## Independent offline verification

`verify_completion` first runs the legacy archive verifier, checks the manifest,
policy/source/domain/authority bindings, and independently scans referenced row
metadata. It requires exactly one witness per retained frame in occurrence order,
matching ordinal/hash/connection; finite ordered clock enclosure; monotonic sync
watermarks; and a successful covering watermark for every frame. A linear scan
assigns the first qualifying barrier, retaining append/durable upper elapsed bounds.
Only referenced metadata is retained on the second scan, not a raw-payload list.

Rehashed missing/swapped duplicate links, bad clocks, mismatched watermarks, source
drift and acceptance claims are rejected. Hashes and internal consistency are not
authentication or external attestation of I/O time. Verification never asserts
venue completeness, lifecycle research eligibility, physical latency, fills or
performance acceptance. `acceptance_demonstrated` and `orders_authorized` stay false.

## Offline programmatic interface

Construct `CompletionWitnesses(spec, domain, clock=clock, monotonic=monotonic,
execute=True)`, then pass it as `completion_observer` to
`collect_with_completion(..., connector=offline_connector, clock=clock,
monotonic=monotonic)`. This entry point requires a segmented, matching, single-use
observer. After close, call `observer.snapshot(archive_root)` once. Publish outside
the immutable archive with `stream_segments.exclusive_json(fresh_path, report)`;
this preserves the report's own `completion_sha256` without adding another schema.
Run `verify_completion(report, archive_root, expected_domain=domain)` separately.
Do not use the resulting durations as a benchmark when clocks/connectors are fake.

Next gates: commit/source-freeze; isolated native Linux compatibility smoke; then
separately freeze one actual-recorder localhost application-budget test. No new
synthetic producer/probe cohort is implied, and no public deployment is authorized.
