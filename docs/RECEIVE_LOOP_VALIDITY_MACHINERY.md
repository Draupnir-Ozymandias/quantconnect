# Validity cost machinery — component stage

## Source freeze

Verified probes and v1 cost protocol were committed as
`d08a37ce988f4008ee839d76291df5006bcf87fd`. The declaration still validates at
`590e270d3766437712cdfbff588278287f1126bb442f0e8959c350e5f7b04235`.
No bound declaration sources or old cohort artifacts were changed afterward.
The commit is local; it has not been pushed.

## Workload component

`infra.stream.receive_loop_validity_worker.WorkloadCore` owns the explicitly
enabled synthetic callback workload. All lanes use the same deterministic
sorted compact JSON preparation (sequence and 512-character body) and in-memory
sink. The generator has an independent content hash. Storage is reference-
preallocated and capped at 30,000 records. Control/pacing/full execute 4/7/11
wall calls per step, plus initialization; full uses two same-thread CPU stamps.
Actual clock/callback counts are tested, not inferred from performance results.

Native failure or sampling failure prohibits replay/success. Delivered raws
survive a later CPU sampling failure, with completed-step and delivered counts
kept separate. Serialization/snapshots occur only at explicit finish. The
offline `verify_core` recomputes every raw by ordinal, checks ordered boundaries
and enclosing CPU pairs, and rejects incomplete/failed reports, tampering and
resource/acceptance claims. It does **not** audit units, enforce the eventual
absolute workload schedule or establish a completed cohort. A 30,000 capacity
label is not proof of that schedule.

## Observer component

`infra.stream.receive_loop_validity_observer.ObserverCore` is explicitly driven
and capped at 512 ticks. It creates no thread or automatic sampling schedule.
Control/pacing do not construct the reader; full reads only the explicit PID
and checks boot, process start and cgroup against the supplied worker identity.
An unavailable or wrong-identity read retains the attempted tick and blocks
success. Snapshot materialization is deferred until finish.

Repeated deadlines and deadlines before the prior wake are refused. The future
absolute scheduler must explicitly skip elapsed ticks and retain the associated
coverage gaps; this core alone does not demonstrate 100 ms sampling coverage,
dedicated cgroups or complete worker-window observation. Those remain launcher
and auditor responsibilities. No sample-limit, rate, CPU or memory retuning was
introduced.

## Verification and remaining work

**14 new component tests passed**, with reduced mocked workloads, covering
identical raw occurrences, exact calls, execution barriers, capacities,
CPU-fault raw preservation, original exception identity, rehashed tampering,
target identity, missing counters and no catch-up/replay. Python 3.9 syntax
parsing passed; these new components have not undergone native Linux runtime
verification. Prior Linux smoke covered the frozen model/probe, not these cores.

**All 765 local regression tests passed** after adding the components.

Still required: source/input implementation receipt; separate worker and observer
process lifecycle/handshake; absolute observer scheduler and gap receipts;
timed worker-plus-observer CPU windows and declared sampled-memory semantics;
strict finite Linux launcher; externally anchored origin/unit/resource auditor;
fault tests and Linux verification for that machinery. No real nine-case cohort
was launched, no collector changed and no performance acceptance was claimed.

The safe next step is isolated process/lifecycle integration, retaining failure
evidence and binding identity/window boundaries before any launcher can execute.

## Follow-up: isolated process lifecycle integrated

`infra.stream.receive_loop_validity_lifecycle` adds fresh exclusive stage and role
claims, a separate implementation/source/input receipt, worker-ready/observer-
ready/start/done/acknowledgment bindings, and bounded waits. The existing v1
declaration and its historical machinery flags are unchanged. No systemd or
whole-cohort launcher is added by this module.

