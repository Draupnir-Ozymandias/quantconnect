# Compact overhead preparation — 2026-10-09

The isolated recorder integration was committed/source-frozen at
`0d29b3dbb8ff4777c0fa52f16adb1775d9624311`. Its 47-file recorder source inventory
is bound by `0c52e1220ee41cac13aa9dd967fb37472af4187848fab75c805bab529850b1a2`.

A separate, offline compact-overhead declaration is prepared:
`c909b91e94413bc2f5a0bcc34f14b328bd4ed76d5258cde6168d05e4db224e8e`.
The actual original corpus and unchanged original native loop contract were used,
not test fixture substitutes. The reference preregistration was independently
hash-checked before extracting the contract; origin evidence was not modified.

Fresh ignored review directory:
`.qcrl/reviews/compact-overhead-prereg-20261009-5taf05zs/`.
It retains original input copies, declaration, preparation receipt, file-byte
hashes and all 56 declaration-bound source files. Preparation receipt SHA-256:
`6429a6d88f59df10c05f79e6ae17a6d9a87f95309a23e8b1e781feca392d95a4`.

Only the policy schema and instrumented implementation identity differ from
the reference policy. The six cases, pair order, 30,000 deliveries/case, pacing,
encoder, native limits, cap128 policy, cgroup quotas, timed window, acceptance
thresholds and no-replay failure policy are unchanged. A policy-parity test
checks all fields rather than selecting favorable gates. The prior reference
cohort remains rejected. No metrics, observations or artifacts were relabeled.

Six new tests verify roundtrip/source bindings, exact policy parity, refusal of
rehashed authority/threshold/source changes, wrong corpus/analysis/native contract,
copy isolation, old-validator rejection and exclusive offline CLI output.
**679 local tests** and **77 Linux candidate/reference tests** passed. The exact
retained declaration was also validated independently on Linux with the same
plan hash. Local/Linux module, test and documentation SHA-256 values matched:

- Module: `3472c5d5de1b1de47a69df74ee30b4afc4d37b11382d4787bb071aef60a78cfb`.
- Tests: `cce144459b4babdfbd7e5c8ab776a721f300a89c3f18389e4247d42cf49481c0`.
- Policy documentation: `434c7b11747205a445be53210a6b7ee352500629a7946bbe50d2b805bddb454c`.

This preparation starts no producer, consumer, Linux unit, timer or benchmark.
There is no candidate worker/launcher implementation or performance acceptance
yet. Tests used isolated temporary Linux checkouts and localhost unit fixtures;
deployed collectors, resource limits, credentials and QuantConnect were not changed.

Next: build separate source-bound compact workers, Linux launcher and independent
origin/resource audit; verify failure/single-use/lifecycle paths and archive/
occurrence/sideband linkage on Linux. Freeze those sources before an explicitly
approved finite execution. Do not reuse the reference launcher unchanged or
retrofit candidate semantics into the rejected cohort's validators.
