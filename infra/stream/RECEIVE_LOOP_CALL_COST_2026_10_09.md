# Isolated observer-call cost — October 9, 2026

## Outcome

**Bookkeeping/allocation work is the next optimization target; no lower-overhead
transport or recorder acceptance has been established.** The rejected six-case
cohort remains rejected and unchanged. No cohort was replayed, public collector
modified, quota expanded or clock/performance threshold relaxed.

`infra.stream.receive_loop_cost` is a bounded synthetic model, not a recorder
benchmark. It compares native-only calls, direct observer calls and the original
gate/socket/flow proxies. The model uses a fixed one-byte fake recv, an uncontended
native lock, two callbacks per read and pause/resume under a modeled existing
assembler mutex every sixteen reads. It has no socket, protocol parsing, network,
real backpressure wait, delivery archive or cgroup launcher.

Each pass has 4,096 reads, 8,192 modeled callbacks and 256 native pause/resume pairs.
Identical native operation populations and released-lock state are checked in every
mode. Both observer paths produce complete independently scanned sidebands with
4,096 read rows, 512 flow edges and **33,792 clock/guarded-update calls**. This is
model equivalence, not proof of real transport semantics or constructor coverage.

## Separate measurements

Unprofiled process-CPU measurements have three repetitions per fixed mode order.
Construction, source inspection, sideband snapshots/validation and output are
outside the workload CPU interval. cProfile and tracemalloc each have separate
passes; their CPU overhead is not substituted for the unprofiled measurements.
Cumulative profiler entries overlap and must not be added together. Tracemalloc
retained bytes are Python allocations within this pass, not process RSS or a peak
memory prediction for the recorder. Post-snapshot memory is not included.

| Synthetic mode | Local median CPU ms | Linux median CPU ms | Linux retained traced bytes |
| --- | ---: | ---: | ---: |
| Native-only model | 1.390 | 6.712 | 56 |
| Direct observer calls | 14.075 | 67.860 | 3,934,264 |
| Original proxy calls | 15.297 | 74.607 | 3,934,328 |

In this Linux model, observation without proxies already accounts for most of the
observed call-path CPU; adding proxies changes the median by about 6.75 ms. This
does **not** quantify proxy contribution to the failed real recorder cohort or
assign blame for its tails. These are tiny fixed-order samples on nonexclusive
hosts, with different Python/hardware between local and Linux. Local regression
checks also overlapped this local model; do not interpret cross-host speed ratios
or claim controlled scheduling equivalence.

The Linux profiled direct path calls `_observe` 33,792 times, with 26.0 ms self
and 99.0 ms cumulative time. `_stamp` also has 33,792 calls, with 21.2 ms self and
30.3 ms cumulative time. Guard locking, action closures, calls, dictionary updates
and clock validation all contribute; this does not isolate the cost of a lock or
closure alone. A controlled ablation is still needed before claiming either cause.

Read-row construction at probe line 53 retains about **2.86 MB**, roughly 73% of
Linux traced retained bytes; this source site includes row fields and identity/
counter allocations, not just dictionary buckets. Clock-value floats retain about
612 KB. Flow-row construction and frame counters are smaller contributors.

## Clock-bracket fixtures

Five new tests include deterministic sampling-delay fixtures: a receiver or
application sample wider than the original **1 ms** bracket limit remains timing-
ineligible even with positive elapsed bounds; narrow samples remain eligible;
overlapping samples retain their separate warning; regressing clocks fail.
These fixtures model uncertainty, not an observed scheduler mechanism. They do
not rewrite the five wide-bracket records from the completed cohort or imply
that the original clock guard is defective.

The other tests verify identical native/model clock populations, complete scanning,
separate CPU/profile/allocation passes, explicit nonacceptance flags and rejection
of unsupported modes/read sizes. Final local suite: **638 tests passed**, 20.478
seconds. All five new tests passed on Linux/Python 3.9, 0.341 seconds. The Linux
model ran in a fresh temporary checkout, with no actual capture/systemd worker.

## Evidence bindings

Ignored review:
`.qcrl/reviews/receive-loop-call-cost-20261009-VuNaNT/`.

Local profile SHA-256:
`ace4714582a501510e0e45d5fc0cae9c9403f299bd622bd983709f519a37e463`.
Linux profile SHA-256:
`7122934ca535602b22e3a8f14eb1c0b9efb858519b1ebb995df33ec4c582e53a`.
Linux originating profile **file-byte hash**, independently obtained over pinned
SSH and matched after download:
`b0fe21889b0240795cf1b9138ebb8019fbd300558fae78d395c0890f20f15d5f`.

Both canonical profile hashes and all recorded source-file hashes were rechecked
against local source. The source-pinned local/Linux runtime receipts and policies
remain distinct/explicit. The existing receive-loop prototype and production
receive-path files were not edited. No credentials, trading or QuantConnect sync.

## Proposed next prototype

Build a **separately versioned compact, closure-free buffer**, initially model-only:

- Replace repeated action-closure/helper dispatch with direct locked updates,
  preserving the same validated clock calls, counters, field meanings and failure
  behavior. Do not remove the metadata lock or rely on the GIL for cross-thread safety.
- Explore fixed-layout/slotted read rows and cache receiver identity only at the
  verified receiver-entry boundary. Materialize output dictionaries after join.
  Flow edges retain their actual calling-thread identity and assembler-mutex context.
- Keep all original budgets and native delegation exactly once. Native operations
  must still run outside the telemetry lock; observation faults disable only telemetry.
- Emit an honest new implementation/schema binding, not the rejected prototype's
  source hash. Require differential field/clock/error tests and independent scanning
  before any adapter integration, then fault-test installation/transport equivalence.

Do not present a faster synthetic model as end-to-end overhead acceptance. Any new
real recorder comparison requires a separate source-frozen prospective protocol;
the earlier all-pair gates and evidence cannot be rewritten to produce a pass.
