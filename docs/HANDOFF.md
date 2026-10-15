# Development handoff

Updated October 15, 2026. Continue in
`/Users/eric/Projects/quantconnect/polymarket-martingale` on
`codex/lupus-development`. The Intel migration base is `f05d5dd`; use Git history
for subsequent development revisions. Keep this branch separate from main.

## October 15 — Approved cohort stopped at readiness OOM; zero cases; audit complete

One controller (PID 1492498) ran under approved candidate 8c72652 / freeze
90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686.
After sign-in, the partial stage was inspected, approved packet/source/control
bytes verified and exact 516-file/runtime/public preflight passed. Native readiness
PID 1492531 was killed by memory-cgroup OOM at 148.369297 s under unchanged
512-MiB / 240-s limits. Actual properties and the separately anchored existing
kernel journal confirm the readiness cgroup and PID. No case was prepared or
started; no replay, extra smoke, population/skip or resource change occurred.

Frozen independent audit: complete=false, verdict=fail, application_budget_pass=false.
All ten originating evidence files and external byte anchors verify. Native test
completion/count/skip, active test/allocation at kill and every unrun case's budget,
stimulus/archive/window/slot evidence remain unavailable. Continuous RSS peak and
incremental overhead remain unknown. The readiness unit's whole CPU total is
101.731637 s; it is not recorder/observer budget evidence. Unit MemoryPeak absent.

[Full result and anchors](RECORDER_PERSISTENCE_COHORT_RESULT_20261015.md).
Private evidence: `.qcrl/reviews/recorder-cohort-native-20261015LupusCohort01/`.
Source/runtime/public context remains unchanged; no scoped unit runs. The test
unit remains failed with MainPID=0; failure state was not reset. No preservation
errors reported. Fresh raw EC2 mode remains standard, latest returned balance
576 at 22:26 UTC; no minimum credit gate. Historical evidence/verdicts untouched.

**Stop: authorization spent.** No native replacement/replay, standalone smoke,
cohort, resource change, merge or QC sync. Next prospective work requires offline
memory analysis/fix and a new reviewed identity before another native attempt.
Earlier staging/pending approval sections below preserve chronology, not current
status. No implementation or threshold was changed after this failure.

## Approved cohort staging checkpoint — AWS sign-in required

The user explicitly approved the exact executable packet ("totally approved").
That approval remains valid for candidate 8c726522a7ba9b19411d309b42d17a92faf72395 /
freeze 90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686.
Fresh pre-staging runtime/boot/public/namespace checks passed. Refreshed raw AWS
responses at 20:34:54 UTC confirm unchanged t4g.small/standard context; latest
returned credit balance remains 576 at 20:29 UTC, without a minimum gate.

Created the fresh private recorder-persistence-20261015LupusCohort01 stage and
transferred all 187,056 base64 characters of the approved 140,290-byte packet,
with every offset acknowledged. The console expired during the following
extraction/checkout command attempt; no completion acknowledgement was observed.
**Inspect actual stage/extraction/source state after sign-in before any mutation.**
Do not recreate/adopt a measurement launch or blindly repeat the staging command.
No controller invocation, claim or native readiness/case unit was submitted.

Private resume checkpoint:
`.qcrl/reviews/recorder-cohort-native-20261015LupusCohort01/sign-in-required-checkpoint.json`
(payload 65cf7379778e76fc6f473c77a9a629f770b7a230139cef79d8a11f1197b9bafa).
AWS portal now requires user sign-in. Once restored, verify remote packet SHA,
all controls/516 candidate sources and full preflight, then invoke the approved
controller exactly once. Readiness remains first and unrun; no retry, replay,
extra smoke/cases or resource/public changes. Preserve partial staging evidence.
The packet's pending-approval wording below is the earlier frozen checkpoint.

## Frozen executable cohort packet — awaiting approval

Candidate `8c726522a7ba9b19411d309b42d17a92faf72395`, 516 selected source files.
Freeze `90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686`.
Approval-packet payload `e9805de66fb3eb939ad7c5ad57b7820625ba731e30c4e0f68679092834d073c5`.
Transport 140,290 bytes, SHA-256
`13d24cec0206c648702823982bda2d8d3ebe9eeac98545d579f42f2a996caa60`.
[Exact executable approval packet](RECORDER_PERSISTENCE_COHORT_APPROVAL_20261015.md)
binds fresh raw host/credit evidence, installed runtime, exact compatibility delta,
source/bundle reconstruction, command/stage, 13-unit lifecycle, unchanged schedules/
budgets and fatal-stop/audit rules. Fresh stage is recorder-persistence-
20261015LupusCohort01. Neither source staging nor native units have started.

One readiness-gated cohort only after explicit approval. Expected Linux gate:
1,169 total, 1,168 pass plus one declared version skip within unchanged 240 s.
No further smoke, retries/replay/replacement/tuning, resource/public/infrastructure/
IAM changes, credentials, merge or QC sync. Stop afterward for independent review.
The implementation candidate, not subsequent documentation-only HEADs, is frozen.

