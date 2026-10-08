# Single-pass encoding pair, version 1

This finite **localhost-only diagnostic** follows the independently audited
recorder-stage cost study. It is not a public collector deployment. Production
`SegmentedStreamLog`, stream specifications and public configuration remain
untouched. The candidate lives only in `infra/stream/single_pass_encoder.py`.

The baseline hashes canonical JSON, then serializes the row again for storage.
The candidate serializes the unhashed row once with the same canonical serializer,
hashes those exact UTF-8 bytes, and appends a hexadecimal `record_sha256` field
and newline to that root object. Its physical JSON is compact and places the
hash field last. Decoded logical fields and canonical row digests are unchanged.
Physical bytes, byte counts and segment boundaries can differ. Numeric byte
quotas remain identical and apply to actual encoded bytes; smaller records do
not constitute removal of a quota.

The candidate subclasses the real writer and changes only the two encoding
assignments in `append`. Tests compare ASTs to prove all remaining branches are
identical, including quota/reserve checks, rollover, chain updates, profiling,
64-record/one-second/non-frame flushes and fsync. Opening, sealing, metadata,
directory fsync, manifests and exclusivity remain inherited. Fixed-clock tests
prove decoded rows and digests are identical; full v7 archives verify normally.

## Prospectively fixed streaming comparison

- Same immutable 64-template corpus and synthetic initial both-token book.
- Three rounds, two full-recorder lanes, receive-v3 in both lanes.
- Lane order: reference/candidate, candidate/reference, reference/candidate.
- Each case: six cycles of four seconds at 500 messages/s and one second at
  3,000 messages/s, totaling 30 seconds / 30,000 messages.
- Scheduled synthetic text PONG replaces each cycle's last message in both lanes.
- Absolute producer deadlines, no intentional drops, numeric `127.0.0.1` only.
- Separate producer/consumer processes and cgroups on the same shared host,
  without core affinity. Producer CPU 100%, consumer CPU 75%; each has 512 MiB,
  32 tasks and a 120-second cap. No diagnostics are audited during measurement.

The wrapper binds the full diagnostic and execution-truth source inventory.
It scopes the old burst policy to this new declared protocol without changing
the historical module, and selects the candidate through a temporary symbol
replacement only inside the isolated consumer. The borrowed consumer checks the
signed ready binding and numeric loopback URI before opening its socket.
Importing the candidate or pushing Git does not select it in public code.

Complete evidence is downloaded after all six cases. Offline verification checks
every producer/consumer raw-body/probe/heartbeat identity, full sealed archive,
receive-v3 recovery trajectory, and every row's declared physical representation
and canonical digest. Saved systemd properties independently establish resource
settings and process identities. A generic case report alone is insufficient:
each lane must also have its encoding-verification receipt and independent audit.

Compare consumer CPU, producer attainment, per-phase delivery-age tails, maximum
age, unknown/eligible callback fractions, recoveries, queue/backpressure samples,
and actual storage bytes. Medians are over three runs, not pooled messages.
Different cases do not have identical clocks or probes; logical-row/hash equality
across encoders is established separately by fixed-clock tests, not by comparing
independent streaming run digests. No fills or profitability are measured.

This tests a combined single-serialization/compact-format candidate, not a clean
separation of those two effects. A beneficial outcome still requires further
validation before public rollout. Do not attribute prior live gaps or multi-second
tails to encoding solely from this synthetic experiment.

The [completed six-case result and independent audit](../infra/stream/SINGLE_PASS_ENCODING_2026_10_08.md)
show a modest CPU benefit and non-uniform tail improvement. Public rollout remains
on hold; the next gate is an order-reversed confirmation under the same limits.
