# Six-case successor cohort readiness — October 15

**Historical blocked checkpoint, superseded by the implementation and fresh host
evidence described in [HANDOFF](HANDOFF.md) and the [successor contract](RECORDER_PERSISTENCE_COHORT.md).**

The following preserves the original readiness finding; its blocked packet is not
the final executable packet. This review checks development
commit `92889b0b54745dc28c5dd7736c0723df0274ddf9`. The passing successor smoke
establishes its own bounded compatibility only. There is no frozen successor
six-case executable or independently bound compatibility receipt for that route.
No native command, unit, standalone smoke or cohort was started for this review.

The governing contracts are the [parent application preregistration](RECORDER_APPLICATION_BUDGET_PREREGISTRATION.md),
[absolute observer successor](RECORDER_ABSOLUTE_BUDGET_PREREGISTRATION.md),
[Linux launcher requirements](RECORDER_APPLICATION_LINUX_LAUNCHER.md) and
[prospective persistence policy](RECORDER_PERSISTENCE_SMOKE_PREPARATION.md).
Historical declarations, failures and thresholds remain frozen.

## Resource requirements and limits of the smoke

| Requirement | Contract and readiness interpretation |
| --- | --- |
| Recorder CPU | Inclusive dedicated-cgroup cost, observer included; each complete epoch-anchored 60-s window must be at most 70% of independently evidenced effective quota. Reads must enclose the original boundaries, each bracket at most 5 ms. Nine windows across six cases: two per steady case, one per mixed case. The smoke passes only its one window; cohort measurements remain unrun. |
| Recorder RSS | Every required integer-second current-VmRSS sum across unique live unit processes must be at most 80% of the 512-MiB limit, with bracket at most 5 ms and lateness at most 50 ms. Membership races, missing slots and invalid brackets remain unknown. The smoke's 69 samples do not populate the cohort. |
| Incremental observer overhead | **Not a required gate in this preregistration; unknown.** The parent explicitly says this is not a probe-overhead comparison. Inclusive CPU cannot isolate observer overhead. Earlier 5%-probe rejections remain unchanged; no claim that a 5% test passed. |
| Continuous RSS peak | **Not a required gate; unknown.** Parent policy has `rss_peak_claim=false`, and both the draft and evaluator explicitly deny continuous-peak proof. Sampled maxima are not peak acceptance. No continuous peak threshold is introduced or silently waived. |
| Other resource evidence | Require live PID/start/boot/cgroup and actor ancestry, actual commands/limits, effective cpu.max/cpuset/memory.max, cpu.stat throttling, memory.events, before/after concurrency, startup/close/publication costs and separate producer costs. Report cgroup memory and any available high-water values separately; unavailable high-water fields remain unknown and cannot replace current RSS. |

The smoke measured inclusive CPU upper fraction 0.0048931556 and sampled RSS
27,553,792 bytes. Those are valid observations for that smoke, not cohort values.
Neither incremental overhead nor continuous peak is promoted to pass. Adding
either as an acceptance gate would require a separate prospective contract and
measurement design; that is not needed to execute the existing declared question.

## Host credits: required configuration evidence versus unknown balance

The native launcher/auditor requires operator-retained raw `DescribeInstances`
and `DescribeInstanceCreditSpecifications` responses, a matching instance-identity
document and live boot, with a separately observed byte anchor. Labels such as
"t4g.small / standard" and console text alone do not satisfy this requirement.
Hashes bind retained bytes, not AWS authenticity by themselves.

Retained October 12 context was found and verified against its historical external
file anchor `4d56d7a2a130afbd88cae70e8488c85d251ae5b73f56c024565fc1b4e8186841`.
It identifies the same Ohio instance, t4g.small, standard credit mode and boot used
by the successor smoke. `verify_host` accepts those historical raw responses.
They are **not fresh October 15 configuration evidence**, and are not relabeled
as such. The October 15 console-only smoke context fails the cohort host verifier
because the required raw fields are absent. The collector role's describe denial
is preserved; no permissions or credit mode were changed.

Credit **balance** remains unknown. Neither parent policy nor `verify_host`
declares a numerical minimum balance, credit-exhaustion safety margin or continuous
credit-history gate. Do not invent one after seeing results, assume sufficient
credits, or equate a positive balance with configuration verification. Fresh raw
mode/instance/identity evidence is an unmet launch requirement. Available credit
balance/history should be retained with timestamps and scope; unavailable data
must stay disclosed as unknown. CPU-credit effects or shared-host effects cannot
be ruled out or attributed from unit throttling counters alone.

Fresh read-only AWS responses can use an already available authorized operator
API session, as the October 12 review did. No credential import, IAM expansion,
credit-mode change or infrastructure provisioning is part of this packet. An
unavailable authorized access path is a blocker, not grounds to weaken the gate.

## Concrete offline integration blockers

1. `recorder_application_launch` invokes the legacy application worker and legacy
   relative observer. It does not invoke the persistence fix and absolute observer
   together. Its preflight also requires a same-source/runtime native compatibility
   receipt with its exact original schema; the new smoke audit cannot be renamed
   or have its authority flags edited to satisfy that requirement.
2. `recorder_persistence_worker.verify_recorder_completion` calls the historical
   smoke archive reader. An offline 69-frame archive deterministically fails with
   `extra smoke archive frame`. Its 68-frame/1,024-row caps cannot verify a
   60,000-frame cohort. The frozen smoke reader must remain unchanged; a bounded
   cohort verifier and producer completion path are needed under a new identity.
