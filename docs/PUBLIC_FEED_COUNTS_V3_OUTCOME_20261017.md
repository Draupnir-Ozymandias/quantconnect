# Public-feed v3: retained counts, unresolved coverage

**Historical application-budget verdict remains FAIL. This capture retained a
closure fault and does not establish complete acquisition coverage. There is no
combined acceptance badge.** Both earlier targets remain **not_run**. No trading,
execution, venue-completeness or generalized market-performance claim follows.

The [prospective v3 declaration](PUBLIC_FEED_COUNTS_SUCCESSOR_V3.md) ran once for
`btc5m-20261017T183000Z-local-counts-03`. The independent audit verifies archive
and occurrence linkage and answers the descriptive question for the **known
archived population**, while the frozen report leaves all 60 coverage labels
`unverified`. The original thresholds and fault are preserved without correction.

## Fixed execution and independently retained evidence

Exact source: `de4c10bf3f53bb4fd4ab3646c22a7d5e3fc1536c`, 547 selected files.
Freeze: `b4bb07c78cf5558fea2befe1b7611166678f00344ba6664d942fd6becbe8d7ed`.
Event: BTC five-minute Up/Down, October 17 at 18:30–18:35 UTC / 2:30–2:35 PM EDT.
Market ID `5784125`; both supported outcome tokens were locked before capture.

One controller started at 18:15:00.524492Z. The sole metadata opportunity began
at 18:25:00.508932Z; five bounded public requests completed and the exact case
locked at 18:25:01.091810Z, before the 18:29 cutoff. The private recorder armed
at 18:30:40; its independent unit/PID/start/boot/cgroup release and subscription
readiness preceded the original epoch by the required margin. One connection
attempt and eight PONG texts were retained; no reconnect or replay occurred.

The anchor was `(1197557.112501884, 18:30:40.486917Z,
1197557.112530742)` and fixed epoch `1197576625613743` monotonic nanoseconds.
UTC labels remain nominal, with no independent accuracy bound. The local host
reported NTP synchronized before and after; no decreasing UTC timestamp was
observed among retained occurrences. Neither fact proves true-UTC alignment.

The controller published `collected_pending_independent_audit`, then stopped only
its private unit. Unit exit status zero means the worker published its receipts;
it does not erase their recorded acquisition fault. Post-run checks at 18:32:08Z
had no preservation errors. Independent SSH inspection at 18:35:21Z verified the
exact source/runtime/TLS/public freeze, found both scheduler/controller PIDs absent,
and found the private unit inactive/dead. Public collector state, source and
environment hashes remained unchanged. No infrastructure or resource change.

An independently observed 59-file manifest was followed by a sealed local copy:
**15,358,101 file-content bytes**, including every one of the producer's 35
evidence files, all verified by size and SHA-256. The source checkout is excluded
from this copy and independently reconstructed from exact Git blobs; all 547
frozen source hashes match. Producer origin/acceptance flags remain unchanged;
independent copy attestation is separate from those claims.

| Retained artifact | SHA-256 |
| --- | --- |
| Sealed copy, 8,377,349 bytes | `ada4841cc5ead9c0e2bcb82e0376135e0f94c42f80f24ec33863044d7a03bcd6` |
| Independently observed manifest file | `391c6d5e4489bc5c5ab461bed7f97698616493b59333bf00bd6faf1c02ccfbd8` |
| Independent retained-audit payload | `3d0d239508f51686bf5004176891f20f3ff1e2536806fa18c454d1799e951147` |
| Completion-witness payload | `9aa1fc49bd0603342cbbd57ef8c49391e82705e08142a127863160bf2d03d37d` |

Private archive, original controls, frozen source, independent audit/report and
copy receipts: `.qcrl/reviews/public-feed-20261017T183000Z/`. Original copied files
were not modified by offline reporting. Post-run audit tooling needed Python 3.9
API compatibility adjustments; its empty failed transfer is retained separately.
Those were read-only audit operations, not another acquisition attempt.

## What the recording can answer

The archive contains **31,434 supported returned text occurrences**, linked in
full order to completion receipts and the same process/boot clock domain. Its
six immutable segments, hash chain, footer and manifest verify. There are 509
successful barrier witnesses, no unfinished barrier, no unlinked return and no
unplaced occurrence. This links the known returned/archived population; it does
not prove that every venue message reached this process.

| Location of closed observation interval | Occurrences |
| --- | ---: |
| Entirely before the primary minute | 7,221 |
| Within the primary minute | 21,941 |
| Tail after the primary minute | 2,272 |
| Total archived | 31,434 |

All **60 rows** are in the [count table](PUBLIC_FEED_COUNTS_V3_20261017.csv).
A second implementation tested direct exact-fraction containment/intersection
against every bin and independently reproduced all bounds from the frozen report.
There are 58 bins with identical lower/upper archived counts. Sequence 16,452
straddles bins 20/21: bin 20 is **[325, 326]**, bin 21 **[243, 244]**. The same
occurrence causes both upper increments; upper bounds must not be summed as a
population. No interval straddles the primary minute's outer edges.

