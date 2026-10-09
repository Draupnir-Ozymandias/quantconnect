# Receive-loop observation contract, version 1

Status: **frozen v1 declaration, source-verified.** An isolated instance-wrapper
[prototype is now fault-tested](../infra/stream/RECEIVE_LOOP_PROTOTYPE_2026_10_08.md).
Private [recorder integration is now unit-tested](../infra/stream/RECEIVE_LOOP_INTEGRATION_2026_10_08.md);
An [overhead protocol is now preregistered](RECEIVE_LOOP_OVERHEAD.md), but its
runner and performance evaluator remain unimplemented. The original
declaration's implementation-status field remains unchanged for reproducibility.
The prior [delay decomposition](../infra/stream/DELAY_DECOMPOSITION_2026_10_08.md)
places most fully observed tail time before callback entry. This contract identifies
the next observable boundaries without calling that time network latency.

`infra.stream.receive_loop_contract` pins websockets **15.0.1**, four library
source files and thirteen method bodies/locations. Modified source or method
bindings fail closed, even if a receipt is rehashed. Runtime receipts retain
platform/Python identity; their source and method pins must match across hosts.
They are reproducibility receipts, not exchange authentication or capture evidence.

```bash
python -m infra.stream.receive_loop_contract \
  --source-analysis-sha256 VERIFIED_DECOMPOSITION_SHA256 \
  --output /path/to/new-contract.json
```

The output must not exist. Declaring this artifact does not install hooks,
connect a socket, authorize a capture or update a public receive contract.

## Verified library ordering

`Connection.__init__` creates the assembler, attaches native flow-lock
acquire/release callbacks, then starts the receive thread **before constructor
return**. In `recv_events`, each iteration passes through the flow-control lock
before calling `socket.recv(65536)`. The lock is released before that read.

Incoming bytes feed the protocol parser. Its resulting event list is dispatched
after releasing the protocol mutex. There is no additional flow-control gate
between each event in that list. A pause during dispatch does not stop the
remaining parsed events from being processed. This explains why high-water 16
is not a hard cap on parsed frames; it does not prove which batch caused a
particular historical queue sample or marker overflow.

Assembler pause triggers at depth **>16**. Normal low-water resume triggers at
depth **≤4**. `Assembler.close` can resume a paused reader regardless of depth.
All three call native pause/resume while holding the assembler mutex.

## Four separate observation categories

| Category | Planned observation | Must not infer |
| --- | --- | --- |
| Flow gate | Acquire attempt and return/exception, linked operation ID | Pure pause duration or simultaneous queue snapshot |
| Socket read | Entry and data/EOF/exception return, byte count, read-iteration ID | Wire arrival, network RTT or exchange delivery time |
| Flow edges | Native pause/resume operation brackets, existing assembler context and closed flag | That shutdown resume is normal drain/recovery |
| Dispatch summary | Bounded frame-counter range/count and first/last callback context per read iteration | Packet boundaries or a message wholly contained in one read |

One read can produce many frame callbacks; frames/messages can also span reads.
Protocol control/handshake/EOF processing is not automatically an application
message. Failed send/read/close paths must remain explicit. Do not force a
cross-thread total order from observation completion order; use operation IDs,
thread-local ordering and interval relations.

## Installation and transparency requirements

The proposed installation boundary is an overridden `recv_events` entry,
**before** delegating to the unchanged parent loop. All observer state must exist
before the base constructor launches that thread. Installing wrappers after
`connect` or constructor return would miss early activity and cannot be described
as complete observation. The isolated prototype now tests this entry boundary;
private recorder/occurrence integration is unit-tested; measured overhead acceptance
remains pending.

Native methods must execute exactly once and preserve arguments, results,
exceptions, timeouts, shutdown behavior and lock ordering. Do not copy/rewrite
the parent read loop or change its flow-control thresholds. Do not hold a telemetry
lock across native socket/gate operations. An assembler callback observer must
not try to reacquire the mutex already held by its caller.

Observation failures or budget exhaustion disable **only observation**. They
must not swallow or repeat native calls, close/reconnect transport, clear the
assembler, release somebody else's lock, drop raw data or fabricate a successful
attribution. A partial observation cannot satisfy the complete-observation gate.

## Fixed bounds and acceptance gates

Numeric localhost only; diagnostic marker cap 128; library high/low 16/4 and
read buffer 65,536 unchanged. Retain at most 32,768 read summaries and 32,768
flow edges; encoded sideband output is capped at 32 MiB. No raw payload bytes
are added to sideband observations. Persist sideband only after measurement.
These are declared bounds, not proof of runtime memory or overhead.

Before any finite measurement:

1. Implement isolated diagnostic wrappers and fault-injection tests for native
   success/error/timeout/close behavior, observer failures and budget exhaustion.
2. Prove constructor/receive-thread installation coverage and native operation
   equivalence; retain the pinned source/method receipt.
3. Prospectively declare an unchanged-baseline versus instrumented localhost
   comparison with the same corpus, encoding, caps, CPU/memory/tasks/runtime and
   durability. Instrumentation overhead is itself a measurement concern.
4. Require complete sideband bounds, raw archives and occurrence integrity before
   assigning any observed interval to gate waiting or read blocking.

No new benchmark/capture schedule, infrastructure change, public deployment,
credentials, trades or QuantConnect sync is authorized by this contract.

## Verified declaration receipts — October 8, 2026

Fresh ignored artifacts: `.qcrl/reviews/receive-loop-contract-20261008-OeGkzs/`.

Local contract SHA-256:
`5304bec12a5ad04a759930370fdcbc8a8b499f553fd9e8b9202d6f5f41e58625`

Linux contract SHA-256:
`63b69b1df1fd095024e567a77f6d1ee7afa399c83d499afad608cc90a8416c4d`

Source analysis SHA-256:
`c846322545a4c4007b815a066ae4067109af63f4bc01b797fc5c5278337c9dc0`

Inspector/declaration code SHA-256:
`5ee86340ebe585d22a0e57c8cb78bb2f5a9388e3dbeb8239bd0d24ed884793db`

Tests SHA-256:
`0d238d7e7d32f60afaa8c9fdbae8f60a4e93996952aed60093f3e6516235e10f`

Local full suite: **570 tests passed**, 18.576 seconds. All seven new tests passed
on Linux/Python 3.9, 0.208 seconds, in a fresh temporary checkout. Downloaded Linux
and local receipts validated with identical policies, source-file hashes and
method hashes/locations. Their distinct runtime identities explain distinct
receipt/contract hashes. No hooks, new captures or collector changes occurred.
