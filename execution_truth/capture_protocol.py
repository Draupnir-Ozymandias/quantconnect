"""Predeclared early/middle/late book-sequence capture orchestration."""

import json
import os
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .acquisition import AcquisitionError, PublicPolymarketAcquirer, utc_now
from .book_sequence import normalize_book_sequence, validate_sequence_limits
from .bundle import normalize_bundle, store_raw_book_sequence, store_raw_slug_resolution
from .contracts import ContractError, payload_hash, verify_artifact_hash


PROTOCOL_SCHEMA = "qcrl.book_sequence_capture_protocol.v1"
STATE_SCHEMA = "qcrl.book_sequence_capture_state.v1"
PHASES = ("early", "middle", "late")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")


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


def validate_capture_protocol(protocol):
    """Validate and return a defensive copy of a locked capture declaration."""
    if not isinstance(protocol, dict) or protocol.get("schema_version") != PROTOCOL_SCHEMA:
        raise ContractError("unsupported book-sequence capture protocol schema")
    protocol_id = protocol.get("protocol_id")
    if not isinstance(protocol_id, str) or not _ID.fullmatch(protocol_id):
        raise ContractError("protocol_id must be a lowercase kebab-case identifier")
    if not str(protocol.get("evidence_role") or "").strip():
        raise ContractError("capture protocol evidence_role is required")
    limitations = protocol.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        raise ContractError("capture protocol limitations must be nonempty strings")

    locked = _time(protocol.get("locked_at_utc"), "protocol lock")
    market = protocol.get("market")
    if not isinstance(market, dict):
        raise ContractError("capture protocol market declaration is required")
    slug = market.get("slug")
    if (not isinstance(slug, str) or not slug or len(slug) > 120
            or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in slug)):
        raise ContractError("capture protocol market slug is invalid")
    if market.get("reference_kind") not in {"event", "market"}:
        raise ContractError("capture protocol reference_kind must be event or market")
    source = market.get("resolution_source")
    if not isinstance(source, str) or not source.startswith("https://"):
        raise ContractError("capture protocol resolution_source must be an HTTPS URL")
    start = _time(market.get("event_start_at_utc"), "market event start")
    end = _time(market.get("event_end_at_utc"), "market event end")
    if end <= start:
        raise ContractError("capture protocol market end must follow start")

    captures = protocol.get("captures")
    if not isinstance(captures, list) or len(captures) != len(PHASES):
        raise ContractError("capture protocol must declare early, middle, and late once")
    seen = set()
    scheduled = []
    duration = end - start
    for capture in captures:
        if not isinstance(capture, dict):
            raise ContractError("capture declaration must be an object")
        capture_id = capture.get("capture_id")
        phase = capture.get("phase")
        if not isinstance(capture_id, str) or not _ID.fullmatch(capture_id):
            raise ContractError("capture_id must be a lowercase kebab-case identifier")
        if capture_id in seen:
            raise ContractError("capture_id values must be unique")
        seen.add(capture_id)
        if phase not in PHASES:
            raise ContractError("capture phase must be early, middle, or late")
        try:
            validate_sequence_limits(
                capture.get("samples"), capture.get("interval_seconds")
            )
        except AcquisitionError as exc:
            raise ContractError(str(exc)) from exc
        tolerance = capture.get("start_tolerance_seconds")
        if type(tolerance) is not int or not 0 <= tolerance <= 1800:
            raise ContractError("start_tolerance_seconds must be an integer from 0 to 1800")
        target = _time(capture.get("scheduled_at_utc"), f"{capture_id} schedule")
        if target <= locked:
            raise ContractError("every capture must be scheduled after protocol lock")
        if not start <= target < end:
            raise ContractError("every capture must be scheduled inside the market window")
        planned_end = target + timedelta(
            seconds=tolerance
            + (capture["samples"] - 1) * capture["interval_seconds"]
        )
        if planned_end >= end:
            raise ContractError("capture tolerance and schedule must finish before market end")
        fraction = (target - start) / duration
        expected_phase = PHASES[min(int(fraction * 3), 2)]
        if phase != expected_phase:
            raise ContractError(f"{capture_id} is outside its declared market phase")
        scheduled.append((target, phase))
    if {phase for _, phase in scheduled} != set(PHASES):
        raise ContractError("capture protocol must declare each market phase exactly once")
    if scheduled != sorted(scheduled) or [phase for _, phase in scheduled] != list(PHASES):
        raise ContractError("capture declarations must be chronologically early, middle, late")
    return deepcopy(protocol)


