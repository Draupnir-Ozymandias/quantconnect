# Executable six-case cohort approval packet — October 15

**Prepared for approval; not staged or executed.** The three readiness tasks are
complete: declared-count verifier with boundary/full-population tests, dedicated
successor launcher/auditor with exact source/runtime freeze, and fresh read-only
raw host/credit evidence. This packet supersedes the historical blocked packet.
Approval must explicitly cover staging and exactly one readiness-gated cohort.
No further standalone smoke is proposed or required by a failing requirement.

## Exact identities

| Item | Frozen identity |
| --- | --- |
| Candidate | `8c726522a7ba9b19411d309b42d17a92faf72395` |
| Selected source files | 516 |
| Execution freeze payload | `90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686` |
| Cohort plan | `eca23ef82ac9ca72a816a9580483a35657df364ea081f7772f8e5c0477b1fa6b` |
| Source-bound declaration | `2a33eec2c95cf7f47587bf895dd05996b7972ef5d8264db6f8044d08787647ff` |
| Approval packet payload | `e9805de66fb3eb939ad7c5ad57b7820625ba731e30c4e0f68679092834d073c5` |
| Transport | `stage-packet.tar.gz`, 140,290 bytes, SHA-256 `13d24cec0206c648702823982bda2d8d3ebe9eeac98545d579f42f2a996caa60` |
| Incremental Git bundle | 43,128 bytes, SHA-256 `852ac9eeb22880cbe4af174e4d8a4e2f34bf5c771dec50e679e98e5d61a078d7`; prerequisite frozen 371fa03 |
| Host-context file | SHA-256 `4709e6be243135c7f8f07ba5c5e182de467700b5d36b9c211b0491e31e5ffd4b` |
| Fresh stage | `/var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort01` |
| Private unit prefix | `qcrl-persistence-20261015LupusCohort01-` |

The candidate, not a later documentation-only HEAD, is the execution source.
A fresh offline repository initially containing only the 371fa03 prerequisite
reconstructed all 516 selected candidate files exactly from the bundle and
validated the full freeze/lineage. Verification payload:
`2d7e0362953bd23a51f1c13bac95e0fa22b16622fe732793d31e54d5090404f7`.
The six-member transport contains only the bundle and five frozen controls:
execution-freeze.json, runtime-review.json, select-review-source.c,
host-context.json and compatibility-lineage.json. No credentials or raw capture
archives enter the packet or GitHub. Raw host/lineage controls remain private.

## Fresh host and installed-runtime evidence

Read-only operator CloudShell queries at **2026-10-15 19:39:39 UTC** returned raw
DescribeInstances and DescribeInstanceCreditSpecifications responses for the
existing Ohio instance `i-039c11d5ea49cf413`: **t4g.small, standard credit mode**.
The raw response file is independently anchored by SHA-256
`fca4ffc05df6a9cf8fef2a0141ace8c9e29082e351bb713666b20d9aa5015632`.

CPUCreditBalance was available: the latest returned point is **576 credits at
19:34 UTC**; all 12 returned five-minute points in the preceding hour report
minimum/average/maximum 576. This is dated CloudWatch context, not a continuous
future balance guarantee. **No minimum balance or credit-history acceptance gate
is added.** The collector role was not expanded and credit mode was not changed.

Read-only Session Manager inspection at **19:41:45 UTC** obtained the IMDS identity
document and matching native boot, and rehashed installed runtime/dependency and
prior source envelopes. It matched the passed smoke exactly: Linux aarch64,
Python 3.9.25, glibc 2.34, websockets 15.0.1 with all 60 distribution files, and
boot `c2c6dde4-9394-4b65-a1aa-87389cbf3538`. Native observation file SHA-256:
`427b111d49253595d12cc91b4faa7ec8e433cc14adb6089977f6b9f4922d11f6`.
Public source/environment/service state is unchanged. Proposed stage and unit
prefix are absent; free disk was 6,710,198,272 bytes, above the existing 4-GiB
preflight reserve. Repeat source/runtime/public/namespace checks before units;
any drift blocks execution under this identity.

## Compatibility lineage and offline verification

The original passed 68-occurrence smoke audit and external origin attestation
remain byte-bound and unchanged. The new freeze checks every historical selected
Python source unchanged except the worker's exact two-expression substitution of
the case-sized archive verifier. Persistence scheduling, closure/drain algorithm,
absolute observer/syscall adapter, resource reader, completion witnesses and
execution-truth sources remain smoke-tested bytes. Newly introduced launcher,
auditor, scanner and tests are explicitly offline integration deltas. This is
not a same-source native validation claim or a rewritten smoke receipt. The
[prospective successor contract](RECORDER_PERSISTENCE_COHORT.md) declares this
lineage; the old launcher's same-source gate and all historical verdicts stay intact.

