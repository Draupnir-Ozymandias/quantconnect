# Offline receive-phase and gap analysis

`execution_truth.stream_receive_analysis` produces
`qcrl.receive_phase_analysis.v1` under the embedded, hash-bound
`qcrl.receive_phase_analysis_policy.v1`. It performs no networking, trading,
credential access, capture scheduling or deployment.

## Usage and accepted evidence

Run from the repository root, supplying a new output filename:

```bash
python -m execution_truth.stream_receive_analysis CAPTURE_DIRECTORY \
  --output NEW_REPORT.json
```

For a locked rolling-pilot window, explicitly bind its parent declaration:

```bash
python -m execution_truth.stream_receive_analysis PILOT_DIRECTORY/START_EPOCH \
  --pilot-root PILOT_DIRECTORY --output NEW_REPORT.json
```

The tool accepts receive-instrumented stream specs v4 (receive policy v1) and
v5 (receive policy v2), with sealed segmented archives. Supported source roles
are declared public smokes, deterministic synthetic schedules, and explicitly
bound locked-pilot windows. Synthetic archives lacking a raw market bundle
report that verification as unavailable; they are not live evidence.

Verification checks declaration/result hashes, policy and window bindings,
raw market terms where available, the stream chain and terminal footer, and
immutable rolling-window capture derivation. A second bounded pass rechecks
the archive against the initially verified final anchor. Missing publication,
unsupported roles, inconsistent bindings and exceeded budgets fail closed.
Reports preserve source artifact hashes and actual control-file byte hashes.
Input files remain untouched; an existing output cannot be overwritten.

## Reading a report

Totals, phases (`normal`, `draining`, `unknown`) and connections retain every
application-delivered message in their denominators. Reports separate available,
locally timing-eligible, available-but-ineligible and missing-delivery-stamp
counts. Callback-to-delivery bounds and percentile tails are conditional on
both first and last observation intervals being locally timing-eligible.
Unknown and wide-clock messages must not silently disappear from comparisons.

The fixed library-depth bins, pending-marker samples, backpressure samples and
first-reported saturation context describe local instrumentation. They do not
measure wire arrival, exact `recv` return state or exchange queue position.
Time outside `recv` is not necessarily pure reader stall.

Each connection gap retains its reason and logged UTC/monotonic reference.
Recovery separately identifies a later subscription, selected-market delivery,
and both fresh token-book baselines on the same new connection. Old-connection
books cannot satisfy recovery. Log-to-log elapsed times and, where available,
application-delivery brackets are distinct. A missing delivery stamp remains
null; the gap log is **not** the wire-disconnect instant. Unrecovered attempts
remain visible, and the number of messages lost during transport gaps is unknown.

UTC regressions and wall/monotonic interval changes are reported without clock
correction. Resource samples are whole-service context, not event-level causes;
missing or reset counters remain unknown. Neither local clock observations nor
resource samples establish cross-host timing accuracy.

Artifact verification, locally eligible timing coverage and gap-free transport
are separate results. Original smoke acceptance is preserved, including failure.
`continuous_coverage_proven`, `wire_arrival_measured` and `orders_authorized`
remain false. This tool does not establish exchange delivery completeness,
fills, profitability, settlement or an overall cohort verdict.

## Verification on 2026-10-07

All 489 repository tests passed, including real-library localhost tests. The
12 analyzer tests cover both policy matrices, censored tails, missing stamps,
consecutive failures, fresh-book recovery, source tampering, clock changes,
budgets, exclusive output writes and immutable pilot bindings.

Final offline review artifacts are retained locally in the ignored directory:
`.qcrl/reviews/receive-analysis-v1-20261007-UpiCVA/`.
It contains 33 reports: the original Ohio/Ireland v1 smokes, Ohio v2 smoke,
and both fixed 15-scenario matrices. The matrices retain 1,208 deliveries each:
v1 has 283 available / 925 unknown; v2 has 731 available / 477 unknown.
These are scheduling-fixture results, not predictions of live coverage.

Validation hash:
`9f04011c9f745631746559db8808dc4afbbc315684dc97e02f29815fe3a8dcad`.
Ohio v2 report hash:
`b2cb011e864d909b7df7fe07fd768d33e98df3c77e01ce87cec546ae7a392a66`.

The v2 smoke retained 27,419 messages, all locally timing-eligible, but its
original connectivity acceptance remains false after a recovered 1013 close.
From the **logged gap**, re-subscription was logged after 2.361457 seconds;
both fresh token books were logged after 2.481714 seconds, with delivery bounds
of [2.481241, 2.481247] seconds. Conditional callback-to-delivery upper bounds
were p50 0.002991, p99 0.011821 and maximum 0.032343 seconds. Those bounds do not
describe unobserved transport-gap messages or total market-to-client latency.

No new captures, EC2 configuration changes or QuantConnect synchronization were
needed for this offline review. Earlier draft reports remain retained separately.

## Opt-in freshness extension

Stream v6 uses separately versioned analysis/policy v2 to retain raw-replayed
per-connection freshness snapshots and structured close diagnostics. Old stream
v4/v5 output remains v1, unchanged. See
[the opt-in contract and bounds](CONNECTION_FRESHNESS_TELEMETRY.md).
