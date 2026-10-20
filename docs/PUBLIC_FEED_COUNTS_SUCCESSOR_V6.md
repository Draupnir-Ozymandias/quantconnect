# Proposed public-feed v6 — October 21, 2026, noon EDT

**Historical application FAIL remains unchanged.** V5 stays interrupted with
unverified/censored coverage, v4 partial/unresolved with all 60 original rows null,
v3 retains its closure fault/unverified coverage, and v1/v2 remain not_run. This
prospective packet does not repair those outcomes or provide a combined badge.
**Preparation only: staging and execution require separate exact-packet approval.**

## One question and one fixed opportunity

Can this recorder retain auditable observations across interruptions while
correctly marking unavailable acquisition and per-connection book eligibility?
This is one public-feed descriptive validation, not a trading/execution,
real-market performance, maintained-book accuracy or venue-completeness study.

| Item | Exact prospective declaration |
| --- | --- |
| Case | `btc5m-20261021T160000Z-local-counts-06` |
| Product | One public Polymarket BTC five-minute Up/Down condition, both CTF tokens |
| Event terms | October 21, 16:00–16:05 UTC / noon–12:05 PM EDT |
| Launcher opportunity | October 21, 15:44–15:55 UTC; at most 90-second pre-window wait |
| Controller | One invocation during 15:45–15:55 UTC |
| Metadata | One opportunity at 15:55 UTC; at most five GETs / 30 seconds |
| Identity lock | Before 15:59 UTC |
| Private unit arm | 16:00:40 UTC |
| Nominal count minute | 16:01–16:02 UTC / 12:01–12:02 PM EDT; five-second tail |
| Stage | `/var/lib/qcrl-stream/public-feed-20261021T160000Z` |
| Unit | `qcrl-public-counts-20261021T160000Z.service` |
| Host | Existing Ohio instance `i-039c11d5ea49cf413`, pinned SSH `qcrl-ohio` |

Market existence/condition/token IDs are unknown until that sole metadata
opportunity. Require declared matching terms, description/resolution source,
300-second duration and both token bindings; lock before cutoff. No substitute
market, second metadata opportunity, rollover, controller/unit retry, replay,
extra capture, smoke or six-case cohort. Missing approval/access/readiness/deadline
means not_run. After a start retain partial evidence/faults and stop afterward.

Do not induce a disconnect. At most three sequential in-unit connection attempts
are allowed by the contract below, not three studies. If no disconnect occurs,
public reconnect behavior remains **unobserved/inconclusive**, with no automatic
extra run. Even a normal final epoch does not prove recovery of missed messages.

## Prospective identities and source review

| Identity | SHA-256 |
| --- | --- |
| V6 study plan | `6b4d7c4943523e025b645b0f0677e0b7d43e3c11ee1c82624176750ab0e2752c` |
| Unchanged v5 parent plan | `8f36b9350255135ad18445fe602677d3fb6600844f2a546a6c9ecff2414568c9` |
| Recovery contract v1 | `437621e12790da88843eb418b649af6a00972566b21a86d94e11a43b266c6f04` |
| Stop ownership v1 | `dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3` |
| Creation notice v1 | `6dec039e13620846ed83b0850d0d36a83325cb5afbf87372742359b7cd70bceb` |
| Pre-close publication v1 | `9b07b4ecfa5c2c9a186e8f6a9bcb2e25fc2a890aeac98a65579de83a7d5a0f0e` |

All are literal regression anchors. [Recovery contract](PUBLIC_FEED_RECOVERY_CONTRACT_V1.md)
defines the method. The new worker/operator selection is explicitly
`--study-version v6`; default v5 remains unchanged and cannot adopt a v6 case or
freeze. The controller, metadata subprocess and recorder unit all bind the same
selected plan, namespace and source. Wrong-version freezes stop before a claim or
request. Case/spec, callback population, consumer/checkpoint and report bind v6.

Review found a concrete fault-path mismatch: a fatal foreign text was archived
before the stop, but epoch bookkeeping skipped it while offline replay consumed
it. The prospective path now observes its existing return stamp before enforcing
the unchanged fatal binding rule. This aligns the conservative last-return gap
boundary and allows the retained prefix to be audited; the foreign fault still
stops, remains visible and never qualifies book state. No historical result was
regenerated under this source.

The metadata transport's slug allowlist also binds the selected plan explicitly,
rather than the v5 default. A direct local HTTP-adapter fixture exercises the
v6 path and rejects the expired v5 slug before any request.