## October 15 — Successor cohort implementation and fresh host evidence complete

The completion verifier now follows each case's declared frame count, bounded to
its supported 1..60,000 corpus population. Boundary tests cover 1/2/67/68/69/70/
59,999/60,000 and missing/extra/invalid counts; actual 69- and 60,000-frame recorder
completion paths pass. Original smoke reader/evidence and failed verdicts remain
unchanged. The worker change is exactly the two-expression verifier substitution.

The new prospective six-case launcher/auditor routes persistence plus absolute
observation, retains original budgets/schedules, enforces exact readiness, live
bindings, serial lifecycle, fatal stops and scoped cleanup, and uses large producer
artifact verification. Compatibility lineage pins the original passed smoke audit
and external origin receipt, unchanged tested Python sources except the reviewed
verifier substitution, and exact installed wait/dependency/boot envelope. This is
an explicitly identified integration delta, not same-source native validation.
See [successor cohort contract](RECORDER_PERSISTENCE_COHORT.md).

Fresh read-only CloudShell DescribeInstances/DescribeInstanceCreditSpecifications
responses and Session Manager IMDS/boot/source/runtime/public observations are
retained and externally byte-anchored. Host remains Ohio t4g.small/standard, same
boot and public context. Latest returned CPUCreditBalance: 576 at 2026-10-15
19:34 UTC (query 19:39:39 UTC); no minimum balance acceptance gate. Incremental
observer overhead and continuous RSS peak remain unknown, outside the inclusive
CPU/current-RSS acceptance gates. New stage/prefix absent, free space >4 GiB.

All **1,169 offline tests pass in 152.925 s**, Intel macOS/Python 3.14.6. Exact
prospective Linux gate: 1,169 total, 1,168 pass plus one existing version skip,
within the unchanged 240-s readiness unit limit; unrun, no timeout guarantee.
Private freeze/packet preparation: `.qcrl/reviews/recorder-cohort-preparation-20261015/`.
Freeze this implementation candidate and present exact staging/one-cohort approval
before any units. No additional smoke is required or scheduled. No new native code,
case/unit, replay, infrastructure/resource/IAM change, merge or QC sync occurred.
The blocked readiness section below is the preserved pre-implementation checkpoint.

## October 15 — Six-case readiness review: blocked; no native work

Reviewed 92889b0 against the actual parent/absolute/persistence declarations and
launcher/auditor. Incremental observer overhead and continuous RSS peak are **not
acceptance gates** for this inclusive-CPU/current-RSS cohort; both remain unknown,
not passed. Prior probe-cost rejections are unchanged. Credit mode requires raw
operator-anchored EC2 instance/credit responses plus instance identity/live boot.
The October 12 raw context still verifies against its historical external anchor,
but is not fresh; October 15 smoke console context lacks required cohort fields.
Balance remains unknown; no numeric balance threshold was preregistered.

Concrete integration blockers: old six-case launcher still routes legacy workers;
successor completion uses the frozen 68-frame archive reader (offline frame 69
fails); full producer records exceed the small-control cap; no successor six-case
wait/closure/origin auditor, exact execution freeze or same-source compatibility
binding exists. Do not rename the smoke receipt or bypass that binding. Eight
existing launcher/auditor fault tests pass locally; no native validation performed.

[Readiness and single blocked packet](RECORDER_COHORT_READINESS_20261015.md) fixes
all six schedules, units, unchanged budgets and stop rules while marking absent
execution identities explicitly. This is **not yet an executable approval request**.
Private packet payload b8da8c80ef67ddfb4d24eb10517f860a7affbaeb226c9cfba3addb1e60400777.
Resolve offline integration/source/audit requirements and fresh host evidence,
then bind one final concrete approval packet. No standalone smoke is presently
justified or scheduled; another would require a concrete remaining native gate.
No cohort, units, infrastructure changes or remote mutations occurred in this review.

## October 15 — Successor Linux compatibility passes; stopped after one run

The user approved the exact successor packet below. Fresh source/runtime/boot/
public preflight passed; one controller staged and ran one readiness unit followed
by the 68-occurrence producer/recorder pair. Linux Python 3.9.25/aarch64 readiness:
1,156 tests in 112.488 s, 1,155 pass plus the declared existing version skip.
This is distinct from all 1,156 offline Intel macOS/Python 3.14.6 tests passing.

Independent frozen audit **passes bounded compatibility**: 68 ordered frames,
archive/completion integrity, all planned sends plus verified recorder completion,
no drain errors, no missing observer slots. Worst durability upper 0.183876711 s
against unchanged 2 s. Inclusive 60-s CPU upper fraction 0.0048931556; sampled RSS
max 27,553,792 bytes. One-second persistence reserve remains prospective and is
not a guarantee. Separate origin attestation preserves original self-report flags.

