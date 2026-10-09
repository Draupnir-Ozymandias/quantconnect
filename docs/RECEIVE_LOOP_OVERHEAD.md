# Prospective receive-loop instrumentation overhead, version 1

Status: **preregistration only; runner and performance evaluator not implemented**.
The [private integration](../infra/stream/RECEIVE_LOOP_INTEGRATION_2026_10_08.md)
passed correctness tests, not overhead acceptance. This declaration schedules no
workers and does not authorize public captures or deployment.

## Fixed comparison

Six sequential Linux localhost cases, baseline/instrumented,
instrumented/baseline, baseline/instrumented. No concurrent cases, warm-up cohort,
retries, automatic confirmation or tuning. Reuse corpus
`a343b91c289731a9262354bb629b4ef22379b67a806568e3d4f2caf08d1fa849`.
Each case repeats six four-second 500/s and one-second 3,000/s cycles: 30 seconds,
30,000 deliveries including six synthetic text PONG replacements. Preserve
duplicates and ordered message occurrence identities; this is not exchange traffic.

Both lanes use the same original recorder, single-pass encoder, scoped diagnostic
v3/128-marker contract, profiling, freshness, recovery, segment policy, gzip,
flush/fsync and seal behavior. Public validators remain unchanged. The baseline
uses ObservedSocket; the instrumented lane uses DiagnosticSocket's inherited
delivery/queue/send/close methods and private entry-installed wrappers. Do not
run collect_fixture as the timed benchmark: it performs a post-collection archive
audit. A separate runner must expose the declared measurement boundaries.

Keep websockets 15.0.1 source/method pins, high/low water 16/4, socket read 65,536,
message maximum 262,144, no compression/protocol ping/proxy, and probe budgets
32,768 reads, 32,768 flow edges and 32 MiB encoded sideband. Keep producer/consumer
CPU quotas 100%/75%, each 512 MiB, 32 tasks and 120-second runtime, in separate
processes/cgroups on one shared host without affinity. No hardware/quota changes.

## Measurement and audit boundaries

Consumer process CPU window starts immediately before connect and ends after
collector return, closure and receiver-thread join. The recorder's timed writes
and final durability work remain inside. In both lanes, raw/receive-record
retention and profiling remain equivalent. Sideband remains memory-resident;
its allocations and hot-path observation cost are inside the CPU/resource window.
Snapshots, serialization and copied delivery persistence are after this window;
finish post-window persistence and worker exit before starting the next case.
Archive audits and analysis run only after all six measurements; do not subtract probe cost.
Report post-window CPU/time/storage separately, not as free work. Never move
recorder fsync outside the measurement to improve a result.

Capture consumer/producer process, boot and cgroup identities; actual worker start,
exit/order, configured quotas, exits/journals, source inventories, original artifact
hashes and before/after public checkout/config hashes. Host timers stay untouched.
If deployment identity changes or resource isolation cannot be verified, stop and
preserve the cohort as inconclusive. No audits or extra diagnostic load during runs.

Independently verify originating bytes, corpus/source/library binding, ready and
producer records, all 30,000 ordered raw deliveries per case, probe/heartbeat
identity, sealed row chains, physical encoding, receive/recovery occurrences and
all first/last timing-eligibility denominators. Instrumented cases additionally
require complete sidebands, independent frame-range and dispatch-bracket linkage,
no disabled observation or budget loss. Do not relabel unit-fixture envelopes as
benchmark receipts: the runner needs separately declared measurement schemas.

## Preregistered gate

All six cases must complete with every raw delivery intact, 100% locally eligible
timing in both lanes, 100% dispatch linkage in the instrumented lane, no observation
loss, no overflow/open recovery and no resource failure. Per-phase producer
attainment must be at least 99% of target and maximum deadline lateness at most
50 ms in each case. A producer failure makes the comparison inconclusive, not
an attribution to instrumentation.

For **each of the three pairs**, instrumented/baseline ratios must be at most:

- 1.05 for measured consumer CPU seconds.
- 1.05 for low-rate delivery p99, burst delivery p99 and worst delivery upper bound.
- 1.10 for maximum in-capture sampled RSS.

Use the existing independently recomputed delivery-age upper bounds and percentile
definition, including PONGs in their emitted phase; phase membership follows
producer schedule, not arrival rate. Baseline zero denominators, missing metrics,
incomplete attribution or inconsistent sampling are inconclusive, never pass.
Report every pair; lane medians are descriptive, pooled percentiles cannot rescue
a failed pair. These deliberately conservative gates allow modest probe overhead;
they are not statistical proof of equivalence. Do not widen thresholds afterward.

RSS is sparse in-capture context, not true peak memory. Retain whole-unit MemoryPeak
if exposed, distinguish its post-window serialization population, and mark it
unknown otherwise. No OOM, timeout or task-limit failure is acceptable. Report
queue depth/backpressure, flow-gate/read/dispatch counts and coverage without
claiming socket return equals wire arrival or assigning event-specific causality.

Gate success permits diagnostic interval analysis only. Failure/inconclusive
results end this finite cohort; preserve everything, revise a separately versioned
proposal if needed. No public rollout, extra captures, credentials, trading,
infrastructure changes or QuantConnect sync follows automatically.

## Offline declaration

`python -m infra.stream.receive_loop_overhead --corpus ORIGINAL_CORPUS.json
--loop-contract VERIFIED_CONTRACT.json --output NEW_DECLARATION.json` writes a
new, never-overwritten artifact binding this fixed policy, original corpus,
decomposition-linked observation contract and full relevant source inventory.
Validation rejects even rehashed policy/source changes. This is a reproducibility
hash, not a cryptographic signature or execution authority. Runtime-specific
observation receipts can differ across hosts; verify method/file pins identically.
Before measurement, freeze a separate runner/evaluator inventory and validate it
against this protocol; this plan is not evidence that either implementation exists.
