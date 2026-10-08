# Localhost delay decomposition, version 1

Completed findings: [October 8 paired decomposition](../infra/stream/DELAY_DECOMPOSITION_2026_10_08.md).

This offline diagnostic reads the six existing marker-cap cases. It requires an
explicitly pinned prior independent-audit hash, reverifies originating bytes,
sealed archives and row chains, checks saved versus archived raw/receive records,
and binds producer probes, target phases, same-boot identities and source policies.
It neither captures data nor changes collector configuration.

```bash
python -m infra.stream.delay_decomposition /path/to/marker-cap-review \
  --audit-sha256 VERIFIED_AUDIT_SHA256 --output /path/to/new-analysis.json
```

The output must not exist. Budgets: six cases, 30,000 deliveries per case, 256 MiB
per signed JSON input, 10,000 originating inventory entries and twelve detailed
examples per phase tail. Unknown and ineligible callback timing remain explicit
denominators, with no fabricated component intervals.

## Paired clock intervals

For producer-begin scalar `P`, last-data-callback clock bracket `[Clo, Chi]`, and
application-delivery bracket `[Dlo, Dhi]`, calculate each message separately:

| Component | Lower bound | Upper bound |
| --- | --- | --- |
| Producer begin → callback | Clo − P | Chi − P |
| Callback → application delivery | Dlo − Chi | Dhi − Clo |
| Producer begin → application delivery | Dlo − P | Dhi − P |

The callback bracket is shared. Summing component lower bounds undershoots the
total lower bound by callback width; summing uppers overshoots by the same width.
Paired midpoints close exactly within numerical tolerance. **Independent component
percentiles are not additive.** All component quantiles use the same eligible
messages, and each message's interval closure is checked.

Phase and overall tails select the slowest 1% by total upper bound, descending,
with ascending delivery index resolving ties. Selection includes unknown and
ineligible records; component statistics keep their excluded counts explicit.
Phase groups use target producer emissions, not observed receiver state. Known
64-marker populations must not be treated as unbiased substitutes for all
128-marker deliveries or for unknown 64-marker tails.

## Interpretation

Pre-callback includes producer serialization/send, local transport and buffering,
receive-thread scheduling and library backpressure before further reads. It is
not pure network latency. Post-callback includes observation, assembler/queue,
scheduling and caller processing; it is not pure queue wait. The last callback
bracket is the split boundary even for fragmented messages.

Clock eligibility is inherited from both archived observation-to-delivery
intervals. There is no cross-host clock correction, event-specific fsync/quota
attribution, fill claim or public-rollout acceptance in this analyzer.