See [complete audit, inclusive costs, unknowns and anchors](RECORDER_PERSISTENCE_SMOKE_RESULT_20261015.md).
Private evidence: `.qcrl/reviews/recorder-persistence-native-20261015LupusPersistence01/`.
All scoped units are gone; public state/hashes and historical failed evidence are
unchanged. No retry/replay, extra run or cohort occurred. Incremental observer
overhead, continuous RSS peak, credit balance and producer internal sleep retries
remain unknown; original cohort raw host-context gates remain open. Budget/cohort
acceptance and orders remain false. Native authorization is spent: stop here;
no six-case cohort, public rollout, merge or QC sync. The following pending/unrun
sections preserve the historical preparation chronology, not the current state.

## Frozen successor approval packet — October 15 (not executed)

Implementation candidate: `371fa03c3d2622d784128b9359c3ab730f082cf2`, 509 selected
source files. Execution freeze:
`3338edbfc19048fa39787d86cc70abebd458318b4a79abd816c531f2fad3ca4f`.
Successor declaration:
`b3dfda1aa30d2fff664f889e61e76401adc0c561fa331e366429b79450cc066d`.
Private preparation receipt:
`3e30514f0bbda19bbca22826756738f4b19c2a625543c934988b39ee634235b4`.
These bind the implementation candidate, not later documentation-only HEADs.

Exact scope for approval: staging plus **one** successor recorder smoke, only after
fresh source/runtime/public-state preflight and Linux readiness **1,156 total,
1,155 pass plus one declared existing Python-version skip**. Original occurrences
0..67, 1 Hz at epoch+j seconds; 20-second epoch lead / 100-ms readiness margin;
68 frames / 180-second capture cap; unchanged CPU 75%, memory 512 MiB, 32 tasks,
240 seconds per unit. One readiness unit, producer and recorder, original observer
grid with 50-ms CPU pre-read lead. Explicit prospective persistence reserve 1 s
inside the unchanged 2-s durable bound; no guarantee or tolerance adjustment.
Closure requires every planned send and verified recorder completion, not merely
ConnectionClosedOK. Stop afterward for independent completeness/inclusive-cost/
archive/missed-slot review regardless of outcome. No retries/replay, replacement,
extra runs, tuning, resource/public-service changes or six-case cohort.

Proposed fresh stage:
`/var/lib/qcrl-stream/recorder-absolute-20261015LupusPersistence01`.
See [full successor contract/command](RECORDER_PERSISTENCE_SMOKE_PREPARATION.md).
Private packet: `.qcrl/reviews/recorder-persistence-preparation-20261015/`.
`stage-packet.tar.gz` is 107,692 bytes, SHA-256
`7987395433a724ad16adf5f843cd31fb8017547c5e6ebefe8deb77f982adc26f`.
It contains the candidate Git bundle, exact freeze and three unchanged runtime/
host review controls. A fresh offline repository containing only predecessor
81fc2ba history reconstructed all 509 selected candidate files exactly from the
bundle. No credentials or raw capture/measurement archives enter this packet or GitHub.

The freeze binds the previously observed October 15 Ohio installed envelope;
it is **not a fresh successor host observation**. Before any unit, fresh read-only
runtime/boot/dependency/source/public checks must match exactly or stop without
execution. Credit balance, incremental observer overhead and continuous RSS peak
remain unknown. Original cohort host-context gates remain open. No successor stage,
claim or unit was created; no Linux successor result exists. Await explicit user
approval of this exact packet. Historical failed freeze f045b061... and its failed
verdict remain intact.

## October 15 — Successor fixes implemented offline; new smoke awaiting approval

The new isolated persistence lane and worker implement both fixes; historical
runtime files, original c9207f... declaration, 2-s durable limit, failed f045b061...
smoke and audit remain unchanged. Pending receives now stop at the earlier of
last-sync+1 s and oldest pending application-return+1 s, with pre-receive and
append checks. The prospective reserve is explicitly **1 second**, not a timing
guarantee; injected persistence stalls still fail the unchanged bound.

Successor drain retains terminal close type/codes/time even across a concurrent
stop. Success requires all planned ordered sends before the normal close **and**
case-bound verified recorder completion, exact archive population/footer and no
capture/reconnect/observer failure. A normal close or capture-closed marker alone
never passes. Atomic exclusive control publication prevents partial consumer.json
adoption. Existing bounded deadlines, resource limits and observer grid/50-ms lead
are preserved. No diagnostic observer layer or native run was added.

All 1,156 offline tests passed in 77.706 seconds on Intel macOS/Python 3.14.6;
the 14 successor tests also pass after the final declaration metadata clarification.
Prospective Linux gate: 1,156 discovered, 1,155 pass plus one existing version skip.
Fourteen successor tests exercise the actual runtime paths, deterministic boundary
and fault cases, and smoke routing/cleanup. See
[prospective successor smoke](RECORDER_PERSISTENCE_SMOKE_PREPARATION.md) for the
new 68-at-1-Hz plan and explicit reserve. The candidate requires a new committed
source/runtime freeze and approval; prior native authorization is spent. No
replay, six-case cohort, resource change, public rollout, merge or QC sync.
Earlier proposal-only sections below are historical checkpoints.

