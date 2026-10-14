# Development handoff

Updated October 14, 2026. Continue in
`/Users/eric/Projects/quantconnect/polymarket-martingale` on
`codex/lupus-development`. The Intel migration base is `f05d5dd`; use Git history
for subsequent development revisions. Keep this branch separate from main.

## Current execution gate — October 14

One operator-authorized bounded Linux compatibility attempt is complete.
Source/runtime freeze
`8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`
binds implementation commit `2cb688039f1b0c0bf4bae4f783902759aa263aef`
and its original 488-file inventory. The Linux regression gate and both declared
compatibility waits succeeded; separate offline receipt/origin checks passed.
Both private units are stopped; public/source/runtime state is unchanged.
The one-attempt authorization is consumed. No scheduling comparison, recorder
cohort, replay or additional native run is authorized. The source candidate and
all historical evidence remain fixed across subsequent documentation commits.

## Current scientific status

The independently audited October 12 Linux clock-only diagnostic retained 11
observed wakes and one missed target. The 60-second waits returned approximately
59–60 ms late. Select-related slack is a post-hoc mechanism hypothesis, not proof
about the installed runtime or an exclusive cause. Measurement completeness and
performance acceptance remain false. The earlier counter smoke's final endpoint
missed the fixed deadline before any counter read. Preserve both failures and
the original 50-ms budget.

The absolute-monotonic adapter has now passed the single native interface smoke;
recorder integration and scheduling performance remain unverified. The active
prospective comparison is now
[ABSOLUTE_SELECT_COMPARISON_V2.md](ABSOLUTE_SELECT_COMPARISON_V2.md), with plan hash
`c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d`.
V2 preserves two serial 133.3-second AB/BA runs and integer targets while allowing
one Python select call with disclosed runtime retries and unknown internal count.
The predecessor
[ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md](ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md)
and its hash `a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`
remain retained; v1 has no native result. Both hashes have literal regression pins.
Injected select/absolute collection, pair lifecycle, validation, exact descriptive
evaluation and bounded exclusive publication now exist. No native runner exists.

## Verification and migration

The migration receipt records 598 retained evidence files, with no imported
jobs/secrets or cloud-sync authorization. The operator reported all 1,034
bootstrap tests passed on Intel macOS / Python 3.14.6. Migration selection is
curated; omitted historical evidence remains on the originating machine.

After comparison preparation, all 1,037 local offline regression tests passed
in 92.808 seconds, including localhost fixtures. All 12 focused comparison/
absolute-wait tests passed. The new Python files pass Python 3.9 syntax parsing.
The initial restricted sandbox run could not bind localhost and was stopped;
the complete rerun with localhost permission passed. These checks do not verify
Linux ABI compatibility, native scheduling behavior or actual improvement.

## Unfinished work and continuation constraints

A finite compatibility declaration, source/runtime freeze validation and injected
launcher lifecycle rehearsal now exist; see `WAIT_EXECUTION_PREPARATION.md`.
The compatibility worker and production adapters are now implemented and tested
offline; see the production continuation below. The authorized read-only Linux
ABI/symbol, installed select-source and signal context review is complete; see the October 14 receipt below. Fresh native
preflight must match the frozen source/runtime before any further separately
authorized native execution. The single compatibility attempt below is complete.

Recorder application native compatibility and the six-case budget cohort remain
blocked. New comparison results cannot retroactively repair previous verdicts.
Frozen evidence must be audited against its originating source revisions, not
the current expanded source inventory. Preserve the source-frozen reviews and
all original measurement plans; do not edit `.qcrl/` evidence.

Keep signal feature optimization on hold, martingale closed, and the prospective
2026Q4 declaration unchanged and unexecuted until its window completes. Do not
launch captures/native experiments, provision infrastructure, import credentials,
merge into main or sync QuantConnect under this handoff. The current authorized
publication is the reviewed development branch only.

## October 13 pre-integration review

The v1 protocol hash is explicitly pinned in a regression test. The adapter now
caps complete exception text, including its name prefix, at 160 characters;
both exception paths and first-error preservation have injected regression
coverage. All 14 focused tests pass locally; the full-suite count above is from
before this repair. Python 3.9 syntax checks pass, not native runtime validation.

Upstream Python 3.9 select automatically retries signal-interrupted calls with
a recomputed timeout unless the signal handler raises. One Python call and zero
collector retries do not imply one syscall or zero internal retries. The proposed
reference therefore has an unresolved v1 execution gate: verify the exact Linux
runtime and prospectively declare a successor allowing disclosed runtime retries/
unknown counts, or separately declare a compatible reference. Preserve v1's hash;
do not silently alter its semantics. See the preregistration's October 13 review.

## October 13 v2 offline implementation milestone

