# Development handoff

Updated October 21, 2026. Continue in
`/Users/eric/Projects/quantconnect/polymarket-martingale` on
`codex/lupus-development`. The Intel migration base is `f05d5dd`; use Git history
for subsequent development revisions. Keep this branch separate from main.

## October 21 — V6 recovered once; frame cap and close-unverified partial outcome

**Historical application FAIL remains unchanged. V6 is partial/unresolved, not a
combined pass.** One approved attempt from exact source
`fc89c11c8c9186c866385b373db12ba04c721e33` (561 files), freeze
`763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b`.
[Outcome/integrity audit](PUBLIC_FEED_COUNTS_V6_OUTCOME_20261021.md);
[all60 raw/eligible rows](PUBLIC_FEED_COUNTS_V6_20261021.csv).

Fresh gates passed; one controller, five metadata GETs and one private unit ran.
Independent controller binding and16:00:40.636Z worker binding verified identity,
source/version, original signals, limits and ready/release. **One public reconnect
was observed** after the retained exception reported1013 and “slow consumer: send
buffer full”. One1.836239s jitter wait and fresh books for both assets in epoch2
verify; cause of the reported backpressure is not isolated. The first fault stays
retained. No third attempt, induced disconnect, manual retry or extra capture.

60,000 texts hit the unchanged shared frame cap atM0+53.085595s:19,680 prewindow,
40,320 primary, zero tail. Eligible subset59,996 total/40,317 primary. All60 raw
and eligible rows independently match; three ambiguities all prewindow, zero
unplaced. Raw reconnect gap2.704756s; book-ineligible gap2.904021s.49 bins are wholly
inside local acquisition/book-eligible windows; bins24–27 and53–59 are unavailable/
boundary. Eight zero-text bins25,26,54–59 have unknown activity, not observed
silence. All feed-activity upper/full-minute feed bounds null; original coverage
labels unverified.22 foreign creation notices count once; no inferred recovery
of missing messages or venue completeness.

Archive/footer/manifest,60,000 completion witnesses,960 barriers and pre-close
checkpoint survived and link. **Final consumer/observer result absent; final close
unverified.** Unit exited SIGTERM (ExecMainCode2/status15) about five seconds after
checkpoint publication, consistent with the close guard; sender and exact close
progress remain unknown. Socket-interrupt receipts unfired at checkpoint do not
prove later process-guard state. Controller retained partial/unresolved and stopped
its own unit. OS Result=success is not recorder/scientific success.

Five UTC brackets exceed1ms (four primary; maximum30.037893ms); unchanged thresholds
stand. Final RSS/slot/CPU-window evidence is unavailable, not passed or zero
violations. Whole-unit CPU52.553558s is inclusive, not primary-window acceptance or
incremental overhead; continuous RSS/independent UTC accuracy/internal retries
remain unknown. Credits historical/unavailable; no new minimum. Independent copy
verified67 files/28,459,950 content bytes, all43 producer evidence files and all561
source hashes; sealed SHA
`30ff87a242af69579600eee08781d6fc7c4eea491bcfb7c3601e61bf762139cd`.
Public collectors/source/runtime/TLS unchanged; exact worker/controller gone and
unit inactive/dead. Private evidence `.qcrl/reviews/public-feed-20261021T160000Z/`.
Original historical FAIL and every earlier verdict/evidence/limit remain intact.
The one-time follow-up is deleted; attempt over, no pending capture or rollover.

## October 20 — Exact v6 approved and staged; October 21 follow-up scheduled

User directly approved the exact packet: “i approve. please proceed.” Separate
confirmation artifact `e27f98a444440add259db324f28757a0476141938926a43897911c808425617d`
binds one conditional v6 capture to freeze
`763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b`.
Execution source stays `fc89c11c8c9186c866385b373db12ba04c721e33`, 561 selected
files; later documentation HEAD is not a source substitute. No further routine
approval is needed within this exact scope.

Fresh pre-stage read-only SSH at 22:06:25Z matched installed runtime/TLS/CA/public/
boot, 6,122,958,848 free bytes and unused target namespace/unit. Staged once at
22:06:47Z on existing Ohio host at
`/var/lib/qcrl-stream/public-feed-20261021T160000Z`; source/runtime/TLS/public and
approval checks passed, free disk 6,095,101,952 bytes. Exact predeclared
operator-receipt bytes were activated only after separate direct approval; their
template flags are not independent execution authority. Preserved host/credit
context was not rewritten or relabeled fresh; no minimum is inferred.

Independent 22:07:27Z readback matched packet/freeze/confirmation/receipt/launcher
hashes, root permissions, all 561 source bytes and native runtime/TLS/public gates.
Evidence/controller absent, metadata GETs zero, native units zero, unit not found.
These are native staging/import/readiness checks, **not v6 functional/public-feed
validation or resource/coverage acceptance**. Capture has not started.

Prepared root `launch-once.py` SHA
`e4e2f5c4ee2362acadbebc53385aba07c99e7a34108b5b3c7a1700e5b792d8f5`
remains unexecuted; no remote scheduler. One local thread follow-up
`run-and-audit-the-approved-btc-v6-capture` is active for **October 21, 11:44 AM
EDT / 15:44 UTC**. It refreshes gates, invokes the helper once if eligible,
independently binds controller and worker promptly at arm, observes only that
attempt, audits retained evidence with exact source, commits/pushes, then deletes
itself. Quiet on unchanged polling; notify meaningful outcome/failure/blocker or
necessary action. Keep the local Mac awake with the app available for this wake.

Launcher opportunity11:44–11:55AM; controller11:45–11:55; metadata11:55; lockbefore
11:59; arm12:00:40PM; count12:01–12:02PM EDT. Max three declared sequential
**in-unit** connection attempts/two retries share original bounds; no manual
controller/unit retry, induced disconnect, extra capture, replay, substitution,
rollover, smoke or cohort. Existing claim means inspect only. No reconnect means
that component is inconclusive, not an extra run. All historical FAIL, v1/v2
not-run, v3/v4/v5 faults/partial/censored evidence and original thresholds/limits
remain unchanged. Partial evidence and every unknown must survive. Private controls:
`.qcrl/reviews/public-feed-20261021T160000Z/`.

## October 20 — V6 exact packet sealed; staging/execution approval pending

[Prospective v6 declaration](PUBLIC_FEED_COUNTS_SUCCESSOR_V6.md) fixes one BTC
October 21 noon EDT target, count 12:01–12:02 PM, with up to three sequential
in-unit connections under recovery v1. This preparation is authorized; **native
staging/execution are not yet approved**. No automation or public subscription.
Default v5, its literal plan hash, all retained evidence and historical FAIL stay
unchanged. V6 requires explicit `--study-version v6` throughout controller,
metadata adapter and worker, and rejects cross-plan cases/freezes before action.

The actual consumer passes the recovery contract into the shared recorder;
reporting verifies/replays archive lifecycle alongside raw completion witnesses,
keeps raw counts when only lifecycle linkage fails and withholds eligibility.
Missing/corrupt linkage never manufactures zero acquisition coverage. Review
aligned a fatal foreign frame's epoch bookkeeping with replay while preserving
its fatal verdict, and bound the actual metadata slug allowlist to the selected
plan. Both paths have local regressions. No observer optimization or new framework.

Fresh read-only pinned SSH at October20 19:54:31Z verified the existing v5
source/runtime/TLS/CA/boot/public baseline, 6,123,982,848 free bytes and absent
v6 namespace/unit. New-source Linux validation and post-approval staging readback
are still outstanding. Credit mode/balance are historical/unavailable context,
not a refreshed minimum or acceptance gate. No credentials imported, infrastructure
or public collectors changed, controller/metadata/unit/feed started.

Final local suite: **1,280 tests passed in 167.599s**, plus **79 focused tests
in 17.548s** after the metadata transport correction; local Python3.9 grammar
checks pass. Logs are in `.qcrl/reviews/public-feed-20261021T160000Z/`. Exact
sealed source/runtime transport anchors follow below. No native run, staging, schedule, retry of a
previous target or rollover is authorized by the preparation itself. One-shot
transport must require separate direct approval; later documentation HEAD must
not replace the frozen execution commit. No forced disconnect; if reconnect is
not observed, that component remains inconclusive without an automatic extra run.

### V6 sealed execution anchors and approval boundary

Execution source `fc89c11c8c9186c866385b373db12ba04c721e33`, 561 selected files;
freeze `763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b`.
Nine-member packet 113,576 bytes, SHA
`e0e46e15005fa68e97c8dbb2b0cdde9ca76cfc05e2731da063de23cc4029e8c6`.
Launcher SHA `e4e2f5c4ee2362acadbebc53385aba07c99e7a34108b5b3c7a1700e5b792d8f5`.
Member population/hashes, committed source bytes and bundle prerequisite verify.
Four mocked launcher scenarios and staging-without-approval refusal pass; no
native execution was involved. Existing independent binding/copy/audit templates
are adapted and parse locally, including separate eligible-count recomputation.
Private packet/controls: `.qcrl/reviews/public-feed-20261021T160000Z/`.

Present [the exact approval packet](PUBLIC_FEED_COUNTS_SUCCESSOR_V6.md) for one
conditional October21 capture. No active receipt/confirmation, native stage,
scheduler/controller/metadata/unit/feed or follow-up automation exists. Require
separate direct approval before staging or scheduling execution, then exact-source
readback and all fresh gates. One-shot launch opportunity October21 11:44–11:55AM
EDT; controller11:45–11:55; metadata11:55; arm12:00:40PM; count12:01–12:02PM.
No forced disconnect; no reconnect means inconclusive for that component, not an
extra run. No historical result or threshold is changed. Later documentation
HEAD must never replace frozen execution commit `fc89c11c8c9186c866385b373db12ba04c721e33`.

## October 20 — Prospective bounded recovery implemented offline

[Recovery contract v1](PUBLIC_FEED_RECOVERY_CONTRACT_V1.md) defines explicit
connection epochs/gaps, full resubscription, per-connection fresh-book bootstrap
and separate raw/eligible interval populations. Policy SHA
`437621e12790da88843eb418b649af6a00972566b21a86d94e11a43b266c6f04`
is pinned literally in a regression test. This is not a new study plan, runtime
freeze, capture authorization or repair of v5/historical FAIL.

The opt-in recorder path reuses existing `DataWatchdog`, equal-jitter retry,
book/timestamp validators, writer/completion/persistence/storage and stop guards.
At most three attempts/two retries share one deadline, 90-second acquisition
bound, 60,000-text population and all original resource/storage limits. A failed
socket closes before any successor; close failure, emergency, clock/storage/
linkage/foreign-binding faults stop recovery. Prior faults stay retained even if
a later epoch reaches its normal stop. The final epoch's ownership and cleanup
close are reported separately; neither grants whole-recording acceptance.

Every new connection resubscribes and needs fresh valid full books for both
selected assets. Old books/deltas/PONGs cannot bootstrap. All incoming texts count
once, including duplicate deliveries and accepted creation notices; eligible
counts are a separate explicitly bounded subset. Reports replay bootstrap from
linked archive frames and compare lifecycle/footer/completion witnesses. Gaps
include bootstrap/backoff/reconnect/terminal remainder; unavailable zero-text
bins remain unknown, distinct from observed local silence. No reconnect claim
of recovered missed messages, feed completeness or continuously valid book state.

The v5 plan and operator remain one-attempt and do not enable this option. Local
fake-clock, real loopback WebSocket and blocked-socket tests cover lifecycle,
resubscription, retry bounds, book reset/invalidity, races and fatal paths. The
full offline suite passed **1,271 tests in 172.800s**; after final report
metadata/boundary-only additions, **22 focused tests passed in 4.099s**. Python
3.9 grammar accepts changed sources locally. Validation receipts/logs remain in
`.qcrl/reviews/public-recovery-offline/`.
These are Intel macOS/Python 3.14.6 offline tests, not Linux/TLS/public-feed or
budget validation. No SSH, native unit, infrastructure change or capture proposal
was launched. Before proposing a public target, prepare a new explicit plan and
source/runtime envelope for this contract; no rollover or reuse of old approval.
Historical evidence/thresholds, unknown UTC accuracy/incremental overhead/
continuous RSS/internal retries and v5 disconnect cause stay unchanged.

## October 20 — V5 interrupted; linked prefix retained and independently audited

**Historical application FAIL remains unchanged. V5 did not establish full-minute
coverage or normal acquisition completion.** One approved attempt ran from exact
source `f89ada8cb43036464cd77c08fe4ca7829fbc634a` (555 files), freeze
`7cd0b049ff9380aa405d5368bc197205363654244862c2f328d50a58e236f12f`.
[Outcome and integrity audit](PUBLIC_FEED_COUNTS_V5_OUTCOME_20261020.md);
[all 60 interval rows](PUBLIC_FEED_COUNTS_V5_20261020.csv).

Fresh gates passed; one controller, five metadata GETs and one private unit ran.
Independent controller and prompt live unit bindings verified identity, signals,
limits, ready/release linkage. Receive failed with
`ConnectionClosedError:no close frame received or sent` at M0+28.779829488s;
last-safe M0+28.710376203s. Cause unknown. Neither interrupt receipt fired and
normal completion is absent. Cleanup close returned, preserving the genuine
receive fault. Archive/completion/pre-close checkpoint/final consumer all survive
and link; successful OS exit is not scientific success.

32,722 linked texts: 17,070 prewindow, 15,652 primary-prefix, zero tail;
zero ambiguous or unplaced. All 60 independently recomputed rows match frozen
report: slots 0–27 unverified, 28–59 censored; feed-activity upper bounds null.
104 accepted foreign creation notices count once as unconfirmed/other-market.
No inference of zero missing activity, venue completeness or trading performance.

Original thresholds stand: one 26.181905ms UTC bracket exceeds 1ms; ten RSS
brackets exceed 5ms (maximum 255.716210ms). Resource qualification unknown;
32 sampled rows and no full 60s CPU window. Sampled RSS 74,436,608 bytes is not
continuous peak; whole-unit CPU is inclusive, not incremental overhead.

Independent sealed copy: 60 files/15,841,820 content bytes; all 36 producer
evidence files and 555 frozen source hashes match. Compressed SHA
`808dbf901ef68ae0cc04fd2e224124cc75a1e54e6a5d489d3c7ca9ef95904eed`.
Original archive witnesses/barriers verify. Public collectors/source/runtime/TLS
unchanged; exact worker/controller gone and private unit inactive/dead at16:06:33Z.
No retries, extra capture, resource or infrastructure changes. All historical
FAIL/not-run/partial evidence stays intact. Independent UTC accuracy, incremental
overhead, continuous RSS, internal retries and disconnect cause remain unknown;
credits are context, not a new gate. Private evidence:
`.qcrl/reviews/public-feed-20261020T160000Z/`.
The one-time follow-up is removed after final audit. No pending capture or rollover.

## October 19 — Exact v5 approved and staged; October 20 follow-up scheduled

User directly approved the exact v5 packet: “absolutely”. Separate confirmation
payload `6a13886dc3011b1c4151686695d6cd7eb2bd58128b907a9cf63fb82f60e6ae26`
binds one conditional capture to freeze
`7cd0b049ff9380aa405d5368bc197205363654244862c2f328d50a58e236f12f`.
Execution source remains `f89ada8cb43036464cd77c08fe4ca7829fbc634a`, 555 selected
files; later documentation HEAD must not substitute for it. No further routine
approval is required within the exact one-case scope.

Fresh read-only SSH at 21:52:01Z verified expected runtime/TLS/CA/public/boot,
6,174,232,576 free bytes and unused new namespace/unit. Staging completed once at
21:52:12Z at `/var/lib/qcrl-stream/public-feed-20261020T160000Z`, with all source
and readiness checks passing and 6,144,364,544 free bytes. The exact proposed
operator-receipt bytes were activated only after separate direct approval; their
template flags remain unchanged and do not themselves grant execution authority.
The frozen historical runtime-context record remains intact; these are separate
fresh receipts. Credit mode/balance were not refreshed; no minimum is inferred.

Independent 21:53:24Z readback matched local freeze, packet, confirmation, active
receipt and launcher bytes, root ownership/permissions, all 555 sources and native
runtime/TLS/public baseline. Controller absent, evidence directory absent, unit
not found; metadata GETs and native unit starts zero. No feed subscription or
launcher execution. These are native staging gates, not Linux validation of the
new notification/publication behavior or a resource/coverage acceptance result.

Prepared `launch-once.py` SHA
`b94e1b7a2866eb7c6eac897c15d5a3aaede8c641c7eda1382c3555fac82cb822`.
This transport accepts only October 20 15:44–15:55 UTC, waits at most 90 seconds
for 15:45, refreshes gates and exact confirmation, then durably/exclusively claims
one controller launch before default-signal/session/log Popen. It is not executed;
no remote scheduler is running. A prior launch/controller/evidence claim forbids
another launch. The controller owns the sole metadata and unit opportunities.

