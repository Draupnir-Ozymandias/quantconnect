# Receive-v3 recovery foundation verification — October 8, 2026

Implementation revision: `688118ae943551b88d2f759f17d2514b611d462f`.
See [the explicit recovery contract](../../docs/RECEIVE_PATH_RECOVERY_POLICY.md).
The operator approved the next step after the v2 burst audit demonstrated that
callback timing stayed unknown for the remainder of a saturated connection.

The new opt-in tracker retains at most 64 markers and counts all complete
message callbacks while the identified prefix drains. Recovery requires equal
callback/delivery occurrences, empty marker/fragment state and receiver-clock
completion before the delivery bracket, under its metadata lock. The delivery
closing that fence stays unknown. Only subsequent occurrences may carry timing
under a new generation. Known markers bind occurrence, type, raw hash and clock.
Errors other than marker-budget exhaustion remain terminal until reconnect.

The fence is conditional on the pinned adapter observing every callback once
and its single reader delivering every recv once, in order. It is not arbitrary
feed repair, a hash-search heuristic, a queue-depth trigger or wire evidence.
Whole-connection validation additionally checks ordered occurrence progression,
generation/fence transitions and terminal-state persistence against raw messages.

## Verification

All **523 local tests** passed in 14.096 seconds. The suite includes 16 new
recovery tests and all existing v1/v2, collector, campaign and sync regressions.
A real pinned localhost WebSocket test induces overflow with 500 identical
messages, preserves all raw deliveries, drains the connection and verifies a
subsequent fragmented UTF-8 message regains marker occurrence 501 without a
reconnect. Tests cover repeated overflow, incomplete fragments, controls, late
callbacks, duplicates, protocol/clock/counter failure, retired callbacks,
malformed/rehashed records and omitted/duplicated/forged trajectories.

Linux verification used a NEW independent diagnostic clone at
`/var/lib/qcrl-stream/receive-recovery-foundation-20261008-F0JKrB/source`.
The existing runtime remained pinned to websockets 15.0.1. All **523 tests**
passed in 38.782 seconds, with one expected Python-version inventory skip.
Retained successful unit properties confirm qcrl user/group, 75%-of-one-CPU,
512 MiB memory, 32 tasks, 120-second maximum, Result=success and exit status 0.
The unit consumed 26.969 CPU-seconds; that is TEST-SUITE work, not a recorder
throughput/overhead result. The completed diagnostic unit was stopped only
after its successful exit and evidence recording; no recurring unit was installed.

The initial test-unit setup was blocked before Python started with 200/CHDIR:
the freshly created diagnostic parent directory was root-only. Its failure
journal/properties were preserved. Only that explicitly named directory's group
and traversal permissions were changed to root:qcrl/0750; the corrected finite
test unit then passed. No code failure or public capture retry was involved.

Local ignored evidence:
`.qcrl/reviews/receive-recovery-foundation-20261008-qX86Gv/`.
It includes successful/failed unit journals/properties, test-source revision,
source-file hashes and pre/post collector revision/environment hashes. The four
implementation/test/protocol source hashes matched local files exactly after
retrieval. Full diagnostic source and Git objects remain on the data volume.

## Deployment boundary and next step

Deployed observer HEAD remained EXACTLY
`4dd60ba168180243f8600860330dc1afc4816ff4` before/after verification.
Observer environment SHA-256 remained
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
The daily timer remained active; public observer remained inactive. Git objects
were fetched for the isolated clone but deployed files/HEAD were NOT updated.
No public collection, cloud/infrastructure/resource change, credential, trading,
Ireland update or QuantConnect sync occurred.

Public collector/CLI/plan versions still reject receive v3; historical v1/v2
policy payloads and behavior remain unchanged. This is a tested FOUNDATION,
not a deployed fix, a matched burst comparison, or a measured performance win.
Continuing callback/protocol counting while saturated has costs not benchmarked
here. Next: explicitly version compatible recorder/archive/offline-analysis
integration, then prospectively declare a matched synthetic burst comparison
under the unchanged consumer quota. Validate raw identities, complete fence
trajectories, known/unknown coverage and CPU/memory before public deployment
or recorder-stage cost controls.
