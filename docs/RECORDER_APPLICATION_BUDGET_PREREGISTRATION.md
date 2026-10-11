# Actual-recorder localhost application budgets — preregistration v1

This freezes the scientific protocol, synthetic corpus, budgets and recorder
baseline before measuring them. `infra.stream.recorder_application_budget`
produces an exclusive, source-bound, hashed declaration. It does not launch a
worker, implement acceptance or authorize execution. The worker, resource sampler,
launcher and evaluator still need implementation, fault tests, compatibility
smoke and a separate execution-source/environment freeze. That later freeze must
bind this declaration hash unchanged; protocol changes require a new identity.

## Question and population

Can the isolated completion-witness recorder preserve supported text occurrences
under these declared localhost loads within the existing absolute budgets for
one-second-binned descriptive research? This is not a probe-overhead comparison,
a venue feed test, a physical latency measurement or an execution-safety test.

Run exactly six serial cases, with no concurrent case workers:

| Order | Case | Scheduled phases | Text occurrences |
| --- | --- | --- | ---: |
| 1 | steady-0 | 120 s at 500/s | 60,000 |
| 2 | mixed-0 | 10 s at 500/s; 10 s at 3,000/s; 50 s at 500/s | 60,000 |
| 3 | mixed-1 | same mixed schedule | 60,000 |
| 4 | steady-1 | same steady schedule | 60,000 |
| 5 | steady-2 | same steady schedule | 60,000 |
| 6 | mixed-2 | same mixed schedule | 60,000 |

Total: 360,000 occurrences. Each case stays below the unchanged 65,536 witness
cap. Steady cases have two complete 60-second CPU windows; mixed cases have one.
The remaining mixed tail is reported separately, not converted to a complete
window. This does not establish sustained 3,000/s capacity or an entire 300-second
market recording. Three repeats are not a confidence guarantee.

## Input and actual transport

Use a real sync WebSocket server/client on IPv4 `127.0.0.1`, no TLS, compression
disabled, protocol ping disabled, maximum incoming message size 262,144 bytes and
client queue setting 16. That setting is not a hard memory/record limit. Bind exact
dependency versions and connect arguments in the later execution freeze. There
is no fake `recv`, external socket, exchange credential or default public connector.
The injected connector must wrap the real loopback client, not return fixture data.

Server verifies the exact two-token subscription, continuously consumes client
control/text messages without adding unsolicited replies, and sends the declared
corpus only. Corpus PONG messages provide the recorder's text-heartbeat response
witnesses. Record subscription and control traffic separately. Any extra received
message is a workload mismatch, not excluded from recording. No intentional
disconnect/reconnect or network fault belongs in this performance cohort.

The initial two occurrences are the two book strings. For occurrence i >=2 use
cycle[(i-2) mod 8]. The exact strings are in the declaration; retain their UTF-8
bytes and hash. Shapes include 40-level synthetic books, two-token price changes,
batched duplicate changes, repeated PONGs, malformed JSON and an unknown event.
Timestamp `0` remains unchanged and has no timing authority. This deliberately
tests raw text retention, not a valid reconstructed book or representative live
payload distribution. Binary and oversized messages are outside this population.

The execution freeze must provide a hash-verified synthetic five-minute metadata
fixture with token IDs 10001/10002 and the declaration's synthetic condition ID
(0x followed by 32 bytes of 0x11). It must disclose synthetic terms, not pretend
this is a discovered venue market. Instantiate event start at epoch UTC minus
10 seconds, end exactly 300 seconds later; preserve the fixture and generated
stream-spec hashes per case. Retiming the terms is allowed by this recipe; retiming
or sequencing corpus messages is not. Corpus condition labels match the synthetic
spec for initial-book classification; they are not venue condition evidence.

After producer, recorder and resource observer readiness is witnessed, agree on
a future shared native monotonic epoch. For each phase send occurrence j at
epoch + phase offset + j/rate. No adaptive pacing, drops or retuning. Late sends
remain ordered, with original deadlines and native begin/end brackets. Send-start
lateness or send-call duration above 50 ms, or less than 99% of a phase's scheduled
starts occurring inside that phase, fails workload validity. These are declared
stimulus checks, not relaxed recorder budgets. Report all late sends and queued
delivery; invalid stimulus cannot produce an application-budget pass.

## Recorder and resources

