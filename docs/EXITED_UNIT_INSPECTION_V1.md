# Prospective exited-unit inspection v1 — October 22, 2026

Historical application **FAIL** and PreClosePub01's **partial/unresolved** outcome
remain unchanged. The frozen post-inspector and auditor both failed. Their
scripts, declarations, reports and sealed evidence are preserved; this successor
is not applied retrospectively to make either check pass.

## Correction and scope

`infra/stream/recorder_exited_unit.py` provides one reusable read-only successor
to the private packet's numeric-only post-exit counter check. No recorder,
controller, measurement operation, resource limit, acceptance threshold or
existing frozen launcher changes. There is no new observer, daemon or automatic
execution path. Future packet preparation can import this function instead of
copying the old assertion; existing packets continue to bind their original bytes.

Policy `qcrl.exited_unit_inspection.policy.v1` has SHA-256
`24898288fd05207fbfda23597c20a8ba04c56ab4f626a30b262ead55b50c4a6b`,
explicitly pinned in a regression test. Source bytes must also be included in
any future execution freeze; this policy hash alone does not bind implementation.

The caller must supply independently observed exact unit ID, InvocationID,
WorkingDirectory, complete ExecStart value, start monotonic timestamp, host boot,
original private cgroup, and both parent/child PID/start identities. InvocationID
is an explicit prospective binding requirement, not information inferred from old
receipts. Missing or malformed bindings are rejected before reads.

Two finite observation rounds require:

- The same bound invocation in an exited/dead/failed lifecycle state, MainPID zero,
  and no conflicting current cgroup binding. A running or foreign unit is rejected.
- Both original PID/start identities absent. A reused PID is recorded with its
  different start identity; it is not mistaken for the original process. A
  surviving original process rejects the observation regardless of task counters.
- The original cgroup either removed, with the mount/slice still available, or
  present and empty. Members reject the observation even with zero/unavailable
  TasksCurrent. An existing directory's device/inode identity is compared before
  and after its read and between rounds.
- Identical round observations and unchanged boot at the end. Observable restarts,
  PID changes, counter transitions, cgroup replacements or read failures remain
  unresolved; no automatic retry.

Numeric TasksCurrent must be zero. Missing, empty or `[not set]` is recorded as
**null/unknown**, preserving the original raw value. Malformed or positive values
fail the observation. Unknown is never converted to zero or used as proof of
emptiness. Result/exit status, including faults, remain in retained properties;
observing an exited failed unit does not establish scientific success.

The result binds the caller's identity input and policy with hashes and preserves
partial observations plus errors capped at 160 characters including exception
name. `exited_binding_observed` describes only this inspection. Resource
qualification remains null; `stop_authorized` is always false. No combined
acceptance badge or stop/run/cleanup command is produced.

## Bounds and limits

The Linux adapter reuses the existing bounded `command` helper for at most two
`systemctl show` reads (five seconds / 32 KiB each). It reads only selected unit
properties, boot, two process stat files and original cgroup membership; pseudo-file
reads drain short reads to EOF under a 4 KiB cap. Symlinks, malformed data,
permissions, vanished files mid-read and missing mount/slice are unresolved.
Systemctl helper failures retain the inspector's partial observations, rather
than triggering a second attempt. No journal scan or experiment is necessary.

These are read bounds, not hard real-time guarantees against a blocked filesystem.
Two equal snapshots cannot exclude an unobserved change-and-return or make a
future stop atomic. The inspector has no mutation API. Any future cleanup owner
must separately bind its action to the exact invocation under its prospectively
declared protocol; this result alone grants no cleanup authority.

## Offline validation and next use

Tests exercise the successor function through its real file-reading adapter over
temporary fixtures, with only platform/systemctl replaced. They cover active and
exited states, missing/zero/positive/malformed counters, both bound processes,
PID reuse and races, populated/empty/removed cgroups, missing mounts, symlinks,
replacement during a read, short/oversized/malformed reads, permission faults,
boot/invocation drift, partial-report hashes and retained failed exit status.
Existing actual blocked-close worker tests are also run locally.

On October 22, all **36 focused tests passed in 10.482 seconds** (20 successor
checks and 16 existing publication checks). Both new Python files also parse with
Python 3.9 grammar locally; that syntax check is not installed-runtime validation.
Private test logs: `.qcrl/reviews/exited-unit-inspection-v1/`.

This is Intel Mac offline validation, **not Linux/native validation** of this
successor. No remote command, native rerun, public capture or new packet is
authorized by this document. The useful PreClosePub01 resource-retention finding
requires no replay. A future independently justified packet can incorporate the
successor and freeze its source, but no such run is proposed automatically here.
