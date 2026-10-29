# Milestone 3 draft — BTC20-Uneven01

Declared October 28, 2026, before any new acquisition. Design identity:
`qcrl.btc20_uneven01.design_draft.v1`. **Draft for a capture decision, not an
executable approval packet. No target date, market IDs, execution freeze,
staging, scheduler, metadata request or capture is active.**

Engineering baseline: milestone 2 commit
`b108670dc79df2a9b1e3e4cfbedaf431f7cc76e8`,
[current capabilities and limitations](ENGINEERING_BASELINE_20261028.md).
Runtime implementation base is `c8d80810e92b9436fc5b3df8983286bcabcaf2c1`;
the new duration/phase-quota wiring below is **not implemented or validated**.
No earlier v5/v6 plan or evidence is to be edited or upgraded.

## Named research question and decision value

**BTC20-Uneven01: During one fixed 20-second window in one BTC five-minute
market, how uneven are locally archived incoming-text counts across wholly
book-eligible one-second bins, and how many planned bins remain boundary,
unavailable or ambiguous?**

This prospectively defines the descriptive question previously explored
retrospectively on v6. It tests no price, profitability, trading/execution,
venue-completeness or maintained-book hypothesis. It makes no causal comparison
to v6 or claim that reconnecting recovers missed messages. One recording can
answer this question conditionally on its linked observed intervals, even when
other components fail; it cannot establish a general venue rate or reliability.

Primary outputs are exactly **20 ordered bin rows**, with separate raw and
strict fresh-book-eligible lower/upper counts, original coverage/precision labels,
whole-bin availability, ambiguity, unplaced and silence state. Report whole-bin
count n out of 20 and separate prewindow/tail/boundary populations. Incoming
texts are the counting unit: retain duplicates, batches, PONG/unknown texts and
accepted creation notices once; no batch expansion, dedup or favorable filtering.

For n >= 2 wholly eligible bins, report raw and eligible totals, mean, population
SD/CV, nearest-rank p10/p50/p90, range, Gini, largest-one and largest-ceil(n/4)
shares, with denominator and actual k explicit. Rank ties by earlier slot.
No p-values, confidence intervals, predictive rate or significance claim. If
ambiguous/unplaced intervals prevent exact counts, retain bounds and leave
point-valued distribution/concentration unresolved rather than pick midpoints.
If n < 2, retain the rows/populations and mark the unevenness question
inconclusive; no automatic replacement. Missing acquisition is never zero-filled.

## Fixed relative schedule, to be bound to one future opportunity

Keep one public Polymarket BTC five-minute Up/Down condition and both supported
CTF tokens. A later packet must name one event start E, 300-second terms, one
metadata opportunity and one unused case/namespace **before capture approval**.
No live discovery or rate probing is part of preparing this draft.

| Phase | Fixed nominal interval | Purpose |
| --- | --- | --- |
| Prewindow | E+55 to E+60; M0−5 to M0 | Connection, subscription and fresh-book bootstrap |
| Primary | E+60 to E+80; M0 to M0+20 | Twenty one-second bins, k=0..19 |
| Tail | E+80 to E+82; M0+20 to M0+22 | Retain terminal/boundary observations |
| Acquisition stop | M0+22, unless an earlier quota/fault/deadline stops it | No extension to replace gaps or missed bins |

Nominal acquisition exposure is **27 seconds**, versus v6's planned 20-second
prewindow + 60-second primary + five-second tail. The existing one-time
monotonic/UTC/monotonic anchor and exact represented interval arithmetic remain;
M0 is fixed before receiving, never moved to fit readiness or traffic.
Require independent worker release/subscription readiness before M0−1 and fresh
books under the existing bootstrap rules. If readiness is missed, retain the
failed/partial attempt; no late start, new epoch or adopted market. Five seconds
is a chosen preparation allowance, not a connection/bootstrap guarantee.

## Prospective frame and byte envelope

V6 retained 19,680 prewindow texts and reached its shared 60,000 cap at +53.085595
seconds. Reusing its envelope could repeat that truncation. This design both
shortens planned exposure and **partitions** existing capacity; it does not
increase memory, CPU, tasks, global frame capacity or unit runtime.

