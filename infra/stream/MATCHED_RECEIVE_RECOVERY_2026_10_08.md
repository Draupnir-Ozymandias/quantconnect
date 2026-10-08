# Matched receive-v2/v3 integration review — October 8, 2026

Source frozen for this finite experiment:
`ccb7fa8` (versioned recorder/archive/analysis integration).
Protocol: [explicit v3 integration and matched controls](../../docs/RECEIVE_RECOVERY_INTEGRATION.md).
The operator authorized integration followed by the matched synthetic comparison,
not a public collector deployment or further trading/strategy experiments.

## Frozen protocol and operational boundary

Three rotating-order rounds, bare/receive/full-recorder modes, v2 AND v3 lanes:
18 cases, 30,000 messages per case, 540,000 expected messages. Each 30-second case
has six cycles of four seconds at 500 and one second at 3,000 target messages/sec.
The same previously verified corpus/template cycling and synthetic timestamps
are used. Six scheduled text PONGs replace cycle-final data messages in every
lane; these are fixture controls, not genuine network acknowledgments.
Lane order alternates by round plus original mode index, with the declared
one-case imbalance from three rounds. Bare duplicates are host-variation controls.

Producer/consumer groups retain separate 100%/75%-of-one-CPU quotas, each
512 MiB, 32 tasks and 120-second runtime maximum. No core affinity, resource
upgrade, cloud stack change or recorder-stage removal occurred. Producer lateness,
send blocking, attained rates and all raw/delivery observations remain retained.
All case verification and source-bound analyses run AFTER measured loops and
before the next case starts. No evidence transfer runs during measured cases.

Tests at the frozen revision: all **524 local tests** passed in 15.309 seconds;
all **524 Linux tests** passed in 41.743 seconds, with one expected Python-version
inventory skip. Local smoke tests exercise both lanes in all three modes and
their source-bound analyses. A synthetic archive test verifies a full recorder
trajectory with one unknown fence-closing delivery and restored marker afterward.

Linux uses a NEW diagnostic source clone at
`/var/lib/qcrl-stream/receive-recovery-matched-20261008-GL20pl/source`.
The deployed `/opt/qcrl-stream` files/HEAD remain unchanged; only Git objects
were fetched for the diagnostic copy. Daily/observer policies and environment
are not edited, and no public capture or QuantConnect synchronization is run.

Matched evidence root:
`/var/lib/qcrl-stream/reader-burst-matched-20261008-GL20pl/`.
Local ignored review root:
`.qcrl/reviews/receive-recovery-matched-20261008-VCWUcK/`.

## Verification boundary

The recorder's v7 verifier audits complete retained delivery trajectories with
bounded previous-record state, not a hash search. V2's irreversible-disable
validation stays unchanged. Analysis v3 separates restored timing populations
and explicitly keeps unknown/censored denominators. Adapter-failure fallback
cannot supply a complete v3 trajectory; raw evidence is preserved but verification
fails closed. Finalized-session and unseen-message limits remain explicit.

The independent review must compare every originating file and exact file set,
source/corpus/declaration hashes, unit quotas/identities/exits, pacing schedules,
all raw/probe identities, producer-to-delivery statistics, full archives and
source-bound analyses before reporting findings. It additionally checks that
post-recovery marker frame ordinals exceed the complete-frame fence. Callback
entry stamps can precede fence completion due to lock scheduling; a simplistic
timestamp threshold would incorrectly reject otherwise aligned occurrences.

## Independent verification

All **18 cases** completed and verified. All **341 originating files** and the
exact file set matched local SHA-256 inventories after direct SSH streaming.
All **540,000** retained raw bodies matched producer hashes, ordered identities
and the fixed heartbeat/pacing schedule; all **180,000** recorder frames also
matched sealed archives. All six recorded analyses reproduced exactly against
their source declarations/bundles/streams. Actual unit quotas, identities and
successful exits were independently checked. No application timestamp was missing.
All **110 recovery fences** passed complete-connection trajectory checks and
the additional post-fence frame-ordinal boundary check.

Frozen plan hash:
`d30df59c3ab265ee419a6f881e92206a931d44057c7ec6c59e7dd58774f247d9`.
Enhanced independent audit (`qcrl.matched_receive_recovery_audit.v2`) hash:
`45bd680a5f6efba4b3e3aea6dfe3f51016824c17f7fa28d60c85fc7da6626517`.
Its implementation SHA-256:
`ae2f6c4214975960f31ce138cfbdce98e0b8520d494920925019cd5b9552a72c`.
The initial v1 audit is also retained, not replaced:
`09384c2131cd0849ce4ba0b92fc14e00d06d9c4c60b006eed8af9ed685df2001`.
These hashes provide integrity links, not origin signatures or wire evidence.

## Coverage and cost