One-time follow-up `run-and-audit-the-approved-btc-v5-capture` is scheduled for
**October 20, 11:44 AM EDT / 15:44 UTC** to refresh gates, invoke the helper once,
observe only that attempt and independently audit/commit/push afterward. Arrange
required live unit binding promptly at arm time; a missed observation stays unknown.
Use exact frozen report code, including its close-unverified checkpoint path;
checkpoint-only evidence never becomes full coverage or verified close. The new
close stall is not claimed solved. Quiet on unchanged polling; notify meaningful
outcome/failure/blocker or necessary action, then delete the follow-up after final
audit or definitive not-run. Missing access/readiness/deadline means no rollover.
Controller 15:45–15:55; metadata 15:55; lock before 15:59; arm 16:00:40;
nominal count minute 16:01–16:02 UTC. No retry, replay, substitution, smoke or cohort.
All historical FAIL/not-run/partial/unverified evidence and original thresholds,
resource limits and public collectors remain unchanged. Private controls:
`.qcrl/reviews/public-feed-20261020T160000Z/`.

## October 19 — Historical v5 offline preparation before approval

[Prospective v5 packet](PUBLIC_FEED_COUNTS_SUCCESSOR_V5.md): October 20 BTC market
at noon EDT, count 12:01–12:02 PM. User authorized offline review/implementation
and proposal preparation. No SSH/native action or automation this turn. V4's
partial verdict, all 60 null rows and retained bytes remain unchanged.

A narrow structural exception accepts well-formed `new_market` creation metadata.
It remains a counted text, classified unconfirmed/other-market when appropriate,
never selected-market book state. Foreign book/trade/other bindings remain fatal.
The retained v4 event qualifies prospectively; its frozen source still rejects it.
This is not a repaired historical result or a venue routing guarantee.

The actual production worker seals acquisition and publishes existing completion
plus one durable, close-unverified acquisition checkpoint before socket close.
Final consumer remains after close. Checkpoint-only reports retain linked prefix
counts with censored/unverified coverage; they cannot establish full coverage.
Acquisition guard remains armed through publication at attempt+90 seconds;
separate five-second close guard and 240-second unit ceiling remain. Fired guards
survive cancellation. The underlying native close stall remains unproven, and a
future close-guard exit is still possible. No observer/bracket/threshold/resource
change, subtraction, guaranteed publication margin or diagnostic framework.

All 1,250 offline tests passed in 166.923 seconds on Intel macOS/Python 3.14.6;
49 focused checks passed in 12.627 seconds after additional boundary cases.
Actual production consume wiring, real SIGTERM blocked-close evidence retention,
notification/batch/ASCII/size/schema boundaries, failed publication, corrupt linkage
and guard callback/cancel races are covered. Python 3.9 syntax accepts changed
files locally. None of this is new Linux validation.

Exact source `f89ada8cb43036464cd77c08fe4ca7829fbc634a`, 555 selected files;
freeze `7cd0b049ff9380aa405d5368bc197205363654244862c2f328d50a58e236f12f`.
Seven-member packet 94,642 bytes, SHA
`0c1fd7a4db9edb05ceb8007a2ccb7da91ea897431c15025ae9ab6c7ec06c91c0`.
Member population, committed source hashes, policy bindings, original limits and
bundle independently verify. Expected runtime/TLS/public/host bytes are historical;
fresh Linux readiness is outstanding, with no invented credit minimum. Private
packet `.qcrl/reviews/public-feed-20261020T160000Z/`. Later doc HEAD cannot replace
that exact source. Active operator approval is absent; no native stage, capture
or follow-up automation is installed. Conditional exact-packet approval is required.
No additional smoke, cohort or rollover. Historical application FAIL and all
previous not-run/partial/unverified outcomes and thresholds remain unchanged.

## October 19 — Public v4 stopped on foreign notification; primary counts unresolved

The single approved attempt is **partial_or_unresolved**. [Audited outcome](PUBLIC_FEED_COUNTS_V4_OUTCOME_20261019.md)
and [all 60 null count rows](PUBLIC_FEED_COUNTS_V4_20261019.csv). Historical
application **FAIL**, v1/v2 not-run and v3 closure fault/unverified coverage remain
unchanged. No combined badge; no replay or new target.

Fresh readiness passed 15:44:12Z; one exclusive controller launch at15:45:00Z.
Five bounded metadata GETs, case lock15:55:01Z; one private unit arm16:00:40Z.
Exact source `706ebed052945235dd44e7a5c5ef6a231059576c`,552 selected files;
freeze `59c54d22966b2da993e5437aa8a7c7c39baf9002b7e0f475533eed892da8efea`.
The retained prefix records a foreign-condition `new_market` text at16:00:41.662Z,
then the declared fatal `explicit foreign asset/condition binding` gap. This is
not proof that ordinary selected-market book/price data was misbound. The rule
was preserved. SIGTERM exit5.005897sec later is consistent with the five-second
close guard; signal sender/exact close progress are unknown. Consumer/completion/
manifest/footer are absent. Public normal-stop ownership was not demonstrated.

Independent copy:45files/527,514 content bytes, all21producer evidence files and
552 frozen sources verified. Sealed363,917-byte copy SHA
`6839a795d68b20eda0ebbaae5f1c637f6bba5cd3a8396242ff58cab25062a122`.
Partial review payload `14e877392c33d93baa2062cc8a1e0ca7650d1699974f79d7aaa1f9dde3a84c1c`.
599 complete prefix record hashes/ordinals verify, including595text-frame rows;
gzip trailer and full completion linkage do not. Prefix bytes are not a full
returned population. Exact frozen report returns population null and60unresolved
rows; no zero filling or archive-time substitution. Inclusive primary resources,
widths/missed slots/overhead/continuousRSS/independentUTCaccuracy remain unknown.

Source/runtime/TLS/public baseline and original limits preserved. Retained unit
binding verifies; separate live worker signal/PID inspection missed its early exit
and is not marked passed. Unit inactive/dead, controller/worker PIDs absent; no
extra run. One-time follow-up `run-and-audit-the-approved-btc-v4-capture` deleted.
Private controls/evidence/audit `.qcrl/reviews/public-feed-20261019T160000Z/`.
Only a future offline review of global notifications and early-fault publication
is proposed; no implementation or native rerun is authorized by this outcome.

## October 18 — Exact v4 approved and staged; one October 19 follow-up scheduled

User directly approved the exact packet: “i absolutely approve”. Separate
confirmation payload `0482dc084662b488fd7edac8e41a2f0e1bc10207c11b34e60805e7a3233dcb19`
binds one conditional case to freeze
`59c54d22966b2da993e5437aa8a7c7c39baf9002b7e0f475533eed892da8efea`.
Exact source remains `706ebed052945235dd44e7a5c5ef6a231059576c` (552 files),
not later docs HEAD. No further routine approval is required within that scope.

Staged once at `/var/lib/qcrl-stream/public-feed-20261019T160000Z` on Ohio at
16:58:03Z October 18; source/runtime/TLS/CA/public/namespace verification passed,
6,179,475,456 free bytes. The proposed receipt's exact bytes were activated at
`operator-approval.json` only after separate direct confirmation; its template
flags remain unchanged and do not themselves establish authorization. Independent
17:00:02Z readback matches local freeze, approval/confirmation, packet and launcher
bytes; root ownership/permissions verified. Controller absent, metadata GETs zero,
unit absent, evidence directory absent; no feed subscription or launcher execution.

Prepared `launch-once.py` SHA
`e375f771fc64cb84a23c15845d907e7a816fc94be1f75cdf7a4d3c872ce0a98c`.
This control transport accepts only October 19 15:44–15:55 UTC, waits at most
90 seconds for 15:45, refreshes all gates, verifies separate exact approval and
exclusively records launch before one default-signal/session/log `Popen`. It is
prepared, not executed; no remote scheduler is running. Do not reinstall/relaunch
if any launch claim exists. No source or measurement change was made this turn.

One-time thread follow-up `run-and-audit-the-approved-btc-v4-capture` is scheduled
for **October 19, 11:44 AM EDT / 15:44 UTC** to verify fresh gates, invoke that
helper once, observe only the approved attempt, then independently audit retained
evidence and commit/push. Quiet on unchanged polling; notify meaningful outcome,
failure/blocker or necessary action. Delete it after final audit or definitive
not-run. Missing access/readiness/deadline means stop without retry or rollover.
Controller 15:45–15:55; metadata15:55; lock before15:59; arm16:00:40;
nominal counts16:01–16:02 UTC. All original limits/thresholds and historical
FAIL/not-run/unverified evidence remain unchanged. No extra run, smoke or cohort.

## October 18 — Historical v4 preparation checkpoint before approval

[Prospective target v4](PUBLIC_FEED_COUNTS_SUCCESSOR_V4.md): October 19 BTC
five-minute market at 16:00 UTC / noon EDT, nominal count minute 16:01–16:02 UTC.
One metadata opportunity 15:55 UTC, lock before 15:59; controller once within
15:45–15:55, private unit arm 16:00:40. Market existence/IDs unknown until that
opportunity; no substitution, retry, replay, reconnect or rollover.

Plan SHA `359488dc8de8d90508f905411cc3734d5ce78acf763d951813b606fd71354d73`.
The v3 dictionary/hash and all prior evidence remain intact. New plan binds the
StopOwn01-tested ownership policy at the production worker gate. No observer,
measurement, counting or budget change. Existing UTC/RSS/resource unknowns persist.

Read-only pinned SSH at 15:55:56Z October 18 verified installed runtime/TLS/CA,
public baseline, unchanged boot, 6,209,163,264 free bytes and unused new namespace/
unit. Fresh credit mode/balance unavailable after earlier expired SSO refresh;
no inferred balance/minimum gate. This is preparation context, refreshed again
before any future execution. No metadata GET, feed subscription or native unit.
Private packet: `.qcrl/reviews/public-feed-20261019T160000Z/`.

All 1,240 individual tests passed offline across discovery plus the omitted
12-test import-path recovery; initial loader error is retained in the packet.
The 39 focused tests passed. Python 3.9 syntax accepted locally; no new Linux run.

Execution source `706ebed052945235dd44e7a5c5ef6a231059576c`, 552 selected files;
freeze `59c54d22966b2da993e5437aa8a7c7c39baf9002b7e0f475533eed892da8efea`.
Seven-member packet 109,850 bytes, SHA
`4526f4ef04481d05f6bdff2bc5154b8848dc072e23bcc969057ed290bee0142e`.
Member population, committed source hashes and bundle verified independently.
Later doc HEAD must not replace frozen source. Only a proposed approval template
exists; active operator approval is absent. See v4 doc for exact controller argv.

Exact packet approval is pending. No native staging/controller/scheduler or
follow-up automation is installed. The original application FAIL, public v3
closure fault/unverified coverage and earlier not-run outcomes stay unchanged.

## October 18 — StopOwn01 native functional validation independently audited

One authorized Linux loopback case ran once and stopped; [outcome and limits](PUBLIC_STOP_OWNERSHIP_OUTCOME_20261018.md).
All 68 planned texts match peer, ordered archive and verified completion witnesses,
including 22 durable barriers, matching footer and zero gaps. Normal ownership is
`acquisition_thread`; neither emergency interrupt fired, and no acquisition,
terminal receive or close fault was retained. One native test completed in
85.202 seconds, exit 0; unit is inactive/dead and native PID absent.

Exact source `db25a2db79c53af28e38ba6531f0bba21ebd224b`, 550 selected files;
freeze `6861db15528c43baa1d4a0cd3c8b4350dc6c3b8ab6ae240d9a888cc48c4c3c57`.
Fresh read-only gates passed October 18 at 13:29Z; one exclusive unit submission
at 13:31:16Z. Original 512 MiB / 75% / 32 tasks / 240-second limits and public
collectors preserved; no public feed or metadata request. No retry or extra run.
Fresh credit context unavailable (expired SSO refresh), not inferred or a new gate.

Independent copy verifies 23 files / 436,091 content bytes, all 22 producer entries
and all 550 frozen sources. Sealed SHA
`fcfdccbe7ffc57c5ee04046a4215cce0bd6972d89661d1a5eb2a8e75446024d1`;
independent functional-review payload
`249d7baaa063d6f0c2b4dffca98297cde267e3d010d6552a8ddd30ddf6a84ded`.
Private packet/evidence: `.qcrl/reviews/public-stop-validation-StopOwn01/`.

This demonstrates the declared normal-stop functional case on Linux. Offline
fault tests remain offline; no TLS/public-feed/resource-budget acceptance follows.
Historical application **FAIL**, prior public v3 closure fault/unverified coverage,
both earlier not-run outcomes, every threshold and unknown remain unchanged.
No combined acceptance badge. Nothing further is running or scheduled; a future
public target requires its own prospective identity and authorization.

## October 17 — Historical offline implementation and validation proposal

Implemented [prospective stop ownership v1](PUBLIC_ACQUISITION_STOP_OWNERSHIP_V1.md).
The acquisition thread claims normal completion and disarms the socket interrupt
under the same lock before local close. Emergency callback/cancellation ordering
is exclusive; fired/peer/receive/send/close faults never become success. Fresh
claim time must precede the emergency cutoff, even if the callback was delayed.

Policy SHA `dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3`.
Normal stop target remains unchanged. Emergency separation is prospectively
250 ms, capped at the existing 90-second acquisition deadline. Default-SIGTERM
acquisition and five-second close guards preserve bounds; the native unit still
has its 240-second ceiling. No call or lock is added inside original measurement
brackets. Added control work/guard threads are uncalibrated, never subtracted.
New coverage reports require linked, ordered, policy-bound ownership receipts.

Offline tests cover actual writer/witness/WebSocket normal timeout, real blocked
receive/subscription/heartbeat writes, peer closure, deadline equality/stale clock,
callback-first/cancel-first/normal-first races, invalid claim clock, receipt
linkage and a subprocess killed during blocked close with retained partial data.
All 1,240 offline tests passed in 134.043 seconds on Intel macOS/Python 3.14.6,
including 39 focused public-runtime/stop tests. Changed files accept Python 3.9
syntax locally; none of this is Linux validation.

One proposed **StopOwn01** loopback validation: 60 frozen synthetic texts plus
eight PONG replies, expected 68 linked texts, real clocks, about 85 seconds plus
bounded setup/close/publication. Peer holds open; must finish by normal ownership,
not frame cap. Plan SHA
`9702f4e923b99873dd4d4a7d641e9be634dbadd3d81f6991dc1b70230c35d808`.
Only the existing completion verifier is used; no new observer/auditor framework.
No TLS/public-feed or resource-budget claim. Execution candidate
`db25a2db79c53af28e38ba6531f0bba21ebd224b`, 550 selected files; conditional freeze
`6861db15528c43baa1d4a0cd3c8b4350dc6c3b8ab6ae240d9a888cc48c4c3c57`.
Packet SHA `e994325057570d33836183781bf72a84f032238ce0de21ecca7ac597da0d93a6`,
91,690 bytes, five members and all source hashes verified offline. Expected
installed runtime is retained historical context, **not newly verified**; fresh
native gates and explicit one-case approval are required before staging/execution.
Private packet: `.qcrl/reviews/public-stop-validation-StopOwn01/`. Later docs HEAD
does not replace this candidate. No SSH/native run or automation
was started during this offline implementation. Historical v3 closure fault,
all original FAIL/unknown/not-run outcomes and thresholds remain untouched.

## October 17 — Public-feed v3 audited; closure fault and coverage unknown

One authorized capture ran and stopped. [Outcome and limits](PUBLIC_FEED_COUNTS_V3_OUTCOME_20261017.md)
and [all 60 count rows](PUBLIC_FEED_COUNTS_V3_20261017.csv). Historical application
**FAIL** and both earlier **not_run** outcomes remain unchanged; no combined badge.

Independent copy/hash/source review verifies 59 files / 15,358,101 content bytes,
all 35 producer evidence files and all 547 exact frozen source entries. Sealed
copy SHA `ada4841cc5ead9c0e2bcb82e0376135e0f94c42f80f24ec33863044d7a03bcd6`;
independent retained-audit payload
`3d0d239508f51686bf5004176891f20f3ff1e2536806fa18c454d1799e951147`.
Original producer flags/evidence are intact. Frozen source remains de4c10b;
freeze `b4bb07c78cf5558fea2befe1b7611166678f00344ba6664d942fd6becbe8d7ed`.

Full archive/completion/domain/case linkage verifies 31,434 returned texts:
7,221 prewindow, 21,941 primary-minute, 2,272 tail. One occurrence straddles
bins 20/21; bounds [325,326] and [243,244], other 58 bins exact for archived
population. Zero unplaced; second exact-fraction calculation reproduced every row.
All coverage remains **unverified**, and feed-activity upper bounds remain unknown.

Retained fault: `transport already closing at stop; closure timing unknown`.
The deadline watchdog fired, but its causal role is unproven. One gap record;
the frozen normal-completion predicate fails. Neither final near-deadline frame
nor successful unit exit repairs this. Original UTC bracket violation: one at
4.763 ms. RSS: 23 of 67 brackets exceed 5 ms, no missed resource slots; resource
qualification remains unknown. Qualified inclusive 60-second CPU upper fraction
0.447429489 of effective quota; incremental overhead/continuous RSS peak unknown.
No append/durability worst violation. Original thresholds remain authoritative.

