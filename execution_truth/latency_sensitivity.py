"""Offline sensitivity to assumed arrival time using only observed future books."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .book_sequence import normalize_book_sequence
from .contracts import ContractError, payload_hash
from .taker_replay import replay_taker_buy


POLICY_SCHEMA = "qcrl.latency_sensitivity_policy.v1"
RESULT_SCHEMA = "qcrl.latency_sensitivity_result.v1"
SELECTION_RULE = "first_selected_book_observed_at_or_after_arrival"


def _time(value, name):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def _time_text(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _seconds_text(delta):
    microseconds = (
        delta.days * 86400 * 1000000
        + delta.seconds * 1000000
        + delta.microseconds
    )
    value = Decimal(microseconds) / Decimal(1000000)
    text = format(value, "f")
    return (text.rstrip("0").rstrip(".") if "." in text else text) or "0"


def _validate_policy(policy):
    if not isinstance(policy, dict) or policy.get("schema_version") != POLICY_SCHEMA:
        raise ContractError("unsupported latency sensitivity policy schema")
    if policy.get("selection_rule") != SELECTION_RULE:
        raise ContractError("unsupported latency observation selection rule")
    latencies = policy.get("latencies_seconds")
    if not isinstance(latencies, list) or not 1 <= len(latencies) <= 32:
        raise ContractError("latencies_seconds must contain 1 to 32 values")
    if any(type(value) is not int or not 0 <= value <= 86400 for value in latencies):
        raise ContractError("latencies_seconds must be integers from 0 to 86400")
    if latencies != sorted(set(latencies)):
        raise ContractError("latencies_seconds must be unique and increasing")
    maximum = policy.get("max_observation_lag_seconds")
    if type(maximum) is not int or not 0 <= maximum <= 3600:
        raise ContractError("max_observation_lag_seconds must be an integer from 0 to 3600")
    return latencies, maximum


def evaluate_latency_sensitivity(raw_sequence, request, replay_policy, policy):
    """Select actual post-arrival observations and run guarded snapshot replay."""
    latencies, maximum_lag = _validate_policy(policy)
    normalized = normalize_book_sequence(raw_sequence)
    decision = _time(request.get("hypothetical_at_utc"), "decision timestamp")
    started = _time(normalized["capture_started_at_utc"], "capture start")
    completed = _time(normalized["capture_completed_at_utc"], "capture completion")
    if not started <= decision <= completed:
        raise ContractError("decision timestamp must fall within sequence capture bounds")

    token_id = request.get("token_id")
    if token_id not in {
        outcome["token_id"] for outcome in normalized["market_identity"]["outcomes"]
    }:
        raise ContractError("latency request token does not belong to sequence market")

    observations = []
    for summary, raw_bundle in zip(normalized["samples"], raw_sequence["samples"]):
        book = next(item for item in summary["books"] if item["token_id"] == token_id)
        observations.append((summary, raw_bundle, book, _time(
            book["observed_at_utc"], "selected book observation"
        )))

    # Exercise the existing request/policy validator even when every requested
    # latency falls beyond the finite capture.
    validation_request = dict(request)
    validation_request["hypothetical_at_utc"] = observations[0][2]["observed_at_utc"]
    replay_taker_buy(observations[0][1], validation_request, replay_policy)

    rows = []
    for latency in latencies:
        arrival = decision + timedelta(seconds=latency)
        previous = None
        selected = None
        for candidate in observations:
            if candidate[3] >= arrival:
                selected = candidate
                break
            previous = candidate
        row = {
            "assumed_latency_seconds": latency,
            "hypothetical_arrival_at_utc": _time_text(arrival),
            "preceding_observation_at_utc": (
                previous[2]["observed_at_utc"] if previous else None
            ),
        }
        if selected is None:
            row.update({
                "status": "unobserved",
                "reason": "no_observation_at_or_after_arrival",
                "selected_sample_index": None,
                "selected_book_observed_at_utc": None,
                "observation_lag_seconds": None,
                "polling_bracket_seconds": None,
                "selected_snapshot_sha256": None,
                "selected_best_bid": None,
                "selected_best_ask": None,
                "mechanics_result": None,
            })
        else:
            summary, raw_bundle, book, observed = selected
            lag = observed - arrival
            bracket = observed - previous[3] if previous else None
            row.update({
                "selected_sample_index": summary["index"],
                "selected_book_observed_at_utc": book["observed_at_utc"],
                "observation_lag_seconds": _seconds_text(lag),
                "polling_bracket_seconds": _seconds_text(bracket) if bracket else None,
                "selected_snapshot_sha256": book["snapshot_sha256"],
                "selected_best_bid": book["best_bid"],
                "selected_best_ask": book["best_ask"],
            })
            if lag > timedelta(seconds=maximum_lag):
                row.update({
                    "status": "unobserved",
                    "reason": "observation_lag_exceeds_policy",
                    "mechanics_result": None,
                })
            else:
                replay_request = dict(request)
                replay_request["hypothetical_at_utc"] = book["observed_at_utc"]
                mechanics = replay_taker_buy(raw_bundle, replay_request, replay_policy)
                row.update({
                    "status": "evaluated",
                    "reason": None,
                    "mechanics_result": mechanics,
                })
        rows.append(row)

    result = {
        "schema_version": RESULT_SCHEMA,
        "evidence_role": "sequence_observation_sensitivity_only",
        "strategy_eligibility_evaluated": False,
        "raw_sequence_sha256": raw_sequence["sequence_sha256"],
        "normalized_sequence_sha256": normalized["sequence_sha256"],
        "request": dict(request),
        "request_sha256": payload_hash(request),
        "replay_policy": dict(replay_policy),
        "replay_policy_sha256": payload_hash(replay_policy),
        "latency_policy": dict(policy),
        "latency_policy_sha256": payload_hash(policy),
        "results": rows,
        "limitations": [
            "latency values are assumptions rather than measured transport or matching delay",
            "first post-arrival poll is not the unobserved book at arrival",
            "polling gaps may contain arbitrary book changes",
            "snapshot mechanics do not prove queue position, fill, or settlement",
            "strategy compatibility and profitability are not evaluated",
        ],
    }
    result["result_sha256"] = payload_hash(result)
    return result
