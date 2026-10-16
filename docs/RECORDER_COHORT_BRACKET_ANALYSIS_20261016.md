# Cohort02 UTC/RSS bracket analysis — October 16, 2026

**Offline analysis only. Acceptance remains failed**, complete=true, application_budget_pass=false. The nine >1-ms UTC rows and 39 >5-ms RSS reads are unchanged; no threshold, failed-attempt verdict, source/runtime envelope or retained evidence is repaired. No native rerun, new observer or production code change was made.

## Evidence and clock interpretation

Analyzed the retained native case/consumer/producer/completion JSON for all six cases, under candidate `4926d62` and freeze `6428a09a34633987a353c32beeca340be535b33c1e11aa897f291d37a4da434b`. The original frozen auditor and [complete result](RECORDER_COHORT_V2_RESULT_20261016.md) remain authoritative. This supplemental mapping is not a replacement auditor. All 48 unique bracket violations are below; aggregate UTC failures are not extra events.

Times `t` and interval endpoints are seconds relative to each case’s MONOTONIC epoch; duration/latency columns are milliseconds. Values are rounded to six decimals in tables, with original floats in the private mapping. Epoch UTC is the declared projection from the preparation clock bracket, not an independently sampled UTC at each RSS read. UTC rows additionally retain their directly observed UTC string. Do not use the projection to infer wall-clock drift or millisecond host-wide causality.

| Case | MONOTONIC epoch s | Declared epoch UTC | Preparation UTC bracket ms |
| --- | ---: | --- | ---: |
| steady-0 | 1055807.508735244 | 2026-10-16T03:08:10.883160Z | 0.025050 |
| mixed-0 | 1055999.735872469 | 2026-10-16T03:11:23.110296Z | 0.024278 |
| mixed-1 | 1056142.045572059 | 2026-10-16T03:13:45.419993Z | 0.019093 |
| steady-1 | 1056284.262902260 | 2026-10-16T03:16:07.637327Z | 0.030498 |
| steady-2 | 1056475.897665747 | 2026-10-16T03:19:19.272091Z | 0.026544 |
| mixed-2 | 1056668.407479127 | 2026-10-16T03:22:31.781907Z | 0.028406 |

Counter context uses the nearest resource read wholly before the event and the nearest wholly after it, including CPU pre-reads when present. `window` is their **outer** envelope (left.before to right.after), not an event-local CPU interval. The cpu.stat snapshot lies somewhere inside each endpoint bracket. `ΔN/ΔT` is nr_throttled / throttled_usec between those snapshots; intervals overlap and must not be summed. A positive delta establishes throttling somewhere between snapshots, not within the violation. Zero excludes a new recorded consumer-cgroup throttle increment between those counter snapshots; it does not exclude OS preemption, GIL waits, blocking I/O, ancestor/host contention or credit effects. Producer/event-loop CPU attribution is unavailable at this resolution.

`sync` counts recorded recorder sync_begin..sync_complete barriers overlapping the event. These include writer/file flush and file fsync; overlap does not identify a blocking fsync or prove causality. `returns` counts application-return brackets intersecting an RSS bracket, not all frames processed during it. One observed actor/process per consumer sample does not mean one thread.

## All nine UTC violations

| Case | Seq | Phase / rate per s | t start | Width ms | Observed UTC |
| --- | ---: | --- | ---: | ---: | --- |
| steady-0 | 24584 | 0 / 500 | 49.168588 | 3.343150 | 2026-10-16T03:09:00.051743Z |
| mixed-0 | 1320 | 0 / 500 | 2.646053 | 1.146996 | 2026-10-16T03:11:25.757457Z |
| mixed-0 | 14021 | 1 / 3000 | 13.007447 | 2.148269 | 2026-10-16T03:11:36.117730Z |
| mixed-0 | 43496 | 2 / 500 | 36.996049 | 4.449055 | 2026-10-16T03:12:00.106331Z |
| mixed-1 | 14586 | 1 / 3000 | 13.196716 | 1.358457 | 2026-10-16T03:13:58.616697Z |
| mixed-1 | 56373 | 2 / 500 | 62.746426 | 1.347479 | 2026-10-16T03:14:48.166415Z |
| steady-2 | 50423 | 0 / 500 | 100.847762 | 5.210600 | 2026-10-16T03:21:00.125012Z |
| mixed-2 | 7952 | 1 / 3000 | 10.987885 | 2.080684 | 2026-10-16T03:22:42.769774Z |
| mixed-2 | 27712 | 1 / 3000 | 17.572383 | 2.036238 | 2026-10-16T03:22:49.354272Z |

