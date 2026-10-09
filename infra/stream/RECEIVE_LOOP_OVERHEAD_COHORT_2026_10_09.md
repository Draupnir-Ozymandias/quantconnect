# Receive-loop overhead cohort — October 9, 2026

## Verdict

**Six cases complete; independent integrity/resource gates verified; advancement
rejected. Keep the receive-loop probe diagnostic-only.** No confirmation, replay,
threshold change or public deployment follows this result.

All **180,000 raw deliveries** and receive markers are preserved, with zero unknown
markers or recovery/overflow generations. All three instrumented sidebands are
complete, within bounds and independently dispatch-linked for **90,000 deliveries**.
However, five local timing records are ineligible (`wide_clock_bracket`), pair 0
regresses the delivery tails, and pair 2 exceeds the 5% CPU-overhead gate. Removing
the timing-coverage failure hypothetically would not make the performance gate pass.

This is a synthetic localhost recorder experiment, not exchange, wire-arrival,
fill, profitability or public-stream failure evidence. Three pairs on a shared
host do not establish event-specific causality or a universal latency penalty.

## Frozen execution and preparation

Execution/auditor commit:
`5c8cfbb3813e71d23eaf47ed88c81453871b9923`.
Preregistration:
`39f4bfccec57910fec0adad1be3fdec16dd8a67d5f7d7f1abe04c7cd224739bb`.
See the [unchanged protocol](../../docs/RECEIVE_LOOP_OVERHEAD.md).

After explicit approval for a fresh attempt, the source checkout was created as
qcrl:qcrl, with original Git bundle/declaration/corpus bytes verified. Git enumerated
main.py normally; no safe.directory exception was added for qcrl. The prior
[root-owned failed attempt](RECEIVE_LOOP_PREFLIGHT_FAILURE_2026_10_09.md) remains
untouched and contributes no measurement data to this cohort.

New dedicated stage:
`/var/lib/qcrl-stream/receive-loop-overhead-Jx4JbGW6`.
The full frozen Linux regression gate passed (633 tests, one expected Python-version
skip). Then exactly six cases ran baseline/instrumented, instrumented/baseline,
baseline/instrumented. Actual unit timestamps verify each test/worker exit and
both workers finishing before the next producer starts. No cases were retried.

Both lanes retained single-pass encoding, scoped diagnostic v3/128 markers,
library high/low 16/4, original six-cycle 500/3,000-message/s schedule, 30 seconds
and 30,000 deliveries per case including six synthetic PONG replacements.
Producer/consumer CPU quotas were 100%/75%; all thirteen test/worker units had
512 MiB, 32 tasks, 120-second limits, original security settings and successful
exits. PID, boot/cgroup and measured-window bindings passed. No audits ran during
measurement. No hardware/resource limits changed.

## Paired performance

Values are individual case statistics, not pooled percentiles. Phase membership
follows target producer schedule; low-rate windows may retain previous burst
backlog. Delivery bounds begin before producer serialization/send and are not
network latency. CPU includes collection, final recorder durability, close/join;
sideband snapshot/persistence and copied-delivery output are outside that window.

| Pair / first lane | CPU seconds, baseline → probe | Low-rate p99 ms | Burst p99 ms | Worst upper bound ms |
| --- | ---: | ---: | ---: | ---: |
| 0 / baseline | 16.5383 → 17.3053 | 686.363 → 967.484 | 727.717 → 1,088.711 | 862.424 → 1,147.281 |
| 1 / probe | 16.3964 → 17.1437 | 764.652 → 736.574 | 895.306 → 871.264 | 937.373 → 911.845 |
| 2 / baseline | 16.3287 → 17.3544 | 727.763 → 762.660 | 842.451 → 859.508 | 881.849 → 870.016 |

CPU increased **4.64%, 4.56%, 6.28%**: pair 2 fails the 5% limit.
Pair 0 low-rate p99 increased **40.96%**, burst p99 **49.61%** and worst bound
**33.03%**, failing each 5% tail limit. The reversed pair improves its tails and
pair 2 stays within tail limits; neither rescues the failed pair.

Maximum sampled in-capture RSS increased **6.18%, 6.31%, 6.33%**, within the 10%
ratio gate. Every paired case retained the same RSS sample population. Whole-unit
MemoryPeak is unavailable for all thirteen units, not zero. Sparse RSS is not a
true lifetime peak; post-window serialization has a different memory population.

Minimum individual producer phase attained **99.4402%** of target, above 99%.
Maximum producer deadline lateness was **32.835 ms**, below 50 ms. Producer-validity
checks therefore did not make the result inconclusive. Post-window CPU samples
were about 5.68–5.73 seconds baseline and 5.93–6.07 seconds instrumented; they are
not free work and precede final measurement-receipt serialization/write, so they
are not complete whole-unit CPU totals.

## Coverage and clock uncertainty

Known receive markers: 90,000/90,000 in each lane. Timing-eligible records:
baseline **89,999/90,000**, instrumented **89,996/90,000**. The frozen gate requires
100% in every case, so even these rare bounded failures reject advancement.

The five records warn only `wide_clock_bracket`: 0/probe index 8015;
1/baseline 22306; 1/probe 29832; 2/probe 22904 and 22909. None are missing raw,
unknown occurrences, sideband-budget losses or failed dispatch links. Do not
rewrite them as precise timing or infer that the probe alone caused scheduling
uncertainty—the baseline has one too.

Probe read-summary populations were 9,225, 9,589 and 9,594; flow-edge populations
546, 536 and 544. All were within their 32,768 bounds, with no disabled observer.
Complete mechanics observations do not override failed overhead acceptance:
do not advance to gate/read interval interpretation merely because sidebands exist.

## Independent provenance audit

Fresh ignored review:
`.qcrl/reviews/receive-loop-cohort-20261009-QYI1OC/`.
Raw download is under `origin/`; derived combined audit is `audit.json`, outside
the immutable originating tree.

Inventory **file-byte hash**, obtained independently over pinned SSH and re-read
after the full audit:
`ae4adfcdfa87aa0d619d7f16d80087f8592fd542cfccdd061cd23f5088a4286a`.

Combined audit SHA-256:
`7a60661af3dbc9f5b40f77e2e9266687410472a59470275c0be15f08f2e0c655`.
Launcher manifest:
`4170a6b441d7239e879e116a4146036901288803b2ed0aa1da3c8d34231952be`.

The auditor verified exactly **232 originating files**, canonical digests, full
sealed archive chains, compact physical rows, producer/raw/probe/PONG identity,
saved versus archived receive records/stamps, recovery trajectories, frame-range
dispatch links, clock/window eligibility, six case statistics, thirteen configured
unit limits/exits, actual process order, source/corpus bindings and unchanged public
state. It checked the exact file population again after the expensive audit.
Hash bindings are not authenticity signatures or protection from a compromised host.

Public source remained `4dd60ba168180243f8600860330dc1afc4816ff4`; environment hash
remained `33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily timer remains active; public stream pilot/observer remain inactive. All finite
private units finished and were stopped. No public collection, credentials,
trades, infrastructure deployment, S3 writes or QuantConnect synchronization occurred.

## Next step

Treat this as a completed rejected experiment. Keep the evidence and thresholds
frozen. Next useful work is isolated observer hot-path/allocation profiling and
clock-bracket fault fixtures, leading to a separately versioned lower-overhead
prototype if justified. Do not relax 100% timing coverage, expand quotas, repeat
this cohort automatically, or deploy the current probe. The rare wide brackets
remain valid uncertainty exclusions; CPU and first-pair tails require attention
independently of those exclusions.