Each mode/lane contains 90,000 delivered messages across three runs. Callback
known and locally timing-eligible fractions coincided in this cohort; unknown
messages are never assigned timestamps. Bare lanes have no callback telemetry.
CPU values are median measured consumer-process CPU seconds per thirty-second
case, excluding post-loop raw publication/verification, including handshake,
close and receiver-thread work. Delivery p99 values are medians of three run
p99s for producer-begin-to-delivery UPPER bounds, not wire latency or pooled
independent message trials. They include serialization/send and host scheduling.

| Mode / lane | Known callbacks | Median consumer CPU | Burst delivery p99 |
| --- | ---: | ---: | ---: |
| Bare / v2 control | Not measured | 4.172 sec | 0.598 ms |
| Bare / v3 control | Not measured | 4.103 sec | 0.539 ms |
| Receive / v2 | 58.73% | 9.044 sec | 56.506 ms |
| Receive / v3 | 99.19% | 9.914 sec | 254.256 ms |
| Recorder / v2 | 7.35% | 15.039 sec | 718.054 ms |
| Recorder / v3 | 36.89% | 17.181 sec | 853.235 ms |

Receive v2/v3 unknown counts were **37,147 / 726**; recorder v2/v3 unknown counts
were **83,381 / 56,798**. V3 verified 57 receive-mode and 53 recorder-mode fences.
The observer recovers repeatedly without reconnect; it does not promise that
bursts drain enough to keep all markers. V2 remains irreversibly disabled after
saturation, which intentionally saves ongoing marker work but censors timing.

Median consumer CPU increased about **9.6%** in receive mode and **14.2%** in the
full recorder. This is the combined cost of continued tracking, restored markers
and their downstream handling, NOT the isolated cost of occurrence counters.
Largest delivery upper bounds were 249.774/290.343 ms for receive v2/v3 and
917.760/1,300.830 ms for recorder v2/v3. The 500-rate phase p99s for recorders
were 550.161/771.300 ms; these include residual preceding-burst backlog and are
not standalone steady-rate experiments.

Overall producer rates ranged about 999.88–1,000.11 messages/sec. The slowest
burst attained 2,986.06 messages/sec, so not every burst exactly achieved 3,000.
Largest producer deadline lateness was 23.424 ms and send-call duration 11.334 ms.
All such pacing observations are retained. The fixed corpus, one reader, shared
host, finite repeated synthetic shape and three runs limit generalization.
The live five-to-twelve-second age problem was **not reproduced**: the maximum
upper bound in this cohort was about 1.30 seconds. No geographic, upstream,
profitability, fill, queue-position or resource-upgrade conclusion follows.

## Post-audit validation hardening and deployment decision

After the measured revision and independent audit were frozen, the archive
validator was tightened to reject known markers reusing a frame ordinal at or
before their recovery fence, including during a later draining episode. A
rehashed forged-frame regression test was added. This is post-run VALIDATION
hardening, not a change to measured tracker behavior or a silent replay of the
experiment. The independent audit had already checked that condition for all
captured restored markers. Original code, declarations, reports and evidence
remain bound to measured source `ccb7fa8` in the diagnostic clone.

Hardening revision: `0e40b25`. All **525 local tests** passed in 15.155 seconds;
all **525 Linux tests** passed in 41.401 seconds with one expected Python-version
skip, in a third independent diagnostic clone at
`/var/lib/qcrl-stream/receive-recovery-hardened-20261008-LtPt4S/source`.
The new validator reverified ALL six original recorder archives and their exact
original verification results, covering 180,000 frames without rewriting source
artifacts. Post-hardening re-verification audit hash:
`a749648aa1dc3a9947f9a3550659e170209dac5a6b44ab5a5f5584217e30f686`.
Hardened verifier source SHA-256:
`69729eaf34b5184aafa6bf3c18f3eb29020476494a26cbde562a1fce5a5b34be`.
The original source-bound analyses are reproduced with their frozen measured
revision; current source-file checks correctly reject silently substituting
later code for that declared source. The new guard changes no valid result or
measured acquisition behavior, only rejection of falsely attributed frames.

Postflight confirms deployed HEAD remained
`4dd60ba168180243f8600860330dc1afc4816ff4`, clean, with environment SHA-256
`33ea1a9a853f94f4c50c8ebb6e11047d7ee6f8dc4de9041cb770826ce4a86cca`.
Daily timer remained active; public observer inactive. `/tmp` had 921 MiB free;
data volume about 13 GiB free. Matched evidence occupies about 1.6 GiB, retained
on the data volume and locally. Nothing was deleted, upgraded, synchronized to
QuantConnect, collected publicly, traded or changed in Ireland.

Decision: retain v3 for controlled diagnostics, but **do not deploy publicly yet**.
Recovery demonstrably restores legitimate timing, but the full recorder still
has 63.11% unknown callback observations and measurable additional CPU/tail cost.
Next high-value step is separately declared recorder-stage cost isolation:
encoding/hashing, freshness bookkeeping and durable storage. Preserve raw
integrity, explicit unknown coverage and unchanged resource controls; do not
blindly raise marker capacity, strip safeguards or assume a larger node is the fix.
No additional cohort or public deployment is authorized/launched by this record.
