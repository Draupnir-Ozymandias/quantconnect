# QCRL AWS collector

[`qcrl-collector.yaml`](qcrl-collector.yaml) creates a small, always-on,
execution-evidence collector. It cannot place orders. By default it receives no
Polymarket credentials; an optional manual probe can read one existing Secrets
Manager value through a narrowly scoped instance-role permission.

## What the stack creates

- One Amazon Linux 2023 ARM64 EC2 instance, pinned to a reviewed QCRL commit.
- AWS Systems Manager remains the recovery and bootstrap channel. Hardened SSH
  is also available from one explicitly declared operator IPv4 CIDR; password,
  keyboard-interactive, and root login are disabled.
- An encrypted, versioned S3 bucket retained when the stack is deleted.
- A one-minute `systemd` timer that discovers locked protocols from S3.
- Bounded execution retries using QCRL's existing capture worker.
- S3 replication of ignored raw evidence and capture state after each cycle.
- CloudWatch bootstrap and collector logs; host recovery, instance, heartbeat,
  and protocol-problem alarms; an SNS email subscription; and 80% forecast /
  100% actual monthly budget notices.

The supplied subnet must have a route through an internet gateway. The template
explicitly assigns the instance a public IPv4 address and allows TCP/22 only
from `SshIngressCidr`. Use the operator's current public IPv4 address with
`/32`; never supply `0.0.0.0/0`. HTTPS egress is required for GitHub, AWS APIs,
and the public Gamma/CLOB endpoints. AWS bills public IPv4 addresses separately
from the instance.

## Deploy

Choose an existing VPC and public subnet. Pin `RepositoryCommit` to a commit
that is already available from the configured repository URL.

```bash
aws cloudformation deploy \
  --stack-name qcrl-collector \
  --template-file infra/aws/qcrl-collector.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    VpcId=vpc-REPLACE_ME \
    SubnetId=subnet-REPLACE_ME \
    RepositoryCommit="$(git rev-parse HEAD)" \
    SshIngressCidr=REPLACE_ME/32 \
    SshPublicKey="$(cat ~/.ssh/qcrl_collector_ed25519.pub)" \
    ProbeSecretArn='' \
    AlertEmail=REPLACE_ME@example.com
```

Confirm the SNS subscription sent to `AlertEmail`. Inspect stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name qcrl-collector \
  --query 'Stacks[0].Outputs' \
  --output table
```

## Smoke test

Use the stack's `SshCommand` output for routine administration and file
transfer:

```bash
ssh -i ~/.ssh/qcrl_collector_ed25519 ec2-user@PUBLIC_IP_FROM_STACK_OUTPUTS
scp -i ~/.ssh/qcrl_collector_ed25519 FILE ec2-user@PUBLIC_IP_FROM_STACK_OUTPUTS:/tmp/
```

The security group accepts SSH only from `SshIngressCidr`. Session Manager
remains the recovery path if the operator's public IP changes or SSH fails:

```bash
aws ssm start-session --target INSTANCE_ID_FROM_STACK_OUTPUTS
```

On the instance:

```bash
sudo systemctl status qcrl-collector.timer
sudo systemctl start qcrl-collector.service
sudo journalctl -u qcrl-collector.service --since today
sudo tail -n 200 /var/log/qcrl/collector.log
```

The heartbeat alarm can initially enter `ALARM` while the instance bootstraps.
It should return to `OK` after the first successful collector cycle.

## Optional authenticated read probe

`ProbeSecretArn` is empty by default. In that state the instance role has no
Secrets Manager access and `qcrl-authenticated-probe` refuses to run. The
periodic collector never invokes the probe.

After separately creating a Secrets Manager value with exactly `address`,
`api_key`, `secret`, and `passphrase`, update the stack with that one complete
secret ARN. The conditional IAM policy permits only
`secretsmanager:GetSecretValue` on that ARN. No secret value is accepted as a
CloudFormation parameter or exposed as an output.

Bootstrap 6 stores the ARN reference in the stack-managed SSM String parameter
`/qcrl/STACK_NAME/probe-secret-arn`; an empty `ProbeSecretArn` stores `disabled`.
The instance role can read exactly that parameter. Each manual probe fetches
the latest reference before reading the credential secret, so subsequent ARN
changes do not require a reboot or edits to `/etc/qcrl-collector.env`.
Failed parameter reads and invalid/disabled values stop before secret access.

The first deployment of this repair replaces the launch template and EC2
instance. Review the change set for that replacement and for preservation of
the evidence bucket. Before execution, ensure there is no active/near-term
capture and the latest runtime evidence has reached S3. Reconnect using the new
stack outputs after bootstrap completes. Preserve the existing secret ARN,
network parameters, SSH key/CIDR, and other settings during the update.

Inspect the reference without reading credential contents:

```bash
aws ssm get-parameter --region us-east-2 \
  --name /qcrl/qcrl-collector/probe-secret-arn \
  --query Parameter.Value --output text
