# Batch execution metadata audit

Implemented and first run: 2026-10-04. This is an offline descriptive audit,
not a signal campaign, execution authorization, or fill model.

## Declaration and command

`execution_truth/specs/metadata_audit_daily_20260915_20260930.json` pins the
existing cross-market phase cohort by file SHA-256 and the October 3
documentation policy. It explicitly declines current-documentation defaults
for these historical observations. Changing the input cohort requires a new
reviewed declaration and hash, not a silent expansion of this result.

```bash
./synch.sh evidence metadata-audit \
  execution_truth/specs/metadata_audit_daily_20260915_20260930.json \
  --output-directory .qcrl/execution_truth/audits
```

Without `--output-directory`, the command prints JSON. Saved audits are
content-addressed, ignored runtime outputs; reruns are deterministic and
existing files cannot be overwritten with different content. No network,
credentials, promotion, Git push, QuantConnect submission, or EC2 update occurs.

## Verification and semantics

Each supplied sequence and nested bundle is verified using the existing
normalizers. The audit checks identity/outcome agreement across phases,
chronological phase order, duplicate observations, and duplicate conditions
under different market labels. Malformed or tampered inputs stop the entire
audit. Missing phases must be declared as null and remain coverage gaps.

Per observation, the report pins bundle, CLOB payload, and interpretation
hashes. It retains normalized state and constraints separately from interpreted
fields and raw optional metadata (`r`, `cbos`, `aot`, `ibce`, `v`). These raw
features have presence markers; their inclusion does not endorse operational
semantics. Rewards `r.moas` never supplies execution `oas`.

Changes compare adjacent *observed* metadata configurations within each market,
distinguishing within-sequence and between-phase differences. They do not
locate the actual change time or prove stability between polls. Counts concern
snapshots, not independent trials, statistical significance, or success rates.
Unobserved metadata keys are outside this report's change-detection scope.

The current-documentation flag is declared in the audit spec, not inferred from
the computer's date. The existing interpreter rejects it for pre-review
captures. Documented omission defaults stay sidecar-only; raw and normalized
execution constraints, replay gates, and promoted inventories remain unchanged.
Minimum order age's operational scope remains unresolved even when explicit.

## First cohort findings

Five markets, 13 observed sequences, 156 snapshots, and two missing middle
phases (September 20 and September 22).

- All 156 snapshots omit explicit taker-delay and minimum-order-age evidence.
  Both fields remain unknown under the historical interpretation policy.
- Four between-phase tick-size differences were observed: `0.01` to `0.001`
  on September 15, 18, 20, and 30. September 20 has no middle observation,
  so its comparison spans early to late; the others span middle to late.
- No changes were observed in the other selected metadata fields. This does
  not prove they stayed constant between samples or outside the captured phases.
- The report does not explain why tick size changed, nor establish that a
  resting order would survive, reprice, reject, or fill after such a change.

Audit SHA-256:
`94176a502c52126a63b51a9d28a51a9392a008e3979ebf24158109b88e7bc0d8`.
All 43 promoted inventory artifacts passed the existing offline verifier.

## Next high-value step

Audit the existing replay/intent contracts for tick-grid changes between
observation and submission. Declare a fail-closed, fixture-tested mechanics
policy before changing replay behavior; use freshly observed constraints and
do not guess order acceptance or silently round an intent onto a new grid.
Polymarket clarification still governs `oas`, and an aligned Binance research
lane remains a separate prerequisite for signal-to-execution claims.