| Phase | Incoming-text ceiling | Encoded uncompressed archive stop threshold |
| --- | ---: | ---: |
| Prewindow | 8,000 | 32 MiB |
| Primary | 50,000 | 128 MiB |
| Tail | 2,000 | 8 MiB |
| Termination/control reserve after acquisition | No new incoming texts | Hard 32 MiB allowance |

Frame ceilings sum to the original **60,000**. Counters are cumulative across all
connection attempts; no reset on reconnect. Unused phase allowances are not
borrowed. Prewindow cannot consume the primary's 50,000-text / 128-MiB allowance.
If a phase exhausts its allowance, stop the entire acquisition, preserve the
prefix and label the quota reason/censoring. **Do not pause/drop prewindow traffic
and resume at M0**, reset counters, roll over, or add another run. These quotas
protect allocation, not availability: they may themselves cause an early stop.

Assign a text to its budget phase using the already recorded return-before
endpoint relative to M0. A cross-phase interval consumes the earlier phase's
budget without splitting its occurrence; analysis still uses its full original
interval and may mark multiple candidate bins. Controls during acquisition use
their existing append timestamp. No added clock/read/lock is placed inside a
return or RSS bracket. Phase tests must cover callbacks spanning M0/M0+20.

Byte thresholds count **encoded uncompressed archive records**, including phase
controls, using the existing writer's byte count, not payload-length estimates
or a compression ratio. Check after each completed append; at most one existing
4-MiB maximum record may cross each of the three phase thresholds, then stop
before another receive. Reserve remains for terminal/error records and sealing;
an oversized/failed/unlinked write remains a fault, not an excluded observation.

Accounting bound: 32 + 128 + 8 + (3 × 4) + 32 = **212 MiB uncompressed**,
including the termination allowance. This is below the unchanged 1-GiB global
raw ceiling. Termination allowance must be enforced even for `session_end`,
which has a special reserve exception in the legacy writer; no unlimited summary
exemption. Any failure retains partial evidence rather than promising a seal.

Retain the independent **256-MiB compressed cap**, 8-MiB segment target/gzip1,
**32-MiB completion**, **64-MiB auxiliary** (including the at-most-4-MiB resource
component), **1-GiB private evidence spool**, 1,024-file bound, initial **2-GiB
free disk** and **1-GiB disk reserve**. Compressed bytes are bounded separately;
do not assume they equal or shrink uncompressed bytes. Archive + completion +
auxiliary allowances total 352 MiB, with the existing 8-MiB next-write reserve
still leaving substantial nominal space under the 1-GiB spool cap. Actual disk/
file/quota guards remain authoritative and can stop earlier. No eviction,
overwrite, extra in-unit evidence copy or storage expansion.

Keep incoming cap **262,144 bytes**, library queue **16**, disabled compression/
automatic protocol ping and existing heartbeat/data watchdogs. These settings
and logical ceilings do not prove a 512-MiB resident-memory bound under Python
allocation, compression and completion serialization; the hard unit limit and
offline worst-case boundary/fault checks remain necessary.

The figures above are chosen finite budgets for a narrower question, **not a
v6-rate extrapolation or guarantee of 20 complete bins**. No observed-rate
multiplier, retrospective minimum or adaptive increase applies. Higher volume,
large texts, bootstrap delay, reconnects, storage faults or scheduling can still
truncate the planned window. Keep every resulting unknown.

## Runtime, recovery and publication

Preserve CPU75%, Memory512MiB, Tasks32, Runtime240s and the original **90-second
acquisition/publication process guard**. Stop acquisition at the earlier of the
new nominal M0+22 deadline, phase/global/storage limits, existing hard deadline
or fatal fault. At a nominal M0−5 first attempt the hard guard leaves about
**63 seconds** after planned acquisition for seal/checkpoint/pre-close work;
this is explicit prospective scheduling headroom, not a persistence-time promise.
Do not renew the guard on reconnect or add time after a quota/fault.

Reuse at most three sequential connection attempts/two equal-jitter retries,
each clipped to the one acquisition deadline; close the old socket first.
Resubscribe fully and require new nominally fresh books for both assets in
each epoch. Preserve faults and explicit acquisition/book-eligibility gaps.
No induced disconnect, manual retry, replay, replacement or extra case. If no
reconnect occurs, that component is inconclusive; this question does not require
a reconnect. Internal runtime/library retry counts remain unknown.

