# Proposed fixed public-feed target v4 — October 19, 16:00 UTC

**Historical application FAIL remains unchanged.** Prior v1/v2 targets remain
not_run; v3 retains its closure fault and unverified coverage. No combined
acceptance verdict, trading/execution claim or venue-completeness claim is defined.
This packet is preparation for review, not authorization to stage or execute.

## Exact question and window

How many archived public-feed text occurrences can be assigned definitely or
possibly to each second of one selected minute?

| Item | Proposed fixed declaration |
| --- | --- |
| Identity | `qcrl.public_feed_interval_counts.study.v4` |
| Policy SHA-256 | `359488dc8de8d90508f905411cc3734d5ce78acf763d951813b606fd71354d73` |
| Parent policy SHA-256 | `6cdc0386787c0a6bd68ac0061e59c6f50b657dfac19f2ec27bd056f336488533` |
| Case | `btc5m-20261019T160000Z-local-counts-04` |
| Product | Public Polymarket BTC five-minute Up/Down; one condition, both supported CTF tokens |
| Event terms | October 19, 2026, 16:00–16:05 UTC / noon–12:05 PM EDT |
| Controller start | Once, October 19, 15:45–15:55 UTC / 11:45–11:55 AM EDT |
| Metadata | One opportunity at 15:55 UTC, at most five GETs within 30 seconds |
| Identity lock | Before 15:59 UTC |
| Private unit arm | 16:00:40 UTC |
| Nominal count minute | 16:01–16:02 UTC / 12:01–12:02 PM EDT |
| Stage | `/var/lib/qcrl-stream/public-feed-20261019T160000Z` |
| Unit | `qcrl-public-counts-20261019T160000Z` |

Market existence, condition/token IDs, metadata terms and resolution binding are
unknown until that single discovery opportunity. Require exactly matching explicit
300-second event terms and both supported token bindings. Missing/ambiguous/
contradictory metadata, absent approval, readiness failure or missed deadline means
not run, with no substitute or rollover. Once attempted, retain partial evidence
and stop on failure. No retry, replay, reconnect, second target or six-case cohort.

The unchanged [draft](PUBLIC_FEED_INTERVAL_COUNT_STUDY_DRAFT_V1.md) and
[v1 execution contract](PUBLIC_FEED_COUNTS_EXECUTION_V1.md) retain their measurement,
counting and storage requirements. This successor supplies a new identity/window/
namespace and binds [stop ownership v1](PUBLIC_ACQUISITION_STOP_OWNERSHIP_V1.md).
Original v1/v2/v3 policy dictionaries and literal regression hashes are preserved.
The original draft's historical authorization/readiness statements describe its
checkpoint; this proposed packet requires separate approval for the new target.

## Lifecycle change and evidence limits

Policy SHA `dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3`
is bound in the plan and checked at the production worker gate before feed I/O.
The acquisition thread must claim normal completion under the interrupt's lock,
with an OPEN transport and fresh nonregressing time before the emergency cutoff,
and disarm the emergency interrupt before local close. Emergency/cancel ordering
is exclusive. Fired interrupts, early peer closure and genuine send/receive/close
faults remain faults, including across the stop race.

Normal acquisition target stays `min(M0+65 s, attempt+90 s)`. The prospective socket
emergency cutoff is 250 ms later, capped at the same 90-second acquisition bound.
This separation is not extra authorized acquisition or a margin guarantee.
Default-SIGTERM acquisition and five-second close guards remain bounded by the
240-second unit ceiling. Added control work remains uncalibrated and unsubtracted;
no timing calls were added inside the original UTC or RSS brackets.

[StopOwn01](PUBLIC_STOP_OWNERSHIP_OUTCOME_20261018.md) independently verified
68/68 loopback texts and normal ownership on Linux. It did not exercise TLS or
public transport, resource acceptance or native fault injection. The failed public
v3 recording remains public-path evidence with its original limitations; it is
not retrospectively repaired by this source. No standalone smoke is proposed.

## Counting, clocks, gaps and limits

Freeze one after-endpoint monotonic/UTC anchor before feed receipt. Compute M0
with exact represented arithmetic and one upward nanosecond rounding. Keep exactly
60 half-open one-second bins `[M0+k,M0+k+1)`. For each closed callback interval,
lower counts intervals wholly inside a bin; upper counts those intersecting it.
Retain boundary ambiguity, unplaced occurrences, pre-window and five-second tail.
Every returned supported text counts once, including duplicates, batches, PONGs,
malformed and unknown schemas; no deduplication or batch expansion.

UTC labels are nominal. Independent UTC accuracy and network/source-event timing
are unknown. Preserve the original <=1-ms UTC, <=5-ms RSS, <=50-ms RSS-start and
all other budgets/labels; subtract nothing. Wide intervals remain in the population.
Invalid linkage or clocks leaves dependent counts unresolved. A disconnect or
fatal fault censors from the last safely linked boundary; no zero filling or finite
upper bound for missing feed activity. One uninterrupted connection still cannot
establish venue completeness. Synthetic results demonstrate the method only on
those recordings, not real-market performance.

One connection, zero reconnects; readiness before M0−1 s; max 90 seconds and
60,000 returned texts; normal five-second tail. Connection/subscription is bounded
by 10 seconds and readiness, close by five seconds. Retain verified TLS/CA context,
websockets 15.0.1, compression disabled, automatic protocol ping disabled,
262,144-byte incoming size and max_queue 16, with text PING every ten seconds.
Queue threshold is not a memory cap. Runtime syscall/TLS retry behavior is retained
in the runtime review; internal retry counts and kernel retransmissions remain
unobserved. No application retry, auth/proxy fallback or alternate endpoint.

