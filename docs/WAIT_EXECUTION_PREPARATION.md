# Wait compatibility preparation and bounded native smoke

Declared October 13, 2026. This adds a separate finite compatibility plan and
an execution-envelope/lifecycle rehearsal. The later implementation section below
adds a worker and production adapters initially tested offline only. The authorized
October 14 native smoke is recorded at the end of this document. The comparison
remains prospective v2; v1/v2 plan identities and prior evidence are unchanged.

## Finite compatibility declaration

`infra/stream/recorder_wait_execution.py::COMPATIBILITY` has hash
`aec6f48ff1558e544cf68665c062126ce5b44366bf8c7e9e0d18ac82268fd864`.
It is a literal regression pin. It binds comparison-v2 hash
`c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d`.
Any later protocol correction needs a new identity and retained predecessor.

In one private compatibility unit, choose an integer monotonic epoch after
independent readiness/release. Invoke select then absolute once each, at epoch
plus 50 ms and epoch plus 100 ms respectively. Preserve exact cumulative targets,
pre-request/return brackets, requested duration/representation, signed lateness,
error/status, zero application retries and unknown select internal retry count.
Select retains v2's disclosed recomputed-timeout behavior; absolute retains returned
EINTR without retry. No clock baseline is required for this interface smoke and
no performance threshold is introduced. No signal injection, handler changes,
reordering, catch-up, retry or replay. If the second target is already missed,
it stays unknown; any fault stops subsequent attempts. Retain unknown/unattempted
arms in the future worker's failed artifact, never replace them with successes.

Exactly two observed, valid brackets establish a complete interface-smoke receipt
only. They cannot establish native origin, installed runtime provenance, repeated
scheduling improvement or recorder acceptance. The validation implemented here
accepts complete smoke receipts only; incomplete native artifacts must still be
retained by the future driver, alongside readiness and journals. The worker now retains those failed artifacts; the success validator still
requires a complete receipt. This declaration is preparation, not authority to execute it.

Use CPU 75%, memory 512 MiB, 32 tasks and runtime 240 seconds. Errors include the
name prefix within 160 characters; result/control objects are capped at 256 KiB.
Stop after this single compatibility attempt or its first fault/timeout. It cannot
unlock the comparison until an independent, source/runtime-bound native audit is
available under separate execution authorization.

## Source/runtime envelope

`source_inventory(root, tracked_paths)` reads a caller-supplied list of Git-tracked
paths under an absolute canonical checkout. It hashes regular nonsymlink source,
documentation and fixture files with a 4-MiB per-file cap. Selection covers tracked
Python, JSON, Markdown, shell and notebook files at the project root or below
infra, execution_truth, tests, ops, campaigns, syntheses, discovery and docs. It
excludes dot paths, evidence, environments, credential scripts `poly.py`/`poly2.py`,
and unrelated directories/extensions. Required compatibility/comparison sources,
contracts, protocol docs and tests must be present. Missing or duplicate tracked
inputs, symlink paths or oversize files refuse inventory creation. A production
preflight must additionally verify clean Git state and compare bytes against the
exact committed source; a supplied tracked list alone does not establish that.

This broad current inventory must not be substituted into historical audits:
use each frozen experiment's originating revision and inventory. No retained
`.qcrl/` evidence is read, modified or re-audited by this preparation.

`freeze(source_commit, sources, runtime)` requires an exact 40-hex commit and
validated inventory hashes. Native-envelope metadata must declare the unchanged
Linux / glibc / GIL-enabled Python 3.9.25 context, aarch64 or x86_64 LP64, 64-bit
long/pointers, 16-byte timespec with offsets 0/8, clock/flag IDs 1, monotonic clock
implementation and positive finite resolution, clock_nanosleep symbol and exact
ctypes signature. Retain kernel/glibc versions and bounded read-only existing
signal-handler context. Both architecture variants are admitted by the ABI
contract; this does not authorize moving or resizing the existing Linux host.

