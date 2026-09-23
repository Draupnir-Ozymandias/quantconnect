"""Deadline-aware retry worker for locked public capture protocols."""

from copy import deepcopy
from datetime import datetime, timezone
import time

from .acquisition import AcquisitionError, PublicPolymarketAcquirer, utc_now, utc_text
from .capture_protocol import (
    capture_protocol_status,
    execute_protocol_capture,
    load_capture_state,
    validate_capture_protocol,
)
from .contracts import ContractError, payload_hash


WORKER_REPORT_SCHEMA = "qcrl.capture_worker_report.v1"


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def run_capture_with_retries(protocol, capture_id, raw_directory, state_path,
                             max_attempts=4, initial_backoff_seconds=5,
                             max_backoff_seconds=30, acquirer_factory=None,
                             clock=None, sleeper=None):
    """Retry acquisition failures inside the immutable capture start window.

    Contract and timing failures are intentionally not retried: they indicate a
    declaration violation rather than a transient network condition.
    """
    protocol = validate_capture_protocol(protocol)
    if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
        raise ContractError("max_attempts must be an integer from 1 to 10")
    if type(initial_backoff_seconds) is not int or not 1 <= initial_backoff_seconds <= 60:
        raise ContractError("initial_backoff_seconds must be an integer from 1 to 60")
    if type(max_backoff_seconds) is not int or not 1 <= max_backoff_seconds <= 60:
        raise ContractError("max_backoff_seconds must be an integer from 1 to 60")
    clock = clock or utc_now
    sleeper = sleeper or time.sleep
    acquirer_factory = acquirer_factory or (
        lambda: PublicPolymarketAcquirer(clock=clock)
    )
    attempts = []
    report = {
        "schema_version": WORKER_REPORT_SCHEMA,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": payload_hash(protocol),
        "capture_id": capture_id,
        "retry_policy": {
            "max_attempts": max_attempts,
            "initial_backoff_seconds": initial_backoff_seconds,
            "max_backoff_seconds": max_backoff_seconds,
            "retryable_error": "AcquisitionError",
        },
        "attempts": attempts,
        "status": None,
        "result": None,
    }

    for attempt_number in range(1, max_attempts + 1):
        moment = clock()
        state = load_capture_state(protocol, state_path)
        status = capture_protocol_status(protocol, state, now=moment)
        row = next((item for item in status["captures"]
                    if item["capture_id"] == capture_id), None)
        if row is None:
            raise ContractError(f"capture_id is not declared: {capture_id}")
        if row["status"] != "eligible":
            if not attempts:
                raise ContractError(
                    f"capture {capture_id} is {row['status']}, not eligible"
                )
            report["status"] = "window_closed"
            break
        attempt = {
            "attempt": attempt_number,
            "started_at_utc": utc_text(moment),
            "outcome": None,
        }
        attempts.append(attempt)
        try:
            result = execute_protocol_capture(
                protocol, capture_id, raw_directory, state_path,
                acquirer=acquirer_factory(), now=moment, sleeper=sleeper,
            )
        except AcquisitionError as exc:
            attempt["outcome"] = "acquisition_error"
            attempt["error"] = str(exc)
            if attempt_number == max_attempts:
                report["status"] = "attempts_exhausted"
                break
            delay = min(
                initial_backoff_seconds * (2 ** (attempt_number - 1)),
                max_backoff_seconds,
            )
            remaining = (_time(row["deadline_at_utc"]) - clock()).total_seconds()
            if delay >= remaining:
                report["status"] = "window_closed"
                break
            attempt["backoff_seconds"] = delay
            sleeper(delay)
        else:
            attempt["outcome"] = "collected"
            report["status"] = "collected"
            report["result"] = deepcopy(result)
            break

    report["completed_at_utc"] = utc_text(clock())
    report["report_sha256"] = payload_hash(report)
    return report