Per-occurrence producer context is the matching sequence’s send-call start minus its planned deadline (`send late`), send-call elapsed (`send call`), then application-return bracket start minus send-call end (`gap`). A send return is not receipt/completion; these intervals cannot attribute network, queue or scheduler costs separately. `append` is append_completed minus UTC bracket end.

| Case / seq | Send late ms | Send call ms | Gap ms | Append ms | Counter window t | ΔN / ΔT µs | Overlapping RSS slots | Sync |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| steady-0 / 24584 | 0.134827 | 0.164085 | 0.289032 | 0.349626 | 49.000227–50.003268 | 0 / 0 | none | 0 |
| mixed-0 / 1320 | 0.083483 | 0.086604 | 5.882621 | 0.141324 | 2.000216–3.020024 | 0 / 0 | none | 0 |
| mixed-0 / 14021 | 0.077639 | 0.072771 | 0.296400 | 0.502963 | 12.000146–14.011527 | 2 / 4748 | 13 | 0 |
| mixed-0 / 43496 | 1.606591 | 0.055819 | 2.386577 | 0.148651 | 36.000311–37.003369 | 0 / 0 | none | 0 |
| mixed-1 / 14586 | 0.070292 | 0.050683 | 1.261202 | 0.296007 | 13.000165–14.004521 | 1 / 1444 | none | 0 |
| mixed-1 / 56373 | 0.083654 | 0.132176 | 0.210345 | 0.277955 | 62.000191–63.003879 | 0 / 0 | none | 0 |
| steady-2 / 50423 | 1.458649 | 0.138846 | 0.164496 | 0.210781 | 100.000185–101.003571 | 0 / 0 | none | 0 |
| mixed-2 / 7952 | 0.576822 | 0.015081 | 3.293042 | 0.149308 | 10.000172–11.007316 | 2 / 8436 | none | 0 |
| mixed-2 / 27712 | 0.068862 | 0.038974 | 1.608063 | 0.198899 | 17.000149–18.011912 | 0 / 0 | none | 0 |

`CompletionWitnesses.application_return` brackets `utc_text(self.clock())` with `_now()`. The elapsed interval also includes the first `_now`’s post-clock validation and second `_now`’s pre-clock ownership check. It can include arbitrary descheduling between stamps. It is **not a measurement of a UTC syscall alone**. No target/wake deadline exists for this per-frame operation, so a late receive before the first stamp cannot by itself widen this bracket. The evidence localizes elapsed time between stamps, but cannot split clock acquisition, formatting/Python work, GIL delay and OS scheduling inside that interval. No UTC violation overlaps a recorded persistence barrier; one overlaps an RSS read (shown above), which is evidence of concurrent activity, not the cause.

## All 39 inadmissible RSS reads

`wake` = wait.after_ns − target_ns; `handoff` = reader.before − wait.after_ns; start lateness is their sum (subject to floating conversion). Each is nonnegative here and the total is below the unchanged 50-ms start gate. Width is reader.after − reader.before; **that** is the failing >5-ms requirement. The wait receipt ends in Python after native return; `wake` can itself include rescheduling and return bookkeeping.

