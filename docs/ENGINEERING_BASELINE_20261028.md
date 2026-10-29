# Milestone 2 — engineering baseline, October 28, 2026

**Historical application verdict: FAIL. V6 and PreClosePub01 remain
partial/unresolved. No combined acceptance is defined or implied.** This is the
current engineering baseline, consolidating the dated records linked below.
It grants no capture, deployment, rerun or cohort authority.

The inspected development checkout is `codex/lupus-development`, source HEAD
`c8d80810e92b9436fc5b3df8983286bcabcaf2c1` before this documentation milestone.
That HEAD is not a new execution freeze and cannot replace a historical report's
source. No fresh Linux/host/credit observation was made for this consolidation.

## Capabilities and their evidence boundaries

| Capability | Supported evidence | What remains unestablished |
| --- | --- | --- |
| Public acquisition and bounded recovery | V6 retained 60,000 texts across two connection epochs, one declared retry, full resubscription and fresh books for both assets in each epoch; prior receive fault retained | Venue completeness, recovery of missed messages, maintained-book accuracy, general reliability/performance; reconnect cause not isolated |
| Interval-aware descriptive counting | V6 archive/completion/checkpoint linkage; all 60 raw/eligible rows independently recomputed. The 49 wholly eligible bins contain 39,605 texts; other 11 contain 715 raw / 712 eligible | Complete-minute acquisition or zero activity in unavailable periods; nominal clock anchoring is not independent UTC accuracy |
| Normal acquisition versus interruption ownership | Existing production ownership logic and local timeout/closure/stop-race regressions; faults survive cancellation. V6 accurately reports its frame-cap end | V6 did not reach normal scheduled completion; watchdog or graceful peer closure alone is not success |
| Archive and pre-close checkpoint | V6 sealed archive, 60,000 completion witnesses and 960 durable barriers survived SIGTERM | Final consumer, final cleanup return and final resource result were absent; signal sender/final close progress unproven |
| Pre-close returned-resource publication | PreClosePub01, exact later source, retained 87 linked synthetic texts and one exact synthetic resource row through real worker SIGTERM during blocked close | Native resource measurement, public-path/high-rate finalization, complete observer window or graceful final close; its frozen inspection/auditor gates failed |
| Corrected exited-unit inspector | Successor v1 has 20 local lifecycle/adapter tests; together with 16 existing publication checks, 36 passed on Intel Mac | No Linux execution of this successor, no new packet wiring or stop authority. Two equal snapshots are not an atomic future-stop guarantee |
| Unevenness analysis | Retrospective arithmetic over the original v6 data: mean 808.27, CV 13.51%, top-five share 11.92%; recording-specific | Cause of block differences, new-market estimates, predictive rates or capacity guarantees |

The incoming population is **text occurrences**, including duplicate deliveries,
batches and accepted metadata, not individual trades/events. Raw and strict
fresh-book-eligible populations stay separate. Unavailable zeros are not observed
silence; ambiguity, unplaced occurrences, censoring and all original coverage
labels survive. Public-feed outcomes do not turn synthetic timing experiments
into venue-completeness or trading/execution evidence.

## Exact versions and validation status

| Component / record | Exact source or policy | Validation scope |
| --- | --- | --- |
| V6 execution and original report | `fc89c11c8c9186c866385b373db12ba04c721e33`, 561 selected files; freeze `763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b` | One actual Ohio Linux public recording, with partial verdict. Its 1,280-test full/79-test focused results were Intel Mac offline checks, not native acceptance |
| Termination review/regressions | `c95f34296be8230eb4ed85a0c24a89cac11167d9` | Code/evidence review and local boundary tests; no resolution of v6 signal attribution |
| Production pre-close publication opt-in | `7ce5b9fed67b3f700acbf6ac939eac2bac574a89` | 1,298 full tests / 102 focused tests on Intel Mac. Original v5/v6 freezes retain legacy behavior; extension requires a new explicit freeze |
| PreClosePub01 execution/report | `3054bc50cb0bb32fa5803853112ffda83f2d60f5`, 566 selected files; freeze `0e359464dec8952c7f8f68047a2dbfe16eff9dbeefbe7a3aa47cc05330b96d55` | One Linux synthetic blocked-close compatibility case, not a public recording or native resource test |
| Corrected inspector | `be254c989ecc1919a8733b1670a91f3d257e5818`; policy `qcrl.exited_unit_inspection.policy.v1`, SHA `24898288fd05207fbfda23597c20a8ba04c56ab4f626a30b262ead55b50c4a6b` | 36 focused offline tests in 10.482 s; includes 20 inspector tests. Python 3.9 grammar checked locally, not installed-runtime execution |
| Retrospective v6 analysis | `c8d80810e92b9436fc5b3df8983286bcabcaf2c1` | Original CSV SHA `b5712ba918794474132984ba5f96d9c7d69da9b0bf654285fb1eb93dd157860b`; exact-rational recomputation and independent arithmetic checks |