## October 15 — Offline failure diagnosis and prospective fixes

The failed smoke verdict, frozen bytes, implementation and thresholds remain
unchanged. [Offline diagnosis](RECORDER_FAILURE_ANALYSIS_20261015.md) traces both
failures. Persistence scheduling can consume nearly two seconds in two receive
waits before flush/fsync finishes; the full path has no sufficient margin under
the 2-s bound. Drain records normal close as an error after all sends and cannot
distinguish premature normal closure; a concurrent stop can also mask read faults.
The capture-closed marker is published on failure as well as success, and the
producer currently adopts presence without validation. The retained close's exact
ordering is unknown, so the historical failure is not waived.

All 1,142 offline tests passed in 89.878 seconds on Intel macOS / Python 3.14.6.
Fourteen deterministic tests reproduce interval/count boundaries, persistence
faults, exact threshold, close/timeout/control/stop interleavings and failed/missing
capture witnesses using existing code. Proposed successors: cap blocking receives
at pending sync deadlines, and classify a bounded terminal close event against
completed-send and verified recorder lifecycle evidence. These are proposals;
no runtime fix is wired in, and no diagnostic layer was added. Implementation
would change receive/persistence/producer/audit scope and require a new prospective
identity and source/runtime freeze. No native replay or cohort is authorized.

## October 15 — One Linux recorder smoke completed; compatibility failed; stopped

User approval covered exactly one staging/run under freeze
`f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`.
Candidate `81fc2ba` was staged in a fresh private namespace and all 500 selected
source/runtime/public-context bindings passed preflight. Linux readiness passed
1,128 tests in 109.029 seconds: 1,127 pass plus the declared Python-version skip.
The controller then ran the one 68-occurrence producer/recorder pair once under
the unchanged limits. All scoped units are gone; public collectors, source and
environment hash remain unchanged. No replay, tuning, extra run or cohort.

Independent audit: complete 68-frame ordered archive and durability linkage,
verified origin inventory/bytes and actual unit bindings; zero missed observer
slots across 71 absolute wait receipts. Resource gates pass, including one complete
60-second CPU window at upper fraction 0.0045852; sampled RSS max 27,389,952 bytes.
**Overall fail:** sequences 9/44 durability upper bounds 2.000667292/2.000551980 s
exceed 2 s, and producer drain retains `ConnectionClosedOK`. Compatibility and
budget acceptance remain false. No frozen implementation, threshold or evidence
was changed to reinterpret these failures. The 50-ms lead remains prospective.

See [full native audit result](RECORDER_ABSOLUTE_SMOKE_RESULT_20261015.md) for
inclusive CPU/read/RSS/throttling measurements, archive anchors and all limitations.
Incremental observer overhead, continuous RSS peak, host credit balance and producer
internal sleep retries remain unknown. The original six-case host-context gates
remain open. Private evidence/audit/origin receipt:
`.qcrl/reviews/recorder-smoke-native-20261015LupusSmoke01/`.
Only offline retained-evidence analysis remains in scope; no further native run,
cohort, resource change, merge or QuantConnect sync is authorized. Earlier sections
below preserve the preparation chronology; their pending/unrun wording describes
the state before this approved smoke, not current readiness.

## October 15 — Recorder smoke transport prepared; native approval pending

The next target is exactly one native recorder compatibility smoke, not another
isolated timing comparison. The smoke-only controller has one readiness-regression
unit, one producer and one recorder; no cohort route. It sends original corpus
occurrences 0..67 at epoch+j seconds, frame limit 68/capture limit 180 seconds,
20-second epoch lead and 100-ms readiness margin. Separate live PID/cgroup bindings,
fixed commands/limits, one capture per unit and scoped cleanup are audited offline.
Every unit retains CPU 75%, memory 512 MiB, 32 tasks and 240 seconds; numeric IPv4
localhost only. See [exact smoke preparation](RECORDER_ABSOLUTE_SMOKE_PREPARATION.md).

The 2-ms to 50-ms CPU pre-read lead **changes measurement timing** despite unchanged
budgets. Prospective observer policy remains bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f;
new smoke plan is e3b86ea5be1482c7352552459ab14df365789f12b74e37c746adcdb1b529321d.
The producer adds an explicit injected transmitter; its legacy default is unchanged.
This changes its source-bound declaration prospectively. The October 14 declaration
41187030fbf5825311b03c0558bd137b104b7d692078a11777b7bf4242931e15 and private receipt remain
historical frozen identities, not the new candidate. No earlier unknown or result
is repaired; original recorder c9207f... declaration and absolute-wait code stay fixed.

Read-only Session Manager inspection on October 15 observed the existing Linux
Python 3.9.25/aarch64/glibc 2.34 runtime, unchanged boot and public collector/hash
context, and byte-hashed all 60 installed websockets 15.0.1 distribution files.
The EC2 console showed t4g.small/two vCPUs/standard credit mode. The instance role
denied credit-description API access; no IAM change. Console observation is
retained honestly as console evidence, not substituted raw API output. Credit
balance remains unknown. The original cohort host-context gates still apply later.
Private preparation receipts: `.qcrl/reviews/recorder-smoke-preparation-20261015/`.

