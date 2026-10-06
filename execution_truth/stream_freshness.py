"""Offline, verified public-stream receipt-age diagnostics; never fill evidence."""

import argparse
from array import array
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import verify_segments


SCHEMA = "qcrl.stream_freshness.v1"
MAX_EVENTS = 1000000
THRESHOLDS = (0.1, 0.25, 1.0, 5.0)


def epoch(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ContractError("receipt timestamp must include timezone")
    return parsed.timestamp()


def milliseconds(value):
    # Explicit archived CLOB millisecond format, never guess seconds/microseconds.
    if type(value) is int:
        number = value
    elif isinstance(value, str) and len(value) == 13 and value.isascii() and value.isdigit():
        number = int(value)
    else:
        raise ValueError("invalid millisecond timestamp")
    if not 10**12 <= number < 10**13:
        raise ValueError("timestamp outside declared millisecond range")
    return number / 1000


def statistics(values):
    values = sorted(values)
    if not values:
        return {"count": 0}
    def quantile(q):
        position = (len(values) - 1) * q
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 6)
    return {"count": len(values), "min_seconds": round(values[0], 6),
            "p50_seconds": quantile(.5), "p90_seconds": quantile(.9),
            "p99_seconds": quantile(.99), "max_seconds": round(values[-1], 6),
            "negative": sum(v < 0 for v in values),
            "above_seconds": {str(t): sum(v > t for v in values) for t in THRESHOLDS}}


def analyze_rows(rows):
    """Summarize supplied rows. Public analyze_stream verifies them first."""
    ages = array("d")
    grouped = {"event_type": {}, "connection": {}, "receipt_minute_utc": {}}
    counts = Counter()
    frame_minutes = Counter()
    gaps = []
    pending = None
    last_selected = None
    previous_mono = None
    initial_offset = None
    offset_change = 0.0
    backwards = 0
    seen_timestamps = {}
    assets = set()
    books = set()
    spec = None
    selected_total = 0
    for row in rows:
        receipt = epoch(row["received_at_utc"])
        mono = row["local_monotonic_seconds"]
        if type(mono) not in (int, float) or not math.isfinite(mono):
            raise ContractError("local monotonic receipt time must be finite numeric")
        if previous_mono is not None and mono < previous_mono:
            raise ContractError("local monotonic receipt time moved backwards")
        previous_mono = mono
        offset = receipt - mono
        if initial_offset is None:
            initial_offset = offset
        offset_change = max(offset_change, abs(offset - initial_offset))
        kind, payload = row["kind"], row["payload"]
        if kind == "session_start":
            spec = payload["spec"]
            assets = set(spec["asset_ids"])
        elif kind == "connection_gap":
            pending = {"at_utc": row["received_at_utc"], "reason": payload["reason"],
                       "connection": payload["connection"], "gap_mono": mono,
                       "last_selected_mono": last_selected}
            gaps.append(pending)
            books = set()
        elif kind == "frame":
            counts["frames"] += 1
            minute = datetime.fromtimestamp(receipt, timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")
            frame_minutes[minute] += 1
            raw = payload["raw_text"]
            if raw == "PONG":
                counts["heartbeat_frames"] += 1
                continue
            try:
                data = json.loads(raw)
            except (ValueError, TypeError):
                counts["unparsed_frames"] += 1
                continue
            events = data if isinstance(data, list) else [data]
            classes = payload["classification"]
            if len(events) != len(classes):
                raise ContractError("classification/event count mismatch")
            for event, classification in zip(events, classes):
                if classification["scope"] != "selected_market":
                    counts["other_or_unconfirmed_events"] += 1
                    continue
                selected_total += 1
                if selected_total > MAX_EVENTS:
                    raise ContractError("freshness analysis event budget exceeded")
                if not isinstance(event, dict):
                    raise ContractError("selected event must be an object")
                counts["selected_events"] += 1
                event_type = classification["event_type"]
                if pending and payload["connection"] > pending["connection"]:
                    if "first_selected_seconds" not in pending:
                        pending["first_selected_seconds"] = round(mono - pending["gap_mono"], 6)
                        pending["last_to_next_selected_seconds"] = (None if pending["last_selected_mono"] is None
                            else round(mono - pending["last_selected_mono"], 6))
                    if event_type == "book":
                        books.update(classification["asset_ids"])
                    if assets <= books and "both_books_seconds" not in pending:
                        pending["both_books_seconds"] = round(mono - pending["gap_mono"], 6)
                last_selected = mono
                value = event.get("timestamp")
                if value is None:
                    counts["missing_timestamps"] += 1
                    continue
                try:
                    source = milliseconds(value)
                except ValueError:
                    counts["invalid_timestamps"] += 1
                    continue
                age = receipt - source
                ages.append(age)
                counts["timestamped_selected_events"] += 1
                # Regressions are descriptive only; independent event types/tokens
                # need not share a total ordering or a delivery sequence number.
                key = (payload["connection"], event_type, tuple(sorted(set(classification["asset_ids"]))))
                if key in seen_timestamps and source < seen_timestamps[key]:
                    backwards += 1
                seen_timestamps[key] = source
                for dimension, label in (("event_type", event_type),
                                         ("connection", str(payload["connection"])),
                                         ("receipt_minute_utc", minute)):
                    if label not in grouped[dimension]:
                        if len(grouped[dimension]) >= 128:
                            raise ContractError("freshness grouping budget exceeded")
                        grouped[dimension][label] = array("d")
                    grouped[dimension][label].append(age)
    for gap in gaps:
        gap.pop("gap_mono")
        gap.pop("last_selected_mono")
    return {"counts": dict(counts), "receipt_age": statistics(ages),
            "by": {dimension: {label: statistics(values) for label, values in sorted(groups.items())}
                   for dimension, groups in grouped.items()},
            "frames_by_receipt_minute_utc": dict(sorted(frame_minutes.items())),
            "reconnect_gaps": gaps, "timestamp_regressions_within_connection_type_assets": backwards,
            "max_wall_minus_monotonic_offset_change_seconds": round(offset_change, 6)}


def analyze_stream(root):
    root = Path(root)
    verification = verify_segments(root)
    if not verification["manifest_present"] or not verification["session_end_present"]:
        raise ContractError("freshness report requires a finalized verified stream")
    if verification["header_spec"].get("schema_version") != "qcrl.public_market_stream_spec.v3":
        raise ContractError("freshness report requires raw-reclassified v3 stream evidence")
    def rows():
        for segment in sorted(root.glob("segment-*.gz")):
            with gzip.open(segment, "rt", encoding="utf-8") as handle:
                for line in handle:
                    yield json.loads(line)
    report = {"schema_version": SCHEMA,
              "source": {"market_id": verification["header_spec"]["market_id"],
                         "manifest_sha256": json.loads((root / "manifest.json").read_text())["manifest_sha256"],
                         "final_record_sha256": verification["final_record_sha256"]},
              "measurement": "local_utc_receipt_minus_selected_event_unix_milliseconds",
              "quantiles": "linear_interpolation_at_(count-1)*q",
              "thresholds_role": "descriptive_bins_not_execution_or_acceptance_policy",
              "clock_synchronization_proven": False, "one_way_network_latency_proven": False,
              "continuous_coverage_proven": False, "orders_authorized": False,
              **analyze_rows(rows())}
    report["report_sha256"] = payload_hash(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("streams", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([analyze_stream(path) for path in args.streams], sort_keys=True))


if __name__ == "__main__":
    main()
