# Ohio–Ireland public-feed diagnostic — October 6, 2026

User explicitly approved the scoped Ireland deployment, existing operator-only
SSH key/IP, Session Manager, own-bucket evidence permissions, 48-hour automatic
instance stop, and $75 monthly budget notification amount. Frankfurt is deferred.
No trading, authenticated Polymarket API, credential-bearing disk clone, or
jurisdiction workaround is part of this experiment.

## Budget update

Executed the Ohio stack's previous-template change set
`qcrl-budget-1791317201`. CloudFormation reported `Replacement: Conditional` for
`MonthlyCostBudget`; this was **not** treated as an unconditional safe preview.
The property-expanded before/after contexts were parsed and compared: the only
change was `/Properties/Budget/BudgetLimit/Amount`, `25` to `75`, with USD,
budget name, recipients, and thresholds unchanged. No other resource change
was present. Execution completed with Ohio `UPDATE_COMPLETE`; AWS Budgets
independently returned `Amount: 75.0`, `Unit: USD`.

The allowance is an alert setting, not a spend cap or cost estimate. Forecasted
80% and actual 100% thresholds now correspond to $60 and $75. Stopped replica
disk and retained S3 evidence can continue to incur charges.

## Verified Ohio preparation

The existing watchdog cohort `0e54d82f57360cba89e9843ff66d8a4363692862ee00e9dfb0192be31b7a4b7f`
finished before any source update. Its first two lifecycle captures completed;
the third exhausted the three-attempt limit, including two
`stale_timestamped_book_flow` watchdog triggers. This is an incomplete/unhealthy
cohort, not proof that the feed is fixed or proof of a geographical cause.

Only the inactive, clean `/opt/qcrl-stream` checkout was updated to pinned source
`e319d2c1a3ef40715e807b6281bfd4a671d6112c`. EC2 ran 415 tests successfully with
one platform-specific skip. Daily `/opt/qcrl` was not changed and its timer
remained active.

At `20:14:30 UTC` (4:14 p.m. Eastern), Ohio chrony reported AWS Time Sync
`169.254.169.123`, leap status Normal, system time 2.861 microseconds slow,
root delay 0.333064 ms and root dispersion 0.204212 ms. This is one local
tracking observation, not a guaranteed bound on cross-host measurement error.

## Ireland and shared cohort

Ireland stack `qcrl-ireland-observer` reached `CREATE_COMPLETE` using change set
`qcrl-ireland-1791317201`, pinned source above. Bootstrap signaled success and
SSM independently reported Online. Its clean checkout passed 415 tests with
one platform-specific skip. Root disk had 18 GiB available.

| Observer | Instance | Region | Evidence bucket |
| --- | --- | --- | --- |
| Ohio | `i-039c11d5ea49cf413` | `us-east-2` | `qcrl-collector-artifactbucket-icipysa9venc` |
| Ireland | `i-08884daf5d5704b2d` | `eu-west-1` | `qcrl-ireland-observer-artifactbucket-y5psgiphmqe1` |

Ireland public IP at creation: `108.131.148.110`. Its ED25519 fingerprint
`SHA256:5i3HamcpjxFiwjx/jawDQdu2aJsn8DkCVPz2jPwBcCQ` was read through
SSM command `f842ec57-df88-401b-ab9a-607ea00af562`, matched against the scanned
public key, and pinned in the ignored local `.qcrl/ireland_known_hosts` file.
SSH used strict verification with that file; host checks were not bypassed.

Bootstrap completed at `2026-10-06T20:17:44.646807Z`. The active persistent stop
timer fires `2026-10-08 20:17:44 UTC` (Thursday, 4:17:44 p.m. Eastern), stopping,
not terminating, the instance. S3 evidence and encrypted disk remain charged.

At `20:19:24 UTC`, Ireland chrony reported AWS Time Sync, leap status Normal,
system time 1.614 microseconds fast, root delay 0.322740 ms and root dispersion
0.241969 ms. Local tracking uncertainty is not a complete network-latency or
cross-host accuracy guarantee.

Ohio bounded profiled smoke `smoke-1791317760` passed: 15,980 frames, one
connection, both token book baselines, three text PONGs, verified persisted
manifest/hash chain. All nine evidence files matched their S3 bytes
(3,161,994 bytes total). It is partial connectivity evidence, not complete
market coverage or a geographical comparison.

Ireland profiled smoke `smoke-1791318019` passed: 20,862 frames, one connection,
both token book baselines, three text PONGs and a verified manifest/hash chain.
All eleven evidence files matched S3 bytes (4,136,537 bytes total). The smoke
tests ran on different windows and are not synchronous comparison evidence.

## Shared, prospective finite cohort

Declared once locally at `2026-10-06T20:20:45.466386Z`, schema
`qcrl.btc_5m_rolling_pilot.v4`, with profiling, unchanged resilience policy and
verification deferred until all capture workers finish:

`17e99be1cb5cde20e8d27e2f8498b1fa396c76fe3db11bd49e14c832897560a4`.

