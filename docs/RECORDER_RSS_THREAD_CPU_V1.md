# Prospective RSS thread CPU instrumentation v1

Offline implementation, October 16, 2026. **No native execution is authorized by
this document.** The failed Cohort02 verdict, original OOM attempt, historical
bytes, wall-clock gates and all budgets remain unchanged. This adds one optional
measurement to the existing reader and consumer; it adds no tracing service,
new collector, scheduler or diagnostic framework.

## Identity and activation

Policy: `qcrl.rss_thread_cpu_policy.v1`, SHA-256
`6eb2509c03a390c53d3fdc31124177403638d700e1e4922ee8ce015e7cf81ee5`.
Sample witness: `qcrl.rss_thread_cpu.v1`. The policy hash is pinned explicitly in
`tests/test_recorder_rss_thread_cpu.py`; a protocol change requires a prospective
identity/test update. The hash identifies policy, not the full source/runtime
freeze or an execution permission.

`LinuxReader(..., rss_thread_cpu=True)` enables the measurement for `read(rss=True)`.
`recorder_persistence_worker.consume(..., rss_thread_cpu=True)` passes that option
to the actual consumer reader. The monitor's initial RSS read and subsequent
absolute-observer RSS samples are instrumented on the monitor thread. CPU
pre-reads (`rss=False`) and per-frame UTC brackets have no added CPU calls.
The default is disabled; the old cohort launcher does not opt in. This revision
still changes source/branch work even on the disabled path and must not be
represented as timing-identical to a historical binary.

A future launcher must bind the opt-in argument and this policy to its new
case/declaration/command/source/runtime envelope before execution. It must not
reuse the spent six-case approval or reinterpret a historical freeze as covering
this code. No new launcher or native approval packet is claimed complete here.

## Placement and overhead

On an enabled RSS read the ordering is:

1. Obtain the Python observer thread identifier, before the wall start stamp.
2. Take the **existing** `begin = self.clock()` wall stamp.
3. Call `time.thread_time_ns()` for the CPU start, validating a nonnegative
   integer (booleans are invalid); retain a bounded auxiliary error on failure.
4. Execute the existing resource operation: identity/path/ancestry/membership
   checks, pseudo-file reads, parsing and validation.
5. Call `time.thread_time_ns()` for the CPU end, with the same validation.
6. Take the **existing** `end = self.clock()` wall stamp.
7. Perform the existing wall validation and result assembly, then assemble/hash
   the CPU witness and bind it to that complete resource sample.

The original wall endpoints still enclose resource work. Both additional CPU
clock calls, their Python wrappers, endpoint validation and any caught-clock-error
formatting are **inside that authoritative wall bracket**. Nothing is subtracted.
Thread identification precedes it; policy/sample/witness hashing, delta/status
assembly and result insertion follow it. Those costs remain observer work and
can affect subsequent scheduling and inclusive cgroup CPU/RSS. Parent artifact
serialization/publication is larger as well. No extra CPU calls occur on CPU
pre-reads or when disabled. Each completed enabled RSS read makes exactly two
endpoint attempts, even if the first faults; the second endpoint is not a retry.
An interrupted/failed resource operation may end before the second endpoint.

CPU `delta_ns = after_ns - before_ns` covers the observer thread between the two
CPU clock readings, a subset of the wall bracket. It omits the head/tail clock
and validation work outside those CPU readings. It is not the full instrumentation
cost. It is neither process CPU nor cgroup CPU and does not include other threads'
CPU. Clock resolution/quantization and the extra calls' effects require native
runtime disclosure; no numeric overhead, exact off-CPU duration, overhead
percentage or continuous RSS peak has been established by these offline tests.
An anomalous CPU/wall relationship must be reported, not silently clamped or
converted into a pass. The witness verifies types/order/linkage, not hardware
clock accuracy. No new CPU/wall ratio acceptance threshold is introduced.

The RSS width <=5 ms and start lateness <=50 ms gates, UTC width <=1 ms gate,
append/durability thresholds, 60-second enclosing cgroup CPU windows, 70% quota
budget and sampled RSS budget remain authoritative. A 6-ms wall bracket stays
inadmissible with a 2-ms CPU delta. There is no compensated wall width.

## Faults and publication linkage

A CPU endpoint exception or invalid type/value becomes a null endpoint and a
bounded error (first endpoint fault retained if both fail). A decreasing pair
also produces `status=unknown`, `delta_ns=null`. The valid authoritative resource
sample is retained. Zero is a valid reading/delta. KeyboardInterrupt is propagated
rather than disguised as a successful diagnostic; existing observer fault/stop
handling applies. Wall clock and resource failures still follow their existing
error paths and are not rescued by auxiliary measurements.

