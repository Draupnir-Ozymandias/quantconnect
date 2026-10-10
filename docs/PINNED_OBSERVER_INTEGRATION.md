# Isolated pinned-observer integration — October 10

`receive_loop_pinned_observer.py` and `receive_loop_pinned_fixture.py` are separate
from all frozen cost trials and deployed collectors. The fixture lifecycle accepts
only eight-message test staging; it refuses production staging. The older packed
declaration is a baseline-policy reference, not a new combined-cost declaration.

## Reader and cleanup contract

The adapter retains the original external absolute tick grid and observer capacity.
Control and pacing do not construct a counter reader. Full uses the pinned reader
with the explicitly declared worker identity. First descriptor pinning is inside
the first acquisition bracket; no startup cost is silently excluded. Per-step CPU
coverage is unchanged in the packed worker. No rate or threshold was altered.

Tick failures close reader descriptors, including failures before a counter read
such as a sleep fault. Capacity/no-replay barriers remain. Observer completion
explicitly closes descriptors before its CPU window ends; common resource sampling
then closes the window. Only afterward is the signed cleanup receipt persisted,
followed by the acknowledgment. Thus descriptor close cost is included while
receipt serialization/fsync is outside the collection window.

A cleanup error is retained and prevents successful acknowledgment and complete
observer evidence. The worker persists delivered raws even when that acknowledgment
fails. Cleanup before finish is idempotent; further ticks are refused. Snapshots
and dataclass materialization occur after acknowledgment and timed collection.

## Versioned evidence links

The fixture implementation has a distinct schema binding 18 source files and
both packed-worker and pinned-observer methods. Observer reports use
`qcrl.pinned_observer_core.v1`. A signed `observer-cleanup.json` records the
method, reader presence, remaining owned descriptors, cleanup errors and close
timestamp. The acknowledgment links its artifact hash. The final observer core
must carry the identical cleanup payload, except the outer artifact hash.

Offline verification checks the method/schema, cleanup hash, zero owned handles,
no cleanup errors, lane-dependent reader presence and close timestamp inside the
observer window. Original occurrence, packed-wrapper/core, native counter identity,
interval arithmetic and enclosing observer-window checks remain. Fixture assertions
are not independent OS descriptor or originating-unit audits; those still require
separate native verification. No resource or performance acceptance follows.

## Tests and next gate

Tests cover two-process control/pacing/full fixtures, prepare/snapshot faults,
startup/source drift, partial/missing evidence, no replay, method/readiness links,
failed cleanup blocking acknowledgment, retained raw evidence and rehashed cleanup
hash mismatch. Adapter tests cover no reader in controls, handles closed before
materialization, no post-cleanup reads, sleep failure after a successful acquisition,
path replacement retaining a failed attempt, ambiguous close errors and execution
barriers. Full-lane process fixtures use synthetic reader data, not Linux resource
evidence.

October 10 verification: all **881 local regression tests passed**; the targeted
adapter/lifecycle set passed 19 tests. No native run was performed for this
integrated adapter in this step.

Next: source-freeze and an isolated native lifecycle smoke of this integrated
adapter, then a separately versioned combined-cost declaration and launcher/auditor.
The prior component speedup does not prove this integrated path meets the unchanged
5% combined-CPU gate. No cost cohort, cloud execution or public rollout occurred
during this integration.
