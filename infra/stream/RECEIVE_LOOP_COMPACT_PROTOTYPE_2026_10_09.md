# Compact buffer prototype — October 9, 2026

## Outcome

**Model-only compact buffer passes differential/fault checks and reduces modeled
CPU and retained allocations. Transport and recorder acceptance remain unproven.**
The rejected six-case overhead cohort remains unchanged and rejected. No actual
capture, cohort replay, public deployment, quota/threshold relaxation or credential
use occurred in this step. Existing reference observer and recorder files were
not edited. Changes remain local and uncommitted at this handoff.

## Design

`infra.stream.receive_loop_compact.CompactBuffer` replaces per-update action
closures/helper dispatch with direct `try/with lock` updates. Read and flow records
have fixed slots instead of per-row dictionaries. JSON-shaped output dictionaries
are materialized only in the post-finish snapshot. Existing construction, clock
validation, disable and finish implementations are reused explicitly; all guards,
clock calls, counters, bounded error names, budgets and modeled field meanings
remain unchanged. No dependence on the GIL replaces metadata locking.

Receiver identity is still sampled per read. Caching it was deliberately deferred:
the model does not prove a receiver-entry installation boundary. Flow records keep
their actual calling-thread identity and assembler closed/paused/queue context.
Native gate/socket/flow calls remain outside the telemetry lock; flow observation
uses the caller's existing assembler mutex without reacquiring it.

The candidate is **not** a reference ObservationBuffer subclass, so the original
connector rejects it before transport installation. No new connector exists yet.
Its honest schema is `qcrl.receive_loop_compact_sideband.model.v1`, with its own
implementation hash, `model_only=true` and `transport_installation_verified=false`.
The model's installed flag describes fixture state, not actual constructor coverage.

`scan_model` first validates the candidate hash/scope/encoded bound, then applies
the existing independently implemented ordering/range/flow rules through an
explicit in-memory reference-shaped structural view. That view is never persisted,
passed to a recorder or labeled as reference implementation evidence. Unknown
fields, source/scope tampering and invalid counters fail. This is structural reuse,
not proof that the candidate ran a real native receive loop.

## Differential/fault gate

Ten candidate tests plus one comparison test passed. They cover:

- Identical deterministic read/flow fields, frame/native populations and clock
  counts; independent structural scanning of complete modeled observations.
- Clock failure at each of the eight modeled update boundaries, preserving the
  same reference prefix, disable reason and incompleteness; invalid/regressing clocks.
- Native socket success/EOF/error behavior and exact exception identity under
  observer failure; native calls outside the metadata lock.
- Flow callbacks under an existing assembler mutex, caller-thread identity and
  closed-assembler context; no receiver-thread identity substitution.
- Read/encoded budgets, detached snapshots, early/incomplete snapshot handling,
  slotted storage and absence of action closures.
- Original connector rejection; rehashed schema/source/counter/payload tampering;
  alternating comparison order and explicit nonacceptance flags.

Full local suite: **649 tests passed**, 20.365 seconds.
Linux/Python 3.9: **11 tests passed**, 1.047 seconds, in a fresh temporary checkout.
No socket was opened by candidate/model tests. Existing full-suite localhost
fixtures remain unit tests, not a new recorder cohort. Proxy checks are not complete
transport installation, handshake, timeout or shutdown equivalence coverage.

## Bounded model comparison

The existing synthetic workload remains fixed: 4,096 fake reads, 8,192 modeled
frame callbacks, 256 native pause/resume pairs, 512 flow edges and **33,792 clock
calls** per observer. Native and observation populations match exactly. Cases
alternate reference/compact, compact/reference, reference/compact. Construction,
snapshot/materialization, source inspection and output are outside workload CPU.
Allocation tracing is a separate pass, never used for CPU timings.

| Pair / first variant | Linux reference CPU ms | Linux compact CPU ms | Reduction |
| --- | ---: | ---: | ---: |
| 0 / reference | 67.995 | 57.511 | 15.42% |
| 1 / compact | 69.726 | 54.036 | 22.50% |
| 2 / reference | 67.916 | 54.383 | 19.93% |

Linux traced retained allocation: **3,934,264 → 1,879,032 bytes**, about **52.24%**
lower. Traced peaks: 3,935,220 → 1,879,708 bytes. Those populations exclude snapshot
dictionary materialization; this is not a claim of lower whole-unit MemoryPeak/RSS.

Local CPU reductions were about 38–39%, and traced retained allocation fell from
3,213,376 to 1,924,096 bytes (~40%). Different runtime/hardware and nonexclusive
hosts make cross-host speed ratios uninterpretable. Local regression work also
overlapped this local model. Tiny call-model samples, uncontended locks, fixed
one-byte fake recv and absent protocol/recorder workload cannot predict the earlier
cohort's CPU/tail outcome. Combined closure-removal/storage changes also do not
isolate the causal contribution of either optimization.

## Evidence

Ignored review:
`.qcrl/reviews/receive-loop-compact-model-20261009-jtcF5R/`.
Local comparison SHA-256:
`fb077e303543a09b2922f8ec013330f4a2c8a8b86105e0dda5fde2f605f9a797`.
Linux comparison SHA-256:
`cbb1203f1315ac04a850753905def70544682f90b38607ed77dc734a3a538134`.
Linux originating comparison file-byte SHA-256 independently obtained via pinned
SSH and matched after download:
`67063f62484ac648359beebc81e4197a825855b0ac05578769ccd6de3f6cba86`.

Both canonical artifact hashes and all recorded source hashes were checked against
the current local files. Receipts carry distinct actual local/Linux runtime data.
No public collector, infrastructure, resource limits, credentials, trading or
QuantConnect changes occurred.

## Next gate

Build a separately bound numeric-localhost transport adapter for this candidate,
with constructor/receiver-entry, native success/error/timeout/close and observer
fault/race/budget tests. Establish post-join snapshot coverage and native delegation
exactly once. Then test private recorder integration and independently bind its
new schema/source to archived occurrences. Do not accept model-only flags as
actual installation evidence or retrofit the frozen reference validator.

Only after those correctness gates should a new prospective source-frozen recorder
overhead protocol be considered. Keep the existing 1 ms bracket exclusions and
all-pair coverage/CPU/tail/resource discipline; no automatic repeat or public rollout.
