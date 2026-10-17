# Successor target v2: not run after browser access gate

**Historical application-budget verdict remains FAIL. Original v1 target remains
not run. Successor v2 is also not run; there is no new combined acceptance badge.**

The user directly approved staging and one bounded October 17, 1-PM EDT target
under the [sealed successor packet](PUBLIC_FEED_COUNTS_SUCCESSOR_V2.md):
`btc5m-20261017T170000Z-local-counts-02`, exact candidate
`33cba4a4b38b0b9f0f77e00199f5cc0631b8726b`, freeze
`4c25a8b5dcf31b55abbfecb3faff7adb46c57f8abe021523908e6fad6804d79d`.
Approval was received before the cutoff and is retained separately from the
original proposal receipt. User approval was not the remaining missing gate.

Browser access to `https://us-east-2.console.aws.amazon.com` was denied when
approved staging was resumed at approximately 12:42 PM EDT. After the user's
permission changes, subsequent checks still returned a saved-permission or
managed-policy denial, including the last check at approximately 12:54 PM EDT.
Read-only local configuration inspection showed an allow for that exact HTTPS
origin. The user's 12:53:18 PM screenshot showed Always allow for Browsing on a
truncated AWS entry and for the default; the screenshot does not expose the full
site pattern. That visible configuration did not reconcile the runtime denial.
Whether a stale saved decision, another matching rule or a managed policy caused
the mismatch is unresolved. No such hypothesis is presented as an established
cause. No browser database/configuration edit or alternate execution path was
used to bypass the security decision.

The fixed **12:55 PM EDT / 16:55 UTC metadata opportunity** passed without
completed source staging/readiness. The agent did not invoke the staging script
or successor controller, make a metadata request or feed connection, or submit a
recorder unit. The last observed remote checkpoint contained only the inert
73,219-byte packet in base64 form, with its declared transport hash; source,
controller claim and evidence directory were absent. Fresh remote state after
the access denials is unavailable. This report distinguishes actions not taken
by the agent from an independent post-cutoff host-state verification, which could
not be performed. No public-collector or infrastructure change was made by the
agent during this continuation.

There was no late adoption, retry, replacement, moved epoch, rollover or new
automation. The one-case permission does not authorize execution of this used
proposal in a later window. Any new study would require another prospective
identity/window; resolve access with a read-only check before declaring it.

## Retained evidence and limits

Private directory: `.qcrl/reviews/public-feed-20261017T170000Z/`. The exact local
packet, source/runtime freeze, inspected staging script, prior installed-context
receipt, direct confirmation, user screenshot and local not-run receipt are
retained. No credentials or raw private packet is committed.

| Receipt | SHA-256 payload or file hash |
| --- | --- |
| Direct execution confirmation payload | `9848b52278396adc33446ab53f525864b3d087b174c2eb0d2339107dd42f21a3` |
| Local access-not-run receipt payload | `638fdde4debdf77143548815ad4953d13666e7123d35d40917daf48ca715a958` |
| User permission screenshot file | `7b320c978109a7bb1f2730e77e708c79f231615808aeba9e11d8af3f26ddb2d0` |

The local receipt contains 60 relative rows with null counts and not-run
coverage. No epoch or occurrence population is invented. Market existence and
IDs remain unverified. No recorder UTC/RSS/CPU/append/durability measurement
population exists for v2. Incremental observer overhead, continuous RSS peak,
independent UTC accuracy and venue completeness remain unknown; stale historical
credit context supplies no new gate. The prior 1,228-test local regression and
limited installed Linux TLS-context check retain their stated scopes and do not
become native recorder compatibility or real-market performance evidence.
