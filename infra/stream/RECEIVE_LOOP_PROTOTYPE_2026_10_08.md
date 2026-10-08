# Isolated receive-loop prototype — October 8, 2026

## Outcome

**The isolated wrappers pass the tested fault and native-equivalence cases.**
No overhead benchmark, recorder integration, new evidence cohort or public
deployment was performed. These results are not a claim of zero instrumentation
cost or complete semantic proof for every possible interleaving.

The diagnostic-only implementation is `infra/stream/receive_loop_probe.py`.
It accepts an explicit source-pinned observation contract and connects only to
numeric-localhost plaintext WebSockets. Public URLs, hostname/DNS routes,
credentials, query parameters and unsupported connection reuse are rejected
before connection. There is no capture launcher or collector selection flag.

## What was implemented

- Instance-local socket-read, gate and assembler-callback wrappers. The library's
  parent receive loop is delegated to once and remains unchanged; no global
  production class is patched by the prototype.
- Installation at overridden receive-thread entry before the unchanged parent
  loop, covering its first gate/read and handshake dispatch.
- Bounded read summaries and flow edges, plus aggregate frame-counter ranges.
  No payload bytes or per-frame unbounded event list is retained in sideband.
- Explicit native EOF/error outcomes, observer-disabled reasons, close versus
  ordinary resume context, and callback/receiver error types without error messages.
- Post-receiver-completion snapshots only. No hot-path files, background writer,
  extra receiver thread, queue replacement, forced release or reconnect path.

Assembler callbacks run under the existing assembler mutex without reacquiring
it. Telemetry locks are released before native gate, socket and flow-control calls.
The wrapper returns native values and propagates the original exception objects.
Observer failures disable metadata observation but do not skip or repeat native
operations. The parent library's normal handling of native failures is retained.

The underlying declaration's `implementation_status=declared_not_implemented`
is intentionally unchanged: its original v1 receipt remains reproducible. This
prototype has a distinct sideband schema marked `prototype.v1`, with benchmark
and overhead acceptance explicitly false. A contract declaration is not evidence
that a recorder is already integrated.

## Fault-injection matrix

| Area | Tested cases | Result |
| --- | --- | --- |
| Socket | Raw bytes, EOF, native timeout/OSError, observer begin/end failures | Exact native result/error, one call |
| Gate | Blocking/nonblocking acquire, false return, native error, context release | Arguments/results retained; lock semantics preserved |
| Contention | Reader blocked on gate; another thread resumes | No telemetry-lock deadlock; reader completes |
| Flow | Pause >16, ordinary resume at 4, closed-assembler resume | Native lock state and distinct close context retained |
| Observer | Clock failure/regression, read/flow event budget exhaustion | Telemetry disabled; transport operations continue |
| Serialization | Incomplete prefix, snapshot before receiver finish, encoded-byte exhaustion | No successful attribution; bounded prefix preserved |
| Dispatch | Native callback error plus observer completion failure | Native exception object preserved, one parent call |
| Installation | Unsupported layout, first gate/read, unchanged parent loop | Unsupported observation disabled; parent semantics retained |
| Real socket fixture | Fragmented UTF-8, duplicates, binary, protocol ping, idle timeout, shutdown | Raw application messages unchanged |
| Real observer fault | Clock fails during initial observation | Handshake and raw delivery still succeed; sideband incomplete |

The blocked gate test checks that a resuming thread can acquire the telemetry
lock while the native gate is waiting. Separate spies check that no telemetry
lock is held inside the native calls. Temporary test spies are restored; they
are not part of the prototype or deployment.

Ordinary observation exceptions and budget exhaustion are tested, not arbitrary
process death or signal timing. A failed or partial sideband must never be
interpreted as proof of unobserved read or pause timing. Native errors remain
native errors; a complete observation of an error is not a successful capture.

## Verification and provenance

Final local full suite: **591 tests passed**, 18.918 seconds.
Final Linux/Python 3.9 verification: **28 tests passed**, 0.565 seconds—seven
source-contract tests plus all twenty-one prototype tests. Linux verification
used a fresh temporary checkout, not the deployed collector checkout.

Only short finite unit-test localhost fixtures were run. No benchmark results,
performance-comparison cohort, sideband capture artifacts, public network calls,
credentials, trades, infrastructure updates, quota changes or QuantConnect sync.
Public collector files and configuration were untouched.

Prototype source SHA-256:
`4fb819d00b6f59c14aedffd0321281e4fdc930721491d561212423ce607ac188`

Final prototype tests SHA-256:
`365ed81802cdeca9ff3eff9da270c2e04c3d31b15271505b67fbfe387f76b90f`

The existing [receive-loop contract](../../docs/RECEIVE_LOOP_OBSERVATION.md) pins
four websockets 15.0.1 files and thirteen method bodies. The contract and pinned
library implementations are not modified by this prototype.

## Remaining gates

1. Integrate the sideband **only into a private numeric-localhost recorder lane**,
   retaining the fixed single-pass writer and diagnostic 128-marker semantics.
   Add independent bounded sideband validation and archived occurrence bindings.
   The prototype's own frame counter is not yet an independently verified link
   to the receive-v3 marker ordinals or archived raw messages.
2. Declare a finite baseline-versus-instrumented overhead comparison before any
   measurements. Preserve corpus, encoding, caps, quotas, memory/tasks/runtime,
   durability, pair ordering and complete originating evidence.
3. Require no sideband loss, preserved raw/occurrence integrity and acceptable
   measured CPU/memory/tail impact before using the observations for attribution.

No public rollout is authorized. A prototype snapshot's `complete_observation`
describes its retained operation brackets, not stream completeness, fill truth,
wire-arrival timing or passed performance acceptance.
