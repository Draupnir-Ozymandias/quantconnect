# CLOB schema review and interpretation policy

Reviewed: 2026-10-03. Policy: `qcrl.clob_documentation_policy.20261003.v1`.

## Findings

The current [market-info reference](https://docs.polymarket.com/api-reference/markets/get-clob-market-info)
and [OpenAPI schema](https://docs.polymarket.com/api-spec/clob-openapi.yaml)
state that `itode` is omitted when false. When true, marketable orders wait
250 ms before synchronous processing. The [order lifecycle](https://docs.polymarket.com/concepts/order-lifecycle)
describes revalidation after that hold on selected crypto/finance up/down
markets. This supersedes the documentation uncertainty recorded on September 8;
the date on which these semantics became effective is not established.

Top-level `oas` is an integer described as minimum order age in seconds.
Its omission default and operational scope remain undocumented. The separately
observed rewards field `r.moas` must not be substituted for `oas`.
The [SDK types](https://github.com/Polymarket/py-clob-client-v2/blob/main/py_clob_client_v2/clob_types.py)
also contain an order-age property in rewards configuration; this is a reason
to seek clarification, not proof that the two fields are interchangeable.

An October 3 public GET for September 30's condition
`0x2d54643178d08630377167a5c32d896fd87bec4ca87be8957817d99ccbcf351c`
omitted `itode` and `oas` and returned `r={mi:50,ma:4.5,moas:30}`.
That diagnostic response establishes current metadata only. It has not been
promoted as historical or content-addressed raw evidence.

The two successful authenticated probes at 19:01:54 and 19:17:55 UTC on
October 3 exposed neither target field. Their response summaries omit order
counts, order contents, and the closed-only value. They cannot establish empty
order history or a particular account restriction state.

## Interpretation artifact

`execution_truth/schema_interpretation.py` emits
`qcrl.clob_schema_interpretation.v1` from a verified raw market bundle. It pins
the policy, documentation URL and review date, observation timestamp, original
bundle/contract/payload hashes, raw field presence, and interpretation basis.
It verifies the exact public market-info endpoint.

Default interpretation preserves missing `itode` as unknown. An explicit
`--apply-current-documentation` declaration resolves absent `itode` to false
only for observations dated October 3 or later in UTC. This date guard is a
conservative audit boundary, not a claim about the exchange's deployment date.
Explicit null remains unknown; explicit boolean values remain unchanged.
Missing/null `oas` remains unknown. An explicit integer is retained while its
operational scope remains unresolved.

```bash
./synch.sh evidence interpret-market PATH_TO_RAW_BUNDLE.json
./synch.sh evidence interpret-market PATH_TO_CURRENT_RAW_BUNDLE.json \
  --apply-current-documentation
```

Both commands are offline and print a hashed JSON sidecar. Market contract v3,
normalized bundle v2, promoted inventories, and replay gates remain unchanged.
The sidecar is not consumed by replay. Historical September captures cannot
receive the current omission default through this policy. A future replay
integration requires a separately versioned change and resolution of `oas`.

## Support question (draft, not sent)

For `GET /clob-markets/{condition_id}`, what does top-level `oas` govern:
order acceptance, matching, or liquidity-reward eligibility? What does its
omission mean, and how does it differ from rewards `r.moas`?

Your current documentation says omitted `itode` means false and an enabled
taker delay is 250 ms. Does that omission rule apply to historical September
2026 responses? Can either setting change after a market closes, and is there
an endpoint or published history for the settings in effect while it traded?

Example condition ID:
`0x2d54643178d08630377167a5c32d896fd87bec4ca87be8957817d99ccbcf351c`.

No credentials or account identifiers are necessary for this question.
