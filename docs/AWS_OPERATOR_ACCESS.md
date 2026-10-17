# Local AWS operator access

Prepared October 17, 2026 on the Intel Mac in response to the user's explicit
request for SSH and AWS API access. Initial setup was local; subsequent SSH
verification used only the three read-only commands recorded below. No experiment,
IAM change, network change, credential-file import or expired-target execution
occurred. The public-feed v1/v2 not-run outcomes and historical FAIL stand.

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

## SSH preparation and verified access

The existing `~/.ssh/qcrl_lupus_ed25519` key was preserved, not regenerated or
loaded into an agent. A mode-0600 `~/.ssh/config` was created only because none
existed. Its `qcrl-ohio` alias selects the documented `ec2-user` and IP with that
identity, `IdentitiesOnly yes`, `BatchMode yes`, a ten-second connection timeout
and **StrictHostKeyChecking yes**. Effective local settings verify via `ssh -G`.

On October 17, authenticated EC2 `DescribeInstances` confirmed that the running
instance `i-039c11d5ea49cf413` owns `18.191.254.242` in `us-east-2a`.
`GetConsoleOutput` returned its boot host public keys and fingerprints. The
ED25519 public key was independently hashed, matched to the console fingerprint,
then appended to the local `known_hosts` without replacing existing entries:

`SHA256:V6fmypTZ7S70IPMgsXfvm/FzJ+tUqtjHrH2xGBC5uq0`

A bounded SSH authentication-only check (`-N -T`, no forwardings, no password
prompts, strict checking and ED25519 selected) confirmed the live server matches
that pin. It then failed with `Permission denied (publickey,gssapi-keyex,gssapi-with-mic)`.
The existing local key therefore did not authenticate; the exact server-side
reason is unknown without authorized server inspection. No shell or command was
requested, and no remote `authorized_keys` edit or inbound port change occurred.
API responses, console bytes, the original local known-hosts backup and check
receipts are private under `.qcrl/access-setup/20261017/`.

The earlier statement that browser enforcement categorically prevented SSM key
installation was an overly broad interpretation. The actual browser denial
applied to the console-origin operation and workarounds achieving the same
outcome; it did not expressly prohibit all independently authorized SSH/API/SSM
operations. No SSM key-installation request was made or denied.

The user subsequently reported successfully installing the public key through
their own AWS session and connecting from the Mac. Following their instruction
to proceed, a strict, pinned SSH connection independently succeeded as `ec2-user`
at `2026-10-17T17:54:52Z`. The only remote checks were `id -un`, `hostname` and
`date -u`; the hostname was `ip-172-31-4-31.us-east-2.compute.internal`.
SSH access is now verified. The agent did not edit remote key files or change
services, resources, networking or experiment state.

## Session Manager API

AWS exposes `StartSession` and supports interactive shells through the AWS CLI
and installed plugin, as well as SSH session options. This can support a console-
independent operational transport once authentication, permissions and target
binding are established. See [AWS CLI Session Manager workflow](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html)
and [StartSession API](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_StartSession.html).

No agent SSM session/Run Command or EC2 modification has been invoked by this
setup. The three read-only SSH identity/time checks above are the only agent
instance commands in this access milestone. Browser console-origin access remains
unverified since its last denial; successful SSH does not demonstrate a change
to browser policy. Future operations must respect effective access decisions and
their own authorization. Working SSH/API access does not revive either expired
study packet. A new capture requires a new prospective declaration.
