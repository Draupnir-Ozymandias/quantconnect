# Compact worker machinery — local and Linux verification

Separate candidate modules now exist:

- `receive_loop_compact_trial.py`: exclusive staged worker receipt, fixed
  producer/baseline/compact consumer, raw occurrence/archive/encoding/sideband
  verification, unchanged pairwise gates and explicit worker execution barrier.
- `receive_loop_compact_launch.py`: strict fresh compact-only stage and unit
  namespace, qcrl checkout ownership/Git access, fixed resource/security limits,
  full test prerequisite, six-case ordering, journal/property preservation,
  private-only cleanup and originating byte inventory.
- `receive_loop_compact_audit.py`: independently supplied inventory-file SHA
  and source commit, exact file population, unit/boot/PID/cgroup/limit/exit/window
  checks, public-state preservation and independently recomputed case metrics.

Original reference modules, rejected cohort artifacts, the frozen recorder and
compact preregistration are unchanged. Compact schemas are distinct; candidate
measurements are not relabeled reference evidence. The implementation receipt
records available machinery separately from the offline preregistration's
historical implementation/authority flags. Neither grants implicit execution.

Raw delivery persistence precedes sideband snapshot outside the unchanged timed
window. Snapshot failure retains all raw deliveries plus explicit measurement/
failure receipts. A failure receipt blocks a successful case audit; replay is
refused. Cleanup attempts receiver join even after a close exception. The
launcher checks qcrl source ownership to avoid repeating the reference cohort's
root-owned Git checkout failure. It never alters global Git trust configuration.

## Verification completed

**30 new local tests passed**, including tiny separate-process localhost workers,
snapshot failure with all eight test deliveries retained, single-use refusal,
CLI execution barriers, ownership rejection, six-case mocked launcher ordering,
failure/drift/capture cleanup and synthetic independently anchored resource/
origin checks. **709 complete local tests passed** on Python 3.14.6.

These are test-only reduced workloads and mocked systemd/resource records, not
real cohort runs or evidence of overhead acceptance. They do not replace Linux
runtime verification or actual origin/resource audit of a future cohort.

A fresh offline stage using the actual frozen corpus/preregistration was validated:
`.qcrl/reviews/compact-worker-preparation-20261009-zm94vgku/`.
It retains staged inputs, receipt, file-byte hashes and all 65 bound source files.
The stream specification has exactly 30,000 deliveries and binds the new worker
implementation identity. No producer, consumer or Linux unit was started by staging.

- Preregistration: `c909b91e94413bc2f5a0bcc34f14b328bd4ed76d5258cde6168d05e4db224e8e`.
- Implementation: `b303e740d756fa3071bf69f2697cd58f10c1777adca951d6b01abc8d7f545f87`.
- Preparation: `9115b2510074891d41d80d2440f590049fdf1d26aeef826fcd3c73c785459f9a`.

Candidate module byte hashes:

- Worker: `5ee463321240ed145db2eb25761ab5bc6d301027e1de562307777d3918e40ff8`.
- Launcher: `a78ba535108cfa3bc289257aa803b8a1f3ce807dead2a77b3f8147fef311b833`.
- Auditor: `004757b4efaa2adb62ca925ee708eece6408571fe8c27dc56bf7769ccd7c7d19`.

## Remaining gate

Two strict SSH attempts to the previously verified Ohio host `18.191.254.242`
timed out before connection. No remote tests, deployment or configuration changes
occurred. A read-only Docker fallback check found no running local daemon.
Linux verification of this new machinery has NOT passed or run; earlier Linux
passes covered prior stages only. Network/VPN/SSH access needs attention; this
observation alone does not establish which component caused the timeout.

Changes remain local and uncommitted at this handoff. Resume by restoring verified
SSH access, testing the candidate in a fresh isolated Linux checkout and comparing
source hashes. Then commit/source-freeze the machinery before staging any approved
finite cohort. No firewall, trust, resource, timer, collector, trading, GitHub or
QuantConnect changes were made in this step. No real six-case cohort ran.

## Follow-up: access restored and Linux verification completed

The operator approved a CloudFormation-managed rotation of Ohio's sole SSH
source from `71.104.111.76/32` to `64.246.159.39/32`, TCP/22 only. The standard
change set `qcrl-ssh-network-20261009-6424615939` modified only
`CollectorSecurityGroup`, with replacement false; stack status reached
`UPDATE_COMPLETE`. All other template/parameter values were retained. The
Ohio instance remained `i-039c11d5ea49cf413` at `18.191.254.242`; no Dublin
change, instance replacement, collector restart or deployment occurred.

Existing strict SSH host verification succeeded. **60 candidate Linux tests
passed** on Python 3.9.25 in a fresh temporary checkout
`/tmp/qcrl-compact-machinery-Ta6cMi`, including tiny localhost worker fixtures
and mocked launcher/audit tests. The three module hashes above matched local
source bytes. These tests are not the actual resource-limited cohort and do
not establish overhead acceptance.

Collector environment SHA-256 remained
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily collector timer was active; pilot/observer timers were inactive. The
earlier Linux blocker and uncommitted status describe the original handoff,
not this resolved follow-up. Machinery is now ready for commit/source-freeze,
then a separately approved finite run and independent origin/resource audit.
