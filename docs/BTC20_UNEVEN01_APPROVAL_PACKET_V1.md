# BTC20-Uneven01 — frozen conditional approval packet

Prepared October 28, 2026. **Approval pending. No staging, controller, metadata
request, subscription, native unit or automation has started for this target.**
The user authorized offline implementation/testing and packet preparation only.
Historical application **FAIL**, v6 and PreClosePub01 partial verdicts, all
thresholds, sealed evidence and unknowns stand. There is no combined acceptance.

## Question, source and fixed opportunity

**During one fixed 20-second window, how uneven are locally archived incoming
text counts across wholly book-eligible one-second bins, and which planned bins
remain boundary, unavailable or ambiguous?**

This is a descriptive study of one recording, not a venue-completeness,
maintained-book, predictive-rate, trading/execution or performance experiment.

| Item | Exact frozen declaration |
| --- | --- |
| Case | `btc5m-20261030T160000Z-uneven-01` / BTC20-Uneven01 |
| Product | One public Polymarket BTC five-minute Up/Down condition, both CTF tokens |
| Event terms | October30,2026 16:00–16:05 UTC / noon–12:05 PM EDT |
| Execution and report source | `86c69b24a8c911d9c277be62b034d7beb20f11b8`, **578 selected files** |
| Study-plan SHA | `eaaf6bfa25d0b00fd7985506dfb877680342397a0d47b1f31dfcdb68a3d09049` |
| Execution freeze SHA | `49614da6dd74462091b2404ba222a318fc692d8609606a4a9510bf77378ece06` |
| Sealed transport | **180,831 bytes /16 members**, SHA `b28da82f99509d5ea5b1733baf06fe451d36fee68dddd7b0dde96f7c020a5041` |
| Existing host | Ohio `i-039c11d5ea49cf413`, strict pinned SSH `qcrl-ohio` |
| Proposed new stage | `/var/lib/qcrl-stream/public-feed-20261030T160000Z` |
| Proposed private unit | `qcrl-public-counts-20261030T160000Z.service` |
| Installed interpreter | `/opt/qcrl-stream/venv/bin/python`, Linux ARM64/Python3.9.25/websockets15.0.1 |
| Cardinality | One conditional stage and one controller/metadata/unit attempt, no manual retry/replay/rollover |

Local private packet: `.qcrl/reviews/public-feed-20261030T160000Z/`.
Git delta bundle prerequisite is `fc89c11c8c9186c866385b373db12ba04c721e33` from
the existing v6 source checkout. Stage into a **new** private clone; never modify
old source/evidence stages. Later documentation HEAD is not an execution/report
source substitute. All578 committed file hashes and16 transport members verify.

Members bind candidate bundle, freeze, proposed approval receipt, installed
runtime/select/host context, fresh read-only context, one-shot launcher, independent
controller/unit binding, readback, observed inventory, copy, copy verifier and
offline auditor. The local manifest binds every member. The stage generator is
inactive and refuses absent direct confirmation; its mock-generated remote source
was compiled but never executed. No real active approval or execution confirmation
file has been created.

One-shot launcher SHA:
`336bfb391038d7518a32fe06065e683cf77367fdff6d13b3828c433004c9566a`.
Phase policy SHA:
`a19febf2bbf1824f11d3bdb4c464e085b62f89ce8831375ffc922f374e8df033`.
Mandatory pre-close publication policy SHA:
`97182fefdef0ebd4e5007a8aed416fc13e189abb52c6218f3de252fddb4daa73`.
Single-worker inspector-v2 policy SHA:
`43891e7ffabd8ec4b4955bf5cc8ef483fce2b2b68b5678669c10a90836aae99b`.

| Operation | Sole October30 UTC window |
| --- | --- |
| Prepared launcher | 15:44–15:55; pre-controller wait <=90s |
| Controller submission | 15:45–15:55 |
| Metadata | 15:55, at most30s/five public GETs |
| Identity lock | Before15:59 |
| Private arm / prewindow | 16:00:55; M0−5 |
| Primary | 16:01:00–16:01:20; exactly20 nominal one-second bins |
| Tail / acquisition stop | Through16:01:22, unless an earlier limit/fault stops it |

Condition/token IDs remain unknown until that one metadata opportunity. Verify
declared300-second terms, source/description and two token bindings before lock.
Missing/ambiguous market, readiness, access, approval or deadline means not-run;
no substitute, inferred IDs, fresh window or rollover.

## Allocation, bounds and stopping

| Phase | Incoming-text ceiling | Encoded raw-byte stop threshold |
| --- | ---: | ---: |
| Prewindow | 8,000 | 32 MiB |
| Primary | 50,000 | 128 MiB |
| Tail | 2,000 | 8 MiB |
| Terminal reserve | No further incoming frames | Hard32 MiB |

Counters span all connection epochs, without reset or borrowing. The quota-trigger
text is appended where safe before stopping. Byte thresholds allow one existing
maximum4-MiB crossing record per phase: total logical bound **212 MiB** including
terminal allowance. Controls are charged; terminal summary has no unlimited
exception. Hitting any ceiling ends acquisition and censors remaining bins,
without dropping prewindow data and resuming at M0 or adding a replacement run.

