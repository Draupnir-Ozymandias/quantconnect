# Deferred verification and staged data-health policy — October 6, 2026

## Evidence and first intervention

Profiling cohort `503b3a19...` completed three lifecycles, with 557,413 frames
and all 242 retained files matching S3 byte-for-byte. Nevertheless, selected
events reached socket-return ages of 21.93, 18.20 and 12.43 seconds. Post-read
classification delay had medians near 30 microseconds. Those are receipt ages,
not measured one-way network latency.

During the third market, a five-second window increased cgroup throttled periods
by 51 out of 51 total periods, and process CPU by about 3.76 seconds. This
overlapped the previous market's immediate verification pass in the same
process. Verification rereads, hashes and classifies hundreds of thousands of
frames, competing with the current reader under the service CPU quota/GIL.
This is an avoidable local contention risk, not proof of the entire delay's
cause: the first market's long tail occurred before any preceding verification.

The next prospective cohort changes **only verification scheduling**. Keep
profiling, socket limits, fixed reconnect policy, source terms, frame/byte caps,
two workers and hardware unchanged. Time-of-day and market activity still differ;
this observational before/after comparison is not a randomized causal test.

## Versioned deferral contract

`qcrl.btc_5m_rolling_pilot.v4` supports
`verification_phase=after_all_capture_workers`. Request it with
`declare --profile --defer-verification`.

Each worker completes bounded capture and independent final/postclose metadata
checkpoints, then exclusively persists hashed `capture_result.json`. It performs
no heavy stream verification, including on capture failure. This file is not
verified lifecycle success. After **all** observation workers have joined, the
controller verifies each retained stream and exclusively writes `result.json`,
linking the immutable capture result's hash and recording verification time.
Failed or missing prefixes remain failure evidence; no file is overwritten.

The final cohort health pass rereads evidence and checks the capture/final-result
link, sources, manifests, raw classifications, summaries, both token baselines
and actual checkpoint timing. Only then can the service report healthy.
Intermediate S3 uploads can contain capture results without final results;
they are provisional evidence, not completed verified cohorts. Startup does not
replay declarations. A crash during finalization remains incomplete.

Existing v2/v3 declarations remain valid and reproducible; their original
verification scheduling is retained for archival compatibility. Only newly
declared v4 deferral cohorts activate this change. Daily collection is unchanged.

## Staged, inactive data-health policy

The separately opted-in `qcrl.stream_resilience.v1` contract adds:

- Both initial outcome book messages within 10 seconds of subscription.
- A 30-second selected-market book/price-change inactivity watchdog during the
  explicit trading interval. PONGs, trades, top-of-book and other-market events
  do not reset it. Pre-open/post-close silence is not labeled an active freeze.
- A diagnostic stale-flow watchdog: qualifying book/price-change timestamps
  more than five seconds old for ten monotonic seconds. A fresh qualifying event
  clears suspicion; absent, invalid or future timestamps do not prove freshness.
- Capped exponential **equal jitter**: first retry 1–2 seconds, second 2–4;
  general ceiling eight seconds. The existing maximum three connections remains.
  Record the chosen delay; close the old socket before the jittered wait and
  resubscribe both tokens. Reset book baselines and watchdog state each time.
- Recorded gap reasons `initial_books_timeout`, `selected_book_data_silence`
  and `stale_timestamped_book_flow`; exhausted attempts stop as incomplete.

These thresholds are declared provisional operational heuristics, not optimized
strategy parameters, evidence of an upstream fault, or permission to trade.
Quiet markets and uncertain exchange/local clock semantics can cause false
positives. Neither a heartbeat nor fresh snapshots establish missing-event
recovery or continuous delivery. No order-book reconstruction is introduced.

Activate only in a **separate later declaration** with `--resilient` after review
of the deferral-only cohort; this also requires deferred verification. Do not
change an already locked pilot or mix interventions when evaluating deferral.
The first deployed follow-up therefore has no `resilience` field in either plan
or stream header, and retains the existing two-second reconnect pause.

Sources reviewed October 6:
[CLOB silent-freeze report](https://github.com/Polymarket/py-clob-client/issues/292),
[WebSocket randomized/backoff recovery guidance](https://www.rfc-editor.org/rfc/rfc6455.html#section-7.2.3).
The issue is a participant report, not a confirmed cause for our captures; its
own inactivity workaround uses 120 seconds. Our 30-second heuristic is specific
to the declared active BTC lane and remains subject to prospective validation.

## Verification

Twelve new tests cover heartbeat-only freezes, initial baselines, scoped data
silence, stale/fresh/future timestamps, retry bounds and socket cleanup,
versioned/rehashed policies, deferral-only isolation, immutable capture/final
results, failure checkpoints, and worker-join ordering. Full local suite:
408 tests pass. `git diff --check` passes.

Deployment is limited to the isolated observer checkout and a future finite
three-market pilot. No disk/instance/IAM/firewall/budget changes, credential
access, QuantConnect sync, trading, or new recurring timer is needed.
