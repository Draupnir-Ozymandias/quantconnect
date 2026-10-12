# Curated Intel Mac migration

Use the private package, not a home-directory copy. Source comes from a complete
HEAD-history Git bundle at one clean committed revision. The packaged verifier
and bootstrap are byte-bound by `manifest.json`; compare the package archive
SHA-256 before unpacking and pass the separately supplied manifest SHA-256 to
the bootstrap. Hashes provide integrity against that external anchor, not an
independent signature or permission to execute an arbitrary downloaded script.

Included evidence: all current campaign, execution-truth and synthesis files,
plus the five October 11–12 native reviews listed in `ops/project_migration.py`.
Older bulk review directories are explicitly listed as omitted in the manifest
and remain on the originating Mac. This is not a complete evidence migration.
Archived original bytes and extracted originating trees are copied without
rewriting content. Historical audits must use their frozen source revisions,
not the latest checkout. No audit or capture is automatically rerun.

Virtual environments, Python caches, launchd configuration, temporary migrations,
SSH/AWS credential directories, environment files and operator credential
scripts are not selected. Git history and retained research records may contain
private market/account/infrastructure metadata; keep this package private and
do not add it to GitHub. The exclusions are a path-level selection policy, not
a claim to have performed a forensic secret scan of every historical archive.
Use fresh scoped credentials later, separately from this bootstrap.

The bootstrap requires standard, GIL-enabled Python 3.14.6 on Intel macOS and
an absolute **new** destination path. It clones offline from the local bundle,
checks out the frozen commit detached, sets the normal GitHub origin, restores
hash-verified evidence and creates a fresh `.venv`. It installs only the bundled
websockets 15.0.1 pure-Python wheel, with no index access, dependencies or source compilation, then
runs the complete offline test suite, including localhost fixtures. It does not
install LEAN, contact QuantConnect/AWS/Polymarket, modify power settings, copy
credentials or start jobs. The bootstrap is offline after package transfer.
The wheel SHA-256 was independently matched to the public PyPI release metadata:
`f7a866fbc1e97b5c617ee4116daaa09b722101d4a3c170c787450ba409f9736f`.

Example after copying and extracting the package:

```bash
bash bootstrap.sh /absolute/path/to/python3.14 /Users/eric/Projects/quantconnect/polymarket-martingale MANIFEST_SHA256
```

Choose that destination only if it does not already exist. Existing contents
are never overwritten or adopted. Failures retain the new partial checkout;
there is no automatic deletion or retry. If test execution is blocked by
sandbox permissions, grant the specific localhost access rather
than rerunning a migration into an existing destination. Review the retained
failure before continuing manually.

After a successful test run, open the new checkout in the spare machine's
desktop client. For continuing development, explicitly create a branch from
the frozen revision, or switch to main only after checking its identity. The
bootstrap does not fetch, merge, create a branch or push. Keep the original Mac
and evidence intact until the transferred hashes and tests are verified.

Tool verification: six migration tests passed; all 1,034 offline regression
tests passed in 43.018 seconds using the established environment. Shell syntax
and Python 3.9 verifier syntax checks passed. This is not yet verification of
the spare machine's environment; its bootstrap must run the suite there.
