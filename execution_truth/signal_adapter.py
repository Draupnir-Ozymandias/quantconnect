"""Explicit QCRL source contract and boundary-time signal materialization."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from .contracts import ContractError, payload_hash, verify_artifact_hash


SOURCE_CONTRACT_SCHEMA = "qcrl.directional_source_contract.v1"
SOURCE_BAR_SCHEMA = "qcrl.directional_source_bar.v1"
CANDLE_STREAK_SPEC_SCHEMA = "qcrl.candle_streak_signal_spec.v1"
SIGNAL_DECISION_SCHEMA = "qcrl.directional_signal_decision.v1"
SIGNAL_INTENT_SCHEMA = "qcrl.directional_signal_intent.v2"


def _text(mapping, key, context):
    value = str(mapping.get(key) or "").strip()
    if not value:
        raise ContractError(f"{context}.{key} is required")
    return value


def _integer(mapping, key, context, *, positive=False):
    value = mapping.get(key)
    if isinstance(value, bool):
        raise ContractError(f"{context}.{key} must be an integer")
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{context}.{key} must be an integer") from exc
    if positive and value <= 0:
        raise ContractError(f"{context}.{key} must be positive")
    return value


def _time(value, name):
    if not isinstance(value, str):
        raise ContractError(f"{name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _time_text(value):
    return value.isoformat().replace("+00:00", "Z")


def _price(value, name):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{name} must be decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ContractError(f"{name} must be finite and positive")
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def normalize_source_contract(spec):
    """Normalize the declared feed and exact bar boundary semantics."""
    if spec.get("schema_version") != SOURCE_CONTRACT_SCHEMA:
        raise ContractError("unsupported directional source contract schema")
    duration = _integer(spec, "bar_duration_seconds", "source", positive=True)
    offset = _integer(spec, "bar_anchor_offset_seconds", "source")
    if offset < 0 or offset >= duration:
        raise ContractError("source bar anchor offset must be within duration")
    if _text(spec, "bar_anchor_timezone", "source") != "UTC":
        raise ContractError("source bar anchor timezone must be UTC")
    if _text(spec, "tie_policy", "source") != "skip":
        raise ContractError("source tie policy must be skip")
    normalized = {
        "schema_version": SOURCE_CONTRACT_SCHEMA,
        "asset": _text(spec, "asset", "source").casefold(),
        "instrument": _text(spec, "instrument", "source"),
        "venue": _text(spec, "venue", "source").casefold(),
        "input_resolution": _text(spec, "input_resolution", "source"),
        "bar_timeframe": _text(spec, "bar_timeframe", "source"),
        "bar_duration_seconds": duration,
        "bar_anchor_timezone": "UTC",
        "bar_anchor_offset_seconds": offset,
        "price_semantics": _text(spec, "price_semantics", "source"),
        "tie_policy": "skip",
        "anchor_authority": _text(spec, "anchor_authority", "source"),
    }
    normalized["contract_sha256"] = payload_hash(normalized)
    return normalized


def normalize_source_bar(raw_bar, source_contract):
    """Bind one completed OHLC direction bar to its source contract."""
    verify_artifact_hash(source_contract, "contract_sha256", "source contract")
    if raw_bar.get("schema_version") != SOURCE_BAR_SCHEMA:
        raise ContractError("unsupported directional source bar schema")
    if raw_bar.get("source_contract_sha256") != source_contract["contract_sha256"]:
        raise ContractError("source bar contract hash mismatch")
    start = _time(raw_bar.get("start_at_utc"), "source_bar.start_at_utc")
    end = _time(raw_bar.get("end_at_utc"), "source_bar.end_at_utc")
    available = _time(
        raw_bar.get("available_at_utc"), "source_bar.available_at_utc"
    )
    duration = source_contract["bar_duration_seconds"]
    if end - start != timedelta(seconds=duration):
        raise ContractError("source bar duration mismatch")
    epoch_seconds = int(start.timestamp())
    if epoch_seconds % duration != source_contract["bar_anchor_offset_seconds"]:
        raise ContractError("source bar is not aligned to declared anchor")
    if available < end:
        raise ContractError("source bar cannot be available before it ends")
    normalized = {
        "schema_version": SOURCE_BAR_SCHEMA,
        "source_contract_sha256": source_contract["contract_sha256"],
        "start_at_utc": _time_text(start),
        "end_at_utc": _time_text(end),
        "available_at_utc": _time_text(available),
        "open": _price(raw_bar.get("open"), "source_bar.open"),
        "close": _price(raw_bar.get("close"), "source_bar.close"),
    }
    normalized["bar_sha256"] = payload_hash(normalized)
    return normalized


def _normalize_signal_spec(spec, source_contract):
    if spec.get("schema_version") != CANDLE_STREAK_SPEC_SCHEMA:
        raise ContractError("unsupported candle streak signal spec schema")
    if _text(spec, "entry_model", "signal_spec") != "candle_streak":
        raise ContractError("signal spec entry model must be candle_streak")
    mode = _text(spec, "streak_mode", "signal_spec")
    if mode not in {"follow", "reverse"}:
        raise ContractError("signal spec streak mode must be follow or reverse")
    if _text(spec, "filter_model", "signal_spec") != "none":
        raise ContractError("boundary adapter supports only the unfiltered candidate")
    duration = _integer(
        spec, "target_duration_seconds", "signal_spec", positive=True
    )
    if duration != source_contract["bar_duration_seconds"]:
        raise ContractError("signal target duration must match source bar duration")
    normalized = {
        "schema_version": CANDLE_STREAK_SPEC_SCHEMA,
        "entry_model": "candle_streak",
        "streak_length": _integer(
            spec, "streak_length", "signal_spec", positive=True
        ),
        "streak_mode": mode,
        "filter_model": "none",
        "target_duration_seconds": duration,
        "methodology_version": _text(
            spec, "methodology_version", "signal_spec"
        ),
    }
    normalized["spec_sha256"] = payload_hash(normalized)
    return normalized


def materialize_boundary_signal(source_contract, signal_spec, raw_bars):
    """Emit the next-window intent using only bars completed by the boundary."""
    verify_artifact_hash(source_contract, "contract_sha256", "source contract")
    spec = _normalize_signal_spec(signal_spec, source_contract)
    if not isinstance(raw_bars, list) or not raw_bars:
        raise ContractError("completed source bars are required")
    bars = [normalize_source_bar(bar, source_contract) for bar in raw_bars]
    for previous, current in zip(bars, bars[1:]):
        if previous["end_at_utc"] != current["start_at_utc"]:
            raise ContractError("source bars must be ordered and contiguous")

    target_start = _time(bars[-1]["end_at_utc"], "last_bar.end_at_utc")
    target_end = target_start + timedelta(
        seconds=spec["target_duration_seconds"]
    )
    available = max(
        _time(bar["available_at_utc"], "source_bar.available_at_utc")
        for bar in bars
    )
    directions = []
    for bar in bars:
        open_price = Decimal(bar["open"])
        close_price = Decimal(bar["close"])
        if close_price > open_price:
            directions.append("up")
        elif close_price < open_price:
            directions.append("down")

    streak_length = spec["streak_length"]
    recent = directions[-streak_length:]
    direction = None
    reason = None
    if available > target_start:
        reason = "source_bar_not_available_at_boundary"
    elif len(recent) < streak_length:
        reason = "insufficient_direction_history"
    elif len(set(recent)) != 1:
        reason = "streak_not_present"
    elif spec["streak_mode"] == "follow":
        direction = recent[0]
    else:
        direction = "down" if recent[0] == "up" else "up"

    intent = None
    if direction is not None:
        identity = {
            "source_contract_sha256": source_contract["contract_sha256"],
            "signal_spec_sha256": spec["spec_sha256"],
            "source_bar_sha256": [bar["bar_sha256"] for bar in bars],
            "target_start_at_utc": _time_text(target_start),
            "target_end_at_utc": _time_text(target_end),
            "direction": direction,
        }
        intent = {
            "schema_version": SIGNAL_INTENT_SCHEMA,
            "signal_id": f"qcrl-{payload_hash(identity)[:20]}",
            "asset": source_contract["asset"],
            "source_timeframe": source_contract["bar_timeframe"],
            "direction": direction,
            "available_at_utc": _time_text(available),
            "target_start_at_utc": _time_text(target_start),
            "target_end_at_utc": _time_text(target_end),
            "methodology_version": spec["methodology_version"],
            "source_contract_sha256": source_contract["contract_sha256"],
            "signal_spec_sha256": spec["spec_sha256"],
        }

    decision = {
        "schema_version": SIGNAL_DECISION_SCHEMA,
        "source_contract_sha256": source_contract["contract_sha256"],
        "signal_spec_sha256": spec["spec_sha256"],
        "source_bar_sha256": [bar["bar_sha256"] for bar in bars],
        "boundary_at_utc": _time_text(target_start),
        "emitted": intent is not None,
        "non_emission_reason": reason,
        "intent": intent,
    }
    decision["decision_sha256"] = payload_hash(decision)
    return decision
