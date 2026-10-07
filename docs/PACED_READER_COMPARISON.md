# Finite paced localhost reader comparison

`infra/stream/reader_comparison.py` compares bare reader, receive instrumentation
and the full stream-v6 recorder using a hash-bound archived corpus. No public
endpoint, account credential, order or cloud API is used by the runner.

The fixed v1 policy runs 27 cases: three rounds, 100/500/1,000 target messages
per second, two seconds per case, and three modes. Mode order rotates by round.
All modes use pinned websockets 15.0.1, compression/protocol pings disabled,
queue high-water 16, maximum message 256 KiB and five-second close timeout.
The full recorder retains receive v2, freshness telemetry, profiling, resilience,
storage and raw verification; other modes do not pretend to include those costs.
Bare mode includes minimal delivery-clock and queue sampling, not zero-overhead
socket reads. Mode-independent raw sequence validation happens after measurement.

The initial corpus is the first both-token book message plus the first 64
selected price-change messages from the 4:35 p.m. October 7 archived market.
It is a bounded workload sample, not the whole live size/cadence distribution.
Book messages cycle every 65 messages. Native event timestamps are synthetically
replaced and explicit sequence/producer-monotonic probe fields added; original
templates stay unchanged. Each case must receive exactly the sequence it sent.
These modified messages are synthetic evidence, never promoted live observations.

Producer pacing uses absolute deadlines without dropping late messages.
The producer timestamp precedes JSON serialization and WebSocket `send`, not
wire arrival. Reports include deadline lateness, send-call duration, attained
producer/receiver rates, producer-begin-to-delivery upper bounds, locally
eligible callback bounds, missing telemetry denominators and queue samples.
CPU measurements include handshake/close and shared-process work; they are not
isolated consumer CPU cost. Producer thread CPU is separate, but receiver
background thread work is not attributed to the application-reader thread.

Producer and consumer share the same process/cgroup and host. An unattained
target rate, send buffering/blocking or shared CPU competition limits inference.
Short paced runs do not reproduce long-lived streams, internet buffering,
bursty market load or multistream overlap. Do not infer exchange behavior or
size EC2 from a mode ratio without these limitations and coverage counts.

Run only with a new output directory:

```bash
python infra/stream/reader_comparison.py \
  --corpus VERIFIED_CORPUS.json --root NEW_OUTPUT_DIRECTORY
```

Declarations, corpus, per-case producer/delivery artifacts, reports and recorder
archives are exclusive writes. Failed or partial runs stay retained; there is no
automatic retry or restart. The script contacts `127.0.0.1` only. Bounded Linux
execution uses the existing 512 MiB / 75%-of-one-CPU / 32-task limits with a finite
runtime cap, and must not start the existing market observer or daily service.

Initial corpus hash:
`a343b91c289731a9262354bb629b4ef22379b67a806568e3d4f2caf08d1fa849`.
The corpus is retained in ignored
`.qcrl/reviews/reader-comparison-20261007-vDV2YH/corpus.json`.
Initial local run retained all 28,800 messages across 27 cases, report hash
`47017719b007947091dd09f806ef9c849606a52d3a3382143dc282182b97fb65`.
Local behavior is not capped Linux performance; results must be interpreted
separately. Tests cover unchanged templates, identity injection, invalid corpus,
all modes, raw preservation, full-recorder integrity and exclusive publication.