The v6 report separately verifies/replays recovery lifecycle markers. If lifecycle
linkage fails while raw completion linkage verifies, it retains raw interval counts
and withholds all eligible bounds/availability claims. Missing/corrupt final
consumer never silently falls back to a favorable checkpoint. Missing archive
makes counts null; valid checkpoint-only output remains close-unverified. There
is no combined acceptance badge or conversion of faults into successful coverage.

## Recovery, gaps and counts

Reuse existing watchdogs, jitter, book/timestamp validators, writer, persistence,
storage and deadline ownership. Maximum **three connection attempts / two retries**
total. Existing equal-jitter waits are 1–2 seconds and then 2–4 seconds, clipped to
the common acquisition deadline. Close the failed socket before opening another;
no overlap or background retry queue. Each successful handshake sends the entire
original subscription. Send return is not an acknowledgement.

Every connection gets a new numbered epoch and fresh heartbeat/watchdog/book
state. Eligibility starts strictly after new, structurally valid full books for
both selected assets on that connection. Each snapshot's valid millisecond payload
timestamp must have nominal delivery age 0–5 seconds, and both qualifying receipts
must be no more than five monotonic seconds old at bootstrap completion. These
are declared nominal/bootstrap rules, not continuously verified state freshness.
Old books, deltas, PONGs and lifecycle notices cannot satisfy bootstrap. Bootstrap
texts remain in the raw population and are excluded from the eligible subset.

Recover only transport-origin OSError/premature WebSocket closure (including
premature `ConnectionClosedOK`) and declared initial-book/data-silence/stale-flow/
PONG watchdog reasons. Certificate verification, foreign bindings, clock/linkage,
binary/oversize, storage/archive, cancellation, fired/error guard receipts and
failed retry close are fatal. Retain every earlier fault even if a later epoch
reaches its scheduled deadline. A watchdog firing never establishes success.

Retain all incoming texts exactly once, including accepted creation notices,
PONGs and identical deliveries after reconnect. No deduplication, batch expansion,
replay or favorable-subwindow filtering. Hash-linked epoch/end markers and the
same completion witnesses bind ordered occurrences to their connection epochs.

Use unchanged interval-aware counting for all 60 one-second bins, preserving
ambiguous, unplaced, original wide-bracket, prewindow and tail labels. Eligible
counts are a separate subset: the whole return interval must lie strictly within
one post-bootstrap epoch window. Do not silently replace raw counts with it.

A failed epoch's conservative availability end is the last return's **before**
endpoint (or subscription/attempt if no return). Its detection time does not prove
when loss began. Explicit unavailable complements include initial connect, failed
attempts, close/backoff, resubscription and terminal remainder. Book-ineligible
complements additionally include each bootstrap. Do not erase a gap on reconnect.
Only a bin wholly inside an observed local acquisition interval may label zero
archived texts as observed silence. A boundary/gap bin with zero retained texts
has unknown activity. All feed-activity upper bounds and full-minute feed
population remain null. Reconnecting cannot recover or bound missed messages.

## Unchanged bounds and clock/resource limits

One fixed M0 after-endpoint monotonic/UTC anchor and upward nanosecond rounding;
60 half-open bins and five-second tail. UTC is nominal, with no independent
accuracy bound. Required clock/linkage failures stop; ordinary UTC/RSS width
violations remain visible under the original component requirements.

Acquisition ends at min(M0+65, first attempt+90 seconds), at most **60,000 texts
across all connections**. The 90-second acquisition process guard is never renewed
by retry and remains armed through sealing/pre-close publication. First readiness
is before M0−1 and at most ten seconds; subsequent connection/subscription bounds
are at most ten seconds clipped to the same deadline. Ordinary receive waits
remain capped by the persistence schedule. Text PING every ten seconds, 30-second
PONG timeout; existing data watchdog limits remain. Separate close bound five
seconds, also capped by remaining acquisition time during retries. Final cleanup
close can still stall or fail; process termination can leave only partial bytes.
No publication or persistence margin is guaranteed.

Same verified TLS/CA and installed websockets; disabled compression/automatic
protocol ping, 262,144-byte incoming cap, queue 16. No iterator-based reconnect or
account/auth/proxy fallback. Internal runtime/TLS retries and kernel retransmission
counts remain unknown. The explicit three-attempt counter is not a measurement of
those internal retries.

