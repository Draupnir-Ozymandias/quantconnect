# Five-minute public observation lane

Latest review: [October 6 receipt-age analysis](STREAM_FRESHNESS_REVIEW_2026_10_06.md).
The segmented pilot completed, but freshness tails require profiling before
multi-timeframe concurrency expands.
The next opt-in diagnostic is [bounded recorder profiling](STREAM_PROFILING.md).

Implemented foundation: 2026-10-05. Priority: BTC five-minute market mechanics.
Daily research remains separate; further daily-specific expansion is deferred
while this observation lane is validated. No account access or trading.

## What exists now

`execution_truth/market_stream.py` records a bounded public CLOB market stream
for both outcome tokens of one hash-verified five-minute market bundle. The
engine checks the explicit event interval, not the slug suffix. Market IDs,
condition, outcome tokens, contract and source-bundle hashes are pinned in the
plan. Version 2 records bounded batched fsync; archived v1 plans fsynced every
row. Asset and resolution semantics still require explicit review when
selecting the BTC pilot; a five-minute interval alone does not prove BTC or
compatibility with any QCRL strategy.

The public subscription requests `book`, price changes, trade-price events,
tick changes and custom lifecycle/top-of-book events through the market channel.
It contains no credentials, user subscription, order submission or cancellation.
References: [Polymarket market-channel contract](https://docs.polymarket.com/api-reference/wss/market)
and [WebSocket runtime API](https://websockets.readthedocs.io/en/15.0.1/reference/sync/client.html).
Protocol documentation was reviewed 2026-10-05. A local 25-second public wire
smoke passed: both token books, two text PONGs, one connection, 14,979 frames
and a verified 14,986-row chain. This validates basic wire interoperability,
not exchange delivery completeness or EC2 performance.

The recorder retains each text frame unchanged, including batched arrays,
unknown/malformed messages, and other-market events. Classification checks
condition and token scope without applying price deltas or inferring orders.
Recognized events are counts, not a reconstructed or verified order book.
Exchange event timestamps remain in the raw payload; local receipt UTC and
monotonic time are recorded separately. No one-way network-latency claim is made.

## Durability and discontinuity

Each NDJSON row is hash-chained with its ordinal and previous row hash. Writes
are flushed on each row. Fsync occurs every 64 records or one second, with
immediate sync at session/control boundaries and close. Idle reads also check
the one-second deadline. Power loss can lose the last unsynced batch; an
interrupted prefix remains incomplete. A fresh exclusive path is required. The header pins the
plan and raw bundle. Connection attempts, subscriptions, heartbeats, received
frames and connection failures remain explicit. The footer records stop reason,
counts and book-message assets per connection, not full-coverage success.
Preserve the referenced raw bundle separately from the stream file.

Reconnects are limited and never erase gaps or carry book baselines forward.
Limits: 600 seconds maximum, 100,000 received frames, 256 KiB per text message,
128 MiB log, three connection attempts, two-second reconnect pause. The default
requested duration is 360 seconds. Text PING is sent every ten seconds; lack
of PONG for thirty seconds triggers a recorded reconnect. Socket size/queue
limits are configured in the optional runtime. Binary/oversized messages are
not retained as normal event frames and trigger an explicit failure.

Execution may start only between thirty seconds before market start and thirty
seconds after market end. It stops at market end plus thirty seconds or its
duration/frame limit, whichever occurs first. Starting late is allowed for a
diagnostic partial capture, never relabeled as full lifecycle coverage.
No automatic settlement confirmation follows the stop.

`continuous_coverage_proven` and `orders_authorized` are always false. A socket
that stays connected is not proof that the feed delivered every event. Log
verification detects changed/reordered/truncated records and a missing footer;
a retained prefix without a footer remains an interrupted capture. It checks
record integrity, not signed provenance, exchange delivery completeness, or
semantic validity of every event. No individual queue position or hypothetical
fill is observable from this recorder.

## Operator interface

Preview without networking or a WebSocket dependency:

```bash
./synch.sh evidence market-stream /absolute/path/to/verified-five-minute-bundle.json
```

An explicit bounded capture, after installing the isolated optional runtime:

```bash
python -m pip install -r infra/stream/requirements.txt
python qcrl_execution_truth.py market-stream /absolute/path/to/current-bundle.json \
  --execute --output .qcrl/execution_truth/streams/unique-session.ndjson
```

Use a dedicated virtual environment for the runtime, not the existing daily
collector environment. Invoking its Python directly avoids accidentally using
another environment's Python through `synch.sh`. No dependency was installed
by the original foundation implementation. Verification subsequently installed
`websockets==15.0.1` in `.qcrl/stream-venv`; tests still inject simulated clocks.

Offline verification:

```bash
./synch.sh evidence verify-stream .qcrl/execution_truth/streams/unique-session.ndjson
```

Stream logs are derived local capture state, not automatically promoted into
the existing live-evidence inventory. The separate prospective discovery pilot
has now been deployed alongside the daily collector; its sync namespace is
excluded from the daily wrapper in both directions. Collection logic/timing
remain unchanged. No CloudFormation stack update or QuantConnect push occurred.
The separate discovery pilot and service packaging
are described in [the stream deployment guide](../infra/stream/README.md).
The existing minute-dispatch daily collector is not used to launch the recorder.

## Gates before rolling EC2 collection

1. Isolated runtime and bounded real public-stream smoke test; compare wire
   fields, heartbeat behavior, token scope and initial book messages.
2. Prospectively declare a small consecutive BTC five-minute cohort. Discover
   and verify exact market terms ahead of rollover; missed windows stay missed.
3. Add initial/final and periodic public metadata checkpoints, observed tick
   change handling, platform settlement follow-up, reconnect baselines and
   coverage auditing. Do not assume a daily or previously captured oracle source
   describes the new markets.
4. Add a separate supervised rolling service with bounded disk/backlog, health
   reporting and S3 upload; deploy only after verification. Preserve the daily
   service. Streaming must not block its timer or claim uninterrupted service.
5. Compare prospective five-minute mechanics across markets and time-of-day.
   Add a separate fifteen-minute lane afterward; share infrastructure, not
   signal conclusions or resolution assumptions.

The daily candle-streak signal, Binance/noon-Eastern delayed contracts and
provisional daily binding limits are not five-minute strategies. No daily
success/failure finding is transferred. Unknown execution semantics restrict
future execution modeling but do not prevent public observation.

Deployment and first-capture details are in the
[2026-10-05 deployment record](../infra/stream/DEPLOYMENT_2026_10_05.md).
