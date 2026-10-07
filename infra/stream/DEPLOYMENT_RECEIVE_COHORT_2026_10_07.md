# Three-market receive-path v2 cohort — October 7, 2026

The operator authorized a small prospective cohort after the offline analyzer
was created and verified. This is an Ohio-only public observer cohort, not a
cross-site comparison, policy A/B experiment, trading test or retry-to-pass smoke.
Dublin and its automatic-stop schedule remain untouched.

## Prospective declaration

The tracked declaration is
[receive_v2_ohio_2026_10_07.json](cohorts/receive_v2_ohio_2026_10_07.json),
created at `2026-10-07T16:06:24.860335Z` before any capture. Its plan hash is
`c22409af5e079091930da43dcd0e5760bda2101a681052600b1dffd41f1c5306`.

| Locked market start | UTC | Eastern |
| --- | --- | --- |
| 1791389700 | October 7, 16:15 | 12:15 p.m. |
| 1791390000 | October 7, 16:20 | 12:20 p.m. |
| 1791390300 | October 7, 16:25 | 12:25 p.m. |

Capture workers launch up to 30 seconds before each market and observe the
locked lifecycle under existing time limits. The last bounded metadata
checkpoint is due at 16:32 UTC / 12:32 p.m. Eastern; verification and final S3
replication follow. Elapsed time alone does not establish completion.

## Deployment and unchanged bounds

Ohio host: `18.191.254.242`, instance `i-039c11d5ea49cf413`.
The idle clean observer checkout was fast-forwarded from `8cb4fd0` to the pushed
revision `20f2196f26143af9282b8c28774c863ad6b629af`. The daily checkout is separate.
Websockets remains 15.0.1. Strict existing SSH host verification is required.

The plan declares pilot v6 / receive policy v2, five-second profiling, deferred
verification after all capture workers, and the existing resilience policy:
10-second initial-books timeout, 30-second active selected-data silence,
5-second stale-event suspicion sustained for 10 seconds, and 2–8-second
equal-jitter reconnect backoff. These are observation watchdogs, not freshness
proofs. The failed prior 1013 smoke remains failed and retained.

Unchanged resource limits: 512 MiB memory, 75% of one CPU and 32 tasks; at most
two overlapping market workers; 1,000,000 frames, 1 GiB uncompressed and 256 MiB
compressed per segmented stream; 2 GiB spool budget with two-stream reserve
and at least 1 GiB free space. Preflight found 17 GiB free. Marker budget remains
64, fragment budget 64 and library queue high-water 16. No disk/compute/IAM,
credential, ingress, budget, heartbeat or automatic-stop changes are required.

The installer retains the previous inactive observer environment and uses a
new exclusive `pilot-HASH` directory. The permanent service does not restart
automatically. Do not replay or replace missed/failed windows. Daily collection
must remain active and isolated from `streams/*` objects in both S3 directions.
Evidence uses Ohio's existing bucket
`qcrl-collector-artifactbucket-icipysa9venc`, prefix
`runtime/streams/pilot-c22409af5e079091930da43dcd0e5760bda2101a681052600b1dffd41f1c5306/`.
Replication is encrypted, non-deleting and does not promote evidence.

## Review contract

Verify each source, immutable capture/result binding, checkpoints, sealed stream
chain/footer and originating S3 object bytes independently. Run the
[receive-phase analyzer](../../docs/RECEIVE_PHASE_ANALYSIS.md) per window with
the explicit pilot root. Keep complete/partial lifecycle verdicts separate from
normal/draining/unknown timing coverage, conditional timing tails, saturation,
gaps, watchdog reasons, fresh-book recovery and clock/resource limitations.
Do not pool away individual windows or claim wire loss counts, pure queue wait,
geographical causes, policy performance superiority, fills or profitability.
The existing cross-site v1 analyzer does not accept this receive schema.

Report runtime status from observed service and artifacts, not the schedule.
No additional cohort is authorized by this declaration. No QuantConnect sync
is needed for the observer lane.
