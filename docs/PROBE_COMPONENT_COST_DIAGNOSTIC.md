# Local probe-component diagnostic — October 10

This is an exploratory cached-fixture helper diagnostic, not a new cost cohort,
Linux resource measurement, causal profile, or acceptance gate. The rejected
packed cohort and its frozen declaration remain unchanged.

`infra/stream/receive_loop_probe_components.py` executes three rotated rounds
of seven helper batches, 100 operations per batch. Setup, reader construction,
materialization, source hashing and persistence are outside batch measurements.
It measures raw process CPU and elapsed wall time without subtracting the empty
batch, pooling into a cost verdict, replaying faults or adapting parameters.

## Observations on the local Mac

Per-operation process CPU across the three batches:

- Native pair of thread CPU stamps (two identity calls and four wall calls):
  approximately 0.39–0.40 microseconds.
- Existing validated stamp pair: 1.70–1.75 microseconds.
- Packed stamp helper pair: 1.07–1.10 microseconds.
- Parsing four fixed counter fields: 0.78–0.85 microseconds.
- Fixture identity read (boot/start/cgroup files): 72–94 microseconds.
- Full fixture counter-reader operation: 177–195 microseconds.

These batches use different helper semantics: native calls do not validate;
validated stamps allocate immutable objects; the packed helper writes numeric
columns. They do not include the whole producer step, pair-level enclosure
comparison, observer scheduler or genuine Linux pseudo-files. Small batches,
clock resolution, cache/order effects and one local run limit inference. No
speedup factor or production cost is established by these numbers.

The structural observation is that fixture identity/path/file handling is much
more costly than counter parsing here. That supports investigating the reader's
I/O path before optimizing parsing; it does not prove which Linux syscall or
helper caused the cohort's observer CPU. The cohort itself already showed
additional cost in both worker and observer actors.

## Preserved evidence and verification

Result, source snapshot and provenance receipt are under
`.qcrl/reviews/probe-components-20261010-z2wf63AF/`. Four declared component
source hashes matched the snapshot; three additional semantic dependency files
were preserved alongside them. The result hash was verified before writing the
provenance receipt. All **848 local regression tests passed**, including three
new barrier/population/fault tests. No EC2 connection or cloud execution occurred.

## Next candidate

Prototype a bounded pinned-descriptor counter reader with explicit lifecycle
ownership and before/after identity checks. Do not replace repeated identity
verification with unchecked cached identity. Test PID reuse, changed cgroup
membership, replaced paths/inodes, deleted files, symlink escape, read bounds,
descriptor cleanup and retained failure attempts. Linux descriptor/pseudo-file
semantics need separate native verification before any cohort integration.

Preserve counter cadence and per-step CPU coverage initially. If those must later
be reduced, declare the loss of temporal diagnostic coverage in a distinct plan;
do not silently downsample or retrospectively loosen the 5% CPU allowance.
