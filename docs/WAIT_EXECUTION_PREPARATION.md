# Wait compatibility and execution preparation — offline only

Declared October 13, 2026. This adds a separate finite compatibility plan and
an execution-envelope/lifecycle rehearsal. It does not run compatibility sleeps,
load native libc, supply a production worker or launch a systemd unit. The
comparison remains prospective v2; v1/v2 plan identities and evidence are unchanged.

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
retained by the future driver, alongside readiness and journals. No such worker
exists yet. This declaration is preparation, not authority to execute it.

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
select retry policy is copied from v2. Runtime observation and review generation
are not implemented: callers must not fabricate those hashes from upstream source
or Mac fixtures. The exact installed patched binary, relevant source provenance,
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
No command executor, subprocess or systemd adapter exists in this module.

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

Next implement the bounded compatibility worker and production adapters offline,
with fault fixtures for unknown rows, timeout/SIGKILL partial evidence, bounded
context/journal/identity reads and exclusive controls. Then freeze committed
sources and independently verify installed runtime/ABI and the private envelope.
Do not stage/run the compatibility unit or comparison under offline authorization.
Do not import credentials, provision infrastructure, change public collectors,
merge main, sync QuantConnect or revise prior recorder failures/budgets.

Complete local regression: all 1,063 offline tests passed in 85.739 seconds on
Intel macOS / Python 3.14.6 with localhost fixture permission. This remains local
verification only; Linux/native behavior and actual enforcement are unverified.
