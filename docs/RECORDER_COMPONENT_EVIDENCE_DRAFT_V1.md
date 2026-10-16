# Recorder component-evidence contract — draft v1

**Original application-budget verdict: FAIL.** Cohort02 and RssCpu01 remain failed
under their frozen declarations. Their UTC failures and RSS coverage unknowns
remain prominent in every report. This draft creates no combined acceptance badge.

Identity: `qcrl.recorder_component_evidence.draft.v1`.
Status: **draft for review; not adopted, frozen, executable or execution-approved**.
Drafting and retrospective reporting over retained evidence are authorized;
collecting new evidence, running this as a replacement contract or promoting an
old result is not. This document has no launcher, evaluator or execution commands.

## Scope and reporting structure

Describe what independently linked components establish for an explicitly bounded
recording. Retain a component's original gate outcome alongside its observation,
population and limitations. Do not compute a new scalar verdict, eligibility
score, combined pass, readiness badge or general recorder certification.

Every report begins with the original experiment identity and failed/unknown
verdict, source/runtime freeze and originating byte anchors. Separate original
facts from new retrospective calculations. A historical report produced during
drafting does not execute or validate this draft. Future adoption would require a
separate prospective identity/freeze and approval for any new collection.

| Component | Required evidence and permitted description | Claim boundary |
| --- | --- | --- |
| Occurrence/archive fidelity | Exact ordered supported-text population, byte/hash/ordinal links, manifests/footer, gap/unsupported/terminal status, independently verified provenance | Bound to declared transport/population. Library-returned text retention does not establish all network or venue events. |
| Completion/durability | Every required occurrence linked to recorded monotonic observation, append completion and first successful covering fsync watermark; report full-population per-case/per-phase elapsed bounds and original limits | Start is the recorded application-observation stamp. Append is writer acceptance; successful fsync is a separate observed boundary. Neither proves crash-tail witness survival or pre-stamp delivery latency. |
| Local UTC precision | Actual monotonic enclosure of UTC acquisition for every witness, original <=1-ms qualification and all failures/unknowns | No absolute UTC accuracy, midpoint-error guarantee, cross-host subtraction or automatic bin eligibility. |
| Inclusive CPU | Actor/boot/cgroup/ancestry bindings and fresh counters enclosing each original complete 60-s window; retain original <=5-ms endpoint rule and <=70%-quota budget | Window-specific conservative bounds. No inference to incomplete tails, unmeasured runs, guaranteed host capacity or incremental observer overhead. |
| Current RSS sweeps | Unique live actor VmRSS sum, actual interval, slot/target/lateness, original <=5-ms width / <=50-ms start / <=80%-memory qualification and every missed/racing/invalid slot | Sequential sweeps, not atomic unit snapshots or continuous peaks. Low admissible values do not establish compliance at unqualified/missing slots. |
| Resource/lifecycle context | Unit exits, memory events, throttling, whole-unit startup/capture/close/publication accounting, producer costs, host/credit observations with timestamps and unavailable fields | No invented credit minimum, event-specific cause, memory-safety guarantee or subtraction of observer cost. |

## Essential invariants

- Preserve original bytes, source/dependency/runtime/clock-domain identities and
  independent origin attestations. Self-reported hashes are not signatures.
- Keep every supported occurrence, duplicate, malformed/unknown frame, terminal
  state and timing outlier in its original denominator. Do not select favorable
  phases, retries, timing-qualified rows or repetitions for performance claims.
- Preserve all original thresholds and component outcomes. Wide UTC observations
  remain original precision failures; invalid RSS slots remain original unknowns.
- Expose what each observation interval actually brackets. No clock correction,
  interpolation, baseline/CPU subtraction, fabricated zero, substitute measure,
  retrospective endpoint move or inferred instantaneous RSS.
- Preserve fresh reads and actor/path/membership/race proof. Attribute resources
  inclusively; never convert inclusive cost to incremental overhead.
- Report counts/denominators, known failures and unavailable coverage explicitly.
  Never infer continuous/high-water memory or unobserved timing precision.

## One downstream question per descriptive report

State the question, event definition, population, clock domain, exclusions and
bin/boundary rule before calculating the new summary. Label analysis of existing
data retrospective and exploratory, even if its calculations are specified first.
Do not call the choice a preregistered experiment or use it to repair old gates.

For an interval-defined local-observation count with bins `[epoch+k, epoch+k+1)`,
report a lower count of intervals wholly contained in the bin and an upper count
of intervals intersecting it. Treat the acquisition enclosure as closed, so an
upper endpoint exactly on a boundary is potentially in the following bin.
No midpoint or arbitrary assignment of a straddling interval. Possible counts
across bins need not sum to the population; ambiguous occurrences are reported
once with all candidate bins. Preserve every wide-UTC row and its failure label.

A wider-than-1-ms interval can still lie within one one-second bin. That supports
only the bin's coarse local interval property; it does not qualify the row under
the original precision rule. If a required clock mapping, observation or boundary
is absent, state that the question is unresolved for that population.

Use exact representations of retained clock values for boundary comparisons.
Distinguish the callback's timestamp acquisition from library-internal receipt,
kernel/network arrival and source-event time. Shared native monotonic epochs can
support within-case local bins; UTC/calendar or cross-site bins need their own
independent alignment and uncertainty evidence. No uncertainty bound may be
invented from display precision or clock resolution.

## Adoption and authority boundary

This draft changes no production source, measurement, threshold, frozen protocol
or old audit. There is no new acceptance implementation. Before any future
adoption, review the exact scientific claims and dependencies, settle the event
and clock/coverage semantics, then give the successor its own immutable identity.
Any native/public collection requires a separately approved bounded packet.

No automatic smoke, cohort, observer redesign, public rollout/capture, resource
change, credential import, infrastructure action, QuantConnect sync or orders.
Source-age/lead-lag, book reconstruction, real-market flow, sustained capacity and
strategy conclusions need independent questions and suitable observations.
