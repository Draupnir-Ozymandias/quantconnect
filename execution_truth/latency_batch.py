"""Batch the fixed latency policy across an aligned market-phase cohort."""

from collections import Counter
from decimal import Decimal

from .book_sequence import normalize_book_sequence
from .contracts import ContractError, payload_hash
from .cross_market_phase import analyze_cross_market_phases
from .latency_sensitivity import evaluate_latency_sensitivity
from .phase_stability import PHASES, _phase_summary


LATENCY_BATCH_SCHEMA = "qcrl.latency_phase_batch.v1"
REQUEST_TEMPLATE_SCHEMA = "qcrl.latency_phase_request_template.v1"


def _validate_template(template):
    required = {
        "schema_version", "outcome", "side", "shares", "limit_price",
        "time_in_force", "cash_budget", "decision_time_rule",
    }
    if not isinstance(template, dict) or set(template) != required:
        raise ContractError("latency batch request template fields are invalid")
    if template.get("schema_version") != REQUEST_TEMPLATE_SCHEMA:
        raise ContractError("unsupported latency batch request template schema")
    if template.get("decision_time_rule") != "sequence_capture_started_at_utc":
        raise ContractError("unsupported latency batch decision time rule")


def _request(raw, template):
    normalized = normalize_book_sequence(raw)
    matches = [
        item for item in normalized["market_identity"]["outcomes"]
        if item["label"] == template["outcome"]
    ]
    if len(matches) != 1:
        raise ContractError("latency batch outcome is not unique in market")
    return {
        "schema_version": "qcrl.taker_replay_request.v1",
        "token_id": matches[0]["token_id"],
        "side": template["side"],
        "shares": template["shares"],
        "limit_price": template["limit_price"],
        "time_in_force": template["time_in_force"],
        "cash_budget": template["cash_budget"],
        "hypothetical_at_utc": raw["capture_started_at_utc"],
    }


def _case_summary(market_label, phase, raw, result):
    _, phase_summary = _phase_summary(raw)
    requested = Decimal(phase_summary["requested_interval_seconds"])
    maximum_gap = Decimal(phase_summary["observed_polling_gap_seconds"]["max"])
    rows = []
    for row in result["results"]:
        mechanics = row["mechanics_result"]
        rows.append({
            "assumed_latency_seconds": row["assumed_latency_seconds"],
            "status": row["status"],
            "reason": row["reason"],
            "observation_lag_seconds": row["observation_lag_seconds"],
            "polling_bracket_seconds": row["polling_bracket_seconds"],
            "selected_snapshot_sha256": row["selected_snapshot_sha256"],
            "selected_best_bid": row["selected_best_bid"],
            "selected_best_ask": row["selected_best_ask"],
            "mechanics_status": mechanics["status"] if mechanics else None,
            "mechanics_reasons": mechanics["reasons"] if mechanics else [],
            "mechanics_result_sha256": mechanics["result_sha256"] if mechanics else None,
        })
    return {
        "market_label": market_label,
        "phase": phase,
        "raw_sequence_sha256": result["raw_sequence_sha256"],
        "normalized_sequence_sha256": result["normalized_sequence_sha256"],
        "latency_result_sha256": result["result_sha256"],
        "cadence_warning": maximum_gap > requested * Decimal(2),
        "observed_polling_gap_seconds": phase_summary["observed_polling_gap_seconds"],
        "rows": rows,
    }


def evaluate_latency_phase_batch(markets, request_template, replay_policy, latency_policy):
    """Apply one unchanged request shape and latency grid to every observed phase."""
    _validate_template(request_template)
    cross_market = analyze_cross_market_phases(markets)
    cases = []
    row_statuses = Counter()
    mechanics_statuses = Counter()
    mechanics_reasons = Counter()

    for market_label in sorted(markets):
        for phase in PHASES:
            raw = markets[market_label][phase]
            if raw is None:
                continue
            result = evaluate_latency_sensitivity(
                raw, _request(raw, request_template), replay_policy, latency_policy
            )
            case = _case_summary(market_label, phase, raw, result)
            cases.append(case)
            for row in case["rows"]:
                row_statuses[row["status"]] += 1
                if row["mechanics_status"] is not None:
                    mechanics_statuses[row["mechanics_status"]] += 1
                for reason in row["mechanics_reasons"]:
                    mechanics_reasons[reason] += 1

    result = {
        "schema_version": LATENCY_BATCH_SCHEMA,
        "evidence_role": "cross_market_sequence_observation_sensitivity_only",
        "strategy_eligibility_evaluated": False,
        "cross_market_analysis_sha256": cross_market["analysis_sha256"],
        "coverage": cross_market["coverage"],
        "request_template": dict(request_template),
        "request_template_sha256": payload_hash(request_template),
        "replay_policy": dict(replay_policy),
        "replay_policy_sha256": payload_hash(replay_policy),
        "latency_policy": dict(latency_policy),
        "latency_policy_sha256": payload_hash(latency_policy),
        "summary": {
            "case_count": len(cases),
            "row_count": sum(row_statuses.values()),
            "row_status_counts": dict(sorted(row_statuses.items())),
            "mechanics_status_counts": dict(sorted(mechanics_statuses.items())),
            "mechanics_reason_counts": dict(sorted(mechanics_reasons.items())),
            "cadence_warning_case_count": sum(case["cadence_warning"] for case in cases),
        },
        "cases": cases,
        "limitations": [
            "one fixed latency grid is applied without calibration to observed outcomes",
            "latency values are assumptions rather than measured transport or matching delay",
            "partial markets contribute only observed phases and no phase is imputed",
            "degraded cadence is disclosed and not interpreted as continuous liquidity",
            "snapshot mechanics do not prove queue position, fill, settlement, or profitability",
        ],
    }
    result["batch_sha256"] = payload_hash(result)
    return result
