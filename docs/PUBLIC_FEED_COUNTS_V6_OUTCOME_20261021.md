# Public-feed v6 retained outcome — October 21, 2026

**Historical application verdict: FAIL, unchanged. V6 is partial/unresolved;
normal scheduled completion and final close are unverified.** There is no combined
acceptance badge. The positive component finding is one observed public reconnect
with resubscription, fresh-book bootstrap and linked observations on both sides
of an explicit acquisition gap. It does not establish recovery of missed messages,
venue completeness, maintained-book accuracy, trading/execution or real-market
performance.

## Exact attempt and native binding

[Unchanged prospective packet](PUBLIC_FEED_COUNTS_SUCCESSOR_V6.md).
Case `btc5m-20261021T160000Z-local-counts-06`, one BTC five-minute market starting
16:00 UTC; nominal count minute 16:01–16:02 UTC, with five-second tail.
Execution and offline report source `fc89c11c8c9186c866385b373db12ba04c721e33`,
561 selected files; freeze
`763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b`.
Later documentation HEAD was not substituted.

Fresh independent read-only gates passed at 15:44:21.745308Z. The one prepared
launcher submitted one controller at 15:45:00.646228Z, PID 2171862/start 153321728.
Independent live observation verified argv, explicit v6 and original default
HUP/TERM dispositions. Exactly five metadata requests/bodies verify within the
sole 15:55 opportunity; identity locked at 15:55:01.287856Z. Case artifact
`ce0ed412ec44b37cfb025198c66dd2747ac6b22ccf2dca61b90d3650cf079769`.

The single private unit armed at 16:00:40Z. Independent live binding at
16:00:40.636198Z verified PID 2173238/start 153415687, boot, cgroup, argv/version,
ready/release/case/epoch, original signals and effective limits. Limits stayed
512 MiB, CPUQuota75%, 32 tasks, 240 seconds; acquisition remained at most90 seconds
and60,000 texts across all epochs. No forced disconnect, manual retry, extra
capture, replay, substitute, smoke, cohort or infrastructure/resource change.

## Observed recovery and bounded termination

Times below are relative to fixed nominal M0. Subscriptions are retained local
send-return markers under the frozen source, not separate venue acknowledgements.

| Field | Epoch 1 | Epoch 2 |
| --- | ---: | ---: |
| Connect attempt | −19.362310 s | +26.561542 s |
| Full subscription send returned | −18.962031 s | +27.422669 s |
| Fresh-book bootstrap boundary | −18.865088 s | +27.621934 s |
| Conservative availability end | +24.717913 s | +53.081592 s |
| Retained incoming texts | 41,779 | 18,221 |
| End | Receive fault | Shared frame cap |

Epoch 1's retained exception reports **received 1013 (try again later)** with
reason **“slow consumer: send buffer full”**, followed by sent1013. This is a
peer-reported diagnostic through the installed library, not independent proof
of where or why backpressure arose. The underlying bottleneck remains unknown.
The fault remains in the checkpoint even after recovery.

One retained retry wait requested 1.836239 seconds, inside the declared first
1–2-second jitter range. The frozen path reaches this marker only after the old
close returns; the second attempt/subscription followed it. No third attempt
occurred. Each epoch's first incoming text was a batch containing new full books
for both selected tokens. Independent raw/witness checks reproduced bootstrap;
nominal payload ages were about52–58 ms in epoch1 and52 ms in epoch2. These are
nominal clock-based bootstrap observations, not continuous book-state guarantees.
No previous epoch book was carried forward.

The conservative raw acquisition gap spans M0+24.717913 to +27.422669 seconds,
**2.704756 seconds**. Book ineligibility extends to +27.621934, **2.904021 seconds**.
These are declared conservative availability boundaries, not proven exact instants
of loss. Reconnection supplies no count or recovery guarantee for missing activity.

The global **60,000-text cap** ended acquisition at M0+53.085595 seconds, before
the scheduled M0+65 deadline; no counter/budget was reset on reconnect. Neither
epoch has normal scheduled-end ownership. All four retained socket-interrupt
receipts were unfired/error-free and cancelled at checkpoint publication. They
do not describe the later process-close guard.

## Publication, SIGTERM and retained faults

The archive sealed with footer/manifest, 60,000 ordered completion witnesses and
960 successful durable barriers. `completion.json` and the pre-close
`acquisition-checkpoint.json` survived; their retained file timestamps are
16:01:55.780947Z and16:01:55.808236Z. The checkpoint preserves the1013 receive
fault, two epochs, frame-limit summary, `closed=null`, `close_completed=false` and
`close_verified=false`. No final `consumer.json` or final observer result exists.
No missing control was fabricated.

Retained unit properties report **ExecMainCode=2 / ExecMainStatus=15 (SIGTERM)**,
exiting at16:02:00Z. Nominal timing is about five seconds after checkpoint
publication, consistent with the existing five-second close guard. **The SIGTERM
sender and exact final-close progress remain unproven.** There is no retained
post-close/fired-process-guard receipt. A systemd `Result=success` label does not
establish recorder completion, successful close or scientific acceptance.
The controller correctly retained `partial_or_unresolved` with
`worker exited without consumer receipt`, then stopped/sealed only its unit.

## Descriptive counts and unavailable acquisition

