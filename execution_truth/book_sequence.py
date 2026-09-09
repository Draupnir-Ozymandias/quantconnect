"""Bounded public capture and offline normalization of market-book sequences."""

from datetime import datetime, timezone
from time import sleep

from .acquisition import RAW_BUNDLE_SCHEMA, AcquisitionError, utc_text
from .bundle import NORMALIZED_BUNDLE_SCHEMA, normalize_bundle
from .contracts import ContractError, payload_hash, verify_artifact_hash


RAW_SEQUENCE_SCHEMA = "qcrl.polymarket_raw_book_sequence.v1"
SEQUENCE_SCHEMA = "qcrl.polymarket_book_sequence.v1"
MAX_SAMPLES = 120
MAX_INTERVAL_SECONDS = 60
MAX_SCHEDULE_SECONDS = 3600


def validate_sequence_limits(sample_count, interval_seconds):
    if type(sample_count) is not int or not 2 <= sample_count <= MAX_SAMPLES:
        raise AcquisitionError(f"sample_count must be an integer from 2 to {MAX_SAMPLES}")
    if type(interval_seconds) is not int or not 1 <= interval_seconds <= MAX_INTERVAL_SECONDS:
        raise AcquisitionError(
            f"interval_seconds must be an integer from 1 to {MAX_INTERVAL_SECONDS}"
        )
    if (sample_count - 1) * interval_seconds > MAX_SCHEDULE_SECONDS:
        raise AcquisitionError("requested sequence schedule exceeds one hour")


def acquire_book_sequence(acquirer, market_id, sample_count, interval_seconds, sleeper=None):
    """Capture a finite sequence of complete public market bundles."""
    validate_sequence_limits(sample_count, interval_seconds)
    market_id = str(market_id).strip()
    if not market_id or not market_id.isdigit():
        raise AcquisitionError("market_id must be numeric")
    sleeper = sleeper or sleep
    started = utc_text(acquirer.clock())
    samples = []
    for index in range(sample_count):
        if index:
            sleeper(interval_seconds)
        samples.append(acquirer.acquire_market_bundle(market_id))
    sequence = {
        "schema_version": RAW_SEQUENCE_SCHEMA,
        "market_id_requested": market_id,
        "capture_started_at_utc": started,
        "capture_completed_at_utc": utc_text(acquirer.clock()),
        "requested_sample_count": sample_count,
        "requested_interval_seconds": interval_seconds,
        "samples": samples,
    }
    sequence["sequence_sha256"] = payload_hash(sequence)
    return sequence


