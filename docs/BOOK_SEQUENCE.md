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

If the only identifier available is the slug from a normal
`polymarket.com/event/<slug>` URL, use the atomic convenience command:

```bash
./synch.sh evidence capture-sequence-slug <slug> \
  --samples 5 \
  --interval-seconds 5
```

It first stores a hashed lookup from the official public Gamma event-slug
endpoint, prints the resolved numeric market ID, and then performs the bounded
sequence. Event resolution requires exactly one market and never chooses among
a multi-market event. If you instead possess the exact market slug, add
`--kind market`. The two lookups use distinct documented endpoints.

To resolve without starting a sequence:

```bash
./synch.sh evidence resolve-slug <slug>
./synch.sh evidence resolve-slug <market-slug> --kind market
```

Slug-resolution artifacts are ignored local evidence until explicitly
promoted. A resolution can remain stored if a later sequence request fails;
that is a complete lookup artifact, not a partial sequence.

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

Raw schema `qcrl.polymarket_raw_slug_resolution.v1` records whether the input
was an event or market slug, the exact endpoint observation, resolved numeric
market ID, and a whole-artifact hash. Slugs are restricted to lowercase ASCII
letters, digits, and hyphens and must match the returned object exactly.

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

## Sequence consumer

The implemented latency-sensitivity layer consumes a verified sequence to ask
counterfactual questions such as “what displayed mechanics are observed after
1, 5, or 10 seconds?” It chooses only an observation at or after assumed
arrival, discloses polling uncertainty, and retains mechanics-only labeling. It
does not interpolate unseen books or convert assumed latency into an execution
claim. See [LATENCY_SENSITIVITY.md](LATENCY_SENSITIVITY.md).

For repeated evidence, the capture-protocol layer locks exact early, middle,
and late start windows before observation, rejects missed or retimed phases,
and records resumable local state. See
[CAPTURE_PROTOCOL.md](CAPTURE_PROTOCOL.md).
