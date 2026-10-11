# Isolated completion-witness prototype: local verification

Implemented separately under `infra/stream/recorder_completion.py` and
`infra/stream/recorder_completion_lane.py`; protocol details are in
`docs/RECORDER_COMPLETION_WITNESSES.md`. No legacy execution-truth source file,
public default, archive format, frozen acceptance budget or source pin changed.

## Tests

All **938 local tests passed** in 40.931 seconds on Python 3.14.6, including
22 new completion tests. Coverage includes FIFO duplicate occurrence/hash links,
source/clock/spec/single-use guards, absent default connector, write/flush/fsync
failure without observer replay, observer and disable faults, partial/crash
prefixes, missing footer, regressing clocks, retention/encoded-output caps,
rehashed chronology/watermark/authority tampering, and native-call count parity.

The deterministic clock comparison produced identical reference/prototype archive
bytes and identical file-sync call counts. AST comparisons preserve reference
collector control flow and writer operations after stripping only declared hooks
and prototype guards. These establish the tested semantic behavior, not equal
runtime performance under real clocks, scheduling, I/O or network traffic.

An initial implementation changed the reference recorder. The full suite then
failed nine frozen-source tests and one AST-equivalence test. The reference files
were restored exactly, and the prototype moved outside the frozen execution-truth
module inventory. No test/pin was weakened to accommodate the change.

## Retained offline smoke

Review: `.qcrl/reviews/completion-witness-prototype-20261010-Asexz8up`.
Verification receipt:
`34d61fd0098a639a1892c95ce0e8ffe2ce9e508a0f38bf9ccc2d42908642b264`.

A fake-clock/injected-transport capture retained two identical application messages
as distinct occurrences. The independent sideband verifier matched every frame
to ordinal/hash/connection and successful covering watermarks, including seven
successful data-file sync barriers. It re-read the saved sideband rather than
trusting the in-memory result. Eleven exact source/test/spec/document files were
archived and hash-verified; the archive and sideband file hashes remain in the
exclusive offline receipt. No private/public endpoint was contacted.

Clock domain and runtime identity are retained caller/process evidence, not an
independent Linux PID/boot/cgroup binding. The sideband is post-collection and
cannot recover an unpersisted witness tail after a real process/host crash.
File sync, manifest publication and replication are distinct boundaries. All
acceptance/order flags remain false, and fake durations have no performance meaning.

## Next gate

Commit/source-freeze, followed by one isolated native Linux compatibility smoke
with actual clocks and file barriers. Then separately declare an actual-recorder
localhost application-budget test. No renewed synthetic probe-cost cohort,
deployment, public capture, infrastructure change, Git push, QC sync, credentials
or trading was performed or authorized by this prototype report.
