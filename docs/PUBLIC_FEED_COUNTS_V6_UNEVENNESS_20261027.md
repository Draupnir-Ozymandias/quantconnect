# Retrospective v6 bin unevenness — October 27, 2026

**Recording-specific descriptive analysis, chosen after acquisition. Historical
application verdict: FAIL, unchanged. V6 remains partial/unresolved.** This report
answers how uneven the retained incoming-text counts were across the 49 nominal
one-second bins wholly inside both declared local acquisition and book-eligible
windows. It does not estimate missing activity or establish venue completeness,
real-market performance, execution quality or successful recorder completion.

The answer: **39,605 texts across 49 bins, mean 808.27, median 830, range 471–951**.
The population coefficient of variation is **13.51%**; the five largest bins hold
**11.92%** of that population, compared with 10.20% for five equally populated
bins out of 49. Raw and eligible counts are identical within this selected set.
There is a lower-count block after the reconnect, but this recording cannot
attribute that difference to venue activity, backpressure or any particular
recorder/observer/network mechanism.

## Population and selection

Case `btc5m-20261021T160000Z-local-counts-06`: one BTC five-minute market beginning
October 21 at 16:00 UTC. M0 is nominal **16:01:00 UTC**; slot k means
`[M0+k, M0+k+1)`. The primary window is 16:01–16:02 UTC.

The unit is an archived incoming WebSocket **text occurrence**, not an event,
trade, book update or unique message. Batches are not expanded; duplicate
deliveries and accepted creation notices remain counted once per incoming text.
Eligibility uses the original strict whole-return-interval rule, after both
selected assets have fresh books in the same connection epoch. Neither label
guarantees maintained-book accuracy or complete venue acquisition.

| Population | Raw texts | Eligible texts |
| --- | ---: | ---: |
| Entire retained recording | 60,000 | 59,996 |
| Prewindow | 19,680 | 19,679 |
| Primary minute, all 60 bins | 40,320 | 40,317 |
| Analyzed 49 whole eligible bins | 39,605 | 39,605 |
| Other 11 boundary/unavailable bins | 715 | 712 |
| Planned tail, retained occurrences | 0 | 0 |

The 49 bins are **0–23 and 28–52**. Selection follows the existing availability
flags, not count size or a new precision filter. The three primary exclusions
are one text each in slots 24, 27 and 53; the fourth exclusion is prewindow.
Raw intervals include those texts; eligibility excludes epoch bootstrap/final
boundaries. Zero retained tail occurrences do not establish observed tail silence.

No statistics below use zero-filling of the 11 other bins, division by the full
60 seconds, or extrapolation to a complete minute. All primary intervals have
equal raw lower/upper and eligible lower/upper bounds in this recording. The
three retained interval ambiguities are prewindow; none intersects a primary
bin. Zero occurrences are unplaced.

## Distribution across the 49 bins

Raw and eligible statistics coincide; all figures are texts per nominal bin.

| Statistic | Value |
| --- | ---: |
| Minimum | 471 (slot 33) |
| 10th percentile | 664 |
| 25th percentile | 761 |
| Median | 830 |
| 75th percentile | 891 |
| 90th percentile | 933 |
| 95th percentile | 949 |
| 99th percentile / maximum | 951 (slot 4) |
| Arithmetic mean | 808.2653 |
| Population standard deviation | 109.2058 |
| Population SD / mean | 0.1351134 (13.51%) |
| Gini coefficient | 0.07324266 |

Percentiles use nearest rank `ceil(p × 49)` with ascending counts, without
interpolation. SD uses divisor 49, describing this finite set rather than an
estimated population. Gini is `sum_i sum_j abs(x_i-x_j)/(2*n*sum(x))` for these
49 counts; its exact value is `142138/1940645`. These choices are retrospective
summaries, not preregistered hypothesis tests, significance claims or forecasts.

| Texts per bin | Number of bins |
| --- | ---: |
| 0–499 | 1 |
| 500–599 | 2 |
| 600–699 | 4 |
| 700–799 | 16 |
| 800–899 | 16 |
| 900–999 | 10 |

All 49 have observed texts; none is an observed zero-text bin. The minimum is
about half the maximum. That spread coexists with relatively limited ranked
concentration: a large fraction of retained texts is not confined to a few bins.
This says nothing about the unavailable portions of the recording.

## Concentration and temporal blocks

Shares below use **39,605** as denominator. Ranked bins need not be adjacent;
ties are ordered by earlier slot solely for reproducibility.

| Ranked selection | Texts | Share | Equal-count reference |
| --- | ---: | ---: | ---: |
| Largest 1 bin | 951 | 2.4012% | 2.0408% |
| Largest 5 bins | 4,720 | 11.9177% | 10.2041% |
| Largest 10 bins | 9,321 | 23.5349% | 20.4082% |
| Smallest 5 bins | 2,875 | 7.2592% | 10.2041% |
| Smallest 10 bins | 6,425 | 16.2227% | 20.4082% |

