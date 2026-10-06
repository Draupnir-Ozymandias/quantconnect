from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import classify_frame
from execution_truth.stream_freshness import analyze_rows, analyze_stream, milliseconds, statistics
from execution_truth.stream_segments import SegmentedStreamLog


BASE = 1791238200
SPEC = {"schema_version": "qcrl.public_market_stream_spec.v3", "market_id": "test",
        "condition_id": "condition", "asset_ids": ["up", "down"]}


def row(kind, payload, seconds=0):
    return {"kind": kind, "payload": payload, "local_monotonic_seconds": seconds,
            "received_at_utc": datetime.fromtimestamp(BASE + seconds, timezone.utc).isoformat()}


def frame(seconds, timestamp, connection=1, event_type="price_change", assets=None):
    event = {"event_type": event_type, "market": "condition", "timestamp": timestamp}
    if event_type == "book":
        event.update(asset_id=assets or "up", bids=[], asks=[])
    else:
        event["price_changes"] = [{"asset_id": "up"}]
    raw = json.dumps(event)
    return row("frame", {"connection": connection, "raw_text": raw,
                         "classification": classify_frame(raw, SPEC)}, seconds)


def header():
    return row("session_start", {"spec": SPEC, "spec_sha256": payload_hash(SPEC)})


class FreshnessTests(unittest.TestCase):
    def test_timestamp_units_are_explicit(self):
        self.assertEqual(milliseconds(str(BASE * 1000)), BASE)
        for invalid in (True, BASE, BASE * 1000000, "NaN", "1791238200000.0", -1):
            with self.assertRaises(ValueError):
                milliseconds(invalid)

    def test_linear_quantiles_and_negative_ages(self):
        s = statistics([-1, 0, 1, 2])
        self.assertEqual(s["p50_seconds"], .5)
        self.assertEqual(s["negative"], 1)
        self.assertEqual(s["above_seconds"]["1.0"], 1)
        self.assertEqual(statistics([]), {"count": 0})

    def test_missing_invalid_future_and_regression_are_retained(self):
        rows = [header(), frame(1, BASE * 1000), frame(2, None), frame(3, "broken"),
                frame(4, (BASE + 5) * 1000), frame(5, (BASE + 3) * 1000)]
        result = analyze_rows(rows)
        self.assertEqual(result["counts"]["selected_events"], 5)
        self.assertEqual(result["counts"]["missing_timestamps"], 1)
        self.assertEqual(result["counts"]["invalid_timestamps"], 1)
        self.assertEqual(result["receipt_age"]["negative"], 1)
        self.assertEqual(result["timestamp_regressions_within_connection_type_assets"], 1)

    def test_heartbeat_not_counted_as_exchange_event(self):
        result = analyze_rows([header(), row("frame", {"raw_text": "PONG"}, 1)])
        self.assertEqual(result["counts"]["heartbeat_frames"], 1)
        self.assertEqual(result["receipt_age"]["count"], 0)

    def test_gap_requires_both_book_baselines(self):
        rows = [header(), frame(1, BASE * 1000),
                row("connection_gap", {"connection": 1, "reason": "test"}, 2),
                frame(4.5, BASE * 1000, 2, "book", "up"),
                frame(4.6, BASE * 1000, 2, "book", "down")]
        gap = analyze_rows(rows)["reconnect_gaps"][0]
        self.assertEqual(gap["first_selected_seconds"], 2.5)
        self.assertEqual(gap["both_books_seconds"], 2.6)
        self.assertEqual(gap["last_to_next_selected_seconds"], 3.5)

    def test_clock_offset_is_not_silently_corrected(self):
        shifted = frame(2, BASE * 1000)
        shifted["received_at_utc"] = datetime.fromtimestamp(BASE + 12, timezone.utc).isoformat()
        result = analyze_rows([header(), shifted])
        self.assertEqual(result["max_wall_minus_monotonic_offset_change_seconds"], 10)
        self.assertEqual(result["receipt_age"]["p50_seconds"], 12)

    def test_monotonic_regression_rejected(self):
        with self.assertRaises(ContractError):
            analyze_rows([header(), frame(2, BASE * 1000), frame(1, BASE * 1000)])

    def test_event_budget_is_enforced(self):
        with patch("execution_truth.stream_freshness.MAX_EVENTS", 1):
            with self.assertRaises(ContractError):
                analyze_rows([header(), frame(1, BASE * 1000), frame(2, BASE * 1000)])

    def test_nonfinite_monotonic_rejected(self):
        for value in (float("nan"), float("inf"), True):
            invalid = frame(1, BASE * 1000)
            invalid["local_monotonic_seconds"] = value
            with self.assertRaises(ContractError):
                analyze_rows([header(), invalid])

    def test_legacy_unreclassified_evidence_rejected(self):
        with patch("execution_truth.stream_freshness.verify_segments", return_value={
            "manifest_present": True, "session_end_present": True,
            "header_spec": {"schema_version": "legacy"}}):
            with self.assertRaises(ContractError):
                analyze_stream("unused")

    def test_finalized_verified_stream_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            seconds = [0]
            log = SegmentedStreamLog(root,
                lambda: datetime.fromtimestamp(BASE + seconds[0], timezone.utc),
                lambda: seconds[0], {"segment_uncompressed_bytes": 1500,
                    "max_uncompressed_bytes": 100000, "max_compressed_bytes": 8 * 1024**2})
            log.append("session_start", header()["payload"])
            seconds[0] = 1
            log.append("frame", frame(1, BASE * 1000)["payload"])
            seconds[0] = 2
            log.append("session_end", {"status": "lifecycle_stop"})
            log.close()
            report = analyze_stream(root)
            self.assertEqual(report["receipt_age"]["p50_seconds"], 1)
            self.assertFalse(report["one_way_network_latency_proven"])
            self.assertEqual(report["report_sha256"], payload_hash(
                {k: v for k, v in report.items() if k != "report_sha256"}))
            segment = next(root.glob("*.gz"))
            segment.write_bytes(segment.read_bytes() + b"corruption")
            with self.assertRaises(ContractError):
                analyze_stream(root)

    def test_missing_footer_rejected(self):
        with patch("execution_truth.stream_freshness.verify_segments",
                   return_value={"manifest_present": True, "session_end_present": False}):
            with self.assertRaises(ContractError):
                analyze_stream("unused")


if __name__ == "__main__":
    unittest.main()