Independent post-check found scheduler/controller gone and unit inactive/dead;
source/runtime/TLS/public baseline unchanged. No replay, restart, new target,
extra experiment, observer optimization or resource change. The one-time audit
follow-up has been deleted; future capture needs its own authorization.
Private archive, controls and audit: `.qcrl/reviews/public-feed-20261017T183000Z/`.

## October 17 — Historical new capture staging and deployment checkpoint

Exact execution source `de4c10bf3f53bb4fd4ab3646c22a7d5e3fc1536c`, 547 selected
files, freeze:
`b4bb07c78cf5558fea2befe1b7611166678f00344ba6664d942fd6becbe8d7ed`.
The new stage `/var/lib/qcrl-stream/public-feed-20261017T183000Z` verified source/
runtime/TLS/public/namespace gates at 18:00:31Z. Transport SHA:
`91db072bcf16bf82c65a00fd72a1ff3f30aaff33ca76cc8d9c81b8e6c282e621`.

One exclusive finite scheduler deployed at 18:01:25Z (2:01:25 PM EDT), PID
1720744; exact bytes/hash and root launch receipt retained privately. Independent
readback matched freeze/authorization/scheduler bytes and live PID command line;
neither SIGHUP nor SIGTERM is ignored. Scheduler SHA:
`6d588b5035df9da3949d042abb22cf449290f96c6aed3f9bf1b26e02f776f25a`.
No controller claim, evidence directory, launch failure or recorder unit existed
at deployment/readback; metadata GETs were zero. It waits until 18:15Z and performs
fresh gates before at most one controller submission inside 18:15–18:25Z. Metadata
once at 18:25, lock before 18:29, arm 18:30:40; count nominally 18:31–18:32 with
five-second tail. Missing gates mean stop, never another epoch or attempt.

The existing follow-up now runs October 17 at 2:34 PM EDT to inspect and audit
only this already-deployed attempt; it must not relaunch anything. Do not restart
the scheduler if it fails. Independent copy/hash/archive/population/count/resource/
clock/coverage review remains pending. The native public adapter remains unvalidated
until evidence supports a bounded conclusion. All historical FAIL/not-run outcomes,
thresholds and unknowns stand. [Full declaration](PUBLIC_FEED_COUNTS_SUCCESSOR_V3.md).
Private packet/readbacks: `.qcrl/reviews/public-feed-20261017T183000Z/`. Later doc
HEAD is not execution source. Public collectors and historical stages are untouched.

## October 17 — New public-feed target v3 declared prospectively

The user's “please proceed with setup and deployment of a new capture” authorizes
one new conditional target. [Declaration](PUBLIC_FEED_COUNTS_SUCCESSOR_V3.md):
`btc5m-20261017T183000Z-local-counts-03`, BTC five-minute 18:30–18:35 UTC
(2:30–2:35 PM EDT), nominal counts 18:31–18:32 UTC. One metadata opportunity
18:25 UTC, lock before 18:29, arm 18:30:40. Policy SHA:
`6cdc0386787c0a6bd68ac0061e59c6f50b657dfac19f2ec27bd056f336488533`.
Prior v1/v2 dictionaries and literal regression hashes remain intact. Only
identity/window/namespace change; method, transport, observers, thresholds and
resource/storage budgets are unchanged. Missing gates mean retained not-run or
partial evidence and stop, with no substitute/retry/replay/rollover.

Fresh read-only Linux checks at 17:57:11Z verified the historical source/runtime,
current TLS modules/CA, actual mandatory-verification context (143 certificates),
public state/source/environment and about 6.3 GB free disk. No metadata/feed
request or unit ran. All 1,228 local tests passed in 153.665 seconds; all 27
focused tests pass and changed files accept Python 3.9 syntax. Exact source/
freeze/deployment receipts follow after completion. Local tests are not Linux
public-adapter validation. Fresh AWS context reports standard credit mode and
latest reported balance 576 at 17:54 UTC, with no credit acceptance minimum.
NTP reports synchronized, without an independent accuracy bound. A finite,
exclusive launch scheduler may wait
for the fixed controller window without creating a unit or making data requests.
Historical application **FAIL**, both expired **not_run** outcomes, evidence and
all measurement unknowns remain intact. No combined acceptance badge.

## October 17 — SSH access independently verified

The user installed the existing Mac public key through their own AWS session,
reported successful SSH access and instructed continuation. A strict, pinned SSH
connection then independently succeeded as `ec2-user` at `17:54:52Z`. Only
`id -un`, `hostname` and UTC time were read; the hostname matches the documented
private host. No experiment, service, resource, networking or evidence changes
were made. [Operator access](AWS_OPERATOR_ACCESS.md) records the setup and checks.

Correction to the earlier checkpoint: the browser tool prohibited the denied
console operation and workarounds achieving the same outcome. Treating this as
a categorical prohibition on all independent SSH/API/SSM operations was the
agent's overly broad interpretation, not an explicit global tool restriction.
No SSM key-installation operation was submitted or denied. The user performed
the key installation; browser access has not been retested or claimed restored.

SSH and named-profile API authentication now work. Both expired public-feed
targets remain **not_run**, historical application **FAIL** and original thresholds
stand. No expired controller, new capture, smoke or cohort was launched. Another
public-feed window requires its own prospective declaration and readiness gates.

## October 17 — Historical SSH host verified; local key rejected checkpoint

Following the user's request to complete SSH setup, authenticated read-only EC2
APIs verified the current instance/IP binding and retrieved its console host-key
record. Independently hashed and pinned the console ED25519 public key locally;
the live SSH server matched that pin. A bounded authentication-only SSH check
requested no shell, command, password or forwarding and failed with `Permission
denied (publickey,gssapi-keyex,gssapi-with-mic)`. Host verification is complete;
the existing local key did not authenticate. Server-side cause remains unknown.

No remote key installation or host command occurred. The effective browser
denial explicitly prohibits alternate execution routes, preventing SSM key
installation while that restriction persists. User authorization is clear;
tool enforcement is the remaining blocker. Read-only API responses, console
record, local known-hosts backup and authentication receipts are retained in
`.qcrl/access-setup/20261017/`. See [operator access](AWS_OPERATOR_ACCESS.md).
Both targets remain **not_run**, historical **FAIL** remains unchanged, and no
experiment, resource change or evidence modification occurred.

## October 17 — Historical local CLI/SSO access established checkpoint

At the user's request, prepared [AWS operator access](AWS_OPERATOR_ACCESS.md).
Official signed Intel packages supplied user-local AWS CLI 2.38.1 and Session
Manager plugin 1.2.896.0 without Homebrew, sudo or replacing the existing CLI.
The new `qcrl-ohio` profile uses the existing account/AdministratorAccess role;
the user confirmed the Identity Center region as Ohio and completed device login.
A bounded STS identity API call succeeded and verified the expected account and
role. Default profile settings and the existing credentials file remain unchanged.
No tokens, private keys or device codes are included in tracked documentation.

Prepared the local `qcrl-ohio` SSH alias with the existing key and strict host-key
checking. No pinned host key exists for the documented IP; current IP binding and
remote public-key authorization remain unverified. No SSH connection, SSM session,
Run Command, instance command, IAM/network change or experiment was attempted by
this setup. Effective local SSH configuration, wrapper shell syntax and tool
versions verify; these are local checks, not Linux runtime validation.

Browser enforcement still denied the console origin after the user's removal of
site exceptions. API authentication does not resolve that browser gate, and no
alternate transport was used to perform the blocked host actions. Both fixed
public-feed targets remain **not_run**; historical application **FAIL**, thresholds,
frozen evidence and all measurement unknowns stand. Neither expired packet may
be revived. Private installation and identity receipts are under
`.qcrl/access-setup/20261017/`.

## October 17 — Approved successor missed access/readiness cutoff: not run

[Successor v2 outcome](PUBLIC_FEED_COUNTS_SUCCESSOR_OUTCOME_20261017.md).
Direct study approval was received in time. Browser enforcement nevertheless
denied the AWS origin despite an explicit local config allow and the user's
visible Always allow setting. The cause of that mismatch remains unresolved.
The fixed 12:55-PM EDT opportunity passed without completed staging/readiness.
Successor v2 is **not_run**; original v1 remains not run and historical application
verdict remains FAIL. No new combined acceptance badge.

The agent launched no successor staging script, controller, HTTP request, feed
connection or recorder unit, and made no public/infrastructure changes. Last
observed remote state was an inert packet only; independent fresh remote state
after the browser denial is unavailable. No policy workaround, late adoption,
retry, rollover, new target or new automation. Resolve origin access read-only
before proposing any other prospective window; do not execute this expired packet.

Direct-confirmation payload SHA:
`9848b52278396adc33446ab53f525864b3d087b174c2eb0d2339107dd42f21a3`.
Local access-not-run receipt SHA:
`638fdde4debdf77143548815ad4953d13666e7123d35d40917daf48ca715a958`.
Both, the user permission screenshot and exact packet remain in the private v2
review directory. All 60 relative slot counts are null/not-run, with no invented
epoch or population. Every measurement/resource unknown remains unchanged.
Following sections are historical checkpoints, not permission to resume.

After the user's Codex update/restart and Chrome update/restart, a read-only
access retry at approximately 1 PM EDT could observe the AWS sign-in page but
was still denied navigation to the Ohio console origin by the saved-permission /
managed-policy gate. Restart did not resolve the observed enforcement mismatch.
No alternate browser surface, policy bypass, remote command, new staging or
capture was attempted. The origin blocker remains unresolved; both outcomes and
all frozen evidence remain unchanged.

## October 17 — Historical direct approval and browser-origin access checkpoint

The user directly approved staging and one bounded 1-PM EDT target under freeze
`4c25a8b5dcf31b55abbfecb3faff7adb46c57f8abe021523908e6fad6804d79d`.
Direct confirmation is retained privately in the successor review directory as
`execution-confirmation.json`; it is separate from the immutable proposal receipt
that originally marked exact-window approval pending. No further study approval
is required for this exact packet, subject to all declared gates and deadlines.

At 12:42 PM EDT the browser independently denied permission to observe the AWS
console origin. After the user's permission-setting attempts, access checks still
reported a saved permission or managed-policy deny at 12:47 and 12:51 PM EDT.
The local configuration already contains an allow for the exact HTTPS origin;
that does not override the browser's separate saved/managed decision. No policy
file, browser database, alternate browser surface, SSH/CLI path or other workaround
was used to bypass the denial. Only local read-only configuration diagnosis and
official permission guidance were consulted.

Checkpoint: uploaded inert packet only; no staging script or successor launcher
executed, no controller claim, HTTP request, feed connection or native recorder
unit started by this agent. Exact-checkout staging/readiness remains outstanding.
Prepared launch wrapper requires the direct confirmation's literal hash and the
unchanged freeze. If access/readiness is not restored before the fixed 12:55 PM
EDT opportunity, retain this target as not run; no rollover/retry or adoption of
a later epoch. Earlier approvals remain historical, not permission for another
window. Original target not-run and historical application FAIL remain unchanged.

## October 17 — Historical CA repair and successor proposal checkpoint

In response to “can you retry now?”, implemented the targeted offline CA fix and
prepared [one prospective successor proposal](PUBLIC_FEED_COUNTS_SUCCESSOR_V2.md),
case `btc5m-20261017T170000Z-local-counts-02`. Exact new policy SHA:
`220e1b592365b33dd5e0e4c46ab53103735f4add634694aba4cb745a7fa0adff`.
Original v1 declaration remains verbatim in `ORIGINAL_PLAN` and its regression
hash remains pinned. Original 16:00 target remains **not_run**, all historical
application-budget verdicts remain FAIL, and every threshold/measurement limit is
unchanged. This is a new proposal, not permission to resume the used stage.

Proposed event October 17 at 1:00–1:05 PM EDT; metadata once at 12:55 PM, exact
lock before 12:59 PM, nominal count minute 1:01–1:02 PM. New namespace only;
one private unit/connection, unchanged caps, no reconnect/replay/substitution.
Exact-window confirmation remains pending; no successor controller, HTTP request,
subscription, recorder unit or new automation has started.

The loader passes a byte-verified private anonymous CA snapshot to OpenSSL's file
interface, preserving trust roots and mandatory hostname/certificate verification.
Readiness now constructs the context before HTTP. Focused tests cover non-ASCII
comments, malformed/empty/oversized PEM, hash/profile drift, original-path race,
snapshot permissions/cleanup and the actual readiness path. Read-only Linux
context preparation at 12:27:11 PM EDT loaded 143 CA certificates from the original
pinned bundle with mandatory verification and no network connection/unit.
This is limited context readiness, not native recorder compatibility or budget
validation. Newly used installed `tempfile` module bytes are included in the
successor runtime inventory. All 1,228 local tests passed in 179.786 seconds;
27 focused tests also pass after the final module-inventory addition. Python 3.9
syntax parsing passes, without claiming native test-suite validation. Private preparation:
`.qcrl/reviews/public-feed-20261017T170000Z/`. Candidate/freeze and final regression
receipts follow after sealing. Following sections are historical checkpoints.

Sealed candidate `33cba4a4b38b0b9f0f77e00199f5cc0631b8726b` (544 selected files),
pushed; full freeze
`4c25a8b5dcf31b55abbfecb3faff7adb46c57f8abe021523908e6fad6804d79d`.
The 73,219-byte packet is uploaded inertly and matches transport SHA
`17324ee17c94e9a4f0af253e442a31dfbfb51324304e272dc6ef556991e8c147`.
Automatic approval review rejected executing its root staging script, saying the
retry request did not clearly authorize this exact successor deployment and the
generated script was uninspected. The script has now been inspected locally; no
workaround/repeated execution occurred. Its SHA is
`4c41f2cbb21e40d48e59e008f2819cf5a59f5ad54a2f3fa4293a55fb894af0c8`.
Observed new stage contains only `stage-packet.b64`: source is not unpacked, no
controller claim/evidence exists. Fresh exact-checkout readiness is outstanding.
The successor document is the executable approval packet: request direct approval
for that bounded staging and the single 1-PM EDT target together, conditional on
all fresh gates, before 12:55 PM EDT. No timing has rolled forward automatically.
Later doc commits do not replace 33cba4a. Preserve both old stage and outcome.

## October 17 — Fixed public-feed target stopped before HTTP: not run

**Historical application-budget verdict remains FAIL; no combined badge.**
[Outcome and independent retained-evidence audit](PUBLIC_FEED_COUNTS_OUTCOME_20261017.md).
The one controller began at 11:50:47 EDT after renewed AWS sign-in and matching
fresh source/runtime/TLS-byte/public/namespace/disk gates. At 11:55:00.575922 EDT
the single metadata opportunity failed constructing the pinned CA context:
ASCII decoding encountered byte 0xc5 at offset 129802. This happened before any
HTTP request. Retained traceback identifies the exact frozen adapter call;
the outer controller error is a nonzero helper exit.

Disposition is **not_run**, not a zero-count recording. No market identity was
locked; zero HTTP requests, feed connections and recorder units. Controller
exited; post-checks at 11:56:55 EDT match source/runtime/TLS/public baseline and
confirm no matching study unit. No retry, substitute, rollover or extra experiment.
Public collectors, resources and original evidence remain unchanged.

All 21 retained files / 619,691 file-content bytes copied independently and match
their complete selected inventory. Sealed archive SHA:
`8e19d8939e2cf028b8534a58ab68686055dfe6299ac683753fb8fdab48fb17fc`.
Not-run audit payload SHA:
`93d216ca9b73f9c2f8004f366b74f16511605d51b3be1c89fb3ce05ca8f721f5`.
Private directory remains `.qcrl/reviews/public-feed-20261017T160000Z/`.
Exact 3ec2f92 source is retained and all 542 frozen entries independently verify.
No observer timing/resource sample population exists for this target; every one
of the 60 relative report slots has null counts and not-run coverage, without an
invented epoch. Market availability/IDs, incremental overhead, continuous RSS
peak, independent UTC accuracy and real-market completeness remain unknown.

Offline reproduction with the actual frozen TLS function and a valid synthetic
CA fixture confirms the ASCII assumption is too restrictive; OpenSSL's verified
file loader accepts the non-ASCII-comment fixture. Provenance checks did not
exercise context construction. Recommended next work is a prospective binary-safe
same-bundle TLS load and offline readiness/fault tests; no production patch or
new window is adopted here. The scheduled one-case attempt is over. Following
sections are historical checkpoints, not permission to resume this used stage.

## October 16 — Historical fixed public-feed implementation and preparation

**Historical application-budget verdict remains FAIL; no combined badge.**
The user subsequently authorized regular commit/push and proceeding with the
proposed target. [Prospective execution contract](PUBLIC_FEED_COUNTS_EXECUTION_V1.md)
implements only `btc5m-20261017T160000Z-local-counts-01`, subject to its exact
source/runtime/public/disk/market readiness gates. The original draft below is
preserved. No observer optimization or additional smoke/cohort is authorized.

New separate public transport, controller and independent interval report retain
the original timestamp operation, measurement semantics, thresholds and failed
evidence. Fixed policy SHA:
`90fe9a6a7fc6fd0ba78b1a1d6218188cfd7399dd06cbd5bae02de870e2f56d32`.
One metadata attempt October 17 at 15:55 UTC, 30 seconds maximum; exact market
lock before 15:59; unit arm 16:00:40; nominal counting 16:01–16:02 UTC (12:01–12:02
EDT). Market existence/IDs remain unknown until that opportunity. No substitute,
retry or rollover if any required gate fails. Retain partial evidence and stop.