Baseline implementation is the source frozen at e4b28b7; the declaration pins its
bytes plus the execution-truth dependency inventory. Use segmented capture and
completion witnesses only. No detailed probe/profiling/freshness modes, new queue,
writer split, legacy edits or reduced durability. Keep sync every 64 records or
one second, gzip level 1, 8-MiB segment target, 1-GiB uncompressed and 256-MiB
compressed storage caps, 4-MiB row cap and 32-MiB completion sideband cap. Capture
limit is 60,000 frames / 180 seconds. Normal completion requires frame-limit stop,
both initial-book witnesses, no reconnect/gap, footer and complete manifest/sideband.
Timeout, quota, observer overflow or unexpected termination fails completion.

Use native Ohio Linux in a fresh private stage. Recorder, supervisor and resource
observer share one dedicated unit: 75% CPU, 512 MiB memory, 32 tasks, 240 seconds.
Producer has its own unit with the same limits, reported separately. No affinity
or host exclusivity is assumed. Public collectors, infrastructure and their limits
remain unchanged. Retain before/after source, environment and service-state checks.

Independently witness boot, PID/starttime, live cgroup membership, actor ancestry,
unit command/limits, cpu.max, effective cpuset, memory.max, dependency/runtime
versions, instance/credit configuration, clock domain and concurrent host actors.
Do not accept only a self-reported cgroup string. Effective quota is the most
restrictive evidenced ancestor CPU quota/cpuset capacity in core units; absent or
ambiguous ancestry makes its gate unknown, never the nominal 75% by assumption.

Resource sampling is included in recorder cost. CPU uses dedicated cgroup usage,
not summed overlapping process/group counters. For epoch-anchored complete 60-s
windows, retain reads enclosing both boundaries, with <=5-ms read brackets.
Use the enclosing usage delta as a conservative upper bound, divided by
60 * effective quota. No interpolation/subtraction or pooled average rescue.
Record cpu.stat throttling and memory.events before/after, including OOM/resource
exits. Throttling is disclosed, not attributed to particular latency events.

At epoch plus every integer second through capture/close, sum current VmRSS over
unique live processes in the evidenced unit. Retain process membership and read
brackets; each sample bracket <=5 ms and lateness <=50 ms. Missing/racing process
reads or missed sample slots make coverage unknown; do not substitute zero or
lifetime high-water RSS. Report high-water and cgroup memory separately. One-second
samples are not continuous-peak proof. Capture/close tails and startup/publication
resource use remain reported, even where no complete CPU window exists.

## Unchanged gates and independent audit

Copy the budgets verbatim from the minimum-useful-recorder draft:

- Append upper elapsed bound: nearest-rank p99 <=100 ms and worst <=1 second.
- First covering successful data-file fsync upper elapsed bound: worst <=2 seconds.
- Local application-return UTC bracket width: <=1 ms for every required witness.
- CPU conservative fraction: <=70% of effective quota in every complete window.
- Every retained current-RSS sum: <=80% of the unit memory limit.
- Zero supported occurrence loss; zero missing required witnesses for a pass.

Evaluate append/durability/brackets per case and per separate phase, assigned by
original producer occurrence schedule. No pooling phases/repeats, dropping tails,
or selecting timing-qualified rows to improve percentiles. Include duplicate and
malformed/unknown messages. Retain the full denominator and all known violations.

After all collection work, publish immutable inventories and completion sidebands
exclusively. Offline verification must independently check originating byte
anchors, sources, runtime bindings, stream specs, ordered sent/received/archive
raw bytes, ordinal/hash links, manifests, successful covering watermarks and
resource counters. Producer send success is not library receipt; archive fidelity
requires exact population/order comparison, not equality of digest sets.

Keep separate archive-integrity, stimulus-validity and application-budget outcomes.
Known loss, bad linkage, budget exceedance, resource exit or observation overflow
is a known failure. Missing/ambiguous evidence is unknown; retain known failures
alongside unknowns. Pass requires all six cases valid and every gate known/pass.
Do not infer research eligibility, complete venue coverage, global clock accuracy,
durable crash-tail witnesses, profitability or order authority from localhost pass.

## Stopping and authority

One finite cohort, then review. Preserve every failure/prefix; do not retry a case,
replace it, tune thresholds from outcomes or run until a lucky pass. A harness
failure before collection may motivate a new frozen execution identity; retain
the failed attempt and obtain direction before a replacement run. Changes to
workload, implementation or resource observations require a new declared identity.

This preregistration authorizes no launch, Git push, public capture, EC2 deployment,
infrastructure/resource change, QuantConnect sync or trading. Prior 5%-probe-cost
rejections stay intact. Next: implement and fault-test the finite worker/resource
observer/offline evaluator, then freeze exact execution sources and obtain approval.
