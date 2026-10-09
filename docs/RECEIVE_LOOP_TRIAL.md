# Private receive-loop overhead workers and evaluator

The [frozen preregistration](RECEIVE_LOOP_OVERHEAD.md) is unchanged. Its original
source inventory remains valid. `infra.stream.receive_loop_trial` adds a separately
bound implementation receipt for private numeric-localhost workers and offline
performance checks. **There is no cohort/systemd launcher or resource/origin audit
implementation yet. No six-case benchmark has run.**

## Implementation boundary

Staging creates a new evidence directory exclusively, validates the frozen corpus,
decomposition-linked observation contract and original sources, then records the
new worker/test source hashes. It never installs code, creates a service, connects
a socket or authorizes execution. Changing either inventory invalidates context.

Producer workers reuse the original fixed paced producer under the private cap128
scope. Consumer workers use one identical recorder/spec, single-pass writer and
raw/receive-record tracing in both lanes. Only the selected socket construction
differs: ObservedSocket or DiagnosticSocket. Numeric `127.0.0.1` URI validation
precedes either adapter, including the baseline adapter which otherwise permits
the public feed. CLI production workers require `--execute`; the consumer requires
distinct Linux cgroups and a known shared boot. These checks do not prove quotas.

CPU timing includes collection, native close, final recorder durability and
receiver joins. Sideband snapshots, copied raw/record serialization and measurement
receipt persistence follow the CPU window. No archive audit runs in the measured
worker. Every consumer claims its case exclusively: failed cases cannot replay.
On collection/closure failure, retain partial raw/receive records, available
sidebands, measurement and failure receipts before returning failure. Failure
before collection (source, readiness or isolation) retains the claim and whatever
producer evidence already exists; it never fabricates a measurement.

Each measurement has a new trial-specific schema with its implementation, delivery
and spec bindings. Low-level probe sidebands retain their original diagnostic
prototype schema/status; they are not relabeled as overhead acceptance. The old
fixture envelope/verifier is not repurposed as a benchmark receipt.

## Offline verification and evaluation

The verifier recomputes the original producer/raw/probe/PONG and phase statistics,
sealed archive integrity and compact physical encoding. It compares every saved
receive record and delivery stamp against archived records, and bounds delivery
timestamps inside the declared measured window. Producer begin/send/end ordering
must be finite and nonregressing. Archive/source/receipt hashes are reproducibility
bindings, not authenticity signatures.

Instrumented sidebands are independently scanned using the source-pinned scanner;
each known marker's first/last occurrence and clock bracket must fit an archived
dispatch range. Duplicate connections, missing callback populations or forged
complete-observation assertions fail verification. Incomplete observation cannot
pass coverage. Baseline must have no probe sidebands. Native recovery trajectory
is independently checked. Repeated verification recomputes, without overwriting
or trusting a cached report.

The evaluator requires six unique pair/lane cases, recomputes the fixed all-pair
coverage, CPU, phase-p99, worst-upper-bound and sampled-RSS gates, and keeps
producer validity separate. Missing/zero denominators and inconsistent sampling
are inconclusive. One failed pair cannot be rescued by lane averages. It checks
consumer interval order in the prescribed alternating order, not file order;
this is **not** proof of actual producer/consumer worker exits.

Even a performance metric pass returns `advancement=inconclusive` and
`resource_and_origin_gate=not_verified`. The still-required Linux launcher/audit
must independently verify actual unit order/exits, quotas/resource failures,
originating bytes and unchanged public checkout/configuration. This implementation
does not accept a caller-provided `resource_verified=true` shortcut. It cannot
authorize interval interpretation or rollout on its own.

## API and safety

Offline stage: `python -m infra.stream.receive_loop_trial stage --root NEW_ROOT
--declaration FROZEN_DECLARATION.json --corpus ORIGINAL_CORPUS.json`.

Worker roles are `produce` and `consume`, with `--root`, fixed `--pair 0|1|2`,
`--lane baseline|instrumented`, and `--execute`. They are building blocks for a
future isolated sequential launcher, not instructions to run an ad hoc cohort.
Offline roles are `verify` for one fixed case and `evaluate` for all six.
The evaluator writes a new, never-overwritten result. No public endpoints,
Polymarket credentials, trading or QuantConnect paths are used.

Unit tests use an explicitly injected eight-message schedule and a same-cgroup
waiver unavailable from the CLI. Those temporary fixtures cannot satisfy the
fixed 30,000-message cohort gate and are not retained market or overhead evidence.
Synthetic gate fixtures test rejection logic, not observed performance.

Next gate: implement/source-freeze the finite Linux cgroup launcher and independent
origin/unit-resource audit, test those boundaries, then separately decide whether
to execute the six cases. Do not increase quotas or tune thresholds as part of it.
