# Offline CPU-set observer repair — 2026-10-11

This repair follows the retained failed native smoke described in
`RECORDER_APPLICATION_NATIVE_SMOKE_2026_10_11.md`. It changes only the isolated
application-budget resource observer and its regression tests, not the public
collector, recorder, preregistered workload or acceptance budgets.

## Evidence semantics

Each newly observed ancestor retains `cgroup.controllers` and
`cgroup.subtree_control`, plus the observed CPU, memory and effective CPU-set
files. An absent child `cpuset.cpus.effective` is retained as `null`, never
replaced with a guessed CPU count or a copied string presented as a local read.

The offline quota calculation accepts that absence only when a complete,
canonical child-to-root controller hierarchy establishes that the parent did
not enable cpuset for that child. Available/enabled declarations must be
consistent, and root must still expose an observed nonempty effective CPU set.
Observed child CPU sets must be subsets of their observed ancestors. Effective
quota remains the minimum of observed CPU-bandwidth limits and observed CPU-set
constraints. Existing fully populated legacy witnesses can still be read;
legacy missing CPU-set evidence cannot use this exception without controller
proof. New native reads always include the proof fields.

This follows the kernel's documented parent-controlled interface-file and
top-down controller rules, and the definition of `cpuset.cpus.effective` on
cpuset-enabled groups:
[Linux cgroup-v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html).

Only genuine file absence is considered. Permission failures, symlinks, malformed
controller declarations, missing enabled-controller files, missing root evidence,
skipped ancestors and contradictory hierarchy evidence remain errors. The reader
checks controller/limit snapshots on both sides of the sample and rejects observed
changes; these are bracketed reads, not an atomic kernel snapshot. Existing
scheduled-slot errors and the evaluator's unknown/failure precedence are unchanged.
The extra proof reads are part of observer cost and must be measured in the fresh
native smoke and eventual unchanged-budget cohort; no overhead acceptance is claimed.

## Regression coverage and execution boundary

Seven added tests cover Ohio's three-level hierarchy, explicit nulls, ancestor
bandwidth constraints, uncapped bandwidth with observed root CPUs, enabled and
partly disabled nested CPU sets, contradictory/malformed/stripped proof,
nonregular/permission failures, changes inside a sample, and independent evaluator
recalculation with unknown evidence retained. These are synthetic filesystem
fixtures, not fresh EC2 measurements.

Verification: **975 complete local tests passed** in 41.482 seconds using the
existing `.qcrl/receive-path-venv` (Python 3.14.6, websockets 15.0.1), with localhost
socket permission. The final focused component/launcher/auditor run passed
31 tests after an additional enabled-but-missing-file assertion. The declaration
hash remains `c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade`.
Earlier local attempts used an interpreter missing websockets or lacked permission
to bind localhost; those environment failures are not recorded as passing runs.

The failed smoke, its origin evidence and rejection are untouched. No compatibility
success receipt, cloud deployment, public capture, cohort, Git push or QC sync is
authorized by this repair. Commit the tested implementation, then use that new
source revision for a separately authorized fresh native compatibility smoke.
The old revision's failure must not be replayed or retrospectively marked passed.