```

Fresh public captures remain protocol-driven. The collector does not run
`interpret-market`; documentation interpretation is a separate offline audit.

On the instance, preview the GET-only plan without reading credentials:

```bash
cd /opt/qcrl
python3 qcrl_execution_truth.py authenticated-probe 0xCONDITION_ID
```

Execute the sanitized probe through the root-owned streaming wrapper:

```bash
sudo qcrl-authenticated-probe 0xCONDITION_ID
```

See [`docs/AUTHENTICATED_PROBE.md`](../../docs/AUTHENTICATED_PROBE.md) for the
route allowlist, data-handling contract, and interpretation limits.

## Submit a locked protocol

The instance never follows `main` and never invents protocols. Upload an
already reviewed and committed protocol to the stack's `ProtocolInboxUri`:

```bash
aws s3 cp execution_truth/protocols/LOCKED_PROTOCOL.json \
  s3://BUCKET_FROM_STACK_OUTPUTS/protocols/LOCKED_PROTOCOL.json \
  --sse AES256
```

Do this before every declared capture window. The collector downloads protocol
objects and retained runtime evidence once per minute, validates them with the
pinned QCRL code, executes only currently eligible captures, and mirrors
`.qcrl/execution_truth/` back into the bucket's `runtime/` prefix. Hydrating the
runtime prefix before protocol evaluation preserves completion state across EC2
replacement. Old or already missed protocols remain inert.

Download evidence for local inspection without promoting it:

```bash
aws s3 sync s3://BUCKET_FROM_STACK_OUTPUTS/runtime/ .qcrl/execution_truth/
./synch.sh evidence protocol-status execution_truth/protocols/LOCKED_PROTOCOL.json
```

Promotion into `evidence/polymarket/live/` remains a separate, deliberate local
review step. The EC2 role can read protocol objects and write runtime objects,
but cannot delete bucket content or modify the GitHub/QuantConnect sources.

## Updating collector code

Push and review the new source commit first, then update the stack explicitly:

```bash
aws cloudformation deploy \
  --stack-name qcrl-collector \
  --template-file infra/aws/qcrl-collector.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    VpcId=vpc-REPLACE_ME \
    SubnetId=subnet-REPLACE_ME \
    RepositoryCommit=FULL_40_CHARACTER_COMMIT \
    SshIngressCidr=REPLACE_ME/32 \
    SshPublicKey="$(cat ~/.ssh/qcrl_collector_ed25519.pub)" \
    ProbeSecretArn=REPLACE_WITH_COMPLETE_SECRET_ARN_OR_EMPTY \
    AlertEmail=REPLACE_ME@example.com
```

`RepositoryCommit` and `bootstrap-N` are embedded in the launch template name.
Changing either replaces the template and its referenced instance, ensuring
bootstrap executes on a fresh host. Perform that update during a planned
no-capture window. Template maintainers must increment both the name and tag's
`bootstrap-N` whenever embedded bootstrap changes. S3 evidence survives stack
deletion because the bucket is retained. Secret-reference-only updates change
the SSM parameter and conditional IAM policy without instance replacement.