Private preparation receipts:
`.qcrl/reviews/public-feed-20261017T160000Z/`. Read-only Linux inspection October
16 at 22:49 UTC found boot `c2c6dde4-9394-4b65-a1aa-87389cbf3538`, 6,316,806,144
free disk bytes and unchanged historical source/runtime/public collectors.
Installed runtime payload SHA:
`4dac9c24b3ec1350a627f3316e50060a97e58d57139b4d816a9dc22b1d801f0c`.
At 22:58 UTC the socket/TLS modules, OpenSSL 3.5.8 libraries and system CA bundle
were independently hashed through Session Manager. At 23:12 UTC the proposed
new stage and unit namespace were absent; NTP reported synchronized, which is
context rather than an independent UTC accuracy bound. These are provenance
inspections, not native public-adapter validation. Historical credit context is
not refreshed by them; no new credit minimum or acceptance gate is invented.

Twenty-two focused local tests pass, including actual writer/completion paths,
stop-race closure, blocked socket/subprocess faults, clock failure and missing
receipts. A separate local verified-TLS blocked-write check passed; local OpenSSL
3.5.7/Python 3.14.6 differs from Linux OpenSSL 3.5.8/Python 3.9.25. Python 3.9 syntax
parsing passes and does not constitute native execution. The complete local suite
passed all 1,223 tests in 135.465 seconds, including existing localhost fixtures.
Source freeze and staging receipt will be recorded below after completion.

Exact execution source is `3ec2f92b16b6d1334770acc25c4869f18868ea63`, pushed to
the development branch; 542 selected source files match its clean inventory.
Full prospective freeze:
`02942f3bfbbf45d78ed818fe3c574546ded4fdf7d49fe4720107aefc240d18a8`.
Packet transport SHA:
`e8b2909a13d5db8aec4fec4bd4c7c18904275818f568c021133baca0e2533ac3`.
Staged only in `/var/lib/qcrl-stream/public-feed-20261017T160000Z` on the existing
host. At 23:28:45 UTC, observed installed-interpreter verification matched source,
runtime, TLS/CA and public baseline, and confirmed no controller claim, evidence
directory or matching native unit. Staging receipt payload SHA:
`c2faba03efa97cdc1f785f9a0a9867adb52b4b57b7b973f9294c25516170edff`.
An incomplete browser packet transfer was retained as a partial file; a subsequent
transfer matched the transport hash before extraction. This was staging, not a
metadata/capture retry. No historical file or public service was changed.

The app follow-up is bound to this exact freeze and staged checkout. Later
documentation commits do not replace the execution candidate. Refresh gates
tomorrow before one controller start in the fixed preparation window; use the
installed interpreter with normal signal dispositions, `start_new_session=True`
and a retained log, not `nohup`. Root claim publication prevents resumption.
Native public-path compatibility remains unestablished until this single
descriptive acquisition; no extra standalone test is inserted. Missing gates or
deadline leave the target not run. After acquisition, stop and independently
copy/hash/audit; never infer origin from producer flags alone.

One app follow-up is scheduled for October 17 at 11:45 EDT (15:45 UTC), before
the fixed metadata slot. It depends on app/access availability. Controller rejects
early starts outside 15:45–15:55 UTC. No controller, metadata GET, feed subscription
or native unit has started during this preparation. Preserve public collectors,
historical stages, quotas and all original unknowns, including incremental
observer overhead and continuous RSS peak. Following sections are history.

## October 16 — Historical draft checkpoint; no authority at that checkpoint

[Prospective study draft](PUBLIC_FEED_INTERVAL_COUNT_STUDY_DRAFT_V1.md), identity
`qcrl.public_feed_interval_counts.study_draft.v1`. Proposed one BTC five-minute
Up/Down market with exact terms October 17, 2026, 16:00–16:05 UTC (noon EDT), both
outcome tokens; existence/IDs not verified. Nominal counting minute 16:01–16:02 UTC,
with one fixed recorded monotonic epoch and 60 interval-aware local bins. One
metadata attempt / fixed approval cutoff; absent readiness/approval means not run,
never automatic rollover or substitution. This is a draft, not an adopted packet.

Counts include every returned supported text occurrence; preserve ambiguous-bin,
unplaced, pre/tail and censored denominators. UTC labels are nominal without an
independent accuracy bound. One connection attempt, zero reconnects; first gap /
fault / cap stops, retains prefix and leaves dependent bins unknown. Five-second
tail, 90-s acquisition cap, 60,000-frame limit, existing bounded segmented storage
and 512-MiB/75%-CPU/32-task/240-s private-unit ceiling; no public resource changes.

Public transport readiness is outstanding: isolated completion worker currently
requires offline/loopback transport and legacy public lifecycle has incompatible
defaults. No guard bypass or implementation here. Need separately reviewed public
integration, offline fault verification, exact IDs/source/runtime/host freeze and
explicit one-case approval before any capture. Stop observer optimization.

Original application verdict remains FAIL; no combined badge. Synthetic interval
results describe those recordings, not venue completeness or real-market performance.
No metadata/feed capture, remote access, native run, credentials, infrastructure,
QC sync, rollout or trading authorized. Following sections are history.

## October 16 — Component contract drafted; retained-evidence question answered

**Original application-budget verdict remains FAIL. No new combined badge.**
[Draft component contract](RECORDER_COMPONENT_EVIDENCE_DRAFT_V1.md), identity
`qcrl.recorder_component_evidence.draft.v1`, is not adopted/frozen/executable or
execution-approved. [Small retrospective report](RECORDER_COMPONENT_REPORT_20261016.md)
keeps original archive/completion, timing, CPU and RSS findings separate, with
all original UTC failures and resource unknowns prominent. No contract execution.

Concrete question: do one-second local timestamp-observation counts resolve the
ten-second burst in the original three mixed cases, with boundary ambiguity?
All 180,000 occurrences retained. Every burst bin has >=2,986 certain observations;
no low-rate bin has >514 possible observations. 179,999 intervals fit one bin;
mixed-0 sequence 43496 straddles bins 36/37 and stays an original UTC failure.
Mixed-2's final occurrence falls in bin 70 and is retained. Seven wide-UTC rows
are included without requalification. This answers local synthetic coarse-count
description, not real-market flow, true UTC alignment or exact recv/venue times.

All 208 cohort origin files/218,570,554 bytes and original byte anchors reverify;
exact-rational binning agrees with independent direct interval scanning and fault /
edge checks. One-off report retained privately; public method/results/hashes in
the report. Current-source acceptance was not substituted for frozen audit.
No production/threshold/observer change, native run, cohort or execution approval.
Incremental overhead/continuous RSS remain unknown. Following sections are history.

## October 16 — Bracket requirements reviewed; recommend narrower claims

[Requirement rationale, dependencies and recommendation](RECORDER_BRACKET_REQUIREMENTS_REVIEW_20261016.md).
The 1-ms UTC and 5-ms resource ceilings are binding frozen design assumptions,
not derived sufficiency guarantees for one-second analysis. UTC width bounds
local timestamp acquisition, not absolute UTC accuracy or exact library-return
time. RSS width bounds a sequential full-reader sweep, not an atomic snapshot,
continuous peak or incremental overhead. The same 5-ms width also qualifies CPU
window endpoints. Archive fidelity, monotonic completion measurements and valid
CPU windows retain separate meaning when UTC/RSS qualification fails.

Recommend a prospective component/descriptive evidence scope with actual timing
intervals, explicit ambiguous-bin/slot coverage and full population accounting;
do not label it an original application-budget pass. This recommendation is not
an adopted successor contract. Preserve every old threshold and failed verdict.
If a specific research need requires both strict uniform guarantees, it calls
for a materially different bounded acquisition architecture and new measurement
identity, not further micro-optimization alone. No implementation, threshold
change, new native test or execution authority. Four UTC failures remain a
separate blocker to the original claim. The following sections are chronology.

## October 16 — Quota reuse v1 implemented offline; no Linux run justified alone

[Implementation, complete-input review, tests and benchmark](RECORDER_QUOTA_REUSE_V1_20261016.md).
Prospective identity `qcrl.resource_quota_reuse.v1`; reader source SHA-256
`8cf1450a19a3d0ff95d3d878f4aaed435151ec259baebd2c275e8bbec3c2d7f3`.
Full ordered dictionary/list equality covers every quota/controller/CPU-set/path
input and ancestor structure, plus memory limits. Validate first fresh snapshot
once inside the original bracket; reuse only within this read. Changed closing
snapshots still undergo validation before the original race error. All fresh
I/O, measurement semantics, clocks, publication and thresholds stay unchanged.

Local discovery: 1,200 passed in 153.739 s; final quota module 7/7 passed,
including the added boundary test. Changed/malformed ancestry, structural/cap
boundaries, membership/PID/path/I/O races and publication linkage are covered.
Python 3.9 syntax passes locally; no installed Linux/native validation claim.

Offline paired benchmark, original vs successor: three-ancestor in-bracket
validation 118.237 → 59.784 microseconds; median paired saving **0.059655 ms**.
This is only 0.306–0.913% of retained 6.532–19.520-ms native wall widths, with no
cross-machine speedup guarantee. Total validation saves 0.116527 ms including
after-bracket work; full-reader paired measurements are noisier. **Do not spend
a standalone native run on this alone.** No new timing layer or native rerun.

The four UTC failures (7236, 11693, 12410, 24142) remain a separate blocker.
All eight RSS unknowns, failed verdicts and historical thresholds/evidence remain
unchanged; prior archive/audit anchors match. Incremental overhead/continuous RSS
peak remain unknown. No six-case cohort. The following sections are chronology.

## October 16 — Offline RSS path review; one optimization proposed only

[Parsing, allocation, file access, locking and repeated-work review](RECORDER_RSS_PATH_REVIEW_20261016.md).
Reader source still matches the frozen native candidate exactly. An existing
three-ancestor/one-actor offline fixture confirms 48 text requests (40 reads,
eight expected absences), four identity calls, two membership/path passes and
three quota validations: two inside the wall bracket, one afterward. These are
operation counts, not native substep timings or a syscall/allocation profile.

Propose only per-read quota reuse: validate first fresh ancestry once, retain
its effective quota locally, and reuse it if the second fresh snapshot matches.
On mismatch retain closing validation before the original race error. Keep all
file reads, actor/identity/membership/path checks, RSS parsing, wall/CPU endpoints
and thresholds. This removes one redundant validation inside and one after the
bracket, with no measured saving or compliance guarantee. No implementation,
new production instrumentation, native rerun or cohort is authorized by this review.

Alternative sources/cached or narrower RSS must be distinct measures unless
equivalence is demonstrated; cgroup memory.current is not the current VmRSS sum.
The four UTC failures (7236, 11693, 12410, 24142) remain separate and unresolved.
RSS optimization does not establish UTC coverage. All eight RSS unknowns,
failed verdicts and historical evidence remain unchanged. Authorization for the
completed native attempt remains spent; the following sections are chronology.

## October 16 — RssCpu01 audited: useful measurement, application fails; stop

[Full single-case result, every UTC failure and RSS CPU/wall pair](RECORDER_RSS_CPU_VALIDATION_RESULT_20261016.md).
The approved eb13a51 / freeze babeeced... attempt completed exactly one mixed-0
case, 60,000 ordered frames, with archive/completion/closure and native bindings
verified. Exactly three units exited 0. Installed Linux readiness passed 1,194
total / 1,193 pass + one declared skip in 204.935 s, under 1-GiB readiness only;
measurement units retained 512 MiB and all original limits. No extra run.

Frozen independent audit: **complete=true, verdict=fail,
application_budget_pass=false**. Four UTC rows exceed 1 ms (worst 1.943665 ms).
Eight RSS widths exceed 5 ms, leaving resource acceptance unknown; every required
slot 0–71 is present, all 74 waits observed, all RSS starts inside 50 ms. Empty
missed_slots is not a resource pass. Append/durability and one complete CPU window
pass (36.100538% effective quota); admissible sampled RSS max 92,704,768 bytes.

Auxiliary coverage is complete: **73 linked RSS CPU/wall pairs**, no CPU unknown
or CPU-greater-than-wall anomaly. The eight wide reads span 6.531977–19.519640 ms
wall with 3.012961–5.580687 ms thread CPU. This is useful evidence of reader-thread
execution within a larger elapsed interval, supporting scheduling/blocking as
well; it does not identify GIL/OS/I/O or exact off-CPU time. Slot 15's measured
CPU alone is 5.580687 ms; active work also matters in that observation. Nothing
is subtracted, excused, tuned or extrapolated into an intrinsic cost guarantee.
Incremental observer overhead, continuous/high-water RSS, producer internal retry
count and event-local host/credit attribution remain unknown. MemoryPeak is
unavailable for all three units. Seven surrounding bad-read counter windows have
throttle increments, slot 24 does not; four overlap sync barriers and four do not.

All 43 originating files / 36,788,158 bytes verify. Outcome 10,933,856 bytes,
SHA-256 `1b077a9745ada5742ac4962e7bc1d5653c0f08faa4b58ea5ac7151a11e560b18`.
Frozen independent audit file SHA-256:
`c115ad33d1c95cfc1f9eb215d7ee882a99a0ad23cea5b3d73d0f63cd8ec8ffb8`.
Separate observed-origin receipt payload:
`4e0b275662ae8e6b8665f72ddbc50b3ee631a70b8e3e4f6d37ea1b1cb8ea6432`.
Native/CloudShell/downloaded byte anchors match. Post-stop source/runtime/public
checks pass, no scoped units remain. Historical Cohort02/OOM evidence and failed
verdicts are unchanged. Private RssCpu01 directory is listed below.

**Stop. Authorization is spent.** No retry/replay/replacement, extra validation,
six-case cohort, resource/public change, new diagnostic framework, merge, QC sync
or orders. Earlier sections preserve chronology, not pending authorization.

## October 16 — RssCpu01 staged; one controller submitted, readiness pending

Candidate `eb13a5136ae5a4f88a2987706cf46a5d874f2054` (528 selected files) is frozen:
`babeecedfe2ac3f4d3f2c86cd2d952f8f28745feeff5f48f03511c2e3ff5caee`.
Operator packet `5dc7a5b5a6130156af7a773f0e9f2eb83765faab777275366f830772c48a576b`.
Transport: 151,734 bytes, SHA-256
`c7c4ac476048e6ea699cdd25eb917284aa3b25e31fe9e81f42c147a5ff30ff7a`.
Both offline reconstruction and native staging verify all source bytes, reviewed
delta, runtime/thread clock, public state and fresh namespace. Staging preflight
passed at 15:36:21 UTC, with zero units started at that checkpoint.

Exactly one controller, PID **1588005**, submitted at **15:36:48.252682 UTC**.
Readiness is pending: 1,194 total with one declared skip required, under the
existing 1-GiB readiness-only envelope. Only on pass may one mixed-0 pair start.
At most three units and one case; no repetition, six-case cohort or changes to
measurement limits, thresholds, public collectors or historical failures.
Retain partial evidence and stop on declared faults. Do not start another
controller if this chat is interrupted; inspect this exact stage and retained
controller-start.json first. Private directory remains the RssCpu01 path below.

## October 16 — One RssCpu01 validation authorized; preparing exact packet

The user approved proceeding with the proposed single-case validation. Scope is
one readiness unit followed, only on its pass, by one 60,000-frame mixed producer /
recorder pair, then stop and audit. [Exact scope and gates](RECORDER_RSS_CPU_VALIDATION_20261016.md).
The new adapter reuses the original lifecycle/resource/native-binding audit with
an explicit one-case plan; it enables RSS thread CPU only in that consumer.
Historical six-case declaration/default behavior remain unchanged.

Full offline suite: 1,192 tests pass in 177.606 s on Intel macOS / Python 3.14.6.
After two additional binding tests and stricter auxiliary checks, all 17 focused
instrumentation/validation tests pass in 1.709 s. Exact current discovery count
is 1,194; native readiness must run 1,194 total with the one declared skip.
Python 3.9 syntax checks pass; no Linux validation is claimed yet.

Fresh read-only host/public/runtime checks pass at 15:27:55 UTC; new prefix/stage
absent, 6.38 GB free disk, about 1.227 GB available memory. Native thread clock
reports CLOCK_THREAD_CPUTIME_ID, monotonic/non-adjustable, resolution 1 ns.
Read-only AWS query at 15:26:15 UTC: t4g.small, standard mode, latest balance 576
at 15:21 UTC. No credit minimum. Historical failed unit remains retained.

Private preparation/evidence directory:
`.qcrl/reviews/recorder-rss-cpu-validation-20261016LupusRssCpu01/`.
Next: freeze the clean candidate, stage/verify transport/source/runtime, one
controller only after every gate passes. No native unit or new stage started at
this checkpoint. Preserve previous failed verdict/evidence, all thresholds and
measurement limits; no replay/replacement/extra case or six-case cohort.

## October 16 — RSS thread CPU v1 implemented offline; native approval pending