Offline fixtures exercise full synthetic archives, byte anchors, ordered corpus,
completion/durability linkage, binding/release/lifetime/limit and rehashed wait
faults, failed readiness/cleanup, missing slots with known budget failure, extra
files/symlinks and incomplete launches. They do not establish Linux/native results.
The post-run review must cover archive integrity, completeness, missed slots,
inclusive recorder CPU/RSS/read brackets/throttling/memory events and separate
producer resources. Incremental observer overhead remains unknown from one run.
Any required unknown blocks progression. Stop after this smoke for independent
review and a separate six-case authorization decision. No units have started.

Verification: all 1,128 offline tests passed in 85.018 seconds on Intel macOS /
Python 3.14.6, including the 14 new transport/audit tests and existing localhost
fixtures. New transport/auditor/tests compile with local Python 3.8.2. Fresh
read-only wait-runtime bytes exactly match the earlier frozen comparison envelope;
that observation is not execution of the new recorder path. Installed Linux
readiness tests and native recorder measurements remain unrun. New source-bound
observer declaration: 0f3a9b8494804f792d5778a0388d787cb2bc52a5de7fd4bc1cdb60738ded6bf1.

The exact candidate/freeze approval packet is recorded below. No main merge, QC sync,
credentials import, infrastructure change or native execution is authorized here.

## Frozen approval packet — October 15

Implementation candidate: `81fc2ba00fc5cae35316b3661dbb2ec6044f666b` (500 selected source files).
Execution freeze: `f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`.
Private preparation verification receipt:
`3f15daf0206e50663d3174ce78218c48132f496cd7bd894e1068ec3ff1774d1e`.
These bind the implementation candidate, not later documentation-only HEADs.
The original three native audit payload hashes still verify unchanged.

Prepared private transport packet `stage-packet.tar.gz`: 119,716 bytes,
SHA-256 `f974a66a733218802f53afc31fa1f31ca9335557fbe20c33ad4c74fc28c6164f`.
It contains the incremental Git bundle (prerequisite frozen cb23c4c), exact freeze,
reviewed select source/review and dated host context. No credential or evidence
archive is included. Source is not yet staged remotely; no new candidate code,
readiness unit or recorder unit has executed on Linux. After approval, stage into
one fresh private directory, verify packet/commit/all source/runtime bindings
before starting units, and reject any existing evidence/claim/unit namespace.
Do not overwrite or execute in an old comparison/evidence directory. The transport
bundle and controls must reconstruct the candidate exactly; stop on any mismatch.

Proposed stage: `/var/lib/qcrl-stream/recorder-absolute-20261015LupusSmoke01`.
After separately approved staging and gate checks, the one controller invocation is:

```sh
/opt/qcrl-stream/venv/bin/python -B -m infra.stream.recorder_absolute_smoke --root /var/lib/qcrl-stream/recorder-absolute-20261015LupusSmoke01 --execute
```

Run it as root from that stage's `source` directory through the authorized existing
Session Manager connection. Expected readiness population: **1,128 tests, 1,127
passing and one existing Python-version skip**, within its separate 240-second
unit. Those are prospective Linux counts, not observed Linux results. Any other
population, failure, drift, effective-limit/binding/readiness fault or retention
failure stops progression and preserves the attempt without replay. Then only
the declared producer/recorder pair: 68 occurrences at 1 Hz over offsets 0..67,
20-second original epoch lead, frame limit 68/capture limit 180 seconds, fixed
75% CPU/512 MiB/32 tasks/240 seconds per unit, 50-ms CPU pre-read policy.

Stop after one smoke. Independently transfer/verify the external origin inventory
anchor, audit completeness, ordered archive/durability, actual wait/read/missed-slot
coverage, inclusive observer/recorder cost and every unknown. Incremental observer
overhead and host credit balance are explicitly unknown. The console's dated
standard-credit observation does not replace the original six-case cohort's raw
host-context gates. No isolated timing run, tuning, replay, cohort, public-service
change, infrastructure provisioning, main merge or QC synchronization is included.
**Await the user's approval of this exact packet before staging/execution.**

## October 14 — Offline absolute observer integration and successor preregistration

Absolute waiting is integrated into the isolated recorder's in-unit CPU/RSS
observer through explicit prepare/consume wrappers. The receive path, producer
pacing, segmented writer, completion witnesses, public collectors and original
recorder declaration remain unchanged. Legacy consume defaults to its old observer.
The original recorder plan is still c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade.

