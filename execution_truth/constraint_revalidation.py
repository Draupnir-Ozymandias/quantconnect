"""Fail-closed, two-observation guard for offline taker mechanics replay."""

from .bundle import normalize_bundle
from .contracts import ContractError, payload_hash
from .taker_replay import replay_taker_buy, _time


POLICY_SCHEMA = "qcrl.constraint_revalidation_policy.v1"
RESULT_SCHEMA = "qcrl.constraint_revalidated_replay.v1"


def replay_taker_buy_revalidated(origin_bundle, current_bundle, request,
                                 replay_policy, revalidation_policy):
    """Revalidate an unchanged request; never reprice, resize, or submit it.

    The origin is the observation against which the request was prepared.
    A passing guard permits only the existing snapshot mechanics calculation,
    not execution. Neither documentation sidecars nor inferred values are used.
    """
    if (revalidation_policy.get("schema_version") != POLICY_SCHEMA
            or revalidation_policy.get("mode") != "reject_any_observed_change"):
        raise ContractError("unsupported constraint revalidation policy")
    origin = normalize_bundle(origin_bundle)["market_contract"]
    current = normalize_bundle(current_bundle)["market_contract"]
    # Validate the request and existing policy against its declared origin.
    # Discard this estimate: it is never a fallback for rejected revalidation.
    replay_taker_buy(origin_bundle, request, replay_policy)
    origin_at = _time(origin["observed_at_utc"])
    current_at = _time(current["observed_at_utc"])
    if current_at < origin_at:
        raise ContractError("current metadata observation precedes request origin")
    at = _time(request["hypothetical_at_utc"])
    reasons, differences = [], []
    for section in ("identity", "outcomes", "terms", "state", "constraints"):
        if origin[section] != current[section]:
            differences.append({"section": section,
                                "origin": origin[section], "current": current[section]})
            reasons.append(section + "_changed_since_origin")
    if current_at > at:
        reasons.append("current_metadata_observed_after_replay_time")
    if current_at == origin_at and origin["contract_sha256"] != current["contract_sha256"]:
        reasons.append("conflicting_metadata_at_same_timestamp")
    tick_changed = (origin["constraints"]["minimum_tick_size"]
                    != current["constraints"]["minimum_tick_size"])
    if tick_changed:
        reasons.append("tick_grid_changed_requires_new_request")
    result = {
        "schema_version": RESULT_SCHEMA,
        "evidence_role": "two_observation_snapshot_mechanics_only",
        "origin_raw_bundle_sha256": origin_bundle["bundle_sha256"],
        "current_raw_bundle_sha256": current_bundle["bundle_sha256"],
        "origin_market_contract_sha256": origin["contract_sha256"],
        "current_market_contract_sha256": current["contract_sha256"],
        "origin_observed_at_utc": origin["observed_at_utc"],
        "current_observed_at_utc": current["observed_at_utc"],
        "request_sha256": payload_hash(request),
        "replay_policy_sha256": payload_hash(replay_policy),
        "revalidation_policy": dict(revalidation_policy),
        "revalidation_policy_sha256": payload_hash(revalidation_policy),
        "metadata_revalidation_passed": not reasons,
        "rejection_reasons": reasons,
        "observed_differences": differences,
        "request_modified": False,
        "replay": None if reasons else replay_taker_buy(current_bundle, request, replay_policy),
        "limitations": [
            "Revalidation is offline and cannot establish current exchange settings at submission.",
            "Two equal observations do not exclude an intervening change and reversal.",
            "A passing guard does not override snapshot replay rejection or authorize execution.",
            "An observed change requires a new request, not automatic rounding or resizing.",
            "No actual order acceptance, resting-order survival, or fill evidence is produced.",
        ],
    }
    result["result_sha256"] = payload_hash(result)
    return result