| Case | Slot | Phase / rate per s | t start | Wake ms | Handoff ms | Width ms | Counter window t | ΔN / ΔT µs | Sync | Returns |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |
| steady-0 | 76 | 0 / 500 | 76.000204 | 0.098005 | 0.105591 | 5.111065 | 75.000299–77.003279 | 0 / 0 | 0 | 3 |
| mixed-0 | 3 | 0 / 500 | 3.000489 | 0.402934 | 0.086120 | 19.535399 | 2.000216–4.003070 | 0 / 0 | 1 | 8 |
| mixed-0 | 10 | 1 / 3000 | 10.000168 | 0.094457 | 0.073509 | 10.013310 | 9.000191–11.012359 | 0 / 0 | 1 | 28 |
| mixed-0 | 11 | 1 / 3000 | 11.000188 | 0.111938 | 0.075668 | 12.171441 | 10.000168–12.013284 | 1 / 4508 | 0 | 27 |
| mixed-0 | 12 | 1 / 3000 | 12.000146 | 0.077966 | 0.068086 | 13.138393 | 11.000188–13.016441 | 2 / 7170 | 1 | 36 |
| mixed-0 | 13 | 1 / 3000 | 13.000142 | 0.073483 | 0.068430 | 16.299235 | 12.000146–14.011527 | 2 / 4748 | 1 | 44 |
| mixed-0 | 14 | 1 / 3000 | 14.000479 | 0.382876 | 0.096582 | 11.047142 | 13.000142–15.019405 | 2 / 4412 | 0 | 32 |
| mixed-0 | 15 | 1 / 3000 | 15.000174 | 0.076405 | 0.097764 | 19.231326 | 14.000479–16.004498 | 3 / 9754 | 1 | 62 |
| mixed-0 | 17 | 1 / 3000 | 17.000182 | 0.103100 | 0.078802 | 6.414145 | 16.000148–18.010095 | 1 / 2024 | 1 | 12 |
| mixed-0 | 18 | 1 / 3000 | 18.000183 | 0.104922 | 0.078121 | 9.911460 | 17.000182–19.019053 | 3 / 14087 | 1 | 20 |
| mixed-0 | 19 | 1 / 3000 | 19.000443 | 0.342533 | 0.100586 | 18.609923 | 18.000183–20.003089 | 4 / 34065 | 1 | 37 |
| mixed-0 | 22 | 2 / 500 | 22.000248 | 0.108829 | 0.139421 | 9.588237 | 21.000188–23.002824 | 0 / 0 | 0 | 5 |
| mixed-1 | 10 | 1 / 3000 | 10.000173 | 0.096113 | 0.076488 | 11.430113 | 9.000166–11.008970 | 2 / 6466 | 0 | 34 |
| mixed-1 | 11 | 1 / 3000 | 11.000183 | 0.115169 | 0.067988 | 8.786823 | 10.000173–12.005956 | 4 / 10683 | 1 | 26 |
| mixed-1 | 12 | 1 / 3000 | 12.000528 | 0.453551 | 0.074888 | 5.427911 | 11.000183–13.010508 | 3 / 5329 | 0 | 9 |
| mixed-1 | 13 | 1 / 3000 | 13.000165 | 0.089947 | 0.075011 | 10.343129 | 12.000528–14.004521 | 2 / 2556 | 1 | 28 |
| mixed-1 | 15 | 1 / 3000 | 15.000162 | 0.079395 | 0.082264 | 5.791504 | 14.000217–16.002308 | 0 / 0 | 0 | 13 |
| mixed-1 | 17 | 1 / 3000 | 17.000187 | 0.082841 | 0.104320 | 11.453563 | 16.000175–18.008098 | 0 / 0 | 1 | 31 |
| mixed-1 | 18 | 1 / 3000 | 18.000191 | 0.124232 | 0.066379 | 7.907871 | 17.000187–19.003708 | 1 / 175 | 1 | 23 |
| mixed-1 | 38 | 2 / 500 | 38.000240 | 0.104695 | 0.134982 | 5.147323 | 37.000171–39.004004 | 0 / 0 | 0 | 3 |
| steady-1 | 25 | 0 / 500 | 25.000177 | 0.099947 | 0.076775 | 6.261958 | 24.000175–26.003038 | 0 / 0 | 0 | 3 |
| steady-1 | 38 | 0 / 500 | 38.000321 | 0.212384 | 0.108938 | 7.431231 | 37.000201–39.003097 | 0 / 0 | 0 | 4 |
| steady-1 | 78 | 0 / 500 | 78.000341 | 0.226412 | 0.114723 | 19.092548 | 77.000171–79.002391 | 0 / 0 | 0 | 7 |
| steady-2 | 4 | 0 / 500 | 4.000293 | 0.206901 | 0.085907 | 15.453753 | 3.000187–5.003249 | 0 / 0 | 0 | 8 |
| steady-2 | 57 | 0 / 500 | 57.000226 | 0.095687 | 0.130174 | 7.012937 | 56.000197–58.003205 | 0 / 0 | 1 | 3 |
| steady-2 | 65 | 0 / 500 | 65.002586 | 2.491327 | 0.094531 | 10.020277 | 64.000164–66.013697 | 0 / 0 | 0 | 4 |
| steady-2 | 66 | 0 / 500 | 66.004503 | 3.581434 | 0.921275 | 9.193797 | 65.002586–67.003153 | 0 / 0 | 0 | 5 |
| steady-2 | 68 | 0 / 500 | 68.000207 | 0.096487 | 0.110169 | 11.481684 | 67.000177–69.003344 | 0 / 0 | 0 | 6 |
| mixed-2 | 11 | 1 / 3000 | 11.000151 | 0.073800 | 0.076774 | 7.165067 | 10.000172–12.011434 | 2 / 8436 | 1 | 17 |
| mixed-2 | 12 | 1 / 3000 | 12.000205 | 0.146565 | 0.058560 | 11.228713 | 11.000151–13.012233 | 2 / 2710 | 0 | 31 |
| mixed-2 | 13 | 1 / 3000 | 13.000216 | 0.127443 | 0.088828 | 12.016310 | 12.000205–14.004570 | 2 / 2710 | 1 | 31 |
| mixed-2 | 15 | 1 / 3000 | 15.000161 | 0.091487 | 0.069136 | 5.596510 | 14.000163–16.015019 | 2 / 3368 | 1 | 10 |
| mixed-2 | 16 | 1 / 3000 | 16.000472 | 0.376009 | 0.096114 | 14.546445 | 15.000161–17.009367 | 1 / 3368 | 1 | 46 |
| mixed-2 | 17 | 1 / 3000 | 17.000149 | 0.074738 | 0.073895 | 9.218659 | 16.000472–18.011912 | 0 / 0 | 1 | 26 |
| mixed-2 | 18 | 1 / 3000 | 18.000160 | 0.093400 | 0.066436 | 11.752017 | 17.000149–19.009808 | 2 / 3589 | 0 | 33 |
| mixed-2 | 19 | 1 / 3000 | 19.000258 | 0.179384 | 0.079097 | 9.549914 | 18.000160–20.003442 | 5 / 12143 | 0 | 25 |
| mixed-2 | 38 | 2 / 500 | 38.000190 | 0.094046 | 0.095499 | 5.393681 | 37.000181–39.003292 | 0 / 0 | 0 | 3 |
| mixed-2 | 54 | 2 / 500 | 54.000200 | 0.097189 | 0.102407 | 5.120452 | 53.000210–55.007292 | 0 / 0 | 0 | 3 |
| mixed-2 | 55 | 2 / 500 | 55.000199 | 0.094780 | 0.104377 | 7.092616 | 54.000200–56.003469 | 0 / 0 | 0 | 4 |