| Start epoch | Start UTC | Start Eastern |
| --- | --- | --- |
| 1791318600 | 20:30 | 4:30 p.m. |
| 1791318900 | 20:35 | 4:35 p.m. |
| 1791319200 | 20:40 | 4:40 p.m. |

The identical declaration input bytes were distributed to both sites and
SHA-256 checked: `31b14d89bf065226408346989ebf7232d5f98635b13653a9aa561619f3502e08`.
Each installer validates the same artifact hash; installed JSON formatting
can differ without changing its semantic content. Ohio's previous environment
was retained. Ireland's installer verified completion/checkpoint reserve before
its stop deadline. Both environments were inspected for their own bucket/region.

Hash-linked `observer_preflight.json` artifacts retain per-node clock tracking,
instance/region identity, source commit, common input and plan hashes, free disk,
and systemd resource settings. Both service units have identical SHA-256
`42e08018b92d83f2de16ad49d5da7ceb8ce64696806c90d52123d979f94d6a31` and limits
75% of one CPU, 512 MiB RAM, 32 tasks. Clock tracking before activation reported
Normal leap state on both; root dispersion about 0.182 ms Ohio and 0.188 ms
Ireland. This is local synchronization evidence, not guaranteed cross-host
timing accuracy.

Preflight artifact hashes:

- Ohio: `224a55c18c332fa1e4dd9d6e888b97aedadede856b08778c544866f06694e77a`.
- Ireland: `76ffc83bdf46b78e366624c49a3a8bf9b7149a8a76488a840e59f8b3456b548d`.

Services were independently confirmed active/running at `20:23:11 UTC` Ohio
and `20:23:14 UTC` Ireland, ahead of the first pre-open boundary at 20:29:30.
This confirms activation and waiting, **not completed captures**. Daily Ohio
and Ireland's automatic-stop timers remained active.

Each bucket uses its own `runtime/streams/pilot-17e99be1cb5cde20e8d27e2f8498b1fa396c76fe3db11bd49e14c832897560a4/`
prefix. Automatic minute replication was verified before collection: both
sites' `pilot.json` and `observer_preflight.json` matched their S3 bytes, with
both services still active and the same three market starts. This is not a
verification of future stream files. There is no shared cross-node writer
destination. Last market ends at
4:45 p.m.; final post-close checkpoint is due about 4:47, followed by deferred
verification and replication. Review around 4:55 p.m. Eastern or later.

Next review must verify each source/result/manifest and all copied S3 bytes,
then compare market identities/terms/tokens, matching raw event fingerprints,
clock evidence, timestamp age, watchdog/gap timing and profiling. Preserve
duplicates, unmatched events and incomplete captures. A shared stale period
does not prove a particular upstream component failed; a site-specific period
does not prove geography caused it. Never merge streams into invented fills
or promote this diagnostics lane to trading/profitability evidence.

## Unchanged-policy repeat — October 6, evening

After review of the first cohort, the user authorized one repeat on both
existing observers. No Frankfurt, infrastructure, IAM, budget, source, watchdog,
CPU/memory, synchronization/upload or stop-deadline change was made.

New declaration: `2026-10-06T22:12:52.687716Z`.
Plan: `936cdd98223c7837277b43b790421b80c81bf9c39d24680d4a8339bfddd50b7b`.
Identical input file SHA-256:
`cb90ed88c6caacd54155fca65983779fdeb01eb9cf99004b31e053d60b39a001`.

| Start epoch | Start UTC | Start Eastern |
| --- | --- | --- |
| 1791325500 | 22:25 | 6:25 p.m. |
| 1791325800 | 22:30 | 6:30 p.m. |
| 1791326100 | 22:35 | 6:35 p.m. |

Both hosts were confirmed inactive and clean at pinned source `e319d2c` before
installation. Input bytes were hash-checked and normalized declarations compared
against the first plan: **only** `declared_at_utc`, `market_starts` and
`plan_sha256` changed. The previous environments and all first-cohort evidence
were retained. Each regional bucket uses a new `runtime/streams/pilot-936cdd98223c7837277b43b790421b80c81bf9c39d24680d4a8339bfddd50b7b/`
prefix; cross-site writers remain isolated.

Fresh exclusive/hash-linked preflight artifacts record clocks, resource limits,
free disk and a link to the preceding plan. Both clocks reported Normal leap
status and retained the same service-unit hash and 75% CPU/512 MiB/32-task caps.
The repeat is finite and public-only; it is not a recurring/restarting daemon.

Both services were confirmed active/running ahead of pre-open: Ohio at
`22:14:12 UTC`, Ireland at `22:14:15 UTC`. Both nodes' automatically uploaded
`pilot.json` and `observer_preflight.json` matched S3 bytes and the services
remained active, waiting for the same three market starts. Ohio's daily timer
and Ireland's automatic-stop timer remain active. Preflight hashes are
`633c5253fc116ad63b87693136f13454ad3c75190967c3bb26306d9809fa3352` (Ohio) and
`f916e975bbc922f19ef16cccaadf52490626cdd8cd6139fe6873177cbe717699` (Ireland).

