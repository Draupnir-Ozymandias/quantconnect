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

The absolute-monotonic adapter remains isolated and offline-tested. The next
finite implementation comparison is declared in
[ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md](ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md):
two serial 133.3-second runs, select/absolute then absolute/select, with integer
cumulative targets, retained unknowns, fixed fault/stopping rules and no replay.
Its plan hash is
`a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`.
Only the declaration and offline target expander exist; no native runner exists.

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

Implement the select wrapper and injected collector, fault/unknown/stop handling,
partial evidence retention, bounded exclusive publication, independent validator/
evaluator and a bounded launcher. Independently verify the Linux ABI, timespec
field offsets and native symbol envelope; freeze execution sources and runtime
before any separately authorized native measurement. Disclose the reference
runtime's interrupt/retry semantics before execution.

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
