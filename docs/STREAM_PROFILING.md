# Opt-in public recorder profiling — October 6, 2026

Purpose: discriminate local reader/storage pressure from upstream or other
delay after the verified October 5 captures showed receipt-age tails of 4–6
seconds. Existing evidence cannot attribute the delay, and a successful capture
does not establish timely delivery. No hardware upgrade or concurrency increase
is part of this profiling rollout.

## Version and bounds

Profiling is opt-in: `qcrl.btc_5m_rolling_pilot.v3` carries an exact
`qcrl.stream_profiling.v1` policy. Existing v2 declarations remain byte-for-byte
reproducible with profiling absent. The segmented v3 stream envelope/raw row
schema is retained; a profiled stream header explicitly pins the policy. The
normal validator reconstructs and checks the entire plan, including that policy.

Profile samples are hash-chained control rows every five seconds, plus bounded
initial/terminal samples. Maximum: 121 samples per stream. No per-frame resource
file reads, separate telemetry thread or indefinite service restart is added.
Existing byte/frame/spool/CPU/memory caps, two market workers, immutable S3
segments, failure-aware health and independent metadata checkpoints remain.

Every profiled frame adds local UTC and monotonic timestamps immediately after
`socket.recv` returns and before classification. Existing row receipt fields
retain their previous meaning (taken inside append, after classification).
These are application socket-return times, not kernel packet arrival times.
They do not prove when the exchange generated or transmitted an update.

## Metrics

- Monotonic wall-duration counts, totals, maxima and fixed histogram buckets for
  successful/idle receive waits, classification, append, encoding/hash, gzip
  writes, flush/fsync, and segment sealing.
- Buckets: <=1, 5, 10, 50, 100, 500 and 1,000 ms, then >1 second.
- Append includes nested encoding/compression/fsync/sealing; do not add
  overlapping stages to infer elapsed time or CPU consumption.
- Receive wait includes normal waiting for data; it is not busy CPU time.
  Failed receive waits are not included in duration totals; failures remain
  explicit connection-gap records.
- Cumulative process user+system CPU seconds and current Linux RSS bytes.
- Supported cgroup v2 cumulative `cpu.stat` counters, including periods,
  throttled periods and throttled microseconds, where readable.
- Missing RSS/cgroup readings are null with unavailable labels, never zero.
  Process readings cover both market threads; cgroup readings cover the whole
  service, including helper subprocesses. Shared readings must not be summed
  across streams. Differences require matching scope and counter continuity.

Each sample covers timings since the preceding sample; its own append enters
the next interval. The terminal sample precedes the footer and final close, so
final footer/segment-close costs are not claimed to be fully sampled. The
instrumentation itself has overhead, including a small extra fsync per sample.
An observed association is not proof of causation or a network latency measure.

## Verification and deployment procedure

```bash
python3 -m unittest discover -s tests -q
```

Commit and push reviewed observer changes before fetching/pinning that exact
revision in `/opt/qcrl-stream`. Preserve `/opt/qcrl` and the daily timer. Run
EC2 tests and a bounded smoke in a dedicated writable diagnostic directory:

```bash
sudo -u qcrl /opt/qcrl-stream/venv/bin/python \
  /opt/qcrl-stream/infra/stream/smoke.py --profile
```

Then declare three future consecutive BTC five-minute windows, leaving enough
lead time for installation/review (not simply the minimum 45 seconds):

```bash
sudo /opt/qcrl-stream/venv/bin/python -m execution_truth.rolling_stream declare \
  --first-start FUTURE_ALIGNED_EPOCH --markets 3 --profile \
  --output UNIQUE_PLAN_PATH
sudo /opt/qcrl-stream/venv/bin/python infra/stream/install.py \
  --plan UNIQUE_PLAN_PATH --bucket VERIFIED_BUCKET --replace-plan
sudo systemd-analyze verify /etc/systemd/system/qcrl-stream-pilot.service
sudo systemctl start qcrl-stream-pilot.service
```

The installer preserves the prior environment and rejects replacement while
the observer is active. Missed windows stay missed. Verify start/stop state,
samples and frame timestamps, manifests, both token snapshots, actual postclose
checkpoints, and final S3 bytes. Capture completion and profiling results are
separate gates; no collection result is asserted before the pilot finishes.

Public metadata and market streams only: no account access, orders, secrets,
IAM/firewall changes, QuantConnect push or recurring timer is introduced.