Question: what archived incoming-text interval bounds can this recording establish
across its connection interruption, separately from fresh-book eligibility?

There are **60,000 linked texts**: **19,680 prewindow**, **40,320 intersecting the
primary minute**, zero tail. Raw primary lower and upper sums both equal40,320.
The separate eligible population is59,996 total, **40,317 primary**. Four texts
are excluded by the declared strict whole-interval rule: each epoch's bootstrap
text and each epoch's final boundary text. They remain in raw counts. No dedup,
batch expansion, favorable filtering or missing-message recovery was applied.

All [60 raw/eligible interval rows](PUBLIC_FEED_COUNTS_V6_20261021.csv) were
independently recomputed with exact represented rational endpoints and match the
frozen report. Three interval ambiguities are retained, **all prewindow**; none
intersect a primary bin. There are zero unplaced occurrences. All original
`coverage` fields remain `unverified`; the separate availability/eligibility
columns are component descriptions, not a replacement acceptance badge.

49 bins lie wholly inside local acquisition/book-eligible windows. The11
boundary/unavailable bins are24–27 and53–59. Bins24,27 and53 contain known archived
texts despite incomplete interval coverage. The **eight zero-text bins**—25,26
and54–59—are unavailable, with `silence=unknown`; none establish observed silence
or zero venue activity. Every feed-activity upper bound and the full-minute feed
population remain null. Terminal availability is censored afterM0+53.081592;
the unobserved primary remainder is about6.918408 seconds, plus the planned tail.

All22 accepted foreign-condition creation notices are retained/count once as
unconfirmed/other-market metadata; no foreign book/trade/other contamination was
found by the frozen predicate. Classification counts may expand batches and must
not be summed as incoming-text population.

## Precision, resources and limits of inference

Five original UTC return brackets exceed **1 ms**: one prewindow and four primary.
Widths are20.134220,4.117825,19.983336,30.037893 and30.029515 ms; maximum30.037893 ms.
Nothing was subtracted, filtered or relabeled acceptable. None of these five
brackets crosses a bin boundary; precision violations and bin ambiguity are
separate facts. Clock labels/ages remain nominal; the anchor is not an independent
UTC-accuracy guarantee.

The final resource-observer rows/RSS brackets were not published. Their absence
is **unknown qualification**, not zero RSS violations or evidence that all planned
slots were observed/missed. The initial read and startup unit snapshot cannot
replace them. No qualified primary60-second CPU window or continuous RSS peak is
established. Retained whole-unit CPU is52.553558 CPU seconds over80.530816 elapsed
seconds, inclusively; that is not the original primary-window qualification or
incremental observer overhead. Original CPU/RSS/bracket/start thresholds stand.

For the linked texts, append upper nearest-rank p99/worst are2.773352/33.947457 ms;
durability upper p99/worst are96.668241/396.369930 ms. No linked text exceeds the
original1-second append-worst or2-second durability-worst bounds. These component
facts do not repair missing resource/final-close evidence or the historical FAIL.
The peer's slow-consumer reason does not isolate observer, recorder, network or
venue contribution; no new diagnostic experiment or optimization was run.

## Independent integrity and final disposition

Independent origin inventory/copy/hash/seal covers **67 bounded retained files**,
28,459,950 content bytes, exactly all **43 producer evidence files**, and all
**561 selected source hashes**. Archive/header/footer/manifest/completion/runtime/
domain/case/epoch/lifecycle linkage verifies under the exact frozen source.
Independent checks also verify metadata response hashes/window, two subscriptions,
bootstrap receipts, one retry/gap, strict eligible exclusion and all60 counts.
A separate checkpoint supports these linked prefix components while final close
and final resources remain unknown.

Private evidence: `.qcrl/reviews/public-feed-20261021T160000Z/`.
Sealed copy15,493,759 bytes, SHA-256:
`30ff87a242af69579600eee08781d6fc7c4eea491bcfb7c3601e61bf762139cd`.
Observed-origin inventory file SHA-256:
`62cc5bde2df72a80d2a457386a29c85883d27cfcc1adf75349ed453463a0dbd6`.
Retained-audit payload SHA-256:
`387353451ae8355a173884702a7f218d71ebb1bc7a34f06a3fcd76e5e7fac1c8`.
Independent lifecycle supplement payload SHA-256:
`04a7e7e40220fc8e354bf0a4253ba93d73518275a3506b050b384bef2e866da1`.

Post-run and independent readback verify public collectors/source/runtime/TLS
unchanged; exact worker/controller gone, private unit inactive/dead. No extra run
was started. The one-time follow-up was deleted after the final audit. Local
1,280 tests/79 focused checks remain offline evidence; this single Linux recording
adds the specific observed recovery/publication components above, not overall
Linux/public/resource acceptance or general performance claims.

SIGTERM sender, final-close progress, underlying slow-consumer cause, missing feed
activity, final observer samples/RSS qualification/primary CPU window, incremental
overhead, continuous RSS peak, independent UTC accuracy and internal transport
retries remain unknown. Credits are historical/unavailable context, not an invented
minimum or new gate. Historical application FAIL and all v1–v5 evidence/thresholds
remain unchanged. The authorized attempt is over; no capture or rollover remains
scheduled and no further native run follows from this result.
