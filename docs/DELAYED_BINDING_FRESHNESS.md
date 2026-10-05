# Delayed binding and super-fresh diagnostic policy

Implemented 2026-10-05. Offline diagnostics only. No order authorization.

`execution_truth/delayed_binding.py` consumes the aligned declaration, raw
boundary dataset, delayed decision, raw market/book bundle, explicit market
terms declaration, freshness policy, and a binding timestamp. It verifies hashes
and regenerates the delayed decision from source evidence. A rehashed but
hand-edited intent is not accepted merely because its hash is consistent.

The policy in `execution_truth/specs/delayed_binding_freshness.json` uses
provisional engineering limits, not exchange defaults or optimized thresholds:

| Check | Limit |
|---|---:|
| Binding delay from target's starting noon | 300 seconds |
| Intent age from recorded signal decision | 30 seconds |
| Gamma and CLOB observation ages, independently | 5 seconds |
| Each outcome book's local observation age | 2 seconds |
| Each outcome book's exchange timestamp age | 2 seconds |
| Exclusion before target end | Last 60 seconds |

Maximum-age and entry-delay bounds are inclusive. End cutoff is exclusive:
binding at the cutoff rejects. Limits must be explicit integer seconds, not
booleans, floats, or defaults. Both outcome books are checked, not just the
selected side. All metadata and book timestamps must be no earlier than the
signal decision and no later than binding. Exchange timestamps must also not
follow their local observations. This is intentionally strict and may reject
unchanged books whose exchange timestamps are old.

## Explicit market compatibility

`qcrl.delayed_market_terms_declaration.v1` is a deliberate semantic declaration,
not automatic interpretation of a slug or description. It pins lane hash,
market ID, condition ID, description hash, explicit start/end times, resolution
source, BTCUSDT, America/New_York, 1m close price, and split-50/50 ties. Its basis
must be `explicit_terms_declared_for_offline_diagnostic`, and `terms_sha256`
hashes the object without that hash field.

Those exact terms must be checked when preparing a declaration. A matching
description hash alone does not prove the prose has been interpreted correctly.
The binder verifies its pins against normalized metadata, checks the exact
target window and resolution source, and maps the intent to one outcome token.
Calendar target duration comes from the verified delayed decision, not a fixed
86,400-second assumption. No approved declaration for a live market is created
by this implementation; tests use clearly synthetic descriptions.

Market must be active, not closed, order books enabled, accepting orders, and
explicitly fee-enabled under this initial supported configuration. Missing
execution fields still reject. Enabled taker delay and nonzero minimum order
age require separate temporal execution models and therefore also reject.
Support assertions or interpretation sidecars are not substituted into raw fields.

## Output and interface

`qcrl.delayed_binding_result.v1` pins all inputs, records binding time, per-source
ages, rejection reasons, and a mapped token. `binding_checks_passed` means only
that these offline checks pass; a mapped token may be recorded even on rejection.
`orders_authorized` is always false and `constraint_revalidation_required` true.
No acceptance, fees, fills, or profitability are estimated.

```bash
./synch.sh evidence delayed-binding /absolute/path/to/spec.json
```

The spec schema is `qcrl.delayed_binding_example.v1`. It declares
`declaration_path`, `dataset_path`, `decision_path`, `raw_bundle_path`,
`terms_declaration_path`, `policy_path`, and `binding_at_utc`. All paths are
relative to the spec. Output is hashed JSON on stdout; no network or writes.

This is a separate opt-in API. Legacy binding, signal contracts, inventories,
campaigns, and collectors remain unchanged. Passing freshness is only as-of
the declared binding time. Any later use needs new observations and constraint
revalidation; stale rejection does not automatically reacquire or retry.

Next is an offline re-acquisition/revalidation protocol with explicit states
for stale data and changed constraints. The unresolved `oas` default/scope,
historical availability, and evidence needed for trading remain separate gates.