New observer policy hash:
`bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f`.
Source-bound declaration:
`41187030fbf5825311b03c0558bd137b104b7d692078a11777b7bf4242931e15`.
Private offline receipt: `.qcrl/reviews/recorder-absolute-offline-20261014/`.
It uses the shared epoch's ceiling integer nanoseconds, fixed integer-second RSS
slots and 50-ms pre-boundary CPU lead (an explicit successor to the old 2-ms
lead). Budgets stay unchanged; the enclosing CPU delta is not normalized or
subtracted to remove the larger lead. Every endpoint gets at most one absolute
wait. Past/equal targets and >50-ms late wakes cause no read/catch-up, retain
unknowns and continue original slots. Wait/clock faults and KeyboardInterrupt
stop the observer with its prefix; ordinary read faults retain their unknown slot
without retry. Capacity/overflow remains 184 slots. Wait receipts and case/source
bindings are checked before the unchanged resource gates; known failures survive
missing evidence. No native-origin or acceptance flag is promoted.

Prospective test: one 68-occurrence, 1-Hz real-loopback compatibility run spanning
one complete 60-second CPU window, then stop for independent review. This is not
a shortened acceptance case. Only after a separate approval may the original
six serial 60,000-occurrence cases / 360,000 total run with unchanged workload,
corpus, resource limits and application budgets. No tuning or replacement.
See [recorder absolute preregistration](RECORDER_ABSOLUTE_BUDGET_PREREGISTRATION.md) for the full declaration,
missed-slot rules, bounds, stopping conditions and remaining implementation gates.

Offline verification uses injected clocks/syscalls/readers and recorder wiring;
no new native wait, Linux unit, capture, infrastructure, credential operation or
QC sync. The 68-at-1-Hz transport, native launcher routing, fresh committed
source/runtime/dependency envelope and independent launch/origin audit still need
implementation and review before requesting native authorization. Old launchers
must not be reused to claim this path ran. Earlier frozen evidence and verdicts
remain unchanged; audit each against its originating revision.


Verification: all 1,114 offline tests passed in 78.738 seconds on Intel macOS /
Python 3.14.6 with numeric-localhost fixtures permitted. All 21 new integration
and fault tests pass, including real WebSocket/recorder completion wiring with
injected syscalls/resources/Linux context. Four changed/new Python files compile
with local Python 3.8.2. This is not installed Python 3.9/Linux or native recorder
validation. No new native experiment or acceptance result exists.

## October 14 — Frozen two-run comparison completed, one unknown

Renewed direct approval covered corrected cb23c4c / execution freeze
`7c0ddaf5f697493302fd6791a64aacc68618d391a2a80c3bfd3a8dca198c3f55`.
Fresh exact source/runtime/public preflight passed. Linux Python 3.9.25 regression
passed: 1,093 discovered in 105.935 seconds, 1,092 pass and one declared skip.
The two fixed serial AB/BA units then completed once, without fatal wait or
transport faults. No tuning, catch-up, replay or additional measurement occurred.

Independent native audit
`c2a6b59f07563fbf10f8184fd09494d89f0400e6bc9917bf1337ced04a466f4d`
checks the observed host/transfer, all 23 retained evidence files, source/runtime,
readiness/release/live identities, actual limits, serialized lifetimes, journal
and receipt equality, independent timing/float/rational arithmetic and cleanup.
Private receipt: `.qcrl/reviews/wait-comparison-native-20261014LupusCompare02/`.
All private units are inactive; public/environment/source/runtime unchanged.
Original declarations, compatibility smoke and failed first readiness evidence
remain untouched. All producer/freeze authority flags remain false.

Transport is complete but scientific comparison completeness remains false:
23 observed cells, one unknown. Run-zero absolute 50-ms target was already
8.892023 ms late before invocation, following select's 58.771055-ms-late
60-second return. No absolute request was made for that cell; no replacement.
The paired 50-ms median is null. All 12 select internal retry counts remain
unknown. All 20 declared context-file observations succeeded; 16 structured
ancestry nulls retain absent root limit/disabled child cpuset files, not invented
numeric limits. Endpoint context cannot identify per-target host/signal/scheduler
causes. Quiet regression identities and RPM signature/reproducible-build limits
remain explicit in the full audit.

At 60 seconds, select lateness was 58.771055 / 60.099649 ms and absolute was
0.136841 / 0.131331 ms; paired median absolute-minus-select = -59.301266 ms.
These are descriptive serial samples with host/time confounding, no tail,
significance, exclusive-causality, recorder-acceptance or trading conclusion.
Recorder application compatibility and its budget cohort remain unfinished; the
new absolute-observer path is implemented offline and preregistered above.
The finite comparison authorization is consumed; further native execution needs
separate approval. No new diagnostic layer, main merge or QC sync.

Full observations, identities and every unknown are documented in
[native comparison audit](WAIT_COMPARISON_NATIVE_AUDIT_2026_10_14.md).

## Earlier execution gate — preserved failed comparison readiness

This section records the stopped first attempt; the renewed, corrected-source
execution and its separate receipts are reported above.

