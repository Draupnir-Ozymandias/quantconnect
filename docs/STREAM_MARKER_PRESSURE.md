# Receive-marker pressure analyzer, version 1

Completed retained-cohort findings: [October 8 analysis](../infra/stream/MARKER_PRESSURE_2026_10_08.md).

`execution_truth.stream_marker_pressure` is an offline diagnostic for sealed
receive-v3 archives. It does not change capture, freshness, queues, marker caps,
durability or execution policy. It has no network, credential or order interface.

```bash
python -m execution_truth.stream_marker_pressure /path/to/sealed/stream \
  --output /path/to/new-analysis.json
```

The output path must not exist. Keep reports outside originating evidence.
The complete stream verifier runs first; a second bounded scan checks the sealed
row chain and byte count against that anchor. Every raw delivery is then checked
through the complete-connection v3 occurrence/fence validator. Missing or legacy
telemetry fails closed. The report binds the source contract and final record
hash, but does not independently establish campaign/cohort provenance.

Fixed budgets: one million deliveries, 100 connections, 10,000 overflow episodes,
512 joint classification cells. Existing archive verifier limits also apply.
No list of raw messages or per-message timing samples is retained by the analyzer.

## Populations and observables

- All archived deliveries remain in denominators, including unknown timing.
- Joint cells combine availability, alignment state, unavailable reason,
  sampled library-depth band and sampled backpressure.
- An episode is keyed by connection and overflow generation, not payload digest.
  Repeated identical payloads remain distinct delivery occurrences.
- Report retained-prefix deliveries, unknown deliveries, exact recovery fence,
  first known delivery after that fence, and open versus closed episodes.
- A new overflow can occur before the first known delivery after a prior fence.
  That delivery belongs to the new retained prefix and establishes the previous
  episode's resumption; tests cover this overlap.
- Known fragmented messages are counted separately. Unknown message fragment
  counts are not retained and cannot be reconstructed from aggregate counters.

Observed-message/frame increments are differences between delivery snapshots.
The first interval includes callbacks before the first delivery. These are not
transport-read batches, packet boundaries, or proof of when an assembler resumed.
Library depth is sampled after the delivery clock bracket and before consuming
the marker, whereas occurrence counters are captured under the tracker lock.
They are not simultaneous measurements and must not be equated.

## Interpretation boundaries

`pending_marker_budget` plus verified overflow/fence provenance identifies why
the adapter withheld a receive timestamp. It does not identify why backlog
formed, establish wire arrival, or justify filling in unknown timestamps.
Queue depth below the marker cap cannot by itself establish recovered alignment.
Library `max_queue` is a high-water setting, not a hard parsed-batch capacity.

An open episode remains open even if the archive itself is complete. A closing
fence remains an unknown delivery; subsequent known delivery is separately
reported, or missing at the archive boundary. Do not infer unobserved resumption.

There is no public-rollout acceptance rule in this diagnostic. Keep separate
cohorts separate and retain their original byte inventories and audit receipts.
