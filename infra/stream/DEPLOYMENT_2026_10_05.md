# EC2 BTC five-minute pilot deployment — 2026-10-05

Instance: `i-039c11d5ea49cf413`, Ohio (`us-east-2`), account `690971215658`.
SSH host fingerprint was independently confirmed by the operator through
Session Manager before first-use trust was saved.

Observer source is pinned to `744b556ee4daef7c2a2e1cff00498f83867b3448` in
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
