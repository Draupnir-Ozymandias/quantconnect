"""Offline, close-to-close source records for the separate aligned lane.

No acquisition, signal emission, backdating, interpolation, or legacy intent.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from .binance_resolution import _normalize_observation
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .research_lane import normalize_research_lane


DATASET_SCHEMA = "qcrl.binance_boundary_dataset.v1"
RECORD_SCHEMA = "qcrl.binance_calendar_source_record.v1"
RESULT_SCHEMA = "qcrl.binance_calendar_source_audit.v1"


def _date(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("noncanonical date")
        return parsed
    except (TypeError, ValueError) as exc:
        raise ContractError("boundary date must be YYYY-MM-DD") from exc


def _time(value):
    if not isinstance(value, str):
        raise ContractError("boundary observation time must be ISO-8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("invalid boundary observation time") from exc
    if parsed.tzinfo is None:
        raise ContractError("boundary observation time must include timezone")
    return parsed.astimezone(timezone.utc)


def _text(value):
    return value.isoformat().replace("+00:00", "Z")


def adapt_boundary_dataset(lane, raw):
    """Verify exact candles, audit gaps, and derive only adjacent calendar pairs.

    The declared range is inclusive of its boundary dates. Missing dates are
    explicit audit data, never replaced. Only complete, adjacent pairs produce
    source records. These records do not claim original-time availability.
    """
    lane = normalize_research_lane(lane)
    if raw.get("schema_version") != DATASET_SCHEMA:
        raise ContractError("unsupported Binance boundary dataset schema")
    verify_artifact_hash(raw, "dataset_sha256", "Binance boundary dataset")
    if raw.get("declaration_sha256") != lane["declaration_sha256"]:
        raise ContractError("boundary dataset declaration hash mismatch")
    if raw.get("evidence_role") != "historical_retrieval":
        raise ContractError("boundary dataset supports historical_retrieval only")
    if raw.get("evidence_class") not in {"synthetic_fixture", "captured_public_observation"}:
        raise ContractError("boundary dataset requires explicit evidence class")
    first = _date(raw.get("first_boundary_local_date"))
    last = _date(raw.get("last_boundary_local_date"))
    count = (last - first).days + 1
    if not 2 <= count <= 10000:
        raise ContractError("boundary dataset must span 2 to 10000 boundary dates")
    observations = raw.get("observations")
    if not isinstance(observations, list) or len(observations) > count:
        raise ContractError("boundary observations must be a bounded list")
    eastern = ZoneInfo(lane["source"]["timezone"])
    by_date = {}
    previous = None
    for entry in observations:
        if not isinstance(entry, dict):
            raise ContractError("boundary entry must be an object")
        day = _date(entry.get("boundary_local_date"))
        if day < first or day > last:
            raise ContractError("boundary observation outside declared range")
        if day in by_date:
            raise ContractError("duplicate boundary observation date")
        if previous is not None and day <= previous:
            raise ContractError("boundary observations must be calendar ordered")
        previous = day
        boundary = datetime(day.year, day.month, day.day, 12, tzinfo=eastern).astimezone(timezone.utc)
        observation = entry.get("observation")
        if not isinstance(observation, dict):
            raise ContractError("boundary candle observation is required")
        candle, _ = _normalize_observation(
            {"observations": {"boundary": observation}}, "boundary", boundary
        )
        # REST close time is inclusive; finalized availability starts after it.
        end_exclusive = boundary + timedelta(seconds=60)
        observed = _time(observation["observed_at_utc"])
        if observed < end_exclusive:
            raise ContractError("boundary candle observed before minute completion")
        by_date[day] = {
            "boundary_local_date": day.isoformat(), "boundary_at_utc": _text(boundary),
            "candle_end_exclusive_at_utc": _text(end_exclusive),
            "observed_at_utc": _text(observed), "close": candle["close"],
            "payload_sha256": candle["payload_sha256"],
            "observation_sha256": payload_hash(observation),
        }
    expected = [first + timedelta(days=index) for index in range(count)]
    missing = [day.isoformat() for day in expected if day not in by_date]
    records = []
    unavailable_pairs = []
    for start_day, end_day in zip(expected, expected[1:]):
        if start_day not in by_date or end_day not in by_date:
            unavailable_pairs.append({"start_local_date": start_day.isoformat(),
                                      "end_local_date": end_day.isoformat(),
                                      "reason": "missing_exact_boundary_candle"})
            continue
        start, end = by_date[start_day], by_date[end_day]
        first_close, last_close = Decimal(start["close"]), Decimal(end["close"])
        direction = "up" if last_close > first_close else "down" if last_close < first_close else "tie"
        record = {
            "schema_version": RECORD_SCHEMA, "declaration_sha256": lane["declaration_sha256"],
            "raw_dataset_sha256": raw["dataset_sha256"],
            "start_local_date": start_day.isoformat(), "end_local_date": end_day.isoformat(),
            "start_at_utc": start["boundary_at_utc"], "end_at_utc": end["boundary_at_utc"],
            "duration_seconds": int((_time(end["boundary_at_utc"]) - _time(start["boundary_at_utc"])).total_seconds()),
            "start_close": start["close"], "end_close": end["close"], "direction": direction,
            "market_comparison_outcome": {"up": "Up", "down": "Down", "tie": "Split"}[direction],
            "input_candle_end_exclusive_at_utc": end["candle_end_exclusive_at_utc"],
            "observed_available_at_utc": _text(max(_time(start["observed_at_utc"]), _time(end["observed_at_utc"]))),
            "boundary_observation_sha256": [start["observation_sha256"], end["observation_sha256"]],
            "original_boundary_availability_proven": False,
        }
        record["record_sha256"] = payload_hash(record)
        records.append(record)
    directions = {value: sum(r["direction"] == value for r in records) for value in ("up", "down", "tie")}
    result = {
        "schema_version": RESULT_SCHEMA, "declaration_sha256": lane["declaration_sha256"],
        "raw_dataset_sha256": raw["dataset_sha256"], "evidence_role": "historical_source_exploration_only",
        "input_evidence_class": raw["evidence_class"],
        "first_boundary_local_date": first.isoformat(), "last_boundary_local_date": last.isoformat(),
        "expected_boundary_count": count, "observed_boundary_count": len(by_date),
        "missing_boundary_local_dates": missing, "complete": not missing,
        "boundary_candles": list(by_date.values()), "source_records": records,
        "unavailable_source_pairs": unavailable_pairs, "direction_counts": directions,
        "signal_emitted": False, "orders_authorized": False,
        "limitations": [
            "Later retrieval does not establish what was observable at the historical boundary.",
            "Adjacent complete pairs are source evidence only; gaps cannot be crossed by a signal consumer.",
            "Equal closes retain split settlement separately from signal-history tie skipping.",
            "No market binding, campaign verdict, fill, fee or profitability estimate is produced.",
        ],
    }
    result["audit_sha256"] = payload_hash(result)
    return result
