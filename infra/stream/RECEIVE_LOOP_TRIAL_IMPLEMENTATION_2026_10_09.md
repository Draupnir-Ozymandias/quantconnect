# Private worker/evaluator implementation — October 9, 2026

Outcome: **private worker and offline performance evaluation implemented and
unit-tested; six-case Linux cohort not started**.

See [implementation boundaries](../../docs/RECEIVE_LOOP_TRIAL.md) and the unchanged
[preregistered protocol](../../docs/RECEIVE_LOOP_OVERHEAD.md). Original policy,
corpus and source declaration remain byte-valid. Worker/test/document sources
have a separate implementation receipt, not a rewritten preregistration.

Ten new tests cover both real eight-message localhost worker lanes; independent
raw/archive/receive/dispatch checks; repeatable offline recomputation; rehashed
spec/window/stamp tampering; replay refusal; partial-failure preservation; rejection
of public URLs before adapter construction; prescribed interval order; all-pair
ratio/coverage gates; missing/zero/nonfinite/negative metrics; incomplete observation
and duplicate case populations. Unit-only injected workloads and same-cgroup
waivers are unavailable from the CLI and cannot satisfy the fixed cohort gate.

Final local regression suite: **616 tests passed**, 19.643 seconds. No Linux host
commands or benchmark measurements ran during this implementation step. Local
tests used finite numeric-localhost fixtures only; no public endpoint was contacted.

Offline staged implementation receipt:
`.qcrl/reviews/receive-loop-trial-freeze-20261009-PJtIYg/evidence/implementation.json`

Implementation SHA-256:
`9d55ffb4f5d1941c4eabba5e69146a3f76c31711906304b2f1c05852123be998`

Original preregistration SHA-256:
`39f4bfccec57910fec0adad1be3fdec16dd8a67d5f7d7f1abe04c7cd224739bb`

Staging created source/corpus receipts only, with no ready, measurement or producer
artifacts. It does not prove Linux quota configuration, originating object bytes,
actual unit order/exits or overhead acceptability.

The performance evaluator therefore intentionally retains
`resource_and_origin_gate=not_verified` and `advancement=inconclusive`, even if
all performance metrics pass. There is no caller-controlled boolean to bypass
that missing independent audit. Consumer interval order is a separate check,
not a substitute for worker exit evidence.

Next: build/source-freeze the finite sequential Linux cgroup launcher and independent
origin/unit-resource auditor, test their failure boundaries, then decide whether
to execute the preregistered six cases. Public collectors, quotas, infrastructure,
credentials, trading and QuantConnect remain untouched. Changes remain local;
no commit or push occurred in this step.