The operator directly authorized exact b7db2c2 / freeze
`f1339e0b54b84703368fc39efdfeb7c470ce4220bbb15d6df8284e46c0036f61`.
A fresh private stage passed live source/runtime/public preflight, then its bounded
Linux regression failed before either comparison worker was created. The declared
native gate stopped advancement; no measurement, retry, tuning or extra run occurred.
The failed test unit is retained as failed with MainPID 0; both comparison units
are absent. Public collectors, environment and frozen source/runtime are unchanged.
Corrected candidate cb23c4c2b6b2 is sealed offline (full identity below).
Further native execution requires new approval of that execution revision.

Linux Python 3.9.25 discovered 1,079 entries in 105.799 seconds: 1,077 passed,
one existing Python 3.10+ stdlib-inventory guard skipped and one module import
error. Fifteen new tests were replaced by one loader-error placeholder. The exact
failure is `SyntaxError: too many statically nested blocks` in the new fault test,
line 312. The earlier Python 3.9 AST parse checked grammar, not compiler block
depth. Offline correction uses ExitStack for the same mocks, preserving their
order, cleanup and assertions. Production Python and every plan remain unchanged.
Both new files now compile with local Python 3.8.2; 15 focused fault tests pass.
This is local verification, not repaired Linux validation. The corrected candidate
seal and complete local regression result are recorded below.

Untouched receipts: `.qcrl/reviews/wait-comparison-native-20261014LupusCompare01/`.
Separate failed-gate audit:
`353a9e1fa414aa8a77bf562ada0aa34bb5ff332c61d367f8d20bc055ac1af5e6`.
All eight native evidence files match origin inventory
`c4c320fcb1d61dc2f374d5c2a0fdebd15b243e1c2b05de8b08ca7da2b04111c7`;
transferred archive SHA-256
`7e502385ac81b015faec70c187010d2ae386dd4ffddea05552436374f248d265`.
Audit independently checks observed host/transfer origin, frozen controls, failed
unit properties/journal, no comparison directories/units, no worker processes and
unchanged public/source/runtime. It does not verify a successful scientific pair.
Producer flags and original b7db/2cb freezes/evidence remain unchanged.

For this failed attempt only, all 24 run/arm/interval cells remain unknown
(two runs × two arms × 50 ms,
100 ms, 500 ms, 1 s, 5 s, 60 s); epochs, baselines, request/return brackets,
worker context and all descriptive comparison statistics are unavailable.
Select internal retry counts remain unknown; no comparison calls were made.
Quiet regression output does not enumerate individual passing test identities.
RPM provenance still lacks independent signature verification/reproducible build.
No scheduling, recorder-acceptance, causal or trading conclusion follows.

The earlier single native compatibility smoke remains independently verified
under the original 2cb6880 / 488-source freeze
`8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1`.
Its 1,078-entry Linux gate and both waits passed. The failed new gate does not
rewrite that evidence or validate the new transport on Linux.

## Current scientific status

The independently audited October 12 Linux clock-only diagnostic retained 11
observed wakes and one missed target. The 60-second waits returned approximately
59–60 ms late. Select-related slack is a post-hoc mechanism hypothesis, not proof
about the installed runtime or an exclusive cause. Measurement completeness and
performance acceptance remain false. The earlier counter smoke's final endpoint
missed the fixed deadline before any counter read. Preserve both failures and
the original 50-ms budget.

The absolute-monotonic adapter passed its native interface smoke and the later
finite v2 comparison retained 23 observed cells and one missed target. Recorder
integration and performance acceptance remain unverified. The active comparison is
[ABSOLUTE_SELECT_COMPARISON_V2.md](ABSOLUTE_SELECT_COMPARISON_V2.md), with plan hash
`c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d`.
V2 preserves two serial 133.3-second AB/BA runs and integer targets while allowing
one Python select call with disclosed runtime retries and unknown internal count.
The predecessor
[ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md](ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md)
and its hash `a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee`
remain retained; v1 has no native result. Both hashes have literal regression pins.
Injected select/absolute collection, pair lifecycle, validation, exact descriptive
evaluation and bounded exclusive publication now exist. The native transport
first stopped on a failed Linux readiness gate. Its corrected source later passed
the gate and completed the declared pair, as audited above.

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

## October 14 — Two-run native transport prepared offline

The operator relayed a proposed frozen two-run continuation. Readiness review found
that original candidate 2cb6880 only launches tests/compatibility; executing the
comparison under that freeze is impossible. Added a separate bounded native worker,
controller and retained-byte auditor without editing the v1/v2 declarations or
any existing Python implementation. The original full freeze, native compatibility
audit and all historical evidence remain intact. Source/runtime extension and direct
native authorization are required before execution; this is a material execution
source change, not a timing-plan revision or a new diagnostic layer.

The new controller runs a frozen Linux regression readiness gate before two fresh
AB/BA workers. Source/runtime/public drift, missing/additional skipped tests,
readiness/binding/unit/publication/capture faults stop advancement. Run-zero fatal
receipts cancel run one; nonfatal missed targets retain original targets and continue.
No retry, replay, adjustment, tuning or additional measurement run exists. Limits
remain CPU 75%, 512 MiB, 32 tasks and 240 seconds; comparison network remains denied.
Captured before/after context uses the existing bounded reader. Helper polling,
private-only cleanup and partial-evidence retention reuse the tested production
adapters. Independent audit checks bytes, identities, lifetimes, effective limits,
original arithmetic, exact summary and explicit unknown cells/context.

