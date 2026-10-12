# Isolated CPU-counter endpoint prototype

`infra/stream/recorder_counter_prototype.py` explores narrower CPU-counter read
brackets without editing the completed cohort, its sampler, evaluator, recorder,
workload or budgets. It is not connected to a worker or launcher and has no CLI,
scheduler, deployment or execution authority.

The October 12 cohort's source/runtime, ordered archive population and stimulus
verified, but the fixed application contract failed: five cases had UTC brackets
over 1 ms, and all six resource verdicts were unknown. Every pre-window CPU read
finished after its fixed boundary; 33 full resource-read brackets exceeded 5 ms.
The preserved review is `.qcrl/reviews/application-cohort-20261012-cBCDc6eB/`.
This prototype cannot retroactively repair any of those outcomes.
Re-audit that cohort from its frozen `adf29ff` source, not this new working tree:
the prospective execution-source inventory includes new prototype files even
though no worker imports them. Its scientific declaration hash remains unchanged.

## Experimental separation

The prototype preopens a bounded, regular, nonsymlink `cpu.stat` leaf and reuses
the descriptor with offset-zero reads. Only the raw read is inside its narrow
native monotonic bracket; parsing and hashing follow outside that interval.
Exact bounded ASCII bytes, parsed counters and their byte hash are retained for
independent consistency checks. File/directory identity and full resource guards
are retained before and after, outside the narrow counter interval. The endpoint
also retains a total begin/end envelope, so guard cost is not hidden.

Guards must agree on owner/starttime/boot, unique cgroup actor population,
controller/limit ancestry and effective quota. The counter must lie between their
observed usage values. Changed identities/controls, replaced or removed leaves,
counter resets, malformed bytes, nonfinite/regressing clocks, failures or oversized
reads are refused. Descriptor cleanup is scoped and idempotent; no retry occurs.
Full guards are bracketed observations, not an atomic kernel snapshot or proof
that no transient/ABA configuration change happened between observations.

The pure offline window diagnostic requires the original complete 60-second
window and 5-ms read ceiling. Both counter reads must enclose the fixed boundaries;
late starts, early ends, overlapping total envelopes and counter resets are
refused. No interpolation, shifted window, guard-cost subtraction or timestamp
repair exists. It reports the enclosing CPU-usage fraction as a diagnostic, not
an acceptance verdict. Independent native origin binding is explicitly false.

## What this does not establish

Reducing the timed critical section does not establish reduced total observer
overhead. This first prototype deliberately retains two full guards per endpoint;
their cost may exceed the prior reader's. Reused-descriptor cgroup pseudo-file
behavior and real scheduling/GIL effects require a separately frozen native smoke.
Ordinary temporary-file fixtures are not evidence that Linux `cpu.stat` behaves
identically under `pread` or that the 5-ms bound will hold under load.

There is intentionally **no old-sampler scheduling change**. The old sampler's 2-ms lead
was inadequate for the observed full reads, but this prototype does not select a
replacement for that old sampler. The separate `recorder_counter_schedule.py`
prototype fixes one pre-boundary attempt at minus 50 ms and one post-boundary
attempt at plus 60 seconds. Readiness must precede the first target; wakes over
50 ms late are skipped, early wakes are refused, and counter reads must still
enclose the original boundaries within the unchanged 5-ms ceiling. The lead is
a prospective smoke scheduling recipe, not a claim of adequate scheduling under
recorder load. Missed boundaries remain unknown/refused, without retry, catch-up,
adaptive lead or shifted epoch. Exactly two bounded rows retain all attempts.
RSS evidence is unchanged. The separate
UTC-bracket failures also remain unresolved.

## Tests and next gate

Fixture tests cover narrow versus total cost, exact raw-byte verification,
fixed-window enclosure, late/early/slow reads, resets, quota/identity/member
changes, tampering, authority flags, malformed/missing/capped data, read/guard
failures, repeated offset-zero reads, leaf replacement/removal/symlink/FIFO and
scoped descriptor cleanup. These use injected clocks or ordinary temporary files.

All **987 local regression tests passed** in 41.726 seconds using the existing
Python 3.14.6 / websockets 15.0.1 test environment. The focused prototype suite
passed 12 tests. Python 3.9 syntax parsing passed; this is not a native-runtime
test. The original resource reader, worker, evaluator, recorder/completion files
and declaration remain unchanged from `adf29ff`. The 203 originating cohort
evidence files were independently byte-verified again after this work.

Scheduling implementation: the complete suite passed 994 tests in 42.052 seconds;
the final focused prototype/scheduling suite additionally covers a valid wake
whose guarded read crosses the boundary, and clock regression between attempts.
The original sampler and scientific declaration remain unchanged. The next
native smoke is one idle diagnostic window, with the same private-unit limits;
it is not the six-case workload or an overhead comparison.

Next: source-freeze the tested endpoint scheduling/fault contract and perform
the separately authorized finite native compatibility smoke. Do not
integrate this prototype into the cohort launcher, launch another cohort, or
claim lower overhead or a public-research pass from the local fixture tests.
