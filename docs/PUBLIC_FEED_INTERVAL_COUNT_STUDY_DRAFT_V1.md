# Public-feed interval counts — prospective study draft v1

**Draft only: no discovery, subscription, capture, native run or rollout approved.**
Identity: `qcrl.public_feed_interval_counts.study_draft.v1`.
Proposed case: `btc5m-20261017T160000Z-local-counts-01`.
Declared October 16, 2026, before any evidence from this proposed window.
The market's existence/availability and outcome IDs have **not** been verified.
This is not an executable approval packet or adoption of the
[component-evidence draft](RECORDER_COMPONENT_EVIDENCE_DRAFT_V1.md).

**Historical application-budget verdict remains FAIL.** Synthetic Cohort02 and
RssCpu01 findings, thresholds, failures and unknowns remain unchanged. The
[synthetic interval-count report](RECORDER_COMPONENT_REPORT_20261016.md) demonstrates
the method on those recordings; it establishes neither venue completeness nor
real-market performance. No new combined acceptance badge will be produced.

## One question, market and fixed window

**What are the lower/upper counts of locally observed public-channel text
occurrences in each of 60 consecutive one-second bins for one preselected BTC
five-minute market, and how much boundary/coverage ambiguity remains?**

| Item | Fixed prospective choice |
| --- | --- |
| Venue/product | Polymarket BTC five-minute Up/Down market, both supported CTF outcome tokens, one condition |
| Target event terms | Start `2026-10-17T16:00:00Z`, end `2026-10-17T16:05:00Z` (October 17, noon–12:05 p.m. America/New_York, EDT) |
| Nominal counting window | `16:01:00Z`–`16:02:00Z` on the collecting host's UTC clock; actual analysis is the fixed local monotonic window below |
| Observation population | Every supported text occurrence returned on the one subscribed connection; duplicates, batches, PONGs, malformed and unknown text each remain occurrences |
| Primary output | Exactly 60 ordered rows of count bounds and coverage state, total occurrence/ambiguity/unplaced counts, plus explicit pre-window and tail counts |
| Replication | One attempted case only; no replacement market, second window, extension, backfill or run-until-success |

The counting unit is a returned text message, not an individual update inside a
batch, trade, quote change, unique payload or venue event. No deduplication,
batch expansion, price/return analysis, threshold-defined burst finding or
post-hoc event-type selection. Retain ordinary source classification separately;
do not make it a reason to drop raw text. A zero denotes zero linked recorded
occurrences only where local recorder coverage supports that statement.

## Deterministic discovery and pre-capture lock

Propose one bounded public metadata acquisition at `2026-10-17T15:55:00Z`, maximum
30 seconds, using the repository's public event/market resolution and normalization
rules. This step is not authorized by the draft. Require exactly one matching
BTC Up/Down condition with explicit 300-s terms above and exactly two supported
outcome-token bindings. Match authoritative event terms, not merely a title,
date-like slug or generic market creation time. Retain raw responses, request
times, normalized terms, market/condition IDs, outcome labels/token IDs and hashes.
Ambiguous, absent, contradictory or unsupported-protocol results mean **not run**.
No alternate target, repeated discovery or inferred IDs.

Before `15:59:00Z`, the later approval packet must bind these exact identities,
metadata/source/runtime/dependency hashes, host/boot/clock domain, public transport
and subscription bytes, limits, output directory and this study identity. Pin
the same target even if subsequent activity looks uninteresting. No approval or
readiness by the cutoff means **not run**, with the missed proposal retained.
Rescheduling would require a new declaration before its new window.

## Local clock model and interval counting

Arm the private study worker nominally at `16:00:40Z`. Before receiving any feed
data, take one retained monotonic/UTC/monotonic anchor `(m_before, u, m_after)`.
Set the nominal-reference epoch deterministically to
`M0 = m_after + (16:01:00Z - u)` using the recorded clock representations.
Compute from exact represented inputs, ceiling once to integer monotonic
nanoseconds; retain the operands and rounding. Bin edges are then M0 plus exact
integer multiples of one billion nanoseconds. Compare recorded callback endpoints
as exact represented fractions in that domain, without rounding them inward.
Freeze M0 once; do not reanchor it from later traffic, wake time or UTC readings.
This explicit choice of the anchor's after endpoint is a schedule definition,
not a best estimate, correction or guarantee of true UTC correspondence.