For each overlapping RSS/sync pair, these are the recorded barrier intervals (same relative clock; not inferred disk service times):

| Case / RSS slot | Sync barrier sequence(s): t begin–end |
| --- | --- |
| mixed-0 / 3 | 28: 3.018837–3.022719 |
| mixed-0 / 10 | 83: 10.009880–10.011990 |
| mixed-0 / 12 | 178: 12.012881–12.014933 |
| mixed-0 / 13 | 225: 13.015497–13.017716 |
| mixed-0 / 15 | 319: 14.998936–15.001363 |
| mixed-0 / 17 | 414: 17.005270–17.007312 |
| mixed-0 / 18 | 461: 18.009558–18.011788 |
| mixed-0 / 19 | 509: 19.017255–19.019369 |
| mixed-1 / 11 | 131: 11.000588–11.002733 |
| mixed-1 / 13 | 226: 13.009654–13.011646 |
| mixed-1 / 17 | 415: 16.998922–17.001133 |
| mixed-1 / 18 | 462: 18.001947–18.004283 |
| steady-2 / 57 | 457: 56.998936–57.002371 |
| mixed-2 / 11 | 131: 11.006127–11.008272 |
| mixed-2 / 13 | 225: 12.998149–13.001862 |
| mixed-2 / 15 | 320: 15.003542–15.005916 |
| mixed-2 / 16 | 367: 16.006556–16.009532 |
| mixed-2 / 17 | 415: 17.008959–17.011076 |

## What is established, and what remains a hypothesis

