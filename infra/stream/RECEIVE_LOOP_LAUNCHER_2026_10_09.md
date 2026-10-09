# Finite Linux launcher verification — October 9, 2026

Outcome: **launcher implemented and unit-tested, not executed**.
The preceding private worker/evaluator and preregistration were committed and
pushed as `3373945` before this work. See the
[launcher protocol and operation boundaries](../../docs/RECEIVE_LOOP_LINUX_LAUNCHER.md).

The launcher requires explicit execution, canonical dedicated staging, clean
committed source and original corpus/declaration bindings. It refuses prior
evidence and existing private-unit names. It retains the fixed six alternating
cases, original systemd quotas and separate producer/consumer cgroups. Regression
tests finish before measurements; no archive/performance audits run alongside
the measurement workers. Both workers finish before advancing to the next case.

Unit properties and journals are saved before private unit cleanup. Failures stop
the finite sequence without retry and preserve partial/completed evidence,
available unit records, preservation errors and originating file hashes. Public
configuration, deployed commit and service states are compared without automatic
restoration. Daily timer and public stream units are never started or stopped.

Eight launcher tests cover execution opt-in, platform/path rejection, canonical
stage and existing-unit refusal, fixed limits, six-case order, prefix-only cleanup,
failed-launch preservation/no replay, public drift/missing capture and symlink
inventory rejection. All systemd/subprocess launcher operations are mocked.
The first final local suite exposed a macOS `/var` temporary-path alias in a
test fixture; resolving the fixture path fixed it without weakening production
canonical-path checks.

Final complete local suite: **624 tests passed**, 19.428 seconds.
Final Linux/Python 3.9 checks: **18 tests passed**, 2.391 seconds—eight launcher
checks and ten private worker/evaluator tests. They ran in a fresh temporary
checkout over the already pinned SSH connection; only the worker tests used
short numeric-localhost fixtures. No actual launcher/systemd cohort was invoked.
An earlier transfer emitted harmless macOS archive-metadata warnings; the final
verification transfer excluded extended metadata.

No public collector, infrastructure, hardware/quota, credential, trade or
QuantConnect change occurred. No overhead acceptance is claimed. Origin inventory
creation is not independent originating-byte verification, and saved properties
are not yet independently parsed quota/order evidence.

Next: implement and test the independent origin/unit-resource auditor, then decide
whether to run the six preregistered cases. The evaluator remains advancement-
inconclusive until that audit and the full archive/dispatch/performance gates pass.
