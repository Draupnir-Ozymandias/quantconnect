# Checkpointed recorder-stage replay, version 2

Version 1 remains unchanged for reproducibility. Version 2 reuses its five
component implementations and the same retained 30,000-frame localhost workload,
three rotating repetitions, encoding, flush cadence, and durability settings.
It changes the **diagnostic lifecycle**, not the public collector.

```text
prepare (bounded source audit, no retained measurement data)
  → measure (all 15 stages, durable UNVERIFIED timing checkpoints)
    → verify each stage (separate bounded processes, streaming comparisons)
      → finalize (all receipts required, then publish verified cost report)
```

All phases bind the exact input-file set and bytes and the implementation source
bytes. Preparation seals the original full stream verification. Measurement
checks that binding before reading the already verified input; it does not run
the heavyweight stream verifier. Each completed stage writes its CPU/wall timing,
output-file hashes and process identity outside its timer and before auditing.
Completion of measurement is separately sealed, but remains explicitly unverified.

Verification processes hold no complete decoded/encoded input lists. They compare
output records through bounded streaming reads. The durable stage additionally
runs the full stream verifier and must reproduce the prepared source result.
Freshness samples are replayed exactly; encoding totals and compression/fsync
summaries are checked. Every receipt binds its exact checkpoint. Finalization
rechecks source, code, checkpoints, output hashes and all 15 receipts. Preparation
and measurement PIDs must differ; verification PIDs must differ from measurement.
The launcher independently preserves actual systemd process/cgroup properties.

Incomplete or interrupted phases never publish a final verified report. Existing
outputs cannot be overwritten; this is a finite run, not automatic resume or
retry. A fresh run is required after any measurement interruption. Old unverified
checkpoints remain unverified even after a matching separate receipt exists;
only the final report expresses completed verification. Hashes are integrity
bindings, not external cryptographic attestations of CPU timings.

Each Linux worker uses **75% CPU, 512 MiB, 32 tasks and 120 seconds**. Resource
settings of public collectors do not change. A fresh frozen checkout is used,
the public stream observer must be inactive, and cases are serial. No network
capture, credentials, orders or market replay occurs. Runtime caps now apply to
separate preparation, measurement and stage-audit jobs—not one accumulated audit.

```bash
python infra/stream/recorder_stage_split.py prepare SOURCE FRESH_OUTPUT
python infra/stream/recorder_stage_split.py measure SOURCE OUTPUT
# All rounds 0,1,2 and all five fixed stages are required:
python infra/stream/recorder_stage_split.py verify SOURCE OUTPUT --round 0 --stage encode_hash
python infra/stream/recorder_stage_split.py finalize SOURCE OUTPUT
```

Component measurements remain unpaced, source-specific, cache-sensitive offline
costs. The durable writer stage includes replay-clock parsing and digest checking,
but excludes socket/receive instrumentation, classification, watchdogs, profiling
and freshness processing. The synthetic gzip sinks are not collector archives.
Do not add/subtract component medians or interpret them as wire latency, fills,
profitability, or justification for weakening public recorder safeguards.

Tests cover interrupted measurement checkpoints, missing receipts, changed inputs
and outputs, re-signed incorrect summaries, invalid timings, exclusive publication,
and overlapping phase identities. Production acceptance also requires independent
originating-byte audit and Linux process/resource verification.