Prospectively resolved the retry contract with a new v2 identity; neither v1 nor
its evidence was replaced. Zero application retries and unknown select-internal
retry counts are separate fields. Exposed faults cancel remaining attempts;
missed targets stay unknown and later original slots continue. The evaluator
preserves unknown pairs and reports rational medians without changing acceptance.
Publication is exclusive and byte-bounded; it does not claim atomicity/fsync or
native process-kill recovery. Thirty focused tests and all 1,055 local offline regression tests passed
(91.860 seconds for the full suite, with localhost fixtures). New v2 files pass
Python 3.9 syntax parsing. No Linux validation, native binding or scheduling run.

Primary development may continue offline implementation, tests, documentation
and reviewed development-branch commits/pushes without consulting another chat.
Surface material design decisions, blockers and actions outside this scope.
Native execution, main merges and QC sync remain unauthorized.

## October 13 compatibility-envelope preparation

Added compatibility plan hash
`aec6f48ff1558e544cf68665c062126ce5b44366bf8c7e9e0d18ac82268fd864`, pinned in tests.
It declares one select then one absolute wait on a 50-ms cumulative grid, without
signal injection or performance acceptance. Broad tracked-source hashing excludes
evidence/dot paths/credential scripts and refuses symlinks/oversize files. The
freeze validates LP64 timespec offsets, exact interface metadata, installed-binary
and source-review receipt hashes, positive clock resolution and read-only signal
context. No actual Linux runtime receipt or execution freeze was generated.

Injected lifecycle tests cover fresh claims, serial tests/compatibility, bounded
readiness/unit/result/journal interfaces, active binding before release, private
cleanup and public/source drift. Unit specifications have no worker entrypoint;
no production launcher or native worker is available. Thirty-eight focused local
tests and all 1,063 offline regression tests passed (85.739 seconds, localhost
fixtures permitted); Python 3.9 syntax checks passed for the new files.
Native verification and process-kill/host-loss evidence retention remain pending.

## Compatibility worker and production-adapter milestone

The worker now retains both arm slots and failed setup/interruption/missed-target
states, publishes bounded exclusive durable controls/results, and requires native
source/runtime match plus independently bound release. It installs no signal
handlers and cannot retry. The production root-Linux entrypoint runs only the
private regression-test and declared two-wait compatibility roles, with fixed
unit limits, no measurement-network access and private-only cleanup. Helper
output/deadlines, effective properties, live identities, partial journals and
final origin inventories have offline fault coverage. No new diagnostic layer.

A concrete receipt-validation gap was repaired: non-null collector/fatal errors
cannot pass even if adapter observations are marked observed. A built-in-select
fixture also required recording reviewed binary kind and hashing its actual
Python backing binary. Original compatibility/v1/v2 plan hashes are unchanged.

The source candidate will be sealed from the clean published implementation
revision under `.qcrl/reviews/wait-compatibility-source-COMMIT12/source-freeze.json`.
This is source-only: runtime remains unfrozen pending authorized read-only access
to the existing Ohio host and independent installed-binary/source review. The
full execution freeze must bind this exact source inventory and the verified
Linux runtime; no Mac/fixture runtime may substitute. Remote inspection permission
is pending. Afterward report readiness and request separate native authorization
for one compatibility smoke only; the v2 comparison remains unauthorized.

Offline readiness: the worker, production adapters and final copy/output
safeguards pass 53 focused tests. Complete exception/collector failure states,
release/setup/drift paths, effective property checks, bounded helper failures,
partial journals/source copies and exclusive claims have regression coverage.
No compatibility wait syscalls, native unit or remote inspection was performed.
The read-only remote authorization question remains pending; without installed
binary/source review the Linux runtime freeze and smoke execution readiness
cannot be claimed. The source-only candidate receipt will identify the exact
clean published commit. Full regression counts are in the preparation document.

Final verification for this milestone: all 1,078 offline tests passed in 72.261
seconds on Intel macOS / Python 3.14.6 with localhost fixtures permitted. All 53
focused tests and Python 3.9 syntax checks passed. The implementation is ready
for source-candidate sealing and authorized read-only Linux runtime inspection;
full source/runtime freeze and native-smoke execution readiness are still gated
on that installed-runtime review. No smoke authorization is implied.

## October 14 — SSH authorized; connection method still needed

The operator explicitly authorized read-only SSH inspection of the existing Ohio
host. This does not authorize native smoke/comparison units, infrastructure or
credential import. Local access checks found no documented QCRL identity file,
no SSH configuration, no identities in the existing agent, and no saved host pin
for the recorded historical Ohio address. Only an older default AWS profile is
present; it was not used to substitute for the documented scoped access. No EC2
connection, remote command, AWS API request or access-rule change was attempted.

