# Offline RSS reader review — October 16, 2026

**Propose one change: reuse the per-read validated quota when the two fresh
ancestry snapshots are equal.** No production optimization is implemented here,
no native work is authorized, and the failed RssCpu01 verdict is unchanged.
The four UTC violations are a separate unresolved requirement.

Reviewed `LinuxReader.read`, `text`, `identity`, `members`, `quota` and `cpu_sets`
in [recorder_application_resources.py](../infra/stream/recorder_application_resources.py),
the identity parsers, absolute observer and consumer monitor. Current reader
source SHA-256 `39607be9ee51e3055ed8196c80f6be58e66806367eaa247f649ff904db2591ae`
matches the native candidate `eb13a51` / freeze `babeeced…ff5caee`. This review
uses code and retained evidence, with one existing fake proc/cgroup fixture;
it is not a Linux profiler, allocation trace, syscall trace or timing benchmark.

## Definition and boundaries to preserve

RSS is the sum of freshly read `/proc/<pid>/status` **VmRSS** values, multiplied
by 1024, for every unique live process in the dedicated cgroup. The owner must
be present, actor count is bounded, descendant cgroups are refused, membership
must match before/after, and each actor's PID/start/cgroup/boot identity is checked
around its RSS read. This is a sum of process RSS observations, not a PSS or
shared-page-deduplicated physical-memory measure, and not a continuous peak.

The wall start precedes path/owner checks and resource acquisition; the wall end
follows closing ancestry/path checks. Both auxiliary thread CPU calls stay inside
those same wall endpoints, with their existing placement. RSS width <=5 ms,
start lateness <=50 ms, all CPU/resource budgets and UTC <=1 ms remain unchanged.
No work is subtracted or made admissible using a CPU-adjusted duration.

## Work inside and outside the bracket

| Area | Observed work and limits of evidence |
| --- | --- |
| Parsing | Every identity parses proc stat and cgroup membership and strips boot ID. VmRSS parsing decodes the entire bounded status file, splits it into lines, filters exact `VmRSS:` prefixes, then tokenizes only matching lines. It checks exactly one field, shape, `kB`, integer value and nonnegativity. Counter parsing checks duplicate keys and decimal values. CPU ancestry parsing builds/validates controller and CPU sets, canonical paths, hierarchy and quota restrictions. No substep CPU attribution is retained. |
| Allocation | Fresh bytes/ASCII strings, split-line lists, identity/actor dictionaries, ancestry lists/dictionaries, Path/PurePosixPath objects, sets, and nested helper functions are created. Repeated quota validation recreates its parsing/sets. Such allocation is visible in source; its byte count, GC contribution and share of native CPU are not measured. |
| File access | Each `text` request opens anew with O_RDONLY/O_NONBLOCK/O_NOFOLLOW, fstats a regular file, reads at most 16,385 bytes, closes, rejects >16,384 bytes, then decodes ASCII. These flags/checks must remain. Two ancestry snapshots reopen all relevant pseudo-files; two membership checks reopen cgroup.procs and enumerate child entries with `p.is_dir()`. Two path checks stat every anchored ancestor. O_NONBLOCK is not evidence that elapsed time excludes scheduling or blocking. |
| Locking and scheduling | The reader contains no explicit application Lock/RLock acquisition. The monitor calls it on one observer thread; the producer's attempt_lock is in a different worker path. Stop-event checks and thread join are outside the resource read. Python parsing/allocation shares the GIL with recorder work; kernel/file-access synchronization and OS scheduling are not instrumented. No particular lock, GIL handoff, syscall or collector is established as the cause. |
| Repeated validation | `ancestry_snapshot()` calls `quota(rows)` on both snapshots inside the bracket; unchanged snapshots are then compared. Result construction calls `quota(ancestry)` again after the wall end. That is three pure validations of the same metadata on the stable path, two inside. `quota` and its helpers do not mutate the snapshot or perform file access. This is the narrow redundancy selected for optimization. |
| Outside the bracket | Thread identification is before the wall start. Final finite/order validation, result construction, the third quota call, RSS summation, CPU delta/status assembly and policy/sample/witness hashing occur after the wall end. Parent JSON publication is later. These still cost memory/CPU and can influence later scheduling; moving more work outside would not demonstrate a cheaper end-to-end observer. |

The four owner/actor identity calls for one actor are not treated as dispensable:
they bracket different stages of the acquisition. Neither are repeated membership,
path or live-ancestry reads. Caching those observations across reads, or deleting
rechecks, would weaken the current evidence qualification.

The absolute observer retains bounded rows (capacity 184), with occasional CPU
pre-reads; RssCpu01 retained 72 rows plus initial readiness. This explains some
retention by design, not a finding of an unbounded reader cache or a proven GC
cause. Recorder frame/completion allocations and other threads coexist; these
retained CPU endpoints cannot attribute their effects to individual substeps.