Production role calls require explicit execution and native Linux identity;
the CLI cannot select a reduced workload. Internal fixtures are distinctly
`test_only`, with eight messages and a 10 ms observer grid, and never contribute
performance evidence. Normal roles retain the declared 30,000 messages and
100 ms observer grid. Absolute scheduling records skipped ticks instead of
issuing catch-up counter bursts. Skips are evidence, not quietly treated as
continuous coverage or successful sampling.

The worker remains alive through observer acknowledgment. Snapshot/JSON
materialization follows the collection window, with raw delivery persistence
**before** workload snapshotting. Snapshot failure retains all delivered raw
occurrences and an explicit failure receipt, without a successful result.
Preparation, startup/handshake and observer failures preserve available claims,
attempts and partial receipts. Role reuse is refused; no retries are performed.

Read-only case verification rehashes source/declaration/implementation receipts,
recomputes raw occurrence identity, binds handshake identities and absolute
deadlines, checks observer window enclosure, tick arithmetic, counter read
identity/order/reset and independent sideband encoding bounds. It does not
modify missing evidence directories or claim verified origin/resources. Neither
source self-hashes nor this case verifier replace externally anchored unit and
origin audits.

**Seven new lifecycle tests passed; all 772 local regression tests passed.**
On Ohio, **21 component/lifecycle tests passed** in isolated checkout
`/tmp/qcrl-validity-lifecycle-h4HN7XAw`, Python 3.9.25. Linux process fixtures use
mocked full-lane counter values; they test orchestration, not native throttling
or observation-cost acceptance. The earlier native smoke separately verified
actual counter acquisition. No real 30,000-message case or nine-case cohort ran.

