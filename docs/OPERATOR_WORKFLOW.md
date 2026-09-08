# QCRL Operator Workflow

The local Git checkout is the source of truth. GitHub is the durable remote.
QuantConnect project 33239307 is the cloud compiler, data, backtest, and result
environment. `.qcrl/` is ignored local execution state.

## Normal change sequence

```text
edit locally
  -> ./synch.sh test
  -> ./synch.sh push-plan
  -> inspect git diff/status
  -> git add + git commit
  -> git push origin main
  -> ./synch.sh push (confirm overwrite)
  -> cloud campaign run
  -> API collect
  -> validate/analyze
  -> update and commit documentation
```

`./synch.sh push` sends LEAN-eligible source files from the local checkout to
the linked QuantConnect project. The installed LEAN CLI considers `.py`, `.cs`,
`.ipynb`, `.css`, and `.html` files; Markdown documentation and ignored
`.qcrl/` state are not uploaded. `git push` sends Git commits to GitHub and does
not update QuantConnect. Those are separate operations.

`./synch.sh push-plan` is read-only. It lists every tracked file eligible for
upload, reports its character count, and fails if any file exceeds
QuantConnect's 64,000-character limit or shadows a Python standard-library
module name rejected by QuantConnect. `push` runs the same preflight before it
asks for confirmation.

## Before any QuantConnect push

```bash
./synch.sh status
./synch.sh test
./synch.sh push-plan
git status --short --branch
git log -1 --oneline
git push origin main
./synch.sh push
```

The sync guard requires a clean tree. The confirmation is meaningful: local
project files overwrite their linked cloud counterparts. Do not edit the same
files locally and in the web IDE.

## Campaign lifecycle

```bash
./synch.sh campaign plan campaigns/<manifest>.json
./synch.sh campaign run campaigns/<manifest>.json --execute --limit 1
./synch.sh campaign status campaigns/<manifest>.json
./synch.sh campaign run campaigns/<manifest>.json --execute
./synch.sh campaign collect campaigns/<manifest>.json
./synch.sh campaign validate campaigns/<manifest>.json
```

Use the one-case integration gate for a new engine or contract. The runner is
resumable and skips ineligible/completed cases; “No eligible campaign cases
remain” normally means state already records all cases as completed, not that
the manifest is empty.

Load QuantConnect API credentials only into the current shell:

```bash
set -a
source .env
set +a
```

Never commit `.env`. Collection through the API is authoritative; terminal
tables can wrap or truncate custom metrics.

## Public execution evidence

No credentials are used for public Polymarket discovery or market/book capture:

```bash
./synch.sh evidence capture-discovery <series-id> <target-utc>
./synch.sh evidence capture-market <market-id>
./synch.sh evidence promote .qcrl/execution_truth/raw/<artifact>.json
./synch.sh evidence verify
```

Capture writes ignored local evidence. Promotion is a deliberate decision that
revalidates and copies an immutable artifact into
`evidence/polymarket/live/raw/`; it does not automatically edit the inventory.
Add the new artifact's role and limitations to `inventory.json`, then run
`evidence verify`. Verification requires every tracked raw artifact to be
declared and every declaration to exist, hash correctly, and replay offline.

To exercise offline taker mechanics, run:

```bash
./synch.sh evidence replay execution_truth/specs/synthetic_taker_replay.json
./synch.sh evidence replay execution_truth/specs/daily_taker_replay.json
```

These commands print JSON without network access or file writes. The first
demonstrates fills; the second demonstrates the live capture's missing delay
metadata. See [TAKER_REPLAY.md](TAKER_REPLAY.md) for expected results.

## Interpreting campaign state

- `pending`: not submitted.
- `completed`: cloud backtest completed but may still require collection.
- `collected`: authoritative QCRL metrics stored locally.
- `failed`: compilation/runtime/submission exhausted its policy.
- `incomplete` or `uncollected`: evidence is not ready for a verdict.

Do not analyze until expected, failed, incomplete, uncollected, and pair/cohort
checks are reconciled. A new campaign is not “done” merely because cloud runs
finished.

## Rate limits and retries

Campaign submission is sequential and rate-aware. Recognized rate limits use
the manifest/default backoff policy; ordinary compilation or runtime failures
stop rather than being disguised as throttling. Use `--retry-failed` only after
the cause is understood or rate retries are exhausted.

QuantConnect syntax-checker warnings about `getattr` or guarded `try/except`
are advisory when builds and deterministic tests pass. Track them as technical
debt, but do not refactor persistence/report compatibility during a scientific
campaign without a separate tested change.

## Pull and recovery

Use `./synch.sh pull` only when the intended source really is QuantConnect. It
requires a clean tree and creates a recovery branch before replacing local
content. After pulling, inspect the diff and run tests before committing. Do
not use pull as a routine round trip when local Git is authoritative.

## Prospective lock

The 2026Q4 prospective campaign is declared and locked. Do not execute it
partially, edit it, or inspect interim evidence. It may be run and evaluated
only after its declared window ends on 2026-12-31.

## End-of-session reconciliation

1. Validate all executed campaigns and syntheses.
2. Update campaign, hypothesis, and decision registries.
3. Update `QCRL_PROJECT_STATUS.md` if current truth changed.
4. Append a dated provenance block to `QCRL_SYNC.md`.
5. Run deterministic tests and whitespace checks.
6. Commit, push GitHub, then push the committed project to QuantConnect if
   cloud execution needs the documentation/code revision.
