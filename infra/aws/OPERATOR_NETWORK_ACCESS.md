# Operator network access

“Upstate” and “jersey” are operator network-context labels, not fixed CIDRs.
Public IPs may change between or during sessions. Never infer the current
address from the label, a previous rule or this historical record.

## Verified rotation: 2026-10-09

After explicit approval, Ohio stack `qcrl-collector` changed only its
`SshIngressCidr` parameter from `71.104.111.76/32` to `64.246.159.39/32`.
CloudFormation change set `qcrl-ssh-network-20261009-6424615939` modified
`CollectorSecurityGroup` (`sg-001165b47b78281c0`) without replacement.
Stack reached `UPDATE_COMPLETE`; strict SSH to instance
`i-039c11d5ea49cf413` / `18.191.254.242` succeeded. Dublin was not changed.
This records a past observation, not a persistent IP assignment.

## Subsequent sessions

1. Check the actual public IPv4 from the machine/network used for SSH and
   compare it with the target instance's live SSH source rule.
2. Sign in through the existing Identity Center access portal, not root:
   `https://d-9a675fab47.awsapps.com/start/#/`.
3. If a rotation is needed, prepare a standard CloudFormation change set using
   the existing template. Change only `SshIngressCidr` to the observed IP `/32`;
   retain every other parameter, especially source revision, credentials and AMI.
4. Inspect the generated resource/property diff. Require only the intended SSH
   CIDR change, TCP/22 and no replacement. Stop if an AMI, instance, IAM, secret,
   budget, outbound rule or other resource would change. Request confirmation
   of the exact access change before executing it.
5. Verify stack completion, the live rule and strict SSH with the existing key
   and host pin. Never bypass host-key checking. Preserve collector configuration
   and service state; do not use a connectivity repair as authority to redeploy.

Do not open SSH to `0.0.0.0/0`, broaden the subnet to accommodate dynamic IPs,
automatically accumulate old networks or change other regions unnecessarily.
No credential/key change is needed merely because the operator network changes.
