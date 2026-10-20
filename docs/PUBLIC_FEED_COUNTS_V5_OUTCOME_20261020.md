# Public-feed v5 retained outcome — October 20, 2026

**Historical application verdict: FAIL, unchanged. This capture was interrupted;
full-minute coverage and normal acquisition completion are not established.**
There is no combined acceptance badge. The retained prefix supports descriptive
counts of recorded incoming texts, not venue completeness, trading/execution
claims or real-market performance conclusions.

## Exact attempt and independent observations

[Unchanged prospective declaration](PUBLIC_FEED_COUNTS_SUCCESSOR_V5.md).
Case `btc5m-20261020T160000Z-local-counts-05`, BTC five-minute market starting
16:00 UTC; nominal count minute 16:01–16:02 UTC, with five-second tail.
Exact execution/report source `f89ada8cb43036464cd77c08fe4ca7829fbc634a`
(555 selected files); freeze
`7cd0b049ff9380aa405d5368bc197205363654244862c2f328d50a58e236f12f`.
Later documentation HEAD was not substituted.

Fresh read-only gates passed at 15:44:22Z. The one prepared launcher submitted
one controller at 15:45:00.677556Z, PID 2056544/start 144681731; independent live
observation verified its argv and default HUP/TERM dispositions. Exactly five
retained metadata requests ran from 15:55:00.591860 to 15:55:01.080886Z; response
body hashes/lengths match their receipts. Identity locked at 15:55:01.154283Z,
before the declared deadline. Case artifact:
`02fee3cc2c20e4deec36164bd84e3843dc5d12c8fb2472da5dc17b28afc60c65`.

The single private unit started at 16:00:40Z. Independent live binding at
16:00:40.568437Z verified PID 2057932/start 144775687, boot, cgroup, argv,
ready/release identity and epoch, original signals and declared limits. Limits
remained 512 MiB, CPUQuota 75%, 32 tasks and 240 seconds; acquisition remained
90 seconds/60,000 texts maximum. No retry, reconnect, replay, replacement or
additional capture was launched.

## Interruption, ownership and publication

Acquisition ended with `ConnectionClosedError:no close frame received or sent`
at M0+28.779829488 seconds. Last-safe boundary was M0+28.710376203 seconds.
There is one archived connection-gap record and one connection. The underlying
network/peer/TLS cause is unknown; no retained trace establishes it.

Both deadline-interrupt receipts have `fired=false`; ownership is cancelled,
not normal completion. No normal-completion witness exists. The later cleanup
`close()` returned with no close errors at M0+30.303504104 seconds. This verifies
cleanup return, not graceful peer closure or successful scheduled acquisition.
The roughly 1.524 seconds after acquisition includes finalization/publication
and close; it is not an isolated measurement of close duration.

Archive sealing, `completion.json`, pre-close `acquisition-checkpoint.json` and
final `consumer.json` all survived. Independent comparison links case, domain,
epoch, identity and every acquisition result field. The only checkpoint/final
result differences are `closed` (null to timestamp) and `close_completed` (false
to true); the receive fault persists. The checkpoint remains explicitly
close-unverified. This native path demonstrates retained publication and accepted
creation notices on this recording, not normal public-feed end or a guarantee
against future blocked-close publication loss.

The OS process exited status 0; that is not scientific success. Controller
post-checks at 16:01:31Z and independent readback verified unchanged public
collectors/source/runtime/TLS. At 16:06:33Z both exact PIDs were absent and the
private unit was inactive/dead, MainPID 0. No manual stop or restart was needed.

## Descriptive question and interval counts

Question: how many archived incoming text occurrences intersect each nominal
one-second bin of this recording's count minute, under its declared clock model?

There are **32,722** linked incoming texts: **17,070 prewindow**, **15,652
intersecting the primary minute**, zero tail. All 60 interval rows were recomputed
independently using rational interval comparisons and match the exact frozen
report. There are **zero ambiguous-bin or unplaced occurrences**. See the
[60-row count table](PUBLIC_FEED_COUNTS_V5_20261020.csv).