[Prospective identity, placement, faults and smallest validation proposal](RECORDER_RSS_THREAD_CPU_V1.md).
Policy `qcrl.rss_thread_cpu_policy.v1`, hash
`6eb2509c03a390c53d3fdc31124177403638d700e1e4922ee8ce015e7cf81ee5`.
The existing LinuxReader and persistence consumer accept explicit opt-in; existing
launchers remain disabled. Two thread CPU calls sit inside each enabled RSS wall
bracket. That wall bracket and every original threshold remain authoritative;
nothing is subtracted. CPU pre-reads and UTC witnesses receive no CPU calls.
Hashing/publication work outside the bracket is disclosed; incremental overhead
is unmeasured. A CPU fault/invalid reading retains the RSS sample with auxiliary
unknown. Parent artifacts, sample hashes, policy and observer thread bind each
witness; the auxiliary verifier does not change resource acceptance.

88 related offline regressions passed in 58.546 s on Intel macOS / Python 3.14.6
(localhost permission enabled); nine focused tests passed again after fixture
refinement. Tests cover actual reader/absolute observer/consumer publication
paths, clock faults and tampering. Python 3.9 syntax checks pass, but native clock
behavior/overhead remains unvalidated.
Propose one new mixed-rate case (60,000 frames over 70 s), preserving measurement
limits, original scheduling/budgets and failure evidence. No wide bracket means
inconclusive; no automatic repeat or six-case cohort. A new single-case launcher,
source/runtime/transport freeze and exact approval are still required before any
native execution. Historical source/evidence and failed verdicts remain intact.

## October 16 — Offline bracket mapping complete; failed verdict preserved

[Every UTC/RSS violation and contention context](RECORDER_COHORT_BRACKET_ANALYSIS_20261016.md)
is mapped from retained bytes: nine UTC rows and 39 RSS reads, with case-relative
timing, duration, matching send context, wait/handoff latency, enclosing cgroup
counter windows and persistence-barrier overlaps. All 39 RSS starts are inside
50 ms; excess elapsed time is inside the reader bracket, without evidence to
split active work from GIL/OS scheduling or blocking inside that operation.
The UTC clock/formatting bracket has the same attribution limitation.

24/30 burst-slot RSS reads exceed 5 ms versus 15/552 other reads. Eighteen bad
RSS brackets overlap recorded persistence barriers; 21 do not. Enclosing counter
windows show throttle increments for 20/39 RSS and 3/9 UTC events, but cannot
locate those increments within a particular violation. No causal mechanism is
established; host/credit snapshots are not event-local contention evidence.

One prospective recommendation only: paired observer-thread CPU time around the
existing RSS read, retaining monotonic gates and explicitly identifying the added
cost/scope in any future freeze. Not implemented. No new framework, test suite,
native observation or rerun. Original source, thresholds, OOM evidence, cohort
audit and failed verdict remain unchanged. Execution authorization remains spent.

## October 16 — Cohort02 audit complete: acceptance fails; stop

The single approved 4926d62 / freeze 6428a09a... cohort completed all six cases
in order, 360,000 ordered frames, all completion/closure/native unit bindings
verified. All 13 units exited successfully; Linux readiness passed 1,177 total /
1,176 pass + one declared skip in 201.118 s, under the prospective 1-GiB allowance.
All 12 producer/recorder units retained 512 MiB and the unchanged budgets.

**Frozen independent audit: complete=true, verdict=fail,
application_budget_pass=false.** Nine UTC brackets exceed the unchanged 1-ms gate
(worst 5.210600 ms); five cases fail and steady-1 is unknown. There are **39** RSS
resource-sample unknowns, all read brackets >5 ms (worst 19.535399 ms), with starts
inside 50 ms. All 597 wait receipts were observed/no explicit target misses, but
an empty frozen missed_slots list does not establish valid RSS coverage. Every
unknown slot and each UTC violation is listed in the [full result](RECORDER_COHORT_V2_RESULT_20261016.md).

Append/durability gates pass for every case/phase; worst durable 144.319336 ms.
All nine complete CPU windows pass, maximum upper 35.582940% effective quota;
max admissible timed RSS 93,057,024 bytes. These do not pass unknown resource
coverage or incremental-overhead/continuous-peak claims. MemoryPeak unavailable
for all 13 units; producer internal retries/shared-host/continuous-credit effects
remain unknown. No causal attribution or tuning is claimed.

All 208 originating files (218,570,554 bytes), frozen controls and the native /
CloudShell / downloaded archive byte anchors verify. Outcome SHA-256:
`51609e2ecca1b155d0ea3a631b3961ee46b207489be49504dc0840782ce71b64`.
Independent frozen audit file SHA-256:
`c9296f31e5c89efb3071f883cdf15ff54f3ae1bbace64e70c01f2f1488f67618`.
Separate observed-origin review payload:
`91924019f6e8d4686aa0e5c90409ec5a633b6ce5f6734a7f39c604abfadba816`.
Private evidence: `.qcrl/reviews/recorder-cohort-native-20261015LupusCohort02/`.
Browser interruption delayed only the same sealed evidence download; no experiment
was repeated. Original OOM evidence/verdict remains unchanged. Dated post-stop
source/runtime/public checks match, with no running scoped units.

**Stop after the approved cohort/audit.** Authorization is spent. Preserve all
failures/unknowns and frozen thresholds. No replay/replacement/extra smoke/cohort,
parameter/resource change, public rollout, merge, QC sync or orders. Any future
execution needs a separately reviewed prospective identity/approval. Earlier
sections below preserve chronology, not current state or unused authorization.

## October 16 UTC — Six-case collection complete; sealed evidence retrieval/audit pending

Cohort02 controller 1516839 completed exactly the six declared cases in order,
with complete=true, error=null and preservation_errors=[]. At 03:24:48 UTC no
scoped units remained listed. All 13 retained unit property files show success /
exit 0; readiness MemoryMax=1 GiB, all 12 case units MemoryMax=512 MiB. Native
readiness passed 1,177 total in 201.118 s, one declared skip. Original OOM evidence
and failed verdict remain unchanged; no retry/replay/extra run or resource tuning.

Post-stop exact source/runtime/public checks pass. Origin inventory: **208 files,
218,570,554 bytes**. Sealed outcome archive: **65,739,818 bytes**, SHA-256
`51609e2ecca1b155d0ea3a631b3961ee46b207489be49504dc0840782ce71b64`.
External origin inventory file SHA-256:
`69dfa0dfff98f2ca085cb1150ee1d4c9212b6810360a3797230e83afafca9847`.

Full evidence is being retrieved using the existing Session Manager client in
CloudShell (read-only archive copy after all units stopped; no IAM/credential/
infrastructure change). The stream and originating archive remain private.
**No application budget, archive-order or missed-slot verdict is claimed yet.**
Next: verify the external archive anchor before safe exclusive extraction,
reconstruct only the five byte-identical frozen controls, verify all 208 origin
files and run the exact candidate's independent auditor offline. Retain all
failures/unknowns and authority flags. Then update final result/HANDOFF and push.
Native approval is spent; no further native experiment is authorized.

## October 16 UTC — Linux readiness passed; declared cohort in progress

The single Cohort02 controller PID 1516839 remains the only submitted attempt.
Native readiness **passed 1,177 total tests in 201.118 s, one declared skip**
(1,176 pass), successful exit under actual MemoryMax=1,073,741,824 bytes and
240-s ceiling. Test PID 1516872; whole-unit CPU 142.162724 s, lifetime 202.476770 s.
MemoryPeak unavailable; no continuous RSS peak or incremental-overhead claim.
This is new v2 readiness evidence, not a repair of the original 512-MiB OOM.

At 03:13:35 UTC the controller had completed steady-0 and mixed-0 runtime/closure
checks and started mixed-1, exactly in declared order. The cohort remains live;
no case/application budget pass is claimed before independent audit. Observe only
this existing controller, retain final evidence after it stops, then independently
verify all known results and unknowns. Do not replay, restart or add cases/runs.
Private live progress: `.qcrl/reviews/recorder-cohort-native-20261015LupusCohort02/`.
Operator packaging/transport scripts there are **not executed yet** and require
a stopped controller, sealed inventory and no running scoped units. Native stage:
`/var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort02`.

## October 16 UTC — Revised cohort approved and submitted once

The user's “please continue” approved the exact revised packet dcce731d... /
freeze 6428a09a34633987a353c32beeca340be535b33c1e11aa897f291d37a4da434b.
After AWS access restoration, fresh read-only host checks verified prior source,
installed runtime/dependencies/live boot and public state. Host MemAvailable was
1,230,979,072 bytes (snapshot only), no swap; disk free 6,689,808,384 bytes.
Raw EC2/credit-mode response at 02:54:25 UTC confirms t4g.small/standard; latest
balance 576 at 02:49 UTC, without a minimum gate. API file SHA-256:
09083646b4406b3ff71d22f1aee72d265a2e3034185c94ca72c3b4f030a7a90c.

Exact transport SHA and all six member/control bytes verify. Detached candidate
4926d62 and all 520 source files match; full lineage/runtime/public/namespace
preflight passed. Fresh Cohort02 stage created. Controller PID **1516839** was
submitted exactly once at **2026-10-16 03:04:26.911235 UTC**. Readiness is the first
gate (1 GiB, 240 s); no outcome is claimed yet. Producer/recorder limits and all
budgets remain unchanged. Do not resubmit this controller under any circumstance.

Private operator/preflight/API evidence:
`.qcrl/reviews/recorder-cohort-native-20261015LupusCohort02/`.
Next: observe the existing controller only; fatal conditions stop remaining units,
retain all partial evidence, independently audit after stop. No retry/replay,
replacement, extra smoke/case/cohort, tuning, public/resource/IAM changes, merge or
QC sync. Historical OOM evidence/failed verdict remains intact. Earlier sections
below preserve chronology, not current authorization or outcome.

## October 15 — Revised executable packet frozen; no native rerun

Candidate **4926d62faab552af8a3c8e3fe964dc16052e4773** is committed/pushed. All 1,177 revised
offline tests pass (154.120 s, Intel macOS/Python 3.14.6); installed Linux
readiness is still unrun. Exact v2 freeze:
`6428a09a34633987a353c32beeca340be535b33c1e11aa897f291d37a4da434b`.
Approval packet payload: `dcce731de610681470fb773e3ed95be1d47329b9bc0905fa0b7cfdb3ad3399e2`.

[Revised approval packet](RECORDER_COHORT_READINESS_V2_APPROVAL_20261015.md)
proposes 1-GiB readiness only, then the same six serial cases/360,000 occurrences.
Producer/recorder remain 512 MiB; CPU/time/tasks, all measurement thresholds,
original plan and failed OOM evidence/verdict remain unchanged. Actual readiness
properties and independent audit paths are tested; no extra diagnostic observer.
All 520 selected candidate source files reconstruct from the incremental bundle in a
fresh scratch checkout. Controls/runtime/lineage are frozen as dated expectations,
not freshly observed Linux validation. Private packet/transport directory:
`.qcrl/reviews/recorder-cohort-readiness-v2-preparation-20261015/`.

Fresh stage proposed: recorder-persistence-20261015LupusCohort02. Nothing is staged,
no remote inspection/native unit was run for this revision. Obtain fresh read-only
host/credit/runtime/public/namespace checks after new approval and before units;
report available host memory/balance and unknowns without inventing a minimum.
**Await new explicit staging/execution approval.** The prior approval is spent.
No smoke/replay/retry, public/resource/infrastructure/IAM change (apart from the
explicit proposed private readiness allowance), main merge or QC sync.
Earlier sections preserve chronology and do not authorize an old launch.

## October 15 — Offline readiness memory revision; awaiting a new approval

Offline profiling at cfe5154 identifies the 60,000-frame completion/producer/audit
fixture as the dominant working set: 604,839,936-byte fresh-process peak versus
647,921,664-byte full-suite peak. All original 1,169 tests passed locally. Final
RSS remained 231,817,216 bytes even after explicit GC; this does not prove a leak
or identify the active native OOM test. Profiling and raw local logs remain private
in `.qcrl/reviews/readiness-memory-offline-20261015/`.

Prospective code now separates **1-GiB readiness only** from the unchanged
512-MiB producer/recorder units. Complete test discovery, one declared Python 3.9
skip, CPU 75%, TasksMax 32 and 240 s remain. The new v2 freeze binds the explicit
readiness envelope; launcher capture and independent audit verify actual limits
without rewriting retained properties. Eight new fault/routing/audit tests cover
the distinction. All **1,177 offline tests pass in 154.120 s** on Intel macOS /
Python 3.14.6; local peak RSS 632,987,648 bytes. Python 3.9 syntax checks pass.
The first revised full suite caught a removed import still used by recorder binding;
it was restored and the complete suite passed; both local logs are retained.
See [prospective rationale](RECORDER_READINESS_MEMORY_V2.md).

No native staging, unit, replay or host change occurred for this revision.
The original failed 512-MiB attempt and all measurement budgets/evidence remain
unchanged. A separate exact approval packet will bind candidate, full offline
suite, freeze, bundle and fresh Cohort02 namespace. Read-only host/runtime/public
and credit context must be refreshed before any newly approved execution; retained
host/credit evidence is dated, not new native validation. No minimum credit gate.
The prior authorization is spent. Do not execute without a new approval.

## October 15 — Approved cohort stopped at readiness OOM; zero cases; audit complete

One controller (PID 1492498) ran under approved candidate 8c72652 / freeze
90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686.
After sign-in, the partial stage was inspected, approved packet/source/control
bytes verified and exact 516-file/runtime/public preflight passed. Native readiness
PID 1492531 was killed by memory-cgroup OOM at 148.369297 s under unchanged
512-MiB / 240-s limits. Actual properties and the separately anchored existing
kernel journal confirm the readiness cgroup and PID. No case was prepared or
started; no replay, extra smoke, population/skip or resource change occurred.

Frozen independent audit: complete=false, verdict=fail, application_budget_pass=false.
All ten originating evidence files and external byte anchors verify. Native test
completion/count/skip, active test/allocation at kill and every unrun case's budget,
stimulus/archive/window/slot evidence remain unavailable. Continuous RSS peak and
incremental overhead remain unknown. The readiness unit's whole CPU total is
101.731637 s; it is not recorder/observer budget evidence. Unit MemoryPeak absent.

[Full result and anchors](RECORDER_PERSISTENCE_COHORT_RESULT_20261015.md).
Private evidence: `.qcrl/reviews/recorder-cohort-native-20261015LupusCohort01/`.
Source/runtime/public context remains unchanged; no scoped unit runs. The test
unit remains failed with MainPID=0; failure state was not reset. No preservation
errors reported. Fresh raw EC2 mode remains standard, latest returned balance
576 at 22:26 UTC; no minimum credit gate. Historical evidence/verdicts untouched.

**Stop: authorization spent.** No native replacement/replay, standalone smoke,
cohort, resource change, merge or QC sync. Next prospective work requires offline
memory analysis/fix and a new reviewed identity before another native attempt.
Earlier staging/pending approval sections below preserve chronology, not current
status. No implementation or threshold was changed after this failure.

## Approved cohort staging checkpoint — AWS sign-in required

The user explicitly approved the exact executable packet ("totally approved").
That approval remains valid for candidate 8c726522a7ba9b19411d309b42d17a92faf72395 /
freeze 90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686.
Fresh pre-staging runtime/boot/public/namespace checks passed. Refreshed raw AWS
responses at 20:34:54 UTC confirm unchanged t4g.small/standard context; latest
returned credit balance remains 576 at 20:29 UTC, without a minimum gate.

Created the fresh private recorder-persistence-20261015LupusCohort01 stage and
transferred all 187,056 base64 characters of the approved 140,290-byte packet,
with every offset acknowledged. The console expired during the following
extraction/checkout command attempt; no completion acknowledgement was observed.
**Inspect actual stage/extraction/source state after sign-in before any mutation.**
Do not recreate/adopt a measurement launch or blindly repeat the staging command.
No controller invocation, claim or native readiness/case unit was submitted.

Private resume checkpoint:
`.qcrl/reviews/recorder-cohort-native-20261015LupusCohort01/sign-in-required-checkpoint.json`
(payload 65cf7379778e76fc6f473c77a9a629f770b7a230139cef79d8a11f1197b9bafa).
AWS portal now requires user sign-in. Once restored, verify remote packet SHA,
all controls/516 candidate sources and full preflight, then invoke the approved
controller exactly once. Readiness remains first and unrun; no retry, replay,
extra smoke/cases or resource/public changes. Preserve partial staging evidence.
The packet's pending-approval wording below is the earlier frozen checkpoint.

## Frozen executable cohort packet — awaiting approval

Candidate `8c726522a7ba9b19411d309b42d17a92faf72395`, 516 selected source files.
Freeze `90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686`.
Approval-packet payload `e9805de66fb3eb939ad7c5ad57b7820625ba731e30c4e0f68679092834d073c5`.
Transport 140,290 bytes, SHA-256
`13d24cec0206c648702823982bda2d8d3ebe9eeac98545d579f42f2a996caa60`.
[Exact executable approval packet](RECORDER_PERSISTENCE_COHORT_APPROVAL_20261015.md)
binds fresh raw host/credit evidence, installed runtime, exact compatibility delta,
source/bundle reconstruction, command/stage, 13-unit lifecycle, unchanged schedules/
budgets and fatal-stop/audit rules. Fresh stage is recorder-persistence-
20261015LupusCohort01. Neither source staging nor native units have started.

