# Three-market Ohio freshness cohort — October 7, 2026

The operator authorized the first finite public freshness capture after commit,
push and bounded Linux verification. This Ohio-only diagnostic cohort uses
three future BTC five-minute windows. It is not a cross-site experiment,
causal reconnect comparison, live trading test or retry-to-pass rerun.

## Locked declaration and reviewed source

The [tracked declaration](cohorts/freshness_v1_ohio_2026_10_07.json) was created
at `2026-10-07T20:27:06.736855Z`, before capture. Plan hash:
`2a8a6684ea02d09e8c5e0ba9cba32d78c7d557743a50f33858bb8cb8a799bf11`.

| Locked market start | UTC | Eastern |
| --- | --- | --- |
| 1791405300 | October 7, 20:35 | 4:35 p.m. |
| 1791405600 | October 7, 20:40 | 4:40 p.m. |
| 1791405900 | October 7, 20:45 | 4:45 p.m. |

The source remains the Linux-verified pushed revision
`575f7ea7df01c5e5d705d20cc4af689d875d86c3` in `/opt/qcrl-stream` on Ohio
`18.191.254.242` / `i-039c11d5ea49cf413`. Both observer checkout and working
tree were clean at preflight. The prior verification passed 501 Linux tests
with one expected Python-version skip, plus a real-adapter localhost archive
check. Python remains 3.9.25 and websockets 15.0.1.

The declaration enables pilot v7 / stream v6, receive policy v2, profiling,
existing resilience, deferred archive verification and freshness telemetry v1.
The diagnostics observe but do not control reconnects. Existing raw market
terms/source/token identities must still match exactly; changed terms fail
closed. Missed, quota-limited and failed windows stay in the denominator and
are not replayed. Older cohort artifacts and failure verdicts remain retained.

## Unchanged limits and preservation

Watchdogs retain 10-second initial books, 30-second active selected-data silence,
five-second event-age suspicion sustained for ten seconds, 2–8-second equal-
jitter retries and at most three connections per market. The fixed marker and
fragment budgets remain 64, library queue high-water 16 and max message 256 KiB.
Systemd limits remain 512 MiB, 75% of one CPU and 32 tasks; two market workers
permit rollover overlap. Stream budgets remain 1,000,000 frames, 1 GiB
uncompressed and 256 MiB compressed; spool budget is 2 GiB with two-stream reserve
and minimum 1 GiB free space. Preflight showed 16 GiB available. No capacity,
budget, IAM, ingress, credential or infrastructure change is involved.

The existing install procedure backs up the inactive observer environment and
uses a new exclusive `pilot-HASH` directory. It does not delete old evidence,
enable recurring observation or automatically restart failed captures. The
separate daily checkout stayed at `da280f59684dd4bc80e314b31e23154d620de721`,
its timer was active, and namespace isolation is validated by the installer.
Dublin and its automatic-stop schedule remain untouched.

Evidence replicates without deletion, encrypted, to the existing Ohio bucket:
`qcrl-collector-artifactbucket-icipysa9venc`, prefix
`runtime/streams/pilot-2a8a6684ea02d09e8c5e0ba9cba32d78c7d557743a50f33858bb8cb8a799bf11/`.
Replication is not evidence promotion or proof of complete object publication.

## Completion and review

Workers begin up to 30 seconds before each locked window. The last bounded
metadata checkpoint is due at 20:52 UTC / 4:52 p.m. Eastern. Archive verification,
health computation and final replication follow; check around 21:00 UTC /
5:00 p.m. Eastern, but infer completion only from service and sealed artifacts.

Verify originating S3 bytes, source/plan bindings, immutable capture/result
derivation, metadata checkpoints, raw stream chains and replay-derived freshness
samples. The analyzer selects analysis/policy v2 for this new stream schema;
older v4/v5 reports stay v1. Report each window's full/partial lifecycle,
normal/draining/unknown receive coverage, conditional delays, freshness onset/
clearance, both-token recovery, structured close fields and clock/resource
limitations. Missing codes remain unknown; fresh snapshots alone do not prove
sustained event-flow freshness or reconstructed state validity. Do not pool away
failed windows, infer wire loss counts or treat nominal age as network latency.

No trade, account endpoint, credential use, QuantConnect sync or additional
cohort is authorized by this declaration. Public market GETs and public market-
channel observation only. Launch status is recorded separately below after
verification; this prospective section does not claim any completed capture.
