# Development handoff

Updated October 13, 2026. Continue in
`/Users/eric/Projects/quantconnect/polymarket-martingale` on
`codex/lupus-development`. The Intel migration base is `f05d5dd`; use Git history
for subsequent development revisions. Keep this branch separate from main.

## Current scientific status

The independently audited October 12 Linux clock-only diagnostic retained 11
observed wakes and one missed target. The 60-second waits returned approximately
59–60 ms late. Select-related slack is a post-hoc mechanism hypothesis, not proof
about the installed runtime or an exclusive cause. Measurement completeness and
performance acceptance remain false. The earlier counter smoke's final endpoint
missed the fixed deadline before any counter read. Preserve both failures and
the original 50-ms budget.

The absolute-monotonic adapter remains isolated and offline-tested. The active
prospective comparison is now
[ABSOLUTE_SELECT_COMPARISON_V2.md](ABSOLUTE_SELECT_COMPARISON_V2.md), with plan hash
`c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d`.
V2 preserves two serial 133.3-second AB/BA runs and integer targets while allowing
one Python select call with disclosed runtime retries and unknown internal count.
The predecessor
[ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md](ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md)
and its hash `a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`
remain retained; v1 has no native result. Both hashes have literal regression pins.
Injected select/absolute collection, pair lifecycle, validation, exact descriptive
evaluation and bounded exclusive publication now exist. No native runner exists.

## Verification and migration

The migration receipt records 598 retained evidence files, with no imported
jobs/secrets or cloud-sync authorization. The operator reported all 1,034
bootstrap tests passed on Intel macOS / Python 3.14.6. Migration selection is
curated; omitted historical evidence remains on the originating machine.

After comparison preparation, all 1,037 local offline regression tests passed
in 92.808 seconds, including localhost fixtures. All 12 focused comparison/
absolute-wait tests passed. The new Python files pass Python 3.9 syntax parsing.
The initial restricted sandbox run could not bind localhost and was stopped;
the complete rerun with localhost permission passed. These checks do not verify
Linux ABI compatibility, native scheduling behavior or actual improvement.

## Unfinished work and continuation constraints

A finite compatibility declaration, source/runtime freeze validation and injected
launcher lifecycle rehearsal now exist; see `WAIT_EXECUTION_PREPARATION.md`.
The compatibility worker and production adapters are now implemented and tested
offline; see the production continuation below. Independently verify
the Linux ABI, timespec field offsets and native symbol envelope; freeze execution
sources and runtime before any separately authorized native measurement. Confirm
the installed select retry behavior and signal context against v2's disclosure.

Recorder application native compatibility and the six-case budget cohort remain
blocked. New comparison results cannot retroactively repair previous verdicts.
Frozen evidence must be audited against its originating source revisions, not
the current expanded source inventory. Preserve the source-frozen reviews and
all original measurement plans; do not edit `.qcrl/` evidence.

Keep signal feature optimization on hold, martingale closed, and the prospective
2026Q4 declaration unchanged and unexecuted until its window completes. Do not
launch captures/native experiments, provision infrastructure, import credentials,
merge into main or sync QuantConnect under this handoff. The current authorized
publication is the reviewed development branch only.

## October 13 pre-integration review

The v1 protocol hash is explicitly pinned in a regression test. The adapter now
caps complete exception text, including its name prefix, at 160 characters;
both exception paths and first-error preservation have injected regression
coverage. All 14 focused tests pass locally; the full-suite count above is from
before this repair. Python 3.9 syntax checks pass, not native runtime validation.

Upstream Python 3.9 select automatically retries signal-interrupted calls with
a recomputed timeout unless the signal handler raises. One Python call and zero
collector retries do not imply one syscall or zero internal retries. The proposed
reference therefore has an unresolved v1 execution gate: verify the exact Linux
runtime and prospectively declare a successor allowing disclosed runtime retries/
unknown counts, or separately declare a compatible reference. Preserve v1's hash;
do not silently alter its semantics. See the preregistration's October 13 review.

## October 13 v2 offline implementation milestone

