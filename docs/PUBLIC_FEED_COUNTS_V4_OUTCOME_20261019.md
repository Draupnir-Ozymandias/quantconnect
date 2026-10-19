# Public-feed v4 — October 19 partial attempt

**Historical application FAIL remains unchanged. This attempt is
`partial_or_unresolved`, not a completed counting study.** All 60 primary count
rows are unresolved/null. There is no combined acceptance verdict or claim about
venue completeness, real-market performance, trading or execution.

## Fixed attempt and retained first fault

The user approved [v4](PUBLIC_FEED_COUNTS_SUCCESSOR_V4.md) under freeze
`59c54d22966b2da993e5437aa8a7c7c39baf9002b7e0f475533eed892da8efea`.
Exact execution source was `706ebed052945235dd44e7a5c5ef6a231059576c`, 552 selected
files. Fresh independent source/runtime/TLS/public/approval/namespace checks passed
at 15:44:12Z. The prepared helper was invoked once; the exclusive controller launch
was recorded at **15:45:00.529510Z**, PID 1940873. Live command/start identity and
unignored, uncaught HUP/TERM were independently observed for that controller.

One metadata opportunity began at 15:55:00.564281Z, used five bounded GETs, and
locked the matching BTC 16:00–16:05 UTC market at 15:55:01.133235Z. One private unit
started at 16:00:40Z. Worker readiness and independent controller release bind
case, epoch, PID 1942244, start identity, boot and cgroup. The retained running-unit
snapshot verifies source/command and the unchanged 512-MiB / 75% / 32-task /
240-second limits and isolation. No reconnect, retry, replay, substitute, extra run,
resource change, credential import or public-collector change occurred.

The partial log contains these archive-row timestamps and events:

| Event | Retained evidence |
| --- | --- |
| Connect attempt | 16:00:40.585588Z |
| Subscribed | 16:00:40.976751Z |
| Offending text, ordinal 597 | 16:00:41.662021Z; event type `new_market`, explicit `market` value different from the locked condition |
| Gap, ordinal 598 | 16:00:41.662702Z; `ContractError:explicit foreign asset/condition binding` |
| Native exit | SIGTERM, `ExecMainCode=2`, `ExecMainStatus=15`; 6.374003 seconds after unit start |
| Controller outcome | `partial_or_unresolved`: `worker exited without consumer receipt` |

The offending text was retained before the declared contamination rule stopped
acquisition. Its classification is `unconfirmed_or_other_market`. This establishes
that a notification for another condition was delivered on this subscription;
it does not establish that ordinary selected-market price/book data was misbound,
nor whether this notification is expected public-channel behavior. The prospective
rule explicitly treats an explicit foreign binding as fatal; it was not relaxed
or retrospectively reinterpreted. No new external request was made to diagnose it.

The exit occurred 5.005897 seconds after the gap. That is **consistent with** the
frozen five-second process guard around `conn.close()` after an early fault.
The sender of SIGTERM and exact close progress are unobserved: no final consumer,
completion or interrupt receipts survived. Do not promote that timing inference to
causal proof or treat it as normal acquisition completion. The exit happened before
the counting minute and far before the planned normal acquisition end. Public
normal-stop ownership was therefore not demonstrated by this attempt.

Systemd's retained `Result=success` does not override its signal-15 exit evidence
or the failed study outcome. Post-stop transient-unit fields reset to status zero;
the original `unit-after.txt` remains authoritative for this exit. No second unit
or controller was started. The controller stopped the exact private unit and sealed
its available evidence. Both controller and worker PIDs were independently absent
at 16:03:44Z; the unit was independently inactive/dead.

## What verifies, and what does not

Independent origin inventory and stable-file copy/hash review verified **45 files /
527,514 content bytes**, including all **21 producer-inventoried evidence files**
and all **552 frozen selected source files**. The 363,917-byte sealed copy SHA is:
`6839a795d68b20eda0ebbaae5f1c637f6bba5cd3a8396242ff58cab25062a122`.
Independent observed-manifest file SHA:
`bcad3fdf79a65733d64deb0442f4c8be0980df2d51f5162595237df5eb74de9e`.
Independent partial-review payload SHA:
`14e877392c33d93baa2062cc8a1e0ca7650d1699974f79d7aaa1f9dde3a84c1c`.

