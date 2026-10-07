# Deterministic receive-path burst analysis — October 7, 2026

The capped EC2 localhost run exhausted the 64-message metadata budget for small
bursts while preserving raw messages. This follow-up isolates callback ordering
from application delivery using the real recorder and archive verifier with an
explicitly synthetic transport and clock. It does not change production code,
capture policy, library flow control, resource caps or EC2 configuration.

## Reproduction and retained evidence

```bash
.qcrl/receive-path-venv/bin/python infra/stream/receive_path_burst.py \
  --root .qcrl/reviews/receive-burst-NEW
```

The root must be new. The finite experiment has 15 fixed scenarios, writes
exclusive declarations/reports and sealed segmented archives, and independently
verifies every archive. Fixture/source hashes and runtime are retained. No
network, credentials, trades, AWS or Polymarket endpoints are used.

Retained final run: `.qcrl/reviews/receive-burst-20261007-validated/`.
Experiment hash:
`c4c543eb692f6bbe4d55b06f63cea00f72593b0adcb1af4ad79366c43f6df51f`.
All 1,208 application-delivered raw messages matched their archived messages
exactly. Of those, 283 had timing attribution and 925 correctly remained unknown.
These totals are fixture outcomes, not estimates of live coverage or data loss.

## Exact boundary under the unchanged v1 policy

All burst callbacks occur before any burst message is delivered. Message sizes
are tested separately at 543 and 2,079 bytes, with identical results under this
fixed schedule. Library queue/backpressure and reader-stall diagnostics remain
unknown: a fixture cannot claim to measure the real assembler.

| Callback burst before delivery | Valid timing records | Unknown timing records |
| --- | --- | --- |
| 1 message | 1 | 0 |
| 16 messages | 16 | 0 |
| 64 messages | 64 | 0 |
| 65 messages | 0 | 65 |
| 300 messages | 0 | 300 |

The 65th pending complete message disables attribution and clears ALL pending
markers, not just the overflowing marker. Subsequent deliveries stay unknown
until the next connection. Timing already delivered before overflow stays valid.
With 25 alternating callback/delivery messages followed by a 65-message burst,
the first 25 retain attribution and the remaining 65 do not. The overflowing
callback is message 90 of that connection (25 consumed plus 65 queued).

This reproduces the EC2 run's pattern of 25 available then unknown records under
a controlled schedule. It is consistent with pending-budget saturation, but is
not proof of the exact packet batching/thread schedule on EC2. Different observed
outcomes for payload sizes alone do not establish a size-specific tracker bug:
pending COMPLETE message count, not bytes or fragments, is the saturated budget.

## Safety and recovery checks

Six new tests cover the matrix and these additional recorder/archive cases:

- A fixture transport close after overflow creates one explicit gap. The next
  connection restores timing, starts occurrence IDs at 1, and retains the prior
  `pending_marker_budget` reason in its reset record. Overflow itself causes no
  reconnect.
- Two-fragment messages split inside multibyte UTF-8, with interleaved protocol
  pings, consume one marker per complete message. Sixty-four messages retain
  attribution across 192 frame callbacks; the 65th complete message still
  saturates the same budget.
- A transport close with 63 undelivered markers and an incomplete fragment
  explicitly discards both in the reset; neither contaminates the next connection.
  Those messages were not application-delivered in this scenario, so this is
  not a transport completeness/lossless-delivery claim.
- A forged, individually hash/clock-valid delivery attempting to resume timing
  after unavailability is rejected by the connection-wide archive verifier even
  after all integrity hashes are recomputed. Identical raw payloads cannot be
  used to bypass occurrence and sticky-unavailability checks.

All 468 repository tests passed in the pinned local runtime, including real
localhost tests. These deterministic cases do not benchmark CPU, heap, real
queue capacity, network receipt or exchange timing. No additional live capture
or EC2 deployment was performed.

## Recommended next experiment, not an implemented policy

Evaluate a separately versioned **bounded drain-before-unknown** policy: stop
adding markers at saturation, but permit the already-identified FIFO prefix to
drain before marking the remainder unknown. Keep the same 64-marker budget,
avoid reconnecting for telemetry alone, and never resume attribution mid-connection
or search ahead by payload hash. Clock regressions, malformed fragments, callback
errors or mismatches would still invalidate attribution conservatively.

For a synthetic 65-message burst this could preserve at most the known 64-message
prefix instead of discarding it. That is a counterfactual bound, not a measured
result or validated implementation. It cannot provide timing for all 300 messages
in a 300-message burst, and incomplete coverage must remain explicit. A new
contract/policy plus adapter and archive tests are required before deployment.
The current v1 policy and its historical evidence must stay unchanged.
