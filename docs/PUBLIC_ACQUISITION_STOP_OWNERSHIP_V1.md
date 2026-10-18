# Acquisition stop ownership v1 — offline implementation

**Historical application FAIL and public-feed v3's unresolved closure/coverage
remain unchanged.** This is a prospective implementation, not a reanalysis or
repair of the [retained v3 outcome](PUBLIC_FEED_COUNTS_V3_OUTCOME_20261017.md).
No native validation, new capture or deployment is authorized by this document.

Policy: `qcrl.public_acquisition_stop_ownership.v1`, SHA-256
`dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3`.
The regression test pins that literal. Both prior public-study declarations,
their evidence, original brackets, resource/storage limits and all thresholds
remain intact. This addresses stop ownership, not UTC/RSS precision failures.

## Ownership and ordering

The acquisition thread owns normal completion. The socket-deadline thread owns
emergency FD interruption. Both transitions use one lock and an armed flag.
Cancellation uses that same lock; it cannot erase an emergency that already won.

| Order | Required behavior |
| --- | --- |
| Normal target | The unchanged receive loop caps its timeout at `min(M0+65, attempted+90)` and stops taking new receives at that target |
| Normal claim | Under the deadline lock: no emergency, normal target reached, transport observed OPEN, fresh finite/nonregressing clock still before emergency cutoff |
| Disarm | Assign normal ownership and disarm/cancel the callback before releasing the lock; join it before local close |
| Local close | Begins only after acquisition outcome is decided; a close failure is retained and defeats complete coverage |
| Emergency wins | Mark emergency ownership/fired before raw FD shutdown under the same lock; retain the interruption, socket error and any peer/receive/send fault |
| Cancel wins first | Disarm pending work; a queued callback becomes a no-op, never a later FD shutdown |

The emergency cutoff is prospectively **250 ms after the normal target**, capped
at attempted+90 seconds. This is a control margin, not permission to acquire for
another 250 ms, a timing guarantee or a measurement correction. If the acquisition
thread cannot claim before that cutoff, it cannot report normal completion even
if the callback was delayed and never fired. Equal-boundary events fail closed.

A default-SIGTERM process guard remains armed through acquisition, ending at
attempted+90 seconds. The original earlier connection/readiness guard remains.
A separate default-SIGTERM close guard bounds a stalled close to its five-second
deadline. These guards use the same armed/cancel ordering. Timer scheduling has
no real-time guarantee; the unchanged native unit's 240-second ceiling remains
the external bound. Hard termination can leave only synced partial evidence and
missing final witnesses; it never becomes successful completion.

Subscription success also requires finishing before its declared readiness
deadline with no emergency interruption. No reconnect, recovery or retry is added.
`ConnectionClosedOK` before or at the stop target remains a fault. A transport
already closing at normal claim remains unresolved. A fired watchdog is never
an exemption, including when send/receive returned without raising an exception.

## Placement and publication

No lock, validation, timer or extra clock call is inserted between a supported
receive return and the original monotonic/UTC/monotonic observation operation.
The new event check is at the next loop iteration, outside that bracket. Returned
raw texts still receive their original witness and archive linkage before a
later control fault stops the loop.

New control work is one lock/armed-state transition at stop/cancel, an emergency
check at each loop iteration, an acquisition-lifetime process timer, and a close
process timer. In normal execution these add four control monotonic reads: the
90-second timer's setup read, a fresh clock inside normal claim, and two close-
guard setup reads. They are outside the measurement brackets. Their elapsed and
incremental CPU/RSS overhead is uncalibrated and is not subtracted. The additional
guard threads remain inside the same existing task/memory/CPU limits.

The normal claim's fresh clock becomes `acquisition_ended`, before local close.
The result binds the policy hash and normal transition to the ordered subscription
and acquisition deadline receipts. Offline coverage qualification requires exactly
those two receipts, matching ownership/deadline/end fields, neither fired/error,
and all existing archive/consumer/completion/readiness/no-gap predicates. Missing,
duplicated, mutated or legacy stop receipts cannot establish new-policy coverage.
Historical recordings must continue to use their exact frozen report source.

## Offline fault checks

The tests exercise the actual collector, segmented writer and completion witness,
with a real localhost WebSocket for normal timeout and real socket pairs for
blocked receive, subscription send and heartbeat send. Deterministic event barriers
cover callback-first/cancel-first and normal-first callback ordering; deadline
boundary and stale-clock attempts fail. Peer normal closure stays a fault before
and at the deadline whether or not fired is set. A returned subscription send
cannot erase a simultaneously recorded emergency. A subprocess blocked in actual
collector close is terminated by the default five-second SIGTERM guard, leaving
its partial segment and no invented final manifest. Receipt linkage mutations
cannot qualify coverage. These are local functional checks, not Linux validation.

Final local regression: **1,240 tests passed in 134.043 seconds** on Intel macOS
with Python 3.14.6, including 39 public-runtime/stop checks. Changed source/test
files parse with Python 3.9 grammar. No native code execution is established by
that syntax check, and the explicit real-clock Linux branch remains unexecuted.

## One proposed bounded Linux validation — not executed