The envelope also requires SHA-256 identities for Python/libc/select binaries,
reviewed select source and the independent runtime-review receipt. The expected
select retry policy is copied from v2. Runtime observation is now implemented behind an explicit Linux gate. Review
generation still requires independent installed-source provenance inspection;
callers must not fabricate review hashes from upstream source or Mac fixtures. The exact installed patched binary, relevant source provenance,
review and signal context need independent Linux evidence before staging. A valid
metadata object or hash only proves structure/content consistency, not truth.
Execution/native/compatibility/acceptance/order authority stays false in the freeze.

## Injected bounded-launch lifecycle rehearsal

`infra/stream/recorder_wait_lifecycle.py` produces unit specifications for a fresh
`/var/lib/qcrl-stream/recorder-wait-ALPHANUMERIC` stage and rehearses injected
operations. Specifications retain the fixed interpreter, qcrl user/group, unit
limits, read-only source, private evidence write path, protected home/system,
no-new-privileges, inaccessible collector environment files and denied IP access.
Only the test role allows numeric localhost fixtures; compatibility allows AF_UNIX
only. Every specification has `worker_entrypoint=null` and native authority false.
No command executor exists in the lifecycle module itself; the explicit Linux
production adapter maps these specifications to fixed private commands.

The rehearsal requires preflight receipts for a fresh canonical stage, clean
source/runtime match, qcrl ownership, fixed interpreter, disk reserve above four
GiB, public prerequisites and absent private units. It claims the stage once
before starting anything. The test role must complete successfully before the
compatibility role. Compatibility readiness has a 12-second wait and 256-KiB read
cap; active unit/PID/cgroup and effective-property binding precedes a hash-linked
release. Unit completion waits have a 240-second ceiling, result reads a 256-KiB
cap and journal capture a 64-KiB cap. Overflow/truncation must be explicit failure
in the future production adapter; do not quietly treat truncated journals as
complete. These callback bounds are declared interfaces, not installed enforcement.

Before cleanup, retain each started unit's journal/properties. Capture is attempted
once; a failed capture remains a preservation failure. Cleanup stops only recorded
private unit names and never restores, restarts or deletes public services/evidence.
Afterward compare public state and recheck clean source/runtime, then retain a
hashed final receipt. Readiness timeout, start/binding/capture/stop failure, unit
failure, invalid smoke result or source/public drift makes completion false.
A reused claim aborts before any start. Final-publication failure propagates;
production must retain the partial publication rather than retry or erase it.

The rehearsal cannot guarantee that a blocked callback obeys its timeout or that
a SIGKILL/host loss produces a final result. Production timeout/process control,
exclusive durable control publication, bounded journal/context reading, origin
inventory and independent remote audit remain unfinished. With no handler changes
in this compatibility plan, termination can leave only partial/readiness/journal
evidence; never claim a complete two-wait receipt from that state.

## Offline verification and next gate

Thirty-eight focused absolute/v1/v2/envelope/lifecycle tests passed locally on
Intel macOS / Python 3.14.6. They cover pinned plans, ABI/review-field refusals,
source selection/incomplete inventory/symlink/size faults, freeze integrity,
unit restrictions, claim/release sequencing and private-only failure cleanup.
All observations are fixtures; no native wait, real unit or installed Linux runtime
verification was performed. The three new Python files pass Python 3.9 syntax
parsing, which is not runtime validation.

Worker and production-adapter implementation is described below. Next complete
the installed Linux runtime/source review and execution freeze, then independently
verify the private envelope before requesting smoke execution.
Do not stage/run the compatibility unit or comparison under offline authorization.
Do not import credentials, provision infrastructure, change public collectors,
merge main, sync QuantConnect or revise prior recorder failures/budgets.

Complete local regression: all 1,063 offline tests passed in 85.739 seconds on
Intel macOS / Python 3.14.6 with localhost fixture permission. This remains local
verification only; Linux/native behavior and actual enforcement are unverified.

## Compatibility worker and production adapters — offline implementation

