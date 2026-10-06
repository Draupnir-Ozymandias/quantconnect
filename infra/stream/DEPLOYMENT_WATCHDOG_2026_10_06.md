# Ohio watchdog activation — October 6, 2026

The existing isolated Ohio observer remains pinned to tested source
`a25be8177ff4f6b8422e0f6182ec4d1cbea125f3`. The twelve resilience tests were
rerun on EC2 immediately before activation and passed. No source update was
needed. Existing instance is `t4g.small`, verified using only the instance-type
metadata path; no IAM credentials or secret values were read.

## Locked, finite pilot

Schema `qcrl.btc_5m_rolling_pilot.v4`, declaration
`2026-10-06T19:32:48.797445Z`:

`0e54d82f57360cba89e9843ff66d8a4363692862ee00e9dfb0192be31b7a4b7f`.

| Start epoch | Start UTC | Start Eastern |
| --- | --- | --- |
| 1791315600 | 19:40 | 3:40 p.m. |
| 1791315900 | 19:45 | 3:45 p.m. |
| 1791316200 | 19:50 | 3:50 p.m. |

Last scheduled market ends at 3:55 p.m.; end-plus-120-second checkpoint is due
about 3:57. Deferred verification/health and replication follow. Service was
confirmed active/running before the first window; completion is not yet claimed.

The exact resilience policy is now present in the declaration and pinned stream
headers: initial both-book deadline 10 seconds, active selected book/price-change
silence 30 seconds, more-than-five-second timestamp ages sustained for ten
seconds, equal-jitter exponential retries, and maximum three connection attempts.
Profiling and verification-after-all-workers remain active. CPU/memory,
frame/byte/spool caps and two-worker concurrency remain unchanged. Exhausting
attempts can intentionally produce an incomplete/unhealthy cohort; do not
increase caps to manufacture green status or infer the heuristic proves a fault.

Runtime S3 prefix:
`s3://qcrl-collector-artifactbucket-icipysa9venc/runtime/streams/pilot-0e54d82f57360cba89e9843ff66d8a4363692862ee00e9dfb0192be31b7a4b7f/`.
The previous environment and all evidence cohorts are retained. Daily timer
remains active. No instance, disk, IAM, firewall, credentials, QuantConnect,
trading or recurring-schedule changes occurred.

## Proposed geographically synchronized comparison

User requested Ireland and Amsterdam replicas to compare simultaneous public
observations with Ohio. AWS currently lists Ireland as `eu-west-1`; Amsterdam
appears among announced, not available, Local Zones, under the European Sovereign
Cloud. Frankfurt `eu-central-1` is a proposed alternative, not an authorized
silent substitution. Location and intended paid runtime are awaiting user choice.
No extra instances or stacks have been created by this activation.

References reviewed October 6:
[AWS Regions](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html),
[available Local Zones](https://docs.aws.amazon.com/local-zones/latest/ug/available-local-zones.html),
[announced Local Zones](https://aws.amazon.com/about-aws/global-infrastructure/localzones/locations/).

Before a synchronized experiment:

- Deploy clean public-observer-only hosts, not cloned credential-bearing disks
  or the daily/authenticated-probe role. Use the same instance shape, code,
  capture policy and declared market windows. Pin market identity/terms/tokens.
- Check clock synchronization and retain offset/uncertainty, host/region and
  runtime provenance. Local clock consistency is not proof of cross-host accuracy.
- Use separate evidence buckets/prefixes and least-privilege per-node roles.
  Identical plan hashes must never cause three writers to share one destination.
- Compare matching raw event fingerprints/timestamps, preserving duplicates,
  unmatched events, snapshot boundaries and connection gaps. There is no proven
  total ordering/delivery guarantee; never merge recordings into invented fills.
- Keep per-node profiling and synchronization/upload policies equivalent.
  Shared delays suggest common infrastructure/timestamp semantics; node-specific
  delays suggest path/host/session differences, not necessarily geography alone.
- Declare a bounded synchronized cohort only after all nodes are bootstrapped
  and verified. Do not launch already elapsed windows. All replicas remain
  public-data-only, without trading/authentication or jurisdiction workarounds.
- Additional EC2, EBS, public IPv4, storage and transfer charges require explicit
  operational scope; the existing $25 budget is not automatically changed.

No local AWS CLI or active AWS browser session was available during this turn;
new stack deployment will require an authenticated administrative AWS session.
Do not expand the existing collector's instance-role privileges to provision it.