Public source remained `4dd60ba168180243f8600860330dc1afc4816ff4`; environment
SHA-256 remained `33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily timer was active, pilot/observer services inactive before and after tests.
No public source, resource, timer or collector configuration was changed.

Remaining: sampled-memory acquisition semantics and timed combined CPU/unit
receipts; strict finite Linux launcher; independent origin/unit/resource and
paired-cost auditor; launcher/audit fault tests and verification. These must
precede any actual cohort. Source-freeze commit remains local; new machinery
changes are uncommitted and nothing has been pushed or synchronized to QC.

## Follow-up: resource measurements, launcher and auditor implemented

Separate modules now provide common Linux resource samples, guarded finite
launch, pure per-phase paired gates and independently anchored origin/unit/cost
audit. The frozen v1 declaration and thresholds still validate unchanged.
Resource-method semantics are source-bound in the separate implementation receipt:
two Linux `getrusage` process high-water RSS samples per role, summed maxima,
without shared-page deduplication. They are neither current RSS nor a collection-
window peak; startup/import history can affect them. Resource sampling cost is
included in timed process CPU. Missing samples remain unknown.

The launcher requires explicit execution, Linux root, a fresh canonical
`/var/lib/qcrl-stream/receive-loop-validity-<alphanumeric>/source` checkout owned
and Git-readable by qcrl, clean tracked sources, fixed interpreter, at least
4 GiB free, matching preregistration and no prior evidence/private unit prefix.
The full bounded regression unit precedes all nine cases. Worker/observer quotas
are 100%/25%; tests use 75%. Each unit retains 512 MiB, 32 tasks, 120 seconds and
the original private/security settings. Journals/properties are retained before
stopping only its own units. Failure or public-state drift preserves evidence;
there is no automatic retry, restoration or retuning.

The auditor requires an externally learned originating inventory FILE hash and
source commit. It verifies exact file population/bytes, outer metadata copies,
source/input hashes, real case order, successful units, command/security/limits,
PID/boot/dedicated-cgroup bindings, CPU/window containment, raw occurrences and
diagnostic sidebands; it rechecks origin bytes after analysis. Nine synthetic
fixture cases cannot constitute a real cohort. Tail budgets are checked for
**each of the 12 individual phase windows**, not pooled across cycles. Missing
data and known failures are retained together. Passing self-reported metrics
never establishes independent acceptance.

### Native smoke exposed a binding-capture gap

**789 local regression tests passed**, and **38 Linux tests passed** in a fresh
private source stage. A separate eight-message `test_only` full-lane smoke then
ran native worker/observer units under the declared limits at
`/var/lib/qcrl-stream/receive-loop-validity-c5tL3jMp`. Both units exited successfully
and produced native clocks/counters and lifecycle artifacts. However, **the
smoke audit did not pass**; it is not accepted unit/resource evidence.

The smoke driver passed unit names without the required `.service` suffix.
Correcting that caller label during read-only inspection exposed the substantive
gap: systemd omitted `ControlGroup` from the retired unit properties. The
auditor correctly refused to substitute an inferred group or an actor's own
report for that missing independent binding. No units were replayed and no
limits or original evidence were edited.

Original receipt and artifacts are retained under
`.qcrl/reviews/validity-unit-smoke-20261010-vfXmD3Ky/origin/`. Externally obtained
inventory byte SHA-256:
`d0449f20e0b01f86f79137064d780b760d6a13785cb7f1e18d99598cfcd71171`.
All 16 original smoke source files were preserved in sibling `source-snapshot/`
and verified against that anchored receipt. The failed driver, failed offline
check and review status remain retained; no successful audit receipt replaced
them. Public checkout/configuration/service states were unchanged.

### Safeguard added, still awaiting native revalidation

The launcher now captures PID/boot/ControlGroup while each unit is **running**.
A source-bound handshake seals both live receipts before production collection
can begin. The observer establishes its CPU window and signals collection
readiness before the worker starts. The auditor checks live binding timestamps,
unit identity, dedicated cgroup and the linkage to the start handshake. Missing
live evidence still fails closed; a retired property is only allowed to be absent
when a genuine matching live receipt exists. Limits/security checks are unchanged.

Tests cover both missing retired properties with valid live receipts and wrong
live PID/group rejection. The original smoke lacks these receipts and **cannot
be retrospectively repaired**. Native revalidation of the new safeguard remains
required, followed by commit/source-freeze before any separately approved real
nine-case cohort. No real cohort, Git push or QC sync occurred in this step.

An internal tiny fixture can now explicitly require the same live-binding
handshake while remaining `test_only`; the CLI cannot select that fixture or
disable production binding. This makes native safeguard revalidation possible
without a real 30,000-message case. **791 local tests passed** for the live
capture/audit guard changes, before adding this additional fixture-mode test.

Final local regression: **all 792 tests passed**. Native revalidation of the
new live-binding handshake is still pending; the earlier 38-test Linux pass
and failed native unit smoke covered its predecessor, not the corrected guard.

### Corrected native handshake revalidated — October 10

A fresh private stage, `/var/lib/qcrl-stream/receive-loop-validity-cOp4utTT`,
passed **41 Linux tests** and one **eight-message, test-only full-lane smoke**.
Both live unit receipts were sealed before their collection windows. Independent
offline verification checked the binding-marker links, actual PID/boot/cgroup,
unit limits/security/commands, CPU-window enclosure, clocks/counters and all
eight raw occurrences. Both units exited successfully; only their private units
were stopped. Public checkout/configuration/service states remained unchanged.

The originating inventory byte SHA-256, obtained directly from Ohio, is
`b88edccec64377a8583aae46ab7ee46aad3195cdda1e0b87147545932f92a300`.
Offline verification matched **22 inventoried evidence/driver/result files**
and **16 preserved source files**, with exact evidence population checked before
and after analysis. Receipts and source snapshots are retained under
`.qcrl/reviews/validity-unit-revalidate-20261010-OXzsPhz7/`; the independent
receipt is `offline-verification.json`. The earlier failed smoke remains intact.

This clears the native handshake smoke gate only. It does **not** accept probe
cost, run the real nine-case cohort, or authorize public deployment/trading.
Commit/source-freeze and separately approved finite-cohort execution remain next.
No Git push or QuantConnect synchronization occurred during revalidation.
