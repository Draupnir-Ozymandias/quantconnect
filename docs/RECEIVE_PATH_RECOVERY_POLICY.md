# Opt-in bounded receive recovery — v3 foundation

`ReceiveRecoveryTracker` implements explicit `qcrl.receive_path_policy.v3`.
V1/v2 policy payloads, contracts and behavior remain unchanged. V3 is available
only through explicit low-level recorder v7 and the versioned matched synthetic
runner; it is NOT enabled in public deployments, rolling service plans, cloud
CLI or campaign execution. See [the integration contract](RECEIVE_RECOVERY_INTEGRATION.md).
The base tracker rejects a v3 contract: callers must select
the recovery tracker explicitly. The unchanged pinned WebSocket adapter accepts
the subclass; its queue/flow-control/reader behavior is not replaced.

## Recovery boundary

Each connection independently counts complete data-message callbacks and every
successful application delivery. Control frames do not consume message ordinals;
fragmented messages consume one ordinal only on final continuation. Markers stay
bounded at 64. On overflow, the identified oldest prefix drains normally, then
deliveries are explicitly unknown while complete callback occurrences continue
being counted. Unretained payloads/markers are not saved or searched by hash.
Fragment order, byte/fragment bounds and clocks remain checked during this gap.

A recovery fence requires, under the same metadata lock:

- Complete-callback count equals delivered-message count.
- No pending marker and no incomplete fragmented message.
- The latest receiver clock bracket ends before this delivery bracket begins.
- The ONLY disabled reason is recoverable marker-budget exhaustion.

The fence-closing delivery REMAINS UNKNOWN. A new alignment generation permits
only subsequently observed messages to obtain fresh markers. Each known delivery
must match its connection-scoped ordinal, text/binary type and raw SHA-256.
Identical payloads are distinct occurrences, never lookup/resynchronization keys.
Neither low queue depth, elapsed time, PONG, nor a promising payload rearms timing.
Repeated overflow yields bounded latest-episode/fence metadata; all prior episodes
remain visible in archived records rather than an unbounded tracker history.

Counters are bounded at one million messages / 64 million frames per connection.
Counter overflow, digest/ordinal mismatch, missing callback, adapter observation
failure, invalid frame/fragment metadata, clock regression or invalid clocks fail
closed until reconnect. Reconnect resets counters, pending/partial state, overflow
and generation, and rejects retired-connection callbacks. It does not reset the
observer/boot clock domain or create wire-arrival measurements.

## Conditional assurance, not wire evidence

The fence depends on the pinned adapter observing every data callback exactly
once, in library order, and its single reader reporting every successful recv
exactly once, in order. These are transport/adapter invariants, not assumptions
that counters can prove independently. A manually corrupted callback/delivery
feed can violate them, particularly in unretained duplicate-message gaps.
Do not claim arbitrary-feed self-healing, packet timestamps, lossless market data,
pure queue-wait latency or authentication from hashes. Unknown timestamps are
never reconstructed. If the adapter invariant is uncertain, reconnect is required.

Delivery v3 records bind current counts, state/generation, latest overflow and
recovery-fence provenance plus the existing raw/stamp/elapsed checks. Standalone
validation checks local consistency, not the entire history. The independent
`validate_recovery_connection` checks a COMPLETE connection's ordered deliveries
against raw messages: no missing/duplicate ordinals, counter regressions, skipped
generations, rewritten active overflow/fence, or terminal-to-aligned restoration.
Generation advancement must occur on that exact unknown fence-closing delivery.
An arbitrary archived slice is not a complete-trajectory proof.

## Verification and rollout boundary

Tests cover duplicates, multiple overflow generations, partial UTF-8 messages,
interleaved protocol controls, callbacks racing with delivery clock sampling,
malformed/forged records, truncated/duplicated trajectories, digest mismatch,
protocol/clock/counter failures, reconnect and retired callbacks. A real pinned
loopback adapter test sends 500 identical valid frames, induces exhaustion,
drains the queue, and verifies subsequent fragmented UTF-8 regains a correctly
numbered marker without a reconnect. It never changes the client queue or limits.

Before public integration, introduce explicitly compatible stream/archive and
offline-analysis versions, retain all historical v1/v2 evidence, and declare a
new matched synthetic burst comparison. Establish raw integrity, fence-trajectory
validity, actual known/unknown denominators and CPU/memory costs under the same
consumer quota. This foundation alone is not a performance improvement claim;
continuing protocol/occurrence tracking while saturated adds measurable work.