Each witness records both CPU endpoints, delta/status/error, thread ID, policy
hash, `sample_sha256` of the complete resource result excluding the witness,
and its own `witness_sha256`. The resource owner includes PID/start ID/boot/cgroup;
wall endpoints and RSS/ancestry/counters are covered by the sample hash. Copying
a witness to a different timed resource sample fails verification. These are
integrity/linkage checks, not independent native-origin attestation.

The actual consumer publishes the policy hash in both `observer-ready.json`
and `consumer.json` when enabled. Their existing case binding and artifact hashes
cover the initial/row samples and witnesses. Offline review must verify those
parent hashes/case and owner bindings, and use `verify_rss_thread_cpu(sample,
expected_thread_id=initial_thread_id)` for the initial and every present RSS
sample. Missing/mismatched policy, witness, thread or sample linkage prevents a
claim of complete auxiliary coverage. A retained raw sample can have a CPU
witness even when its wall bracket is inadmissible; that does not repair its gate.

CPU diagnostic unknowns are separate from wall/resource acceptance. The existing
resource evaluator deliberately does not promote or demote a valid resource
sample based on this optional CPU witness. Future reporting must disclose both
outcomes: an accepted resource gate alone cannot establish valid auxiliary data.

## Offline validation

Tests exercise the actual LinuxReader against bounded fake proc/cgroup files,
with injected CPU/wall clocks. They cover exact call ordering, no opt-in/pre-read
CPU calls, CPU exceptions on either endpoint, invalid/nonfinite/negative/bool
readings, regressing and zero deltas, interrupts, wall/resource faults, hash and
thread/policy/sample tampering, and uncompensated wall acceptance. An integration
test runs the actual consumer monitor, absolute observer and exclusive publication
path with injected resource files/wait syscall and capture, then verifies the
parent artifacts and every RSS witness. Existing localhost worker regression
coverage remains distinct from native Linux validation.

On Intel macOS / Python 3.14.6, **88 related offline regressions passed in
58.546 s**, including existing localhost worker/closure tests and nine new
instrumentation tests. The initial sandboxed run could not bind localhost for
two existing tests; the related set passed with that permission enabled. The nine
focused tests passed again after refining the fixture to construct the reader
through its opt-in constructor. Python 3.9 syntax parsing passed for both changed
modules and the new test file; this is not installed Python 3.9/Linux validation.

## Smallest proposed bounded native validation

Propose **one instrumented mixed case**, using the existing 60,000-frame corpus
and schedule: 10 s at 500/s (5,000), 10 s at 3,000/s (30,000), 50 s at 500/s
(25,000). Case identity must be new (suggested suffix `RssCpu01`); it is not a
replacement Cohort02 case or a six-case cohort. One producer/recorder pair is the
smallest existing workload that retains the burst and its baseline/tail context,
and supplies one complete [0,60] cgroup CPU window. An idle or 68-frame low-rate
smoke would not expose the observed burst-associated ambiguity.

Use the unchanged integer-second absolute RSS grid through capture closure and
its existing stop/coverage rule (required slots 0 through ceil(max(70, closed −
epoch)), inclusive), with capacity 184, 50-ms CPU pre-read lead, future epoch
lead 20 s and 100-ms readiness margin. Do not promise exactly 72 RSS reads:
closure determines the final required slot. Every completed RSS read, including
initial readiness, gets two CPU endpoint calls; pre-reads get none. Preserve
60,000 ordered sends, verified completion/closure, 180-s capture bound and all
original acceptance limits. Preserve partial evidence on every failure.

Before approval, prepare a new exact source/runtime/transport freeze, bind the
opt-in command/policy and clock availability/implementation/resolution, and verify
host/public/credit context read-only. Report available credit balance without a
retrospective/new minimum. Preserve each measurement unit's 512 MiB, CPU 75%,
TasksMax 32, RuntimeMax 240 s. Plan one readiness unit for that exact candidate
under the already prospectively justified 1-GiB readiness allowance, otherwise
unchanged limits. Start the pair only if readiness passes with its declared skip;
this proposal is at most one readiness unit plus one pair, never an automatic
six-case controller. The changed scope
needs its own launcher/audit binding rather than bypassing the old six-case gates.

The question is whether a valid, linked per-thread CPU delta is available for
an observed wide RSS bracket, making its CPU-versus-wall relationship reportable.
Report every slot's raw wall/CPU pair and CPU unknown, then inspect wide brackets
alongside unchanged wait, throttle-counter and sync context. Small CPU relative
to wall supports a scheduling/blocking component; substantial CPU supports active
reader work, without isolating GIL versus OS versus I/O. This does not measure
incremental overhead: there is no paired uninstrumented control. It does not
resolve the old UTC causes or validate all six-case behavior.

If no wide bracket occurs, report **inconclusive for the original delay question**.
If CPU clocks/linkage fail, report auxiliary unknown/failure and retain all wall
results. A failed wall/UTC gate remains failed even if the diagnostic is useful.
No replay, replacement, extra standalone smoke, tuning or automatic six-case run.
Stop after that one pair and its independent audit, if separately approved.
