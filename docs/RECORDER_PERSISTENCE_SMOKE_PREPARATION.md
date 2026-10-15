# Prospective persistence/closure recorder smoke (v2)

This is one new 68-occurrence recorder compatibility smoke, subject to explicit
approval of its committed source/runtime freeze. It is not a replay under the
failed f045b061... declaration. The failed run, 2-second durability threshold,
other application/resource thresholds and public collectors remain unchanged.

Runtime entry point: `infra.stream.recorder_persistence_smoke`. The successor
isolated collector caps pending receives at the earlier of last-sync+1 s and
oldest pending application-return+1 s, checks before blocking and after appends,
and retains the 64-record sync cap. The **prospective persistence reserve is 1 s**
inside the unchanged 2-s end-to-end bound. Dispatch, classification, encoding,
gzip/file flush and fsync consume actual time: this reserve is not a guarantee.
No baseline subtraction or tolerance is added. Persistence faults retain failure
and no successful watermark; no retry/replay is introduced.

The producer retains one bounded terminal receive event including monotonic time,
actual WebSocket exception type and sent/received close codes (both must be 1000
or 1001 for expected closure). Expected closure
requires all planned sends completed by the close, the exact ordered original
corpus, a verified case-bound recorder completion/archive/footer, frame_limit,
no reconnect/capture error and a stopped observer. A normal close alone never
passes. Unexpected receive faults remain recorded even when the stop flag changes
during recv. Missing completion/marker, unsigned/wrong-case marker, premature or
abnormal close, missing terminal event, unexpected controls or live drain thread
fail. Existing 185-second evidence deadline and 1-second drain join are unchanged.
The independent auditor repeats completion/closure verification from retained bytes.

Original observer code and its 50-ms CPU pre-read timing, missed-slot handling,
original epoch/grid and resource budgets remain unchanged. Separate successor
runtime modules preserve old runtime bytes, original c9207f... declaration and
historical audit reproducibility; these modules implement the new runtime paths,
not an additional diagnostic observer. Original command routes stay unchanged.

Exactly one readiness unit, one producer and one recorder; 68 original occurrences
0..67 at epoch+j seconds; 1 Hz, 20-second epoch lead, 100-ms readiness margin,
68-frame/180-second capture cap. Each unit: CPU 75%, memory 512 MiB, 32 tasks,
240 seconds. Numeric IPv4 loopback only, existing hardening/environment masking,
public timer/services/source/environment preserved. Linux regression must match
the exact frozen test population with the one declared existing Python 3.9 skip.
No tuning, extra timing experiments, retry, replacement, resource change or cohort.
Fatal/readiness/source/runtime/binding/limit/retention faults preserve partials
and stop. Audit archive integrity/completeness, missed slots, inclusive cost and
all unknowns after the single smoke, then stop regardless of verdict.

Proposed new namespace:
`/var/lib/qcrl-stream/recorder-absolute-20261015LupusPersistence01`.
Source/runtime drift and any pre-existing stage/evidence/unit claim reject staging.
An offline freeze may bind the previously observed installed envelope; it does not
claim a fresh host observation. Fresh read-only runtime/source/public preflight is
required before units. Credit balance and incremental observer overhead remain
unknown; sampled RSS does not prove a continuous peak. Original cohort host gates
are not waived. No native execution or six-case cohort is authorized by this file.

The successor publishes control JSON completely under an exclusive pending name,
then exposes an exclusive final hard link and fsyncs the directory. A reader never
adopts partially serialized consumer.json; collisions and publication faults retain
partials and fail instead of replacing evidence. Completion.json is fully written
before consumer.json becomes visible. This is publication correctness in the
existing artifacts, not an added diagnostic layer.

Prospective smoke plan hash:
`8aee41893efd0dfd19f0dab1a66f9b96ee460fe55a8b251eb8b3e60a6dd224e1`.
Persistence policy hash:
`5f411e0c585062d8657f504ba7b97cdf5aff789d18a5766dec746bd4dc7bee65`.
Both literals are pinned in regression tests. The new source-bound declaration
also binds the successor lane, worker, controller, auditor, tests and this document.

Fourteen successor tests cover actual localhost producer/drain/recorder/archive
paths with Linux resources injected, actual collector timeout decisions with
injected clocks, oldest-return processing time, count boundaries, stalls beyond
the reserve, flush/file/fsync faults, normal/early/abnormal/missing closure,
missing/failed/unsigned/wrong-case/corrupt recorder evidence, stop races, atomic
publication/collision/partial-write faults, full unit-command routing and finite
controller readiness/cleanup faults. Old deterministic failure reproductions and
original runtime tests stay unchanged. Local functional sockets are not the
preregistered 68-at-1-Hz Linux smoke or performance validation.

Offline verification: all 1,156 tests passed in 77.706 seconds on Intel macOS /
Python 3.14.6. All 14 successor runtime/fault tests also pass after separating the
successor declaration's main plan from its unchanged observer sub-plan. New Python
files parse as Python 3.9 syntax; this is not Linux/native validation. Prospective
Linux gate: **1,156 discovered, 1,155 passing and exactly the one declared existing
Python-version skip**, within the separate 240-second readiness unit. Any different
population or result stops without producer/recorder execution.

After separate approval, the one controller command, as root from the new stage's
exact committed `source` checkout, is:

```sh
/opt/qcrl-stream/venv/bin/python -B -m infra.stream.recorder_persistence_smoke --root /var/lib/qcrl-stream/recorder-absolute-20261015LupusPersistence01 --execute
```

Approval must identify the candidate/execution-freeze receipt. No stage, claim or
unit has been created for this successor. Stop after this one smoke and review
completeness, inclusive cost, archive integrity, missed slots and all unknowns.
Neither this packet nor a passing compatibility result authorizes a six-case cohort.
