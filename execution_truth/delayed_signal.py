"""Separate offline diagnostic signals with honest post-boundary decision times."""

from .binance_source import adapt_boundary_dataset, _time, _text
from .contracts import ContractError, payload_hash
from .research_lane import normalize_research_lane, plan_research_boundary


DECISION_SCHEMA = "qcrl.delayed_directional_signal_decision.v1"
INTENT_SCHEMA = "qcrl.delayed_directional_signal_intent.v1"


def materialize_delayed_signal(lane, raw_dataset, target_end_date, decision_at_utc):
    """Compute only declared length-2 reversal; never bind or authorize execution.

    Input must end at the target's start boundary. Historical retrieval times
    are retained, not replaced by assumed candle-finalization availability.
    """
    lane = normalize_research_lane(lane)
    plan = plan_research_boundary(lane, target_end_date)
    audit = adapt_boundary_dataset(lane, raw_dataset)
    start = _time(plan["target_start_at_utc"])
    end = _time(plan["target_end_at_utc"])
    decision = _time(decision_at_utc)
    boundaries = audit["boundary_candles"]
    if not boundaries or _time(boundaries[-1]["boundary_at_utc"]) != start:
        raise ContractError("signal dataset must end exactly at target start boundary")
    records = audit["source_records"]
    # All provided history, including ties, must actually be observed by decision.
    available = max(_time(c["observed_at_utc"]) for c in boundaries)
    reasons = []
    if not audit["complete"]:
        reasons.append("missing_exact_boundary_history")
    if decision < _time(plan["decision_not_before_utc"]):
        reasons.append("decision_before_latest_input_completion")
    if available > decision:
        reasons.append("inputs_not_observed_by_decision")
    if decision >= end:
        reasons.append("target_window_expired")
    recent = [r for r in records if r["direction"] != "tie"][-2:]
    if len(recent) < 2:
        reasons.append("insufficient_non_tied_history")
    elif recent[0]["direction"] != recent[1]["direction"]:
        reasons.append("streak_not_present")
    intent = None
    if not reasons:
        direction = "down" if recent[-1]["direction"] == "up" else "up"
        intent = {
            "schema_version": INTENT_SCHEMA,
            "evidence_role": "offline_delayed_decision_diagnostic_only",
            "input_evidence_class": audit["input_evidence_class"],
            "asset": "btc", "instrument": "BTCUSDT", "venue": "binance_spot",
            "declaration_sha256": lane["declaration_sha256"],
            "raw_dataset_sha256": raw_dataset["dataset_sha256"],
            "source_audit_sha256": audit["audit_sha256"],
            "selected_source_record_sha256": [r["record_sha256"] for r in recent],
            "available_at_utc": _text(available), "decision_at_utc": _text(decision),
            "target_start_at_utc": _text(start), "target_end_at_utc": _text(end),
            "target_duration_seconds": plan["target_duration_seconds"],
            "decision_delay_seconds": (decision - start).total_seconds(),
            "direction": direction, "entry_model": "candle_streak",
            "streak_length": 2, "streak_mode": "reverse", "filter_model": "none",
            "original_boundary_availability_proven": False,
            "legacy_binding_compatible": False, "orders_authorized": False,
        }
        intent["intent_sha256"] = payload_hash(intent)
    result = {
        "schema_version": DECISION_SCHEMA,
        "declaration_sha256": lane["declaration_sha256"],
        "raw_dataset_sha256": raw_dataset["dataset_sha256"],
        "source_audit_sha256": audit["audit_sha256"], "boundary_plan_sha256": plan["plan_sha256"],
        "decision_at_utc": _text(decision), "available_at_utc": _text(available),
        "target_start_at_utc": _text(start), "target_end_at_utc": _text(end),
        "emitted": intent is not None, "non_emission_reasons": reasons, "intent": intent,
        "orders_authorized": False,
        "limitations": [
            "This diagnostic does not establish historical live signal availability.",
            "No maximum entry-delay trading policy or market binding is approved.",
            "Emission is not order eligibility, fill evidence, or a campaign verdict.",
            "Legacy boundary-time intent and binding remain incompatible and unchanged.",
            "Unknown execution fields, including oas, remain independent restrictions.",
        ],
    }
    result["decision_sha256"] = payload_hash(result)
    return result