def empty_capture_state(protocol):
    validated = validate_capture_protocol(protocol)
    state = {
        "schema_version": STATE_SCHEMA,
        "protocol_id": validated["protocol_id"],
        "protocol_sha256": payload_hash(validated),
        "captures": {},
    }
    state["state_sha256"] = payload_hash(state)
    return state


def validate_capture_state(protocol, state):
    validate_capture_protocol(protocol)
    if not isinstance(state, dict) or state.get("schema_version") != STATE_SCHEMA:
        raise ContractError("unsupported book-sequence capture state schema")
    verify_artifact_hash(state, "state_sha256", "book-sequence capture state")
    if state.get("protocol_id") != protocol["protocol_id"]:
        raise ContractError("capture state belongs to a different protocol")
    if state.get("protocol_sha256") != payload_hash(protocol):
        raise ContractError("capture protocol changed after state creation")
    completed = state.get("captures")
    if not isinstance(completed, dict):
        raise ContractError("capture state captures must be an object")
    declared = {item["capture_id"] for item in protocol["captures"]}
    if not set(completed).issubset(declared):
        raise ContractError("capture state contains an undeclared capture")
    for capture_id, item in completed.items():
        if not isinstance(item, dict) or item.get("status") != "collected":
            raise ContractError(f"capture state entry is malformed: {capture_id}")
        for field in ("resolution_sha256", "raw_sequence_sha256",
                      "normalized_sequence_sha256", "resolution_path", "sequence_path"):
            if not str(item.get(field) or "").strip():
                raise ContractError(f"capture state entry lacks {field}: {capture_id}")
    return deepcopy(state)


def capture_protocol_status(protocol, state=None, now=None):
    """Report immutable collected state and time eligibility without networking."""
    protocol = validate_capture_protocol(protocol)
    state = (validate_capture_state(protocol, state) if state is not None
             else empty_capture_state(protocol))
    now = _time_text(now or utc_now())
    moment = _time(now, "status time")
    rows = []
    for capture in protocol["captures"]:
        capture_id = capture["capture_id"]
        target = _time(capture["scheduled_at_utc"], f"{capture_id} schedule")
        deadline = target + timedelta(seconds=capture["start_tolerance_seconds"])
        if capture_id in state["captures"]:
            status = "collected"
        elif moment < target:
            status = "not_open"
        elif moment <= deadline:
            status = "eligible"
        else:
            status = "missed"
        rows.append({
            "capture_id": capture_id,
            "phase": capture["phase"],
            "scheduled_at_utc": capture["scheduled_at_utc"],
            "deadline_at_utc": _time_text(deadline),
            "status": status,
            "result": deepcopy(state["captures"].get(capture_id)),
        })
    result = {
        "schema_version": "qcrl.book_sequence_capture_status.v1",
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": payload_hash(protocol),
        "evaluated_at_utc": now,
        "captures": rows,
    }
    result["status_sha256"] = payload_hash(result)
    return result


def load_capture_state(protocol, state_path):
    state_path = Path(state_path)
    if not state_path.exists():
        return empty_capture_state(protocol)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"capture state is unreadable: {state_path}") from exc
    return validate_capture_state(protocol, state)


