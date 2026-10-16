# Per-read quota reuse v1 — offline implementation and comparison

Prospective implementation identity: **`qcrl.resource_quota_reuse.v1`**.
This succeeds the [proposal-only review](RECORDER_RSS_PATH_REVIEW_20261016.md).
It does not amend any historical declaration, evidence, audit or failed verdict.
No native run is authorized or performed by this change.

## Complete-input review

`LinuxReader.read` compares the entire two ordered lists of freshly constructed
dictionaries, without projecting fields, comparing hashes or retaining a cache
across reads. All acquired values are strings or `None`; the lists/dictionaries
are local, unexposed until publication, and unmodified by validation.

| Validator input | Where used | Included in equality |
| --- | --- | --- |
| `cpu_max` | Quota/period parsing, positive integers, finite vs unlimited restrictions | Full value, including `None` vs string |
| `path` | Root-only absent quota, canonical relative ancestry, immediate parent binding | Full value for every row |
| `cpuset_effective` | Enabled/disabled-file proof, CPU/range parsing, subset and intersection cardinality | Full value, including absent vs present |
| `controllers` | Presence/partial-witness mode, valid unique controller names, availability, root cpuset proof | Key presence and full value |
| `subtree_control` | Presence, valid unique names, enabled subset and next-parent controller binding | Key presence and full value |
| List structure | One through 32 ancestors, ordered child/parent/root relationships | Length, order and every row |

`quota`, `cpu_sets`, `controllers` and `cpus` read no clock, file, process,
environment or mutable external measurement. Their parsing rules/constants are
unchanged. Equality also retains `memory_max`; although its value does not affect
quota, a memory-limit ancestry change must still fail. A changed string ordering
or whitespace retained after acquisition can fail equality even when the numeric
quota would remain the same. No semantic-equivalence shortcut is introduced.

The first snapshot is validated inside the original bracket, before actor reads.
Its derived effective quota is held only until this read returns. The second
snapshot still acquires every file; when equal, deterministic validation would
yield the same result. If unequal, the original validator is called on the
closing snapshot before the original ancestry-race error: malformed closing
metadata retains its validation fault and precedence. This preserves existing
race detection, including its original inability to detect an unobserved ABA
change between reads; equality is not proof of continuous stability.

## Measurement and envelope

Stable-path quota calls change from **two inside / one after** the bracket to
**one inside / zero after**. The original closing-validation work is eliminated
only after equality; no validation is deferred beyond the wall end. Both fresh
ancestry acquisitions, identity/membership/path checks, proc-status parsing,
current VmRSS sum, counters, file flags, regular-file/size/ASCII checks and error
handling remain. There are no additional production timing calls, locks,
diagnostic fields or runtime dependencies.

Wall start → auxiliary CPU start → resource acquisition/checks → auxiliary CPU
end → wall end remains authoritative. CPU timing policy/hash, sample linkage,
publication format, fresh reads and RSS definition are unchanged. Neither CPU
time nor benchmark savings is subtracted from a wall bracket. The original RSS
5-ms width, UTC 1-ms width, slot-start bounds, resource limits, persistence/case
budgets and all other acceptance thresholds remain unchanged. This source has
not been staged or validated on Linux; any future packet must freeze its own
source/runtime envelope. The old native freeze cannot authorize this source.

## Deterministic verification

`tests/test_recorder_quota_reuse.py` exercises the actual reader against bounded
fake proc/cgroup files. It checks all quota value dependencies and key presence,
complete dictionary/list equality, no validator mutation, exactly one stable
validation inside the original clock endpoints, 48 fresh text attempts in the
three-ancestor/one-actor fixture, and new quota acquisition on a subsequent read.

Changed closing CPU quota, root CPU set, controller declarations, enabled
controllers and memory limit are rejected, including equal-quota changes.
Malformed first and closing quota/CPU-set/controller inputs retain validation
faults. Reordered, omitted, repeated and over-cap ancestry is rejected. The
one/32/33-ancestor boundary and CPU index 65,535/65,536 boundaries are explicit.
Membership, process-start identity, directory-inode replacement and missing-file
races still fail. Existing clock-failure, invalid-reading, policy-hash and worker
publication-linkage tests continue to apply without changing timing policy.

Local Python 3.14.6: full discovery **1,200 passed in 153.739 s**; final quota
module **7/7 passed** (including the additional ancestry/CPU boundary test).
The combined resource/auxiliary modules passed 38 tests before that addition.
Python 3.9 syntax parsing passed for changed Python files; this is not installed
Linux/native runtime validation. No localhost fixture contacts a remote host.

