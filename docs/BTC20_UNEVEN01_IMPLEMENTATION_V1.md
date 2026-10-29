# BTC20-Uneven01 offline implementation — October 28, 2026

**Historical application FAIL and v6/PreClosePub01 partial verdicts stand.**
This implements the [milestone 3 design](MILESTONE_3_BTC20_UNEVEN01_DRAFT_V1.md)
prospectively, with explicit `--study-version v7`. Legacy v5 remains the default;
v5/v6 literal plan hashes are pinned unchanged. No old evidence is regenerated.
No new capture, native staging or scheduler is authorized by implementation.

Named question: unevenness of locally archived text counts over one fixed
20-second primary, separately from book eligibility and unavailable acquisition.
The proposed single approval target is October 30, 2026, event 16:00–16:05 UTC
(noon EDT); primary 16:01:00–16:01:20 UTC, arm 16:00:55, tail through16:01:22.
The exact packet, rather than this document, must bind source/runtime and approval.

## Identities and wiring

Plan `qcrl.public_feed_interval_counts.study.v7` SHA:
`eaaf6bfa25d0b00fd7985506dfb877680342397a0d47b1f31dfcdb68a3d09049`.
Phase policy `qcrl.btc20_phase_quotas.v1` SHA:
`a19febf2bbf1824f11d3bdb4c464e085b62f89ce8831375ffc922f374e8df033`.
These are explicitly pinned in tests. New worker/report/operator CLI selection,
supported-plan checks, actual collector deadline, storage guard, missing-control
null rows, interval counting and recovery eligibility now use the selected
20-second plan; the old 60-bin/M0+65 behavior is preserved for old plans.

The stream spec still binds 90 seconds /60,000 maximum texts and the original
storage limits. An additional plan/policy-bound allocation governs the shorter
schedule, without changing the frozen legacy spec schema or measurement brackets.
Archive footer binds the policy and terminal-allocation ordinal; result receipts
bind phase counts, actual bytes, received/archived counts and any unarchived
occurrence. The report independently replays quotas from verified archive lines
and completion intervals. Quota corruption with valid raw linkage preserves raw
counts while withholding eligibility; missing completion is not treated as zero.

## Exact allocation and stop semantics

| Input / event | Frame allocation | Byte allocation and disposition |
| --- | --- | --- |
| Return-before < M0 | Prewindow, cap8,000 | Encoded archive bytes to32 MiB stop threshold |
| M0 <= return-before < M0+20 | Primary, cap50,000 | Encoded archive bytes to128 MiB stop threshold |
| Return-before >= M0+20 | Tail, cap2,000 | Encoded archive bytes to8 MiB stop threshold; late returns still retained/disclosed |
| Boundary-straddling text | Once, using original return-before endpoint; exact boundary belongs to the later phase | Full record charged to that phase; analysis keeps the full interval, ambiguity and possible prewindow/tail overlap |
| Bootstrap book/batch | Charged in full like any incoming text, even when bootstrap is incomplete | No quota exemption or batch expansion; strict eligibility begins after fresh books for both assets in that epoch |
| Reconnect/resubscription | Same cumulative counters; no reset or borrowing | Control records consume their actual append-time phase; new books required; old faults/gaps remain |
| Accepted metadata/duplicate/PONG | One incoming occurrence each | Full encoded row charged; no dedup, content-based quota exemption or favorable filtering |
| Oversized returned text | Charged before size validation finishes | Attempt ordinary archival under existing4-MiB record/storage bounds, then fatal; no reconnect. If it cannot fit/write/link safely, disclose it and stop |
| Library rejects size before returning | No application return observed | Retain transport fault, including1009; no invented text count or payload. Oversize/certificate faults do not trigger another connection |
| Binary return | One received occurrence, allocated when timing is valid | Existing frame schema cannot archive bytes as a valid text; explicit unarchived receipt and fatal stop, incomplete completion remains unresolved |
| Invalid return clock/linkage | Count the observed return; phase is unallocated if timestamp unavailable | Do not fabricate time/phase or reconstruct payload. Explicit unarchived/unlinked disclosure and fatal stop |
| Acquisition control | No incoming-text count | Actual encoded row length, assigned using its original archive append timestamp |
| Terminal records | No new incoming frames | Separate hard32-MiB allowance, including session_end; no unlimited terminal-summary exemption |

A supported text reaching a frame ceiling is appended and linked first, then
acquisition stops with `phase_limit`. A byte crossing is charged after actual
writer return, then stops before another receive, including when a control/PING
record caused exhaustion. No idle/drop-and-resume at M0 and no extension/retry to
replace censored slots. A simultaneous genuine foreign/clock/storage/transport
fault still wins over an apparently benign quota stop; faults are never cleared.

