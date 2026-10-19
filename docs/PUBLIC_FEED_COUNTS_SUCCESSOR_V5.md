# Proposed public-feed v5 — October 20, 16:00 UTC

**Historical application FAIL remains unchanged.** V4 remains partial/unresolved
with all 60 original rows null; v3 retains its closure fault/unverified coverage,
and v1/v2 remain not_run. This is a prospective source and capture proposal, not
execution approval, a repaired result or a combined acceptance badge.

## Offline findings and prospective identities

V4 retained a `new_market` creation notification with another condition ID,
then stopped under its declared rule. Its SIGTERM exit about five seconds later
is consistent with the close guard, but the sender and exact close progress remain
unknown. Review used retained bytes and frozen code only; no new market/feed
request or remote command was made during this offline implementation.

[Official real-time documentation](https://docs.polymarket.com/market-data/realtime-data),
checked October 19, describes creation notifications among custom-feature events
and supplies the raw `new_market` envelope. It does not establish a routing or
venue-completeness guarantee. The observed v4 event supplies concrete evidence of
one other-condition notification on this subscription. The successor handles that
specific event family prospectively; it does not relabel v4 as successful.

| Contract | Prospective SHA-256 |
| --- | --- |
| Creation notice `qcrl.public_creation_notice.v1` | `6dec039e13620846ed83b0850d0d36a83325cb5afbf87372742359b7cd70bceb` |
| Pre-close publication `qcrl.public_acquisition_publication.v1` | `9b07b4ecfa5c2c9a186e8f6a9bcb2e25fc2a890aeac98a65579de83a7d5a0f0e` |
| Unchanged normal stop ownership v1 | `dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3` |
| V5 study | `8f36b9350255135ad18445fe602677d3fb6600844f2a546a6c9ecff2414568c9` |
| V4 parent, preserved literally | `359488dc8de8d90508f905411cc3734d5ce78acf763d951813b606fd71354d73` |

A recognized creation notice must have exact raw `event_type=new_market`, a
64-hex-digit condition in `market`, 2–64 distinct ASCII decimal token strings in
`assets_ids`, and equally many nonempty outcome labels. Optional `condition_id`
and `clob_token_ids` aliases must agree. Book/trade/order payload fields and nested
protocol envelopes do not receive the exemption. Another-condition notice must
not overlap selected tokens; a selected-condition notice must bind exactly the
selected token set. Malformed or inconsistent foreign bindings remain fatal.
Other explicit foreign condition/token bindings—including book/trade and
`market_resolved`—remain fatal. No broad exemption based on an event name alone.

Accepted creation notices are retained once and counted once in the same incoming
text population. Classification remains `unconfirmed_or_other_market` for another
condition; no selected-market book state is built from them. The question concerns
**texts on the selected subscription**, which can include lifecycle notifications
about other markets and PONGs, not counts of selected-market trades or updates.
No filtering, deduplication, batch expansion or favorable-subwindow selection.

## Ownership and failure-critical publication order

The actual acquisition path now ends acquisition and seals its archive before a
potentially blocking socket close. The production worker publishes the existing
single-use completion sideband followed by one exclusive, durable
`acquisition-checkpoint.json`, then attempts close. That checkpoint is the minimal
persistence change required by v4's lost evidence; no observer, profiler, tracing
framework, extra timer or new diagnostic experiment is added.

The checkpoint has `closed=null`, `close_completed=false`, `close_verified=false`.
It binds case/result/identity/domain/epoch and does not claim final resources or a
stopped observer. The ordinary observer continues on its existing schedule until
the original worker-finally stop after close. Its sampling semantics and all
application-return clock brackets are unchanged. Added serialization/fsync/control
work is uncalibrated and never subtracted.

The acquisition process guard remains armed through sealing/checkpoint publication
at its original attempt+90-second deadline. It is canceled before the separate
unchanged five-second close guard. The 240-second unit ceiling and original
resource/storage limits remain. Publication inside that envelope is **not a
completion-margin guarantee**: a blocked persistence/publication can still leave
partial evidence. No retry or second snapshot is used after a publication failure.
Guard callbacks mark their fired state before SIGTERM; cancellation cannot erase a
fired guard or convert it into a successful final result.

Final `consumer.json` is published only after close returns or raises; it preserves
acquisition, publication and close errors. Actual close return and no fired close
guard are required for `close_completed=true`. A valid checkpoint without a final
consumer can support independently linked **prefix** intervals/counts, with censored/
unverified coverage. It never establishes full-window coverage, successful close
or a combined acceptance verdict—even after normal acquisition ownership. A corrupt
final consumer cannot silently fall back to a more favorable checkpoint. Archive
session-end now means acquisition sealing; it alone does not prove transport close.
The report still requires final consumer, successful close, normal acquisition
ownership and every original linkage/coverage condition before any `recorded` label.

## One proposed target; no additional smoke

| Item | Fixed prospective declaration |
| --- | --- |
| Case | `btc5m-20261020T160000Z-local-counts-05` |
| Product | Public Polymarket BTC five-minute Up/Down, one condition, both supported CTF tokens |
| Event terms | October 20, 2026, 16:00–16:05 UTC / noon–12:05 PM EDT |
| Controller window | October 20, 15:45–15:55 UTC / 11:45–11:55 AM EDT, one invocation |
| Metadata opportunity | 15:55 UTC, at most five GETs within 30 seconds |
| Identity lock | Before 15:59 UTC |
| Private arm | 16:00:40 UTC |
| Nominal count minute | 16:01–16:02 UTC / 12:01–12:02 PM EDT |
| Stage | `/var/lib/qcrl-stream/public-feed-20261020T160000Z` |
| Unit | `qcrl-public-counts-20261020T160000Z` |

This one public attempt is the smallest proposed native follow-up. No standalone
smoke, timing experiment or cohort is proposed. Market existence/IDs remain unknown
until the sole discovery opportunity. Require explicit matching 300-second terms,
resolution/description and both token bindings. Missing approval/readiness/access/
deadline or invalid discovery means stop/not_run; after a start, preserve partial
outcomes and stop. No substitution, retry, reconnect, replay or rollover. The other
foreign event families remain declared stopping risks, not presumed solved.

Retain one after-endpoint monotonic/UTC anchor and exact represented arithmetic,
one upward nanosecond rounding, fixed M0 and 60 half-open one-second bins. Use
closed callback intervals for definite/possible counts; retain ambiguous, unplaced,
pre-window and five-second-tail occurrences. UTC labels are nominal, with no
independent accuracy bound. Missing activity is never zero-filled. Linked prefix
bounds describe retained occurrences only; unknown missing feed activity has no
inferred finite upper count. No archive-row timestamp substitutes for a callback.
The unchanged draft and original execution contract apply except for the explicit
successor identity, notification rule and publication ordering declared here.

Normal acquisition still ends at min(M0+65 seconds, attempt+90 seconds), at most
60,000 texts; one connection, readiness before M0−1 second, ten-second bounded
connection/subscription and five-second close. Preserve verified TLS/CA, installed
websockets 15.0.1, disabled compression/automatic protocol ping, incoming size
262,144, max_queue16 and ten-second text PING. Runtime syscall/TLS retry behavior
remains documented; internal retry and kernel retransmission counts are unknown.
No account/auth/proxy fallback or execution/trading path.

Keep CPU75%, Memory512MiB, Tasks32, Runtime240sec; gzip1, 8MiB raw segments,
1GiB raw /256MiB compressed, 32MiB completion sideband, 64MiB auxiliary and 1GiB
spool limits, initial2GiB free and1GiB reserve. Existing persistence reserve is
prospective, not a guarantee. Preserve <=1ms UTC, <=5ms RSS, <=50ms RSS-start and
all CPU/RSS/append/durability thresholds. Ordinary width exceedances remain visible
component failures/unknowns; required clock/linkage/identity/storage/unit-limit
faults still stop. No observer optimization, resource change or public-collector edit.

## Readiness and independent review

This turn is offline. Expected installed runtime/TLS/host context is retained from
v4 and explicitly historical; fresh read-only Linux verification is outstanding.
StopOwn01 demonstrates an earlier-source Linux loopback normal-stop case only.
The new notification/publication ordering has no Linux validation yet. Fresh
credits remain unavailable/historical, with no inferred minimum or new credit gate.

Before any future start, require exact-packet approval, clean frozen source,
installed runtime/dependency/binary/TLS/CA/boot/public-state match, disk and unused
namespace, prospective metadata/case lock, actual unit limits and independent
live PID/start/boot/cgroup release. Launch once with original HUP/TERM dispositions,
DEVNULL stdin, retained log and `start_new_session=True`; no nohup. A separate direct
approval confirmation must activate the exact proposed operator receipt. Later
documentation HEAD must not substitute for the frozen execution source.

Afterward stop, independently inventory/copy/hash/seal the complete retained
population and exact sources; verify archive/completion/consumer-or-checkpoint/
domain/case linkage, actual close state, all60count rows, ambiguity/unplaced/
pre-window/tail/censoring, gaps/missed slots and original precision labels. Report
inclusive resources separately. Incremental overhead, continuous RSS peak,
independent UTC accuracy, internal retries and venue completeness remain unknown
absent independent evidence. Preserve all original failed/not-run/partial outcomes.
Synthetic tests establish behavior on those test paths only, not real-market
performance. No combined badge, trading or execution conclusion.

No SSH, native staging/unit/capture or follow-up automation was started this turn.
The exact sealed packet and local test evidence will be recorded below before
requesting approval for this new target.

The underlying native close stall is not causally established or claimed solved.
The installed synchronous client's close waits for handshake/TCP completion and
incoming-message drainage; that is a plausible context, not proof of v4's cause.
This change makes sealed acquisition evidence available before that operation.
A future five-second guard exit can still occur. Its linked prefix may answer
archived-occurrence questions, while close and full recording coverage remain
unverified. No favorable exit status or checkpoint is used to erase that fault.


## Offline verification before source freeze

All **1,250 tests** passed in **166.923 seconds** with
`PYTHONPATH=.:tests .venv/bin/python -m unittest discover` on Intel macOS/Python
3.14.6. The final **49 focused tests** passed in **12.627 seconds**, rerun after
additional creation-notice size/ASCII/selected-binding boundary cases. Changed
Python accepts 3.9 syntax locally. These are offline checks, not Linux validation.

Tests cover the actual production `consume` wiring and collector/writer/witness
paths, early faults and normal acquisition, pre-close single-use publication,
close errors, real default-SIGTERM subprocess bounds with evidence surviving a
blocked close, process-guard callback/cancel races, notification mixed batches and
malformed/contradictory envelopes, publication errors without retries, malformed/
mutated checkpoint linkage, and corrupt or dangling-symlink final receipts without
favorable fallback. Existing clock-failure and interval/report regressions pass.
V1/v2/v3/v4 plan dictionaries retain their literal hash regressions. The actual
retained v4 event was separately checked: its frozen source still rejects it,
while this prospective notice recognizer accepts it. No historical count report
was regenerated under the new source to repair an old outcome.

## Sealed conditional approval packet — offline, not staged

Exact execution source: `f89ada8cb43036464cd77c08fe4ca7829fbc634a`, **555 selected
files**. Freeze SHA-256:
`7cd0b049ff9380aa405d5368bc197205363654244862c2f328d50a58e236f12f`.
Seven-member transport: **94,642 bytes**, SHA-256:
`0c1fd7a4db9edb05ceb8007a2ccb7da91ea897431c15025ae9ab6c7ec06c91c0`.
Private packet: `.qcrl/reviews/public-feed-20261020T160000Z/stage-packet.tar.gz`.
The bundle requires retained ancestor `706ebed052945235dd44e7a5c5ef6a231059576c`.
All member hashes, complete member population, all 555 committed source files,
policy bindings, unchanged limits and bundle verification independently passed.
Later documentation HEAD does not replace this source.

Contents: candidate bundle, freeze, proposed operator receipt, installed select
review/source, historical host context, and explicit expected-runtime context.
The latter records the previous native observation at October 19 16:01:07Z and
says fresh verification has **not** happened this turn. It supplies no fresh clock,
credit or host-readiness guarantee. The active operator approval is absent.

Approval of this exact freeze would authorize fresh read-only Linux gates, staging
once if those gates pass, one conditional October 20 capture and independent
retention/audit/commit/push afterward. It would not authorize a replacement window,
replay, retry, extra native validation, observer tuning or cohort. A failed/missed
gate stops this target without rollover. A separate direct confirmation must
activate the proposed receipt; the file template alone grants no authority.

Only after approval, staging and successful fresh gates, the exact controller argv
would be:

```text
/opt/qcrl-stream/venv/bin/python -m infra.stream.recorder_public_operator controller --root /var/lib/qcrl-stream/public-feed-20261020T160000Z --freeze-sha256 7cd0b049ff9380aa405d5368bc197205363654244862c2f328d50a58e236f12f --execute
```

Invoke once as root from the exact staged source, only in the controller window,
using the declared session/log/signal settings. The controller owns the sole
metadata opportunity, case lock, unit submission and independent release; do not
invoke those separately. No stage, launcher, controller, unit, subscription or
follow-up automation has been created for v5.


## Subsequent direct approval and staging — October 19

The user directly approved this exact freeze: “absolutely”. Separate confirmation
payload SHA `6a13886dc3011b1c4151686695d6cd7eb2bd58128b907a9cf63fb82f60e6ae26`
records that authorization. The frozen declaration, runtime-context checkpoint and
proposed receipt bytes remain unchanged; the latter were installed under the active
operator-approval filename only after separate direct approval. Their template-only
flags do not themselves establish authorization. No future human approval is claimed.

Fresh read-only Linux verification passed at 21:52:01Z, including unchanged runtime,
TLS/CA/public/boot, free disk and unused namespace. Staging completed once at
21:52:12Z, verifying all 555 source files and expected installed bytes; free disk
was 6,144,364,544 bytes. Independent 21:53:24Z readback matched local packet/freeze/
confirmation/receipt/launcher hashes, root permissions and source/runtime/TLS/public
checks. No controller, evidence directory or unit exists, metadata GETs and native
unit starts are zero, and no feed subscription was started. This is staging
readiness; the new ordering has not been exercised by a Linux capture. Fresh gates
still apply at launch. Credits were not refreshed or converted into a minimum gate.

Prepared, unexecuted `launch-once.py` SHA:
`b94e1b7a2866eb7c6eac897c15d5a3aaede8c641c7eda1382c3555fac82cb822`.
It is control transport outside the frozen measurement source. It accepts only
October 20 15:44–15:55 UTC, waits at most 90 seconds for the controller window,
refreshes gates and the direct confirmation, and durably claims one launch before
Popen with original signal/session/log settings. An existing claim prevents a
second launch. No remote scheduler or native unit is running for v5.

One local thread follow-up, `run-and-audit-the-approved-btc-v5-capture`, is scheduled
for **October 20 at 11:44 AM EDT / 15:44 UTC**. It will refresh gates, invoke that
helper once if eligible, obtain live unit binding promptly at arm time, observe
only the declared attempt and independently audit final or partial evidence using
the exact frozen report. Missing live observation must remain unknown. A checkpoint
alone never proves close or full coverage. Failed access/readiness/deadline stops
without rollover. The follow-up deletes itself after final audit or definitive
not-run. No further routine approval is required within this exact one-case scope;
no extra smoke, cohort, retry, infrastructure/resource or public-collector change.