- All 39 resource starts are timely; their excess wall time lies inside `LinuxReader.read(rss=True)`, rather than before entry. That operation checks cgroup directory identity; reads process identity, ancestry/controllers twice, actor membership twice, per-actor status/identity, cpu.stat, memory.events and memory.current; parses/validates values; then stamps its end. Its single wall bracket cannot separate these substeps or active work from off-thread pauses. Work after the end stamp is outside the acceptance bracket.
- Burst association is strong but descriptive: 24/30 RSS observations at mixed slots 10–19 have bad widths, versus 15/552 other retained RSS observations. The burst occupies [10,20) s and starts at slot 10. These are scheduled-phase labels, not claims of exact instantaneous receive rate. Repeated samples share a host/process and are not independent causal trials.
- Eighteen bad RSS brackets overlap a persistence barrier and 21 do not. No bad UTC bracket overlaps one. Persistence can therefore be concurrent context for some RSS events, but overlap is neither necessary nor evidence that fsync caused them.
- The enclosing counter windows have positive throttling deltas for 3/9 UTC events and 20/39 RSS events. Others have zero deltas, including steady-case failures. Consumer quota throttling is not a complete explanation. Positive windows cover roughly one or two seconds, far longer than each violation.
- All resource samples retain one actor, unchanged quota/ancestry, and zero memory.events counters (high/max/oom/oom_kill included). This gives no sampled evidence of a consumer-cgroup memory-pressure event; it does not establish absence of host reclaim, file stalls, or continuous RSS peaks.
- Host process inventories are before/after snapshots, not event-local runnable/CPU/steal/GIL/I/O traces. Prelaunch standard credit mode and last available 576-credit observation do not establish the balance or steal/credit behavior at each event. Shared public collectors, producer activity, OS scheduler/preemption, GIL contention and pseudo-file access costs remain possible but unisolated. No retrospective credit minimum is imposed.
- All nine accepted CPU windows and append/durability gates still pass; inclusive CPU and sampled RSS cannot establish incremental observer overhead or continuous RSS peak. Empty missed_slots and observed waits do not repair the 39 unknown coverage slots.

## One targeted prospective instrumentation recommendation

Add a **paired per-thread CPU-time delta to the existing RSS read bracket only**, using `time.thread_time_ns()` in the observer thread, alongside the existing monotonic endpoints. This targets the 39-event dominant ambiguity: high wall time with little thread CPU would support an off-thread/blocking component; comparable CPU and wall time would support work executed by the reader thread. It would not distinguish GIL wait from OS descheduling or blocking I/O, identify a slow pseudo-file, or resolve the nine historical UTC events. Process/cgroup CPU is unsuitable for this split because other recorder threads contribute.

This is a recommendation, not implemented or authorized for execution here. Keep the original monotonic acceptance endpoints and 5-ms/50-ms gates; explicitly specify placement and any enclosing CPU-scope uncertainty before implementation. Extra clock calls change observer work and scheduling even when thresholds stay fixed, so a future source/runtime freeze must prospectively identify that change and include its cost. Do not subtract measured CPU time from wall width, reinterpret prior violations, relax limits, add a tracing service, or claim an overhead guarantee. No new framework or additional standalone smoke is proposed.

## Reproduction and preservation

Private supplemental files under `.qcrl/reviews/recorder-cohort-native-20261015LupusCohort02/`: `bracket-contention-map-analysis.py` (one-off offline read-only analysis) and `bracket-contention-map.json` (all 48 events, exact monotonic endpoints, matching sends, adjacent counter brackets, barrier overlaps and SHA-256 hashes of all 24 input files). Supplemental mapping SHA-256: `7cf66362753cea5615ee048ae2395d63eba6ce123b22ce80f7e49a26de31eb75`. These files stay outside Git.

Checked unique event counts against the retained boundary review and independently enumerated the full frame/resource populations. Original evidence anchors remain: outcome `51609e2ecca1b155d0ea3a631b3961ee46b207489be49504dc0840782ce71b64`; frozen audit `c9296f31e5c89efb3071f883cdf15ff54f3ae1bbace64e70c01f2f1488f67618`. This is offline analysis on Intel macOS, not a new Linux validation, test suite run, native observation, or acceptance pass. Original OOM/failed evidence and frozen declarations are unchanged.
