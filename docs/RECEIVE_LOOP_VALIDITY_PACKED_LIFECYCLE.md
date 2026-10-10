# Packed lifecycle integration — isolated fixtures

`receive_loop_validity_packed_lifecycle.py` is a separate eight-message fixture
path, not a modification to the frozen v1 lifecycle or launcher. Production
staging (`test_only=False`) is refused before directory creation. Its distinct
implementation schema binds the packed method, original generator, common
resource method and 12 source files. The original cost declaration is retained
only as a validated baseline-policy reference; it is not a new packed cost
preregistration. No cost or unit acceptance follows from these fixtures.

The bounded worker/observer lifecycle preserves absolute deadlines, process
identity, single-use role claims, readiness handshake, observer-window enclosure,
acknowledgment before snapshots, raw delivery persistence before materialization,
and exclusive signed artifacts. Optional live-binding requirements cannot be
satisfied merely by elapsed time. Offline verification checks readiness and
source links, and, when required, live receipt identity/window/hash links.
Independent originating systemd verification is still required separately; fixture
receipt checks do not prove that a unit actually existed.

The worker saves the versioned prototype wrapper in `packed-prototype.json`
and its canonical core in `worker-result.json`. Verification checks both hashes,
rejects premature prototype acceptance claims, requires exact core equality,
then uses the original semantic occurrence/CPU verifier. Any snapshot failure
retains raw occurrences and a failure receipt without fabricating a successful
worker result. The observer remains unchanged in measurement semantics.

## Tests and boundaries

Separate-process fixtures exercise control, pacing and full lanes, ordered raw
occurrences, distinct worker/observer identities and enclosing CPU windows.
Full-lane fixture counters are synthetic, not native resource evidence.
Tests cover prepare and snapshot faults, retained raw prefixes, no replay,
missing-case read-only verification, finite startup timeout, source/method drift,
production staging refusal, explicit binding requirements, rehashed prototype
claims and mismatched collection-readiness receipts.

October 10 verification: **816 local regression tests passed**. The combined
packed-core, packed-lifecycle and original-lifecycle set passed 32 tests; the
final packed-lifecycle rerun passed all 11 tests. No native Linux unit or cost
experiment was executed during this integration.

The lifecycle implementation is intentionally isolated from the frozen v1 module.
Shared measurement/verifier dependencies remain source-bound. The duplicated
orchestration is temporary prototype machinery; it should not become a second
unmaintained production path.

## Remaining gates

The separate declaration and dedicated trial/launcher/auditor are now implemented
in `docs/RECEIVE_LOOP_VALIDITY_PACKED_COST.md`; native source-freeze, smoke and
finite-cohort execution remain pending. The list below describes their required
sequence and does not authorize those executions.

1. Separately declare a packed cost experiment with explicit representation and
   validation-timing changes; do not relabel the rejected v1 experiment.
2. Add real workload integration and a dedicated launcher/auditor bound to that
   declaration, retaining the original limits, rotations and cost thresholds
   unless a new policy change is explicitly justified before execution.
3. Commit/source-freeze, run a fresh native eight-message live-unit smoke, then
   seek execution authorization for the finite cohort. No captures, infrastructure
   changes, public rollout or trades are authorized by fixture success.
