# QCRL AWS collector

[`qcrl-collector.yaml`](qcrl-collector.yaml) creates a small, always-on,
public-evidence collector. It does not place orders and receives no Polymarket,
QuantConnect, GitHub, or AWS user credentials.

## What the stack creates

- One Amazon Linux 2023 ARM64 EC2 instance, pinned to a reviewed QCRL commit.
- No inbound security-group rules; administration uses AWS Systems Manager.
  Bootstrap explicitly starts the bundled SSM Agent and installs the regional
  AWS ARM64 package if the selected AMI unexpectedly lacks it.
- An encrypted, versioned S3 bucket retained when the stack is deleted.
- A one-minute `systemd` timer that discovers locked protocols from S3.
- Bounded execution retries using QCRL's existing capture worker.
- S3 replication of ignored raw evidence and capture state after each cycle.
- CloudWatch bootstrap and collector logs; host recovery, instance, heartbeat,
  and protocol-problem alarms; an SNS email subscription; and 80% forecast /
  100% actual monthly budget notices.

The supplied subnet must have a route through an internet gateway. The template
explicitly assigns the instance a public IPv4 address but creates no inbound
rules. HTTPS egress is required for GitHub, AWS APIs, and the public Gamma/CLOB
endpoints. AWS bills public IPv4 addresses separately from the instance.

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

Use Session Manager rather than SSH:

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

## Submit a locked protocol

The instance never follows `main` and never invents protocols. Upload an
already reviewed and committed protocol to the stack's `ProtocolInboxUri`:

```bash
aws s3 cp execution_truth/protocols/LOCKED_PROTOCOL.json \
  s3://BUCKET_FROM_STACK_OUTPUTS/protocols/LOCKED_PROTOCOL.json \
  --sse AES256
```

Do this before every declared capture window. The collector downloads protocol
objects once per minute, validates them with the pinned QCRL code, executes only
currently eligible captures, and mirrors `.qcrl/execution_truth/` into the
bucket's `runtime/` prefix. Old or already missed protocols remain inert.

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
    AlertEmail=REPLACE_ME@example.com
```

`RepositoryCommit` is embedded in a launch-template version, so changing it
causes CloudFormation to replace the instance and execute the bootstrap from a
clean host. Perform that update during a planned no-capture window. Template
maintainers must increment the launch template's `bootstrap-N` tag whenever the
embedded bootstrap itself changes. S3 evidence survives stack deletion because
the bucket is retained.
