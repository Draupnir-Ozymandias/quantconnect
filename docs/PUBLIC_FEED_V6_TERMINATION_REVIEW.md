# V6 offline termination and publication review — October 21, 2026

**Historical application FAIL and v6 partial/unresolved remain unchanged.**
This review adds local regressions and a proposed publication change, not a new
capture, threshold, combined acceptance badge or retrospective repair. The
[retained outcome](PUBLIC_FEED_COUNTS_V6_OUTCOME_20261021.md) remains authoritative.

## What the retained evidence establishes

The shared 60,000-text limit ended acquisition at M0+53.085595 seconds, before
its M0+65 deadline. This is a bounded frame-cap exit, not normal scheduled
completion. Both epochs and the first receive fault survive. Archive, completion
and acquisition checkpoint sealed before final close; final consumer/resources
are absent. SIGTERM followed checkpoint publication by approximately five seconds.
That timing is consistent with the declared close guard, but neither its sender
nor the exact blocked operation was retained. This review cannot identify them.
The independently sealed copy still hashes to
`30ff87a242af69579600eee08781d6fc7c4eea491bcfb7c3601e61bf762139cd`.

Recovery/resubscription/fresh-book observations answer the narrow recovery
question. More public recordings are not required to establish that observation.
Full-minute coverage and original resource/precision acceptance remain unproven;
five UTC-width violations are a separate unresolved requirement. No publication
change would repair them, the missing acquisition interval or missing messages.

## Code findings and deterministic checks

`recorder_public_capture.collect` leaves the acquisition process guard armed
through archive sealing and pre-close publication, cancels it, then starts a
separate five-second process guard around final `conn.close()`. The connection
was constructed with the library's own `close_timeout=5`. Equal nominal bounds
provide **no reserved cleanup margin**: even an on-time library timeout can
compete with process termination before socket/thread cleanup returns. Ordinary
scheduler delay, lock acquisition and publication are not covered by a claim
that the library timeout guarantees return within five seconds.

Inspection and local execution of installed websockets 15.0.1 show:

- `Connection.send_context` acquires `protocol_mutex` before setting the close
  deadline. Contention can therefore delay entry beyond the nominal close timeout.
- A receive-thread timeout triggers `close_socket`, followed by another thread
  join without a timeout. The external process guard remains necessary.
- `Connection.close` catches the resulting `ConnectionClosed` exception. It can
  return after timeout-induced transport shutdown with no peer close frame.
  Return establishes completion of that cleanup call, not a graceful peer handshake.
- Receive flow control can pause the library receive thread when queued messages
  are not being consumed. Final acquisition has stopped consuming. This is a
  plausible close-delay path, **not an established explanation of v6**. The peer's
  earlier slow-consumer diagnostic does not identify the final-close bottleneck.

Frozen report `close_verified`/`cleanup_close_completed` labels must be interpreted
under their original contract as cleanup-return evidence, never independent
proof of a graceful peer handshake. V6 has neither final label established.
Normal acquisition ownership is separately proved: a later cleanup fault does
not erase that ownership, and ownership cannot erase the cleanup fault. V6's
frame-cap exit has no normal scheduled ownership in the first place.

Production `recorder_public_study.consume` stops/joins its resource observer and
publishes `consumer.json` only **after** `collect` returns from close. Therefore a
process kill during close prevents the resource result from being published even
if the observer had already completed useful samples. The pre-close checkpoint
contains acquisition evidence only. Its literal `observer_thread_alive=true` is
not a sampled observation or a substitute for the missing rows. This ordering is
established by code; whether particular missing samples actually existed in v6
cannot now be established.

New `tests/test_public_termination_review.py` exercises four actual paths:

1. Installed library timeout/forced shutdown returns without a peer close frame;
   deterministic thread-join seam, no wall-time or native timing claim.
2. The actual recorder's close guard wins while library close subsequently returns;
   SIGTERM is intercepted locally, fired state/close fault persist, and acquisition
   ownership remains a separate fact.
3. The actual recorder/writer/witness pipeline reaches exactly 60,000 texts,
   snapshots a verified sealed archive before close, retains a close fault, and
   never labels the cap as normal scheduled completion. No reduced test-only cap; a bounded child process releases the large witness
   allocation before subsequent suite tests.
4. A subprocess with the installed library blocked on its protocol lock is killed
   by the real unchanged five-second guard; completion/checkpoint survive and final
   consumer is absent. No remote execution or real feed is involved.

Existing fault-publication, recovery and v6 integration regressions additionally
exercise publication failures/linkage, blocked I/O, deadline/peer-close races,
retry-close faults and cancellation races. These are Intel macOS offline results,
not Linux scheduling, public transport or resource acceptance.

Focused checks passed **44 tests in 23.450 seconds** before the frame-cap test
was isolated into its own bounded child process; the final four-test file was
then passed **4 tests in 12.920 seconds**. No full-suite or new Linux result is claimed.

## One proposed change, before any further native proposal

Introduce a prospectively identified **pre-close resource publication** contract.
At the existing pre-close acquisition-publication boundary, ask the existing
observer to stop, perform a bounded join, and durably retain only its completed
result if available. If it has not returned, record unavailable/live status;
do not race-copy its mutable state, fabricate rows, catch up missed slots or
weaken any resource gate. Link the component artifact to case, process/boot,
epoch, resource plan and acquisition checkpoint. Final consumer can reference it
but remains separately contingent on final cleanup returning.

This moves observer stopping earlier—from after cleanup to before cleanup—and
must explicitly declare that execution-envelope change and affected terminal
slots. Keep the original sample definition, UTC/RSS brackets, grid, thresholds,
90-second acquisition/publication guard, five-second close guard, unit bounds,
frame/storage budgets and prior evidence. Bounded join and durable publication
consume existing time/storage budgets; there is no completion guarantee. A kill
during publication still yields missing/partial evidence. Do not add a signal
handler, extra observer, tracing framework or periodic diagnostic stream.

Before implementation is considered ready, deterministic production-worker tests
must demonstrate linkage and survival when close is blocked, observer completion
and non-completion, publication failure, and simultaneous guard/stop events.
Incomplete observer results remain incomplete. This proposal retains evidence;
it does not establish graceful close or solve full-minute frame-cap exhaustion.
Do not shorten the library timeout, raise the cap, or alter shutdown semantics
silently as part of this publication change.

No new public capture is proposed now. If implemented and locally verified, the
smallest justified native validation would be one bounded **loopback** worker
case with controlled blocked final close, solely to check retained component
publication under the installed Linux runtime. It would need its own exact
prospective identity and execution approval. No public subscription, observational
cohort, induced public disconnect or automatic run follows from this review.
