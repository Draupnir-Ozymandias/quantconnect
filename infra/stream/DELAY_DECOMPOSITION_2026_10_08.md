# Paired delay decomposition — October 8, 2026

## Finding

**The slowest fully timed deliveries spend most of their measured interval before
the last data-frame callback—not between that callback and application delivery.**
In each 128-marker run, the pre-callback lower bound exceeds the post-callback
upper bound for every member of the slowest overall 1%, and for every member of
each phase's separately selected slowest 1%.

This localizes the interval, not its cause. Pre-callback includes producer work,
local transport/buffering, scheduling, and receiver backpressure before further
reads. It is **not network latency**. It does not exonerate the recorder: slow
application consumption can pause subsequent receiver reads, moving the resulting
wait into the pre-callback interval. No wire arrival was observed.

## Fully timed overall tails

Each row selects its own 300 slowest messages from 30,000 by producer-begin to
application-delivery upper bound. All 300 are locally eligible in each 128-marker
case. Values are **means of paired clock-bracket midpoints**, not additive p99s,
and not pooled across runs.

| 128-marker pair | Pre-callback mean, ms | Post-callback mean, ms | Total mean, ms | Pre-callback share of mean |
| --- | ---: | ---: | ---: | ---: |
| 0 | 696.025 | 31.809 | 727.834 | 95.63% |
| 1 | 871.916 | 22.329 | 894.245 | 97.50% |
| 2 | 807.883 | 25.169 | 833.051 | 96.98% |

The share is a ratio of matched means, not a mean of per-message ratios and not
an attribution to a particular implementation stage. Both the callback and delivery
clock brackets remain in the underlying interval calculations.

Separately selected phase tails show the same direction: every one of the 120
low-rate-tail and 180 burst-tail messages in each 128-marker case has a larger
pre-callback interval. Phase-tail pre-callback shares of paired means range
95.50–97.46%. Phase labels follow target producer emission, not receiver phases.
The overall and phase tails overlap and must not be counted as independent data.

## The 64-marker tails remain censored

| 64-marker pair | Eligible / 300 overall-tail deliveries | Unknown |
| --- | ---: | ---: |
| 0 | 0 / 300 | 300 |
| 1 | 167 / 300 | 133 |
| 2 | 85 / 300 | 215 |

Pair 0 has no defensible component statistics for its overall tail. Its known
messages' favorable conditional p99s cannot substitute for the unknown slowest
messages. No unknown callback timestamp was reconstructed. The 128-marker lane
provides full observability for these synthetic cases, not a claim that increasing
the cap improves speed or that its results transfer to public streams.

The [marker-cap trial's failed acceptance gates](MARKER_CAP_PAIR_2026_10_08.md)
remain in force: all three 128-marker delivery tails regressed. This analysis
does not authorize deployment or a new confirmation capture.

## Method and validation

See [the versioned analyzer contract](../../docs/DELAY_DECOMPOSITION.md).
The analyzer pins the six-case prior audit, reverifies all **223 originating
files**, full sealed archives and row chains, saved versus archived raw and
receive records, producer sequence/probe/heartbeat identity, target phases,
same-boot producer/consumer bindings, source policies and corpus.
All **180,000 archived deliveries** remain in their denominators.

Every eligible message's split checks bracket-aware interval closure. Component
lower-bound sums undershoot the total lower bound by callback-bracket width;
upper-bound sums overshoot the total upper by that width. Paired midpoints close
within numerical tolerance. Quantiles are computed independently on the same
eligible population and are explicitly **not additive**.

Recomputed phase total-upper p99s match the bound independent audit. An additional
independent checker, without calling analyzer functions, recomputed tail rankings,
unknown/eligible denominators, midpoint means, interval dominance and closure
for all eighteen case/phase populations.

Local full suite: **563 tests passed**, 18.912 seconds.
All eight new tests passed on Linux/Python 3.9, 0.009 seconds, in a fresh temporary
checkout. Tests cover clock domains/order, unknown/ineligible exclusions, shared
brackets, fragmented-message boundary choice, nonadditive quantiles, censored
tails, budgets, byte tampering, unsafe inventory paths and explicit audit pinning.

No new capture was performed. Linux verification ran only offline tests; public
collector checkouts, configuration and resource limits were not changed. No
credentials, trades, infrastructure changes or QuantConnect synchronization.

## Provenance

Original source capture commit: `20864012a2eb0272d40206e71a7ed7c77621984d`.
Source review: `.qcrl/reviews/marker-cap-linux-20261008-dwJ721/`.
New ignored analysis: `.qcrl/reviews/delay-decomposition-20261008-wGL113/`.

Source audit SHA-256:
`9b08704388c1ef2336ff8238bc4c0f2bea198774042a86589921b1ccc24bb39a`

Analysis SHA-256:
`c846322545a4c4007b815a066ae4067109af63f4bc01b797fc5c5278337c9dc0`

Analyzer SHA-256:
`175b82ce84cf203bd9479478a7c73a49b4ab35881edc93f67136fb3c2bed670b`

Tests SHA-256:
`e4f14e2abdf052104ef4f4d82a08b24f22688ca1660972017ef261413f70c12b`

Independent check SHA-256:
`94596fc527a140592c97b59c9e889d41bedc38dbac7b17d78085602c305799c3`

Independent checker SHA-256:
`6ccba98387a391300c0309d2ee7f5169b6f033854d6b37c427b2a17f4225f42f`

## Next high-value gate

Inspect the pinned library's receive-loop **pause/resume and socket-read boundaries**
and declare a bounded diagnostic observation contract before implementing or
capturing it. The current traces show backpressure samples, not exact pause
durations or socket-read timing. Whole-service profiling/quota samples cannot
fill those missing boundaries or establish event-specific causes.

Any subsequent experiment should preserve flow control, encoding, caps and
process limits, remain numeric-localhost only and compare instrumentation against
its unchanged baseline. Keep the 128 marker cap a diagnostic-only variant and
hold public rollout. Increasing hardware, adding filters or calling the pre-callback
span exchange/network delay would not resolve this evidentiary gap.