The blocker is now the available approved connection method, not SSH permission.
Requested an existing host alias/key path or confirmation that access remains on
the original Mac. Do not copy credentials from the migration package, use unknown
legacy AWS credentials, bypass host verification or change ingress implicitly.
After a method is supplied, verify the current destination and pinned identity
before read-only installed-runtime/source review. Native execution still requires
separate authorization after the full freeze is complete.

The existing source-only receipt has been rechecked and remains bound to
`2cb688039f1b0c0bf4bae4f783902759aa263aef` (488 selected files; source seal
`9a9a36efb5fc986de8a3cffeb96712235acb66d6ad90616bad89cabf4e6c4f34`).
Its path is `.qcrl/reviews/wait-compatibility-source-2cb688039f1b/source-freeze.json`.
This documentation continuation does not replace that candidate or its evidence;
use its exact frozen checkout for runtime binding. Runtime remains unfrozen.

## October 14 — Dedicated Lupus SSH key generated

Operator explicitly authorized generating a new dedicated Ed25519 key and adding
its public half to ec2-user's authorized_keys. Generated
`/Users/eric/.ssh/qcrl_lupus_ed25519` without replacing an existing file; private
mode is 600, public mode 644. Public fingerprint:
`SHA256:ld+08VAeLSi1eLAzpKuwkTjnhUFFl7TtaRPIBmT3FDc` (comment `qcrl-lupus`).
Private material remains in ~/.ssh, outside the project/Git; none was imported.

A BatchMode/IdentitiesOnly/StrictHostKeyChecking=yes connection to the explicitly
provided Ohio address reached SSH but refused the unknown ED25519 host key before
authentication or remote command execution. No host key was accepted implicitly.
There is still no other local SSH-agent identity for bootstrapping installation.
The next access step is an existing authenticated ec2-user session adding only
the new public key and returning the trusted server public host key. Public-key
installation is authorized; changing ingress/infrastructure or running native
smoke/comparison units is not. Source candidate and prior evidence are unchanged;
runtime review remains pending authenticated access.

## October 14 — Read-only Linux review and full freeze complete

Used the operator-approved AdministratorAccess console session for Session Manager
on the existing Ohio collector. Automatic approval review initially blocked that
broad role; the operator explicitly approved its use solely for this inspection.
No IAM, ingress, infrastructure, services, packages or remote files were changed.
No credentials were imported. The dedicated SSH key remains local and uninstalled;
Session Manager supplied the needed access without changing SSH authentication.

Observed aarch64 Linux kernel `6.18.51-120.163.amzn2023.aarch64`, glibc 2.34,
GIL-enabled Python 3.9.25, 64-bit pointers/long, 16-byte timespec with offsets 0/8,
CLOCK_MONOTONIC 1 and resolution 1e-09. Bound the declared clock_nanosleep
signature without calling it. Existing handlers were observed without changes.
Python/libc/select file hashes matched their installed RPM SHA-256 manifests;
repeat hashes, boot identity and public service states were unchanged. The public
collector timer remained active/waiting and pilot/observer inactive/dead.

Fetched the exact release's official Amazon Linux source and python3-libs RPMs
locally over verified TLS, checked repository metadata/package hashes, and matched
the extracted official select extension byte for byte to the installed extension.
Reviewed the matching SRPM spec and all 43 declared patches: none changes
selectmodule.c. The retained C source confirms select's EINTR retry after checking
Python signals, with remaining timeout recomputed from a monotonic deadline;
a raising handler propagates. Runtime retries remain disclosed and uncounted.
This establishes package/source provenance, not a reproducible build or independent
RPM signature verification, and does not establish a cause of historical lateness.

Private evidence is retained under
`.qcrl/reviews/wait-runtime-20261014-jlwy2fu9/`: linux-observation.json (transcribed
from visible console output), runtime-review.json, select-review-source.c,
execution-freeze.json, official repository/RPM inputs and review-inventory.json.
Runtime-review hash:
`359b2b60db756b43ea21340b8434163abbeba13c2c15bbaf24ccd94d96ec7a9d`.
Execution-freeze hash:
`8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`.
Review inventory hash:
`4215b012370a33fa49e0ea7e1242bf040906be06e221574f2e742a0d92264843`.
The original source-only receipt and migration/frozen scientific evidence remain
unchanged; every one of the 488 source hashes was checked against exact commit
2cb6880. Current Python implementation bytes also match that candidate.

Readiness is for one separately authorized compatibility attempt: stage a fresh
private copy of exact 2cb6880 plus these controls; verify source/runtime, qcrl
ownership, disk reserve, absent private units and unchanged public prerequisites;
run the bounded Linux regression unit, then only if it passes run the declared
select/absolute compatibility unit. Limits remain CPU 75%, memory 512 MiB,
32 tasks and 240 seconds per unit. Retain readiness, release, effective properties,
journals, failures and origin inventory; no retry/replay. Audit independently
before claiming native compatibility. Staging and execution have not begun.
The AB/BA scheduling comparison and recorder budget cohort remain unauthorized.
No new diagnostic layer or protocol revision was introduced.

