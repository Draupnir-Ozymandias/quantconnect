"""Contract-driven Polymarket market discovery without slug semantics."""

import json
from datetime import datetime

from .acquisition import RAW_DISCOVERY_SCHEMA
from .contracts import ContractError, payload_hash


DISCOVERY_SPEC_SCHEMA = "qcrl.polymarket_discovery_spec.v1"
DISCOVERY_RESULT_SCHEMA = "qcrl.polymarket_discovery_result.v1"


def _array(value, name):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{name} is not valid JSON") from exc
    if not isinstance(value, list):
        raise ContractError(f"{name} must be an array")
    return value


def _time(value, name):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return parsed


def _payload(observation, name):
    if not isinstance(observation, dict):
        raise ContractError(f"{name} observation is required")
    payload = observation.get("payload")
    if not isinstance(payload, dict):
        raise ContractError(f"{name} payload must be an object")
    if observation.get("payload_sha256") != payload_hash(payload):
        raise ContractError(f"{name} payload hash mismatch")
    return payload


def _exact_bool(mapping, key, expected, name):
    value = mapping.get(key)
    if not isinstance(value, bool) or value is not expected:
        raise ContractError(f"{name}.{key} must be {str(expected).lower()}")


def _integer(value, name):
    if isinstance(value, bool):
        raise ContractError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be an integer") from exc


def _required_text(mapping, key, name):
    value = str(mapping.get(key) or "").strip()
    if not value:
        raise ContractError(f"{name}.{key} is required")
    return value


def normalize_discovery(raw_discovery, spec):
    """Select one market by explicit series, timing, and crypto configuration."""
    supplied_hash = verify_raw_discovery(raw_discovery)
    if spec.get("schema_version") != DISCOVERY_SPEC_SCHEMA:
        raise ContractError("unsupported discovery spec schema")

    series_id = _required_text(spec, "series_id", "spec")
    recurrence = _required_text(spec, "recurrence", "spec")
    expected_asset = _required_text(spec, "asset", "spec")
    expected_duration = _required_text(spec, "duration", "spec")
    expected_resolution = _required_text(spec, "resolution_source", "spec")
    if not isinstance(spec.get("twap_enabled"), bool):
        raise ContractError("spec.twap_enabled must be a boolean")
    expected_lookback = _integer(
        spec.get("twap_lookback_seconds"), "spec.twap_lookback_seconds"
    )
    if expected_lookback < 0:
        raise ContractError("spec.twap_lookback_seconds must be nonnegative")
    expected_outcome_list = _array(spec.get("outcomes"), "spec.outcomes")
    expected_outcomes = {
        str(value).strip().casefold() for value in expected_outcome_list
        if str(value).strip()
    }
    if len(expected_outcome_list) != 2 or len(expected_outcomes) != 2:
        raise ContractError("spec.outcomes must contain two unique labels")

    observations = raw_discovery.get("observations") or {}
    series = _payload(observations.get("series"), "series")
    event = _payload(observations.get("event"), "event")
    if str(raw_discovery.get("series_id_requested") or "") != series_id:
        raise ContractError("requested series does not match specification")
    if str(series.get("id")) != series_id:
        raise ContractError("discovered series does not match specification")
    if str(series.get("recurrence")) != recurrence:
        raise ContractError("series recurrence does not match specification")
    _exact_bool(series, "active", True, "series")
    _exact_bool(series, "closed", False, "series")

    target = _time(raw_discovery.get("target_at_utc"), "target_at_utc")
    start = _time(event.get("startTime"), "event.startTime")
    end = _time(event.get("endDate"), "event.endDate")
    if not start <= target < end:
        raise ContractError("selected event does not contain target time")
    summaries = [
        item for item in series.get("events") or []
        if str(item.get("id") or "") == str(event.get("id") or "")
    ]
    if len(summaries) != 1:
        raise ContractError("selected event is not uniquely listed by the series")
    if (
        summaries[0].get("startTime") != event.get("startTime")
        or summaries[0].get("endDate") != event.get("endDate")
    ):
        raise ContractError("series and event intervals disagree")
    memberships = {str(item.get("id")) for item in event.get("series") or []}
    if series_id not in memberships:
        raise ContractError("event is not a member of the specified series")

    eligible = []
    rejected = []
    for market in event.get("markets") or []:
        reasons = []
        config = market.get("cryptoMarketConfig") or {}
        if str(config.get("asset", "")).casefold() != expected_asset.casefold():
            reasons.append("asset_mismatch")
        if str(config.get("duration")) != expected_duration:
            reasons.append("duration_mismatch")
        if config.get("twapEnabled") is not spec.get("twap_enabled"):
            reasons.append("twap_mode_mismatch")
        try:
            actual_lookback = _integer(
                config.get("twapLookbackSeconds"),
                "market.cryptoMarketConfig.twapLookbackSeconds",
            )
        except ContractError:
            actual_lookback = None
        if actual_lookback != expected_lookback:
            reasons.append("twap_lookback_mismatch")
        if str(market.get("resolutionSource")) != expected_resolution:
            reasons.append("resolution_source_mismatch")
        outcomes = {
            str(value).casefold()
            for value in _array(market.get("outcomes"), "market.outcomes")
        }
        if outcomes != expected_outcomes:
            reasons.append("outcome_mismatch")
        if market.get("eventStartTime") != event.get("startTime"):
            reasons.append("event_start_mismatch")
        if market.get("endDate") != event.get("endDate"):
            reasons.append("event_end_mismatch")
        for key in ["active", "enableOrderBook", "acceptingOrders"]:
            if market.get(key) is not True:
                reasons.append(f"{key}_false_or_missing")
        if market.get("closed") is not False:
            reasons.append("closed_true_or_missing")
        item = {
            "market_id": str(market.get("id") or ""),
            "condition_id": str(market.get("conditionId") or ""),
            "reasons": reasons,
        }
        if reasons or not item["market_id"] or not item["condition_id"]:
            rejected.append(item)
        else:
            eligible.append(item)

    if len(eligible) != 1:
        raise ContractError(
            f"expected one eligible market, found {len(eligible)}"
        )
    result = {
        "schema_version": DISCOVERY_RESULT_SCHEMA,
        "raw_discovery_sha256": supplied_hash,
        "spec_sha256": payload_hash(spec),
        "series_id": series_id,
        "event_id": str(event.get("id") or ""),
        "target_at_utc": raw_discovery["target_at_utc"],
        "event_start_at_utc": event["startTime"],
        "event_end_at_utc": event["endDate"],
        "selected_market_id": eligible[0]["market_id"],
        "selected_condition_id": eligible[0]["condition_id"],
        "rejected_markets": rejected,
    }
    result["result_sha256"] = payload_hash(result)
    return result


def verify_raw_discovery(raw_discovery):
    """Verify a raw discovery envelope without interpreting market meaning."""
    if raw_discovery.get("schema_version") != RAW_DISCOVERY_SCHEMA:
        raise ContractError("unsupported raw discovery schema")
    unhashed = dict(raw_discovery)
    supplied_hash = unhashed.pop("discovery_sha256", None)
    if supplied_hash != payload_hash(unhashed):
        raise ContractError("raw discovery hash mismatch")
    observations = raw_discovery.get("observations") or {}
    _payload(observations.get("series"), "series")
    _payload(observations.get("event"), "event")
    _time(raw_discovery.get("acquired_at_utc"), "acquired_at_utc")
    _time(raw_discovery.get("target_at_utc"), "target_at_utc")
    return supplied_hash