Last market ends at 6:40 p.m. Eastern, its final post-close checkpoint is due
about 6:42, and deferred verification/replication follow. Review about 6:50 p.m.
or later. Completed captures are not asserted by this activation record.

## Completed reviews and versioned analyzer

Both three-market cohorts subsequently completed all six observer lifecycles.
The first retained 775,020 frames and 366 files; the repeat retained 754,721
frames and 358 files. Every downloaded file was independently compared with
its originating S3 object, and source/checkpoint/result/stream integrity was
reverified. Completion does not erase reconnect gaps or prove lossless coverage.

The offline `qcrl.stream_cross_site.v1` analyzer reverified both cached cohorts
and reproduced the one-off timing findings. It rejects mismatched plans,
runtime policies, identities and corrupt sources, excludes payload duplicates
over each entire stream from timing pairs, and keeps partial lifecycles and
unknown resource counters explicit. See [the analysis contract](../../docs/CROSS_SITE_STREAM_ANALYSIS.md).

| Paired market start, Eastern | Ohio minus Ireland median | Paired p99 |
| --- | --- | --- |
| 4:30 p.m. | 42.631 ms | 1.347831 s |
| 4:35 p.m. | 38.789 ms | 8.368924 s |
| 4:40 p.m. | 50.220 ms | 3.715779 s |
| 6:25 p.m. | 45.194 ms | 0.817040 s |
| 6:30 p.m. | 46.427 ms | 2.000284 s |
| 6:35 p.m. | 46.677 ms | 4.058641 s |

Positive means Ireland recorded the exact uniquely matched event earlier.
These are six correlated market windows, not hundreds of thousands of independent
trials. No geographical-causality or one-way-network-latency conclusion follows.
Ohio's first cohort included one stale-flow watchdog; neither observer triggered
that watchdog in the repeat. Both observers experienced transient 1013 gaps.

Ignored local report paths: `.qcrl/reviews/two-site-17e99be1/cross-site-v1.json`
and `.qcrl/reviews/two-site-936cdd98/cross-site-v1.json`. Their report hashes are
`6f519d7b405e05ea4eb80ed29203f916fb08a13577bf88d46a54f186f220d958` and
`03c5713c237d93624d166b8862c58f9342e6fea8a0bcd0bae8b035f097a041ba`.

## Extended prospective comparison — October 6, late evening

User approved the versioned analyzer followed by a longer unchanged-policy
comparison. A single twelve-market declaration was created at
`2026-10-06T23:12:13.758850Z`:
`76dbcd28597468152f1b7eecfb5f7e57838fc49d687659af07e1aea107339e0a`.
Input bytes SHA-256:
`2f422e3ad160a433d43737f7234101637331dadac7ac26e0f5b5938771b435d5`.

Markets begin every five minutes from epoch `1791329400` through `1791332700`
(23:30 UTC October 6 through 00:25 UTC October 7). This is **7:30–8:30 p.m.
Eastern October 6** including the final market's end. Final post-close checkpoint
is due about 8:32 p.m.; deferred verification and replication follow. Review
about **8:45 p.m. Eastern or later**, not merely when the last market closes.

On both clean inactive nodes, prospective lead and identical input bytes were
checked. Against the prior plan, only market starts, declaration time and plan
hash changed. The same collector revision `e319d2c`, unit hash, retry/watchdog
policy, 75% CPU/512 MiB/32-task caps, two-worker concurrency and per-stream/spool
limits remain deployed. Offline analyzer changes do not alter the experiment.
No Frankfurt, compute, IAM, budget or automatic-stop changes were made.

Previous environment files and raw cohorts were retained. Fresh preflights
reported normal AWS Time Sync tracking and more than 16 GiB free per node:

- Ohio: `71e5d666074f1f83f1cd4f609785fd6ba1edd97f0416e53ba64ce1d724a2cbfa`.
- Ireland: `0a8a344f5763dd51ff6c3cb48342e11ec0329a8be259bc14468b06e5dc99467f`.

Services were independently confirmed active/running at 23:14:08 UTC Ohio and
23:14:10 UTC Ireland, ahead of the first pre-open boundary at 23:29:30 UTC.
Ohio daily and Ireland automatic-stop timers remain active. This is an
activation record, **not** an assertion that future captures succeeded.
Both regional buckets use separate `runtime/streams/pilot-76dbcd28597468152f1b7eecfb5f7e57838fc49d687659af07e1aea107339e0a/`
prefixes; raw evidence is not automatically promoted to the research inventory.

Before the first market, both nodes' automatically replicated `pilot.json` and
`observer_preflight.json` were downloaded from their own S3 prefixes and matched
local bytes exactly, with services still active/running. This verifies initial
configuration replication only, not future capture success. All 427 local tests
passed, including twelve cross-site analyzer tests; whitespace checks passed.
Analyzer, tests and documentation remain local/uncommitted at this checkpoint;
neither GitHub nor QuantConnect was pushed during this step.