Local verification remains 1,078 passing offline tests on Intel macOS/Python
3.14.6, including 53 focused tests and Python 3.9 syntax checks. Linux runtime
metadata/source inspection is now real evidence; Linux tests, unit enforcement,
compatibility behavior, scheduling improvement and performance acceptance remain
unverified. All freeze execution/native/compatibility/acceptance/order flags stay
false. Request native authorization before staging or starting the finite attempt.

This review continuation reran all 53 focused offline tests successfully in 0.403
seconds and verified freeze/review hashes plus all 67 inventoried evidence files.
The full 1,078-test result above is the preceding implementation milestone, not
a new Linux or full-suite run. Documentation diff and append-only sync checks pass.

## October 14 — Authorized single native compatibility smoke passed

The operator approved fresh staging and the bounded Linux regression unit followed
only on success by the single select/absolute compatibility unit. Used the existing
Ohio host through Session Manager. No infrastructure, IAM, SSH, package or public
collector changes. Created only the fresh private stage
`/var/lib/qcrl-stream/recorder-wait-20261014Lupus01`. Anonymous partial Git clone and
sparse checkout bound exact 2cb6880 while excluding poly.py/poly2.py; no credentials
were imported. Reviewed source/control bytes and live source/runtime reproduced the
exact existing execution-freeze hash. Fresh staging/live preflight checks passed.

The declared production launcher ran once. The qcrl Linux regression unit discovered
1,078 tests in 105.240 seconds: 1,077 passed and one was skipped. The skipped test
is SyncContractTests.test_tracked_python_files_do_not_shadow_standard_library_modules,
whose frozen guard requires sys.stdlib_module_names (Python 3.10+). This reason
was identified from the frozen guard, not a verbose rerun. All pinned WebSocket
fixture gates were available. This is real Linux regression evidence, distinct
from the preceding 1,078 passing local Mac tests.

After success, the compatibility unit produced independent readiness/live binding
and hash-linked release, then observed exactly select at epoch+50 ms and absolute
at epoch+100 ms. Both returned code 0 with no errors and zero application retries.
Select's internal retry count remains unknown. Retained signed lateness was
185,322 ns (select) and 128,759 ns (absolute). These single short waits establish
interface compatibility only; their difference is not scheduling improvement or
an explanation of the historical 60-second lateness. No signal injection/handler
change or retry/replay occurred, and no AB/BA comparison was launched.

Captured effective properties match CPU 75%, memory 512 MiB, 32 tasks and runtime
240 seconds; the live resource sample also showed cpu.max 75000/100000 and
memory.max 536870912. Compatibility allowed AF_UNIX only, with denied IP access;
tests allowed numeric localhost. Both units exited successfully and were stopped.
Retained journals/properties/readiness/release/result and origin inventory report
no capture or preservation fault. Public collector states, environment-file hash,
public source HEAD and exact private source/runtime remained unchanged, including
a separate final read-only recheck. No public service was restored or restarted.

Remote evidence remains in the private stage. The local copy is
`.qcrl/reviews/wait-compatibility-native-20261014Lupus01/`. All twelve native evidence
files match the producer's origin inventory; identical reviewed control bytes were
copied from the existing local review and checked against those remote hashes.
The retained transfer archive contains the remaining exact native bytes, origin
inventory, staging preflight and launcher log/PID record. It is not in Git.

Compatibility result:
`a8927bd009b4218869a1fa91dd3b357017f963c5d97f1df427e9beefa03dcc0a`.
Launch receipt:
`b0816cfe7f0af3bac0ef5561eb3de6d3823ab2f777dfa32edffafa5410069171`.
Origin inventory:
`2770fc0c1313cb65f70770212f5d0076014961d8c673788c3b30ea70593e8da7`.
Separate offline native audit:
`c5f7e48f1dc97f38966a0d5c7dcd51761cf2f1f5644c09b446c018bb85f3a0cb`.
The audit checks source/runtime freeze, all byte hashes, valid integer brackets,
readiness/release/live PID/start/boot/cgroup identity, raw effective properties,
actual quota/memory context, unit completions, journals and unchanged final state.
It verifies native origin and this finite interface compatibility only. Producer
and frozen control authority flags stay unchanged; the separate audit does not
establish performance, recorder acceptance, trading or comparison execution authority.

No failing requirement demands another diagnostic layer or a protocol correction.
Next native action would require separate authorization for the preregistered v2
comparison after review of these receipts. Do not replay this stage or consume new
results under the single-smoke approval. Preserve all original declarations,
scientific failures and budgets. Continue authorized offline work on the development
branch; no main merge or QuantConnect sync.