The only archive file is `segment-000000.gz.partial`, 114,894 bytes. Bounded
read-only decompression exposes 851,328 bytes containing **599 complete JSON
records**, with contiguous ordinals and independently verified record hashes and
chain: one session start, one connection attempt, one subscribed record, **595
text-frame rows**, and one gap. The final visible text is the foreign notification;
all preceding visible texts pass the same frozen contamination predicate.
No recovered bytes were appended, finalized or substituted for original evidence.

The gzip trailer, sealed segment descriptor, manifest, session-end footer, consumer
and completion witnesses are absent. Byte-copy integrity and prefix record-chain
verification do **not** establish archive finalization, total returned population,
application-return intervals, completion linkage or successful durable watermarks.
The 595 visible frame rows are a retained prefix count, not a verified full capture
population or a substitute for the intended counting measure.

The gap precedes the fixed M0 by 18.337312 seconds. The exact frozen report code
returns population `null` and 60 `unresolved_consumer` rows. See [all 60 rows](PUBLIC_FEED_COUNTS_V4_20261019.csv),
where literal `null` means unavailable, not zero. Lower/upper archived counts,
feed-activity upper bounds, ambiguity/unplaced totals and pre-window/tail totals
cannot be established using the required completion intervals. Archive-row times
were not substituted for missing callback intervals. All primary bins remain
unresolved; no missing period is filled with zeros.

## Resource, clock and audit limits

Only initial resource context survived: observed RSS 27,185,152 bytes and an
initial 2.517255-ms read bracket, before the primary window. This is not a peak or
whole-run bound. Retained unit CPU accounting is 598,131,000 ns across its short
lifetime, not primary-window recorder-only CPU or incremental observer overhead.
No final consumer/resource rows survived: inclusive primary CPU/RSS qualification,
original UTC/RSS bracket widths, scheduled resource missed slots, append/durability
upper intervals and memory-limit events over the full attempt remain unavailable.
The initial memory-event counters are zero; that is not a retrospective guarantee
about later events. No OOM cause is established by the retained signal-15 exit.

The controller's retained release checks bind live unit PID/start/boot/cgroup and
command, and the source and unit snapshots independently verify afterward. Our
separate native-unit inspection at 16:00:56Z found it already gone; independent live
worker signal masks were not observed. Its frozen guard requires default SIGTERM,
but missing live observation is not labeled as a passed independent signal check.
The initial offline live-inspection assertion failed because it expected a still
running unit; the snapshot is retained and no launch was repeated. The full-study
audit requiring consumer/completion was not applied as though those files existed;
the existing report's missing-consumer branch and a bounded partial-byte review
were used instead. No diagnostic or observer change was deployed.

Read-only clock context at 15:56Z reported NTP enabled/synchronized. That does not
establish an independent UTC accuracy bound. All UTC labels remain nominal. Fresh
credit mode/balance were unavailable; historical credit context remains historical,
without an invented minimum or added acceptance gate. Internal runtime retry counts,
unobserved source/network/library timing, incremental observer overhead, continuous
RSS peak and venue completeness remain unknown. Original 1-ms UTC, 5-ms RSS,
50-ms RSS-start and all other thresholds are unchanged; nothing was subtracted.

Post-run source/runtime/TLS/CA/public baseline verified unchanged, with no controller
post-check errors. Private retained bytes, inventory, report and review are in
`.qcrl/reviews/public-feed-20261019T160000Z/`. The one-time follow-up was deleted
after this audit. Historical v1/v2 not-run, v3 closure fault/unverified coverage and
synthetic application FAIL remain untouched. No further experiment is scheduled.

The useful next work is offline review of the foreign `new_market` notification
and the early-fault close/publication path. Any different treatment needs a
prospective successor contract; this attempt and its thresholds must stay intact.
No fix, threshold change or new native execution is authorized by this outcome.