Offline fault coverage exposed default-handler KeyboardInterrupt as a BaseException
that the unchanged injected collector cannot directly retain. The transport wraps
only the wait/clock callable boundary, records this fault as an Exception without
handler changes or retries, and preserves prior rows. An escaping interruption
outside those boundaries after collection starts leaves the receipt unavailable;
it never fabricates a null-epoch setup result. Post-collection journal publication
retains rows if exclusive file creation fails. Kills/timeouts before publication
cannot recover all in-memory rows; retain available files/journals and report every
unavailable cell rather than claiming success or adopting a partial artifact.

The frozen Linux test expectation is 1,093 discovered with exactly the existing
Python 3.10+ inventory skip on Python 3.9.25. No new Linux test or native comparison
has run. All 68 focused offline tests pass, including 15 new transport fault tests;
Python 3.9 syntax parsing passes. Complete local regression and exact source/runtime
seal are recorded below when finalized. Native origin, comparison completeness,
scheduling improvement, recorder acceptance and orders remain unclaimed.

Final offline verification for this execution candidate: all 1,093 tests passed
in 90.520 seconds on Intel macOS/Python 3.14.6, with localhost fixtures permitted.
All 68 focused tests and Python 3.9 syntax checks pass. Seven-file implementation/
documentation diff reviewed; every original Python file, all three plan hashes
and original private evidence are unchanged. Native validation of the new transport
remains pending its separate authorization and Linux regression readiness gate.

## Sealed comparison execution candidate — October 14

Implementation commit: `b7db2c25d8550b3f75d3324846f45b2ad4c3503d`.
Selected source inventory: 491 files, each verified against that exact Git commit.
Full execution-freeze hash:
`f1339e0b54b84703368fc39efdfeb7c470ce4220bbb15d6df8284e46c0036f61`.
Private controls and local verification:
`.qcrl/reviews/wait-comparison-source-b7db2c25d855/`.
Verification receipt hash:
`4bb24cc655edafd303d91ef1608785f91165e9ab2f38ba52aaff3e6c4e335b2c`.

The freeze reuses the independently reviewed original runtime and compatibility
audit and confirms every previous Python file unchanged. It preserves all original
source/runtime/compatibility evidence and all three declared plan identities.
These later receipt-documentation commits do not replace the execution candidate;
stage exact b7db2c2, not the later documentation HEAD. Native origin/execution/
compatibility/acceptance/order flags in the new freeze remain false.

Ready to request direct operator approval of this exact new freeze: one bounded
Linux regression readiness unit (1,093 discovered, the existing Python 3.10+ skip),
then the preregistered two comparison units once in AB/BA order. No additional
compatibility smoke, tuning, replay or extra measurement run. Preserve public
collectors, retain partial evidence, stop on declared fatal/native gate conditions,
independently copy/hash/audit results and enumerate all unknowns. The forwarded
other-chat instruction is not treated as authorization for this new execution
revision. No remote staging, new Linux test or comparison call occurred during
this offline implementation/sealing continuation. Original 2cb6880 cannot run it.

Corrected local regression: all 1,093 tests passed in 97.249 seconds on Intel
macOS/Python 3.14.6 with existing numeric-localhost fixtures permitted. Fifteen
focused fault tests pass; Python 3.8.2 compilation reproduces the original nested
block failure and accepts the corrected files. No corrected Linux unit ran.

## Corrected offline execution candidate sealed — October 14

Exact candidate `cb23c4c2b6b2d7de76435bd6397415f4550e4727` contains only the
fault-test context-manager refactor and status updates relative to failed b7db.
All production Python and scientific plan hashes remain unchanged. Its 491-file
inventory matches exact Git blobs and retains the reviewed runtime and original
compatibility prerequisite. Full freeze:
`7c0ddaf5f697493302fd6791a64aacc68618d391a2a80c3bfd3a8dca198c3f55`.
Private controls: `.qcrl/reviews/wait-comparison-source-cb23c4c2b6b2/`.
Verification: `a445c94f0eb50f88821954d4ce3fb9ec07a447879ee8fb3b54708f3fe10c6db8`.
Later receipt-documentation HEAD does not replace this execution source.

Ready offline for a new operator-approved, fresh-stage Linux readiness attempt,
conditional on the unchanged source/runtime/public gates. Expected Linux population
remains 1,093 discovered, one existing skip. Only after a successful gate may the
unchanged two AB/BA runs execute once. No corrected source was staged or run on
Linux; no resumption, retry, replay, extra measurement or recorder cohort is
currently authorized. Original failed stage/receipts remain untouched. All freeze
and producer authority flags remain false; the failed gate demonstrates no
scientific comparison or acceptance. Obtain approval before any further native
unit, rather than reusing the failed attempt's permission.
