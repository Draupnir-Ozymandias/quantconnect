# October 17 public-feed target: not run

**Historical application-budget verdict remains FAIL. No new combined acceptance
badge or real-market measurement result.** The one fixed target
`btc5m-20261017T160000Z-local-counts-01` stopped during its declared metadata
opportunity, before any HTTP request, case lock, feed connection or recorder unit.
No retry, replacement target or rollover occurred.

Exact frozen source: `3ec2f92b16b6d1334770acc25c4869f18868ea63`, 542 selected files.
Freeze: `02942f3bfbbf45d78ed818fe3c574546ded4fdf7d49fe4720107aefc240d18a8`.
The [prospective contract](PUBLIC_FEED_COUNTS_EXECUTION_V1.md) and original draft
remain unchanged. This outcome does not retroactively revise their requirements.

## Observed sequence and failure

The scheduled follow-up began at 11:45 EDT. AWS access initially required renewed
sign-in; the user restored it before the preparation deadline. Fresh read-only
source/runtime/TLS-byte/public-state/namespace/disk checks succeeded at
15:50:32 UTC (11:50:32 EDT), with 6,294,167,552 free disk bytes. One controller
was submitted at 15:50:47 UTC and published its exclusive claim. Fresh clock
context reported NTP synchronized; it supplies no independent UTC accuracy bound.

At **15:55:00.575922 UTC**, the controller invoked the single metadata opportunity.
The helper failed while constructing its verified TLS context, at the frozen
`pinned_tls` call `ssl.create_default_context(cadata=data.decode('ascii'))`:

```text
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc5 in position 129802
```

This precedes construction of the public acquirer and every GET. The attempt
receipt and traceback were retained; there are zero request receipts and no
response bodies. The controller's disposition is `not_run`, with
`capture_unit_submission_attempted=false`. The helper's outer error is
`CommandError:helper nonzero exit 1`; its retained traceback identifies the cause.
The controller exited. No case, release, epoch, archive, completion receipt,
consumer receipt or matching recorder unit exists.

The provenance gates verified installed bytes, including the CA bundle, but did
not exercise TLS-context construction. The offline verified-TLS fault check used
a different local fixture; it did not cover this installed-bundle decoding path.
Therefore the successful provenance checks did not establish functional transport
readiness. This is a local adapter setup failure, not evidence that the target
market was absent, that the venue rejected a connection, or that a network failed.

## Independent retained-evidence review

Post-checks at 15:56:55 UTC matched the original source/runtime/TLS/public baseline,
confirmed the controller PID absent and found no matching study unit. Public
collector state, public source/environment hashes, resource limits and historical
evidence were preserved. No recorder needed stopping because none was submitted.

The observed Session Manager host/stage anchor was followed by an independent
local copy of the sealed archive. All **21 files / 619,691 file-content bytes**,
including every file selected by the origin inventory, match their byte counts
and SHA-256 values. The copy retains the original staging packet and incomplete
staging transfer as well as this attempt's controls/error. The exact source tree
is excluded from that archive and separately verified against all 542 frozen
entries in a detached local checkout. Producer origin/acceptance flags remain
false; observed copy linkage is recorded separately and proves no budget result.

| Artifact | SHA-256 |
| --- | --- |
| Sealed archive, 452,642 bytes | `8e19d8939e2cf028b8534a58ab68686055dfe6299ac683753fb8fdab48fb17fc` |
| Origin inventory payload | `ad009c78c24f2719fbb5a692ae42b3c74f703789cd5de20c8861f4b38b208d7a` |
| Controller outcome payload | `ac29723b62d003ae22d68b353b2575384848e096d75eae2f928e241b9d2622e1` |
| Independent not-run audit payload | `93d216ca9b73f9c2f8004f366b74f16511605d51b3be1c89fb3ce05ca8f721f5` |

Private receipts, original archive, extracted bytes, detached source, offline
audit script and output are in `.qcrl/reviews/public-feed-20261017T160000Z/`.
Neither credentials nor raw private packet contents are committed to GitHub.

## What this evidence establishes

The declared descriptive question remains unanswered for this market/window.
The private not-run report contains 60 relative slot rows with null lower/upper
counts and `not_run` coverage. There is no monotonic epoch or occurrence
population; these rows are unavailable measurements, not observed zero activity.
Market existence and outcome bindings remain unknown. No UTC precision, RSS,
CPU, append, durability or observer-overhead population was acquired. Continuous
RSS peak and incremental observer overhead remain unknown; historical credit
context is stale and no minimum was added. Synthetic counting results retain
their original scope, not venue completeness or real-market performance.

A local offline reproduction invokes the actual frozen `pinned_tls` function
with a byte-hashed, valid CA fixture containing a non-ASCII comment. The frozen
ASCII decode fails; the verified OpenSSL file loader accepts the same fixture.
This demonstrates the restrictive decoding assumption. It does not establish the
semantic location of byte 0xc5 in the native bundle, whose full content was not
copied, or validate any native public transport.

The targeted prospective repair is binary-safe loading of the same byte-pinned
CA bundle through OpenSSL's file interface, with unchanged trust roots and
certificate/hostname verification. Its offline checks should cover non-ASCII
comments, malformed PEM, file/hash drift and the actual context-construction
readiness path before metadata. A later target would need a new prospective
identity and authorization. This attempt's source, freeze, thresholds and
`not_run` outcome are immutable; no patch or new execution was made here.