One readiness-gated cohort only after explicit approval. Expected Linux gate:
1,169 total, 1,168 pass plus one declared version skip within unchanged 240 s.
No further smoke, retries/replay/replacement/tuning, resource/public/infrastructure/
IAM changes, credentials, merge or QC sync. Stop afterward for independent review.
The implementation candidate, not subsequent documentation-only HEADs, is frozen.

## October 15 — Successor cohort implementation and fresh host evidence complete

The completion verifier now follows each case's declared frame count, bounded to
its supported 1..60,000 corpus population. Boundary tests cover 1/2/67/68/69/70/
59,999/60,000 and missing/extra/invalid counts; actual 69- and 60,000-frame recorder
completion paths pass. Original smoke reader/evidence and failed verdicts remain
unchanged. The worker change is exactly the two-expression verifier substitution.

The new prospective six-case launcher/auditor routes persistence plus absolute
observation, retains original budgets/schedules, enforces exact readiness, live
bindings, serial lifecycle, fatal stops and scoped cleanup, and uses large producer
artifact verification. Compatibility lineage pins the original passed smoke audit
and external origin receipt, unchanged tested Python sources except the reviewed
verifier substitution, and exact installed wait/dependency/boot envelope. This is
an explicitly identified integration delta, not same-source native validation.
See [successor cohort contract](RECORDER_PERSISTENCE_COHORT.md).

Fresh read-only CloudShell DescribeInstances/DescribeInstanceCreditSpecifications
responses and Session Manager IMDS/boot/source/runtime/public observations are
retained and externally byte-anchored. Host remains Ohio t4g.small/standard, same
boot and public context. Latest returned CPUCreditBalance: 576 at 2026-10-15
19:34 UTC (query 19:39:39 UTC); no minimum balance acceptance gate. Incremental
observer overhead and continuous RSS peak remain unknown, outside the inclusive
CPU/current-RSS acceptance gates. New stage/prefix absent, free space >4 GiB.

All **1,169 offline tests pass in 152.925 s**, Intel macOS/Python 3.14.6. Exact
prospective Linux gate: 1,169 total, 1,168 pass plus one existing version skip,
within the unchanged 240-s readiness unit limit; unrun, no timeout guarantee.
Private freeze/packet preparation: `.qcrl/reviews/recorder-cohort-preparation-20261015/`.
Freeze this implementation candidate and present exact staging/one-cohort approval
before any units. No additional smoke is required or scheduled. No new native code,
case/unit, replay, infrastructure/resource/IAM change, merge or QC sync occurred.
The blocked readiness section below is the preserved pre-implementation checkpoint.

## October 15 — Six-case readiness review: blocked; no native work

Reviewed 92889b0 against the actual parent/absolute/persistence declarations and
launcher/auditor. Incremental observer overhead and continuous RSS peak are **not
acceptance gates** for this inclusive-CPU/current-RSS cohort; both remain unknown,
not passed. Prior probe-cost rejections are unchanged. Credit mode requires raw
operator-anchored EC2 instance/credit responses plus instance identity/live boot.
The October 12 raw context still verifies against its historical external anchor,
but is not fresh; October 15 smoke console context lacks required cohort fields.
Balance remains unknown; no numeric balance threshold was preregistered.

Concrete integration blockers: old six-case launcher still routes legacy workers;
successor completion uses the frozen 68-frame archive reader (offline frame 69
fails); full producer records exceed the small-control cap; no successor six-case
wait/closure/origin auditor, exact execution freeze or same-source compatibility
binding exists. Do not rename the smoke receipt or bypass that binding. Eight
existing launcher/auditor fault tests pass locally; no native validation performed.

[Readiness and single blocked packet](RECORDER_COHORT_READINESS_20261015.md) fixes
all six schedules, units, unchanged budgets and stop rules while marking absent
execution identities explicitly. This is **not yet an executable approval request**.
Private packet payload b8da8c80ef67ddfb4d24eb10517f860a7affbaeb226c9cfba3addb1e60400777.
Resolve offline integration/source/audit requirements and fresh host evidence,
then bind one final concrete approval packet. No standalone smoke is presently
justified or scheduled; another would require a concrete remaining native gate.
No cohort, units, infrastructure changes or remote mutations occurred in this review.

## October 15 — Successor Linux compatibility passes; stopped after one run

The user approved the exact successor packet below. Fresh source/runtime/boot/
public preflight passed; one controller staged and ran one readiness unit followed
by the 68-occurrence producer/recorder pair. Linux Python 3.9.25/aarch64 readiness:
1,156 tests in 112.488 s, 1,155 pass plus the declared existing version skip.
This is distinct from all 1,156 offline Intel macOS/Python 3.14.6 tests passing.

Independent frozen audit **passes bounded compatibility**: 68 ordered frames,
archive/completion integrity, all planned sends plus verified recorder completion,
no drain errors, no missing observer slots. Worst durability upper 0.183876711 s
against unchanged 2 s. Inclusive 60-s CPU upper fraction 0.0048931556; sampled RSS
max 27,553,792 bytes. One-second persistence reserve remains prospective and is
not a guarantee. Separate origin attestation preserves original self-report flags.

See [complete audit, inclusive costs, unknowns and anchors](RECORDER_PERSISTENCE_SMOKE_RESULT_20261015.md).
Private evidence: `.qcrl/reviews/recorder-persistence-native-20261015LupusPersistence01/`.
All scoped units are gone; public state/hashes and historical failed evidence are
unchanged. No retry/replay, extra run or cohort occurred. Incremental observer
overhead, continuous RSS peak, credit balance and producer internal sleep retries
remain unknown; original cohort raw host-context gates remain open. Budget/cohort
acceptance and orders remain false. Native authorization is spent: stop here;
no six-case cohort, public rollout, merge or QC sync. The following pending/unrun
sections preserve the historical preparation chronology, not the current state.

## Frozen successor approval packet — October 15 (not executed)

Implementation candidate: `371fa03c3d2622d784128b9359c3ab730f082cf2`, 509 selected
source files. Execution freeze:
`3338edbfc19048fa39787d86cc70abebd458318b4a79abd816c531f2fad3ca4f`.
Successor declaration:
`b3dfda1aa30d2fff664f889e61e76401adc0c561fa331e366429b79450cc066d`.
Private preparation receipt:
`3e30514f0bbda19bbca22826756738f4b19c2a625543c934988b39ee634235b4`.
These bind the implementation candidate, not later documentation-only HEADs.

Exact scope for approval: staging plus **one** successor recorder smoke, only after
fresh source/runtime/public-state preflight and Linux readiness **1,156 total,
1,155 pass plus one declared existing Python-version skip**. Original occurrences
0..67, 1 Hz at epoch+j seconds; 20-second epoch lead / 100-ms readiness margin;
68 frames / 180-second capture cap; unchanged CPU 75%, memory 512 MiB, 32 tasks,
240 seconds per unit. One readiness unit, producer and recorder, original observer
grid with 50-ms CPU pre-read lead. Explicit prospective persistence reserve 1 s
inside the unchanged 2-s durable bound; no guarantee or tolerance adjustment.
Closure requires every planned send and verified recorder completion, not merely
ConnectionClosedOK. Stop afterward for independent completeness/inclusive-cost/
archive/missed-slot review regardless of outcome. No retries/replay, replacement,
extra runs, tuning, resource/public-service changes or six-case cohort.

Proposed fresh stage:
`/var/lib/qcrl-stream/recorder-absolute-20261015LupusPersistence01`.
See [full successor contract/command](RECORDER_PERSISTENCE_SMOKE_PREPARATION.md).
Private packet: `.qcrl/reviews/recorder-persistence-preparation-20261015/`.
`stage-packet.tar.gz` is 107,692 bytes, SHA-256
`7987395433a724ad16adf5f843cd31fb8017547c5e6ebefe8deb77f982adc26f`.
It contains the candidate Git bundle, exact freeze and three unchanged runtime/
host review controls. A fresh offline repository containing only predecessor
81fc2ba history reconstructed all 509 selected candidate files exactly from the
bundle. No credentials or raw capture/measurement archives enter this packet or GitHub.

The freeze binds the previously observed October 15 Ohio installed envelope;
it is **not a fresh successor host observation**. Before any unit, fresh read-only
runtime/boot/dependency/source/public checks must match exactly or stop without
execution. Credit balance, incremental observer overhead and continuous RSS peak
remain unknown. Original cohort host-context gates remain open. No successor stage,
claim or unit was created; no Linux successor result exists. Await explicit user
approval of this exact packet. Historical failed freeze f045b061... and its failed
verdict remain intact.

## October 15 — Successor fixes implemented offline; new smoke awaiting approval

The new isolated persistence lane and worker implement both fixes; historical
runtime files, original c9207f... declaration, 2-s durable limit, failed f045b061...
smoke and audit remain unchanged. Pending receives now stop at the earlier of
last-sync+1 s and oldest pending application-return+1 s, with pre-receive and
append checks. The prospective reserve is explicitly **1 second**, not a timing
guarantee; injected persistence stalls still fail the unchanged bound.

Successor drain retains terminal close type/codes/time even across a concurrent
stop. Success requires all planned ordered sends before the normal close **and**
case-bound verified recorder completion, exact archive population/footer and no
capture/reconnect/observer failure. A normal close or capture-closed marker alone
never passes. Atomic exclusive control publication prevents partial consumer.json
adoption. Existing bounded deadlines, resource limits and observer grid/50-ms lead
are preserved. No diagnostic observer layer or native run was added.

All 1,156 offline tests passed in 77.706 seconds on Intel macOS/Python 3.14.6;
the 14 successor tests also pass after the final declaration metadata clarification.
Prospective Linux gate: 1,156 discovered, 1,155 pass plus one existing version skip.
Fourteen successor tests exercise the actual runtime paths, deterministic boundary
and fault cases, and smoke routing/cleanup. See
[prospective successor smoke](RECORDER_PERSISTENCE_SMOKE_PREPARATION.md) for the
new 68-at-1-Hz plan and explicit reserve. The candidate requires a new committed
source/runtime freeze and approval; prior native authorization is spent. No
replay, six-case cohort, resource change, public rollout, merge or QC sync.
Earlier proposal-only sections below are historical checkpoints.

## October 15 — Offline failure diagnosis and prospective fixes

The failed smoke verdict, frozen bytes, implementation and thresholds remain
unchanged. [Offline diagnosis](RECORDER_FAILURE_ANALYSIS_20261015.md) traces both
failures. Persistence scheduling can consume nearly two seconds in two receive
waits before flush/fsync finishes; the full path has no sufficient margin under
the 2-s bound. Drain records normal close as an error after all sends and cannot
distinguish premature normal closure; a concurrent stop can also mask read faults.
The capture-closed marker is published on failure as well as success, and the
producer currently adopts presence without validation. The retained close's exact
ordering is unknown, so the historical failure is not waived.

All 1,142 offline tests passed in 89.878 seconds on Intel macOS / Python 3.14.6.
Fourteen deterministic tests reproduce interval/count boundaries, persistence
faults, exact threshold, close/timeout/control/stop interleavings and failed/missing
capture witnesses using existing code. Proposed successors: cap blocking receives
at pending sync deadlines, and classify a bounded terminal close event against
completed-send and verified recorder lifecycle evidence. These are proposals;
no runtime fix is wired in, and no diagnostic layer was added. Implementation
would change receive/persistence/producer/audit scope and require a new prospective
identity and source/runtime freeze. No native replay or cohort is authorized.

## October 15 — One Linux recorder smoke completed; compatibility failed; stopped

User approval covered exactly one staging/run under freeze
`f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`.
Candidate `81fc2ba` was staged in a fresh private namespace and all 500 selected
source/runtime/public-context bindings passed preflight. Linux readiness passed
1,128 tests in 109.029 seconds: 1,127 pass plus the declared Python-version skip.
The controller then ran the one 68-occurrence producer/recorder pair once under
the unchanged limits. All scoped units are gone; public collectors, source and
environment hash remain unchanged. No replay, tuning, extra run or cohort.

Independent audit: complete 68-frame ordered archive and durability linkage,
verified origin inventory/bytes and actual unit bindings; zero missed observer
slots across 71 absolute wait receipts. Resource gates pass, including one complete
60-second CPU window at upper fraction 0.0045852; sampled RSS max 27,389,952 bytes.
**Overall fail:** sequences 9/44 durability upper bounds 2.000667292/2.000551980 s
exceed 2 s, and producer drain retains `ConnectionClosedOK`. Compatibility and
budget acceptance remain false. No frozen implementation, threshold or evidence
was changed to reinterpret these failures. The 50-ms lead remains prospective.

See [full native audit result](RECORDER_ABSOLUTE_SMOKE_RESULT_20261015.md) for
inclusive CPU/read/RSS/throttling measurements, archive anchors and all limitations.
Incremental observer overhead, continuous RSS peak, host credit balance and producer
internal sleep retries remain unknown. The original six-case host-context gates
remain open. Private evidence/audit/origin receipt:
`.qcrl/reviews/recorder-smoke-native-20261015LupusSmoke01/`.
Only offline retained-evidence analysis remains in scope; no further native run,
cohort, resource change, merge or QuantConnect sync is authorized. Earlier sections
below preserve the preparation chronology; their pending/unrun wording describes
the state before this approved smoke, not current readiness.

## October 15 — Recorder smoke transport prepared; native approval pending

The next target is exactly one native recorder compatibility smoke, not another
isolated timing comparison. The smoke-only controller has one readiness-regression
unit, one producer and one recorder; no cohort route. It sends original corpus
occurrences 0..67 at epoch+j seconds, frame limit 68/capture limit 180 seconds,
20-second epoch lead and 100-ms readiness margin. Separate live PID/cgroup bindings,
fixed commands/limits, one capture per unit and scoped cleanup are audited offline.
Every unit retains CPU 75%, memory 512 MiB, 32 tasks and 240 seconds; numeric IPv4
localhost only. See [exact smoke preparation](RECORDER_ABSOLUTE_SMOKE_PREPARATION.md).

The 2-ms to 50-ms CPU pre-read lead **changes measurement timing** despite unchanged
budgets. Prospective observer policy remains bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f;
new smoke plan is e3b86ea5be1482c7352552459ab14df365789f12b74e37c746adcdb1b529321d.
The producer adds an explicit injected transmitter; its legacy default is unchanged.
This changes its source-bound declaration prospectively. The October 14 declaration
41187030fbf5825311b03c0558bd137b104b7d692078a11777b7bf4242931e15 and private receipt remain
historical frozen identities, not the new candidate. No earlier unknown or result
is repaired; original recorder c9207f... declaration and absolute-wait code stay fixed.

Read-only Session Manager inspection on October 15 observed the existing Linux
Python 3.9.25/aarch64/glibc 2.34 runtime, unchanged boot and public collector/hash
context, and byte-hashed all 60 installed websockets 15.0.1 distribution files.
The EC2 console showed t4g.small/two vCPUs/standard credit mode. The instance role
denied credit-description API access; no IAM change. Console observation is
retained honestly as console evidence, not substituted raw API output. Credit
balance remains unknown. The original cohort host-context gates still apply later.
Private preparation receipts: `.qcrl/reviews/recorder-smoke-preparation-20261015/`.

Offline fixtures exercise full synthetic archives, byte anchors, ordered corpus,
completion/durability linkage, binding/release/lifetime/limit and rehashed wait
faults, failed readiness/cleanup, missing slots with known budget failure, extra
files/symlinks and incomplete launches. They do not establish Linux/native results.
The post-run review must cover archive integrity, completeness, missed slots,
inclusive recorder CPU/RSS/read brackets/throttling/memory events and separate
producer resources. Incremental observer overhead remains unknown from one run.
Any required unknown blocks progression. Stop after this smoke for independent
review and a separate six-case authorization decision. No units have started.

Verification: all 1,128 offline tests passed in 85.018 seconds on Intel macOS /
Python 3.14.6, including the 14 new transport/audit tests and existing localhost
fixtures. New transport/auditor/tests compile with local Python 3.8.2. Fresh
read-only wait-runtime bytes exactly match the earlier frozen comparison envelope;
that observation is not execution of the new recorder path. Installed Linux
readiness tests and native recorder measurements remain unrun. New source-bound
observer declaration: 0f3a9b8494804f792d5778a0388d787cb2bc52a5de7fd4bc1cdb60738ded6bf1.

The exact candidate/freeze approval packet is recorded below. No main merge, QC sync,
credentials import, infrastructure change or native execution is authorized here.

## Frozen approval packet — October 15

Implementation candidate: `81fc2ba00fc5cae35316b3661dbb2ec6044f666b` (500 selected source files).
Execution freeze: `f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`.
Private preparation verification receipt:
`3f15daf0206e50663d3174ce78218c48132f496cd7bd894e1068ec3ff1774d1e`.
These bind the implementation candidate, not later documentation-only HEADs.
The original three native audit payload hashes still verify unchanged.