def _time(value, name):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def normalize_book_sequence(raw_sequence):
    """Verify a raw sequence and derive compact, hashed sample summaries."""
    if not isinstance(raw_sequence, dict):
        raise ContractError("raw sequence must be an object")
    if raw_sequence.get("schema_version") != RAW_SEQUENCE_SCHEMA:
        raise ContractError("unsupported raw book sequence schema")
    verify_artifact_hash(raw_sequence, "sequence_sha256", "raw book sequence")
    count = raw_sequence.get("requested_sample_count")
    interval = raw_sequence.get("requested_interval_seconds")
    try:
        validate_sequence_limits(count, interval)
    except AcquisitionError as exc:
        raise ContractError(str(exc)) from exc
    market_id = str(raw_sequence.get("market_id_requested") or "").strip()
    if not market_id or not market_id.isdigit():
        raise ContractError("raw sequence market id must be numeric")
    samples = raw_sequence.get("samples")
    if not isinstance(samples, list) or len(samples) != count:
        raise ContractError("raw sequence sample count disagrees with declaration")

    started = _time(raw_sequence.get("capture_started_at_utc"), "capture start")
    completed = _time(raw_sequence.get("capture_completed_at_utc"), "capture completion")
    if completed < started:
        raise ContractError("capture completion precedes capture start")

    identity = None
    previous_acquired = None
    timeline_cursor = started
    summaries = []
    for index, raw in enumerate(samples):
        if not isinstance(raw, dict) or raw.get("schema_version") != RAW_BUNDLE_SCHEMA:
            raise ContractError(f"sequence sample {index} is not a raw market bundle")
        if str(raw.get("market_id_requested")) != market_id:
            raise ContractError(f"sequence sample {index} has a different market id")
        acquired = _time(raw.get("acquired_at_utc"), f"sequence sample {index} acquisition")
        if acquired < started or acquired > completed:
            raise ContractError(f"sequence sample {index} falls outside capture bounds")
        if previous_acquired is not None and acquired <= previous_acquired:
            raise ContractError("sequence sample acquisition times must strictly increase")
        previous_acquired = acquired

        observations = raw.get("observations")
        if not isinstance(observations, dict):
            raise ContractError(f"sequence sample {index} has no observations")
        ordered_observations = [
            observations.get("gamma_market"),
            observations.get("clob_market"),
            *(observations.get("order_books") or []),
        ]
        moments = [(acquired, f"sequence sample {index} acquisition")]
        for observation_index, observation in enumerate(ordered_observations):
            if not isinstance(observation, dict):
                raise ContractError(f"sequence sample {index} observation is missing")
            moments.append((_time(
                observation.get("observed_at_utc"),
                f"sequence sample {index} observation {observation_index}",
            ), f"sequence sample {index} observation {observation_index}"))
        for moment, name in moments:
            if moment < timeline_cursor:
                raise ContractError(f"{name} precedes the prior capture observation")
            if moment > completed:
                raise ContractError(f"{name} falls after capture completion")
            timeline_cursor = moment

        normalized = normalize_bundle(raw)
        contract = normalized["market_contract"]
        current_identity = {
            "market_id": contract["identity"]["market_id"],
            "condition_id": contract["identity"]["condition_id"],
            "outcomes": contract["outcomes"],
        }
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise ContractError("market identity or outcome mapping changed within sequence")

        books = sorted(normalized["order_books"], key=lambda item: item["token_id"])
        summaries.append({
            "index": index,
            "acquired_at_utc": raw["acquired_at_utc"],
            "raw_bundle_sha256": raw["bundle_sha256"],
            "normalized_bundle_schema": NORMALIZED_BUNDLE_SCHEMA,
            "normalized_bundle_sha256": normalized["bundle_sha256"],
            "market_contract_sha256": contract["contract_sha256"],
            "gamma_payload_sha256": observations["gamma_market"]["payload_sha256"],
            "clob_payload_sha256": observations["clob_market"]["payload_sha256"],
            "execution_metadata": {
                "accepting_orders": contract["state"]["accepting_orders"],
                "fees_enabled": contract["state"]["fees_enabled"],
                "taker_order_delay_enabled": contract["constraints"]["taker_order_delay_enabled"],
                "minimum_order_age_seconds": contract["constraints"]["minimum_order_age_seconds"],
            },
            "books": [{
                "token_id": book["token_id"],
                "outcome": book["outcome"],
                "observed_at_utc": book["observed_at_utc"],
                "exchange_timestamp": book["exchange_timestamp"],
                "exchange_book_hash": book["exchange_book_hash"],
                "snapshot_sha256": book["snapshot_sha256"],
                "best_bid": book["best_bid"],
                "best_ask": book["best_ask"],
            } for book in books],
        })

    result = {
        "schema_version": SEQUENCE_SCHEMA,
        "raw_sequence_sha256": raw_sequence["sequence_sha256"],
        "market_identity": identity,
        "capture_started_at_utc": raw_sequence["capture_started_at_utc"],
        "capture_completed_at_utc": raw_sequence["capture_completed_at_utc"],
        "requested_sample_count": count,
        "requested_interval_seconds": interval,
        "samples": summaries,
        "limitations": [
            "public polling cadence is requested sleep plus network duration",
            "observations do not establish maker queues, hidden liquidity, or actual fills",
            "exchange delay is unknown unless explicit contemporaneous evidence defines it",
        ],
    }
    result["sequence_sha256"] = payload_hash(result)
    return result
