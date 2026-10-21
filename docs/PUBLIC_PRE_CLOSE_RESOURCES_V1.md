# Prospective pre-close resource publication v1

Declared October 21, 2026; **offline implementation only**. Historical application
FAIL, v6 partial/unresolved, original UTC/RSS widths and every resource/capture
budget remain unchanged. This is evidence preservation, not a new acceptance
badge, graceful-close claim, observer optimization or public-capture authorization.

Policy identity `qcrl.public_preclose_resources.policy.v1`, SHA-256:
`97182fefdef0ebd4e5007a8aed416fc13e189abb52c6218f3de252fddb4daa73`.
A regression pins this literal hash. The existing stop/publication/recovery
policies and v5/v6 plan identities are unchanged. A **new** source/runtime freeze
must explicitly contain `resource_publication_policy_sha256` with this exact hash;
absence preserves legacy behavior, and a malformed/unknown value fails before
resource reads or capture. `make_freeze(..., preclose_resources=True)` binds the
extension into the freeze hash. It grants no execution authority and does not
turn an expired v6 target into an executable new target.

## Ownership, ordering and envelope

The acquisition owner follows the existing recorder path through end acquisition,
archive sealing, completion witnesses and the acquisition checkpoint. The new
checkpoint additionally declares the resource-publication policy. Its original
literal `observer_thread_alive=true` remains a checkpoint-schema convention,
not an observed thread-state sample.

Only after that checkpoint is published does the acquisition owner set the
existing observer's stop event and join its thread for **at most three seconds**.
It checks liveness once for the component. If the thread has exited, it retains
a deep copy of the returned result, including every original row/error/missed
slot. If still live, `resources=null` and `observer_thread_alive=true`: no mutable
prefix is inspected or copied. An observer exception retains the existing bounded
error. A returned result does not imply a complete observation window or valid
readings. Resource qualification remains null until separate original validation;
component linkage never changes the original gates.

The worker publishes one `preclose-resources.json` via the existing exclusive
pending/link/fsync machinery, then the original recorder starts final close.
No publication retry, second join after a pre-close join, signal handler, extra
observer, diagnostic stream, observer read retry or catch-up is added. If the
pre-close callback is never reached, the worker's original final stop/join path
remains. Final `consumer.json`, if reached, references the component hash. A
publication fault remains in the recorder's error/close-errors; a visible file
with pending publication state is not treated as a completed component, even
when final consumer is absent. Partial/pending bytes are retained on failure.

The existing **90-second acquisition/publication process guard stays armed**
through the stop/join and component write. The separate five-second final-close
guard, library `close_timeout=5`, default SIGTERM behavior and 240-second unit
bound are unchanged. There is no newly reserved time or guarantee that observer
return, component publication or final cleanup will finish. Guard firing still
wins cancellation and remains a fault when a mocked kill permits execution to
continue in tests. Abrupt termination can still leave only partial evidence.

This deliberately requests observer stopping **before cleanup**, rather than
after cleanup. The observer checks stop after its current row: an in-progress
wait/read can therefore finish on the original grid after the request; no new
sampling point is inserted. Terminal rows that would previously have occurred
only during cleanup may be absent. If a wait/read does not return within the
join, the pre-close component remains unavailable even if the observer returns
later and final consumer subsequently retains its result. No later overwrite of
the earlier component or inference of missing samples is permitted.

## Work placement, storage and verification

No new clocks, file access, locks, parsing or allocations are placed inside
application-return UTC brackets or RSS read brackets. The new stop/join, copy,
completion-file hash, JSON size/hash computation, spool checks and durable
publication happen outside those operations, **after acquisition**. The observer
may still finish an existing scheduled operation while the owner waits. Added
work still consumes inclusive CPU, memory, storage and wall time under the old
limits; no incremental-overhead or Linux timing claim follows from local tests.
The completion digest requires one bounded completion-file read (original cap
32 MiB); serialization/copy cost scales with the existing bounded observer result.

The component adds at most **4 MiB**, including its hash/newline, within the
existing 64-MiB auxiliary allowance and 1-GiB spool cap. The existing storage
guard is checked before and after publication. JSON rejects NaN/Infinity before
publishing. No original storage/resource limit, 60,000-text cap, acquisition
budget or measurement semantics changes.

Bindings cover checkpoint hash, completion-file hash, case (which binds freeze),
full available process/boot identity, epoch, domain, original resource-plan hash
and prospective publication-policy hash. Final consumer must reference the exact
component; checkpoint-only reporting can retain it with close still unverified.
Independent acquisition/archive/completion linkage remains a prerequisite. A
bad/missing resource component yields an explicit component error without erasing
independently linked raw counts or promoting coverage. Pending/symlink/oversize,
changed identity/epoch/domain, policy, plan, completion, checkpoint or final
reference are refused. Hash linkage and completed publication are distinct from
original resource validation and independent producer-origin attestation.

No final consumer means no final cleanup-return evidence. Even a final library
close return does not independently prove a graceful peer handshake. Neither
resources nor close can convert an early frame-cap exit into scheduled completion.
The five v6 UTC violations, missing feed activity, missing final v6 resource
rows and unknown SIGTERM sender remain unchanged and cannot be reconstructed.

## Local verification and smallest prospective native validation

Final local full suite: **1,298 tests passed in 173.834 seconds** with
`PYTHONPATH=tests .venv/bin/python -m unittest discover -v`; final focused suite:
**102 tests passed in 22.285 seconds**, including14 new test methods with fault/
linkage subcases. The initial default-path discovery retained its existing bare-
import error; no tests were changed to suppress it. Python3.9 grammar parses
locally; this is not execution on Python3.9.

Local production-worker/recorder tests cover completed observer results,
stop-delivered results, a still-live observer, actual observer clock exceptions,
invalid clock/readings and read faults, publication/link/directory-fsync faults,
linkage mutations, guard/stop races, legacy behavior and a real process-guard kill
while close is blocked. Invalid/unavailable results remain unqualified. The large
60,000-frame regression remains process-isolated. Test results belong in HANDOFF;
they are Intel macOS evidence, not installed Linux/resource/public acceptance.

The smallest useful next native validation is **one controlled blocked-close
worker case**, reusing
`tests.test_public_preclose_resources.PrecloseResourceTests.test_real_process_guard_kill_during_close_keeps_component_and_no_final_consumer`.
It runs the actual worker/recorder/persistence/publication code with synthetic
transport and resource fixtures, then deliberately blocks final close; the real
five-second SIGTERM guard must terminate the child. No TCP server or public feed
is needed to answer this publication question. This narrows the earlier proposed
loopback case to its concrete failing requirement; it adds no diagnostic framework.

Exactly one invocation, no retry/replay/extra case. Expected outcome is a killed
child, independently linked archive/completion/checkpoint/resource component,
missing final consumer, close unverified and no combined acceptance. Refuse
pending/malformed/missing linkage; preserve every partial file on failure. No
observer timing/resource acceptance, reconnect, venue completeness or trading
claim follows. The test's mock Linux reader/virtual clock do not validate Linux
resource measurement or the public adapter.

Before execution approval, a separate executable packet must bind a committed
source inventory and fresh read-only installed-runtime evidence; declare a fresh
private namespace, retained temporary-root handling, one-shot launch/claim and
independent copy/hash audit, under the existing private resource limits. Parent
runtime must bound the single test while preserving the deliberately killed
child's files; test assertions are not a replacement for independent observation.
There is no such approved native packet, stage, scheduler or launch in this
implementation milestone. No public recording or cohort is proposed.
