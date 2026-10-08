# Prospective marker-cap sensitivity, version 1

Six finite localhost recorder cases compare **64 versus 128 retained markers**,
with the single-pass encoder fixed in both lanes. This is a separately versioned
experiment, not a public receive-policy upgrade or a queue-cap change.

Pair order: 64/128, 128/64, 64/128. Reuse the frozen corpus and six-cycle,
30-second / 30,000-message workload, 500/3,000-message/s phases and six synthetic
text PONGs. Producer/consumer are separate processes/cgroups. Keep CPU quotas
100%/75%, memory 512 MiB, tasks 32, runtime 120 seconds, library high-water 16,
durability, freshness, recovery rules and all other numerical caps unchanged.
No audits run during measurement. Preserve all failed and completed evidence.

The diagnostic wrapper temporarily selects a v3-shaped contract with only its
marker cap changed and binds that variant in its signed experiment declaration.
Ordinary production validators reject the 128 variant. Only the explicitly
selected diagnostic lane accepts it; scope exit restores original policies.
The legacy common-shape validation helper receives the same temporary cap,
so it can validate pending depths above 64 without relaxing any other checks.
Do not present the variant as an accepted production v3 contract or teach public
collectors to accept it. Numeric-localhost checks and fixed encoder selection
remain in the unchanged producer/consumer implementation.

## Preregistered evaluation

Verify exact originating bytes, full archive chains, raw/probe/heartbeat identity,
every occurrence/recovery fence, canonical row hashes and physical encoding.
Check actual pair order from worker timestamps, resource caps and successful
exits, source/corpus bindings and unchanged public checkout/configuration.
Run the marker-pressure analyzer only in the bound diagnostic validation scope.

Report each pair and lane separately: known/eligible fractions, unknown records,
overflow episodes, open episodes, CPU, phase p99s, worst delivery upper bound,
producer attainment/deadline lateness, queue/backpressure and memory context.
Do not pool this experiment with earlier encoding cohorts or reconstruct old
unknown timestamps. Conditional known timing does not describe unknown timing.

Advancing to a confirmation requires higher eligible coverage in every pair,
no candidate phase p99 or worst upper-bound regression in any pair, no resource
failure and complete raw preservation. These conservative small-cohort gates
are diagnostic only, not authorization for public rollout. RSS samples and
whole-unit MemoryPeak are descriptive, not identical timed populations.

No public network capture, credentials, orders, infrastructure update, process
quota increase, deployment, or QuantConnect synchronization is authorized here.
