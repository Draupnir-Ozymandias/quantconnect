# EC2 BTC five-minute pilot deployment — 2026-10-05

## Final deployment state

The repaired observer is active/running at
`55ae4adc1b2c85081f44f0c52789a7303d86203b`. The replacement six-market plan is
`86fd6c8ee5eb98ecc92292594a7a74fc4557fede5e4af816912dca0ad7c09883`, declared
at 18:10:09 UTC, with starts 18:15 through 18:40 UTC. Its trading windows end
at 18:45 UTC (2:45 p.m. Eastern), with the last bounded follow-up around
2:47 p.m. Eastern. The old environment was backed up; the interrupted cohort
was not replayed. Daily timer remains active.

Final local suite: 362 tests pass. EC2 full suite: 362 run, one explicitly
Python-3.10-only inventory test skipped, no failures. Stream plan v2 records
64-record/one-second fsync batching, immediate control/footer sync, and the
possible loss of the last unsynced batch on power failure. Raw hashes and gap
reporting are unchanged; no lossless-delivery claim follows.

The passing 35-second smoke under the service's 75% CPU / 512 MiB limits retained
19,000 frames, both token books, three PONGs and one connection. Its 19,007-row
chain verifies. Exchange-timestamp-to-receipt age was about 0.053 seconds median,
0.707 seconds maximum. An earlier per-frame-fsync run accumulated about 19 seconds
of age; these are operational diagnostics on different traffic, not a controlled
network-latency benchmark. One intervening v2 attempt also reconnected; reliability
is not established by the later passing smoke. Bounded close-code diagnostics
remain enabled for the cohort. All failed attempts are retained in S3.

Replacement evidence prefix:
`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/pilot-86fd6c8ee5eb98ecc92292594a7a74fc4557fede5e4af816912dca0ad7c09883/`.

The following sections retain the initial deployment and repair history.

Instance: `i-039c11d5ea49cf413`, Ohio (`us-east-2`), account `690971215658`.
SSH host fingerprint was independently confirmed by the operator through
Session Manager before first-use trust was saved.

Initial observer source was pinned to `744b556ee4daef7c2a2e1cff00498f83867b3448` in
`/opt/qcrl-stream`, using a dedicated Python 3.9 virtual environment and
`websockets==15.0.1`. The daily checkout remains at
`da280f59684dd4bc80e314b31e23154d620de721`; its collection logic and timer were
not replaced. Two S3 sync exclusions isolate `streams/*`; the original wrapper
is retained at `/usr/local/bin/qcrl-collector-cycle.pre-stream`.

No EC2 replacement, IAM expansion, firewall change, CloudFormation stack update,
QuantConnect push or order/account access occurred. The CloudFormation source
contains the same namespace exclusions for future reviewed deployments. The
observer service remains an explicitly installed host overlay, not automatically
restored by the stack on replacement.

## Verification

- Local full suite: 359 tests pass; all 43 promoted evidence artifacts verify.
- EC2 targeted observer suite: 20 tests pass on Python 3.9.
- The full EC2 suite exercised 359 tests; one test-only stdlib inventory check
  requires Python 3.10's `sys.stdlib_module_names`. It passes locally and now
  explicitly skips on Python 3.9. This is not a production runtime failure.
- The first live smoke uncovered variable-fraction Gamma timestamps unsupported
  by Python 3.9; parsing now pads/truncates to datetime microsecond precision,
  preserving existing complete evidence hashes.
- A 25-second EC2 smoke saw both books but only one PONG; its failed diagnostic
  result/raw log were preserved, not relabeled successful.
- The subsequent 35-second smoke passed: 6,118 frames, three PONGs, both token
  books, one connection and a verified 6,125-row chain. It also preserved one
  unconfirmed/other-market `new_market` event rather than discarding it.
- Both EC2 smoke attempts and discovery artifacts were uploaded under
  `runtime/streams/ec2-smokes/` in the existing encrypted/versioned bucket.

Full-suite Git-based checks require the test process to explicitly trust the
root-owned `/opt/qcrl-stream` checkout. Use scoped `GIT_CONFIG_COUNT=1`,
`GIT_CONFIG_KEY_0=safe.directory`, `GIT_CONFIG_VALUE_0=/opt/qcrl-stream`;
do not add a global wildcard trust exception or change code ownership.

## Locked cohort and live state

Plan hash:
`40934ea2dfed46cf8bc9ce7c18a497f7bb71747ba38a1c049bebb9c2dea3b5a1`.
Declared at 17:53:44 UTC, before all six markets. Starts are 17:55, 18:00,
18:05, 18:10, 18:15 and 18:20 UTC (1:55 through 2:20 p.m. Eastern).
The last market ends at 2:25 p.m. Eastern; its one bounded post-close checkpoint
is due around 2:27 p.m. Service stops after the cohort, not on a recurring timer.

`qcrl-stream-pilot.service` was verified active/running. The first market
(5292787) began recording before its 17:55 UTC start. Initial discovery/bundle,
the pilot declaration and a provisional stream prefix reached S3 at 17:54:47
UTC. Daily `qcrl-collector.timer` remained active. Pilot objects use:

`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/pilot-40934ea2dfed46cf8bc9ce7c18a497f7bb71747ba38a1c049bebb9c2dea3b5a1/`

The first cohort was interrupted for repair after the first stream exhausted
three connection attempts. Its valid 11,544-row S3 log proves retention, not a
clean lifecycle: the adapter had classified idle `TimeoutError` (an `OSError`
subclass) as a connection failure. This is now covered by a regression test.
An early-stopped stream's bounded follow-up was also incorrectly labeled
`postclose_120s` despite occurring before close. Original artifacts are retained;
use their actual observation times, not that old label. Future labels distinguish
before-close/after-close/120-second post-close observations. A fresh prospective
replacement cohort is required; the interrupted cohort must not be replayed.

This is deployment/first-capture verification, **not** a completed-cohort verdict.
Review each final result, footer, quota stop, reconnect gap, checkpoint failure
and settlement state after completion. Active S3 uploads are provisional prefixes.
No continuous coverage, fill, queue position or profitability claim is made.