Bin 35 has archived count [0, 0]. This means no linked archived timestamp interval
intersects that bin, **not** zero venue activity or proof that acquisition was
uninterrupted. `feed_activity_upper` remains unknown for every row. All coverage
labels remain `unverified`; none were upgraded based on apparently sufficient
tail time. The fault suffix is not zero-filled.

Counting units remain returned texts: batches are not expanded, duplicates are
not deduplicated, and PONGs count. The independent scan finds one selected-market
condition and no explicit foreign bindings. The normalized generic stream spec
retains its legacy connection/reconnect defaults; the frozen one-shot adapter
does not use them to retry, and the observed archive has one connection attempt.

## Retained closure fault and evidence limits

The result is `interrupted`, with one archived connection-gap record:

```text
ContractError:transport already closing at stop; closure timing unknown
```

The scheduled acquisition deadline was M0+65 seconds. The final linked return's
before endpoint was M0+64.999983201; acquisition ended at M0+65.001514100 and
local close returned at M0+65.015844364. The acquisition socket watchdog reports
that it fired; close reports no additional error. Nevertheless, the original
guard observed a transport state other than OPEN, and these receipts do not
identify when or why that state changed. A race with the deadline interrupt is
a plausible explanation, **not an established cause or success exemption**.

The frozen completeness predicate requires normal scheduled stop without a gap
or error. It is false here, even though the last linked frame is near the tail
deadline. Complete local acquisition coverage, missing feed population and venue
completeness therefore remain unknown. No closure exception or threshold changed.

## Separate timing and resource components

The original wall-clock brackets remain authoritative; nothing is subtracted.
The following descriptive timing population is all 31,434 linked occurrences,
without excluding the wide sample or inventing synthetic workload phases.

| Recorded component | Finding |
| --- | --- |
| Return-to-append upper bound | Nearest-rank p99 1.352 ms; worst 32.504 ms; no 1-second worst violation |
| Return-to-durable-watermark upper bound | Worst 1.003027 s; no 2-second violation |
| Original UTC bracket | One violation: sequence 7,270, width 4.762675 ms versus 1 ms, within primary bin 0 |
| Resource grid | 67 rows, slots 0–66; no missing read, wait failure, missed slot or catch-up |
| RSS bracket qualification | 23 of 67 wider than 5 ms, ranging 5.188–36.187 ms; retain as unqualified evidence |
| Wake/read start | Maximum observed wake lateness 22.088 ms and read-start lateness 22.228 ms, below unchanged 50 ms |
| One qualified enclosing 60-second CPU window | Inclusive upper fraction 0.447429489 of the effective 0.75-core quota, versus original 0.7 budget |
| Observed current RSS readings | Grid maximum 60.051 MiB; final post-publication reading 69.758 MiB |

The frozen resource evaluator returns **unknown**, with 23 unqualified sample
rows. Numerical RSS readings below the 512-MiB unit limit do not make those
brackets qualified. The final RSS read has a separate 23.299-ms bracket, outside
the epoch grid. Neither sampled values nor cgroup `memory.current` establish
continuous RSS peak; no `MemoryPeak` evidence was available in the unit receipt.

CPU accounting includes recorder and active observer work in one cgroup, without
subtraction. The complete unit used 29.346447 CPU seconds, including startup and
post-collection publication; its recorded lifetime was about 87.234 seconds.
Final cumulative resource counters show no OOM/memory-limit event, and 95 throttled
periods / 2.065397 seconds throttled. These counters supply context, not a causal
explanation for the wide brackets. Incremental observer overhead and inside-
operation versus scheduling contributions remain unknown; this version has no
RSS thread-CPU instrumentation. Historical observer failures remain FAIL.

Storage stayed bounded: archive raw 43,379,050 bytes, compressed 5,576,839 bytes,
completion sideband 9,142,672 bytes, and copied total 15,358,101 bytes. Readiness
had more than 6.2 GB free; the later post-audit disk snapshot also exceeds the
unchanged reserve. No storage allowance was increased and no evidence deleted.

## Stop and remaining unknowns

The single attempt is over. No second capture, replay, smoke, cohort or tuning
was performed or scheduled. The one-time app follow-up is removed after this audit.

The bounded useful result is the interval-aware count table over this retained
public-feed recording. Full acquisition coverage, closure timing/cause, venue
completeness, true-UTC accuracy, unobserved network/kernel/library timing and
internal transport retries remain unknown. Continuous RSS peak, incremental
observer overhead and contention attribution are not established. Preparation
credit mode/balance are context only; no within-run minimum was observed or made
an acceptance gate. This recording does not generalize to real-market performance;
earlier synthetic results still demonstrate the method only on their recordings.
