# Receive-path drain-before-unknown policy v2 — October 7, 2026

Implemented locally as an explicit opt-in; not deployed to EC2. V1 policy,
defaults and historical artifacts remain unchanged. This improves bounded timing
coverage, not transport completeness, wire measurements, fills or profitability.

## Version selection

| Artifact | Existing opt-in v1 | New opt-in v2 |
| --- | --- | --- |
| Receive policy | `qcrl.receive_path_policy.v1` | `qcrl.receive_path_policy.v2` |
| Header contract | `qcrl.receive_path_contract.v1` | `qcrl.receive_path_contract.v2` |
| Delivery record | `qcrl.receive_path_delivery.v1` | `qcrl.receive_path_delivery.v2` |
| Public stream specification | `qcrl.public_market_stream_spec.v4` | `qcrl.public_market_stream_spec.v5` |
| Rolling pilot | `qcrl.btc_5m_rolling_pilot.v5` | `qcrl.btc_5m_rolling_pilot.v6` |

V2 requires `--receive-path --receive-policy v2 --profile --defer-verification`
when declaring a rolling pilot. `--resilient` remains a separate choice. The
public smoke supports `--receive-path --receive-policy v2 --profile`, but must
be separately authorized before being run on EC2. Omitting the new version
selection retains v1. Non-receive captures retain their existing schemas.

The adapter failure record remains `qcrl.receive_adapter_failure.v1`: it contains
no timing claim and binds whichever validated contract was declared. Existing
freshness and cross-site v1 analyzers still reject these newer stream schemas;
there is no automatic boundary substitution.

## Fixed-budget behavior

The marker cap remains 64; fragment cap 64, message cap 262,144 bytes and pinned
library flow-control settings remain unchanged. No new transport queue, thread,
background writer or reconnect trigger was introduced.

On the 65th pending complete message, v2 stops accepting new timing markers for
that connection and clears only the in-progress fragment. It retains the already
identified FIFO prefix. Deliveries consume those markers in occurrence order and
must match complete-message type/hash. Once that prefix drains, all subsequent
messages remain unknown until a new transport connection. Freeing marker slots
does NOT permit new observations or mid-connection resumption.

Fatal observation errors, malformed identified fragment/message metadata, FIFO
mismatches and invalid chronology still invalidate the retained prefix. Receiver
clock/header checks continue after saturation, but later untracked messages have
no fragment/timing attribution; their protocol validation remains the library's
job. Adapter
errors preserve raw data with a hash-bound failure record. Delivery clock
regressions or impossible elapsed intervals explicitly discard v2 markers;
v1 error handling is unchanged. No payload-hash search ahead is allowed.

Each v2 delivery has `saturation`: null before saturation, or an immutable
connection-scoped record of the last retained message ID, overflow frame ID,
64 retained prefix markers and the overflow callback's bracketed clock sample.
Available prefix deliveries have no unavailable reason; their pending depth
must equal the last retained message ID minus the delivered occurrence ID.
Unknown overflow deliveries require the prefix to be fully drained.

Archive verification checks policy/schema/contract bindings, raw bytes, clocks,
prefix start and order, stable saturation provenance, pending depths, complete
draining and sticky unavailability. It rejects recomputed-hash attempts to erase
or alter saturation, skip the retained prefix, or resume timing after unknown.
Hashes enforce consistency, not exchange authenticity or delivery completeness.

Saturation is contextual metadata sampled under the tracker lock after the
application-delivery clock bracket; a concurrent receiver may have saturated
between those observations. Do not equate the saturation context with the exact
instant of recv return, packet arrival or a causal explanation for elapsed time.

## Deterministic coverage comparison

The same 15 recorder-level schedules and payloads were run under v2. All 1,208
application-delivered messages remained unchanged, and all sealed archives
verified independently. Synthetic clock domains are isolated per scenario.

| Identical scheduled workload | V1 available / unknown | V2 available / unknown |
| --- | --- | --- |
| 64-message burst | 64 / 0 | 64 / 0 |
| 65-message burst | 0 / 65 | 64 / 1 |
| 300-message burst | 0 / 300 | 64 / 236 |
| 25 delivered, then 65-message burst | 25 / 65 | 89 / 1 |
| Entire fixed 15-scenario matrix | 283 / 925 | 731 / 477 |

These are controlled scheduling outcomes, not live coverage predictions or
performance measurements. Missing timing is burst-dependent, not random:
percentile comparisons that silently exclude overflow messages can be biased.
Keep unknown counts and saturation context visible in any future analysis.

Retained final v2 experiment: `.qcrl/reviews/receive-drain-v2-20261007-final/`.
Report hash:
`8d4bf9021121a9bf62e31af3402075520b6a168fd3731983c9f34acc00687b4b`.
Both original Ohio/Ireland v1 EC2 archives were reverified with the new code;
verification objects matched their frozen smoke reports exactly.

## Real-library local checks and remaining work

All 477 repository tests passed, including nine new v2 tests with actual
localhost adapter and recorder/archive paths, metadata failure preservation,
malformed fragments, mismatch/clock handling, reconnect and rehashed tampering.

The final finite macOS/Python 3.14.6 loopback run retained all 3,600 raw messages
unchanged and all 1,800 instrumented deliveries were timing-eligible. That run
did not saturate the marker budget; deterministic fixtures, not this benchmark,
establish saturated-prefix coverage. Median observed/bare batch ratios were
2.25x for 543-byte payloads and 2.90x for 2,079-byte payloads. The earlier retained
diagnostic, overlapping regression work, showed 2.65x/2.63x; do not cherry-pick
ratios or interpret these as controlled policy-to-policy improvements. An
intermediate source revision also produced 2.00x/2.92x and is preserved.

Final loopback: `.qcrl/reviews/receive-drain-v2-loopback-20261007-final.json`.
Report hash:
`41f783bf78a94566ed81412785dd25b130f00a02864cbef6fa600df0de9e5e69`.
The earlier report is retained at `.qcrl/reviews/receive-drain-v2-loopback-20261007.json`.
The intermediate report is `.qcrl/reviews/receive-drain-v2-loopback-20261007-validated.json`.
Neither benchmark measures complete-recorder storage/CPU cost, Linux behavior,
wire latency, exchange parameters or fills.

Next: an explicitly authorized, capped Linux v2 loopback/burst verification and
one finite public smoke, with separate evidence and independent S3 checks. Do
not replace existing capture declarations or launch a larger synchronized cohort
on the strength of local coverage tests alone. EC2, AWS settings, schedules and
QuantConnect were untouched during this implementation.
