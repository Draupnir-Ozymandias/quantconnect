# Isolated compact recorder integration — 2026-10-09

## Result and scope

The compact transport now has a separate recorder fixture lane in
`receive_loop_compact_lane.py`. Archive and sideband linkage passed on normal
and reconnect fixtures. Failure paths preserve evidence and fail closed rather
than manufacture successful attribution. This is functional verification, not
a performance benchmark, overhead acceptance, public deployment, or cohort run.
The previous six-case overhead rejection remains in force.

The application adapter inherits `ObservedSocket.recv`, `queue_snapshot`,
`send`, and `close` unchanged. The compact transport permits a private parent
extension only if its constructor, receive loop and close implementation retain
the pinned native methods. Its outer dispatch bracket includes the existing
v3 recovery frame observation. A thin recorder boundary translates native
transport exceptions into the recorder's reconnect errors; idle timeouts remain
idle timeouts. Native limits and the scoped 128-marker policy are unchanged.

## Independent verification

The new envelope schema is `qcrl.receive_loop_compact_fixture_sideband.v1`;
verification results use `qcrl.receive_loop_compact_fixture_verification.v1`.
The envelope binds the integration sources, stream specification, original loop
contract, final archive record and each connection's honest compact transport
sideband. No reference/model envelope is relabeled or persisted as candidate
evidence. Existing archive, recovery, reference and model validators are unchanged.

Verification checks compressed/sealed archive integrity and record/hash chains
first, then source/scope bindings, successful connector outcome, sideband shape
and ordering, callback ordinal ranges and receive-clock containment. Every
archived connection must have exactly one sideband and the delivery denominator
must agree with the archive. Duplicate raw payloads remain separate occurrences;
linkage is by connection and frame ordinal, not payload equality. A different
archive containing the same payloads cannot borrow the original sideband.

Completed observation, successful connection, completed recorder bound, local
timing eligibility and attribution availability remain separate concepts. A
storage-limit footer is valid partial evidence, not successful recorder completion.
All benchmark, overhead-acceptance, public-rollout, wire-arrival and trading
claims remain false. The transport component's recorder-integration flag stays
false; linkage evidence lives in the separately verified recorder envelope.

## Retained fixture audit

Fresh ignored review directory:
`.qcrl/reviews/compact-recorder-integration-20261009-pkcdjiha/`.
It contains the original contract, five sealed streams, summaries, persisted
envelopes, independently reread verification results and file-byte SHA-256 maps.
The 47 integration source files were also retained with their declared hashes.

Audit SHA-256:
`763d36e63c6ea656841ddb06d7f3c1b4c7c54162e1223fbbb8101c9c030a88eb`.

| Fixture | Deliveries | Linked | Unknown | Incomplete sideband | Attribution |
| --- | ---: | ---: | ---: | ---: | --- |
| Normal | 5 | 5 | 0 | 0 | Available |
| Reconnect, two connections | 5 | 5 | 0 | 0 | Available |
| Observer clock fault | 5 | 0 | 0 | 5 | Unavailable |
| Recovery tracker fault | 5 | 0 | 5 | 0 | Unavailable |
| Storage quota | 2 | 2 | 0 | 0 | Unavailable: storage limit |

These are tiny correctness fixtures, not a measured market/cohort population.

## Failure and regression tests

Fourteen new tests cover inherited methods/private-parent guards, duplicate and
fragment linkage, reconnect populations, observation and tracker faults,
primary write errors with secondary cleanup faults, snapshot errors, quotas,
cross-archive borrowing, rehashed source/spec/connection/callback/time tampering,
and compressed archive corruption. Application-delivery telemetry failure
retains five raw/hash-bound failure records, but the existing v3 archive validator
refuses verification because the recovery trajectory is unavailable. No envelope
is returned on that path. A storage write exception retains a sealed partial
archive without a terminal session record and retires the receiver; it likewise
does not return a success envelope.

Final verification: **673 local tests passed** on Python 3.14.6; **64 Linux
candidate/reference tests passed** on Python 3.9.25 and websockets 15.0.1, in a
fresh Ohio temporary checkout. Linux/local source hashes agreed:

- Recorder: `5a4985436f49676ff706374b9d03d06ef659f38333e1c2570f6e3cfc1ab80c68`.
- Transport: `adabcf0acc30b194b8c2f034ddef96a6ac1829a04e782b0c4d87fcd9a710a951`.
- Tests: `fba7208d80fc0ba28cf21dfc45353e7e45814f91fdce8790db2eb0d077ffdfc1`.

Deployed collector configuration stayed unchanged:
`/etc/qcrl-stream.env` SHA-256
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily collector timer was active; pilot/observer timers were inactive. No
infrastructure, timer, quota, public collector, trading or QuantConnect changes
were made. This implementation remains local and uncommitted at this handoff.

## Next gate

Commit/source-freeze this candidate, then prepare a distinct bounded overhead
declaration and candidate worker/launcher before executing anything. Reuse the
fixed workload, limits and acceptance thresholds, not the rejected cohort's
artifacts or implementation identity. CPU/allocation model improvements and
functional linkage success do not establish full-recorder latency or resource
acceptance. A new cohort still needs independent origin/resource and archive
verification before any advancement decision.