Same CPU75%, Memory512MiB, Tasks32, Runtime240sec; gzip1 and 8MiB raw segments,
1GiB raw/256MiB compressed, 32MiB completion, 64MiB auxiliary/1GiB private spool,
initial2GiB free and1GiB disk reserve. No eviction/rollover/overwrite. Original
<=1ms UTC, <=5ms RSS, <=50ms RSS-start and every CPU/RSS/append/durability threshold
remain authoritative. Additional control parsing, epoch clock reads and lifecycle
writes occur outside the unchanged return bracket; transport-wrapper overhead is
not assumed neutral. No cost is subtracted. Incremental observer overhead and
continuous RSS peak remain unknown without independent evidence.

## Readiness, approval and independent audit

Read-only pinned SSH on October 20 at 19:54:31Z verified the existing v5 stage's
555 source hashes, installed runtime/binary/dependencies, TLS/CA, boot and public
collector state against its retained freeze. Free disk: 6,123,982,848 bytes. The
new target stage is absent and unit not found; preparation started zero metadata
requests, subscriptions, controllers or native units. These observations establish
expected installed bytes, **not Linux validation of the new v6 source**. The
preserved runtime host record includes historical credit context; fresh credit
mode/balance were not obtained. No minimum, within-run credit history or new
acceptance gate is invented. Refresh these read-only readiness gates before any
approved stage/start; a mismatch stops without substitution.

After exact-packet approval only, activate the predeclared operator-receipt bytes
using a separate direct approval confirmation, stage once in the unused namespace,
verify all selected source/member hashes, and invoke the prepared launcher once
in its declared window. It durably/exclusively claims before a single Popen with
DEVNULL stdin, retained log, new session and original default HUP/TERM dispositions;
never nohup. An existing launch/controller/evidence claim forbids relaunch.
Controller owns the sole metadata opportunity, unit, release and stop/sealing.
No source/runtime substitutions from later documentation HEAD.

Independently observe controller PID/start/argv/signals, then promptly bind the
short-lived private worker at arm: PID/start/boot/cgroup/argv/effective limits,
ready/release/epoch and original signals. Missed independent live observation
remains unknown; producer checks cannot replace it. This is the existing required
read-only binding, not a new in-recorder observer.

After bounded completion independently inventory/copy/hash/seal all retained
controls/evidence, reconcile complete file population and producer inventory,
and use this exact source for offline report/audit. Verify archive/header/footer,
ordered completion/frame/barrier linkage, source/runtime/domain/case/epoch,
final consumer or close-unverified checkpoint, every epoch/gap/retry/subscription,
fresh-book witnesses, all 60 raw/eligible interval rows and ambiguity/unplaced/
prewindow/tail/censoring. Verify inclusive resource/precision and missed-slot
context separately; missing samples are not automatically scheduler misses.
Check exact private processes gone/unit inactive and public state unchanged.
Preserve faults/partial evidence and every unknown; no automatic repeat.

## Final offline verification before source freeze

All **1,280 tests passed in 167.599 seconds** on Intel macOS/Python 3.14.6.
The focused recorder/recovery/stop/publication/v6 integration set passed **79 tests
in 17.548 seconds** after the actual metadata allowlist correction. Changed Python
accepts 3.9 grammar locally; no new-source Linux runtime test was executed.
The earlier local development checkpoint is not substituted for these final runs.

Local tests cover explicit plan/version and namespace selection, actual metadata
URL gating, wrong-version rejection before controller claim or request, actual
production consume/recovery/checkpoint/final report wiring, normal/failed/retried
epochs, fatal foreign retention, corrupt/missing consumer/archive/completion and
lifecycle linkage, and all earlier stop/storage/clock/boundary regressions.
Private logs: `.qcrl/reviews/public-feed-20261021T160000Z/`. No native staging,
launcher/controller, metadata GET, unit, subscription or automation was started.

The committed execution source, sealed transport and runtime-envelope anchors
will be appended in the final approval record; they must not be inferred from a
later documentation HEAD. Active operator approval/direct confirmation are absent.

## Exact sealed approval packet — pending human approval

Execution source **`fc89c11c8c9186c866385b373db12ba04c721e33`**, **561 selected files**.
Freeze SHA-256:
`763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b`.

Nine-member private transport: **113,576 bytes**, SHA-256
`e0e46e15005fa68e97c8dbb2b0cdde9ca76cfc05e2731da063de23cc4029e8c6`.
Local path: `.qcrl/reviews/public-feed-20261021T160000Z/stage-packet.tar.gz`.
Candidate bundle prerequisite is retained v5 commit
`f89ada8cb43036464cd77c08fe4ca7829fbc634a`. Every member hash/population, all committed selected
source hashes and Git bundle verification passed. Members: candidate bundle,
execution freeze, proposed operator receipt, runtime review, select review source,
preserved host context, fresh-verification context, read-only readiness receipt
and one-shot launcher. Historical host/credit fields are not relabeled fresh.

