# Ohio + Ireland synchronized observation experiment

Requested October 6, 2026. First two sites: existing Ohio (`us-east-2`) plus
Ireland (`eu-west-1`). Frankfurt is optional later, not part of the first rollout.
Purpose is public feed-path diagnosis, never order placement or jurisdiction
workarounds. Ireland proximity is a hypothesis; source-serving location is not
established.

## Dedicated clean replica

`qcrl-observer-replica.json` creates its own VPC/public subnet, a `t4g.small`
Amazon Linux ARM64 observer, encrypted 20 GiB gp3 volume, IMDSv2, SSM, optional
operator-only SSH, a versioned/retained TLS-only evidence bucket, and a limited
instance role. Permissions are SSM, its own runtime evidence objects, and its
own bootstrap completion signal. No probe secret, credentials, daily collector,
Polymarket account API, recurring capture timer, or automatic capture is included.

Bootstrap fetches the declared pushed source commit, installs the isolated
WebSocket runtime and service unit, checks SSH configuration, records initial
clock tracking, and schedules an absolute UTC stop deadline 48 hours later.
CloudFormation waits for a success signal; failure is not healthy bootstrap.
The stop timer is persistent across reboot and EC2 shutdown behavior is `stop`,
not termination. Encrypted disk and S3 evidence remain and continue to cost
money. Before any later deletion, preserve any unreplicated partial evidence.

Bootstrap refuses an existing primary `/opt/qcrl` host/runtime. A separate
`install_replica.py` configures a validated future declaration without starting
it, preserves previous environments, supplies the replica's regional bucket,
and reserves ten minutes after the last post-close checkpoint before the stop
deadline. Ohio continues to use its existing isolated installer and bucket.

## Deploy after cloud validation

From an authenticated administrative AWS shell, in Ireland:

```bash
aws cloudformation validate-template --region eu-west-1 \
  --template-body file://infra/aws/qcrl-observer-replica.json
aws cloudformation deploy --region eu-west-1 \
  --stack-name qcrl-ireland-observer \
  --template-file infra/aws/qcrl-observer-replica.json \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides RepositoryCommit=FULL_PUSHED_SHA ObserverLabel=ireland \
    RuntimeHours=48 SshPublicKey='TYPE BASE64_PUBLIC_KEY' SshIngressCidr=OPERATOR_IP/32 \
  --no-execute-changeset
```

Review the change set and scoped IAM role before execution. Do not reuse an
authenticated-probe role or add provisioning permissions to the Ohio collector.
The operator public key is non-secret; never upload the private key. Verify
the new host fingerprint through SSM before trusting a first SSH connection.

## Budget

The proposed initial monthly account budget alert is $75 (formerly $25), giving
room for the two-site diagnostic. This is a chosen notification allowance, not
a cost forecast or an enforced spend cap. Compute, public IPv4, EBS, S3 and
transfer/request costs are additional. A stopped replica retains storage costs.

Update the existing Ohio stack with its **previous template**, changing only
`MonthlyBudgetUsd` and preserving every other parameter with `UsePreviousValue`.
Create/review a change set and execute only if it modifies `MonthlyCostBudget`
without replacement or any other resource change. Do not redeploy the current
repository's primary template or replace Ohio during an active capture. Keep
existing alert recipients and percentage thresholds. Inspect actual billing
before further expansion; do not infer a new budget was applied from this file.

## Prospective synchronization gates

1. Verify both source commits, instance types, CPU/memory/storage limits, SSM/SSH
   identities, clock tracking, disk space, HTTPS/WebSocket connectivity and a
   bounded profiled smoke. Keep per-node clock/offset evidence; consistency of
   one clock is not accuracy or a bound on cross-host error.
2. Wait for any existing finite Ohio pilot to finish. Pin the same reviewed code
   on both sites. No mid-capture upgrades.
3. Generate **one** prospectively locked common plan with exact future BTC
   windows, profiling, resilience and deferred verification; distribute identical
   bytes to both observers. Verify its hash and sufficient lead time on both.
4. Confirm each environment uses its own bucket/region. The same plan hash may
   have the same local folder name; it must not have a shared writer destination.
5. Start both finite services before the pre-open boundary. Missed windows stay
   missed; independent discovery pins the same identities, terms and tokens.
6. Verify result links, manifests, both book baselines, watchdog reasons, gaps,
   checkpoints and every S3 copy before cross-node analysis.
7. Match canonical raw-event fingerprints and timestamps, preserving duplicate
   multiplicity, unmatched events and snapshot boundaries. No sequence-number,
   complete-delivery, signed-provenance, queue/fill or profitability guarantee
   follows. Shared delays may reflect common infrastructure or timestamp
   semantics; differences may reflect host, path or assigned session/shard,
   not geography alone.

Local tests cover the JSON template's bounded/security properties, validation,
absolute stop timer and stop-deadline reserve. CloudFormation validation and
real bootstrap/SSM/smoke verification are required before claiming deployment.
