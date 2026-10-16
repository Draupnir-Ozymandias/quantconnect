# Fixed public-feed interval-count execution contract v1

**The historical application-budget verdict remains FAIL. There is no new
combined acceptance badge.** This prospective implementation follows the
[unchanged study draft](PUBLIC_FEED_INTERVAL_COUNT_STUDY_DRAFT_V1.md). Synthetic
results demonstrate interval arithmetic on those recordings; they establish
neither venue completeness nor real-market performance. This study describes
locally returned public text occurrences. It makes no trading, execution,
venue-event-rate or latency claim.

The user's subsequent “commit and push … then proceed with the proposed target”
authorizes preparation and this one conditional target, not another smoke,
cohort, substituted market or repeated attempt. The private authorization receipt
records that instruction; its hash is integrity linkage, not a signature or a
claim that the user manually inspected future market IDs or a source hash.

## Fixed recipe and gates

Policy identity: `qcrl.public_feed_interval_counts.study.v1`; declared policy SHA:
`90fe9a6a7fc6fd0ba78b1a1d6218188cfd7399dd06cbd5bae02de870e2f56d32`.
Regression tests pin that literal. Case:
`btc5m-20261017T160000Z-local-counts-01`.

The BTC five-minute Up/Down market must have exact October 17, 2026,
16:00–16:05 UTC terms and both CTF outcome tokens. Market existence and IDs remain
unknown until the one declared metadata opportunity. Existing public acquisition,
normalization, resolution-source, description and market-window checks apply;
the expected slug is a locator, not proof of the terms. Incompatible live
metadata means not run; do not adapt the rules after seeing it.

One controller may start only October 17, 15:45–15:55 UTC. At 15:55 UTC it makes
one metadata acquisition attempt, at most five bounded HTTPS GETs in 30 seconds
total: slug resolution, Gamma market, CLOB market and two books. Each response
is capped at 2 MiB; redirects, proxies, account paths and repeated acquisitions
are refused. A parent process deadline also bounds blocked DNS/HTTP. Preserve
request receipts and partial bodies on failure. Lock exact IDs, case bytes and
freeze before 15:59 UTC. Missed gates mean not run, with no rollover.

Arm one private recorder unit at 16:00:40 UTC. Establish the unchanged
monotonic/UTC/monotonic anchor before feed acquisition, compute the future
16:01 UTC reference from the after endpoint using exact represented inputs,
and round upward once to integer nanoseconds. Never reanchor. Require independent
PID/start/boot/cgroup/unit-property release and subscription readiness before
M0 minus one second. Count 60 half-open local monotonic one-second bins. Stop
acquisition at M0+65 seconds or 90 seconds from the connection attempt, whichever
comes first, or at the first declared fault/cap. No reconnect, replay, tuning,
substitution, extra capture or automatic recovery.

Fresh source, installed interpreter/modules/binaries, TLS/CA bytes, boot,
public-collector state/source/environment and disk checks must match the freeze.
The private source checkout and control files are separate from public services
and historical stages. The worker gets only its private evidence directory
writable. One unit retains CPU 75%, memory 512 MiB, 32 tasks and 240 seconds.
The new public unit permits Internet sockets but denies metadata addresses;
old isolated units and public collectors are unchanged. No credentials or
environment files are imported. Cancellation is the private stage's `cancel`
file; retain evidence and stop only this bound unit.

## Transport and timing placement

The separate public adapter uses verified TLS, the byte-pinned installed system
CA bundle and `websockets==15.0.1` synchronous connect. One application connection
attempt: open at most 10 seconds, close at most 5 seconds, max text 262,144 bytes,
queue high-water mark 16, no compression, library ping or proxy. Queue 16 is flow
control, not a hard memory bound. Send the exact frozen market subscription,
then application PING every ten seconds with the existing 30-second PONG guard.
Internal DNS/socket/TLS/kernel retry behavior is not fully observed; zero
application retries does not imply zero internal retries.

The original application-return monotonic/UTC/monotonic operation remains
immediately after a supported receive, before classification and archive work.
No UTC or resource bracket is subtracted, widened, corrected or requalified.
The ordinary absolute resource observer is used without RSS thread-CPU
instrumentation. The current quota-validation reuse has only local offline
validation; this does not repair historical wide RSS or UTC brackets.

Control timing calls, deadline timers, storage checks and classification occur
outside the original brackets. A connection timer terminates only this worker
with default SIGTERM if DNS/connect stalls; already-synced prefixes survive but
final receipts may be absent. After connection, a socket timer interrupts the
underlying descriptor to unblock a stalled TLS write without concurrently
mutating its SSL object. These are limit enforcement, not a new measurement
layer or real-time guarantee. Scheduling latency and their inclusive overhead
remain uncalibrated. Local subprocess/socket and verified-TLS fault checks do
not establish Linux production compatibility.

Receive waits also honor the existing prospective persistence reserve before
the two-second end-to-end target. That margin is not a guarantee. Faults survive
the stop race; an already-closing connection at scheduled stop is unresolved,
and `ConnectionClosedOK` is not evidence of successful completion. Record
acquisition end before local close, so close time cannot repair early acquisition.

## Storage, linkage and report

Retain the draft's 60,000 total returned-text cap, gzip level 1 segmented archive,
8-MiB raw segments, 1-GiB logical raw / 256-MiB compressed limits and existing
terminal reserve. Sideband publication remains capped at 32 MiB encoded;
that is not a heap bound. Reserve 64 MiB for auxiliary evidence, a maximum
1-GiB spool including partials, and at least 1 GiB free disk after the initial
2-GiB readiness requirement. Per-append checks reserve the auxiliary allowance
and next segment outside the measurement bracket. No expansion or deletion.

Count each returned supported text once, including PONG, duplicates, batches,
malformed and unknown schemas. Do not expand batches or deduplicate. Explicit
foreign condition/token bindings stop after retaining the offending raw text.
Link the complete ordered archive population to completion receipts and clock
domain before binning. Closed observation intervals yield certain lower and
possible upper archived counts in half-open bins; ambiguous and unplaced
occurrences retain their denominators. Gap/cap/fault suffixes are censored,
never zero-filled. Missing archive or final consumer receipt yields unknown
population/coverage, not a finite feed bound or an empty recording.

UTC labels are nominal: read-only NTP state is context, not an independent
accuracy bound. Preserve original wide-UTC labels alongside intervals. RSS is
sampled/inclusive; incremental observer overhead and continuous RSS peak remain
unknown. Fresh host/runtime/TLS receipts do not refresh historical EC2 credit
context; no credit minimum has been invented or made an acceptance gate.
Archive integrity, observation counts, resource context and unknowns are reported
separately. Origin inventories still require observed independent copy/hash
attestation. No producer-written origin flag proves itself.

The one app follow-up is scheduled for October 17 at 11:45 EDT (15:45 UTC), before
the fixed metadata opportunity. It requires the app/access to be available;
it is not a promise of unattended execution. No controller or native unit
starts during October 16 preparation. The exact source/runtime freeze and
staging receipt are recorded prospectively in HANDOFF and private controls.