Launcher SHA-256:
`e4e2f5c4ee2362acadbebc53385aba07c99e7a34108b5b3c7a1700e5b792d8f5`.
Local mocked tests checked four scenarios: valid one-start ordering with claim
before Popen, missing approval, expired window and existing claim. Second launch
was refused; Popen was mocked and no native command or public socket ran. The
staging generator separately refuses activation without direct confirmation.
Existing independent binding/copy/inventory/audit helpers have been adapted to v6,
including independent raw/eligible interval recomputation, and accept Python3.9
grammar locally. This is preparation, not execution of the native audit paths.
Transport review file SHA-256:
`69d91cad064f78e912fb8f9c9fb418f673716e18c2be4e36f69869b6ba62faba`.

After separate approval and successful staging/readback, the sole launch command,
only in the declared October21 15:44–15:55 UTC opportunity, is:

```sh
sudo -n /opt/qcrl-stream/venv/bin/python \
  /var/lib/qcrl-stream/public-feed-20261021T160000Z/launch-once.py \
  --execute 763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b
```

The controller and all subprocesses explicitly select v6. The offline report uses
this exact source with `python -m infra.stream.recorder_public_study report
--study-version v6 --root RETAINED_EVIDENCE`; it acquires nothing. Independent
origin/copy/source linkage remains required before interpreting that output.

**Approval requested:** stage this exact packet once, then run one conditional
October21 BTC v6 capture under these gates, with at most three sequential in-unit
connections/two declared retries, and independently audit/stop afterward. This
permits no induced disconnect, extra capture, standalone smoke, cohort, replay,
substitution, rollover, resource/infrastructure/public-collector change or
credential import. If reconnect never occurs, report that component inconclusive.

No active `operator-approval.json`, direct `execution-confirmation.json`, native
stage, scheduler, controller, metadata GET, capture unit, subscription or follow-up
automation was created. Source/runtime readiness after staging and at execution is
still conditional. The exact frozen source is the execution authority's byte
anchor; subsequent documentation-only HEAD is **not** a substitute.

## Subsequent direct approval and staging — October 20

The user directly approved this exact packet: “i approve. please proceed.”
Separate confirmation payload SHA
`e27f98a444440add259db324f28757a0476141938926a43897911c808425617d` binds the approved case,
freeze and recovery policy. The original declaration, proposed receipt, sealed
packet and source/runtime envelope remain unchanged. Exact receipt bytes were
activated after this separate approval; template flags alone grant no authority.

Fresh read-only SSH gates passed at 22:06:25Z. Staging completed once at
22:06:47Z in the declared unused namespace, with all 561 source/runtime/TLS/public/
approval gates passing and 6,095,101,952 free bytes. Independent readback at
22:07:27Z matched packet/freeze/confirmation/receipt/launcher hashes and root
permissions; source/runtime/TLS/public checks passed. Evidence/controller absent,
metadata GETs=0, native units=0, unit not found; launcher remains unexecuted.
No remote scheduler exists. These are native staging/readiness checks, not new
Linux functional/public-feed validation or measured acceptance. Credit records
remain historical/unavailable context; no new credit gate.

One local thread follow-up, `run-and-audit-the-approved-btc-v6-capture`, is active
for **October 21 at 11:44 AM EDT / 15:44 UTC**. It is authorized to refresh gates
and start the prepared helper once in its existing opportunity, then independently
bind/observe/audit only that attempt, update HANDOFF/outcome, commit/push and delete
itself after final audit or definitive not-run. The exact helper enforces its
window and durable claim; late wake or failed readiness means no rollover. No
remote scheduler, detached early controller or capture was started today. The
Mac/app must remain available for this local follow-up. No further routine
approval is needed within the exact one-case scope.

Only declared in-unit recovery is allowed: up to three sequential connection
attempts/two retries under one common runtime/storage/frame envelope. No manual
controller/unit retry, forced disconnect, extra capture, replay, substitution,
smoke, cohort or infrastructure/public-collector/resource change. No reconnect
means inconclusive for that component. Preserve all faults, original thresholds,
historical failed outcomes and unknowns; no combined acceptance badge.