Largest-five slots are **4, 3, 9, 2, 10** (951, 949, 949, 938, 933).
Smallest-five slots are **33, 32, 30, 38, 37** (471, 526, 551, 663, 664).
The equal-count reference is arithmetic `k/49`, not a fitted stochastic null.

| Whole-bin block | Bins | Texts | Mean per bin | Share of analyzed texts |
| --- | ---: | ---: | ---: | ---: |
| Before interruption: slots 0–23 | 24 | 21,490 | 895.42 | 54.2608% |
| After rebootstrap: slots 28–52 | 25 | 18,115 | 724.60 | 45.7392% |

The second block's mean is about **19.1% lower** than the first. This comparison
confounds time, connection epoch and acquisition conditions. The peer-reported
“slow consumer: send buffer full” remains a diagnostic, not causal attribution.
This is not a controlled before/after effect, an estimate of message loss or a
general statement about BTC/Polymarket activity.

## All 11 boundary/unavailable bins

Every listed bin retains original `coverage=unverified` and
`feed_activity_upper=null`. Raw/eligible figures are known archived occurrences,
not bounds on missing venue activity. Partial bins are not prorated to one second.

| Slot / nominal UTC second | Raw | Eligible | Availability context | Silence label |
| --- | ---: | ---: | --- | --- |
| 24 / 16:01:24 | 609 | 608 | Boundary before receive fault; conservative window ends +24.717913 s | texts_observed |
| 25 / 16:01:25 | 0 | 0 | Inside reconnect gap | unknown |
| 26 / 16:01:26 | 0 | 0 | Inside reconnect gap | unknown |
| 27 / 16:01:27 | 52 | 51 | Raw availability resumes +27.422669 s; book eligibility +27.621934 s | texts_observed |
| 53 / 16:01:53 | 54 | 53 | Terminal boundary; conservative window ends +53.081592 s | texts_observed |
| 54 / 16:01:54 | 0 | 0 | Unavailable after shared frame cap | unknown |
| 55 / 16:01:55 | 0 | 0 | Unavailable after shared frame cap | unknown |
| 56 / 16:01:56 | 0 | 0 | Unavailable after shared frame cap | unknown |
| 57 / 16:01:57 | 0 | 0 | Unavailable after shared frame cap | unknown |
| 58 / 16:01:58 | 0 | 0 | Unavailable after shared frame cap | unknown |
| 59 / 16:01:59 | 0 | 0 | Unavailable after shared frame cap | unknown |

Conservative raw reconnect gap: **2.704756 s**; book ineligibility: **2.904021 s**.
These are availability boundaries, not proven exact instants of lost messages.
The final archived boundary text can extend beyond the conservative availability
end; acquisition reaches the 60,000-text cap at +53.085595 s. Primary acquisition
is censored for about **6.918408 s** after the conservative end, plus the planned
five-second tail. The eight zero-text bins establish neither local observed
silence nor zero venue activity. Reconnecting does not recover missed messages;
the full-minute feed population remains null.

## Precision, integrity and reproducibility

The original five UTC brackets above 1 ms remain violations: one prewindow and
four in the analyzed bins **0, 9, 12 and 44**. Maximum width is 30.037893 ms.
All four bins remain in these summaries; no width is subtracted or relabeled
acceptable. No wide bracket crosses a bin boundary, which explains exact
archived primary bin counts without repairing the failed precision requirement.
Nominal UTC anchoring is not independent UTC accuracy or venue event time.

Source/report revision remains `fc89c11c8c9186c866385b373db12ba04c721e33`, freeze
`763f855f0b604c27928f341b39d820822fbfe6adc5d7c5ab1797b0cfa9c67a0b`.
The existing [outcome](PUBLIC_FEED_COUNTS_V6_OUTCOME_20261021.md) and all
[60 original rows](PUBLIC_FEED_COUNTS_V6_20261021.csv) are unchanged. Input CSV SHA:
`b5712ba918794474132984ba5f96d9c7d69da9b0bf654285fb1eb93dd157860b`.
The retained archive still matches its original sealed SHA:
`30ff87a242af69579600eee08781d6fc7c4eea491bcfb7c3601e61bf762139cd`.

Offline verification compared every CSV field to the frozen report, applicable
raw fields to the retained audit, and independently recomputed all 60 raw and
eligible counts from 60,000 completion witnesses using exact represented rational
intervals and original epoch boundaries. Separate arithmetic cross-checks use
pairwise Gini and direct sorted concentration sums. This analysis does not
regenerate historical outcomes under current recorder source.

Reproduce the aggregate arithmetic from the hash-bound committed CSV:

```sh
.venv/bin/python ops/analyze_v6_bin_counts.py
```

That script reads the fixed CSV and prints JSON; it makes no network/API calls
and starts no worker, observer or native unit. Private verification/statistics:
`.qcrl/reviews/v6-bin-unevenness-20261027/`.

Final close, normal scheduled completion, final observer samples/native resource
qualification, primary CPU window, incremental overhead, continuous RSS peak,
independent UTC accuracy, internal retries, signal sender and missing activity
remain unknown. Historical thresholds and verdicts are unchanged. No capture,
replay, optimization or native test was performed or scheduled for this report.
