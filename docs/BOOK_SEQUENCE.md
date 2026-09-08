# Bounded order-book sequences

`PublicPolymarketAcquirer.acquire_book_sequence()` records a finite series of
complete public market bundles. Each sample independently acquires Gamma market
metadata, CLOB market metadata, and both outcome books. The recorder contains
no credentials, signing, POST requests, order submission, retry loop, or daemon.

## Capture contract

The command is:

```bash
./synch.sh evidence capture-sequence <market-id> \
  --samples 5 \
  --interval-seconds 5
```

It stores one ignored, content-addressed raw artifact under
`.qcrl/execution_truth/raw/`. Five samples make twenty public GET requests. The
interval is an integer pause between complete samples, so actual observation
spacing is the pause plus response time. It is not a fixed-frequency clock.

A run requires 2–120 samples, a 1–60 second interval, and at most one hour of
scheduled pauses. Bounds are checked before the first request. Failure of any
response aborts the run without storing a partial sequence. The artifact still
contains the successfully acquired in-memory samples only until the process
exits; it does not claim a complete sequence.

Raw schema `qcrl.polymarket_raw_book_sequence.v1` contains the requested bounds,
capture start/completion, every full raw bundle, and a hash over the entire
sequence. Repeated identical payloads remain separate timed observations. Each
sample retains four endpoint/parameter identities, response timestamps, source
payload hashes, and its raw bundle hash.

## Offline inspection

```bash
./synch.sh evidence inspect-sequence \
  .qcrl/execution_truth/raw/sequence-market-<id>-<hash>.json
```

The compact `qcrl.polymarket_book_sequence.v1` result revalidates every raw
bundle, requires strictly increasing acquisition times and stable market/token
identity, and reports each sample's:

- raw and normalized bundle hashes;
- Gamma and CLOB payload hashes;
- accepting-orders, fee, delay, and minimum-order-age values, including null;
- both outcome books' observation time, exchange timestamp/hash, normalized
  snapshot hash, best bid, and best ask.

The derived result is also content-addressed. It does not discard the raw
sequence, reconstruct full depth from the summary, or infer why a book changed.

## Promotion and evidence meaning

Promotion uses the existing explicit workflow:

```bash
./synch.sh evidence promote <raw-sequence-path>
```

Promotion revalidates the entire sequence and copies it to durable evidence.
The operator must then declare its raw and normalized hashes, role, capture
start, subject, and limitations in the live inventory. Nothing is promoted
automatically.

A sequence establishes how public responses changed at discrete observation
times. It does not establish continuous liquidity, maker priority, hidden
orders, request transit time, matching delay, hypothetical or actual fills,
wallet settlement, or profitability. Exchange delay remains unknown unless
contemporaneous authoritative evidence defines it. Temporal sensitivity models
must label assumed latency separately from verified exchange behavior.

## Next boundary

The next implementation may consume a verified sequence to ask counterfactual
questions such as “what displayed execution would remain after 1, 5, or 10
seconds?” It must choose only an observation at or after the assumed arrival
time, disclose polling uncertainty, and retain snapshot replay's mechanics-only
label. It must not interpolate unseen books or convert an assumed latency into
an execution claim.
