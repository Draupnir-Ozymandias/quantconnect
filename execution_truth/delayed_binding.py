"""Separate delayed diagnostic binding with strict, independently aged sources."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .binance_source import _time, _text
from .bundle import normalize_bundle
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .delayed_signal import materialize_delayed_signal, DECISION_SCHEMA
from .research_lane import normalize_research_lane


POLICY_SCHEMA = "qcrl.delayed_binding_policy.v1"
TERMS_SCHEMA = "qcrl.delayed_market_terms_declaration.v1"
RESULT_SCHEMA = "qcrl.delayed_binding_result.v1"


def bind_delayed_decision(lane, dataset, decision, raw_bundle, terms_declaration,
                          policy, binding_at_utc):
    """Recompute diagnostic intent from evidence; never submit or estimate fills."""
    lane = normalize_research_lane(lane)
    if decision.get("schema_version") != DECISION_SCHEMA:
        raise ContractError("unsupported delayed decision schema")
    verify_artifact_hash(decision, "decision_sha256", "delayed decision")
    target_end = _time(decision["target_end_at_utc"])
    end_date = target_end.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    recomputed = materialize_delayed_signal(lane, dataset, end_date, decision["decision_at_utc"])
    if recomputed != decision:
        raise ContractError("delayed decision does not reproduce from declared source evidence")
    if (policy.get("schema_version") != POLICY_SCHEMA
            or policy.get("evidence_role") != "offline_diagnostic_only"
            or policy.get("orders_authorized") is not False):
        raise ContractError("unsupported delayed diagnostic binding policy")
    limits = {}
    for field in ("max_entry_delay_seconds", "max_intent_age_seconds", "max_metadata_age_seconds",
                  "max_book_age_seconds", "max_exchange_age_seconds", "entry_cutoff_seconds_before_end"):
        value = policy.get(field)
        if type(value) is not int or not 0 <= value <= 86400:
            raise ContractError(f"{field} must be an integer from 0 to 86400")
        limits[field] = value
    if terms_declaration.get("schema_version") != TERMS_SCHEMA:
        raise ContractError("unsupported delayed market terms declaration")
    verify_artifact_hash(terms_declaration, "terms_sha256", "delayed market terms declaration")
    bundle = normalize_bundle(raw_bundle)
    market = bundle["market_contract"]
    observations = raw_bundle["observations"]
    at = _time(binding_at_utc)
    signal_at = _time(decision["decision_at_utc"])
    start = _time(decision["target_start_at_utc"])
    reasons, ages = [], {}
    if policy.get("declaration_sha256") != lane["declaration_sha256"]:
        reasons.append("policy_lane_mismatch")
    expected_terms = {
        "schema_version": TERMS_SCHEMA, "declaration_sha256": lane["declaration_sha256"],
        "market_id": market["identity"]["market_id"],
        "condition_id": market["identity"]["condition_id"],
        "description_sha256": payload_hash(market["terms"]["description"]),
        "event_start_at_utc": market["terms"]["event_start_at_utc"],
        "end_at_utc": market["terms"]["end_at_utc"],
        "resolution_source": lane["target"]["resolution_source"],
        "instrument": "BTCUSDT", "timezone": "America/New_York",
        "candle_interval": "1m", "price_field": "close", "tie_settlement": "split_50_50",
        "basis": "explicit_terms_declared_for_offline_diagnostic",
    }
    supplied = dict(terms_declaration)
    supplied.pop("terms_sha256")
    if supplied != expected_terms:
        reasons.append("explicit_market_terms_declaration_mismatch")
    if market["terms"]["resolution_source"] != lane["target"]["resolution_source"]:
        reasons.append("resolution_source_mismatch")
    if (_time(market["terms"]["event_start_at_utc"]) != start
            or _time(market["terms"]["end_at_utc"]) != target_end):
        reasons.append("target_window_mismatch")
    if not decision["emitted"]:
        reasons.append("diagnostic_signal_not_emitted")
    if at < signal_at:
        reasons.append("binding_precedes_signal_decision")
    if (at - start).total_seconds() > limits["max_entry_delay_seconds"]:
        reasons.append("entry_delay_exceeded")
    if at >= target_end - timedelta(seconds=limits["entry_cutoff_seconds_before_end"]):
        reasons.append("entry_cutoff_reached")
    if (at - signal_at).total_seconds() > limits["max_intent_age_seconds"]:
        reasons.append("intent_stale")

    def check_age(name, observed, limit, local=None):
        age = (at - observed).total_seconds()
        ages[name] = age
        if observed > at:
            reasons.append(name + "_observed_after_binding")
        if observed < signal_at:
            reasons.append(name + "_predates_signal_decision")
        if local is not None and observed > local:
            reasons.append(name + "_timestamp_after_local_observation")
        if age > limit:
            reasons.append(name + "_stale")

    for key in ("gamma_market", "clob_market"):
        check_age(key, _time(observations[key]["observed_at_utc"]), limits["max_metadata_age_seconds"])
    for book in bundle["order_books"]:
        local = _time(book["observed_at_utc"])
        name = "book_" + book["token_id"]
        check_age(name, local, limits["max_book_age_seconds"])
        timestamp = book["exchange_timestamp"]
        if not timestamp.isascii() or not timestamp.isdigit() or len(timestamp) > 15:
            raise ContractError("exchange timestamp must be integer epoch milliseconds")
        try:
            exchange = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=int(timestamp))
        except OverflowError as exc:
            raise ContractError("exchange timestamp out of range") from exc
        check_age(name + "_exchange", exchange, limits["max_exchange_age_seconds"], local)
    for field, expected in (("active", True), ("closed", False), ("order_book_enabled", True),
                            ("accepting_orders", True), ("fees_enabled", True)):
        if market["state"][field] is not expected:
            reasons.append("market_state_" + field + "_unsupported")
    constraints = market["constraints"]
    for field in ("taker_order_delay_enabled", "minimum_order_age_seconds"):
        if constraints[field] is None:
            reasons.append("unknown_" + field)
    if constraints["taker_order_delay_enabled"] is True:
        reasons.append("enabled_taker_delay_requires_temporal_execution_model")
    if constraints["minimum_order_age_seconds"] not in (None, 0):
        reasons.append("nonzero_order_age_requires_execution_model")
    intent = decision["intent"]
    matches = [o for o in market["outcomes"] if intent and o["label"].casefold() == intent["direction"]]
    if intent and len(matches) != 1:
        reasons.append("direction_outcome_unmapped")
    result = {
        "schema_version": RESULT_SCHEMA, "evidence_role": "offline_delayed_binding_diagnostic_only",
        "declaration_sha256": lane["declaration_sha256"], "decision_sha256": decision["decision_sha256"],
        "raw_dataset_sha256": dataset["dataset_sha256"], "raw_bundle_sha256": raw_bundle["bundle_sha256"],
        "market_contract_sha256": market["contract_sha256"],
        "terms_declaration_sha256": terms_declaration["terms_sha256"], "policy_sha256": payload_hash(policy),
        "binding_at_utc": _text(at), "binding_checks_passed": not reasons, "rejection_reasons": reasons,
        "source_ages_seconds": ages,
        "selected_token_id": matches[0]["token_id"] if len(matches) == 1 else None,
        "constraint_revalidation_required": True, "orders_authorized": False,
        "limitations": [
            "Passing diagnostic checks does not authorize execution or establish historical availability.",
            "Terms declaration must be deliberately checked against exact description, not inferred from slug.",
            "Limits are engineering policy, not exchange defaults or optimized strategy parameters.",
            "Freshness is as-of binding only; re-acquisition and revalidation are required before any later use.",
            "No acceptance, resting-order survival, fill, fee or profitability evidence is produced.",
        ],
    }
    result["result_sha256"] = payload_hash(result)
    return result
