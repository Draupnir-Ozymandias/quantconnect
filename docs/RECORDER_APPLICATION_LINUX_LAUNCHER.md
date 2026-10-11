# Private Linux launcher and independent audit

The preregistration remains `c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade`.
No recording workload, budget, sync cadence or legacy recorder changed.

`infra.stream.recorder_application_launch` is a finite six-case launcher for a
fresh canonical `/var/lib/qcrl-stream/recorder-application-<alphanumeric>` stage.
It requires root, the fixed `/opt/qcrl-stream/venv/bin/python`, a clean qcrl-owned
private Git checkout at `stage/source`, tracked frozen files and >4 GiB free.
It refuses an existing evidence directory, claim/inventory or private unit prefix.

Required staged files:

- Original preregistration JSON, validated against its exact source/input hashes.
- Exclusively published execution freeze from `freeze(declaration, commit)`,
  binding the source commit, full stream/recording implementation inventory,
  fixture/test sources, Python/platform and WebSocket version. A freeze is not
  execution authority or proof of a successful native smoke.
- Host context with region, instance ID/type, credit mode and retained raw EC2
  describe-instance/credit-specification responses, an instance-identity document
  and a matching native boot ID. The independent auditor also
  requires a separate external byte anchor for this context. These are operator-
  retained AWS evidence, not authenticated API responses merely because hashed.
- Source-bound `qcrl.recorder_application_native_compatibility.v1` audit with
  `compatibility_verified=true`. No such receipt was generated in this turn.
  The compatibility smoke and its independent audit remain the next gate.

No `--execute` means no launch. A native compatibility receipt and explicit
execution are both required before this launcher can run the six cases. The
private preparation/producer/consumer worker CLI similarly requires `--execute`.

## Isolation and lifecycle

Tests and both case roles use qcrl units with 75% CPU, 512 MiB memory, 32 tasks,
240-second runtime, no new privileges, private temporary directories and strict
system/home protection. The private source is read-only, only evidence is writable,
and public collector environment files are inaccessible. Units restrict address
families to AF_UNIX/AF_INET and IP access to 127.0.0.1/32. Native support/enforcement
of these systemd restrictions must be checked in the compatibility smoke; no
unsupported-property fallback or widening is implemented.

The launcher independently queries systemd and reads live `/proc`/cgroup state to
bind each actor's PID/starttime/boot/membership before the send epoch. The producer
waits for both worker readiness and the launcher's exclusive binding release.
Late readiness fails rather than shifting or adopting an epoch. Producer/recorder
remain in distinct groups; resource observation stays inside recorder cost.

The launcher runs prerequisite tests, then the declared six cases serially. It
captures properties and journals before stopping its own transient units. Failures
preserve prefixes, launch status and a byte inventory; there is no case replay,
automatic replacement or attempt to repair public-state drift. Cleanup targets
only units submitted by this fresh launch. Failure to capture/stop is retained.
Host process snapshots disclose shared-host concurrency without claiming isolation.

## Independent read-only audit

`infra.stream.recorder_application_audit` requires caller-provided origin inventory,
source commit and separate host-context byte anchors learned independently from
the origin/retained AWS context. It reuses the existing exact-population byte-
inventory verifier unchanged; the inventory's legacy generic format is retained.
It verifies frozen source/runtime/plan bindings, public before/after state, all
13 units' actual limits/security/commands/exit properties, native lifetimes and
independent live actor bindings, readiness release, serial lifecycle ordering,
producer/completion/barrier/resource timestamps and cross-group separation.

The offline component audit then rescans ordered raw occurrences and applies the
unchanged timing/stimulus/resource gates. Only after the independent audit passes
its binding checks can it remove the component auditor's missing-independent-
binding marker. All other unknowns and known failures remain. A localhost budget
pass is not public-rollout acceptance, venue completeness or order authority.
Origin population/bytes are checked again after all analysis. Offline output must
be outside the sealed originating evidence tree.

An incomplete/invalid native launch is rejected by the independent verifier; its
component/failure-prefix audit remains available for diagnostic known failures and
unknowns. No launcher success flag alone establishes acceptance. Runtime dependency
versions are frozen/disclosed; platform-specific unit-property serialization that
is not explicitly supported is rejected rather than guessed.

## Tonight's stopping point

All **968 local regression tests passed** in 40.348 seconds. The final focused
launcher/auditor run passed eight tests after the host-context and post-launch
drift checks were tightened. Tests cover exact six-case/13-unit ordering, fixed
limits and loopback isolation, prerequisite/live-binding/capture failures,
preservation and scoped cleanup, public drift without restoration, native unit
command/property tampering, live PID/group/epoch mismatches, raw credit-context
consistency and externally anchored origin population changes. Launcher lifecycle
tests are mocked; no actual Linux/systemd deployment or native happy-path audit
was performed. The saved preregistration and six frozen recorder sources remain
byte-for-byte unchanged.

Launcher/auditor code and local lifecycle/fault tests only. No Linux deployment,
compatibility receipt, performance cohort, public capture, infrastructure/resource
change, trading or QuantConnect sync. After commit/push, stop. Tomorrow: source-
freeze the committed checkout and perform the isolated native compatibility smoke;
review its evidence before authorizing the finite cohort.
