"""Validate a separate research declaration and plan calendar boundaries offline.

This is not the v1 directional source contract, a signal adapter, or a runner.
"""

import copy
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .binance_resolution import BINANCE_KLINES_ENDPOINT, DECLARED_RESOLUTION_SOURCE
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .settlement import normalize_settlement


SPEC_SCHEMA = "qcrl.aligned_research_lane_spec.v1"
PLAN_SCHEMA = "qcrl.aligned_research_boundary_plan.v1"


def normalize_research_lane(spec):
    """Validate locked v1 semantics; no silent defaults or legacy-schema conversion."""
    if spec.get("schema_version") != SPEC_SCHEMA:
        raise ContractError("unsupported aligned research lane schema")
    if "declaration_sha256" in spec:
        verify_artifact_hash(spec, "declaration_sha256", "aligned research declaration")
    expected = {
        "source": {
            "venue": "binance_spot", "symbol": "BTCUSDT",
            "endpoint": BINANCE_KLINES_ENDPOINT, "interval": "1m", "price_field": "close",
            "boundary_candle_selection": "open_time_equals_calendar_boundary",
            "timezone": "America/New_York", "local_boundary_time": "12:00:00",
            "window_rule": "consecutive_local_calendar_noons",
            "availability_rule": "after_boundary_candle_end_and_actual_observation",
            "candle_duration_seconds": 60, "missing_candle_policy": "reject_no_substitution",
            "dst_policy": "retain_actual_elapsed_seconds_no_fixed_utc_offset",
        },
        "signal": {
            "entry_model": "candle_streak", "streak_length": 2, "streak_mode": "reverse",
            "filter_model": "none", "direction_rule": "compare_consecutive_boundary_candle_closes",
            "history_tie_policy": "skip_ties_use_most_recent_non_tied_intervals",
            "sizing_policy": "none_direction_only",
        },
        "target": {
            "series_id": "41", "resolution_source": DECLARED_RESOLUTION_SOURCE,
            "tie_settlement": "split_50_50",
            "future_market_compatibility": "verify_explicit_terms_per_market_not_slug_or_series_alone",
        },
        "evaluation": {
            "historical_results_transfer": False, "historical_role": "new_lane_exploration_only",
            "prospective_window": None, "acceptance_gate": None, "parameter_search": "none",
            "execution_or_profitability_claims": False,
        },
        "activation": {
            "orders_authorized": False, "collector_changes_authorized": False,
            "legacy_adapter_compatible": False,
            "requires": [
                "versioned_calendar_close_to_close_source_adapter",
                "observed_availability_and_delayed_decision_intent_contract",
                "explicit_dst_window_binding_policy",
                "hash_verified_boundary_candle_dataset_and_gap_audit",
                "separate_evaluation_window_and_acceptance_gate_before_confirmatory_test",
            ],
        },
    }
    for section, value in expected.items():
        # Canonical JSON equality also distinguishes bool from numeric 0/1.
        if payload_hash(spec.get(section)) != payload_hash(value):
            raise ContractError(f"aligned lane {section} differs from locked v1 declaration")
    if spec.get("status") != "declared_not_executed":
        raise ContractError("aligned lane must remain declared_not_executed")
    if spec.get("lane_id") != "btcusdt-binance-noon-eastern-candle-streak-2-v1":
        raise ContractError("unsupported aligned lane identity")
    try:
        declared = date.fromisoformat(spec["declared_on"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("aligned lane declaration date is required") from exc
    if declared.isoformat() != spec["declared_on"]:
        raise ContractError("aligned lane date must be YYYY-MM-DD")
    authority = spec.get("authority")
    if not isinstance(authority, dict) or not authority.get("market_terms_path"):
        raise ContractError("aligned lane market terms authority is required")
    digest = authority.get("market_terms_file_sha256", "")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ContractError("aligned lane market terms digest is invalid")
    result = copy.deepcopy(spec)
    result.pop("declaration_sha256", None)
    result["declaration_sha256"] = payload_hash(result)
    return result


def load_research_lane(path):
    """Verify the pinned captured terms, not just a declared URL or filename."""
    path = Path(path).resolve()
    spec = normalize_research_lane(json.loads(path.read_text(encoding="utf-8")))
    authority = spec["authority"]
    data = (path.parent / authority["market_terms_path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != authority["market_terms_file_sha256"]:
        raise ContractError("aligned lane market terms file hash mismatch")
    raw = json.loads(data)
    settlement = normalize_settlement(raw)
    gamma = raw["observations"]["gamma_market"]["payload"]
    if (settlement["market_id"] != authority.get("market_id")
            or gamma.get("resolutionSource") != DECLARED_RESOLUTION_SOURCE):
        raise ContractError("aligned lane market terms authority mismatch")
    return spec


def plan_research_boundary(spec, target_end_date):
    """Plan one local calendar window; emit neither a signal nor eligibility."""
    spec = normalize_research_lane(spec)
    try:
        end_date = date.fromisoformat(target_end_date)
        if end_date.isoformat() != target_end_date:
            raise ValueError("noncanonical date")
    except (TypeError, ValueError) as exc:
        raise ContractError("target end date must be YYYY-MM-DD") from exc
    eastern = ZoneInfo(spec["source"]["timezone"])
    def boundary(day):
        return datetime.combine(day, time(12), eastern).astimezone(timezone.utc)
    def text(value):
        return value.isoformat().replace("+00:00", "Z")
    start = boundary(end_date - timedelta(days=1))
    end = boundary(end_date)
    result = {
        "schema_version": PLAN_SCHEMA, "declaration_sha256": spec["declaration_sha256"],
        "target_end_local_date": end_date.isoformat(),
        "target_start_at_utc": text(start), "target_end_at_utc": text(end),
        "target_duration_seconds": int((end - start).total_seconds()),
        "latest_input_boundary_candle_open_at_utc": text(start),
        "latest_input_candle_end_exclusive_at_utc": text(start + timedelta(seconds=60)),
        "decision_not_before_utc": text(start + timedelta(seconds=60)),
        "availability_requires_actual_observation": True,
        "legacy_adapter_compatible": False, "signal_emitted": False,
        "orders_authorized": False,
        "limitations": [
            "Calendar plan only; no source candles acquired or verified.",
            "Earliest decision time is a lower bound, not proof of data availability.",
            "Every target market requires exact explicit-term verification, including DST windows.",
            "Existing source, intent, binding and reconciliation adapters are not activated by this plan.",
        ],
    }
    result["plan_sha256"] = payload_hash(result)
    return result