Prepared private transport packet `stage-packet.tar.gz`: 119,716 bytes,
SHA-256 `f974a66a733218802f53afc31fa1f31ca9335557fbe20c33ad4c74fc28c6164f`.
It contains the incremental Git bundle (prerequisite frozen cb23c4c), exact freeze,
reviewed select source/review and dated host context. No credential or evidence
archive is included. Source is not yet staged remotely; no new candidate code,
readiness unit or recorder unit has executed on Linux. After approval, stage into
one fresh private directory, verify packet/commit/all source/runtime bindings
before starting units, and reject any existing evidence/claim/unit namespace.
Do not overwrite or execute in an old comparison/evidence directory. The transport
bundle and controls must reconstruct the candidate exactly; stop on any mismatch.

Proposed stage: `/var/lib/qcrl-stream/recorder-absolute-20261015LupusSmoke01`.
After separately approved staging and gate checks, the one controller invocation is:

```sh
/opt/qcrl-stream/venv/bin/python -B -m infra.stream.recorder_absolute_smoke --root /var/lib/qcrl-stream/recorder-absolute-20261015LupusSmoke01 --execute
```

Run it as root from that stage's `source` directory through the authorized existing
Session Manager connection. Expected readiness population: **1,128 tests, 1,127
passing and one existing Python-version skip**, within its separate 240-second
unit. Those are prospective Linux counts, not observed Linux results. Any other
population, failure, drift, effective-limit/binding/readiness fault or retention
failure stops progression and preserves the attempt without replay. Then only
the declared producer/recorder pair: 68 occurrences at 1 Hz over offsets 0..67,
20-second original epoch lead, frame limit 68/capture limit 180 seconds, fixed
75% CPU/512 MiB/32 tasks/240 seconds per unit, 50-ms CPU pre-read policy.

Stop after one smoke. Independently transfer/verify the external origin inventory
anchor, audit completeness, ordered archive/durability, actual wait/read/missed-slot
coverage, inclusive observer/recorder cost and every unknown. Incremental observer
overhead and host credit balance are explicitly unknown. The console's dated
standard-credit observation does not replace the original six-case cohort's raw
host-context gates. No isolated timing run, tuning, replay, cohort, public-service
change, infrastructure provisioning, main merge or QC synchronization is included.
**Await the user's approval of this exact packet before staging/execution.**

## October 14 — Offline absolute observer integration and successor preregistration

Absolute waiting is integrated into the isolated recorder's in-unit CPU/RSS
observer through explicit prepare/consume wrappers. The receive path, producer
pacing, segmented writer, completion witnesses, public collectors and original
recorder declaration remain unchanged. Legacy consume defaults to its old observer.
The original recorder plan is still c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade.

New observer policy hash:
`bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f`.
Source-bound declaration:
`41187030fbf5825311b03c0558bd137b104b7d692078a11777b7bf4242931e15`.
Private offline receipt: `.qcrl/reviews/recorder-absolute-offline-20261014/`.
It uses the shared epoch's ceiling integer nanoseconds, fixed integer-second RSS
slots and 50-ms pre-boundary CPU lead (an explicit successor to the old 2-ms
lead). Budgets stay unchanged; the enclosing CPU delta is not normalized or
subtracted to remove the larger lead. Every endpoint gets at most one absolute
wait. Past/equal targets and >50-ms late wakes cause no read/catch-up, retain
unknowns and continue original slots. Wait/clock faults and KeyboardInterrupt
stop the observer with its prefix; ordinary read faults retain their unknown slot
without retry. Capacity/overflow remains 184 slots. Wait receipts and case/source
bindings are checked before the unchanged resource gates; known failures survive
missing evidence. No native-origin or acceptance flag is promoted.

Prospective test: one 68-occurrence, 1-Hz real-loopback compatibility run spanning
one complete 60-second CPU window, then stop for independent review. This is not
a shortened acceptance case. Only after a separate approval may the original
six serial 60,000-occurrence cases / 360,000 total run with unchanged workload,
corpus, resource limits and application budgets. No tuning or replacement.
See [recorder absolute preregistration](RECORDER_ABSOLUTE_BUDGET_PREREGISTRATION.md) for the full declaration,
missed-slot rules, bounds, stopping conditions and remaining implementation gates.

Offline verification uses injected clocks/syscalls/readers and recorder wiring;
no new native wait, Linux unit, capture, infrastructure, credential operation or
QC sync. The 68-at-1-Hz transport, native launcher routing, fresh committed
source/runtime/dependency envelope and independent launch/origin audit still need
implementation and review before requesting native authorization. Old launchers
must not be reused to claim this path ran. Earlier frozen evidence and verdicts
remain unchanged; audit each against its originating revision.


Verification: all 1,114 offline tests passed in 78.738 seconds on Intel macOS /
Python 3.14.6 with numeric-localhost fixtures permitted. All 21 new integration
and fault tests pass, including real WebSocket/recorder completion wiring with
injected syscalls/resources/Linux context. Four changed/new Python files compile
with local Python 3.8.2. This is not installed Python 3.9/Linux or native recorder
validation. No new native experiment or acceptance result exists.

## October 14 — Frozen two-run comparison completed, one unknown

Renewed direct approval covered corrected cb23c4c / execution freeze
`7c0ddaf5f697493302fd6791a64aacc68618d391a2a80c3bfd3a8dca198c3f55`.
Fresh exact source/runtime/public preflight passed. Linux Python 3.9.25 regression
passed: 1,093 discovered in 105.935 seconds, 1,092 pass and one declared skip.
The two fixed serial AB/BA units then completed once, without fatal wait or
transport faults. No tuning, catch-up, replay or additional measurement occurred.

Independent native audit
`c2a6b59f07563fbf10f8184fd09494d89f0400e6bc9917bf1337ced04a466f4d`
checks the observed host/transfer, all 23 retained evidence files, source/runtime,
readiness/release/live identities, actual limits, serialized lifetimes, journal
and receipt equality, independent timing/float/rational arithmetic and cleanup.
Private receipt: `.qcrl/reviews/wait-comparison-native-20261014LupusCompare02/`.
All private units are inactive; public/environment/source/runtime unchanged.
Original declarations, compatibility smoke and failed first readiness evidence
remain untouched. All producer/freeze authority flags remain false.

Transport is complete but scientific comparison completeness remains false:
23 observed cells, one unknown. Run-zero absolute 50-ms target was already
8.892023 ms late before invocation, following select's 58.771055-ms-late
60-second return. No absolute request was made for that cell; no replacement.
The paired 50-ms median is null. All 12 select internal retry counts remain
unknown. All 20 declared context-file observations succeeded; 16 structured
ancestry nulls retain absent root limit/disabled child cpuset files, not invented
numeric limits. Endpoint context cannot identify per-target host/signal/scheduler
causes. Quiet regression identities and RPM signature/reproducible-build limits
remain explicit in the full audit.

At 60 seconds, select lateness was 58.771055 / 60.099649 ms and absolute was
0.136841 / 0.131331 ms; paired median absolute-minus-select = -59.301266 ms.
These are descriptive serial samples with host/time confounding, no tail,
significance, exclusive-causality, recorder-acceptance or trading conclusion.
Recorder application compatibility and its budget cohort remain unfinished; the
new absolute-observer path is implemented offline and preregistered above.
The finite comparison authorization is consumed; further native execution needs
separate approval. No new diagnostic layer, main merge or QC sync.

Full observations, identities and every unknown are documented in
[native comparison audit](WAIT_COMPARISON_NATIVE_AUDIT_2026_10_14.md).

## Earlier execution gate — preserved failed comparison readiness

This section records the stopped first attempt; the renewed, corrected-source
execution and its separate receipts are reported above.

The operator directly authorized exact b7db2c2 / freeze
`f1339e0b54b84703368fc39efdfeb7c470ce4220bbb15d6df8284e46c0036f61`.
A fresh private stage passed live source/runtime/public preflight, then its bounded
Linux regression failed before either comparison worker was created. The declared
native gate stopped advancement; no measurement, retry, tuning or extra run occurred.
The failed test unit is retained as failed with MainPID 0; both comparison units
are absent. Public collectors, environment and frozen source/runtime are unchanged.
Corrected candidate cb23c4c2b6b2 is sealed offline (full identity below).
Further native execution requires new approval of that execution revision.

Linux Python 3.9.25 discovered 1,079 entries in 105.799 seconds: 1,077 passed,
one existing Python 3.10+ stdlib-inventory guard skipped and one module import
error. Fifteen new tests were replaced by one loader-error placeholder. The exact
failure is `SyntaxError: too many statically nested blocks` in the new fault test,
line 312. The earlier Python 3.9 AST parse checked grammar, not compiler block
depth. Offline correction uses ExitStack for the same mocks, preserving their
order, cleanup and assertions. Production Python and every plan remain unchanged.
Both new files now compile with local Python 3.8.2; 15 focused fault tests pass.
This is local verification, not repaired Linux validation. The corrected candidate
seal and complete local regression result are recorded below.

Untouched receipts: `.qcrl/reviews/wait-comparison-native-20261014LupusCompare01/`.
Separate failed-gate audit:
`353a9e1fa414aa8a77bf562ada0aa34bb5ff332c61d367f8d20bc055ac1af5e6`.
All eight native evidence files match origin inventory
`c4c320fcb1d61dc2f374d5c2a0fdebd15b243e1c2b05de8b08ca7da2b04111c7`;
transferred archive SHA-256
`7e502385ac81b015faec70c187010d2ae386dd4ffddea05552436374f248d265`.
Audit independently checks observed host/transfer origin, frozen controls, failed
unit properties/journal, no comparison directories/units, no worker processes and
unchanged public/source/runtime. It does not verify a successful scientific pair.
Producer flags and original b7db/2cb freezes/evidence remain unchanged.

For this failed attempt only, all 24 run/arm/interval cells remain unknown
(two runs × two arms × 50 ms,
100 ms, 500 ms, 1 s, 5 s, 60 s); epochs, baselines, request/return brackets,
worker context and all descriptive comparison statistics are unavailable.
Select internal retry counts remain unknown; no comparison calls were made.
Quiet regression output does not enumerate individual passing test identities.
RPM provenance still lacks independent signature verification/reproducible build.
No scheduling, recorder-acceptance, causal or trading conclusion follows.

The earlier single native compatibility smoke remains independently verified
under the original 2cb6880 / 488-source freeze
`8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`.
Its 1,078-entry Linux gate and both waits passed. The failed new gate does not
rewrite that evidence or validate the new transport on Linux.

## Current scientific status

The independently audited October 12 Linux clock-only diagnostic retained 11
observed wakes and one missed target. The 60-second waits returned approximately
59–60 ms late. Select-related slack is a post-hoc mechanism hypothesis, not proof
about the installed runtime or an exclusive cause. Measurement completeness and
performance acceptance remain false. The earlier counter smoke's final endpoint
missed the fixed deadline before any counter read. Preserve both failures and
the original 50-ms budget.

The absolute-monotonic adapter passed its native interface smoke and the later
finite v2 comparison retained 23 observed cells and one missed target. Recorder
integration and performance acceptance remain unverified. The active comparison is
[ABSOLUTE_SELECT_COMPARISON_V2.md](ABSOLUTE_SELECT_COMPARISON_V2.md), with plan hash
`c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d`.
V2 preserves two serial 133.3-second AB/BA runs and integer targets while allowing
one Python select call with disclosed runtime retries and unknown internal count.
The predecessor
[ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md](ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md)
and its hash `a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`
remain retained; v1 has no native result. Both hashes have literal regression pins.
Injected select/absolute collection, pair lifecycle, validation, exact descriptive
evaluation and bounded exclusive publication now exist. The native transport
first stopped on a failed Linux readiness gate. Its corrected source later passed
the gate and completed the declared pair, as audited above.

## Verification and migration

The migration receipt records 598 retained evidence files, with no imported
jobs/secrets or cloud-sync authorization. The operator reported all 1,034
bootstrap tests passed on Intel macOS / Python 3.14.6. Migration selection is
curated; omitted historical evidence remains on the originating machine.

After comparison preparation, all 1,037 local offline regression tests passed
in 92.808 seconds, including localhost fixtures. All 12 focused comparison/
absolute-wait tests passed. The new Python files pass Python 3.9 syntax parsing.
The initial restricted sandbox run could not bind localhost and was stopped;
the complete rerun with localhost permission passed. These checks do not verify
Linux ABI compatibility, native scheduling behavior or actual improvement.

## Unfinished work and continuation constraints

A finite compatibility declaration, source/runtime freeze validation and injected
launcher lifecycle rehearsal now exist; see `WAIT_EXECUTION_PREPARATION.md`.
The compatibility worker and production adapters are now implemented and tested
offline; see the production continuation below. The authorized read-only Linux
ABI/symbol, installed select-source and signal context review is complete; see the October 14 receipt below. Fresh native
preflight must match the frozen source/runtime before any further separately
authorized native execution. The single compatibility attempt below is complete.

Recorder application native compatibility and the six-case budget cohort remain
blocked. New comparison results cannot retroactively repair previous verdicts.
Frozen evidence must be audited against its originating source revisions, not
the current expanded source inventory. Preserve the source-frozen reviews and
all original measurement plans; do not edit `.qcrl/` evidence.

Keep signal feature optimization on hold, martingale closed, and the prospective
2026Q4 declaration unchanged and unexecuted until its window completes. Do not
launch captures/native experiments, provision infrastructure, import credentials,
merge into main or sync QuantConnect under this handoff. The current authorized
publication is the reviewed development branch only.

## October 13 pre-integration review

The v1 protocol hash is explicitly pinned in a regression test. The adapter now
caps complete exception text, including its name prefix, at 160 characters;
both exception paths and first-error preservation have injected regression
coverage. All 14 focused tests pass locally; the full-suite count above is from
before this repair. Python 3.9 syntax checks pass, not native runtime validation.

Upstream Python 3.9 select automatically retries signal-interrupted calls with
a recomputed timeout unless the signal handler raises. One Python call and zero
collector retries do not imply one syscall or zero internal retries. The proposed
reference therefore has an unresolved v1 execution gate: verify the exact Linux
runtime and prospectively declare a successor allowing disclosed runtime retries/
unknown counts, or separately declare a compatible reference. Preserve v1's hash;
do not silently alter its semantics. See the preregistration's October 13 review.

## October 13 v2 offline implementation milestone

Prospectively resolved the retry contract with a new v2 identity; neither v1 nor
its evidence was replaced. Zero application retries and unknown select-internal
retry counts are separate fields. Exposed faults cancel remaining attempts;
missed targets stay unknown and later original slots continue. The evaluator
preserves unknown pairs and reports rational medians without changing acceptance.
Publication is exclusive and byte-bounded; it does not claim atomicity/fsync or
native process-kill recovery. Thirty focused tests and all 1,055 local offline regression tests passed
(91.860 seconds for the full suite, with localhost fixtures). New v2 files pass
Python 3.9 syntax parsing. No Linux validation, native binding or scheduling run.

Primary development may continue offline implementation, tests, documentation
and reviewed development-branch commits/pushes without consulting another chat.
Surface material design decisions, blockers and actions outside this scope.
Native execution, main merges and QC sync remain unauthorized.

## October 13 compatibility-envelope preparation

Added compatibility plan hash
`aec6f48ff1558e544cf68665c062126ce5b44366bf8c7e9e0d18ac82268fd864`, pinned in tests.
It declares one select then one absolute wait on a 50-ms cumulative grid, without
signal injection or performance acceptance. Broad tracked-source hashing excludes
evidence/dot paths/credential scripts and refuses symlinks/oversize files. The
freeze validates LP64 timespec offsets, exact interface metadata, installed-binary
and source-review receipt hashes, positive clock resolution and read-only signal
context. No actual Linux runtime receipt or execution freeze was generated.

Injected lifecycle tests cover fresh claims, serial tests/compatibility, bounded
readiness/unit/result/journal interfaces, active binding before release, private
cleanup and public/source drift. Unit specifications have no worker entrypoint;
no production launcher or native worker is available. Thirty-eight focused local
tests and all 1,063 offline regression tests passed (85.739 seconds, localhost
fixtures permitted); Python 3.9 syntax checks passed for the new files.
Native verification and process-kill/host-loss evidence retention remain pending.

## Compatibility worker and production-adapter milestone

The worker now retains both arm slots and failed setup/interruption/missed-target
states, publishes bounded exclusive durable controls/results, and requires native
source/runtime match plus independently bound release. It installs no signal
handlers and cannot retry. The production root-Linux entrypoint runs only the
private regression-test and declared two-wait compatibility roles, with fixed
unit limits, no measurement-network access and private-only cleanup. Helper
output/deadlines, effective properties, live identities, partial journals and
final origin inventories have offline fault coverage. No new diagnostic layer.

A concrete receipt-validation gap was repaired: non-null collector/fatal errors
cannot pass even if adapter observations are marked observed. A built-in-select
fixture also required recording reviewed binary kind and hashing its actual
Python backing binary. Original compatibility/v1/v2 plan hashes are unchanged.

