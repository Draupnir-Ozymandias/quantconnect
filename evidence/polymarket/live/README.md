# Durable Polymarket Live Evidence

This directory contains deliberately promoted, immutable responses from public
Polymarket endpoints. It is version controlled because the response cannot be
recreated after the market changes or closes.

Raw captures first land under ignored `.qcrl/execution_truth/raw/`. Promotion
is a separate operator decision:

```bash
./synch.sh evidence promote .qcrl/execution_truth/raw/<artifact>.json
./synch.sh evidence verify
```

Promotion verifies the artifact and writes canonical JSON to a filename that
contains its contract hash. An existing path is never overwritten with
different content. Public payloads, observation times, endpoint identities,
and payload hashes are retained intact.

These artifacts are evidence, not trading authorization. They may contain
stale market state and cannot prove fills, latency, settlement, or current
availability. Every artifact must also be listed in `inventory.json` with its
evidence role and known limitations.
