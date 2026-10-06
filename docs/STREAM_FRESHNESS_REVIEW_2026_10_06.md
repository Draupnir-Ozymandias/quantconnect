# Verified stream freshness review — October 6, 2026

## Outcome

The October 5 segmented pilot completed all three BTC five-minute lifecycles.
All 158 retained files matched S3 byte-for-byte in the subsequent read-only
review. Integrity and lifecycle completion do not establish timely delivery.
The freshness review finds material receipt-age tails even without reconnects;
expanding concurrency immediately would obscure their cause.

Pilot: `b37b70155999535dc2bd37f16218da9d1cdf4fbddf5e3d46d91e0198c987aae3`.
Captures were made by EC2 checkout `319e0a97a87498ef037302278fd9dfa967b8c569`.
The new offline analyzer was streamed through SSH for execution against retained
evidence; the deployed checkout, service, schedules and evidence were not altered.

## Measurement

`execution_truth/stream_freshness.py` verifies compressed bytes, descriptors,
row chains, raw classifications and final manifests before analysis. It measures
local UTC receipt time minus each selected-market event's explicit Unix
millisecond timestamp. Batched events are counted separately; price-change
entries within a single event are not multiplied into separate samples. PONGs
and other/unconfirmed-market events are excluded from age distributions.

Quantiles use linear interpolation at `(count - 1) * q`. Counts above 0.1,
0.25, 1 and 5 seconds are descriptive bins, not acceptance gates or a trading
policy. Missing, invalid and negative timestamps remain explicit; seconds and
microseconds are not guessed into milliseconds. Groups include event type,
connection and UTC receipt minute. Samples are event-weighted, not time-weighted.

Clock synchronization, exchange timestamp semantics, processing location and
continuous delivery are not proven. Receipt age includes any clock offset,
server generation/queueing, transport, socket queue and local reader delay;
it is **not measured one-way network latency**. UTC-minus-monotonic offset
change measures local clock consistency only, not accuracy against the exchange.
New schema documentation is not retroactive proof of historical semantics.

## Findings

Times below are Eastern on October 5; durations are seconds.

| Market / start | Timestamped events | Median | p90 | p99 | Maximum | Above 1 second |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5306891 / 6:10 p.m. | 72,537 | 0.055 | 0.212 | 3.431 | 4.188 | 3.22% |
| 5307120 / 6:15 p.m. | 195,909 | 0.121 | 1.981 | 4.035 | 4.242 | 19.95% |
| 5307198 / 6:20 p.m. | 94,701 | 0.110 | 4.816 | 5.957 | 6.146 | 29.97% |

Every selected event had a valid timestamp; none had negative age. The analyzer
found no timestamp regression within connection/event-type/asset-set groups.
Those facts do not establish delivery completeness or a global event ordering.

- The middle market had one uninterrupted observed connection, but almost
  one-fifth of its events were over one second old. Reconnects alone therefore
  cannot explain the tails.
- At 6:18 p.m. the middle market received 54,272 frames in that receipt minute;
  selected-event median age was 1.405 seconds and p90 was 3.411 seconds.
- The last market's first connection had median age 3.695 seconds. After
  reconnecting, its second connection still reached age 5.418 seconds.
- The last market had 8,841 events above five seconds (9.34%). Book snapshots,
  best-bid/ask events and trade-price events also had multi-second tails, not
  only price changes.
- Maximum local wall-minus-monotonic offset changes were 1.9, 11.3 and 59.9 ms.
  These changes are much smaller than the multi-second tails, but do not
  establish exchange/local clock agreement.

Reconnect recovery from detected disconnect to both fresh token books was
2.467, 2.438 and 2.442 seconds. Each includes the deliberate two-second pause.
All three recorded received/sent close code 1013. Fresh snapshots do not recover
intervening updates. Retained results still say `continuous_coverage_proven=false`.

## Reproducibility

Run locally on downloaded, finalized stream directories, or use the observer's
isolated Python runtime with the analyzer available:

```bash
python3 -m execution_truth.stream_freshness /absolute/path/to/market/stream
```

The command prints a source-bound, hashed `qcrl.stream_freshness.v1` JSON report
without modifying the evidence. Twelve synthetic tests cover timestamp units,
negative/missing/invalid ages, quantiles, both-token reconnect recovery, clock
changes, monotonic validity, event budgets, legacy rejection and corruption.
The full local suite passes: 388 tests. `git diff --check` also passes.

Derived reports are retained locally under ignored
`.qcrl/execution_truth/stream_freshness/` (not inventory promotion):

| Market | Report SHA256 |
| --- | --- |
| 5306891 | `171ec2e6e37808b3741dbaa8111b77eb2860e521cd94fccfcc882665ba3235e7` |
| 5307120 | `95f91c5a6f19edc08b5bb8b58828f07a232e9832251eefeb178039f3c1cee4de` |
| 5307198 | `b075d51e9fbc1c5b1641181bd1ffc5375ddd66566706ec3845aa5a0701ed105f` |

## Next gate and bounded expansion proposal

First add bounded timing/resource telemetry and run another prospectively locked
five-minute profiling cohort at unchanged concurrency and storage limits:

1. Measure monotonic reader-loop, hashing/write, fsync and segment-seal durations;
   distinguish receipt before recording from time spent recording afterward.
2. Sample process CPU, memory and available cgroup CPU-throttling counters;
   preserve absent metrics as unavailable rather than zero.
3. Correlate receipt-age bursts with local work and throttling. The present
   artifacts cannot attribute the delay to CPU, storage, upstream or networking.
4. Keep current raw evidence and its semantics intact; instrumentation must be
   versioned and bounded, with tests before deployment.

After that review, first expand to **one BTC five-minute stream plus one BTC
fifteen-minute stream**, maximum two simultaneous sockets, in a declared shared
six-minute observation window with unchanged per-stream byte/frame budgets.
The fifteen-minute stream would intentionally be partial, not falsely labeled
a completed lifecycle. Review live interval, resolution source, exact terms,
token identities and phase separately for each market before locking it.
Keep the existing daily collector unchanged. Subsequent hourly, four-hour and
daily stream samples should be bounded observations too, with their own terms
and phase labels; no daily research conclusion transfers to intraday markets.

The current recorder/rolling orchestrator intentionally enforce five-minute
contracts. Implement a separately versioned partial-window observation contract
and compatible health semantics before expanding; do not simply weaken the
five-minute guards or add guessed slugs. No prospective capture is scheduled by
this document. No hardware, budget, IAM, credentials or trading changes occurred.