The source candidate will be sealed from the clean published implementation
revision under `.qcrl/reviews/wait-compatibility-source-COMMIT12/source-freeze.json`.
This is source-only: runtime remains unfrozen pending authorized read-only access
to the existing Ohio host and independent installed-binary/source review. The
full execution freeze must bind this exact source inventory and the verified
Linux runtime; no Mac/fixture runtime may substitute. Remote inspection permission
is pending. Afterward report readiness and request separate native authorization
for one compatibility smoke only; the v2 comparison remains unauthorized.

Offline readiness: the worker, production adapters and final copy/output
safeguards pass 53 focused tests. Complete exception/collector failure states,
release/setup/drift paths, effective property checks, bounded helper failures,
partial journals/source copies and exclusive claims have regression coverage.
No compatibility wait syscalls, native unit or remote inspection was performed.
The read-only remote authorization question remains pending; without installed
binary/source review the Linux runtime freeze and smoke execution readiness
cannot be claimed. The source-only candidate receipt will identify the exact
clean published commit. Full regression counts are in the preparation document.

Final verification for this milestone: all 1,078 offline tests passed in 72.261
seconds on Intel macOS / Python 3.14.6 with localhost fixtures permitted. All 53
focused tests and Python 3.9 syntax checks passed. The implementation is ready
for source-candidate sealing and authorized read-only Linux runtime inspection;
full source/runtime freeze and native-smoke execution readiness are still gated
on that installed-runtime review. No smoke authorization is implied.

## October 14 — SSH authorized; connection method still needed

The operator explicitly authorized read-only SSH inspection of the existing Ohio
host. This does not authorize native smoke/comparison units, infrastructure or
credential import. Local access checks found no documented QCRL identity file,
no SSH configuration, no identities in the existing agent, and no saved host pin
for the recorded historical Ohio address. Only an older default AWS profile is
present; it was not used to substitute for the documented scoped access. No EC2
connection, remote command, AWS API request or access-rule change was attempted.

The blocker is now the available approved connection method, not SSH permission.
Requested an existing host alias/key path or confirmation that access remains on
the original Mac. Do not copy credentials from the migration package, use unknown
legacy AWS credentials, bypass host verification or change ingress implicitly.
After a method is supplied, verify the current destination and pinned identity
before read-only installed-runtime/source review. Native execution still requires
separate authorization after the full freeze is complete.

The existing source-only receipt has been rechecked and remains bound to
`2cb688039f1b0c0bf4bae4f783902759aa263aef` (488 selected files; source seal
`9a9a36efb5fc986de8a3cffeb96712235acb66d6ad90616bad89cabf4e6c4f34`).
Its path is `.qcrl/reviews/wait-compatibility-source-2cb688039f1b/source-freeze.json`.
This documentation continuation does not replace that candidate or its evidence;
use its exact frozen checkout for runtime binding. Runtime remains unfrozen.

## October 14 — Dedicated Lupus SSH key generated

Operator explicitly authorized generating a new dedicated Ed25519 key and adding
its public half to ec2-user's authorized_keys. Generated
`/Users/eric/.ssh/qcrl_lupus_ed25519` without replacing an existing file; private
mode is 600, public mode 644. Public fingerprint:
`SHA256:ld+08VAeLSi1eLAzpKuwkTjnhUFFl7TtaRPIBmT3FDc` (comment `qcrl-lupus`).
Private material remains in ~/.ssh, outside the project/Git; none was imported.

A BatchMode/IdentitiesOnly/StrictHostKeyChecking=yes connection to the explicitly
provided Ohio address reached SSH but refused the unknown ED25519 host key before
authentication or remote command execution. No host key was accepted implicitly.
There is still no other local SSH-agent identity for bootstrapping installation.
The next access step is an existing authenticated ec2-user session adding only
the new public key and returning the trusted server public host key. Public-key
installation is authorized; changing ingress/infrastructure or running native
smoke/comparison units is not. Source candidate and prior evidence are unchanged;
runtime review remains pending authenticated access.

## October 14 — Read-only Linux review and full freeze complete

Used the operator-approved AdministratorAccess console session for Session Manager
on the existing Ohio collector. Automatic approval review initially blocked that
broad role; the operator explicitly approved its use solely for this inspection.
No IAM, ingress, infrastructure, services, packages or remote files were changed.
No credentials were imported. The dedicated SSH key remains local and uninstalled;
Session Manager supplied the needed access without changing SSH authentication.

Observed aarch64 Linux kernel `6.18.51-120.163.amzn2023.aarch64`, glibc 2.34,
GIL-enabled Python 3.9.25, 64-bit pointers/long, 16-byte timespec with offsets 0/8,
CLOCK_MONOTONIC 1 and resolution 1e-09. Bound the declared clock_nanosleep
signature without calling it. Existing handlers were observed without changes.
Python/libc/select file hashes matched their installed RPM SHA-256 manifests;
repeat hashes, boot identity and public service states were unchanged. The public
collector timer remained active/waiting and pilot/observer inactive/dead.

Fetched the exact release's official Amazon Linux source and python3-libs RPMs
locally over verified TLS, checked repository metadata/package hashes, and matched
the extracted official select extension byte for byte to the installed extension.
Reviewed the matching SRPM spec and all 43 declared patches: none changes
selectmodule.c. The retained C source confirms select's EINTR retry after checking
Python signals, with remaining timeout recomputed from a monotonic deadline;
a raising handler propagates. Runtime retries remain disclosed and uncounted.
This establishes package/source provenance, not a reproducible build or independent
RPM signature verification, and does not establish a cause of historical lateness.

Private evidence is retained under
`.qcrl/reviews/wait-runtime-20261014-jlwy2fu9/`: linux-observation.json (transcribed
from visible console output), runtime-review.json, select-review-source.c,
execution-freeze.json, official repository/RPM inputs and review-inventory.json.
Runtime-review hash:
`359b2b60db756b43ea21340b8434163abbeba13c2c15bbaf24ccd94d96ec7a9d`.
Execution-freeze hash:
`8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`.
Review inventory hash:
`4215b012370a33fa49e0ea7e1242bf040906be06e221574f2e742a0d92264843`.
The original source-only receipt and migration/frozen scientific evidence remain
unchanged; every one of the 488 source hashes was checked against exact commit
2cb6880. Current Python implementation bytes also match that candidate.

Readiness is for one separately authorized compatibility attempt: stage a fresh
private copy of exact 2cb6880 plus these controls; verify source/runtime, qcrl
ownership, disk reserve, absent private units and unchanged public prerequisites;
run the bounded Linux regression unit, then only if it passes run the declared
select/absolute compatibility unit. Limits remain CPU 75%, memory 512 MiB,
32 tasks and 240 seconds per unit. Retain readiness, release, effective properties,
journals, failures and origin inventory; no retry/replay. Audit independently
before claiming native compatibility. Staging and execution have not begun.
The AB/BA scheduling comparison and recorder budget cohort remain unauthorized.
No new diagnostic layer or protocol revision was introduced.

Local verification remains 1,078 passing offline tests on Intel macOS/Python
3.14.6, including 53 focused tests and Python 3.9 syntax checks. Linux runtime
metadata/source inspection is now real evidence; Linux tests, unit enforcement,
compatibility behavior, scheduling improvement and performance acceptance remain
unverified. All freeze execution/native/compatibility/acceptance/order flags stay
false. Request native authorization before staging or starting the finite attempt.

This review continuation reran all 53 focused offline tests successfully in 0.403
seconds and verified freeze/review hashes plus all 67 inventoried evidence files.
The full 1,078-test result above is the preceding implementation milestone, not
a new Linux or full-suite run. Documentation diff and append-only sync checks pass.

## October 14 — Authorized single native compatibility smoke passed

The operator approved fresh staging and the bounded Linux regression unit followed
only on success by the single select/absolute compatibility unit. Used the existing
Ohio host through Session Manager. No infrastructure, IAM, SSH, package or public
collector changes. Created only the fresh private stage
`/var/lib/qcrl-stream/recorder-wait-20261014Lupus01`. Anonymous partial Git clone and
sparse checkout bound exact 2cb6880 while excluding poly.py/poly2.py; no credentials
were imported. Reviewed source/control bytes and live source/runtime reproduced the
exact existing execution-freeze hash. Fresh staging/live preflight checks passed.

The declared production launcher ran once. The qcrl Linux regression unit discovered
1,078 tests in 105.240 seconds: 1,077 passed and one was skipped. The skipped test
is SyncContractTests.test_tracked_python_files_do_not_shadow_standard_library_modules,
whose frozen guard requires sys.stdlib_module_names (Python 3.10+). This reason
was identified from the frozen guard, not a verbose rerun. All pinned WebSocket
fixture gates were available. This is real Linux regression evidence, distinct
from the preceding 1,078 passing local Mac tests.

After success, the compatibility unit produced independent readiness/live binding
and hash-linked release, then observed exactly select at epoch+50 ms and absolute
at epoch+100 ms. Both returned code 0 with no errors and zero application retries.
Select's internal retry count remains unknown. Retained signed lateness was
185,322 ns (select) and 128,759 ns (absolute). These single short waits establish
interface compatibility only; their difference is not scheduling improvement or
an explanation of the historical 60-second lateness. No signal injection/handler
change or retry/replay occurred, and no AB/BA comparison was launched.

Captured effective properties match CPU 75%, memory 512 MiB, 32 tasks and runtime
240 seconds; the live resource sample also showed cpu.max 75000/100000 and
memory.max 536870912. Compatibility allowed AF_UNIX only, with denied IP access;
tests allowed numeric localhost. Both units exited successfully and were stopped.
Retained journals/properties/readiness/release/result and origin inventory report
no capture or preservation fault. Public collector states, environment-file hash,
public source HEAD and exact private source/runtime remained unchanged, including
a separate final read-only recheck. No public service was restored or restarted.

Remote evidence remains in the private stage. The local copy is
`.qcrl/reviews/wait-compatibility-native-20261014Lupus01/`. All twelve native evidence
files match the producer's origin inventory; identical reviewed control bytes were
copied from the existing local review and checked against those remote hashes.
The retained transfer archive contains the remaining exact native bytes, origin
inventory, staging preflight and launcher log/PID record. It is not in Git.

Compatibility result:
`a8927bd009b4218869a1fa91dd3b357017f963c5d97f1df427e9beefa03dcc0a`.
Launch receipt:
`b0816cfe7f0af3bac0ef5561eb3de6d3823ab2f777dfa32edffafa5410069171`.
Origin inventory:
`2770fc0c1313cb65f70770212f5d0076014961d8c673788c3b30ea70593e8da7`.
Separate offline native audit:
`c5f7e48f1dc97f38966a0d5c7dcd51761cf2f1f5644c09b446c018bb85f3a0cb`.
The audit checks source/runtime freeze, all byte hashes, valid integer brackets,
readiness/release/live PID/start/boot/cgroup identity, raw effective properties,
actual quota/memory context, unit completions, journals and unchanged final state.
It verifies native origin and this finite interface compatibility only. Producer
and frozen control authority flags stay unchanged; the separate audit does not
establish performance, recorder acceptance, trading or comparison execution authority.

No failing requirement demands another diagnostic layer or a protocol correction.
Next native action would require separate authorization for the preregistered v2
comparison after review of these receipts. Do not replay this stage or consume new
results under the single-smoke approval. Preserve all original declarations,
scientific failures and budgets. Continue authorized offline work on the development
branch; no main merge or QuantConnect sync.

## October 14 — Two-run native transport prepared offline

The operator relayed a proposed frozen two-run continuation. Readiness review found
that original candidate 2cb6880 only launches tests/compatibility; executing the
comparison under that freeze is impossible. Added a separate bounded native worker,
controller and retained-byte auditor without editing the v1/v2 declarations or
any existing Python implementation. The original full freeze, native compatibility
audit and all historical evidence remain intact. Source/runtime extension and direct
native authorization are required before execution; this is a material execution
source change, not a timing-plan revision or a new diagnostic layer.

The new controller runs a frozen Linux regression readiness gate before two fresh
AB/BA workers. Source/runtime/public drift, missing/additional skipped tests,
readiness/binding/unit/publication/capture faults stop advancement. Run-zero fatal
receipts cancel run one; nonfatal missed targets retain original targets and continue.
No retry, replay, adjustment, tuning or additional measurement run exists. Limits
remain CPU 75%, 512 MiB, 32 tasks and 240 seconds; comparison network remains denied.
Captured before/after context uses the existing bounded reader. Helper polling,
private-only cleanup and partial-evidence retention reuse the tested production
adapters. Independent audit checks bytes, identities, lifetimes, effective limits,
original arithmetic, exact summary and explicit unknown cells/context.

Offline fault coverage exposed default-handler KeyboardInterrupt as a BaseException
that the unchanged injected collector cannot directly retain. The transport wraps
only the wait/clock callable boundary, records this fault as an Exception without
handler changes or retries, and preserves prior rows. An escaping interruption
outside those boundaries after collection starts leaves the receipt unavailable;
it never fabricates a null-epoch setup result. Post-collection journal publication
retains rows if exclusive file creation fails. Kills/timeouts before publication
cannot recover all in-memory rows; retain available files/journals and report every
unavailable cell rather than claiming success or adopting a partial artifact.

The frozen Linux test expectation is 1,093 discovered with exactly the existing
Python 3.10+ inventory skip on Python 3.9.25. No new Linux test or native comparison
has run. All 68 focused offline tests pass, including 15 new transport fault tests;
Python 3.9 syntax parsing passes. Complete local regression and exact source/runtime
seal are recorded below when finalized. Native origin, comparison completeness,
scheduling improvement, recorder acceptance and orders remain unclaimed.

Final offline verification for this execution candidate: all 1,093 tests passed
in 90.520 seconds on Intel macOS/Python 3.14.6, with localhost fixtures permitted.
All 68 focused tests and Python 3.9 syntax checks pass. Seven-file implementation/
documentation diff reviewed; every original Python file, all three plan hashes
and original private evidence are unchanged. Native validation of the new transport
remains pending its separate authorization and Linux regression readiness gate.

## Sealed comparison execution candidate — October 14

Implementation commit: `b7db2c25d8550b3f75d3324846f45b2ad4c3503d`.
Selected source inventory: 491 files, each verified against that exact Git commit.
Full execution-freeze hash:
`f1339e0b54b84703368fc39efdfeb7c470ce4220bbb15d6df8284e46c0036f61`.
Private controls and local verification:
`.qcrl/reviews/wait-comparison-source-b7db2c25d855/`.
Verification receipt hash:
`4bb24cc655edafd303d91ef1608785f91165e9ab2f38ba52aaff3e6c4e335b2c`.

The freeze reuses the independently reviewed original runtime and compatibility
audit and confirms every previous Python file unchanged. It preserves all original
source/runtime/compatibility evidence and all three declared plan identities.
These later receipt-documentation commits do not replace the execution candidate;
stage exact b7db2c2, not the later documentation HEAD. Native origin/execution/
compatibility/acceptance/order flags in the new freeze remain false.

Ready to request direct operator approval of this exact new freeze: one bounded
Linux regression readiness unit (1,093 discovered, the existing Python 3.10+ skip),
then the preregistered two comparison units once in AB/BA order. No additional
compatibility smoke, tuning, replay or extra measurement run. Preserve public
collectors, retain partial evidence, stop on declared fatal/native gate conditions,
independently copy/hash/audit results and enumerate all unknowns. The forwarded
other-chat instruction is not treated as authorization for this new execution
revision. No remote staging, new Linux test or comparison call occurred during
this offline implementation/sealing continuation. Original 2cb6880 cannot run it.

Corrected local regression: all 1,093 tests passed in 97.249 seconds on Intel
macOS/Python 3.14.6 with existing numeric-localhost fixtures permitted. Fifteen
focused fault tests pass; Python 3.8.2 compilation reproduces the original nested
block failure and accepts the corrected files. No corrected Linux unit ran.

## Corrected offline execution candidate sealed — October 14

Exact candidate `cb23c4c2b6b2d7de76435bd6397415f4550e4727` contains only the
fault-test context-manager refactor and status updates relative to failed b7db.
All production Python and scientific plan hashes remain unchanged. Its 491-file
inventory matches exact Git blobs and retains the reviewed runtime and original
compatibility prerequisite. Full freeze:
`7c0ddaf5f697493302fd6791a64aacc68618d391a2a80c3bfd3a8dca198c3f55`.
Private controls: `.qcrl/reviews/wait-comparison-source-cb23c4c2b6b2/`.
Verification: `a445c94f0eb50f88821954d4ce3fb9ec07a447879ee8fb3b54708f3fe10c6db8`.
Later receipt-documentation HEAD does not replace this execution source.

Ready offline for a new operator-approved, fresh-stage Linux readiness attempt,
conditional on the unchanged source/runtime/public gates. Expected Linux population
remains 1,093 discovered, one existing skip. Only after a successful gate may the
unchanged two AB/BA runs execute once. No corrected source was staged or run on
Linux; no resumption, retry, replay, extra measurement or recorder cohort is
currently authorized. Original failed stage/receipts remain untouched. All freeze
and producer authority flags remain false; the failed gate demonstrates no
scientific comparison or acceptance. Obtain approval before any further native
unit, rather than reusing the failed attempt's permission.
