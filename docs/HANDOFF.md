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

Next implement a separately declared finite compatibility gate, offline source/
runtime inventory and bounded native launcher with readiness, identity/context
verification and process-timeout/partial-journal retention. Independently verify
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
