# Separate BTC five-minute observer pilot

Current segmented deployment:
[2026-10-05 deployment record](DEPLOYMENT_SEGMENTED_2026_10_05.md).
Latest opt-in profiling deployment:
[2026-10-06 deployment record](DEPLOYMENT_PROFILING_2026_10_06.md).
Latest controlled follow-up:
[deferred verification deployment](DEPLOYMENT_DEFERRED_2026_10_06.md).
Prior follow-up:
[Ohio watchdog activation](DEPLOYMENT_WATCHDOG_2026_10_06.md).
Current geographically synchronized pilot:
[Ohio–Ireland deployment record](DEPLOYMENT_TWO_SITE_2026_10_06.md).
Earlier single-file history and troubleshooting remain below.

Public GETs and public market-channel WebSockets only. No Polymarket credentials,
account endpoints, orders or cancellations. Daily collection logic/timing is
unchanged; installation backs up its S3 wrapper and excludes `streams/*` in both
sync directions to prevent two producers writing observer objects. The same
exclusions are recorded in CloudFormation bootstrap for future instances.

The first rollout is a **six-market prospective pilot**, not an indefinitely
restarting daemon. Declare the exact consecutive windows ahead of collection;
missed windows remain missed. Pin and push the reviewed code before deployment.
The host overlay is not yet bootstrapped by CloudFormation: after an instance
replacement, reinstall explicitly with a new future plan. Do not replay old plans.

## Verification

```bash
python3 -m venv .qcrl/stream-venv
.qcrl/stream-venv/bin/python -m pip install -r infra/stream/requirements.txt
python3 -m unittest discover -s tests -q
.qcrl/stream-venv/bin/python infra/stream/smoke.py
```

The smoke is 35 seconds on the current market and checks both token snapshots,
two text heartbeat replies, a single connection and the persisted hash chain.
It is a partial diagnostic capture, never proof of lossless delivery.

## Install on the existing collector (operator procedure)

Verify stack outputs and SSH host identity first. Inspect the daily timer and
available disk; verify public HTTPS/WebSocket connectivity. These commands assume
Amazon Linux 2023 and the existing `qcrl` user and AWS CLI. Use Session Manager
if the declared SSH ingress CIDR no longer matches the operator's network.
Do not broaden SSH ingress to the internet.

Create an isolated checkout; replace `REVIEWED_COMMIT` with a full pushed SHA:

```bash
sudo git clone https://github.com/Draupnir-Ozymandias/quantconnect.git /opt/qcrl-stream
sudo git -C /opt/qcrl-stream checkout --detach REVIEWED_COMMIT
sudo python3 -m venv /opt/qcrl-stream/venv
sudo /opt/qcrl-stream/venv/bin/python -m pip install -r /opt/qcrl-stream/infra/stream/requirements.txt
sudo install -d -o qcrl -g qcrl -m 0700 /var/lib/qcrl-stream
cd /var/lib/qcrl-stream
sudo -u qcrl /opt/qcrl-stream/venv/bin/python /opt/qcrl-stream/infra/stream/smoke.py
```

Run the smoke from a writable diagnostic directory (e.g. a dedicated directory
under `/var/lib/qcrl-stream` owned by `qcrl`); its output is relative to the working
directory. Do not run from the root-owned code checkout.

Choose an aligned future epoch **at least 45 seconds ahead**, allowing installation
and review time. Six markets span thirty minutes; the final bounded settlement
checkpoint extends beyond the trading windows. No launch is automatic:

```bash
cd /opt/qcrl-stream
sudo /opt/qcrl-stream/venv/bin/python -m execution_truth.rolling_stream declare \
  --first-start FUTURE_ALIGNED_EPOCH --markets 6 --output /tmp/qcrl-stream-plan.json
sudo /opt/qcrl-stream/venv/bin/python infra/stream/install.py \
  --plan /tmp/qcrl-stream-plan.json --bucket VERIFIED_STACK_BUCKET
sudo systemd-analyze verify /etc/systemd/system/qcrl-stream-pilot.service
sudo systemctl start qcrl-stream-pilot.service
sudo journalctl -u qcrl-stream-pilot.service -f
```