`recorder_wait_compatibility_worker.py` implements the declared two-arm collector
and a private Linux worker entrypoint. Injected collection retains both slots on
epoch, checkpoint, early-return, exposed-interrupt, missed-target and setup faults.
Complete exception text is bounded to 160 characters. It never retries or changes
signal handlers. The native entrypoint requires the fixed interpreter, qcrl UID,
canonical fresh private source/evidence path and matching committed source/runtime
freeze before publishing readiness. It chooses the epoch only after hash-linked
independent release, and binds the absolute adapter only after that release.

Exclusive control/result writes enforce the 256-KiB cap before creation and fsync
both the file and directory. A write failure retains partial bytes and prevents
adoption/retry. Compatibility results contain a `fatal_error` and per-arm
collector `error`; neither can be non-null in a passing compatibility receipt,
even if a retained adapter observation says observed. This fixes a concrete
success-validation gap; the declared scientific plan remains unchanged.

`recorder_wait_production.py` supplies the Linux-root launcher and bounded adapters
for the existing lifecycle. It maps only the tests and compatibility roles to
fixed commands. There is no scheduling-comparison entrypoint or automatic cohort
advancement. Construction and launch refuse other platforms, stage paths or
interpreters; fresh controls, clean source ownership/readability, disk reserve,
public prerequisites and absent private unit prefix are required before claim.

Helpers use argument arrays without a shell, incrementally drain output, enforce
10-second/256-KiB default limits and kill only their own helper process group on
cap/timeout. Unit lifetimes remain governed by the declared 240-second systemd
limit. Readiness, live PID/start/boot/cgroup/resource binding and actual effective
unit properties precede release. Raw effective properties/resource samples are
retained alongside their validated normalized properties. Context reads reuse the
existing bounded LinuxReader; no new resource diagnostic was introduced.

Journal capture is limited to 64 KiB and occurs before scoped stop. Truncated or
failed output is saved with an explicit incomplete-capture marker; partial unit
properties are retained too. Timeout, failed/SIGKILL unit or missing result yields
an incomplete launch receipt and retained readiness/journals, never a fabricated
smoke result. The launcher inventories retained regular evidence files and their
exact byte hashes after final publication; all origin/compatibility/acceptance/
order flags remain false pending independent audit. It never restores or mutates
public units, imports credentials, or runs the v2 scheduling comparison.

Runtime observation checks real ABI layout/clock metadata and symbol availability,
records Python/libc/select binary identities and existing signal context, and
requires a hash-checked independent installed-select source review. A concrete
local portability test exposed that select can be built into Python rather than
have `__file__`. The adapter therefore records `select_binary_kind` as builtin or
extension, verifies that kind against the review, and hashes the actual backing
Python binary for a verified built-in module. It refuses an unknown module origin;
it does not invent a module filename or substitute an upstream-source digest for
installed bytes. The runtime-freeze schema now requires this metadata. No previous
native execution freeze existed or was rewritten.

Required staged files outside the clean source tree are `execution-freeze.json`,
`runtime-review.json`, and `select-review-source.c`. The review schema is
`qcrl.installed_select_review.v1`, with `review_sha256`, `installed_binary_verified`
and `distribution_source_verified` true, exact v2 `retry_policy`, `binary_kind`,
`select_binary_sha256` and `source_sha256`. Those assertions require independently
verified distribution/package/source provenance; merely supplying self-consistent
JSON is insufficient. The worker rechecks the installed binary and reviewed source
bytes. A read-only Linux inspection is required before producing this receipt and
the runtime half of the freeze. No native runtime values were inferred from Mac
fixtures, and no full execution freeze has been generated locally.

After source and installed-runtime freezes are verified and native execution is
separately authorized, the production entrypoint is:

```bash
/opt/qcrl-stream/venv/bin/python -m infra.stream.recorder_wait_production --root /var/lib/qcrl-stream/recorder-wait-UNIQUE --execute
```

This runs one bounded Linux regression-test unit, then one bounded compatibility
unit with the two declared 50-ms cumulative waits. It does not run the finite v2
comparison. Failed evidence/claims/units are retained and must never be replayed.

