# Opt-in per-connection freshness diagnostics

The new lane declares `qcrl.btc_5m_rolling_pilot.v7` and
`qcrl.public_market_stream_spec.v6`, with the embedded
`qcrl.connection_freshness_policy.v1`. Legacy declarations and defaults remain
unchanged. This is instrumentation only: the five-second event-age threshold,
ten-second stale-flow watchdog, retry delays, connection allowance, receive
policy and CPU/memory/storage limits are not changed.

To declare, but not start, a separately authorized future cohort:

```bash
python -m execution_truth.rolling_stream declare \
  --first-start FUTURE_ALIGNED_EPOCH --markets 3 \
  --profile --resilient --defer-verification --receive-path \
  --receive-policy v2 --freshness-telemetry --output NEW_PLAN.json
```

Freshness diagnostics require both receive instrumentation and resilience.
The new declaration flag is opt-in; existing plans cannot be silently upgraded.
No EC2 deployment or live capture is authorized merely by creating this plan.

## Retained measurements

Each subscribed connection gets an independent tracker, reset rather than
carried over on reconnect. It retains initial token-book timestamp witnesses,
first nominally fresh price updates per token, last fresh event, latest
timestamped event and stale-flow onset/clearance. Timestamp ages are relative
to the already recorded application-delivery clock; a callback-age witness is
separate and null when the receive marker is absent. Callback timing eligibility
is explicit. Missing/invalid/future timestamps and absent delivery stamps remain
unknown counters, not fresh observations. Unknowns do not clear stale suspicion.

Only selected `book` and `price_change` events count. A mixed message containing
a fresh relevant event clears diagnostic stale suspicion, matching the existing
watchdog rule. This diagnostic tracker does not drive reconnects. Its delivery
clock is not the watchdog's exact evaluation clock, so recorded onset times are
diagnostic witnesses, not claims of identical sub-millisecond control timing.

`connection_freshness` records are sampled every five seconds, plus subscription
and connection-end snapshots, with at most 123 samples per connection. The last
eight onset/clearance transitions are retained; omitted earlier transitions are
counted explicitly. Samples are hash-bound. Storage-quota failures may prevent
a final snapshot; verification reports missing final snapshots explicitly rather
than claiming complete diagnostics. No evidence is deleted to make room.

Fresh token snapshots and fresh updates do not establish current validity of
every book level, delivery completeness, wire latency, fills or profitability.
`state_freshness_proven` and `orders_authorized` stay false.

## Structured close diagnostics

For this opt-in lane, gap records retain `qcrl.close_diagnostics.v1`: bounded
exception type, received/sent close codes, received-before-sent when available,
and watchdog versus transport/other origin. Up to four explicit exception causes
are inspected. Server reason text is not copied. Missing codes remain null;
codes are never inferred from a string such as `ConnectionClosedError` or
`rcvd_code=1013`. Watchdog-triggered gaps cannot claim received/sent close codes.
The diagnostic does not establish a remote cause or geographical explanation.

## Offline verification and analysis

Segment verification replays each freshness sample from the verified raw frames
and receive stamps. Rehashing altered counters or witnesses is insufficient to
pass; source bindings, connection reset, sample indices, chronology, bounds,
final snapshots and structured diagnostic types are checked separately.

The receive-phase analyzer selects `qcrl.receive_phase_analysis.v2` / policy v2
for stream v6, retaining the bounded raw-replayed freshness samples and close
diagnostics. The same CLI and explicit pilot-root binding apply. Older stream
v4/v5 inputs still produce the original v1 analysis/policy and hashes. Neither
analysis turns failed/partial lifecycle verdicts into successful captures.

Tests cover brief stale clearance, sustained deterioration, unknown/future
timestamps, callback versus delivery age, token witnesses/reset, bounded history
and samples, real-library close objects, rehashed policy/sample tampering,
missing final snapshots, quota-limited diagnostics and recorder/analyzer replay.
Deployment and overhead calibration remain separate next steps.

Local verification on October 7, 2026: all 501 repository tests passed,
including localhost WebSocket tests. The three archived Ohio cohort windows
were independently re-analyzed; all three original v1 analysis hashes matched
exactly. No live endpoint or EC2 instance was contacted for this implementation.

Subsequent authorized capped Linux verification also passed all 501 tests with
one expected Python-version skip, plus a real-adapter localhost archive check.
See [the verification record](../infra/stream/VERIFICATION_FRESHNESS_LINUX_2026_10_07.md).
The idle Ohio checkout is updated; its old plan and failed cohort state remain
unchanged, and no public freshness capture has been started.
