# Order-reversed encoding confirmation, version 2

This separately declared six-case cohort confirms the
[first encoding pair](../infra/stream/SINGLE_PASS_ENCODING_2026_10_08.md).
It changes only cohort policy identity and pair order. The candidate, reference,
corpus, producer/consumer algorithms, receive-v3 contract, durations, rates,
heartbeat positions, numerical quotas, durability and process limits are unchanged.
Original Version 1 files and evidence remain untouched.

New order: candidate/reference, reference/candidate, candidate/reference.
Together the two cohorts have three pairs of each ordering, but confirmation
results must remain separately reported; do not rewrite or silently pool the
first cohort's results. Changing source-plan hashes changes individual header
identities, not the declared workload.

Each case retains the six-cycle 30-second / 30,000-message synthetic localhost
fixture. CPU quotas remain producer 100%, consumer 75%; each process has 512 MiB,
32 tasks and a 120-second cap. Twelve measurement workers and one Linux test
worker are finite. Audits occur offline after all measurements, not alongside them.

The confirmation wrapper reuses the original execution and verification code.
Both declarations additionally bind the wrapper and launcher source bytes.
Tests prove policy changes are limited to identity/order and launcher changes
are limited to paths, labels and order, and smoke-test both real socket lanes.

Audit every originating file, message/probe/heartbeat, row digest/representation,
receive record and full recovery trajectory. Verify configured limits against
saved systemd properties and check actual start times establish the reverse
ordering. Confirm old source hashes and corpus hashes match the first cohort.

Compare cohort-specific CPU medians and every paired difference, per-phase
delivery tails, worst delays, timing coverage, recoveries, producer attainment
and storage. The first trial's worst candidate burst and roughly 59% unknown
callback timing remain explicit acceptance concerns. A favorable median alone
does not permit public rollout or establish a cause of live gaps.

No public collection, credentials, trading, infrastructure changes, resource-limit
increase or QuantConnect synchronization is part of this confirmation.
