# Revised executable cohort approval packet — readiness memory v2

**Awaiting new approval. Not staged or executed.** The previous attempt remains
failed at readiness with zero cases. This packet proposes one fresh readiness-gated
six-case cohort. Its sole unit-resource change is **readiness MemoryMax 1 GiB**;
producer/recorder measurement units retain 512 MiB and every original budget.
No additional standalone smoke is proposed.

## Exact identity

| Item | Prospective value |
| --- | --- |
| Candidate (execution source) | `4926d62faab552af8a3c8e3fe964dc16052e4773` |
| Selected source files | 520 |
| Execution freeze v2 | `6428a09a34633987a353c32beeca340be535b33c1e11aa897f291d37a4da434b` |
| Source-bound declaration | `02b6e95d44d930c94e9bac172231d607fcf297fdafd52e44d98978be09eaf2d0` |
| Readiness envelope | `3da708ded82b8ca4f5dcb868401130e8bd9e9b447c19542f7d1842ac2572ce09` |
| Original measurement plan, unchanged | `eca23ef82ac9ca72a816a9580483a35657df364ea081f7772f8e5c0477b1fa6b` |
| Approval packet payload | `dcce731de610681470fb773e3ed95be1d47329b9bc0905fa0b7cfdb3ad3399e2` |
| Transport | 162,991 bytes, SHA-256 `f356aa7abb1d3f84e7da7aa942f94164f1a0aac2f09006fe3603359389202ce3` |
| Git bundle | 65,108 bytes, SHA-256 `3be31516690c5a4a873ca064f2f3b6ba4c2c7bf63d7d846774c899929c14f6c5` |
| Fresh private stage | `/var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort02` |
| Unit prefix | `qcrl-persistence-20261015LupusCohort02-` |

The execution source is this candidate, not a later documentation-only HEAD.
Private prepared files: `.qcrl/reviews/recorder-cohort-readiness-v2-preparation-20261015/`.
The six-member transport contains candidate.bundle and execution-freeze.json,
runtime-review.json, select-review-source.c, host-context.json and
compatibility-lineage.json. Incremental bundle prerequisite remains
371fa03c3d2622d784128b9359c3ab730f082cf2. A clean scratch repository initially
lacking this candidate reconstructed all selected bytes from that bundle;
verification payload `4237808b4f5d5060b01d30d3ab8c5cc6a8abb285f20feca92a2dfc8675abf9ae`.
No credentials or raw historical evidence enter GitHub or the transport.

## Justification and offline verification

The [prospective execution-envelope rationale](RECORDER_READINESS_MEMORY_V2.md)
records local working sets and cumulative retention. The actual 60,000-frame
completion/producer/audit test alone peaked at 604,839,936 bytes (about 577 MiB),
above 512 MiB even in a fresh process. Original-suite peak was 647,921,664 bytes
(about 618 MiB). Final RSS stayed 231,817,216 bytes after explicit GC; allocation
retention/live-object categories remain unquantified, and no unbounded leak is
claimed. The native OOM's active test remains unknown.

The proposed 1-GiB cap has 425,820,160 bytes of margin over that original local
suite peak. This is prospective allowance, not a Linux/cgroup guarantee. The
240-second ceiling is unchanged and still may fail. Readiness ends before the
case units start; its cap equals their already planned aggregate 2 x 512 MiB,
without reserving physical memory or proving shared-host headroom.

All **1,177 revised offline tests passed in 154.120 s**, Intel macOS/Python 3.14.6.
The local process maximum RSS in that run was 632,987,648 bytes. Test log SHA-256:
`7bad621ea903b71c2256d1bdcdb6bdfb5ac55deae7a506aaba9c3aa097954b9b`.
Eight new tests cover exact effective properties,
readiness versus recorder routing, actual start/capture/audit paths, wrong limits,
OOM exit retention, partial evidence and unchanged measurement-adapter delegation.
Python 3.9 syntax parsing passes; installed Linux readiness remains unrun.
The first revised local full suite caught a removed import still used by recorder
binding; it was restored, the failed local log retained, and the complete suite
then passed. No historical/native evidence was rewritten.
Offline memory review payload: `118b070eedb2a4a464542faafbd36561f6a5908453af23524492e4af6c7922f9`.

