# Separate-quota synthetic localhost burst comparison

Historical initial policy `qcrl.burst_reader_policy.v2`: six five-second cycles per case,
each with four seconds at 500 target messages/second then one second at 3,000.
Three rotating-order rounds of bare reader, receive-v2 instrumentation and
unchanged full stream-v6 recorder give nine cases, 30 seconds / 30,000 messages
each. No observed exchange emission distribution is claimed. The corpus stays
the hash-bound sample used by the earlier paced comparison.

Producer and consumer are separate processes in separate transient systemd
cgroups, respectively 100% and 75% of one CPU, each 512 MiB / 32 tasks and
120-second runtime cap. This separates CPU quotas, NOT physical cores, host
scheduling, network/kernel memory or disk. There is no core affinity. Host CPU
contention, burst send blocking, producer lateness and post-loop publication
remain possible. All cases use compression/pings disabled, max queue 16 and
max message 256 KiB. Only 127.0.0.1 is contacted; no credentials or trading.

The full recorder's application text heartbeat remains unchanged. The synthetic
producer replaces the last scheduled message of EACH five-second cycle with text
PONG in ALL modes: 29,994 book/update messages plus six control frames. These are
scheduled fixture controls, not genuine network acknowledgments or responses to
observed PING. No account/order messages are generated. A case hitting any recorder
bound remains a failure, never complete evidence. This is not a complete simulation
of the public protocol or a live market.

The retained initial v1 cohort was stopped on its first full-recorder case:
the fixture omitted PONGs and incorrectly assumed the timeout began at first
PING. It actually begins at connection; the recorder correctly closed at about
30 seconds after 28,840 frames. The producer then failed on its closed socket.
Two complete bare/receive cases and the partial recorder remain preserved;
they cannot provide a complete three-round ranking. The corrected v2 uses a new
declaration and directory, never overwrites or resumes that failed cohort, and
changes no public collector code or watchdog policy.

Absolute-deadline producer timestamps precede serialization/send, not wire
arrival. Shared-host monotonic time is compared only with matching boot identity.
Raw messages for ALL modes are retained after the timed consumer loop, alongside
delivery/receive/queue observations. Exact raw and probe-sequence equality,
deadline schedule, phase statistics and sealed full-recorder raw streams are
checked offline. Unknown receive-v2 markers stay unknown; no timing is invented.
Raw persistence outside the bare/receive measured loop deliberately differs from
the inline full recorder. Consumer process CPU covers all its reader/background
threads plus handshake/close, not pure read cost. Baseline phase tails may include
residual burst backlog. Do not pool these as independent market trials.

The declaration binds policy/corpus and source file bytes. Artifact hashes are
integrity links, not origin signatures. Distinct cgroups are checked by the runner;
actual quota and unit success must also be independently checked from retained
systemd properties. Reports explicitly do not assert quota verification alone.
Artifacts are exclusive writes. Failure stops the launcher, preserves evidence
and performs no retry, public capture, timer modification or resource change.

The current matched v3 policy and two-argument diagnostic-clone launcher are
documented in [the integration contract](RECEIVE_RECOVERY_INTEGRATION.md).
The original v2 source/launcher remain bound to their historical Git revisions.
The root-only finite Linux launcher is `infra/stream/run_burst_reader_comparison.sh`.
It requires an inactive observer, clean committed checkout, more than 4 GiB free,
a fresh explicitly named `/var/lib/qcrl-stream/reader-burst-*` root and the already
retained corpus. It leaves the daily collector and public observer configuration
untouched. Results remain diagnostic artifacts outside the research inventory.
