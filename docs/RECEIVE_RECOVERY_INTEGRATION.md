# Explicit v3 recorder/archive integration and matched controls

This extends the verified [v3 foundation](RECEIVE_PATH_RECOVERY_POLICY.md).
`qcrl.public_market_stream_spec.v7` explicitly requires receive policy v3,
segmented storage, profiling, resilience and freshness telemetry. Defaults remain
v1/v2; rolling discovery/service/public CLI selections are not broadened here.
No public deployment is implied by the low-level opt-in recorder accepting v7.

V7 instantiates `ReceiveRecoveryTracker`. Sealed-stream verification uses the
bounded incremental `RecoveryConnectionAudit` to check every retained delivery's
occurrence and generation/fence trajectory against raw frames. Known messages
after an unknown interval are accepted only under that verified trajectory,
never by weakening v1/v2's irreversible-disable checks. Reconnect resets retain
Restored markers must also use frame ordinals beyond their complete-frame fence;
the validator rejects rehashed reuse of a fence frame, including later draining.
Reconnect resets retain
unknown-backlog and previous-generation fields; previous generation is checked
against the archived prior connection. Freshness replay and structured closes
are verified for v7 as for v6. Old valid v4/v5/v6 report shapes stay unchanged.

`receive_recovery_verification.v1` reports per-connection known/unknown/recovery
counts and bounded latest alignment, with explicit finalized-session status.
It verifies retained deliveries, not unseen packets or callback completeness.
An adapter-failure fallback cannot supply a complete v3 trajectory: verification
fails closed while raw archives remain preserved; no recovery claim is invented.

Offline `receive_phase_analysis.v3` separately counts normal, draining, unknown
and recovered timing populations, retains unknown denominators and reports
verified recovery generations. Its old v1/v2 policies/results remain unchanged.
The explicit `--burst-root` analysis route checks the exact declaration, corpus,
source-file bytes, recorder lane specification, raw bundle, source report and
sealed archive before admitting a matched synthetic case. Source hashes bind
integrity, not authenticated origin or measurement truth.

## Prospective matched burst policy v3

The runner's NEW `qcrl.burst_reader_policy.v3` runs **18 cases**: three rotating
rounds of bare/receive/full recorder, each under receive v2 AND v3. Lane order
alternates by round plus original mode index (bare=0, receive=1, recorder=2).
Three rounds leave a one-case order imbalance per mode; do not claim perfect
counterbalancing or independent market trials. Bare duplicates are controls for
host variation, not evidence that bare reading uses callback tracking.

All lanes retain the same corpus/template cycling, six cycles of four seconds
at 500 and one at 3,000 target messages/sec, 30,000 messages per case, and six
scheduled synthetic text PONGs replacing cycle-final data messages. Probe clocks
and serialization can change bytes slightly; this matches workload structure,
not literally identical real-time payload bytes or exchange emission history.
Producer/consumer groups remain separate 100%/75% quotas, each 512 MiB, 32 tasks,
120-second runtime maximum, shared host/no core affinity. No resource upgrades.

The finite launcher now REQUIRES a fresh diagnostic source clone as its second
argument, under `/var/lib/qcrl-stream/receive-recovery-*/source`, and runs only
while the public observer is inactive. The deployed source checkout is neither
moved nor edited. New output/declaration roots are mandatory; prior cohorts are
not overwritten, resumed or reclassified. Failure stops the run without retry.
After each recorder case, the source-bound offline v3 analyzer runs outside all
measured loops. All modes retain raw bodies and all timings/coverage counters.

Interpret matched results as conditional callback coverage, consumer CPU and
producer-to-delivery upper bounds; unknown messages NEVER get fabricated callback
timestamps. The initial counter-fence foundation test is not proof that every
burst drains far enough to recover, nor that continuing observation is free.
Verify actual phase pacing, raw identities, sealed streams, unit settings,
fence trajectories and local/source file bytes before reporting conclusions.