Opt into the existing pre-close resource publication policy in a **new** freeze:
seal archive/completion/checkpoint, stop/join the existing observer <=3 seconds,
publish only a finished returned result or explicit unavailable component, then
perform final close. Preserve the five-second library and external close bounds;
the equal-bound cleanup issue remains unresolved. Final consumer only after
close. Checkpoint/component alone is not verified final close or scheduled
completion; preserve guard and receive faults through cancellation races.

Original UTC/RSS/RSS-start/CPU/append/durability thresholds and sample definitions
stand; subtract nothing and add no observer layer. Retain the existing observer
grid, request stop via existing publication ownership, and report any prefix/
missing rows/missed slots truthfully. **A 20-second study cannot qualify the
original 60-second primary CPU window**; that qualification remains unavailable,
not relaxed. This is a component-evidence descriptive study, not an application
resource-acceptance experiment. If the capture decision instead requires that
original full-window acceptance, this draft is not suitable.

## Offline integration gates before a capture decision

The current source accepts only fixed v5/v6 plans, still has hardcoded 60-bin /
M0+65 count/stop paths and plan-global storage references, and has no phase
quota policy. Editing a duration field alone is unsafe. Required work is narrow
integration of this named plan through the actual operator/spec/collector/
checkpoint/report paths, while byte-pinning old v5/v6 behavior.

1. Implement new duration, phase counters/byte stops and terminal reserve with
   explicit policy/source identities. Test one-before/exact/one-after boundaries,
   cross-phase intervals, controls, oversized rows, combined caps and no reset/
   borrow across retries. Preserve already received/linkable texts and all faults.
2. Test actual production paths for 20 ordered rows, epoch binding, unchanged
   clocks/brackets, ambiguity/unplaced, gaps/fresh books and cap-censored counts.
   Test memory-heavy maximum populations in bounded child processes under the
   declared envelope, not one cumulatively retaining readiness process. No
   sampled/inclusive result can certify incremental overhead or continuous peak.
3. Wire opt-in pre-close publication and the corrected read-only inspector into
   the successor packet/auditor; independently bind InvocationID, boot, complete
   argv and PID/start/cgroup. A separately owned cleanup action must revalidate
   its exact invocation; the inspector itself grants no stop authority. Missing
   counters stay unknown and failed exits remain faults. No inspector-only
   native smoke is automatically required or scheduled.
4. Freeze a committed source inventory, transport, report/auditor and direct
   approval bindings for **one future dated opportunity**. Obtain fresh read-only
   installed-runtime/TLS/CA/host/disk/public/unused-namespace evidence then, not
   by relabeling historical checks. Credit context is reported if available;
   no invented minimum. Local tests remain distinct from Linux validation.
5. Present one executable approval packet with exact case/window/source/freeze,
   one-shot claims/default signals, live binding, retained partial evidence,
   independent inventory/copy/hash and all 20 raw/eligible rows. Approve or decline
   that one bounded capture separately. Missed access/readiness/window means
   not-run, never rollover. No public capture is needed just to finish this draft.

**Current decision: not ready to capture.** Milestone 2 is consolidated; milestone
3 now has a named question and finite prospective envelope. Offline integration
and packet gates remain. Historical FAIL, v6/PreClosePub01 partial verdicts,
every original threshold/evidence item and all unknowns remain unchanged. No
combined acceptance, staging, metadata request, scheduler or native run follows
from this document.

## Subsequent offline implementation — October 28

The user subsequently authorized offline implementation/testing and preparation
of a frozen approval packet, explicitly withholding capture. The original design
above is preserved. [Implementation and allocation semantics](BTC20_UNEVEN01_IMPLEMENTATION_V1.md)
record explicit v7 selection, 20-bin runtime/report paths, partitioned quota
enforcement, trigger-text retention/unarchived disclosure, inspector-v2 cleanup
wiring and mandatory unavailability of the original 60-second CPU-window result.
The candidate approval target is October30,16:00 UTC; no staging or capture follows
without separate exact-packet approval. This update grants no new execution right.
