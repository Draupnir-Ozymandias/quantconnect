# BTC20 offline takeover review — October 29, 2026

The user requested takeover of the shorter-window/partitioned-quota task.
The latest remote source already contained the implementation (`86c69b2`) and
packet documentation (`2962a24`). Development therefore continued on
`codex/btc20-takeover`, not main or Lupus's existing branch. No native operation
or capture authorization is inferred from takeover.

## Reviewed implementation

The explicit v7 path supplies the 20-bin counting/collection plan, five-second
prewindow and two-second tail. Phase counters persist across reconnects. Return-
before assigns a spanning occurrence once; exact interval analysis retains its
ambiguity. Bootstrap/duplicate/metadata texts are charged. Safely appendable
quota-triggering/oversized texts are retained, and unarchived or unlinked returns
have separate received-population disclosure. Byte accounting uses actual encoded
rows, with a hard terminal allowance and unchanged global resource/storage caps.

Both final and missing-control reports explicitly leave the original 60-second
CPU gate unavailable, not prorated. Eligibility does not prove venue completeness.
Pre-close publication and the single-worker exited-unit inspector are explicitly
selected in v7. Final close remains a known unresolved lifecycle limitation;
the takeover does not expand scope into fixing it or optimizing observers.

## Reproduced verifier defect and correction

The original quota verifier checked final phase counts/bytes and the recorded
stop reason, but did not reject acquisition records *after* the first exhausted
phase. A bounded faulty-collector fixture suppressed stopping, archived exactly
8,000 prewindow texts and one primary text, then published its real receipts.
Ordinary archive/completion integrity passed; quota replay incorrectly accepted
all 8,001 frames. This is a verifier defect, not evidence that the production
collector actually continued after exhaustion.

Replay now checks chronological stopping before accounting each record: after
the first quota trigger, any record preceding the terminal watermark is rejected.
It allows the original trigger and bounded terminal records; incoming frames
remain prohibited in terminal reserve. New adversarial cases cover both a frame
in another phase and a PING control after exhaustion. They fail on the new
ordering requirement, not on altered hashes or exceeding final phase totals.
No scientific policy/hash, budget, historical verdict or evidence was changed.

## Verification and packet status

All 23 BTC20 focused tests pass on the originating Apple Silicon Mac, using the
established Python 3.14.6 environment. These are offline, injected-path checks,
not Intel/Lupus or Linux validation. The initial full-suite run in a Git archive
copy discovered 1,342 tests; two Git-dependent tests failed because the copy had
no Git metadata. Its remaining tests passed. The corrected complete suite then
passed **all 1,343 tests in 94.550 seconds** in the actual Git checkout with
localhost fixtures permitted. Python 3.9 grammar parsing and `git diff --check`
also passed; neither is installed Linux runtime validation.

The historical packet binds source `86c69b24a8c911d9c277be62b034d7beb20f11b8`
and freeze `49614da6dd74462091b2404ba222a318fc692d8609606a4a9510bf77378ece06`.
It does not bind the corrected verifier. Preserve its exact bytes/documentation;
do not substitute a new source under that old identity.

The private packet/runtime/control files at `.qcrl/reviews/public-feed-20261030T160000Z/`
are absent from this checkout. Consequently no replacement transport or full
source/runtime freeze is claimed. A successor approval packet must:

1. Bind the clean committed corrected source inventory and exact report/auditor.
2. Reuse retained verified controls only after byte/provenance checks; refresh
   installed runtime/TLS/public/disk/namespace gates through an approved workflow.
3. Regenerate and independently verify transport, member manifest, source bundle,
   launcher/readback/auditor and exact confirmation bindings without editing old seals.
4. Keep the prospective October 30 window only if still feasible and separately
   approved. A missed window is not-run; there is no implicit rollover or capture.

The candidate source-only receipt is not Linux readiness, a full execution freeze,
an approval, or evidence that the old private transport was reverified here.
No credentials, external-network test, public capture, staging or cloud sync is needed
to finish this offline review. Localhost test fixtures are separate from a public
feed connection.
