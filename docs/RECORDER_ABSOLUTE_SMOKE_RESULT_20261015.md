# October 15 recorder smoke result

The single authorized recorder compatibility smoke completed its workload, but the
frozen independent auditor returned **fail**. Compatibility is not verified and
budget acceptance is false. Stop here; do not run the six-case cohort or repeat
this smoke. Native execution used the new prospective 50-ms CPU pre-read policy;
it does not revise the historical 2-ms measurements or their verdicts.

## Scope and readiness

The user explicitly approved staging and one run under execution freeze
`f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93`.
A new private stage, `recorder-absolute-20261015LupusSmoke01`, reconstructed candidate
`81fc2ba00fc5cae35316b3661dbb2ec6044f666b`. Preflight checked all 500 selected
source files, the frozen installed runtime/dependencies, public context and fresh
unit/evidence namespace before launching. The controller started once.

Installed Linux Python 3.9.25/aarch64 readiness passed: **1,128 tests in 109.029
seconds, 1,127 passing and the one declared existing Python-version skip**
(`stdlib_module_names` requires Python 3.10+). This differs from the earlier Intel
macOS/Python 3.14.6 offline result of 1,128 passing in 85.018 seconds.
Only after readiness did the producer/recorder pair run: original occurrences
0..67 at 1 Hz, original epoch, 68-frame/180-second capture limits and unchanged
75% CPU, 512 MiB, 32-task, 240-second unit limits. No retry, replay, tuning,
additional timing experiment, extra smoke or six-case case ran.

## Independent evidence audit

The frozen auditor verified the complete retained file inventory against an
externally observed origin byte anchor, exact freeze, unit commands and effective
limits, live distinct PID/cgroup bindings, readiness/release chronology and unit
lifetimes. All three units completed successfully; the controller retained no
launch or preservation error. Controller completion is separate from the failed
scientific verdict below.

| Check | Observed result |
| --- | --- |
| Archive integrity and completion linkage | Pass; 68 ordered original frames, including duplicate occurrences, intact segment/manifest hashes and durability witnesses |
| Stimulus | Pass; 68/68 phase attainment, no missing occurrence |
| Append latency | Worst and p99 upper bound 0.352686 ms |
| Durability bound | Fail; sequences 9 and 44 have upper bounds 2.000667292 s and 2.000551980 s against the unchanged 2-s limit |
| Producer control/drain | Fail; eight recorded controls are `PING`, but `control_errors` contains `ConnectionClosedOK` |
| Absolute observer | 69 RSS slots, two CPU pre-reads, 71 observed wait receipts; zero missed slots, retries, overflow or observer faults; maximum wait lateness 0.792141 ms |
| Complete 60-s CPU window | Pass; inclusive upper fraction 0.0045852 (0.45852% of one core) |
| Sampled recorder RSS | Maximum 27,389,952 bytes (26.1211 MiB) |
| Reader bracket | Maximum scheduled read bracket 4.213055 ms |

The exact frozen failure list is `row:9:durable_upper_seconds`,
`row:44:durable_upper_seconds`, `case:durable_worst`, `0:durable_worst` and
`unexpected_client_control_or_drain_error`. The latter records a normal-close
exception type in the producer drain; that interpretation does not waive the
preregistered failure. The two measured upper-bound exceedances likewise remain
failures without tolerance changes or subtraction. Causal attribution of the
small overruns is not established by this single run.

Resource coverage includes the complete epoch-to-60-second window and required
integer RSS slots through capture closure at epoch+67.012047247 s. An additional
slot 68 was retained while the observer finished its already pending wait; it is
not a replacement or a missed target. No reanchoring or catch-up occurred.

## Inclusive cost and limits of inference

The recorded startup interval consumed 24,914 CPU microseconds; first CPU pre-read
to final retained sample consumed 234,449 microseconds. These are cgroup totals
including recorder/observer work, not isolated observer overhead or complete
process-lifetime totals. The first readiness probe already showed 309,845 CPU
microseconds, the first CPU pre-read 334,759 and the last sample 569,208. Retained
systemd exit accounting reports 626,725 CPU microseconds for the whole recorder
unit and 412,118 for the producer (including startup/cleanup). No baseline or
overhead subtraction is available.
The recorder's initial throttling counters were already four periods / 126,380
microseconds; both remained unchanged across retained observations. They must not
be described as zero lifetime throttling. All retained memory-event counters were
zero. Producer initial-to-final CPU delta was 72,531 microseconds, sampled RSS
26,083,328 to 26,562,560 bytes, with unchanged three throttled periods / 79,586
microseconds. Producer resources remain separate from recorder measurements.

The component auditor has no missing-evidence unknowns for its declared gates.
Broader limits remain: incremental observer overhead is unknown; sampled RSS does
not prove a continuous peak; host credit balance remains unknown and the original
cohort's raw host-context gates remain open. Producer relative-sleep internal
runtime retry counts remain unavailable. Select's runtime EINTR retries were
previously disclosed; no select arm ran in this smoke. These disclosures are not
converted to passing evidence. Long-run, high-rate and six-case acceptance remain
unestablished. The quiet native regression journal prints the exact total and one
skip, but not the skipped test identity; attribution to the declared
`stdlib_module_names` version guard is consistent with the frozen source/runtime,
not a separately named native journal witness. Compatibility, budget acceptance
and order authorization stay false.

## Preservation and provenance

The authorized existing Ohio Session Manager session observed staging, the single
controller invocation and its completion on the frozen host. Post-run read-only
inspection found no scoped smoke units remaining. Public collector timer remained
active; pilot/observer services remained inactive; public HEAD and environment
hash were unchanged. Existing resource limits, public collectors and historical
evidence were preserved. No infrastructure, IAM, credentials import, main merge
or QuantConnect synchronization occurred.

Private outcome directory: `.qcrl/reviews/recorder-smoke-native-20261015LupusSmoke01/`.
It retains the original 53,891-byte transport archive, reconstructed evidence,
unaltered independent audit, separate observed-origin receipt and console proof.
Four unchanged approved controls were copied locally from the preparation packet,
then verified byte-for-byte with every other evidence file against the 28-file
origin inventory. Safe extraction accepted only regular relative files; archive
and inventory hashes matched their independently observed origin values. Neither
raw evidence nor preparation packets are committed to GitHub.

| Anchor | SHA-256 |
| --- | --- |
| Origin transport file | `55dcd3e435f0a083f048f0b4e75ca3ac89d4a2e08bbacd6a52ddb084631da7e2` |
| Origin inventory file bytes | `598402a61c20b13b03ad4950e867b0a86a7359934d8602ac4d14e36ded8707ed` |
| Launch payload | `95fd36a943fb93222aeed09b28d00325a97a5cabc19c69ab235c9f472250adf8` |
| Independent audit file bytes | `f62473d6483db2369d3d394826cefb396f9e3665fd0b66ce233534988b113956` |
| Separate observed-origin review payload | `ca240ffac850e7f9e3b4e7d95a9f0126833f790ff14736a77aae30ac2d895924` |

The original artifacts keep their `native_origin_verified=false` fields; the
separate receipt records the operator's observed-origin attestation. Hashes and
console observation establish the documented integrity/provenance chain, not an
independent hardware signature. The three prior native audit payload hashes were
reverified unchanged. Original declarations and preparation receipts remain intact.

Further work may analyze retained bytes offline and prospectively address the
durability/control-drain failures. No replay or cohort is authorized. A new native
attempt would require a new reviewed prospective identity and explicit approval.
