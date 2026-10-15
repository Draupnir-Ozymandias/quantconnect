# Prospective readiness memory envelope v2

The October 15 attempt under freeze
`90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686`
remains failed at readiness: memory-cgroup OOM, zero cohort cases. Its original
512-MiB declaration, raw evidence and independent verdict remain unchanged.
This document prospectively qualifies only the readiness-unit memory statement
in the original successor contract; it does not amend that historical contract.

## Offline findings and choice

At committed source cfe5154, the complete original 1,169-test suite passed on
Intel macOS/Python 3.14.6 with a temporary local profiling harness. Process peak
RSS was 647,921,664 bytes (617.91 MiB). Discovery/import RSS was small relative to
the full-population fixture; the dominant peak increase was
`FullPopulationTests.test_actual_60000_completion_producer_large_reader_and_absolute_audit`
in tests/test_recorder_persistence_cohort.py. That test alone, in a fresh process,
passed in 53.152 s, maximum RSS 604,839,936 bytes (576.82 MiB). A 512-MiB
per-module or per-test subprocess cap therefore has no supporting local margin.
Splitting tests would also add startup/import cost under the unchanged time cap.
No reduced population, special skip, reduced fixture or test-only algorithm is proposed.

The fixture simultaneously retains the first decoded completion report, another
large producer result and decoded producer control, while the actual audit loads
completion/producer controls again and performs archive/completion verification.
The verifier builds ordinal/hash metadata and latency rows for 60,000 frames;
JSON hashing/encoding also creates transient full-size representations. These are
real overlapping working sets, not evidence of a 512-MiB-compatible isolated test.
WorkerTests.test_workload_order_population_and_duplicate_bytes in
tests/test_recorder_application_components.py was the other >=8-MiB process
high-water increase (78,139,392 to 93,696,000 bytes).

Cumulative retention exists locally: RSS was 76,238,848 bytes entering the cohort
module, 311,750,656 after its full-population test, and 231,817,216 after the suite.
An explicit final gc.collect collected 6,048 objects, no uncollectable garbage,
and left RSS at 231,817,216. Thus cyclic garbage collection alone did not return
that resident memory. Allocator retention/imports/live objects are not separately
quantified; these data do not prove an unbounded leak. Suite peak exceeded the
isolated peak by 43,081,728 bytes, but this is a comparison of separate local runs,
not an additive decomposition or native attribution. Both processes overlapped
for part of profiling, so elapsed times are not a native readiness prediction.

**Propose 1 GiB for the single readiness unit only**, versus the old 512 MiB.
It is 425,820,160 bytes above the observed local suite RSS peak, allowing prospective
headroom for transient encodings, interpreter/allocator differences and cgroup
accounting (including filesystem cache). That margin is explicit and unvalidated
on Linux. The installed Python 3.9/aarch64 process and whole-cgroup peak may differ.
The actual test/allocation active in the historical OOM remains unknown.

No VM, account, public-service or global resource setting changes. Readiness ends
before any producer/recorder starts; its proposed 1-GiB cap equals the aggregate
of the already declared two concurrent 512-MiB case-unit caps. This bounds the
proposal but does not reserve physical memory or prove shared-host headroom.
Fresh read-only host/runtime/public and credit-context checks remain necessary
before execution. Report available host memory and any unavailable field; no
retrospective host/credit minimum is invented. No credit-balance minimum gate.

## Executable contract and evidence

`READINESS_ENVELOPE` is hashed inside the source-bound declaration and v2 freeze.
The launcher specifies/tests exactly 1,073,741,824 bytes for role=tests; the
independent auditor checks that same actual value, fixed command, successful exit,
exact test/skip population and lifetime. Producer/consumer actual limits still go
through the unchanged historical validator requiring 536,870,912 bytes.
The readiness capture path retains original property and journal bytes, including
partial command output on failure. It never substitutes 512-MiB property text to
satisfy the historical validator. The old adapter remains frozen.

The unchanged original cohort plan hash remains
`eca23ef82ac9ca72a816a9580483a35657df364ea081f7772f8e5c0477b1fa6b`.
The execution freeze/declaration/candidate identity must be new. All six schedules,
360,000 occurrences, recorder and producer 512-MiB limits, CPU 75%, TasksMax 32,
240-s ceilings, 50-ms pre-read lead, persistence reserve and every measurement
threshold remain unchanged. Readiness is also still CPU 75%, TasksMax 32 and
240 s, with the complete discovered test population and one existing Python 3.9
skip. A later OOM/timeout/population mismatch stops before cases with no retry.
Neither local memory profiling nor the proposed allowance passes Linux readiness.
No extra standalone smoke, new production observer or runtime diagnostic layer.

One new identity may propose staging plus one readiness-gated six-case cohort,
13 units total, then stop for independent completeness, inclusive overhead,
archive and missed-slot audit. Existing source/runtime/public drift/fatal-stop,
partial preservation, no replay/retry/tuning and authority rules still apply.
The exact candidate/freeze/transport/count/stage belong in a separate approval
packet after offline tests. Nothing here authorizes native execution.
