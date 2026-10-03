"""Versioned documentation interpretation alongside immutable market evidence."""

from datetime import datetime, timezone

from .bundle import normalize_bundle
from .contracts import ContractError, CLOB_MARKET_ENDPOINT, payload_hash


INTERPRETATION_SCHEMA = "qcrl.clob_schema_interpretation.v1"
POLICY_ID = "qcrl.clob_documentation_policy.20261003.v1"
DOCUMENTATION_URL = (
    "https://docs.polymarket.com/api-reference/markets/get-clob-market-info"
)
REVIEW_DATE = "2026-10-03"


def interpret_market_bundle(raw_bundle, *, apply_current_documentation=False):
    """Verify a bundle and record explicit values versus documented defaults.

    This sidecar is not consumed by replay. Current documentation applicability
    must be declared by the caller; its historical effective date is unknown.
    """
    if type(apply_current_documentation) is not bool:
        raise ContractError("documentation applicability must be boolean")
    normalized = normalize_bundle(raw_bundle)
    market = normalized["market_contract"]
    observation = raw_bundle["observations"]["clob_market"]
    condition_id = market["identity"]["condition_id"]
    endpoint = CLOB_MARKET_ENDPOINT.format(condition_id=condition_id)
    if observation["endpoint"] != endpoint:
        raise ContractError("interpretation requires the public CLOB market-info endpoint")
    observed_at = market["observed_at_utc"]
    observed_date = datetime.fromisoformat(
        observed_at.replace("Z", "+00:00")
    ).astimezone(timezone.utc).date().isoformat()
    if apply_current_documentation and observed_date < REVIEW_DATE:
        raise ContractError("current documentation cannot be applied to pre-review captures")

    payload = observation["payload"]
    delay = market["constraints"]["taker_order_delay_enabled"]
    delay_basis = "explicit_value" if delay is not None else "unknown"
    if "itode" not in payload and apply_current_documentation:
        delay = False
        delay_basis = "documented_omission_default"
    age = market["constraints"]["minimum_order_age_seconds"]
    result = {
        "schema_version": INTERPRETATION_SCHEMA,
        "policy_id": POLICY_ID,
        "condition_id": condition_id,
        "observed_at_utc": observed_at,
        "raw_bundle_sha256": raw_bundle["bundle_sha256"],
        "market_contract_sha256": market["contract_sha256"],
        "clob_payload_sha256": observation["payload_sha256"],
        "source_endpoint": endpoint,
        "documentation": {
            "url": DOCUMENTATION_URL,
            "reviewed_on": REVIEW_DATE,
            "applicability": (
                "current_documentation_declared" if apply_current_documentation
                else "unconfirmed_for_observation"
            ),
            "historical_effective_date": None,
        },
        "fields": {
            "taker_order_delay_enabled": {
                "raw_presence": (
                    "absent" if "itode" not in payload else
                    "null" if payload["itode"] is None else "explicit"
                ),
                "value": delay,
                "basis": delay_basis,
            },
            "minimum_order_age_seconds": {
                "raw_presence": (
                    "absent" if "oas" not in payload else
                    "null" if payload["oas"] is None else "explicit"
                ),
                "value": age,
                "basis": "explicit_value" if age is not None else "unknown",
                "operational_scope": "unresolved",
                "omission_default": "undocumented",
            },
        },
        "documented_taker_delay_ms_when_enabled": 250,
        "replay_gate_changed": False,
        "limitations": [
            "Documentation interpretation does not measure matching-engine timing.",
            "Current metadata does not establish historical market settings.",
            "Reward r.moas is separate from top-level oas; no substitution is made.",
            "Missing or null oas remains unknown; its operational scope is unresolved.",
        ],
    }
    result["interpretation_sha256"] = payload_hash(result)
    return result