Keep CPU 75%, memory 512 MiB, 32 tasks, 240-second unit ceiling; level-1 gzip,
8-MiB raw segments, 1-GiB raw, 256-MiB compressed, 32-MiB completion sideband,
64-MiB auxiliary and 1-GiB spool bounds; initially 2 GiB free and 1-GiB reserve.
Retain persistence cadence/reserve without claiming a guaranteed completion margin.
Stop on the original fatal conditions, caps or first detected scheduled end;
retain partial raw/witness/control evidence. Required clock/linkage/identity/source
or unit-limit failures stop; ordinary bracket-width exceedances remain component
failures/unknowns rather than being hidden or automatically converted to zero counts.
No observer optimization, measurement-semantic change or new diagnostic framework.

## Preparation, approval and one-run execution

Read-only pinned SSH on October 18 at 15:55:56Z verified the existing source,
installed runtime/TLS/CA and public baseline, unchanged boot, 6,209,163,264 free
bytes, unused new namespace and absent new unit. TLS context construction used
verified CA bytes without a metadata/feed request. No stage, controller, unit,
scheduler or subscription was created. Host is ARM64 Linux/Python 3.9.25.
The runtime embeds historical host/credit context: its byte verification does not
refresh that context. Fresh credit mode/balance remain unavailable after the
October 18 SSO refresh failure; no balance or minimum is inferred or added as a gate.

The sealed packet section below binds exact source/runtime/TLS/public/stop-policy
bytes. Before execution approval, only a **proposed** operator receipt is retained;
the active `operator-approval.json` is absent. Approval would authorize installing
those exact receipt bytes plus a separate confirmation recording the user's actual
approval, staging once, one controller invocation in its window and one bounded
unit if all gates pass. It would not authorize any alternate target or extra run.

Refresh source/runtime/TLS/public/disk/namespace gates before that invocation and
check prospective metadata/case lock and independent live-unit release. Use exact
installed interpreter/source, DEVNULL stdin, retained log, `start_new_session=True`
and original HUP/TERM dispositions; no nohup. Controller and launch claims are
exclusive. Later documentation HEAD must not substitute for the frozen source.
No long-lived scheduler or monitoring task has been installed for this proposal.

Afterward stop and independently copy/hash/seal the complete retained population;
verify archive/completion/runtime/domain/case linkage, all 60 count rows,
ambiguity/unplaced/pre-window/tail/censoring, gaps/missed slots and nominal clock
assumptions. Report inclusive CPU/RSS and precision labels separately. Incremental
observer overhead, continuous RSS peak, independent UTC accuracy and venue
completeness remain unknown absent independent evidence. No combined badge.

## Offline checks before source freeze

All 1,240 individual tests passed on Intel macOS/Python 3.14.6 across two
invocations. Initial default discovery completed 1,228 tests but reported one
loader error: `test_stream_cross_site` imports `test_stream_freshness` by its
unqualified name. With `PYTHONPATH=.:tests`, the omitted 12 tests passed in
0.131 seconds. The initial error/log is retained; this is not a claim of a single
clean full-suite invocation. Correct-path discovery independently enumerated
1,240 tests with no loader errors. The 39 focused public/stop tests passed in
6.870 seconds. Changed Python accepts Python 3.9 syntax locally. These are offline
checks, not new Linux execution. No implementation change was made for the loader.

## Sealed approval packet — not deployed

Exact execution source: `706ebed052945235dd44e7a5c5ef6a231059576c`, **552 selected
files**. Full freeze SHA-256:
`59c54d22966b2da993e5437aa8a7c7c39baf9002b7e0f475533eed892da8efea`.
Seven-member transport: **109,850 bytes**, SHA-256
`4526f4ef04481d05f6bdff2bc5154b8848dc072e23bcc969057ed290bee0142e`.
Private packet: `.qcrl/reviews/public-feed-20261019T160000Z/stage-packet.tar.gz`.
The bundle requires retained ancestor `de4c10bf3f53bb4fd4ab3646c22a7d5e3fc1536c`.
All member hashes and all exact committed source files were independently checked;
bundle verification passed. Later documentation commits do not replace this source.

The packet contains source bundle, execution freeze, proposed operator receipt,
installed runtime review and reviewed select source, historical host context and
fresh read-only readiness. Runtime verification retains historical host context
as such; fresh readiness does not claim refreshed credit measurements. The active
approval filename is absent. Receipt-template flags deliberately say that those
bytes alone grant no execution authority. Explicit approval of this freeze is
required before activation, staging and launch; no future human approval is claimed.

After approval and successful staging/readiness, the exact controller argv is:

```text
/opt/qcrl-stream/venv/bin/python -m infra.stream.recorder_public_operator controller --root /var/lib/qcrl-stream/public-feed-20261019T160000Z --freeze-sha256 59c54d22966b2da993e5437aa8a7c7c39baf9002b7e0f475533eed892da8efea --execute
```

Invoke once as root from the exact staged `source/`, only inside the declared
controller window, with the normal `Popen`/session/log settings above. Do not run
`metadata` separately or submit a unit manually: the controller owns those single
opportunities and verifies independent release. No direct discovery or feed
operation is part of packet preparation. Exact-packet approval would cover staging,
one conditional attempt and its independent audit/commit/push; a failed gate stops
without rollover. Public collectors, historical evidence and resource settings stay
unchanged. No separate smoke, cohort or other target is included.
