# Fixed public-feed target v3 — October 17, 18:30 UTC

**Historical application-budget verdict remains FAIL. Both earlier targets remain
not_run. No combined acceptance badge, trading/execution claim or venue-completeness
claim is defined.** This new prospective declaration follows the user's explicit
instruction, “please proceed with setup and deployment of a new capture.” It
authorizes preparation, deployment and one conditional attempt, with no rollover.
It does not relabel, resume or modify either earlier packet or its evidence.

| Item | Fixed declaration |
| --- | --- |
| Identity | `qcrl.public_feed_interval_counts.study.v3` |
| Policy SHA-256 | `6cdc0386787c0a6bd68ac0061e59c6f50b657dfac19f2ec27bd056f336488533` |
| Parent policy SHA-256 | `220e1b592365b33dd5e0e4c46ab53103735f4add634694aba4cb745a7fa0adff` |
| Case | `btc5m-20261017T183000Z-local-counts-03` |
| Product | Public Polymarket BTC five-minute Up/Down, one condition, both supported CTF tokens |
| Event terms | October 17, 2026, 18:30–18:35 UTC / 2:30–2:35 PM EDT |
| Controller start | Once, 18:15–18:25 UTC / 2:15–2:25 PM EDT |
| Metadata | One opportunity at 18:25 UTC, at most five GETs and 30 seconds total |
| Identity lock | Before 18:29 UTC |
| Private unit arm | 18:30:40 UTC |
| Nominal counting minute | 18:31–18:32 UTC / 2:31–2:32 PM EDT |
| Stage | `/var/lib/qcrl-stream/public-feed-20261017T183000Z` |
| Unit | `qcrl-public-counts-20261017T183000Z` |

Market existence and IDs remain unknown until the single metadata opportunity.
Require explicit matching 300-second terms, resolution source, description and
both token bindings. No inferred IDs, alternate market, repeat discovery, replay,
reconnect, extra run or automatic rescheduling. A missed or failed gate means
not run or retained partial evidence, as appropriate, then stop.

The [v1 execution contract](PUBLIC_FEED_COUNTS_EXECUTION_V1.md), unchanged
[study draft](PUBLIC_FEED_INTERVAL_COUNT_STUDY_DRAFT_V1.md) and v2 verified-CA
repair remain authoritative apart from this new identity/window/namespace. Both
prior policy dictionaries remain intact with literal regression hashes. No
observer, counting, transport, measurement or resource-limit change is included.

Use one after-endpoint anchor and one fixed monotonic epoch, exactly 60 half-open
one-second bins, closed occurrence observation intervals and exact represented
arithmetic. Preserve ambiguous, unplaced and outside-window occurrences. Invalid
or absent linkage leaves population/coverage unknown; gaps and fault suffixes
are censored, never zero-filled. UTC labels are nominal, without an independent
accuracy bound; original 1-ms UTC, 5-ms RSS and all other thresholds remain intact.

One connection only, five-second tail, at most 90 seconds acquisition and 60,000
returned text occurrences. Every supported returned text counts once, including
duplicates, batches, PONGs, malformed and unknown schemas. No batch expansion or
deduplication. Foreign explicit bindings stop after retaining the offending text.
Internal transport retry behavior remains incompletely observed.

Retain CPU 75%, memory 512 MiB, 32 tasks and 240-second unit ceiling; gzip level 1,
8-MiB raw segments, 1-GiB logical raw, 256-MiB compressed, 32-MiB sideband,
64-MiB auxiliary, 1-GiB spool, initial 2-GiB free disk and remaining 1-GiB reserve.
Existing persistence margin is prospective, not a guarantee. No public collector,
host resource, IAM, networking or historical-stage changes. No credential import.

Before one controller start, freeze the exact clean source commit, selected
files, installed runtime/modules/binaries, TLS/CA bytes, boot, public source/
environment/state and authorization receipt. Construct the actual verified TLS
context and refresh disk/namespace gates without metadata or feed requests.
The root controller claim and launch receipt are exclusive; use the installed
interpreter, normal signal dispositions, DEVNULL stdin, retained log and
`start_new_session=True`. No `nohup`. Later documentation HEAD cannot substitute
for the sealed execution source.

Deployment may start one finite, exclusive launch scheduler before the controller
window. It waits only until 18:15 UTC, checks cancellation and a bounded monotonic
deadline, then performs fresh gates and makes at most one controller invocation
inside 18:15–18:25 UTC. It requests no market/feed data, creates no extra unit and
exits after recording the launch or failure. Its exact bytes and hash are retained
prospectively with the packet. Scheduler/controller overhead is not calibrated;
this is control scheduling, not an added measurement or a timing guarantee.

Afterward stop and independently copy/hash/audit retained evidence. Report archive
integrity and complete ordered population linkage, all 60 bin rows, ambiguity,
unplaced/censored coverage, gaps/missed slots, original precision labels, clock
context and resource components separately. Incremental observer overhead,
continuous RSS peak, independent UTC accuracy and venue completeness remain
unknown unless supported independently. Historical credit context remains stale;
no retrospective credit minimum or new acceptance gate is introduced. Synthetic
results establish the method on those recordings only, not real-market performance.

Fresh read-only AWS context at 17:59 UTC reports standard credit mode and latest
CPU credit balance 576 at 17:54 UTC. These receipts describe this preparation;
they neither refresh historical experiment evidence nor establish a minimum
during the future capture. No credit minimum is an acceptance gate.

Exact source, freeze, fresh readiness and deployment receipts will be recorded
in HANDOFF and the new private review directory before execution.

## Sealed and deployed before the fixed window

Exact execution source: `de4c10bf3f53bb4fd4ab3646c22a7d5e3fc1536c`, 547 selected
files. Full freeze:
`b4bb07c78cf5558fea2befe1b7611166678f00344ba6664d942fd6becbe8d7ed`.
Transport: 91,476 bytes, SHA-256
`91db072bcf16bf82c65a00fd72a1ff3f30aaff33ca76cc8d9c81b8e6c282e621`.
The authorization receipt records the user's new-capture instruction and one-case
scope; it does not claim the user inspected a subsequently generated freeze hash.

All 1,228 tests passed locally in 153.665 seconds, with 27 focused tests passing
and changed Python files accepting Python 3.9 syntax. These are Intel macOS checks,
not Linux recorder validation. Staging at 18:00:31Z verified the exact source,
installed runtime/TLS context, public baseline and fresh namespace on Linux.

The exclusive scheduler was deployed at **18:01:25Z / 2:01:25 PM EDT**, PID 1720744.
Scheduler SHA-256:
`6d588b5035df9da3949d042abb22cf449290f96c6aed3f9bf1b26e02f776f25a`.
Independent readback matched the local source-freeze, authorization and scheduler
bytes; the live PID command line matched the installed interpreter and scheduler.
Signal masks showed neither SIGHUP nor SIGTERM ignored. At readback there was no
controller claim, evidence directory or launch-failure receipt and its log was
empty. This is deployment readiness, not a capture result or public-path validation.

The existing app follow-up was moved to October 17 at **2:34 PM EDT** to inspect
and independently audit this already-deployed attempt. It cannot restart the
scheduler/controller or create another run. Local private controls and readbacks:
`.qcrl/reviews/public-feed-20261017T183000Z/`. Subsequent documentation commits do
not replace the exact execution source above. All declared timing/readiness gates
still apply at the future controller and metadata opportunities.