## Offline benchmark

**Do not spend a standalone Linux run on this optimization.** The native-shaped
fixture's median paired in-bracket saving is **59.655 microseconds / 0.059655 ms**,
only **0.306–0.913%** of the retained 6.531977–19.519640-ms wall widths. This is a
scale comparison across different environments, not a predicted Linux speedup,
adjusted native measurement, guarantee of compliance or fix for the wide reads.

| Offline path | Old median (microseconds) | Proposed median | Median paired saving |
| --- | ---: | ---: | ---: |
| Three ancestors, disabled child cpusets: validation inside bracket (2 → 1) | 118.237 | 59.784 | 59.655 |
| Same ancestry: total validation, including after bracket (3 → 1) | 175.894 | 60.679 | 116.527 |
| Two-ancestor legacy metadata: validation inside bracket | 11.412 | 5.713 | 5.602 |
| Same legacy metadata: total validation | 16.849 | 5.627 | 11.269 |
| Complete instrumented reader against three-ancestor fake files | 2,765.449 | 2,593.221 | 126.955 |

The first path includes the unchanged complete snapshot comparison and the new
branch; it excludes acquisition, which is unchanged. First/closing snapshots
are separate equal lists. Total validation includes the old third call after
the wall end; its saving cannot be credited to the authoritative bracket.
The complete-reader number includes all file work, clock calls, result building
and witness hashing, including work outside the bracket. Its paired savings
range from **−389.956 to +347.860 microseconds**, so it is not a precise isolated
estimate of this small change. Three-ancestor in-bracket paired batch savings
range 51.462–65.498 microseconds. Medians of paired differences need not equal
the difference between the two medians.

Method: Intel x86_64 macOS 26.7.1, Python 3.14.6, normal enabled GC, warm local
fake proc/cgroup files, same process, no concurrent test suite. Preserve the old
module using `git show 18a09a3:infra/stream/recorder_application_resources.py`;
load old/new modules separately. Use the existing `ohio_fixture` ancestry for
the three-level shape and `fixtures.ANCESTRY` for the legacy two-level shape.
Warm each old/new pair with 200 calls, then alternate AB/BA over 20 rounds of
2,000 calls per path, timing batch wall duration with `perf_counter_ns` outside
production operations and reporting per-call microseconds. For full readers,
use 20 alternating rounds of 100 calls after the same warm-up. Real auxiliary
thread-CPU clocks are enabled for both full readers. The harness also verifies
identical complete uninstrumented samples with equal injected wall clocks, and
identical ordered traces of **48 fresh text attempts**. It changes no production
clock or instrumentation. No claim about cold cache, allocation counts, kernel
scheduling, contention or incremental observer overhead follows from this test.

Private retained comparison: `.qcrl/reviews/recorder-quota-reuse-20261016/`, with
`baseline.py`, `proposed.py`, one-off `benchmark.py` and all 20 raw batches in
`benchmark.json`. No general diagnostic framework or dependency was added.

- Baseline reader SHA-256: `39607be9ee51e3055ed8196c80f6be58e66806367eaa247f649ff904db2591ae`.
- Proposed reader SHA-256: `8cf1450a19a3d0ff95d3d878f4aaed435151ec259baebd2c275e8bbec3c2d7f3`.
- Benchmark script SHA-256: `44f1813238bb2a924e38071e81a4153d741ab3fa55bce1d5bd2ddda1374b13ea`.
- Benchmark JSON SHA-256: `45aed0ba2269c351b6012923bada1c3eca6c6455c4504df973a8836fab6d724e`.

This source identity is prospective. The measurement contract itself is
unchanged; its existing CPU timing-policy hash remains
`6eb2509c03a390c53d3fdc31124177403638d700e1e4922ee8ce015e7cf81ee5`.

## Separate UTC blocker and historical evidence

The four RssCpu01 UTC failures at sequences **7236, 11693, 12410 and 24142** remain
unresolved. Optimizing RSS validation cannot establish UTC coverage. The eight
RSS unknowns and the failed application verdict also remain unchanged; the
[native result](RECORDER_RSS_CPU_VALIDATION_RESULT_20261016.md) is authoritative.
No adjusted bracket, repaired verdict, new threshold, native rerun or cohort.
The RssCpu01 archive/audit and original Cohort02 archive/audit hashes were
rechecked against their recorded anchors, as was the Cohort01 OOM archive.
All match. Frozen native source, declarations, evidence and audits were not
rewritten or reevaluated under this successor source.
