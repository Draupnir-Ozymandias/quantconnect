# October 30 offline defect review

The [original outcome](BTC20_UNEVEN01_OUTCOME_20261030.md) remains **partial/unresolved**;
historical application **FAIL** stands. Retained receipts, frozen source/report,
original thresholds and unknowns are unchanged. This review performs no remote
command, mutation, replay, capture or new packet preparation.

## Shutdown SIGTERM: established mechanism, unproven historical sender

Retained worker exit status is 15/TERM, no final consumer; checkpoint proves
normal acquisition ownership and a sealed archive, not final close. The independent
controller/worker bindings saw original default HUP/TERM dispositions. No retained
signal-sender trace or close-entry/completion trace identifies who sent SIGTERM.
The controller does not stop the unit before worker exit; its failed inspector
also prevented the subsequent cleanup stop. The observed exit is about six seconds
after acquisition end, consistent with checkpoint/resource publication followed
by the five-second close guard. Timing consistency is not sender attribution.

Frozen `recorder_public_capture.collect` arms `ConnectDeadline(now+5)` immediately
before `conn.close()`, and constructs the WebSocket with `close_timeout=5`.
`ConnectDeadline.interrupt` sets a durable fired flag and calls
`os.kill(os.getpid(), SIGTERM)` under its lock. In websockets 15.0.1,
`Connection.close` enters `send_context`; that code starts its own close timeout
later, waits for the receive thread, and can perform further socket/thread cleanup
on expiry. Thus the external guard supplies **no margin for the library's full
five-second wait plus cleanup**. Lock contention/scheduling can widen this race.
It is a confirmed design limitation, not proof that it caused this recorded signal.
Local library `sync/connection.py` SHA
`02f667220b611cf92312cc43464ba9b0714432a4659c0480d5793271301b3a06`
exactly matches the frozen runtime inventory; this is source review, not a new
Linux execution or evidence of peer behavior.

A deterministic test executes the real collector and real process-guard callback
with manual timers/fake time and intercepted `os.kill`. At the shared five-second
boundary the guard can win; its fault survives cancellation and a returning close,
and earlier receive faults remain. A just-before-boundary return does not fire.
Normal acquisition remains a separate component even when subsequent close fails.
Existing local blocked-close subprocess tests retain publication and terminate
under default SIGTERM. These demonstrate possible paths, not historical attribution.
No shutdown timeout/handler/threshold is changed in this patch. A future design
could reserve explicit library-cleanup margin within the same hard bound; that
would require a prospective contract and cannot guarantee prompt cleanup. No such
execution packet is prepared here.

## Confirmed defect: lifecycle display treated as immutable command identity

Frozen inspector compared complete `systemctl show ExecStart` strings. The retained
before/after pair differs only in stop timestamp, code and status; those fields
are lifecycle data in systemd's display, not a changed command. Exact InvocationID,
start timestamp, path/argv/ignore_errors and WorkingDirectory did not change.
The frozen rejection remains failed; no revised code is applied to authorize a
historical stop or rewrite the audit.

The successor parses the bounded, observed single-command serialization and compares
**path, complete argv display and ignore_errors byte-for-byte**. It retains start/
stop/PID/code/status in the full raw observations; it never shell-splits/unescapes
argv. Unknown structured fields, malformed/multiple commands or unsupported formats
fail closed. Opaque legacy bindings continue to require exact equality. Id,
InvocationID, WorkingDirectory, monotonic start, boot, original PID/start absence,
empty/removed original cgroup and numeric/missing TasksCurrent rules are unchanged.
Two full raw rounds must still agree, so exit status/display changes between
rounds remain unresolved races. Fault status is retained, not converted to success.
Inspector stays read-only and never grants stop/scientific/resource acceptance.

Comparison identity `qcrl.systemd_exec_identity.v1`, SHA
`821675a9cb9f7897203e57d04da00213d5d39fb00274998dce8a837b7943d7ca`,
is pinned in a regression and included in new inspector receipts. Original v1/v2
policy dictionaries/hashes and v7 science plan remain untouched; source plus this
new comparison binding must be frozen prospectively. Tests cover lifecycle-only
changes, changed command/path/ignore_errors, malformed/multiple commands, raw
status races, retained faults/unknown tasks and actual controller cleanup wiring
with injected read-only adapter/systemctl. No live stop was performed.

## Confirmed defect: integer epoch converted through float seconds

Public worker computes an integer epoch, then passed only `epoch/1e9` to the
observer. Observer's correct legacy rule ceilings the exact represented float.
For recorded integer 2311776625614725, that round trip yields 2311776625614726.
This explains the exact 1-ns mismatch, without a tolerance or clock-drift hypothesis.
Frozen checkpoint and resource result remain unequal and unqualified.

The successor public worker passes its original integer epoch explicitly through
`observe_absolute(..., epoch_ns=epoch)`. Observer and optional audit binding validate
bounded integer/type and matching represented seconds, preserve the original
integer grid, and perform no re-anchoring. Callers with seconds only retain the
original exact-float ceiling rule. Report linkage remains exact; a rehashed 1-ns
mismatch is still rejected. No fresh read, RSS definition, bracket placement,
threshold, CPU lead, wait retry or storage limit is changed.

Regression tests cover the recorded uptime and adversarial small epochs, exact
integer targets through the real observer/fake syscall, invalid or contradictory
inputs before wait binding, and actual consume/collector/checkpoint/resource/final
publication with a rounding-sensitive integer. The original complete 60-second
CPU gate remains unavailable for this 20-second study. Correcting linkage cannot
repair wide RSS brackets or establish native resource acceptance.

## Baseline reconciliation and validation

Lupus's development checkout preceded the executed source's independent quota
stop-order correction. This patch carries over exactly the five production lines
and existing cross-phase frame/control regression from `3c443e6`, so future work
does not regress the execution baseline. No plan/quota/hash declaration changes.
Tests use synthetic fixtures, not a replay of the retained capture. Frozen historical
reports must continue to use their own exact source.

All **1,351 tests passed in210.741s**;100 focused tests passed in29.877s.
Changed Python parses with3.9 grammar. All62 retained files, original archive seal
and580 frozen source hashes remain unchanged. Private logs and the arithmetic/
command comparison receipt are retained in the transfer directory. All new validation
is Intel macOS/Python 3.14.6 offline, including local socket/subprocess fixtures;
it is not Linux/native validation of these successor fixes. No capture, replay,
remote mutation, threshold change or new execution approval packet is authorized
or performed. Unknown final close, signal sender, continuous RSS peak, incremental
overhead, independent UTC accuracy and internal retries remain unresolved.
