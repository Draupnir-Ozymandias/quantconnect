# Recorder application native smoke — 2026-10-11

## Verdict

Native compatibility is **not verified**. The Linux unit-test suite passed
968 tests (one skipped), but the following isolation smoke failed in the
resource observer before publishing its result. No loopback functional
capture or six-case performance cohort was launched. No automatic replay
was attempted; no acceptance, fill or profitability conclusion is supported.

## Frozen run and independently verified evidence

- Source: `eb9ba1c272c0b708b6f5e6b762d9096571519534`.
- Preregistration: `c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade`.
- Private Ohio stage:
  `/var/lib/qcrl-stream/recorder-application-smoke-MXbaMLFM`.
- Runtime: Linux aarch64, Python 3.9.25, websockets 15.0.1.
- Origin inventory byte hash, independently read over strict SSH before
  and after download:
  `873222e98aeeb2c9d5810b03ed98e0bce541b8ad0e3a83e1262ac61aee43d717`.
- Local ignored review:
  `.qcrl/reviews/application-native-smoke-20261011-57dVZwah/`.

The downloaded archive's names and member types were checked before
extraction. Its exact file population and hashes, execution/source freeze,
and copied smoke harness bytes were independently verified. The test unit's
actual command, successful exit, fixed limits and isolation properties were
verified from retained systemd properties and journal. The suite reported
968 tests in 95.915 seconds, `OK (skipped=1)`.

## Failure and limitations

`LinuxReader.read()` attempted to open
`/sys/fs/cgroup/system.slice/qcrl-app-smoke-MXbaMLFM-isolation.service/cpuset.cpus.effective`
and raised `FileNotFoundError`. The isolation unit exited with status 1.
It published no isolation-result artifact, so attempted access denials are
**not independently verified**, even though the unit properties retain the
intended restrictions. No compatibility-success receipt was issued.

Read-only host diagnostics showed root `cgroup.controllers` includes
`cpuset`, but root `cgroup.subtree_control` enables only `cpu io memory pids`.
`system.slice` exposes/enables the same four controllers and lacks
`cpuset.cpus.effective`. Root's effective CPU set was `0-1`. The reader's
assumption that every ancestor exposes the cpuset file is therefore
incompatible with this observed host hierarchy. No controllers, quotas,
resource limits or global systemd configuration were changed.

The failed transient unit remains retained as failed/inactive for inspection;
it is not running. Submitted units were stopped by the scoped driver.
Evidence is retained remotely and locally. The initial SCP staging failure
was precollection: a restrictive collector ancestor blocked ec2-user access.
Upload was moved to a fresh temporary directory without broadening ancestor
permissions; the private source checkout was verified clean before launch.

Public HEAD remained `4dd60ba168180243f8600860330dc1afc4816ff4`;
public environment SHA-256 remained
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
The collector timer remained active, with pilot and observer services inactive.
No public collector deployment, trading credentials, trades, QC sync,
commit or push occurred during this run. The separately approved SSH-only
CloudFormation rotation is recorded in `infra/aws/OPERATOR_NETWORK_ACCESS.md`.

## Next decision

Repair the resource observer offline to handle genuinely absent child cpuset
controllers using explicit, verifiable hierarchy semantics—not a fabricated
CPU count or changed host controllers. Add missing-controller and malformed
hierarchy fixtures, preserve unknown/fail-closed cases, then commit/source-freeze
and authorize a **fresh** native smoke. Only independently verified native
compatibility should unlock the preregistered six-case cohort. Policy, workload
and acceptance budgets remain unchanged.
