# Compact candidate independent audit

Separate read-only module: `infra.stream.receive_loop_compact_audit`. It never
launches workers and does not modify originating evidence. Audit output must
be outside the origin tree and is written exclusively.

Required independently learned inputs are the originating inventory FILE byte
SHA-256 and the staged source commit. Never derive those trusted anchors solely
from a downloaded manifest. Verify the exact file population/bytes, path safety,
symlinks and outer/inner metadata copies before analysis, then recheck after it.

The auditor accepts only compact candidate schemas and implementation/source
bindings. It verifies unchanged public state/configuration, the successful test
unit and 12 worker units, fixed quotas/security/exit results, PID/boot/cgroup
identity, actual start/exit ordering and measured/persistence window containment.
Missing, partial or failed lifecycle evidence is not a completed cohort.

Each case is independently recomputed from archive/raw occurrences/physical
encoding and compact sidebands using the candidate worker verifier, not a cached
result. Pairwise performance gates are identical to the preregistered reference
thresholds. Only independently verified origin/resources plus passing metrics
permit diagnostic interval analysis; no causal, wire-arrival, fill, profitability
or public-rollout claim follows. The previous reference rejection stands.

CLI arguments: --root, --expected-inventory-file-sha256,
--expected-source-commit, --output. Synthetic unit/origin tests and tiny localhost
worker fixtures test failure and linkage semantics, not actual overhead.