Identity `qcrl.public_stop_ownership.validation.v1`; case **StopOwn01**; plan SHA:
`9702f4e923b99873dd4d4a7d641e9be634dbadd3d81f6991dc1b70230c35d808`.
This is the sole proposed validation, justified by the concrete native closure
failure. It is not a timing experiment, public-feed study, cohort or new observer.

One numeric-loopback WebSocket peer stays open until the client initiates close.
It verifies the exact synthetic two-token subscription, sends frozen
`message(0)..message(59)` once, then answers exactly the expected eight PINGs.
Expected complete population: **68 texts**, including those eight PONG replies.
The original 60,000 hard frame cap is retained so frame-limit exit cannot replace
the normal deadline. No peer pre-close, injected deadline fault or second case.
All those fault paths are covered offline rather than added as native runs.

Use real clocks, a future M0 20 seconds after fixture preparation, the original
65-second stop target, 250-ms emergency separation, 90-second acquisition process
bound and five-second close bound. Expected runtime is about 85 seconds plus
bounded setup/close/publication. The peer shares the private unit: this validation
makes **no resource-budget or incremental-overhead claim** and adds no resource
observer. Ordinary completion witnesses supply the functional oracle.

The existing test has an explicit native mode, disabled during normal discovery:

```text
/opt/qcrl-stream/venv/bin/python -m unittest tests.test_public_stop_ownership.StopOwnershipTests.test_real_websocket_normal_timeout_owns_close
```

The one private unit is `qcrl-public-stop-StopOwn01`, working from the exact
frozen source under `/var/lib/qcrl-stream/public-stop-validation-StopOwn01/source`.
Set only `PYTHONDONTWRITEBYTECODE=1`, `QCRL_STOP_OWNERSHIP_NATIVE=1` and the exact
`QCRL_STOP_FREEZE_SHA256` from the sealed packet. Use the installed interpreter,
normal signal dispositions, User/Group qcrl, CPU 75%, MemoryMax 512M, TasksMax 32,
RuntimeMaxSec 240, original isolation, and numeric IPv4 loopback networking only.
Only that stage's precreated empty `evidence` directory is writable. A root-owned
direct execution-confirmation receipt must bind this freeze and one-case approval;
an exclusive evidence claim prevents reuse. No launcher or automatic schedule
is added by this implementation.

Before submission, independently refresh clean-source/selected-file and installed
runtime/binary/dependency/boot/public-state/disk/unit-namespace gates against the
packet. Retain existing select retry disclosure and historical host context as
historical; no fresh-credit minimum or resource change. Missing readiness means
not run. No full Linux test suite or extra smoke is requested by this packet.

Success for this narrow compatibility question requires **all** planned peer texts
equal the ordered archive, verified complete recorder witnesses, matching source/
runtime/unit/domain bindings, normal acquisition ownership, no fired socket timer,
no gap/error/close error, and acquisition completion before the emergency cutoff.
A server-observed `ConnectionClosedOK`, final receipt, exit zero or watchdog flag
alone is insufficient. Independently copy/hash/audit the retained evidence after
the single attempt and stop. Fault/timeout/partial files remain evidence; no retry,
replay, public capture, new target or six-case cohort follows automatically.

Exact source, expected-runtime envelope, freeze and packet hashes are recorded
in HANDOFF after offline regression. They are conditional expectations until
fresh read-only native gates pass. Native staging and execution require the user's
separate approval; none occurred during this implementation.

## Sealed conditional validation packet

Execution candidate: `db25a2db79c53af28e38ba6531f0bba21ebd224b`, 550 selected files.
Freeze: `6861db15528c43baa1d4a0cd3c8b4350dc6c3b8ab6ae240d9a888cc48c4c3c57`.
Packet: 91,690 bytes, SHA-256
`e994325057570d33836183781bf72a84f032238ce0de21ecca7ac597da0d93a6`.
All five packet members and selected source hashes verify offline; the Git bundle
verifies and requires the already-retained de4c10b base. Private controls:
`.qcrl/reviews/public-stop-validation-StopOwn01/`.

Expected runtime payload:
`4dac9c24b3ec1350a627f3316e50060a97e58d57139b4d816a9dc22b1d801f0c`.
This is the retained expected installed envelope, **not fresh native verification**.
The packet separately binds installed socket/context bytes and public baseline
for read-only verification before submission; it does not claim a TLS test.
Fresh matching native gates, exact unit/isolation checks and a separate direct
one-case execution confirmation remain mandatory. No staging, unit, native test,
public request or schedule has occurred. The frozen authorization flag remains
false; packet hashes supply integrity, not a signature or execution permission.

Approval would cover staging this exact new namespace and **one** StopOwn01
unit only, subject to those gates, followed by independent copy/hash/completion/
ownership/fault review. Missing gates or any failure stops with retained evidence.
Later documentation HEAD must not replace this candidate. No follow-on public
capture, repair of v3, timing campaign or cohort is included.

## Subsequent outcome (October 18)

The original proposal and sealed declaration above are unchanged. Separate user
approval authorized its single native case; see the [independently audited
StopOwn01 outcome](PUBLIC_STOP_OWNERSHIP_OUTCOME_20261018.md) for evidence and limits.
