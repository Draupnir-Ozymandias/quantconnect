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

## Sealed approval packet and remaining staging gate

Exact candidate: `33cba4a4b38b0b9f0f77e00199f5cc0631b8726b`, 544 selected files.
Full prospective freeze:
`4c25a8b5dcf31b55abbfecb3faff7adb46c57f8abe021523908e6fad6804d79d`.
All 1,228 local tests passed in 179.786 seconds; 27 focused tests also passed
after the final installed-module-inventory addition. Python 3.9 syntax accepted.
These are local tests, separate from the limited Linux context check above.

Packet transport: 73,219 bytes, SHA-256
`17324ee17c94e9a4f0af253e442a31dfbfb51324304e272dc6ef556991e8c147`.
The inert base64 packet is present in the new stage and independently matches
that hash. No source has been extracted there; no controller claim/evidence
directory exists. The proposed authorization receipt explicitly marks exact new
window approval pending. It does not claim the user inspected this new hash.

Reviewed staging script SHA-256:
`4c41f2cbb21e40d48e59e008f2819cf5a59f5ad54a2f3fa4293a55fb894af0c8`.
Private script: `.qcrl/reviews/public-feed-20261017T170000Z/staging-command.py`.
It checks the transport and six explicit members, refuses overwrites/nonregular
or oversized entries, unpacks only into this new private stage, clones the old
source as a read-only Git input into the new checkout, checks out exactly 33cba4a,
and verifies all source/runtime/TLS/public/namespace gates including actual context
construction. It writes a staging receipt, starts no controller/unit and performs
no market GET. Root privileges are used for private file ownership and staging;
historical files, public services, IAM, networking and instance limits are untouched.

Automatic approval review rejected the upload/execution of that script because
the retry request did not clearly authorize the exact successor deployment and
the generated script had not been inspected. It has since been inspected locally;
no workaround or repeated execution was attempted. Exact staging and one-case
execution approval are requested together. After approval, record the direct
confirmation separately, finish staging, refresh gates and start one controller
only during 12:45–12:55 PM EDT. If confirmation/readiness misses the deadline,
retain this proposal as not run; do not move it to another window.

Controller argv after those gates, with working directory the new stage's
`source`, installed interpreter and normal signal dispositions:

```text
/opt/qcrl-stream/venv/bin/python -m infra.stream.recorder_public_operator controller --root /var/lib/qcrl-stream/public-feed-20261017T170000Z --freeze-sha256 4c25a8b5dcf31b55abbfecb3faff7adb46c57f8abe021523908e6fad6804d79d --execute
```

Use one exclusive start receipt, retained log, DEVNULL stdin and
`start_new_session=True`, without `nohup`. The controller enforces the fixed
metadata and arm schedule. No additional smoke, diagnostics, cohort or automatic
attempt is part of this packet. Approval is conditional on successful fresh
staging/readiness; a failure retains evidence and stops rather than granting an
exception. Later documentation HEAD does not replace the frozen candidate.