Prospectively resolved the retry contract with a new v2 identity; neither v1 nor
its evidence was replaced. Zero application retries and unknown select-internal
retry counts are separate fields. Exposed faults cancel remaining attempts;
missed targets stay unknown and later original slots continue. The evaluator
preserves unknown pairs and reports rational medians without changing acceptance.
Publication is exclusive and byte-bounded; it does not claim atomicity/fsync or
native process-kill recovery. Thirty focused tests and all 1,055 local offline regression tests passed
(91.860 seconds for the full suite, with localhost fixtures). New v2 files pass
Python 3.9 syntax parsing. No Linux validation, native binding or scheduling run.

Primary development may continue offline implementation, tests, documentation
and reviewed development-branch commits/pushes without consulting another chat.
Surface material design decisions, blockers and actions outside this scope.
Native execution, main merges and QC sync remain unauthorized.

## October 13 compatibility-envelope preparation

Added compatibility plan hash
`aec6f48ff1558e544cf68665c062126ce5b44366bf8c7e9e0d18ac82268fd864`, pinned in tests.
It declares one select then one absolute wait on a 50-ms cumulative grid, without
signal injection or performance acceptance. Broad tracked-source hashing excludes
evidence/dot paths/credential scripts and refuses symlinks/oversize files. The
freeze validates LP64 timespec offsets, exact interface metadata, installed-binary
and source-review receipt hashes, positive clock resolution and read-only signal
context. No actual Linux runtime receipt or execution freeze was generated.

Injected lifecycle tests cover fresh claims, serial tests/compatibility, bounded
readiness/unit/result/journal interfaces, active binding before release, private
cleanup and public/source drift. Unit specifications have no worker entrypoint;
no production launcher or native worker is available. Thirty-eight focused local
tests and all 1,063 offline regression tests passed (85.739 seconds, localhost
fixtures permitted); Python 3.9 syntax checks passed for the new files.
Native verification and process-kill/host-loss evidence retention remain pending.

## Compatibility worker and production-adapter milestone

The worker now retains both arm slots and failed setup/interruption/missed-target
states, publishes bounded exclusive durable controls/results, and requires native
source/runtime match plus independently bound release. It installs no signal
handlers and cannot retry. The production root-Linux entrypoint runs only the
private regression-test and declared two-wait compatibility roles, with fixed
unit limits, no measurement-network access and private-only cleanup. Helper
output/deadlines, effective properties, live identities, partial journals and
final origin inventories have offline fault coverage. No new diagnostic layer.

A concrete receipt-validation gap was repaired: non-null collector/fatal errors
cannot pass even if adapter observations are marked observed. A built-in-select
fixture also required recording reviewed binary kind and hashing its actual
Python backing binary. Original compatibility/v1/v2 plan hashes are unchanged.

The source candidate will be sealed from the clean published implementation
revision under `.qcrl/reviews/wait-compatibility-source-COMMIT12/source-freeze.json`.
This is source-only: runtime remains unfrozen pending authorized read-only access
to the existing Ohio host and independent installed-binary/source review. The
full execution freeze must bind this exact source inventory and the verified
Linux runtime; no Mac/fixture runtime may substitute. Remote inspection permission
is pending. Afterward report readiness and request separate native authorization
for one compatibility smoke only; the v2 comparison remains unauthorized.

Offline readiness: the worker, production adapters and final copy/output
safeguards pass 53 focused tests. Complete exception/collector failure states,
release/setup/drift paths, effective property checks, bounded helper failures,
partial journals/source copies and exclusive claims have regression coverage.
No compatibility wait syscalls, native unit or remote inspection was performed.
The read-only remote authorization question remains pending; without installed
binary/source review the Linux runtime freeze and smoke execution readiness
cannot be claimed. The source-only candidate receipt will identify the exact
clean published commit. Full regression counts are in the preparation document.

Final verification for this milestone: all 1,078 offline tests passed in 72.261
seconds on Intel macOS / Python 3.14.6 with localhost fixtures permitted. All 53
focused tests and Python 3.9 syntax checks passed. The implementation is ready
for source-candidate sealing and authorized read-only Linux runtime inspection;
full source/runtime freeze and native-smoke execution readiness are still gated
on that installed-runtime review. No smoke authorization is implied.
