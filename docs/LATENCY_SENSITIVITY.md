# Sequence-based latency sensitivity

`evaluate_latency_sensitivity()` asks how displayed taker mechanics vary when a
decision is assigned different hypothetical arrival delays. It uses only a
verified raw book sequence and the existing guarded snapshot replay. It does
not measure latency, infer a matching delay, interpolate books, or claim fills.

## Selection semantics

The original taker request's `hypothetical_at_utc` is the decision time and
zero-latency reference. For each declared nonnegative integer latency:

1. `arrival = decision time + assumed latency`;
2. select the first captured book for the requested token whose independent
   observation time is at or after arrival;
3. disclose the time from arrival to that observation and, when present, the
   interval between the preceding and selected polls;
4. reject selection if the post-arrival observation lag exceeds policy;
5. run snapshot mechanics at the selected book's observation time.

The selected book is evidence of what was displayed after arrival, not what was
displayed at arrival. The unobserved polling interval may contain arbitrary
changes. A missing future observation returns `unobserved`; it never reuses the
last known book or extrapolates beyond capture.

Policy schema `qcrl.latency_sensitivity_policy.v1` requires the exact selection
rule `first_selected_book_observed_at_or_after_arrival`, 1–32 unique increasing
latencies from 0–86,400 seconds, and a 0–3,600 second maximum observation lag.
The decision time must lie within the sequence capture bounds.

## Result semantics

`qcrl.latency_sensitivity_result.v1` hashes the raw and normalized sequence,
request, replay policy, latency policy, every selected observation, nested
mechanics result, and limitations. It is labeled
`sequence_observation_sensitivity_only` with strategy eligibility false.

A row status of `evaluated` means only that an admissible observed book was
selected and passed to snapshot replay. The nested mechanics result controls
whether displayed fills were estimated. A row can therefore be `evaluated`
while mechanics are `rejected` because market timing metadata is unknown or
unsupported. An `unobserved` row has no mechanics result.

Latency values are assumptions. They are not measured network, server, queue,
or exchange delays. The engine does not use CLOB `oas` as a delay duration and
does not override taker replay's fail-closed checks.

## Reproducible live examples

```bash
./synch.sh evidence latency execution_truth/specs/latency_15m_live_20260909.json
./synch.sh evidence latency execution_truth/specs/latency_daily_live_20260909.json
```

Both use assumed delays `[0, 1, 5, 10, 15, 20]` seconds and allow at most six
seconds from hypothetical arrival to the selected poll.

The 15-minute capture selects Up asks of 0.70, 0.63, 0.63, 0.56, 0.60, and
0.64. Observation lag ranges from 0.330649 to 4.768018 seconds. Every nested
mechanics result rejects `taker_delay_requires_temporal_replay` and
`unknown_minimum_order_age`.

The daily capture selects Up asks of 0.65, 0.62, 0.62, 0.62, 0.62, and 0.61.
Observation lag ranges from 0.35966 to 4.885686 seconds. Every nested mechanics
result rejects `unknown_taker_delay_state` and `unknown_minimum_order_age`.

These are execution-infrastructure observations only. The daily Binance
noon-Eastern contract remains incompatible with QCRL's Coinbase midnight-UTC
signal, and the 15-minute Chainlink contract has a different horizon and source.

## Next boundary

Do not tune the assumed latency grid against five polls. The next useful
evidence is repeated, predeclared sequence capture at different market phases,
followed by descriptive stability of spreads, depth, price displacement, and
polling gaps. Actual fills require authenticated shadow or minimal-risk execution
evidence under a separately authorized operating policy; they cannot be derived
from public books alone.

## September 15 phase application

The unchanged `[0, 1, 5, 10, 15, 20]` second grid and six-second maximum
observation lag are declared separately for the promoted early, middle, and late
sequences:

```bash
./synch.sh evidence latency execution_truth/specs/latency_daily_20260915_early.json
./synch.sh evidence latency execution_truth/specs/latency_daily_20260915_middle.json
./synch.sh evidence latency execution_truth/specs/latency_daily_20260915_late.json
```

Their deterministic result hashes are respectively
`d861eba79e941b5ee77c300237d7ffb5fea437ebfab69fa900958811404cc98b`,
`56e3ffb50c980f952934e65d0a792f4ebb9f4fae1fc91328390e08314bf37b0c`,
and `c074674d450594692519aa27eca92bb07017cbed960630a7e4026b64ec477e08`.
All six rows in every phase select an observed book within policy, but nested
mechanics reject both unknown taker-delay state and unknown minimum order age.
The displayed Up asks are `0.58`, `0.21`, and `0.001` across early, middle, and
late; those are phase observations, not measured latency effects.
