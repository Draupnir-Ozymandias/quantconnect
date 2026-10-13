# Isolated absolute-monotonic wait adapter

`infra/stream/recorder_absolute_wait.py` is an offline-tested prototype, not
integrated into any current scheduler, collector, worker or launcher. No native
binding or sleep was performed during this development step. The preceding
failed counter smoke and incomplete finite wake diagnostic remain unchanged.
Re-audit the latter from its frozen `1e44033` checkout, not this newer tree: the
broad execution-source inventory includes new prototype/test files.

## Purpose and interface

The October 12 clock-only run retained 11 observed wakes and one skipped target.
Its 60-second waits returned roughly 59–60 ms late. The published Python/Linux
select-slack mechanism provides a hypothesis, not installed-runtime causal proof.
This prototype prepares an implementation-separated alternative for future
measurement without changing timer slack, affinity, priority, instance size,
Python version, timing budgets or the original measurement plan.

An injected `AbsoluteWait` takes an integer-nanosecond monotonic clock and an
injected four-argument syscall function. `wait(target_ns, execute=True)` performs
at most one call with `CLOCK_MONOTONIC` and `TIMER_ABSTIME`. A past/equal target
is retained unknown without catch-up. Remaining waits over 60 seconds are refused.
This is a per-call safety cap, not authority for an unbounded loop or a native
experiment. No native CLI or caller integration is introduced.

The optional native binder requires an explicit execution gate before loading
libc through CDLL. It supports only declared Linux glibc LP64 aarch64/x86_64,
64-bit pointers/longs, a 16-byte timespec, and the expected monotonic clock ID
and implementation. It binds the libc symbol with explicit ctypes argument and
return types. `remain` is null because this is an absolute deadline.
Unsupported ABI/platform/symbol availability fails rather than falling back.

The Linux interface accepts an absolute deadline and reports positive error
numbers directly. An interrupted call is not automatically restarted. Our
adapter retains any error, including EINTR, without resubmitting the deadline.
Absolute deadlines do not prevent delayed CPU resumption.
[Linux clock_nanosleep documentation](https://man7.org/linux/man-pages/man2/clock_nanosleep.2.html).

## Precision and retained evidence

Timespec seconds/nanoseconds are constructed by integer division, with canonical
nanoseconds in `[0, 1_000_000_000)`. Timestamp range is capped at signed 64-bit
nanoseconds. The optional conversion from float seconds ceilings the exact
represented binary float using its integer ratio, avoiding an intermediate
rounded float multiplication that could move the deadline earlier. It does not
recover precision already lost in a floating-point clock value. Prefer an
integer monotonic epoch and integer cumulative interval grid in a later study.

Each result retains the exact target, inclusive pre-request/return clock pair,
remaining duration, attempted flag, return code, signed lateness, error/status
and zero retry count. Clock regression, early return, nonfinite/noninteger clock
values, invalid return codes and callable failures are refused or retained
unknown. A stateful adapter also detects regression between calls. Preparation,
FFI marshaling and interpreter resumption are inside the inclusive envelope;
this does not reveal exact kernel entry, expiry or runnable-to-running delay.

Hash verification establishes content consistency, not native origin. Native
origin, performance acceptance and trading authority remain false, even for an
observed late return. The prototype does not repair prior missed windows,
subtract overhead, busy-spin, install tracing or set kernel/process controls.

## Offline coverage and next gate

Injected tests cover exact request fields/FFI layout, rounding and nanosecond
rollover, huge/invalid targets, already-missed/over-cap waits, interruption and
other errno values, invalid return conventions, callable failures, early/late
returns, within/between-call clock regression, execution/platform guards, hashes
and authority flags. FFI tests substitute a callable; no real libc sleep is used.

Next: independently validate the native ABI/symbol envelope and preregister a
finite comparison with the select-backed reference. Freeze ordering, integer
targets, artifact bounds, unknown/interrupt handling and stopping rules before
looking at new native results. Native compatibility and actual improvement both
remain unverified. Keep all original budgets, evidence and verdicts intact.

Verification: 1,028 offline regression tests passed in 42.549 seconds in the
established Python 3.14.6 / websockets 15.0.1 environment. All 53 focused
counter/scheduler/wake/launcher/absolute-wait tests passed. Python 3.9 syntax
parsing passed for the new module and tests; there was no real native syscall,
EC2 execution, public change or modification to previous measurement plans.

October 12 continuation: the finite design is now separately declared in
[ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md](ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md).
Only its offline declaration/target expander exists; native compatibility,
collector/evaluator/launcher implementation and execution-source freeze remain
outstanding. This does not integrate or run the adapter.
