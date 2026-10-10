# Pinned counter-reader prototype — offline only

`infra/stream/receive_loop_pinned_counter.py` is isolated from all collectors,
trial launchers and cost declarations. No counter cadence, CPU-stamp coverage,
resource limit or acceptance threshold has changed. The rejected packed cohort
remains immutable. No speedup, Linux compatibility or low-perturbation claim is
made by this prototype.

## Acquisition and lifecycle contract

The caller supplies the complete expected worker identity: boot, PID, process
start and canonical unified cgroup. First read lazily opens read-only descriptors
for boot ID, process stat, membership and the expected group's cpu.stat. Directory
components are opened through parent descriptors with O_DIRECTORY/O_NOFOLLOW;
leaf descriptors also use O_NOFOLLOW and O_NONBLOCK, followed by a regular-file
check. This refuses symlinks and avoids blocking on an unexpected FIFO.

Every attempt checks directory/leaf path device/inode/type anchors and descriptor
link state before and after acquisition, rereads the complete worker identity
before and after counter data, and requires equality to the supplied identity.
It does not cache identity as evidence. Position-independent reads start at zero
and read at most 4,097 bytes to enforce the original 4,096-byte limit. Counter
and sample parsers are the original independently tested semantic components.

At most 64 descriptors and 1,024 attempt slots are owned by one reader. Setup
and descriptor opening are inside its first acquisition bracket; callers must not
silently remove first-read cost in a later experiment. Read failure retains a
failed attempt, closes descriptors and prohibits replay. Capacity exhaustion
prevents additional reads and releases resources. Finish is single-use; close
is idempotent and context-manager exit releases owned descriptors. Explicit
close/finish/context ownership is required; no garbage-collection guarantee is
claimed. Cleanup failures are retained, block completeness, and are not retried
because an ambiguously closed descriptor number might already have been reused.

Path checks are observations at acquisition boundaries, not an adversarially
atomic proof against replacement-and-restoration between checks. Pinned inode
handles, repeated expected process identity and cgroup checks fail closed for
the tested changes. Native process exit/reuse and pseudo-file semantics still
need dedicated Linux verification.

## Offline correctness and fault coverage

Tests verify fresh counter values through retained descriptors, partial/missing
counter fields, before/during-read PID-start and membership changes, wrong boot,
path/inode/parent replacement, deleted files, initial and replacement symlinks,
nonregular FIFO refusal, opening failures, byte/encoding/parser faults, owner
thread changes, capacity/no replay, single-use reporting and descriptor cleanup.
Injected ambiguous close failure preserves a cleanup error while closing other
descriptors exactly once. No absent/failed counter is fabricated as zero.

October 10 verification: all **858 local regression tests passed**, including
10 pinned-reader tests. The combined original-probe/pinned-reader set passed
24 tests. No native Linux acquisition or performance test ran in this step.

## Remaining gates

First independently review and test live Linux /proc and cgroup-v2 descriptor
behavior, especially process exit/reuse, cgroup migration/deletion and fresh
pseudo-file contents. This requires a separately authorized tiny private smoke,
not a collector restart or a cost cohort. Then perform a source-bound comparison
of the original reader and this candidate with unchanged identity semantics.
The repeated path/fstat safeguards may offset open/close savings; correctness
alone does not justify adopting it. Only after measured evidence should a new
cost declaration and lifecycle integration be considered.
