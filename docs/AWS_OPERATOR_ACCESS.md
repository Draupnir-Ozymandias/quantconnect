# Local AWS operator access

Prepared October 17, 2026 on the Intel Mac in response to the user's explicit
request for SSH and AWS API access. No experiment, host command, IAM change,
network change, credential-file import or expired-target execution is part of
this setup. The public-feed v1/v2 not-run outcomes and historical FAIL stand.

## Installed locally

AWS CLI **2.38.1** and Session Manager plugin **1.2.896.0**, x86_64, were obtained
from AWS's official signed packages. `pkgutil` verified the AMZN Mobile LLC
installer chain and Apple trusted notarization. The plugin binary's code
signature also verified. Payloads were installed under the user's `.local/opt`
directory with no sudo, Homebrew, launch daemon, system installer script or
replacement of the existing `/usr/local/bin/aws` installation.

The wrapper `/Users/eric/.local/bin/aws-qcrl` selects the user-local current CLI,
named profile `qcrl-ohio` and Ohio region, and exposes the local Session Manager
plugin on its PATH. Its shell syntax and both tool versions verify. Private
package/binary hashes and installation receipts are retained under
`.qcrl/access-setup/20261017/`; no authentication tokens are recorded there.

The existing CLI was 2.2.2, with only a default profile configured for another
region. A bounded STS identity call using those existing credentials returned
`InvalidClientTokenId`. That is an authentication failure, not proof about EC2
connectivity or permissions. Existing default configuration and the credentials
file were not changed by the agent. A private pre-change config copy is retained.

## Named SSO profile

The new `qcrl-ohio` profile uses SSO session `qcrl-lupus`, the already documented
access portal/account and existing AdministratorAccess role. The user explicitly
confirmed Ohio as the Identity Center directory region; both SSO and operational
regions are therefore `us-east-2`. No role/policy or permanent access key was
created. This is an existing broad role, not a claim of least-privilege isolation.

Authenticate interactively with your own browser when needed:

```sh
/Users/eric/.local/bin/aws-qcrl sso login --no-browser --use-device-code
```

The CLI displays a fresh verification URL and short-lived code. The user should
confirm the CLI request in their own browser; never put tokens, passwords or
access keys into this repository or chat. Verify only the resulting identity:

```sh
/Users/eric/.local/bin/aws-qcrl sts get-caller-identity
```

The user completed device authorization on October 17. A bounded STS call using
this named profile then succeeded and verified the expected account and existing
AdministratorAccess assumed role. The identity response is retained privately;
no credentials or device codes are included in tracked documentation. This
verifies authentication, not EC2/SSM permissions or instance connectivity.

SSO uses temporary credentials and supports refresh, but periodic user sign-in
can still be required. The API replaces routine console interactions, not every
authentication step. See [AWS CLI SSO configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

## SSH preparation and remaining gates

The existing `~/.ssh/qcrl_lupus_ed25519` key was preserved, not regenerated or
loaded into an agent. A mode-0600 `~/.ssh/config` was created only because none
existed. Its `qcrl-ohio` alias selects the documented `ec2-user` and IP with that
identity, `IdentitiesOnly yes`, `BatchMode yes`, a ten-second connection timeout
and **StrictHostKeyChecking yes**. Effective local settings verify via `ssh -G`.

There is no pinned known-host entry for the documented IP, and authorization of
this public key on the instance remains unverified. Current IP-to-instance
binding also needs fresh verification. The alias is prepared; it is not a claim
of a working or authenticated SSH connection. Do not replace those missing gates
with unauthenticated keyscan trust or disabled host-key checking. No remote
`authorized_keys` edit or inbound port change occurred.

## Session Manager API

AWS exposes `StartSession` and supports interactive shells through the AWS CLI
and installed plugin, as well as SSH session options. This can support a console-
independent operational transport once authentication, permissions and target
binding are established. See [AWS CLI Session Manager workflow](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)
and [StartSession API](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_StartSession.html).

No SSM session/Run Command, EC2 modification or instance command has been invoked
by this setup. The browser's console-origin denial is still reported after the
user removed site-specific exceptions. This setup does not use another transport
to perform those blocked host actions. Future operations must respect effective
access decisions and their own authorization; valid API credentials do not revive
either expired study packet. A new capture requires a new prospective declaration.