The scanner follows each case's declared count in the supported 1..60,000 corpus
population. Tests cover counts 1, 2, 67, 68, 69, 70, 59,999 and 60,000, adjacent
missing/extra counts, invalid bounds, traversal/symlink/row/footer faults, actual
69- and 60,000-frame persistence/completion paths, large producer artifacts and
native-binding audit fixtures. Further tests cover all 13 unit routes, serial
lifecycle, readiness/fatal-stop cleanup, lineage drift, origin anchors, wrong case
order and retained known failures alongside unknowns. No diagnostic observer was
added. All **1,169 offline tests passed in 152.925 s**, Intel macOS/Python 3.14.6.
Test-log SHA-256: `b82675f324baab51d438b38b88ead7447d998e2114c8e92f2105d9d4224dc832`.
Python 3.9 syntax checks passed; these are not installed Linux tests.

Installed Linux readiness is deliberately **unrun**. The first and only readiness
unit must discover **1,169 total: 1,168 pass plus the declared existing Python 3.9
skip** (`stdlib_module_names` requires Python 3.10+). Quiet native output may only
print the skip count; attribution follows the frozen source/version. Failure,
count/skip mismatch, or exceeding the unchanged **240-s** unit limit stops before
cases. Offline elapsed time is not a guarantee of native completion within 240 s;
no timeout/resource increase or repeat is authorized.

## The one exact cohort

One readiness unit, then six serial producer/recorder pairs, 13 units total:

| Order | Case | Schedule | Occurrences |
| --- | --- | --- | ---: |
| 1 | steady-0 | 120 s at 500/s | 60,000 |
| 2 | mixed-0 | 10 s at 500/s; 10 s at 3,000/s; 50 s at 500/s | 60,000 |
| 3 | mixed-1 | Same mixed schedule | 60,000 |
| 4 | steady-1 | Same steady schedule | 60,000 |
| 5 | steady-2 | Same steady schedule | 60,000 |
| 6 | mixed-2 | Same mixed schedule | 60,000 |

Total 360,000 original ordered occurrences, unchanged synthetic metadata/corpus.
Each case uses prepare+20-s epoch, 100-ms readiness margin, exact live PID/start/
boot/cgroup release, 60,000-frame/180-s capture caps. Every unit retains CPU 75%,
memory 512 MiB, 32 tasks, 240 s, numeric 127.0.0.1 isolation and existing hardening.
No case workers overlap. Observer grid/50-ms CPU pre-read lead and explicit 1-s
persistence reserve remain fixed; reserve is not a guarantee of the 2-s bound.

Original gates remain: append upper p99 <=100 ms / worst <=1 s; successful durable
upper worst <=2 s; each return UTC bracket <=1 ms; zero loss/missing witnesses.
Full denominators per case/per phase, no pooling or subtraction. Send start/call
bounds <=50 ms, phase attainment >=99%. Inclusive CPU <=70% effective quota for
each of nine complete 60-s windows, enclosing read brackets <=5 ms; current RSS
<=80% memory at every required slot, brackets <=5 ms / lateness <=50 ms. Missing,
racing or invalid samples remain unknown, with known violations retained.

**Incremental observer overhead and continuous RSS peak remain unknown and are
not acceptance gates.** Inclusive CPU and sampled RSS cannot establish them.
Retain startup/publication/close totals, scheduled read brackets, actual unit exit
accounting, cgroup memory/high-water availability, throttling/memory.events and
separate producer costs. No continuous peak, causal host-isolation or incremental
cost claim follows from a pass.

After safe staging and all exact preflight checks, the single controller command
from the frozen `stage/source` checkout is:

```bash
sudo -n /opt/qcrl-stream/venv/bin/python -B -m infra.stream.recorder_persistence_cohort \
  --root /var/lib/qcrl-stream/recorder-persistence-20261015LupusCohort01 --execute
```

This command is for approval, not an instruction to execute before approval.

## Stop, preserve and independent review

Fatal readiness/launch/runtime/closure/source/public/identity faults stop remaining
units. Retain partial evidence, capture properties/journals once, and stop only
submitted private units. No replay, retry, replacement, tuning, new smoke, extra
case, resource change or public-service action. Ordinary scientific budgets are
independently audited afterward rather than used to select a lucky subset.

Stop after the finite cohort regardless of outcome. Independently verify external
inventory/freeze/host byte anchors, exact population/order and archive hashes,
completion/closure, every case/phase/CPU window/RSS slot/wait and all 13 live-unit
bindings/lifetimes. Report every known failure and unknown, inclusive costs,
producer costs, archive integrity and missed slots. Incomplete prefixes remain
non-acceptance. Self-reported origin flags stay false; external observation is a
separate attestation. The frozen auditor CLI is
`infra.stream.recorder_persistence_cohort_audit`, with required caller-provided
`--inventory-sha256`, `--freeze-sha256`, `--host-context-sha256`, `--root` and
exclusive `--output` outside the retained evidence tree.

No public rollout/capture, IAM/infrastructure/resource change, credential import,
main merge, QuantConnect sync, trading or orders. Historical failed cohorts/smokes,
original declarations and thresholds remain unchanged. Private executable packet:
`.qcrl/reviews/recorder-cohort-preparation-20261015/approval-packet.json`.
