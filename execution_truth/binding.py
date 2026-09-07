"""Lookahead-safe binding of a directional signal to one market contract."""

from datetime import datetime, timedelta, timezone

from .contracts import (
    ContractError,
    MARKET_CONTRACT_SCHEMA,
    payload_hash,
    verify_artifact_hash,
)


SIGNAL_INTENT_SCHEMA = "qcrl.directional_signal_intent.v1"
BINDING_POLICY_SCHEMA = "qcrl.polymarket_binding_policy.v1"
BINDING_RESULT_SCHEMA = "qcrl.polymarket_binding_result.v1"


def _time(value, name):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _text(value):
    return value.isoformat().replace("+00:00", "Z")


def _required_text(mapping, key, name):
    value = str(mapping.get(key) or "").strip()
    if not value:
        raise ContractError(f"{name}.{key} is required")
    return value


def bind_signal_to_market(signal, market_contract, policy, decision_at_utc):
    """Return an auditable eligibility result; expected rejection is data."""
    if signal.get("schema_version") != SIGNAL_INTENT_SCHEMA:
        raise ContractError("unsupported signal intent schema")
    if market_contract.get("schema_version") != MARKET_CONTRACT_SCHEMA:
        raise ContractError("unsupported market contract schema")
    verify_artifact_hash(
        market_contract, "contract_sha256", "market contract"
    )
    if policy.get("schema_version") != BINDING_POLICY_SCHEMA:
        raise ContractError("unsupported binding policy schema")

    for field in ["signal_id", "asset", "source_timeframe", "methodology_version"]:
        _required_text(signal, field, "signal")
    policy_asset = _required_text(policy, "asset", "policy")
    policy_resolution = _required_text(
        policy, "resolution_source", "policy"
    )

    direction = str(signal.get("direction") or "").casefold()
    if direction not in {"up", "down"}:
        raise ContractError("signal direction must be up or down")
    available = _time(signal.get("available_at_utc"), "signal.available_at_utc")
    target_start = _time(
        signal.get("target_start_at_utc"), "signal.target_start_at_utc"
    )
    target_end = _time(
        signal.get("target_end_at_utc"), "signal.target_end_at_utc"
    )
    if not available <= target_start < target_end:
        raise ContractError("signal timing must be available by its target start")

    terms = market_contract["terms"]
    event_start = _time(terms["event_start_at_utc"], "market.event_start_at_utc")
    event_end = _time(terms["end_at_utc"], "market.end_at_utc")
    observed = _time(
        market_contract["observed_at_utc"], "market.observed_at_utc"
    )
    decision = _time(decision_at_utc, "decision_at_utc")
    if decision < observed:
        raise ContractError("decision cannot precede market observation")

    try:
        cutoff_seconds = int(policy["entry_cutoff_seconds_before_end"])
        max_delay_seconds = int(policy["max_entry_delay_seconds"])
        expected_duration = int(policy["duration_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("binding policy timing values must be integers") from exc
    if (
        isinstance(policy.get("entry_cutoff_seconds_before_end"), bool)
        or isinstance(policy.get("max_entry_delay_seconds"), bool)
        or isinstance(policy.get("duration_seconds"), bool)
    ):
        raise ContractError("binding policy timing values must be integers")
    if cutoff_seconds < 0 or max_delay_seconds < 0 or expected_duration <= 0:
        raise ContractError(
            "binding policy delays must be nonnegative and duration positive"
        )
    cutoff = event_end - timedelta(seconds=cutoff_seconds)
    latest_start_entry = event_start + timedelta(seconds=max_delay_seconds)

    reasons = []
    if str(signal.get("asset", "")).casefold() != str(
        policy_asset
    ).casefold():
        reasons.append("signal_asset_mismatch")
    if str(terms["resolution_source"]) != policy_resolution:
        reasons.append("resolution_source_mismatch")
    if target_start != event_start or target_end != event_end:
        reasons.append("target_window_mismatch")
    if int((event_end - event_start).total_seconds()) != expected_duration:
        reasons.append("market_duration_mismatch")
    if observed < available:
        reasons.append("market_observed_before_signal_available")
    if decision < event_start:
        reasons.append("decision_before_market_start")
    if decision > latest_start_entry:
        reasons.append("entry_delay_exceeded")
    if decision >= cutoff:
        reasons.append("entry_cutoff_reached")

    state = market_contract["state"]
    if state["active"] is not True:
        reasons.append("market_inactive")
    if state["closed"] is not False:
        reasons.append("market_closed")
    if state["order_book_enabled"] is not True:
        reasons.append("order_book_disabled")
    if state["accepting_orders"] is not True:
        reasons.append("orders_not_accepted")

    matching = [
        outcome for outcome in market_contract["outcomes"]
        if outcome["label"].casefold() == direction
    ]
    if len(matching) != 1:
        reasons.append("direction_outcome_unmapped")

    result = {
        "schema_version": BINDING_RESULT_SCHEMA,
        "signal_sha256": payload_hash(signal),
        "market_contract_sha256": market_contract["contract_sha256"],
        "policy_sha256": payload_hash(policy),
        "decision_at_utc": _text(decision),
        "eligible": not reasons,
        "rejection_reasons": reasons,
        "selected_outcome": matching[0]["label"] if len(matching) == 1 else None,
        "selected_token_id": (
            matching[0]["token_id"] if len(matching) == 1 else None
        ),
        "entry_cutoff_at_utc": _text(cutoff),
        "latest_start_entry_at_utc": _text(latest_start_entry),
    }
    result["result_sha256"] = payload_hash(result)
    return result
