# Polymarket tooling review and build-versus-borrow decision

Reviewed 2026-10-10. Scope: public documentation and selected source paths,
not an independent security audit, installation or reproduced benchmark.
Branch heads were read with `git ls-remote`; selected source sections were also
read at those exact revisions, because cached web pages differed from current HEAD.

## Relevant upstreams

### Polymarket Latency Toolkit

Revision: `658b4f30f91047cf4c9bf3fdf7753b44c50e5cd7`.
[Selected benchmark source](https://github.com/freakspace/polymarket-latency/blob/658b4f30f91047cf4c9bf3fdf7753b44c50e5cd7/ws_benchmark/benchmark.py).
[Operator documentation](https://github.com/freakspace/polymarket-latency/tree/master/ws_benchmark).

The receive loop samples UTC immediately after application `recv()` returns.
It uses a bounded observation queue and periodically yields while consuming it.
The documented default is summary-only, with optional event/connection logging.
These are useful references for relative socket comparisons and avoiding analysis
starvation. They are not kernel-arrival measurements or our raw-archive contract.
Readiness for independent durable replay is not established by this limited review.

Decision: borrow measurement distinctions and bounded-analysis design ideas.
Do not deploy its multi-socket or trading tools, adopt its latency numbers as
targets, or replace our evidence recorder without a separate evaluation.

### poly-book

Revision: `126d30ce9638b9441a3358bbd14ea1b3d420d0cd`.
[WAL design](https://github.com/weiminglong/poly-book/blob/126d30ce9638b9441a3358bbd14ea1b3d420d0cd/crates/pb-wal/README.md).
[Benchmark context](https://github.com/weiminglong/poly-book/blob/126d30ce9638b9441a3358bbd14ea1b3d420d0cd/docs/PERFORMANCE.md).

Its documented architecture separates ingestion and serving through an append-only
log, distinguishes flush visibility from durable sync, and offers strict recovery
reading separately from live reading. Benchmarks explicitly describe a single
Apple workstation, not controlled deployment measurements. These distinctions are
useful; replacing our archive would require checking raw-message preservation,
error/gap semantics, crash recovery and compatibility with our existing evidence.

Decision: architectural reference, not immediate Rust migration. A separate
process/log boundary becomes worthwhile if application tests establish reader
starvation from storage or analysis—not merely because a CPU ratio exceeds 1.05.

### OpenMarket

[Versioned paper](https://arxiv.org/html/2607.26245v1), especially sections 4–5,
8–10 and limitations. It describes collector/source timestamps, quality flags,
explicit gaps, deduplicated analytic exports and unresolved clock offset. It is
a BTC 15-minute research release, not proof about our five-minute contracts.
Dataset contents and strategy assumptions were not reproduced or validated here.

Decision: methodological comparison and a candidate later external-data study.
Keep imported datasets in a separate provenance lane; do not use them to fill
missing prospective captures or claim an execution edge.

## Existing QCRL capabilities and gaps

| Requirement | Current evidence or code | Remaining gap |
| --- | --- | --- |
| Unchanged raw application messages | `market_stream.py`, segmented raw-text rows | Library-returned messages, not packet bytes or venue completeness |
| Immutable integrity and lifecycle | `stream_segments.py`, footer/manifests, versioned verifier | No acceptance from service exit alone; abrupt prefixes remain partial |
| Explicit gaps/reconnects | Market stream and resilience policy | Missing venue events within an open connection are not fully detectable |
| Distinct local/source clocks | Profiling and receive-path payloads | Minimal non-profile mode lacks an immediate socket-return stamp |
| Deferred heavy verification | Rolling deferral contract | Confirm chosen future lane excludes analysis contention |
| Fixed storage/process bounds | Segmented quotas and isolated unit settings | Native library high-water is not a strict queue/memory cap |
| Recorder completion timing | Aggregate profiling durations | No per-message append-completion or durable-watermark witness |
| Capacity/headroom | Coarse service samples and offline component studies | Actual recorder application budget not yet measured |

The base row timestamp is taken at append entry, after classification. It is not
socket return or completed persistence. The segmented gzip writer buffers data;
append completion, flush, successful fsync, sealed-manifest publication and S3
replication are different boundaries. Existing phase counters cannot substitute
for per-record completion or cumulative durable-watermark evidence.

Experimental single-pass encoding and compact observation already exist under
`infra/stream`; they are not automatically the public recorder. This review does
not propose to repeat their implementation or promote their rejected/inconclusive
overhead experiments.

## Decision and smallest next implementation

Retain QCRL's raw archive/verifiers and source/lifecycle evidence. Separate an
ordinary research-recording profile from a detailed diagnostic profile; do not
remove existing safeguards from historical or deployed plans.

Next implement only the missing local boundary witnesses in an opt-in version:
immediate application-return stamp, append-completion witness, and cumulative
successful-fsync watermark. Encode completion receipts separately to avoid a
record claiming its own future completion. Retain unknown/failed witness states.
Use existing bounded archive, resource and offline verifier machinery. Do not
add per-frame CPU pairs or internal receive-loop hooks to this profile.

First verify ordering, shutdown, crash-prefix and I/O-failure semantics offline.
Then perform one separately frozen actual-recorder localhost capacity test against
the proposed research budget, rather than another synthetic probe-cost cohort.
Only after review would a small prospectively locked public cohort be appropriate.
No such run, deployment, dependency installation, trading or QC sync is authorized
or performed by this document.
