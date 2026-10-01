# Authenticated non-trading CLOB probe

**Status:** implemented and fixture-tested; live credentials not provisioned

## Purpose

The probe asks whether L2-authenticated, read-only CLOB responses directly
expose either execution field that public market observations currently omit:

- `itode`: taker-delay enablement;
- `oas`: minimum order age in integer seconds.

It is a field-visibility probe, not an order experiment. Field absence remains
unknown and does not establish `false` or zero. Even an observed field describes
an API response; it does not prove matching-engine timing or fill behavior.

## Mechanical safety boundary

`execution_truth/authenticated_probe.py` exposes only two named requests:

1. `GET /data/orders?market=<condition_id>`;
2. `GET /auth/ban-status/closed-only`.

The caller cannot provide an HTTP method, URL, body, order ID, or arbitrary
query mapping. `POST`, `PUT`, `PATCH`, and `DELETE` are absent from the
transport. The module contains no wallet key, EIP-712 signing, order building,
order submission, cancellation, or heartbeat implementation.

The HMAC input follows the current official CLOB L2 contract:
`timestamp + GET + request_path`; the query string is not included. Tests pin
that behavior and the exact route allowlist.

## Data handling

Credentials are read from JSON on standard input and must contain exactly:

```json
{
  "address": "0x...",
  "api_key": "...",
  "secret": "...",
  "passphrase": "..."
}
```

The probe processes authenticated payloads only in memory. Its stored artifact
contains response shapes, exact target-field observations if present,
limitations, provenance, and hashes. It excludes credentials, authentication
headers, raw orders, order IDs, trade history, balances, and raw account
payloads.

## Dry run

Dry run needs no credentials and performs no network access:

```bash
./synch.sh evidence authenticated-probe 0xCONDITION_ID
```

It prints the hashed request plan and forbidden capabilities.

## AWS execution

The collector stack accepts an optional `ProbeSecretArn`. When empty, no
Secrets Manager permission exists and the wrapper refuses to run. When set,
the EC2 role can call `secretsmanager:GetSecretValue` on exactly that ARN.
CloudFormation does not create, output, or inspect the secret value.

After separately creating and populating the secret, update the stack with its
complete ARN. Then connect through SSH or Session Manager and run:

```bash
sudo qcrl-authenticated-probe 0xCONDITION_ID
```

The wrapper streams `SecretString` directly from AWS CLI into the unprivileged
Python process. It does not place the value in command arguments, environment
variables, files, service logs, S3 paths, or shell history. The sanitized probe
artifact is written under `.qcrl/execution_truth/authenticated_probe/` and is
covered by the collector's existing runtime-evidence synchronization.

## Interpretation gate

A successful authenticated request proves only that the credentials and fixed
read route worked. Promote neither field unless it is explicitly present with
the required type and all occurrences agree. If both remain unknown, the
latency batch remains fail-closed and the next step is documentation/vendor
clarification or a separately authorized shadow/minimal-risk experiment—not an
inference from empty order history.