Require a finite ordered anchor, same native monotonic/boot domain throughout,
and subscription readiness before `M0 - 1 s`. If the anchor puts M0 in the past
or readiness misses that deadline, do not adopt a later epoch or begin late.
Retain the failure and stop. The primary window is **`[M0, M0+60)`**, with bins
`[M0+k, M0+k+1)` for k=0..59. UTC labels/market-phase alignment are nominal: host
offset, rate error and undetected clock steps have no independent bound here.
Report available clock synchronization state and observed UTC anomalies; do not
convert a narrow bracket or reported clock resolution into accuracy evidence.
No true-UTC, cross-host, source-age or venue-arrival comparison is in scope.

For each linked occurrence use the unchanged completion callback's closed
monotonic interval `[returned.before, returned.after]`. The event being counted
is the local timestamp-acquisition operation after library return. Its unmeasured
pre-stamp handoff and library/kernel/network/source-event timing remain outside
the claim. Do not replace the interval by the archive row time or a midpoint.

For each bin report L = number of intervals wholly contained in it and U = number
intersecting it, using exact representations of retained numeric clock values.
An interval ending exactly at an edge can belong to the following bin. Keep
straddling occurrences once in the raw denominator and list all possible bins,
including pre-window/tail bins. U across bins can exceed the total population.
An interval spanning multiple seconds remains possible in every intersected bin;
do not assume the synthetic report's less-than-one-second width restriction.

Retain the original <=1-ms UTC qualification/failure label independently; a wide
interval can still establish a coarse within-bin property. No row is deleted to
improve count coverage or performance statistics. Invalid/missing clock/linkage
means an unplaced occurrence: report its count and conservative possible-bin
set where its evidence permits one. If unconstrained, all 60 bins remain possible
for that archived occurrence. Distinguish finite bounds over known archived
occurrences from unknown missing observation coverage; the latter has no inferred
finite upper count for feed activity. Mark dependent bins unresolved.

## Public transport, connections and gaps

