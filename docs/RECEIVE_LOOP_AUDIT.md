# Independent receive-loop origin/resource audit

The read-only `infra.stream.receive_loop_audit` fills the resource/origin gate
missing from the standalone performance evaluator. It launches no workers, calls
no cloud/SSH commands, repairs nothing and never writes inside originating evidence.
The six-case benchmark remains unrun; fixture passes are not performance evidence.

## Independent inputs

Require an inventory **file-byte SHA-256 obtained separately from the originating
host over the pinned verified transport**, plus the prospectively frozen source
commit. Do not compute the expected hash from the downloaded file and call that
independent verification. This auditor checks the supplied anchor; it cannot prove
how its caller obtained it. Hashes and source commits are reproducibility bindings,
not signatures, exchange authentication or protection from a compromised host.

Copy the full immutable originating stage metadata and evidence into a new review
directory. The inventory lives beside `evidence/`; outer launch manifest/claim must
match the byte-anchored copies inside evidence. The full evidence file population
must match exactly: extra, missing, changed, aliased/traversal paths or symlinks fail.
Recompute the internal inventory hash as well, then repeat all byte checks after
the expensive archive/performance checks. Audit output must be outside this tree
and must not already exist.

## Resource, exit and order gates

Require original launcher/source/preregistration bindings, active daily timer and
inactive stream workers with identical before/after configuration hash and public
commit; successful complete launch result with six cases in the prescribed order,
no failure/preservation errors or preexisting acceptance claims.

Parse saved systemd properties independently. Every test/worker must show qcrl
user/group, 512 MiB, 32 tasks, 120 seconds, fixed CPU quota (100% producer, 75%
consumer/test), private directory/write scope and unchanged security properties.
Require RemainAfterExit and successful exited state, CLD_EXITED/zero status,
positive bounded monotonic lifetime and PID. Missing, duplicate, unsupported or
unlimited resource fields cannot pass. Retain whole-unit MemoryPeak when available;
absence stays unknown, never zero and never a substitute for sampled in-capture RSS.

Bind raw producer/consumer identities to ExecMainPID, launcher boot and per-unit
cgroup paths. Property files often omit ControlGroup after exit; the archived
worker identities supply the cgroup path and must identify the same unit. They
are not an independent external observation of a kernel cgroup. The tests finish
before the first producer; producer starts before consumer; both actual exits
precede the next producer in the alternating order. All thirteen unit PIDs are
distinct. Consumer measurement and post-window persistence timestamps must fit
inside its actual unit lifetime, with one microsecond rounding tolerance.

## Combined result

Invoke the unchanged private case verifier for all six cases: no cached performance
or archive report is trusted. It recomputes physical/raw/occurrence/dispatch
integrity, timing eligibility and resource-independent performance metrics. Preserve
the all-pair thresholds and producer-validity rules. Consumer interval order must
also match the actual unit sequence. No changed thresholds, pooled rescue or retries.

Only this independently byte-anchored, source/resource/order-checked report can
mark its top-level resource/origin gate verified. A performance pass permits only
diagnostic interval analysis; reject/inconclusive remains explicit. The embedded
standalone performance result retains its historical resource-unverified fields;
the combined top-level verdict expresses the additionally verified gate. Public
rollout and orders always remain unauthorized. None of this establishes wire
arrival, exchange delay, event-specific causality, fill quality or profitability.

```bash
python -m infra.stream.receive_loop_audit \
  --root /path/to/immutable-origin-copy \
  --expected-inventory-file-sha256 ORIGIN_TRANSPORT_VERIFIED_FILE_HASH \
  --expected-source-commit FROZEN_EXECUTION_COMMIT \
  --output /path/to/separate-new-audit.json
```

Next: finish unit/integration checks of this auditor, source-freeze it, then decide
whether to run the finite cohort. A future successful launcher exit alone remains
insufficient evidence for advancement.