## Host/runtime conditions still required

This offline revision did **not** refresh remote observations or stage anything.
The frozen expected runtime/boot/dependency and host controls remain byte-identical
to the prior approved controls. Host-context file SHA-256:
`4709e6be243135c7f8f07ba5c5e182de467700b5d36b9c211b0491e31e5ffd4b`.
The retained context was observed at 19:39/19:41 UTC October 15; the last separate
raw API refresh was 22:31:04 UTC, standard t4g.small, latest returned credit balance
576 at 22:26 UTC. These are dated observations, not current readiness passes.

After new approval and before native units: obtain fresh read-only instance and
credit-mode responses; report available credit balance and timestamp, host
MemAvailable and unknowns; recheck exact installed runtime/dependency bytes/live
boot, public source/environment/services and fresh namespace. Drift blocks this
identity. No minimum credit balance, retrospective host minimum, continuous-credit
claim or new acceptance gate is introduced. No IAM/VM/public settings change.
Incremental observer overhead and continuous RSS peak remain unknown, outside the
existing declared gates; sampled/inclusive measurements cannot pass them.

## Exact proposed execution

One readiness unit, then these six serial producer/recorder pairs (13 units total):

| Order | Case | Schedule | Frames |
| --- | --- | --- | ---: |
| 1 | steady-0 | 120 s at 500/s | 60,000 |
| 2 | mixed-0 | 10 s at 500/s; 10 s at 3,000/s; 50 s at 500/s | 60,000 |
| 3 | mixed-1 | Same mixed schedule | 60,000 |
| 4 | steady-1 | Same steady schedule | 60,000 |
| 5 | steady-2 | Same steady schedule | 60,000 |
| 6 | mixed-2 | Same mixed schedule | 60,000 |

Readiness must discover **1,177 total: 1,176 pass plus one existing Python 3.9
stdlib_module_names skip**, in one original discovery process. Readiness only:
MemoryMax=1G. Every unit remains CPUQuota=75%, TasksMax=32, RuntimeMaxSec=240;
producer and recorder MemoryMax=512M. The launcher retains actual property bytes
and the independent auditor strictly checks each role's declared envelope.
No masking or normalization of 1-GiB properties into historical 512-MiB evidence.

Unchanged: 360,000 occurrences; prepare+20-s future epoch and 100-ms readiness
margin; 180-s capture cap; 50-ms CPU pre-read lead; original slots/missed-target
handling; explicit 1-s persistence reserve without a guarantee; successful durable
upper bound <=2 s; append p99 <=100 ms and worst <=1 s; UTC bracket <=1 ms;
zero loss/missing witnesses; inclusive CPU <=70% effective quota in each complete
60-s window (nine total), current RSS samples <=80% of **512 MiB**; producer
start/call <=50 ms and phase attainment >=99%. No threshold, denominator,
closure/completion algorithm, recorder worker, production wait adapter or archive
implementation changes accompany this readiness revision.

After approved verified exclusive staging/check-out of this exact packet into the
fresh stage, the one proposed controller command is:

```bash
sudo /opt/qcrl-stream/venv/bin/python -B -m infra.stream.recorder_persistence_cohort --root /var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort02 --execute
```

A readiness/OOM/timeout/population mismatch, invalid identity, source/runtime/public
drift or declared runtime/closure fault stops remaining units. Retain partial
properties/journals/archives; capture/stop only submitted private units. Do not
reset/delete the prior Cohort01 failed unit/evidence. No retries, replay,
replacement, tuning, extra cases, extra smoke or adaptive resource changes.
After this cohort, stop for independent origin-byte/completeness, ordered archive,
completion/closure, every phase/window, inclusive cost, missed-slot and resource
audit, reporting every failure and unknown. No main merge, public rollout,
QuantConnect sync, credential import, infrastructure/IAM change or orders.

Approval must cover staging and **one** readiness-gated cohort under the exact v2
freeze above, including the explicitly separate readiness allowance. The old
approval is spent. This packet and its authority flags authorize no execution.