Inspect `/etc/qcrl-stream.env` before starting. It has only public collection
configuration and the existing artifact bucket, **not** the probe secret ARN.
The shared EC2 role's existing `runtime/*` permission permits S3 replication;
no IAM expansion or new inbound port is needed. Do not add a recurring timer
until this finite pilot has been reviewed.

## Guardrails and verification after launch

See [segmented capture](../../docs/SEGMENTED_STREAM_CAPTURE.md) for the current
v3 recorder, failure-aware health and checkpoint policy. Legacy budgets below
describe the original single-file pilot; they are retained as deployment history.

Two market workers permit overlap at rollover. Each market re-discovers its exact
slug, verifies both token identities, the explicit 300-second interval, open
state, Chainlink source and exact reviewed description hash. Changed terms fail
closed. Initial raw bundles, periodic metadata every sixty seconds, final metadata
and one checkpoint at end plus 120 seconds are retained. A pending settlement
remains pending; the follow-up does not promise final resolution.

Discovery retries have five-second HTTP timeouts and stop shortly after the
locked window opens. Per-stream limits remain 100,000 frames / 128 MiB; quota
stops are explicit partial captures. Spool budget is 2 GiB with two-stream reserve
and 1 GiB minimum free space at launch of each worker. No evidence is deleted to
recover space. Systemd adds memory/CPU bounds and does not automatically restart
an interrupted cohort. Existing stream headers prevent replay after restart.

S3 sync runs every sixty seconds and after normal completion, using encryption,
the versioned `runtime/streams/pilot-HASH/` prefix and **no deletion**. Active
NDJSON uploads are provisional prefixes; verify downloaded row boundaries,
hash chains and footers before use. An abrupt process kill can leave a newer local
tail not yet uploaded. Replication failures appear in the service journal.
These uploads are not evidence-inventory promotion.

Verify each `result.json`, chain verification, stop reason, initial books on
each connection, reconnect gaps, checkpoint failures and S3 object contents.
Confirm `qcrl-collector.timer` remains active. `continuous_coverage_proven` remains
false even for apparently clean sessions. Raw tick-change events are preserved;
book reconstruction and exchange delivery-completeness auditing are still future
work. No queue, fill or profitability inference follows from the pilot.

## Foundation verification on 2026-10-05

For synchronized observer comparisons, use the
[versioned offline cross-site analyzer](../../docs/CROSS_SITE_STREAM_ANALYSIS.md).
It verifies source/stream/result provenance and preserves duplicates, gaps,
incomplete lifecycles and unknown clock/resource measurements.

Receive-path instrumentation is separately opt-in: see
[the versioned contract and integration notes](../../docs/RECEIVE_PATH_TELEMETRY.md).
Pilot declarations require `--receive-path --profile --defer-verification`.
This creates pilot v5 / stream v4 without changing legacy defaults. Do not deploy
or schedule this mode until its bounded EC2 smoke is separately authorized;
the current cross-site v1 analyzer intentionally rejects the new stream schema.

Explicit `--receive-policy v2` selects the separately versioned
[bounded drain-before-unknown policy](../../docs/RECEIVE_PATH_DRAIN_POLICY.md)
(pilot v6 / stream v5). V1 stays the default; local verification is not EC2
deployment or authorization for a new capture.

Local 25-second live smoke passed (market 5291768): 14,979 frames, both token
books, two PONGs, one connection and a verified 14,986-row hash chain. Raw artifacts
are retained in ignored `.qcrl/execution_truth/streams/smoke-1791221710/`.
Prospective discovery also verified markets 5292498 and 5292787 (17:50 and
17:55 UTC), including exact intervals, source/description and both token books.
The upcoming-book missing last-price edge case now records unknown explicitly.
All 357 local tests and all 43 promoted evidence artifacts pass verification.
EC2 deployment subsequently proceeded after the operator disabled the VPN and
independently confirmed the SSH host fingerprint. See
[the deployment record](DEPLOYMENT_2026_10_05.md) for the pinned revision,
EC2 smoke, namespace isolation, locked cohort and first-capture verification.
