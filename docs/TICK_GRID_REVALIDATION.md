# Tick-grid and metadata revalidation

Date: 2026-10-04. Scope: offline mechanics only.

The batch metadata audit found four observed transitions from a 0.01 tick to
0.001. Existing snapshot replay already checks prices against the snapshot's
tick and rejects book/market tick mismatches. It does not know which earlier
observation informed a request. Signal binding pins a decision-time market
contract, but does not refresh exchange metadata at order submission.

## Separate fail-closed guard

`execution_truth/constraint_revalidation.py` takes an origin raw bundle, a
current raw bundle, an unchanged request, the existing replay policy, and the
versioned policy in `execution_truth/specs/constraint_revalidation.json`.
Both bundles are hash-verified and normalized. The request is validated against
its origin. Any observed difference in identity, outcomes, terms, state, or
constraints rejects revalidation. Even a finer tick that still admits the old
price requires a newly reviewed request. No automatic rounding or resizing.

Reverse observation time is invalid. Conflicting metadata at the same timestamp
and metadata observed after the hypothetical replay time reject the guard.
Passing the metadata guard invokes existing replay against the current bundle;
its freshness, unknown-field, fee, and execution-state gates remain unchanged.
Changing displayed book depth alone does not count as a metadata change.

The result hashes both sources, request, and policies, records differences and
rejection reasons, and includes a nested replay only when revalidation passes.
`metadata_revalidation_passed` is not a fill or execution-eligibility verdict.
An origin estimate used for validation is discarded and never a fallback.

## Operator interface

Run `./synch.sh evidence replay-revalidated /absolute/path/to/spec.json`.
The JSON specification has these fields:

- `schema_version`: `qcrl.constraint_revalidated_replay_example.v1`
- `origin_raw_bundle_path` and `current_raw_bundle_path`: paths relative to the spec
- `requests`: existing `qcrl.taker_replay_request.v1` declarations
- `replay_policy`: existing `qcrl.taker_replay_policy.v1`
- `revalidation_policy`: `qcrl.constraint_revalidation_policy.v1`, with
  `mode` equal to `reject_any_observed_change`

Output is hashed JSON on stdout. This command neither acquires evidence nor
submits orders. Existing replay, binding, latency, and collector consumers are
unchanged; the new guard is an explicitly selected interface, not a retroactive
change to their semantics.

## Limits and next gate

Two matching observations cannot exclude an intervening change and reversal.
Offline revalidation cannot establish the latest exchange settings at actual
submission, resting-order survival, order acceptance, queue position, or fills.
The unresolved execution fields remain unresolved, including order-age scope.
Documentation defaults are not injected into historical raw evidence.

Before a trading path exists, it needs an explicit freshness/reacquisition
protocol and vendor clarification of unknown execution semantics. An aligned
Binance/noon-Eastern research declaration remains separate from this mechanics
work; the frozen Coinbase/midnight-UTC signal is not promoted by these checks.
