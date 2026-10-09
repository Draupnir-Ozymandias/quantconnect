# Compact recorder overhead preregistration

This is a distinct offline declaration, not an executable campaign or authority
to run captures. The verified recorder is frozen at
`0d29b3dbb8ff4777c0fa52f16adb1775d9624311`. Its 47-source inventory hashes to
`0c52e1220ee41cac13aa9dd967fb37472af4187848fab75c805bab529850b1a2`.
The declaration refuses a changed recorder source, corpus, native observation
contract, decomposition binding, policy, or declaration source inventory.

The prior reference preregistration
`39f4bfccec57910fec0adad1be3fdec16dd8a67d5f7d7f1abe04c7cd224739bb`
remains rejected. Its evidence, workers, launcher and validators are not changed.
The candidate receives a new schema and plan hash, never the reference identity.

## Fixed experiment

Only the candidate implementation and policy schema label differ from the
reference policy. The baseline is the unmodified ObservedSocket recorder; the
instrumented lane uses CompactDiagnosticSocket. Both use single-pass encoding,
scoped v3 cap128, the identical frozen corpus and native queue/read/connection
parameters. Order remains baseline/instrumented, instrumented/baseline,
baseline/instrumented: six cases, three pairs. Each case has six 5-second cycles
(4 seconds at 500 messages/second and 1 second at 3,000), 30,000 deliveries,
absolute pacing with no drops and the same synthetic text PONG replacement.

Separate producer/consumer processes and cgroups share one Linux host without
CPU affinity. Producer quota is 100%, consumer quota 75%; each process group
has 512 MiB, 32 tasks and a 120-second unit runtime limit. Observation limits
stay at 32,768 read summaries, 32,768 flow edges and 32 MiB encoded sideband.
No quota relaxation, DNS/public connection, credential use or trading is allowed.

Measurement starts before connect and ends after recorder return, close and
receiver join. Sideband snapshot/serialization, delivery serialization, archive
verification and analysis are outside that window. Durability is unchanged.

## Unchanged acceptance

Every case must retain all 30,000 raw deliveries, timing-eligible markers and
instrumented dispatch linkage. No observation loss, resource failures, marker
overflow or open recovery episodes are allowed. Every pair must independently
meet CPU, low-rate p99, burst p99 and worst delivery-upper-bound ratios <=1.05,
and sampled RSS ratio <=1.10. Producer phase attainment must be >=99% and maximum
deadline lateness <=50 ms. Missing metrics or zero baseline denominators are
inconclusive, not passes. No pooled percentile or median rescues a failed pair.
Failure means preserve evidence without replay, retuning or confirmation in
this cohort. A pass would authorize diagnostic interval analysis only, not a
causal claim, public rollout, wire-arrival measurement or profitability claim.

## Offline preparation

```bash
.qcrl/receive-path-venv/bin/python -m infra.stream.receive_loop_compact_overhead \
  --corpus /absolute/path/to/original/input-corpus.json \
  --loop-contract /absolute/path/to/original/loop-contract.json \
  --output /absolute/path/to/fresh/preregistration.json
```

Output is exclusive, source-bound and deterministic for the same inputs/source.
No network is contacted and no worker, timer, service or collector is started.
The native loop contract can be taken unchanged from the original reference
preregistration; use a separate file, never edit origin evidence.

Before execution: implement and source-freeze separate compact candidate
workers, Linux launcher and independent origin/resource audit with lifecycle,
single-use claim, archive/occurrence/sideband and Linux tests. They must use the
new declaration identity and candidate scanner, not a relabeled reference
measurement. Independently anchor source/input bytes and preserve collector
configuration. Execution requires a subsequent explicit approved finite run;
this declaration does not grant it.