Slots 0–27 have `unverified` coverage; slots 28–59 are `censored`. Every
`feed_activity_upper` is null. Late zero archival counts describe the retained
prefix only; they do not mean zero activity during missing acquisition. The
planned full-minute descriptive population is therefore unavailable. Nominal
UTC anchoring and monotonic-clock assumptions remain those in the declaration;
NTP synchronization context does not establish independent UTC accuracy.

The population includes 104 accepted foreign-condition `new_market` creation
notices, each retained/counting once, all in the primary prefix. They remain
unconfirmed/other-market metadata, not selected-market book state. No foreign
book/trade/other contamination was found by the frozen predicate. Classification
entries can expand batches and must not be summed as incoming text counts.

## Original precision and resource limits

Nothing was subtracted and no threshold changed. One original UTC return bracket,
sequence 21,209, spans M0+4.204377983 to +4.230559888 seconds: **26.181905 ms**,
above the **1 ms** requirement. It lies within bin 4, so this wide bracket creates
no bin ambiguity; the precision violation still stands.

Of 32 RSS observer rows, ten exceed the **5 ms** bracket requirement: slots
0, 1, 2, 3, 5, 6, 7, 9, 29 and 30. Widths range 6.045468–255.716210 ms. Slots
32–60 are absent after early termination; no sampled wait reports an error.
These absent rows do not establish individual scheduler missed-target events.
Resource qualification is **unknown**, with no qualified full 60-second CPU
window. Maximum observed RSS is 74,436,608 bytes, a sample, not a continuous peak.
The whole 50.792809-second unit used 25.708377 CPU seconds inclusively; this is
neither a qualified minute nor incremental observer overhead.

Across all linked texts, append upper p99/worst are 1.370064/49.448949 ms and
durability upper p99/worst are 232.951193/796.803262 ms (nearest-rank p99).
No linked text exceeds the original 1-second append-worst or 2-second
durability-worst bounds. Those component facts do not establish overall timing,
resource or coverage acceptance, or explain the disconnect.

## Integrity, verification and remaining unknowns

Independent origin inventory/copy/hash verification covers all **60 bounded
retained files**, 15,841,820 content bytes, exactly all **36 producer evidence
files**, and all **555 selected source hashes**. The archive has 32,722 complete
ordered frame witnesses and 524 durable barriers; segment/manifest integrity,
header/footer/spec, completion, runtime/domain/case/epoch and consumer linkage
verify. The frozen offline report and independent interval recomputation agree.
No implementation changed; documentation/CSV consistency checks were run locally.
The earlier 1,250 macOS tests remain offline evidence, not Linux acceptance.

Private evidence stays under `.qcrl/reviews/public-feed-20261020T160000Z/`.
The sealed copy is 8,653,585 bytes, SHA-256
`808dbf901ef68ae0cc04fd2e224124cc75a1e54e6a5d489d3c7ca9ef95904eed`.
Independent origin inventory file SHA-256:
`e0204f72b71dfd060398771063cd823099567e9d6b8d7a46e9f379a12ee893fd`.
Independent retained-audit payload SHA-256:
`aa46a8c60cfa1595bb70f0a226add7e727f0cd004e14ddc1d0aabed6476cbf55`.
Separate publication/metadata/final-process checks are retained alongside it.

Disconnect cause, missing-period activity, venue completeness, independent UTC
accuracy, incremental observer overhead, continuous RSS peak and internal
transport retries remain unknown. Credits are historical/unavailable context;
no retrospective minimum or new acceptance gate is inferred. Original historical
application FAIL, v1/v2 not-run, v3 closure fault/unverified coverage and v4 partial
with all 60 null rows are unchanged. The attempt is over; no further native run
is authorized by this result. The one-time follow-up is removed after this audit.