Offline fault coverage includes full worker readiness/release success, release
timeout, source/runtime drift, setup failure, unknown arms and actual subprocess
cap/exit/deadline fixtures. Property normalization refuses relaxed isolation or
budgets; partial journal publication and final inventory are tested. Runtime ABI/
symbol observations in these tests are mocked and do not bind real native libc.
Source-only candidate sealing is local; installed Linux metadata/review and native
smoke remain separate authorization gates.

The final copy/output safeguards also retain non-UTF-8 helper output as bounded
raw failure evidence and stop a reviewed-source copy that grows beyond 4 MiB.
The partial copy and exclusive claim remain retained; a retry is refused.
Fifty-three focused tests passed locally. Final full-suite verification is
recorded below. No Linux compatibility/syscall/unit execution occurred.

Final complete offline regression: 1,078 tests passed in 72.261 seconds on Intel
macOS / Python 3.14.6, including permitted localhost fixtures. All 53 focused
protocol/adapter/envelope/production tests passed, and every changed Python file
passed Python 3.9 syntax parsing. These are local tests, not Linux native
compatibility or enforcement verification. Source sealing occurs after a clean
implementation commit; its local receipt is kept outside Git. Runtime sealing
requires the pending read-only remote review, then smoke execution needs a
separate authorization. No compatibility unit or scheduling comparison was run.

## October 14 installed-runtime review — execution still gated

Read-only Session Manager inspection and independent local distribution-source
review are complete; see `HANDOFF.md` for provenance, limits and private receipts.
Full freeze `8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`
binds the original 488-file implementation candidate 2cb6880 to observed aarch64
Linux/glibc/Python 3.9.25 metadata and binary/source/review hashes. The source-only
receipt remains untouched. Later documentation commits do not replace the candidate.

Installed select equals the official release package payload. The matching SRPM's
43 declared patches do not change selectmodule.c; reviewed source implements the
v2 disclosed signal check and recomputed-timeout EINTR retry. Official TLS repository
checksums and exact payload/RPM-manifest matches establish the review's provenance
basis; neither a reproducible build nor independent RPM signature verification
was performed. This is not a scheduling experiment or causal result.

The next gate is explicit authorization for fresh private staging, live preflight,
one bounded Linux regression unit and, only on success, the single declared
compatibility unit. No staging, native tests, waits or units ran during this review.
Readiness is conditional on clean exact candidate/runtime match and the existing
resource, public-state, readiness/release and isolation checks. Retain partial
results and stop on failure without retry/replay. Independent native audit remains
required; no comparison execution or performance/recorder acceptance is unlocked.

## October 14 authorized native smoke — interface compatibility verified

The operator subsequently authorized one finite attempt. Exact source candidate
2cb6880 and the existing full freeze were staged privately on the unchanged Ohio
host. Live preflight passed. The Linux regression unit completed 1,078 discovered
tests in 105.240 seconds, with 1,077 passing and one existing Python 3.10+ guard
skipped on Python 3.9.25. Only then did the declared compatibility unit run once.
Both select/absolute targets returned code 0 with valid brackets and no errors;
application retries were zero, while select internal retries remain unknown.

Native journals, effective properties, live binding/resource context and twelve
retained file hashes were separately checked offline. Audit identity:
`c5f7e48f1dc97f38966a0d5c7dcd51761cf2f1f5644c09b446c018bb85f3a0cb`.
Evidence identities and limits are in `HANDOFF.md`. Both private units are stopped;
public/source/runtime state is unchanged. No replay, signal injection, package
installation, public collector mutation or scheduling comparison occurred.

This verifies the finite interface smoke and captured effective envelope only.
It does not establish repeated timing performance, exclusive select-slack causality,
recorder budget acceptance or trading authority. The v2 comparison is still
prospective and requires separate native authorization. Original source-only/full
freeze controls and producer flags remain unchanged; the separate audit carries
only its narrowly stated native-origin/interface verdict. No new diagnostic layer.