Each phase byte threshold may be crossed by one maximum4-MiB record. Total logical
accounting bound is32+128+8+3×4+32 = **212 MiB**, within the original1-GiB raw limit.
Admission for terminal records checks exact encoded length before write.
Accounting wraps the existing gzip writer, so no duplicate encoding or payload
estimate is used. Only controls are decoded to reuse their existing row timestamp;
incoming frames use the existing pending return-before timestamp. All allocation,
classification, hashing and metering occurs outside unchanged UTC/RSS brackets.
This added work consumes inclusive budgets; no cost is subtracted or claimed free.

An append/sync/storage/record-ceiling failure can leave partial or visible bytes.
`unarchived_occurrence.archive_status=not_proven_fully_appended` deliberately
does not assert those bytes are absent or durable. It retains sequence, connection,
payload type, original return interval/phase where available, bounded reason,
and UTF-8 size/hash where safely obtained. There is at most one such terminal
return because it ends acquisition. Received and archived counts stay separate;
clock-failed returns are counted as unallocated. Existing completion pending/
failure state is preserved and cannot become complete population linkage.

Original global ceilings remain60,000 frames,1-GiB raw/256-MiB compressed,
32-MiB completion,64-MiB auxiliary including4-MiB pre-close resources,1-GiB spool,
1,024 files,2-GiB initial free disk/1-GiB reserve; CPU75%,512MiB,32 tasks,240s.
No compression ratio or guaranteed message rate is assumed. The nominal27-second
exposure leaves about63 seconds before the existing90-second acquisition/
publication guard at an on-time first attempt; this is scheduling headroom, not
a persistence guarantee. Final close remains separately bounded at five seconds.

## Eligibility, CPU and cleanup ownership

Eligibility means only a linked return interval strictly inside a same-epoch
fresh-book window. Every row retains `feed_activity_upper=null`; venue completeness,
recovery of missed messages and full-minute population remain unproven. Available
zero archived texts and unavailable silence stay distinct. No raw/eligible
population is promoted to complete venue acquisition.

The existing pre-close publication policy is mandatory in a v7 freeze: archive/
completion/checkpoint, stop/join <=3s, finished observer result or unavailable
component, then final close. No new observer or in-bracket clock is added. Existing
five-second close/library race and all guards/faults remain. Resource qualification
stays null. **`original_60_second_cpu_window=null`**, explicitly labeled
`unavailable_short_primary_no_prorating`, is present even on missing-control reports.
Neither a 20-second prefix nor inclusive CPU is a prorated application pass.

Inspector v1 remains unchanged in policy meaning. New explicit v2 permits the
single public worker binding instead of pretending it has a parent/child pair:
`qcrl.exited_unit_inspection.policy.v2`, SHA
`43891e7ffabd8ec4b4955bf5cc8ef483fce2b2b68b5678669c10a90836aae99b`.
The controller prospectively records complete InvocationID/ExecStart/start/boot/
cgroup/PID binding at release. Its v7 cleanup owner checks the freeze/case/root/
unit, uses repeated read-only exited-unit checks, then stops only that exact exited
private unit. Active/foreign/unresolved binding means no fallback stop. Missing
TasksCurrent remains unknown; inspector itself grants no stop authority.
Exclusive case claims prevent another protocol owner adopting the unit, but the
check/action gap is not atomic against an external administrator restart. Retain
that limitation and independently observe live/post-run state in the packet audit.

## Verification scope

Local actual-path tests cover one-before/exact/one-after quota edges; real encoded
byte exhaustion retaining the crossing text; all three frame ceilings; a real
return bracket straddling M0; control/PING exhaustion before receive; bootstrap,
reconnect and no-reset semantics; returned oversize retention and record-ceiling
failure disclosure; binary/timing/disk faults; terminal reserve; actual worker/
checkpoint/resource/report wiring; missing controls and corrupted allocations;
CPU unavailability; explicit v7 unit command; and cleanup refusal for active or
foreign bindings. Full prewindow/primary saturation cases use separate bounded
child processes rather than accumulating their large populations in readiness.

Final full suite: **1,342 tests passed in 178.761 seconds** with
`PYTHONPATH=tests .venv/bin/python -m unittest discover -q`. Changed Python files
Focused collector/recovery/publication/inspector integration: **88 tests passed
in 23.784 seconds**. Changed Python files
parse with Python3.9 grammar locally. These are Intel Mac/Python3.14.6
offline tests, not installed-runtime execution. Fresh read-only installed-byte
inspection through old retained v6 source verified unchanged runtime/TLS/public
state and unused new namespace at **2026-10-29T02:39:36Z** (October28,22:39 EDT),
free disk5,943,533,568 bytes. It started zero metadata requests/subscriptions/units.
Credits remain historical/unavailable context, with no invented minimum. This is
not Linux functional, timing, memory or public-path validation of v7. Exact final
test counts/source/freeze/member identities belong in the later approval packet.
