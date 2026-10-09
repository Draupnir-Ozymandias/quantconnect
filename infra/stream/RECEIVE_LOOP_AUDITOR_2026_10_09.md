# Independent origin/resource auditor — October 9, 2026

Outcome: **read-only auditor implemented and fixture-tested; benchmark unrun**.
See [audit inputs and boundaries](../../docs/RECEIVE_LOOP_AUDIT.md).

The auditor requires a separately obtained origin-inventory file-byte hash and
prospectively frozen source commit. It independently verifies the complete evidence
file population twice, outer/inner launcher metadata bindings, unchanged public
state and source/preregistration receipts. It parses saved systemd limits/security,
successful exits, bounded monotonic lifetimes, PID/boot/cgroup identities, actual
alternating worker order and consumer measurement-window containment.

It invokes the existing uncached archive/raw/occurrence/dispatch verifier and
performance evaluator for all six cases. A metric pass can advance only to
diagnostic interval analysis after the independently anchored resource/order gates
pass. No public rollout, trading or event-specific causality is inferred.

Nine new tests cover external anchoring and exact bytes/populations; unsafe paths,
symlinks and metadata mismatch; missing/duplicate/unbounded properties; incorrect
CPU/memory/tasks/runtime/security settings; failed exits; PID/boot/cgroup mismatch;
measurement-window containment; reanchored wrong worker ordering; and combined
metric rejection. The metadata pipeline fixture mocks only the previously tested
full archive/corpus verification layer. It is not actual cohort evidence and does
not demonstrate live systemd resource enforcement or measured overhead.

Final local suite: **633 tests passed**, 20.314 seconds.
Linux/Python 3.9: **19 tests passed**, 2.481 seconds—nine auditor checks and ten
worker/evaluator tests, in a fresh temporary checkout over pinned SSH. Only short
localhost unit fixtures ran. No launcher, public capture, systemd measurement,
infrastructure/resource change, credential use, trade or QuantConnect sync occurred.

Limitations remain explicit: caller must obtain the inventory anchor independently;
hashes are not signatures; archived worker cgroup identity is not an external kernel
observation; saved configured limits do not measure scheduler exclusivity; whole-unit
MemoryPeak may be absent and includes post-window work when present. Shared-host
noise and conservative finite-cohort thresholds remain unchanged.

Next: commit/source-freeze this auditor, then separately authorize the six-case Linux
cohort and independent originating-byte download/audit. Until that actual audit,
overhead and advancement remain unestablished. Auditor changes are local and
uncommitted at this handoff; no evidence from earlier cohorts was rewritten.