Publication policy `qcrl.public_preclose_resources.policy.v1` SHA is
`97182fefdef0ebd4e5007a8aed416fc13e189abb52c6218f3de252fddb4daa73`.
PreClosePub01's expected returned synthetic payload SHA is
`695811c9421331ba318953d9d2af17e093cc7e334a67cb6d7c0b8dd11743db70`.
Neither hash asserts valid native CPU/RSS readings. The installed runtime used
for those native cases was Linux ARM64/Python 3.9.25/websockets 15.0.1; local
development was Intel macOS/Python 3.14.6. No new combined full-suite run or fresh
installed-runtime validation is claimed by adding these historical test counts.

## Remaining shutdown and publication issues

1. **Final close remains bounded but unreliable/unverified in the public case.**
   The library close timeout and external process guard are both five seconds;
   there is no reserved cleanup margin. Lock/thread cleanup can exceed the
   library timeout. V6 timing is consistent with the close guard, but the sender
   and exact blocked operation are not proven. Do not remove the hard guard,
   soften errors, or accept closure merely because a watchdog fired.
2. **Publication has a narrower supported finding than completion.** The new
   opt-in publishes archive/completion/checkpoint, then stops/joins the observer
   for at most three seconds and retains only a finished returned result before
   close. Live observer means unavailable component; pending/failed writes remain
   faults. Publication, serialization, hashing and fsync still consume the
   original acquisition/publication guard and storage budgets. The 87-text
   synthetic native case does not establish cost/memory/durability at 60,000 texts.
3. **Inspector correction is prospective and not deployed.** The old inspector
   asserted numeric `TasksCurrent=0`; systemd returned `[not set]`. Its failure
   and the ensuing frozen-auditor failure remain authoritative. Successor v1
   records missing counters as unknown, requires separately bound invocation/
   boot/PIDs and an empty/removed original cgroup, repeats reads, and preserves
   faults. It is read-only and grants no stop authority; a future packet needs
   new InvocationID/complete-argv bindings and a separately owned cleanup protocol.
4. **Resource and precision acceptance remain open.** V6 has five original UTC
   brackets over 1 ms, including four primary bins. No resource-publication or
   inspector change repairs them. Final RSS rows/qualification, primary 60-second
   CPU window, continuous RSS peak and incremental observer overhead are unknown.
   Sampled/inclusive values are not substitutes. Independent UTC accuracy,
   internal transport/runtime retries and missing-period activity remain unknown.

The original thresholds remain authoritative: UTC 1 ms, RSS 5 ms, RSS-start
50 ms, original CPU/RSS/append/durability gates, all without subtraction.
A shorter descriptive study cannot qualify an original 60-second CPU window.
Engineering readiness, linked prefix evidence, cleanup state and scientific
measurement acceptance must be reported separately, never collapsed into a badge.

## Integrity and capture decision boundary

Original v6 seal:
`30ff87a242af69579600eee08781d6fc7c4eea491bcfb7c3601e61bf762139cd`.
Original PreClosePub01 seal:
`d898897351d3b607ab088df91b4bb2283ba90105190bc951bcee80177109d9f4`.
Both remain immutable. Older v1/v2 not-run, v3 closure fault, v4/v5 partial
outcomes, original Cohort02/RssCpu01 FAIL and all historical evidence stand.

Milestone 2 is this consolidation, not a Linux acceptance milestone. A capture
decision should follow a named question, changed acquisition envelope, offline
integration of that envelope and exact packet/source/runtime/audit readiness.
No standalone inspector-only smoke is required to preserve the existing
resource-retention finding. No capture, remote refresh, staging or scheduler is
authorized by this baseline; old host/credit context is not fresh evidence or a
new minimum acceptance gate.

References: [v6 outcome](PUBLIC_FEED_COUNTS_V6_OUTCOME_20261021.md),
[termination review](PUBLIC_FEED_V6_TERMINATION_REVIEW.md),
[publication contract](PUBLIC_PRE_CLOSE_RESOURCES_V1.md),
[native publication outcome](PRE_CLOSE_RESOURCE_PUBLICATION_NATIVE_OUTCOME_20261021.md),
[inspector successor](EXITED_UNIT_INSPECTION_V1.md),
[retrospective analysis](PUBLIC_FEED_COUNTS_V6_UNEVENNESS_20261027.md).
