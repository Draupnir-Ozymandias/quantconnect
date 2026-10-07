# Bounded Linux freshness verification — October 7, 2026

The operator requested commit/push and Linux verification. Implementation was
committed and pushed as `575f7ea7df01c5e5d705d20cc4af689d875d86c3`.
Only Ohio's idle, clean observer checkout at `/opt/qcrl-stream` was fast-forwarded
to that revision. The old failed cohort was not restarted or reset. No prospective
plan was replaced, no public capture ran and Dublin was untouched.

## Capped regression suite

On Ohio (`18.191.254.242`, `i-039c11d5ea49cf413`), Python 3.9.25 and websockets
15.0.1 ran all 501 tests in 29.792 seconds. Result: success, with one expected
Python-version standard-library-inventory skip. Real localhost adapter tests
ran. Whole transient-unit runtime was 30.214 seconds; CPU time was 22.582 seconds.

The finite unit `qcrl-freshness-linux-verification-20261007` used qcrl user/group,
512 MiB memory, 75% of one CPU, 32 tasks, a 120-second runtime cap, protected
system/home, private tmp and no new privileges. Process-scoped `GIT_CONFIG_*`
trust for the verified root-owned checkout allowed the Git file-list test;
global Git settings were not changed. No recurring service or timer was enabled.
The complete test journal remains on Ohio.

## Real-adapter localhost archive check

A separate finite unit `qcrl-freshness-linux-loopback-20261007` used the same
resource/security limits, a 60-second runtime cap and the existing writable
observer evidence namespace. It consumed 229 ms CPU and completed in 311 ms.

It connected only to a local `127.0.0.1` WebSocket server, using a synthetic
market clock and fixture terms. The real instrumented adapter received two
token-book snapshots plus a PONG, unchanged. The stream v6 archive sealed,
verified all three receive markers, and replay-verified both subscription and
connection-end freshness snapshots. Both token books were present, two nominally
fresh events were counted, no stale event or transport gap occurred, and the
final freshness snapshot was present. This is not a public connectivity smoke,
live timestamp validation, overhead benchmark or fill/execution evidence.

The source directory is retained on Ohio at
`/var/lib/qcrl-stream/freshness-linux-verification-20261007-7XNf5J/`.
The script, declaration, report and sealed archive were downloaded into fresh
ignored local directory `.qcrl/reviews/freshness-linux-verification-20261007-7XNf5J/`.
Independent local checks verified hashes, script identity, exact regenerated
fixture spec, footer/result equality, raw-message hash and raw-replayed samples.
No S3 promotion or synchronization was needed for these synthetic diagnostics.

Linux report hash:
`d61263629696bb771fbb310f78eedc6b79c93a0d9afa9b37eb232977caeb3abb`.
Independent local re-verification hash:
`4cd69acf86efc321c501729a81359a642434d9b56d66eaf42f6f76926c16056e`.

## Preserved operational state and next step

Postflight confirmed the observer checkout clean and pinned at `575f7ea`.
Observer environment SHA-256 remained
`ead5cdfd91e18422dc5ce2af70fe373b6e68d94b214329b1f84f7eaf63b18e3d`.
The daily checkout stayed at `da280f59684dd4bc80e314b31e23154d620de721` and
`qcrl-collector.timer` remained active. The old observer service remained failed
with its original exit-code result; both verification units exited successfully
and became inactive. Preflight showed 16 GiB available. No resource, IAM,
ingress, account credential, infrastructure, daily schedule or QuantConnect
change occurred.

The opt-in freshness lane is Linux-verified but has not collected public data.
The next step requires a separately declared finite public diagnostic capture,
followed by archive/S3 verification and freshness analysis. Do not replay the old
plan or infer live performance from this three-message localhost check.