Use only the public market channel, with the two locked outcome IDs and
`custom_feature_enabled=true`; no account/user channel, credentials or orders.
The [official market-stream documentation](https://docs.polymarket.com/market-data/realtime-data)
specifies `wss://ws-subscriptions-clob.polymarket.com/ws/market`, a `market`
subscription using `assets_ids`, and text PING every 10 s with PONG replies.
These details were checked October 16; freeze the exact public-client settings
and dependency bytes before execution. Proposed existing client settings:
websockets 15.0.1 synchronous transport, compression disabled, protocol-level
automatic ping disabled, max incoming size 262,144 and max_queue 16. The queue
setting is a flow threshold, not a hard retained-message or memory cap.
Outgoing subscription/PING traffic is
retained separately and excluded from incoming occurrence counts. Incoming PONGs
are included, as declared. TLS verification remains enabled; no proxy/auth fallback.

Exactly **one connection attempt; zero reconnects**. Connection establishment
must be bounded by 10 s and the readiness deadline; close by 5 s and remaining
unit time. No application-level connection retry, resubscription, replay or
reconnection backoff. Disclose installed socket/TLS/Python syscall retry behavior
in the runtime freeze; this is not a claim of zero kernel retransmissions or
invisible runtime retries. Unknown internal counts remain unknown.
Any disconnect, unexpected close (including normal-protocol close before the
declared stop), socket error, unsupported binary/oversized input, wrong-token /
condition contamination or required-witness fault ends acquisition. Preserve all
prefix evidence and the reason. Normal local close is expected only after the
declared acquisition stop; closure alone never establishes recording integrity.
Unknown or malformed schemas remain raw occurrences; classify contamination only
from an explicit contradictory binding, not from absent/unrecognized fields.

Record every gap explicitly. Conservatively mark the affected bin and remaining
planned window censored/unresolved starting at the last safely linked observation
boundary; do not infer the exact start of network loss from disconnect detection.
No carrying book state across gaps or treating a resumed stream as continuous.
With zero reconnects there is no stitched primary series. Prefix counts can be
reported with their censoring masks; unobserved bins are unknown, not zero.
Even an uninterrupted socket does not establish that all venue events arrived.
Retain initial-book status for both tokens as context, without claiming a trusted
book or requiring book validity to classify raw-text counts.

## Bounded retention, resource envelope and stopping rule

| Limit | Prospective setting |
| --- | --- |
| Acquisition duration | Stop at `M0+65 s` (five-second retained tail), or 90 s from the first connection attempt, whichever comes first; primary bins never move/extend |
| Occurrences / witness capacity | Stop at 60,000 supported text frames across pre-window, primary and tail; completion/barrier capacity remains 65,536 each |
| Incoming message / encoded row | 262,144 incoming bytes; 4 MiB encoded-row cap; binary or unsupported input stops with retained prefix |
| Archive | Existing segmented level-1 gzip, 8-MiB raw segment target, 1-GiB raw / 256-MiB compressed archive caps, 4-MiB footer reserve |
| Sideband / auxiliary storage | Existing 32-MiB encoded completion publication cap, not a heap bound; at most 64 MiB total metadata/control/log/receipt outputs including that sideband; private study spool <=1 GiB including partial files |
| Disk readiness | At least 2 GiB free before start; stop before consuming the separate 1-GiB free-space reserve; no disk expansion or evidence deletion |
| Unit | One private unit on the existing Ohio Linux host: CPU 75%, memory 512 MiB, TasksMax 32, RuntimeMax 240 s; public collectors/resources unchanged |
| Durability | Existing 64-record/one-second requested sync cadence and prospective persistence reserve unchanged; report observed successful watermarks, never a cadence guarantee |

Stop at the **first detected** scheduled end, cap, clock regression/nonfinite monotonic
reading, identity/source drift, required observer fault, disk-reserve breach,
memory OOM/max event, unit exit or
transport/lifecycle failure. Retain partial segments and witnesses; a missing
footer or killed publication remains partial/unknown. Cap/abort bins keep explicit
censoring. Close/flush/publication remain within the 240-s unit ceiling; if they
cannot finish, preserve the available prefix. No extra run, replacement or
post-window catch-up. Stop the private unit afterward and audit once offline.

Required observer faults here mean lost/invalid counting clocks, occurrence
linkage or capacity, not ordinary width exceedances. Wide UTC/RSS brackets keep
their original failure/unknown labels and do not by themselves stop counting.
An auxiliary resource read error stays a component unknown unless it exposes
identity/source drift, a unit/resource-limit event or another fatal condition.
Do not retry a failed read. The existing encoded sideband cap is checked at
publication: over-cap output is refused with raw evidence retained, not silently
truncated or represented as an enforced heap bound during capture.

Inclusive resource measurements and unavailable fields remain component context.
Existing <=5-ms resource, <=50-ms RSS-start and original CPU/RSS/append/durability
budgets keep their meanings; no subtraction, new headroom guarantee or combined
application pass. A quota/disconnect stop is a study truncation, not a successful
full-window recording because its retained prefix verifies.
Use the existing ordinary observer; disable optional auxiliary RSS thread-CPU
diagnostics. No new timing calls, detailed profiling, receive-path tracing,
resource-sampler optimization or paired overhead experiment is part of this study.
Ordinary CPU throttling and numerical component-budget exceedances are retained
context/outcomes, not new automatic stop conditions or event-cause evidence.

## Required report and remaining execution gates

Publish immutable byte inventories and an independent bounded archive/linkage
review, 60 bin rows with `[L,U]` over linked occurrences plus coverage/unplaced
flags, unique ambiguity lists, pre/tail totals, original precision labels, source
and clock assumptions, lifecycle/cap failures and separate component observations.
Every original failed synthetic verdict remains visible. No confidence/generalized
population inference from one selected market, and no selecting a favorable
subwindow or substituting a quiet recording for an interrupted one.

**Not ready to execute:** the current isolated completion/persistence worker is
an injected-offline/loopback path, and the legacy public plan defaults to three
connections and a different lifecycle. This draft does not override either guard.
A separately reviewed minimal public transport/lifecycle integration would have
to enforce this one-attempt window, caps, closure and timestamp linkage while
preserving the observer's measurement semantics. Offline faults/boundaries,
independent report support, exact market IDs, source/runtime/host freeze and
explicit one-case approval are outstanding gates. Do not add another observer
optimization or native timing experiment to satisfy this draft.

No live discovery/metadata fetch, feed capture, SSH/SSM, infrastructure/credential
change, public collector edit, trading, order/execution-safety/latency/profit claim,
QuantConnect sync or native execution is authorized. Only this prospective draft
and its documentation are produced now.