Text allocation uses original return-before, including a boundary-straddling
interval; exact edges enter the later phase. Analysis retains the full interval,
ambiguity/unplaced status and separate raw/eligible populations. Bootstrap texts,
accepted metadata, duplicates and batches are charged in full, once per incoming
text. Reconnect requires full resubscription and new fresh books for both tokens;
it does not recover missed messages. At most three sequential attempts/two
declared equal-jitter retries, under one shared deadline and all budgets. Oversize,
binary, certificate, clock, storage, linkage, foreign-binding, emergency and failed
retry-close faults are fatal. No induced disconnect, manual retry, extra capture,
smoke, cohort, resource/infrastructure/public-collector change or credentials.

A returned oversized text is archived where ordinary record/storage bounds allow,
then fatal. Otherwise retain an explicit unarchived/unlinked occurrence receipt
with interval/phase/size/hash where safely available and bounded error; do not
invent missing raw content or claim complete linkage. A size rejection before
application return is a transport fault, not an invented received occurrence.
Hard termination may still leave incomplete receipts; preserve every partial byte.

Keep512MiB / CPU75% /32 tasks /240s; global60,000 texts,1-GiB raw /256-MiB
compressed,32-MiB completion,64-MiB auxiliary including4-MiB resource component,
1-GiB evidence spool/1,024 files, initial2-GiB free disk/1-GiB reserve. Preserve
262,144-byte incoming limit, queue16,8-MiB segments/gzip1 and all timing/heartbeat/
data watchdogs. Compression and byte/rate/memory headroom are not guaranteed.
Independent retained stage controls/transport are bounded separately by the
existing1-GiB+4-MiB copy ceiling, excluding source checkout and historical stages.

The 90-second acquisition/publication guard is unchanged, with nominal63 seconds
of headroom after27-second planned exposure, **not a persistence promise**.
Acquisition checkpoints, completion and finished pre-close observer component
publish before final close; join<=3s, still-live result unavailable. Existing
five-second library/external close bounds remain; the cleanup race is not repaired.
Final consumer only after close; checkpoint/component alone cannot prove cleanup
return, graceful peer handshake or full completion. Guard and genuine faults
survive cancellation. Original1-ms UTC/5-ms RSS/50-ms RSS-start and all other
original thresholds stand, without subtraction or observer optimization.

**The original complete 60-second CPU-window result is unavailable.** Every v7
report carries null with `unavailable_short_primary_no_prorating`. A short prefix,
inclusive CPU or sampled/inclusive RSS cannot establish that gate, incremental
observer overhead or continuous RSS peak. Eligible means only same-epoch local
fresh-book timing; never venue completeness. Feed-activity upper bounds stay null.

## Readiness, independent audit and conditional approval

Fresh read-only old-v6-source verification at **2026-10-29T02:39:36Z** (October28
22:39 EDT) matched installed runtime/TLS/CA/source/public state,5,943,533,568 free
bytes and unused proposed namespace/unit. Zero metadata/subscriptions/native units
started. Host/credit context is labeled historical/unavailable where appropriate;
no invented minimum. This is installed-byte evidence, **not Linux validation of
v7**. Refresh those gates before staging and launch; drift stops the attempt.

Local full suite: **1,342 tests /178.761s**. Focused actual collector/recovery/
worker/publication/inspector set: **88 tests /23.784s**. Real prewindow/primary
frame saturation uses separate bounded local child processes; encoded-byte
exhaustion and terminal/oversize/linkage faults are exercised. Old plan hashes
and new policy/plan literals are pinned. Packet members accept Python3.9 grammar
locally. Four mocked launcher cases verify one submission/claim-before-Popen,
missing approval, expired window and consumed claim. Real worker/report plus
packet auditor ran offline with deliberately mocked origins and independently
recomputed20 raw/eligible rows. None is Linux/public/memory acceptance.

After separate direct approval of this exact freeze only: refresh gates, stage
once, independently verify every source/member/root permission/import, then use
the sole prepared launcher in its window. Claim durably/exclusively before one
Popen, DEVNULL stdin, retained log/new session and original HUP/TERM; never nohup.
Any prior launch/controller/evidence claim prohibits relaunch.

Independently bind controller PID/start/boot/argv/signals, then worker live
PID/start/boot/cgroup/InvocationID/complete argv/effective limits/ready-release/
case/epoch/default signals promptly at arm. Missing live observation is unknown,
not inferred from producer controls. V7 controller cleanup binds its recorded
invocation and only stops an observed exited private unit; no active/foreign
fallback stop. Missing TasksCurrent stays unknown. External administrator restart
is not atomically fenced; preserve that limitation and actual exit faults.

Independently observe/copy/hash/seal the complete bounded controls/evidence
population, reconcile producer inventory and578 frozen sources, then run the
**exact frozen** report/auditor offline. Verify archive/completion/checkpoint or
consumer/resource/case/runtime/domain/epoch linkage, all20 raw/eligible rows,
quota allocations including terminal bytes, ambiguities/unplaced/prewindow/tail,
gaps/fresh books and every boundary/unavailable bin. Preserve original precision
violations and resource/missed-slot unknowns, inclusive overhead labels, post-run
public/source/runtime state and exact private process/unit exit. Partial/no
capture means null/unresolved coverage, not zero counts or a replacement run.

**Prepared decision:** approval may cover one conditional staging and one bounded
October30 BTC20 case under this exact freeze, followed by independent audit.
No such approval has yet been granted, and no staging or automation has started.
The implementation commit is pushed; this packet and HANDOFF document the next
decision without authorizing capture.
