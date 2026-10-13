# Finite absolute/select comparison — prospective v2

Declared October 13, 2026, before native integration or new native results.
This is the active offline implementation contract. It prospectively replaces
v1 for future comparison work; v1, its source/history, hash and frozen evidence
remain retained. No historical verdict is changed and no native execution is
authorized by either this document or the implementation.

V2 `infra/stream/recorder_wait_comparison_v2.py::PLAN` hash:
`c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d`.
Predecessor v1 hash:
`a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`.
Both are literal regression assertions, not only recomputed self-consistency
checks. Further protocol edits require a separately identified successor.

## Prospective resolution of the retry mismatch

One attempt means one application wait invocation. The collector never retries
or resubmits a target. The select reference remains
`select.select([], [], [], timeout)` with its runtime behavior disclosed rather
than suppressed. Upstream Python 3.9 retries after signal interruption using a
recomputed timeout unless the signal handler raises; in that case the exception
propagates. See the
[Python 3.9 select documentation](https://docs.python.org/3.9/library/select.html#select.select).

A select observation records application retries as zero and internal retries
as **null/unknown**, including successful returns. Do not infer zero internal
retries from a returned empty triple or install a signal handler to manufacture
symmetry. The absolute arm calls the existing repaired absolute adapter once;
a returned positive errno, including EINTR, remains unknown without resubmission.
An exposed select exception or absolute errno stops that run's remaining attempts
and cancels the second run when applicable. The arms therefore compare application
wait implementations with explicitly different interruption semantics, not
single-syscall scheduling performance. V1's strict single-request/no-concealed-EINTR
interpretation is not satisfied by relabeling its counts; this v2 identity is
required. Exact installed Linux behavior/signal context still needs verification.

## Fixed design and bounds

Preserve the v1 geometry and budgets: two serial runs, select/absolute then
absolute/select. Each block contains cumulative integer intervals 50 ms, 100 ms,
500 ms, 1 s, 5 s, 60 s. Every run has one integer epoch and 12 targets ending
133.3 seconds later, preceded by 16 adjacent integer-clock pairs. There are two
observations per arm/interval and 24 planned cells total. No adjusted epochs,
catch-up, baseline subtraction, new timing acceptance threshold, shuffled order
or preferred-result replay. AB/BA ordering leaves host/time confounding.

The collector records a monotonic checkpoint immediately before each adapter
invocation and refuses a regressing checkpoint before attempting a wait. The
adapter's own pre-request/return pair remains the inclusive timing envelope.
Retain both; checkpoint overhead can shorten the requested remaining interval
and must not be subtracted from lateness. Cross-arm clock regressions also stop
attempts. Select's exact represented timeout ratio and signed conversion error
relative to integer remaining nanoseconds are retained. FFI marshaling/clock-call
and interpreter overhead remain inside the respective wait envelopes.

A past/equal target is unknown with no wait; later original targets continue.
Any other exposed wait/clock fault or early return stops remaining attempts.
Every error includes its exception-name prefix within a total 160-character cap.
Baseline/epoch faults produce a partial failure receipt with null epoch and no
instantiated targets. A cancelled second run retains its own receipt, no baseline
or epoch, and no observations. Analysis represents these uninstantiated cells as
unknown; it never invents targets or success rows. Original rows remain retained.

Run zero must validate and publish successfully before creating run one's fresh
injected clock/adapters. Fatal run zero results in a cancelled run-one receipt.
Publication failure propagates and prevents the next factory call; keep already
collected evidence and partial publication for inspection, without retry/replay.
The offline orchestrator does not claim timeout/process-kill recovery: retaining
native partial rows and journals requires the future bounded launcher.

Each unit retains CPU 75%, memory 512 MiB, 32 tasks, runtime 240 seconds. Each
application wait has at most 60 seconds remaining. Run results and summary each
have a 256-KiB byte cap; fixed row counts and error caps bound the normal output.
Validate before exclusive creation; existing files are never overwritten. Retain
exact file-byte SHA-256 separately from canonical payload hashes. Publication
occurs after collection. Exclusive creation is not an atomic or fsync durability
claim; failed writes can leave partial files, which must remain retained.

## Implemented offline contracts

`recorder_wait_comparison_v2.py` exposes a copied hashed declaration, an injected
`SelectWait`, `collect_run`, `cancelled_run`, and `collect_pair`. No real clock,
select function, libc binder, CLI, deployment or public collector is supplied.
`execute=True` gates injected calls only and does not convey native authority.

`recorder_wait_comparison_audit.py` validates schema/hash/plan/population,
integer-target and remaining-duration arithmetic, baseline/checkpoint chronology,
wait caps, exact float conversion, statuses and authority/retry flags, fatal
stopping and cancellation. Rehashing changed evidence does not bypass arithmetic
or population checks. Hash verification establishes content consistency only.

The evaluator requires both receipts in declared order; it refuses a resumed run
one after fatal run zero or cancellation after a nonfatal run zero. For each
interval/repeat it retains both arm latenesses and absolute minus select, or null
for an incomplete pair. Per arm/interval it reports unknown count and observed
minimum/median/maximum. Medians and paired median differences use exact rational
nanoseconds (including half-nanoseconds), avoiding float rounding. It reports
completeness separately from acceptance, never pools interval scales or infers
rare tails, significance, native origin, fills or trading authority. A complete
comparison is still descriptive and cannot unlock the recorder budget cohort.

Producers: v2 collector and the existing absolute adapter. Consumer: v2 audit/
evaluator. Schemas: plan/run/summary v2 and select-wait v2; absolute-wait v1
retains its original fields with the disclosed error-bound repair. V1 comparison
artifacts are not accepted by this evaluator. Payload hash fields are
`plan_sha256`, `run_sha256`, `summary_sha256`, and `wait_sha256` respectively.

## Native gates and remaining work

Before any native integration, independently verify installed runtime select
retry behavior and existing signal context, Linux glibc LP64 ABI/timespec size and
field offsets, monotonic clock identity and libc symbol/signature. Freeze exact
execution-source/dependency and Python/glibc/kernel identities with this plan
hash. Neither upstream documentation, injected tests nor Python 3.9 syntax checks
establish installed Linux compatibility or actual scheduling improvement.

A future finite compatibility declaration, source/runtime inventory, bounded
private launcher with readiness/unit/PID/cgroup verification, contextual read-only
snapshots and partial-result/journal retention remain unfinished. Keep original
public services/source/configuration, timer slack, Nice, affinity, clocksource,
instance/runtime, infrastructure and recorder budgets unchanged. No tracing,
credentials, venue acquisition, QC sync or native experiment is authorized here.

## Offline verification

Thirty focused predecessor/absolute/v2 tests passed on Intel macOS / Python
3.14.6. Coverage includes exact/pinned identities, fixed AB/BA population and
integer targets, request conversion, early/late/missed waits, EINTR, return/clock
faults, baseline failure, cancellation, publication order/failure, rehashed
arithmetic/authority tampering, byte bounds, exclusive publication and file hashes.
No native call or real scheduling measurement occurred.

Complete local regression: all 1,055 offline tests passed in 91.860 seconds on
Intel macOS / Python 3.14.6, with localhost fixture permission. New v2 collector,
audit and tests also passed Python 3.9 syntax parsing. These are local tests,
not Linux/runtime/ABI or native scheduling validation.