## Offline operation counts, not native timings

A one-off read used the existing Ohio fixture: three ancestor directories, one
actor, disabled child cpuset files and absent root quota/memory files, matching
the retained native ancestry shape. The actual reader produced the expected
VmRSS sum and quota. Spies recorded:

| Call category | Per successful fixture read |
| --- | ---: |
| `text` open/read requests attempted | 48 |
| Successful bounded pseudo-file reads | 40 |
| Expected FileNotFoundError paths | 8 |
| Identity calls | 4 |
| Membership enumerations | 2 |
| Anchored path-check passes | 2 |
| Quota calls inside / after wall bracket | 2 / 1 |

The 48 requests comprise 12 identity-file reads, 30 ancestry-file attempts,
2 cgroup.procs reads, 1 status read and 3 counter/current-memory reads. Each
successful `text` request also fstats, reads and closes its descriptor. Directory
iteration/type checks and ancestor stats are additional work. These are helper
operation counts, **not the total native kernel syscall count or their cost**;
actual directory population/kernel behavior was not traced. The counts do not
show which operation dominated the native 3.013–5.581 ms thread CPU observations.

Private reproducible analysis: `.qcrl/reviews/recorder-rss-path-review-20261016/`
contains `review-path.py` and `path-counts.json`. It changes no reader or historical
evidence. No additional clocks or diagnostic layer were added to production.

## One minimal optimization, with its proof obligation

Keep both fresh ancestry acquisitions and every I/O, identity, membership and
path check in their current order. Validate the first ancestry snapshot once
inside the bracket and retain its derived effective quota in a **local variable
for this read only**. When the closing snapshot equals it, reuse that quota.
There is no cross-sample cache or stale-data fallback.

On a changed closing snapshot, still call the existing quota validator before
raising the existing ancestry-race error. This preserves rejection of malformed
closing metadata and the prior error precedence, rather than silently accepting
or replacing that fault. The intended structure is:

```text
first = acquire_fresh_ancestry_without_redundant_validation()
effective_quota = quota(first)                 # still inside wall bracket
... unchanged acquisition and checks ...
closing = acquire_fresh_ancestry_without_redundant_validation()
if closing != first:
    quota(closing)                             # preserve original invalid-data fault
    raise existing_ancestry_race_error
... unchanged final path / CPU / wall stamps ...
result.effective_quota = effective_quota        # same result field/value
```

Equality to the already validated first snapshot establishes that running the
same pure validator again would have the same result. On the normal path this
removes **one quota validation inside the bracket and one after it**. It removes
no pseudo-file read, does not relocate required acquisition/validation past the
wall end, and preserves all VmRSS parsing/output rules. It may reduce CPU and
allocation; no millisecond saving or 5-ms compliance is established. It is not a
solution to every observed scheduling delay.

If implemented later, require differential fixtures for unchanged output, both
nested/disabled CPU-controller layouts and multi-actor reads; changed valid and
malformed closing quota/controller data; existing PID/membership/path/symlink/
permission/byte-cap faults; unchanged clock-call placement and auxiliary linkage;
and unchanged wall-threshold decisions. Count assertions should confirm 1/0
inside/after quota calls for stable snapshots, with closing validation retained
on mismatch. Give the code change a prospective source identity/freeze. Historical
results remain frozen; no native rerun or cohort follows automatically.

## Cheaper substitutes are different observations

`memory.current` is already captured as a distinct cgroup counter; it cannot
replace the specified sum of process VmRSS. Own-process-only RSS, RssAnon-only
RSS, cached/less-frequent readings, removing actors or dropping race checks
change population, value source or qualification. Each would require a separately
named measure and prospective declaration, not a drop-in RSS fix.

`statm.resident` or a different process API would need an explicit source/units/
error/race equivalence review; none is established here. Treat such a proposal
as a separate measure until equivalence is demonstrated. Early-exiting on the
first VmRSS line or decoding only that line can also change duplicate-field or
whole-file ASCII rejection behavior. Persistent descriptors or cached directory
type information need their own replacement/race analysis. None is part of this
one proposed optimization.

## Four UTC failures remain separate

RssCpu01's UTC rows **7236, 11693, 12410 and 24142** remain failed at
1.172455, 1.943665, 1.459714 and 1.894590 ms respectively. They measure the distinct
per-frame `utc_text(self.clock())` bracket. RSS optimization neither changes those
historical witnesses nor establishes repaired UTC coverage. A possible shared
GIL/load effect is a hypothesis, not a repair. Any future acceptance evaluation
must independently apply the unchanged 1-ms UTC gate to every required frame,
alongside RSS gates. The eight historical RSS unknowns and overall failed verdict
also remain unchanged. [Original result and evidence anchors](RECORDER_RSS_CPU_VALIDATION_RESULT_20261016.md).
