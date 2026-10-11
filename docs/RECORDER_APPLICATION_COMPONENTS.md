# Localhost application-budget implementation — isolated components

The preregistered protocol remains unchanged. Its saved declaration hash is
`c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade`.
The implementation lives outside the frozen execution-truth module inventory:

- `infra/stream/recorder_application_worker.py`: finite case preparation, real
  numeric-loopback WebSocket producer/adapter/recorder, future shared epoch,
  subscription/readiness/boot/actor bindings, unchanged 60,000-message schedule,
  bounded control traffic, no automatic replay and exclusive artifact publication.
- `infra/stream/recorder_application_resources.py`: bounded native cgroup-v2 and
  current VmRSS reader; PID/starttime/boot/member checks, ancestor CPU/cpuset limits,
  memory/events/counters, current RSS over unique live actors, identity-race errors,
  one-second samples and enclosing complete-window CPU reads. Missing root control
  files remain explicit null values; no fabricated root quota is introduced.
- `infra/stream/recorder_application_evaluator.py`: independent archive/sideband
  verification and ordered raw rescan, producer deadline/phase checks, per-phase
  nearest-rank timing gates, conservative CPU/current-RSS gates, and fixed six-case
  aggregation. Known failed prefixes survive missing final evidence.

## Boundaries preserved

The reference recorder, writer, completion prototype, preregistration sources,
budgets, corpus and source pins were not edited. New case artifacts additionally
bind implementation/test/fixture hashes; workers and the evaluator refuse drift.
Programmatic worker entry points require explicit execution. There is no cohort
CLI/launcher, cloud deployment, public connector or scheduled capture added here.

Producer and recorder must have distinct dedicated cgroups on the same boot.
Recorder/resource-observer threads share the recorder process/unit; producer
startup/end observations are retained separately. Resource read errors stay in
their scheduled slots. No RSS lifetime-high-water substitution, interpolation,
quota assumption or pooled timing rescue is allowed. Nonregular/symlink resource
leaves are refused; directory identity changes and process membership races are
errors. Descendant cgroups are unsupported rather than silently omitted.

The resource observer uses bounded in-memory rows and the completion prototype
publishes witnesses after close. A real process kill can lose those unpersisted
tails. Missing publication is not proof of success or durable crash recovery.
Counter reads/sampling add work included in the recorder resource envelope.

## Tested, not yet accepted

Component tests cover fixed population/order, duplicate corpus strings, explicit
execution/loopback guards, failed sends without retry, percentile/phase behavior,
nonfinite and regressing timings, known failures alongside unknowns, conservative
CPU windows, RSS limits, missing/raced samples, changed quota, counter resets,
current native-file fixtures, duplicate/missing actors, descendant groups, FIFO/
symlink read refusal and incomplete failure prefixes.

A tiny real WebSocket functional test delivers 68 strings through the actual
recorder with native clocks and file I/O. It verifies subscription, both initial
books, frame-limit completion, preserved duplicates and completion/archive links.
This is not a shortened acceptance case, does not estimate the declared workload's
performance, and does not populate the six-case cohort.

All **960 local regression tests passed** in 41.847 seconds on Python 3.14.6.
The focused component/loopback/completion run passed 40 tests. Native cgroup file
behavior has only fixture coverage in this turn; Linux unit integration remains
unverified. The saved preregistration and all six frozen recorder source files
were checked unchanged after testing.

The component auditor deliberately appends
`independent_execution_source_unit_origin_binding_not_implemented` to unknowns.
Even if every component gate passes, its aggregate verdict cannot be accepted.
Internal hashes and process-reported identities are not independent launch/origin
evidence. Acceptance/execution/order-authority flags stay false.

## Remaining gate

Build the isolated Linux launcher and independent unit/origin verifier. Bind actual
unit properties/commands, live identities, dependency versions, source snapshot,
host concurrency and instance credit configuration before evaluating acceptance.
Retain producer resource disclosure and public before/after checks. Test launcher
and verifier lifecycle/fault paths, then source-freeze and run a separately approved
native compatibility smoke. Only after that freeze/review may the finite six-case
cohort be launched. No EC2 access or changes, cohort execution, Git commit/push,
QuantConnect sync, credentials or trading occurred during this implementation.