def store_capture_state(protocol, state, state_path):
    state = validate_capture_state(protocol, state)
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(state, indent=2, sort_keys=True) + "\n"
    temporary = state_path.with_name(f".{state_path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, state_path)
    return state_path


def _resolved_market_payload(resolution):
    payload = resolution["observation"]["payload"]
    if resolution["reference_kind"] == "market":
        return payload
    return payload["markets"][0]


def execute_protocol_capture(protocol, capture_id, raw_directory, state_path,
                             acquirer=None, now=None, sleeper=None):
    """Execute exactly one currently eligible public capture and persist state."""
    protocol = validate_capture_protocol(protocol)
    state = load_capture_state(protocol, state_path)
    status = capture_protocol_status(protocol, state, now=now)
    row = next((item for item in status["captures"]
                if item["capture_id"] == capture_id), None)
    if row is None:
        raise ContractError(f"capture_id is not declared: {capture_id}")
    if row["status"] != "eligible":
        raise ContractError(f"capture {capture_id} is {row['status']}, not eligible")
    declaration = next(item for item in protocol["captures"]
                       if item["capture_id"] == capture_id)
    market = protocol["market"]
    acquirer = acquirer or PublicPolymarketAcquirer()
    resolution = acquirer.resolve_market_slug(
        market["slug"], market["reference_kind"]
    )
    payload = _resolved_market_payload(resolution)
    observed_terms = {
        "event_start_at_utc": payload.get("eventStartTime"),
        "event_end_at_utc": payload.get("endDate"),
        "resolution_source": payload.get("resolutionSource"),
    }
    expected_terms = {
        "event_start_at_utc": market["event_start_at_utc"],
        "event_end_at_utc": market["event_end_at_utc"],
        "resolution_source": market["resolution_source"],
    }
    if observed_terms != expected_terms:
        raise ContractError("resolved market terms differ from capture protocol")
    sequence = acquirer.acquire_book_sequence(
        resolution["resolved_market_id"], declaration["samples"],
        declaration["interval_seconds"], sleeper=sleeper,
    )
    sequence_started = _time(sequence["capture_started_at_utc"], "capture start")
    scheduled = _time(declaration["scheduled_at_utc"], "capture schedule")
    deadline = scheduled + timedelta(
        seconds=declaration["start_tolerance_seconds"]
    )
    if not scheduled <= sequence_started <= deadline:
        raise ContractError("sequence acquisition started outside its declared window")
    normalized = normalize_book_sequence(sequence)
    contract = normalize_bundle(sequence["samples"][0])["market_contract"]
    if {
        "event_start_at_utc": contract["terms"]["event_start_at_utc"],
        "event_end_at_utc": contract["terms"]["end_at_utc"],
        "resolution_source": contract["terms"]["resolution_source"],
    } != expected_terms:
        raise ContractError("captured market terms differ from capture protocol")
    if _time(sequence["capture_completed_at_utc"], "capture completion") >= _time(
        market["event_end_at_utc"], "market event end"
    ):
        raise ContractError("capture completed at or after market end")

    resolution_path = store_raw_slug_resolution(resolution, raw_directory)
    sequence_path = store_raw_book_sequence(sequence, raw_directory)
    state["captures"][capture_id] = {
        "status": "collected",
        "phase": declaration["phase"],
        "market_id": resolution["resolved_market_id"],
        "resolution_path": str(resolution_path),
        "resolution_sha256": resolution["resolution_sha256"],
        "sequence_path": str(sequence_path),
        "raw_sequence_sha256": sequence["sequence_sha256"],
        "normalized_sequence_sha256": normalized["sequence_sha256"],
        "capture_started_at_utc": sequence["capture_started_at_utc"],
        "capture_completed_at_utc": sequence["capture_completed_at_utc"],
    }
    state.pop("state_sha256", None)
    state["state_sha256"] = payload_hash(state)
    store_capture_state(protocol, state, state_path)
    return deepcopy(state["captures"][capture_id])