3. A deterministic 60,000-send steady simulation produced an 11,556,521-byte result
   object. The cohort path must use the existing bounded 32-MiB large-artifact
   verification for producer records rather than the 2-MiB control reader. This
   is a loader/cap requirement, not evidence of native throughput.
4. There is no successor cohort auditor that binds all six cases, new wait receipts,
   persistence/closure rules, effective unit identities, fatal-stop behavior and
   the original per-case/per-phase denominators. The legacy resource evaluator
   alone cannot attest the new absolute wait protocol.
5. Exact successor execution-source/runtime freeze, staged transport byte anchor,
   readiness test total and fresh host-context anchor do not yet exist. Compatibility
   provenance must explicitly bind the tested sources and any new cohort integration
   delta; the original same-source gate must not be silently bypassed.

These are offline integration/evidence requirements. They do not establish that
another native standalone smoke is necessary. Resolve and test the finite cohort
path first; propose another smoke only if a concrete remaining native compatibility
requirement demands one, with its reason and separate authorization.

Verification in this review: eight existing launcher/auditor fault tests passed
in 0.148 s on Intel macOS/Python 3.14.6. Direct offline checks reproduced the
69-frame cap failure, raw-context distinction and full-population producer size.
These are local checks, not Linux validation. Private review payload:
`b7083df69945a357df073efaa8c3cb39d5b27b332aac1caac0a420eaca92fb38`.

## One cohort approval packet — blocked, not executable

Private packet: `.qcrl/reviews/recorder-cohort-readiness-20261015/approval-packet.json`.
Packet payload SHA-256:
`b8da8c80ef67ddfb4d24eb10517f860a7affbaeb226c9cfba3addb1e60400777`.
It freezes the proposed scope and the explicit missing identities below. **It is
not an executable approval request or an execution freeze.** User approval cannot
turn missing implementation/evidence into a passed gate. Once those exist, one
final packet must bind their actual bytes before execution approval is requested.

| Packet item | Exact scope/status |
| --- | --- |
| Native host | Existing Ohio instance `i-039c11d5ea49cf413`; existing configuration and public collectors preserved; fresh raw host-credit/identity context and external anchor missing |
| Compatibility lineage | Candidate `371fa03c3d2622d784128b9359c3ab730f082cf2`, freeze `3338edbfc19048fa39787d86cc70abebd458318b4a79abd816c531f2fad3ca4f`, independent audit file `798a1ed0d68bb796d9805794a967ed4337f3b4183f9d7e2342b7dd7b260a2f88`; no claim of same-source successor cohort validation |
| Execution identity | Successor cohort candidate, declaration, runtime/source freeze, transport hash, native command and fresh stage **not yet bound**; no runnable command supplied |
| Readiness | Exactly one regression unit first, exact total to be frozen after implementation, one declared Python 3.9 version skip; any mismatch stops before cases |
| Case order | steady-0, mixed-0, mixed-1, steady-1, steady-2, mixed-2, serially; six producer and six recorder units, 13 units including readiness |
| Population | 60,000 original ordered occurrences per case, 360,000 total; original corpus and synthetic metadata recipe unchanged |
| Steady schedule | Each of three cases: 120 s at 500/s |
| Mixed schedule | Each of three cases: 10 s at 500/s, 10 s at 3,000/s, 50 s at 500/s |
| Epoch/caps | Fresh shared epoch per case, original 20-s lead and 100-ms readiness margin; 60,000-frame and 180-s capture caps |
| Units | Each producer/recorder/readiness unit: CPU 75%, memory 512 MiB, 32 tasks, 240 s; numeric IPv4 loopback only, existing security restrictions; no affinity, resource change or host exclusivity |
| Observer/persistence | Original integer-second grid and 50-ms CPU pre-read lead; observer policy bdd41717...; prospective 1-s persistence reserve inside unchanged 2-s durability bound, not a guarantee; closure requires all planned sends plus verified recorder completion |
| Application gates | Append upper p99 ≤100 ms, worst ≤1 s; durable upper worst ≤2 s; every return UTC bracket ≤1 ms; zero supported loss/missing witnesses. Per case/per phase, full denominators, no pooling/subtraction/tolerance changes |
| Stimulus gates | Every send-start lateness and send-call bracket ≤50 ms; phase attainment ≥99%; no drops, rate adaptation or send retry |
| Resource gates | Inclusive CPU ≤70% effective quota in every complete window; current RSS ≤80% unit limit at every required sample, with the original enclosure/bracket/lateness/identity/coverage gates |
| Stop/preserve/audit | Stop subsequent units on fatal launch/runtime/source/public/identity faults; retain partial evidence, known failures and unknowns. After the finite cohort, stop and independently audit originating inventory/bytes, ordered archives, completion/closure, all 13 units, every case/phase/window/slot, inclusive and separate producer costs |
| Exclusions | No retry/replay/replacement/tuning/extra cases or standalone smokes, public capture/rollout, credential import, IAM/infrastructure/resource change, main merge, QuantConnect sync or orders |

This packet is a readiness finding with fixed proposed scope, not a claim that
the requested executable approval packet is complete. Launch remains blocked by
the enumerated source/transport/audit and host-evidence requirements.
