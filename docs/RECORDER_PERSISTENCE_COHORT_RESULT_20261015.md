# Successor cohort result — stopped at Linux readiness

**Launch failed at its prerequisite gate; zero cohort cases ran.** The single
approved controller invoked one readiness unit. That unit was killed by a memory-
cgroup OOM under its unchanged configured 512-MiB limit. The controller preserved
evidence and stopped before preparing or starting any case. No retry, replay,
replacement, extra smoke, extra case, tuning or resource change followed.

The independent frozen auditor reports `complete=false`, `verdict=fail`,
`application_budget_pass=false`. This is a failed prerequisite/launch, not a
measured application-budget failure in six workloads. All six workload outcomes
remain unavailable. The passing 68-occurrence smoke, earlier failed smoke/cohort,
original declarations and thresholds remain unchanged.

## Approved identity and actual scope

- Candidate: `8c726522a7ba9b19411d309b42d17a92faf72395` (516 selected source files).
- Freeze: `90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686`.
- Approval packet: `e9805de66fb3eb939ad7c5ad57b7820625ba731e30c4e0f68679092834d073c5`.
- Fresh stage: `/var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort01`.
- Controller: one invocation, PID 1492498. Readiness PID: 1492531.

The interrupted AWS sign-in affected staging only. After access was restored,
inspection found only the complete base64 packet, with no extraction, source,
controller marker, claim, evidence or unit. The approved archive SHA matched;
exclusive six-member extraction and exact detached checkout then completed.
Full source/control/lineage/runtime/public/namespace preflight passed before the
single controller invocation. No prior launch was adopted or repeated.

Fresh operator read-only AWS responses at 22:31:04 UTC confirmed the existing
Ohio t4g.small/standard configuration. The latest returned CPUCreditBalance was
576 at 22:26 UTC. It remains dated context, with no minimum balance gate or claim
of continuous credit coverage. Raw response file SHA-256:
`fe6bdba3a5b82ee4be4d1e7d8587aff002cbdd4e6368a79bf8a48517a31d2556`.

## Native readiness failure

| Retained check | Result |
| --- | --- |
| Actual readiness command | Fixed `/opt/qcrl-stream/venv/bin/python -m unittest discover -s tests -q` |
| Expected population | 1,169 total, 1,168 pass plus one existing Python 3.9 skip; **not completed/verified** |
| Actual unit result | `Result=oom-kill`, `ExecMainCode=2`, `ExecMainStatus=9` |
| Unit lifetime | 148.369297 s, from retained systemd monotonic start/exit properties |
| Whole readiness-unit CPU | 101.731637 s, including startup/test work; not recorder/observer overhead |
| Memory limit | 536,870,912 bytes, unchanged; actual retained limit/security properties verify |
| Runtime ceiling | 240 s, unchanged; this was an OOM kill before that ceiling, not a timeout |
| Continuous peak / MemoryPeak | Unavailable; no continuous RSS peak established |
| Cases prepared / started / completed | 0 / 0 / 0 |
| Preserving/cleanup errors | None reported by the controller |

The journal records the OOM-killed readiness process and no final `Ran ...` /
`OK (skipped=...)` summary. The expected total, individual native pass count and
native skip observation cannot be inferred from the local suite or partial log.
An earlier CLI usage/error line is an expected negative-test output and does not
identify the later active test. The quiet journal does not name the test or
allocation active at the kill; that remains unknown.

A subsequent **read-only existing kernel-journal supplement** identifies
`constraint=CONSTRAINT_MEMCG`, the readiness unit's exact `oom_memcg` /
`task_memcg` path and killed PID 1492531. This supports a memory-cgroup OOM
attribution. The supplement is separately byte-anchored outside the already sealed
origin inventory; it does not replace or rewrite the original unit evidence.
Kernel kill-time process RSS fields are not continuous unit RSS or the recorder's
sampled-RSS acceptance evidence. No additional runtime observer was introduced.

The earlier **1,169 passing offline tests in 152.925 s** used Intel macOS/Python
3.14.6. That local success did not establish success under the installed Linux
Python 3.9.25/aarch64 readiness unit's memory envelope. No native rerun, reduced
test population, skip addition, memory increase or timeout increase was attempted.

## Independent audit, completeness and unknowns

The locally reconstructed ten-file originating evidence population matches every
externally anchored origin byte/hash. The transfer archive and exact freeze/host
controls verify. The frozen auditor's output is retained without changing its
false origin/authority flags. A separate operator observation review records the
Session Manager provenance and before/after checks.

The auditor retains the known `incomplete_native_launch` failure and these seven
unknowns: `independent_unit_binding_incomplete`, plus component-unavailable entries
for steady-0, mixed-0, mixed-1, steady-1, steady-2 and mixed-2. Each missing case is
unrun; none is silently passed, substituted or assigned a measured budget failure.
Independent retained-property review additionally verifies the readiness unit's
fixed limits/security and documents its failed exit and lifetime.

There are **no workload archives or per-frame witnesses to audit**. Integrity of
the sealed readiness evidence passes; ordered 360,000-occurrence archive integrity,
stimulus attainment, append/durability/UTC gates, all nine recorder CPU windows,
RSS coverage and missed observer slots are unavailable because collection never
started. Report no zero-miss or resource-budget pass. The only CPU accounting
above belongs to the prerequisite unit. Incremental observer overhead, continuous
RSS peak and continuous credit balance remain unknown, not acceptance claims.

Final read-only checks confirm the exact source/runtime freeze and public state
unchanged, no case directories and **no running scoped units**. The stopped test
unit remains loaded in `failed` state with `MainPID=0`; it was not reset or deleted
to erase its failure. No public collector, source/environment, IAM, infrastructure
or resource setting changed. The controller retains no preservation errors.

## Evidence anchors and stopping point

Private review:
`.qcrl/reviews/recorder-cohort-native-20261015LupusCohort01/`.
Raw evidence, journal supplement and transport controls remain private.

- Outcome archive: 6,852 bytes; SHA-256 `d00a9c5d779833d52903df7c6bf2d1f90eaf438c2f45e9664e967961422e7989`.
- Origin inventory file: `cecf507d600922c359a838fc7f889182e6fe0ff5104e5bcbc5ce9cc09df1ddb8`.
- Independent audit file: `dbbad8a92853db3afd3f39f5fdef3edb52ddba2d8c64670efc2dbfb3af229337`.
- Controller-start file: `6b5cf0b8773efeb334b9df2360db54f5f444e6854a93d618a3884e30cac1f148`.
- Separate observed-origin review payload: `1a6ef3c62bd871569e8e3c5b3d5a7bc0d5cf56237d381d85b0fbb7ccbad23eea`.
- Separate kernel supplement: 9,803 bytes; SHA-256 `b9d3863490a8cf395a943e199e16f3ae6e5cfdf04b3aa763c36889c7eea34b0b`.
- Kernel supplement review payload: `64587944db15cb784abe4482feea7463e5ac8e4e2d12b697c30e170cfce4a4eb`.

An initial local transfer copy was rejected by its checksum because rolling
terminal history repeated older chunks. It remains retained as a rejected copy.
Offset-labelled transfer then matched the external origin anchor exactly. This
was evidence transport only; native work was not repeated and originating bytes
were unchanged.

Stop here. The approved attempt is spent. Next work, if requested, is offline
memory/lifetime analysis of the frozen readiness path and a prospective fix within
the existing limits. Do not guess the active test, waive the failure, reduce
required coverage, alter budgets/resources or launch a replacement under this
identity. No further native execution, main merge, public rollout or QC sync is
authorized by this result.
