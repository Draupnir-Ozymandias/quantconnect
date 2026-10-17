# Proposed successor public-feed target v2

**Original target remains not run; historical application-budget verdict remains
FAIL. No new combined acceptance badge.** This is a prospective replacement
proposal after the user's request to retry, not a relabel or resumption of
`btc5m-20261017T160000Z-local-counts-01`. Its
[immutable outcome](PUBLIC_FEED_COUNTS_OUTCOME_20261017.md), archive, source and
freeze remain intact. Execution of this exact new window awaits confirmation.

## Exact bounded proposal

| Item | Successor declaration |
| --- | --- |
| Identity | `qcrl.public_feed_interval_counts.study.v2` |
| Policy SHA-256 | `220e1b592365b33dd5e0e4c46ab53103735f4add634694aba4cb745a7fa0adff` |
| Parent policy SHA-256 | `90fe9a6a7fc6fd0ba78b1a1d6218188cfd7399dd06cbd5bae02de870e2f56d32` |
| Case | `btc5m-20261017T170000Z-local-counts-02` |
| Target terms | October 17, 2026, 17:00–17:05 UTC / 1:00–1:05 PM EDT; BTC five-minute Up/Down, both supported CTF tokens |
| Controller preparation | Once, 16:45–16:55 UTC / 12:45–12:55 PM EDT |
| Metadata | One acquisition at 16:55 UTC / 12:55 PM EDT, at most five GETs, 30 seconds total |
| Exact identity lock | Before 16:59 UTC / 12:59 PM EDT |
| Arm | 17:00:40 UTC / 1:00:40 PM EDT |
| Nominal count minute | 17:01–17:02 UTC / 1:01–1:02 PM EDT |
| New stage | `/var/lib/qcrl-stream/public-feed-20261017T170000Z` |
| New unit | `qcrl-public-counts-20261017T170000Z` |

Market existence/IDs remain unverified until that single metadata opportunity.
Require the unchanged product, explicit 300-second terms, resolution source,
description and both token bindings. Missed access, approval, freshness, market
or timing gates mean not run, with no automatic substitution or rollover.

Apart from this new identity/window/namespace and the TLS repair/readiness
requirement below, the [v1 execution contract](PUBLIC_FEED_COUNTS_EXECUTION_V1.md)
and counting method remain authoritative: same after-endpoint anchor, one fixed
monotonic epoch, 60 interval-aware bins, original wall brackets and thresholds,
ambiguity/unplaced/censored handling, one connection, zero reconnects, five-second
tail, 90-second acquisition/60,000-frame cap, existing persistence reserve and
segmented archive. CPU 75%, memory 512 MiB, 32 tasks, unit ceiling 240 seconds;
same disk/spool/sideband/auxiliary bounds. No observer change or diagnostic layer.
No trading, execution, venue-completeness or generalized market-performance claim.

## Prospective CA repair and readiness gate

TLS policy: `qcrl.verified_ca_descriptor_snapshot.v1`. The loader reads at most
4 MiB plus one byte, refuses an oversized or hash-mismatched bundle, and writes
only the verified bytes to a private anonymous mode-0600 temporary file. OpenSSL
loads through its still-open descriptor (`/proc/self/fd` on Linux, `/dev/fd` for
local macOS tests). No Python ASCII decoding or original-path reopening occurs.
The descriptor is closed after context construction. This tolerates non-ASCII
bundle comments without changing trust roots. Certificate and hostname
verification remain mandatory; no additional default trust directory is loaded.

This temporary setup file is bounded, unlinked and outside all measurement
brackets, before subscription. It adds no receive-path timing call. It does not
change measurement limits or supply an overhead guarantee. The runtime inventory
now explicitly includes the installed `tempfile` module. Readiness constructs
the actual verified TLS context before metadata, rather than checking only its
source and CA hashes. Any context failure stops before HTTP with retained error.

Offline tests use the real OpenSSL loader with a valid non-ASCII-comment fixture,
exact loaded-certificate equality, mandatory verification, descriptor permissions
and cleanup, malformed/empty/oversized input, profile/hash drift and replacement
of the original pathname after hashing. The actual readiness function is tested
for successful context construction and refusal of malformed PEM without network
access. Regression tests pin both the preserved v1 and new v2 policy hashes.

At **16:27:11 UTC / 12:27:11 PM EDT**, read-only installed-runtime preparation
invoked the identical repaired function against the original pinned Linux CA
bytes. It constructed a context containing 143 CA certificates with
`CERT_REQUIRED` and hostname verification enabled. No HTTP/feed connection or
unit ran. The original frozen source/runtime/public baseline still matched;
the receipt adds the installed `tempfile` module hash. This is context readiness,
not native public-transport compatibility or a recorder budget experiment.
Private receipts: `.qcrl/reviews/public-feed-20261017T170000Z/`.

## Execution and audit boundary

The exact committed candidate and prospective freeze are recorded in HANDOFF
after local regression and packet sealing. Staging/provenance checks do not
constitute approval. Confirm this exact new one-case packet before a controller
start. Public collectors, original used stages and resource limits are preserved.
Stop at the declared first fault, preserve partial evidence, and never retry this
new target. Afterward independently copy/hash/audit archive and occurrence linkage,
all 60 bin rows, gaps/missed slots, original precision labels and separate resource
components. Incremental observer overhead, continuous RSS peak, independent UTC
accuracy and venue completeness remain unknown unless separately supported;
historical credit context stays stale, with no new credit minimum.
