# Receive-loop overhead preregistration — October 9, 2026

Outcome: **fixed protocol and offline declaration implemented; no benchmark run**.
See [the prospective protocol](../../docs/RECEIVE_LOOP_OVERHEAD.md).

Six cases alternate baseline/instrumented, instrumented/baseline,
baseline/instrumented. Both retain the frozen corpus, 30-second/30,000-message
schedule, single-pass recorder, scoped diagnostic 128 markers, original library
16/4 flow control and previous process/cgroup limits. No public collector changed.

Every pair must preserve complete raw and timing evidence and instrumented
dispatch linkage, without observation loss or resource failure. CPU, both phase
p99s and worst delivery upper bound must stay within 5% of baseline; sampled RSS
within 10%. Producer validity has separate preregistered gates. Missing metrics
are inconclusive, and failed pairs cannot be rescued by pooled statistics.

`infra.stream.receive_loop_overhead` binds the fixed policy, original corpus,
verified decomposition-linked observation contract and relevant source inventory.
It has no execution role, socket call, worker launcher or performance evaluator.
Seven new tests cover roundtrip/bounds, rehashed policy/source/contract tampering,
wrong corpus/analysis, deep-copy isolation and exclusive output creation.

Final local regression suite: **606 tests passed**, 18.477 seconds. The first
sandboxed attempt could not bind an existing localhost fixture and was interrupted;
the full suite then passed with localhost permission. No Linux run occurred in
this declaration-only step; the prior integration's Linux checks remain historical.

Final ignored declaration:
`.qcrl/reviews/receive-loop-overhead-declaration-20261009-mAvrIJ/final-declaration.json`

Plan SHA-256:
`39f4bfccec57910fec0adad1be3fdec16dd8a67d5f7d7f1abe04c7cd224739bb`

An earlier, unexecuted `declaration.json` is retained in the same directory.
It preceded the clarification that per-case post-window persistence finishes
before the next worker while audits wait until all measurements finish. It is
superseded, not overwritten or used as measurement evidence.

Next: implement and source-freeze a private numeric-localhost runner and offline
evaluator against this protocol, with unit-fixture checks before any finite Linux
cohort. Do not reuse fixture envelopes with `benchmark_performed=false` as
benchmark receipts. No measurements, captures, remote commands, infrastructure
changes, trades, credentials or QuantConnect synchronization occurred here.
