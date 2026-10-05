import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo

from execution_truth.binance_source import adapt_boundary_dataset
from execution_truth.binance_resolution import BINANCE_KLINES_ENDPOINT
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.research_lane import load_research_lane


ROOT = Path(__file__).parents[1]
SPEC = ROOT / "execution_truth/specs/binance_noon_eastern_research_lane.json"


def rehash(raw):
    for entry in raw["observations"]:
        observation = entry["observation"]
        observation["payload_sha256"] = payload_hash(observation["payload"])
    raw.pop("dataset_sha256", None)
    raw["dataset_sha256"] = payload_hash(raw)
    return raw


def dataset(first="2026-09-27", closes=("100", "101", "102")):
    start = date.fromisoformat(first)
    entries = []
    for index, close in enumerate(closes):
        day = start + timedelta(days=index)
        boundary = datetime(day.year, day.month, day.day, 12, tzinfo=ZoneInfo("America/New_York"))
        ms = int(boundary.timestamp() * 1000)
        entries.append({"boundary_local_date": day.isoformat(), "observation": {
            "endpoint": BINANCE_KLINES_ENDPOINT,
            "params": {"symbol": "BTCUSDT", "interval": "1m", "startTime": ms,
                       "endTime": ms + 59999, "limit": 1},
            "observed_at_utc": (boundary.astimezone(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "payload": [[ms, "100", "200", "1", close, "1", ms + 59999, "1", 1, "1", "1", "0"]],
        }})
    return rehash({
        "schema_version": "qcrl.binance_boundary_dataset.v1",
        "declaration_sha256": load_research_lane(SPEC)["declaration_sha256"],
        "evidence_role": "historical_retrieval", "evidence_class": "synthetic_fixture",
        "first_boundary_local_date": first,
        "last_boundary_local_date": (start + timedelta(days=len(closes)-1)).isoformat(),
        "observations": entries,
    })


class BinanceSourceTests(unittest.TestCase):
    def setUp(self):
        self.lane = load_research_lane(SPEC)

    def test_adjacent_closes_not_daily_ohlc_derive_direction(self):
        raw = dataset(closes=("100", "102", "101"))
        original = copy.deepcopy(raw)
        result = adapt_boundary_dataset(self.lane, raw)
        self.assertEqual({"up": 1, "down": 1, "tie": 0}, result["direction_counts"])
        self.assertTrue(result["complete"])
        self.assertEqual("100", result["source_records"][0]["start_close"])
        self.assertEqual(original, raw)
        self.assertFalse(result["signal_emitted"])
        self.assertFalse(result["orders_authorized"])
        for item in [result, *result["source_records"]]:
            field = "audit_sha256" if "audit_sha256" in item else "record_sha256"
            unsigned = dict(item)
            self.assertEqual(unsigned.pop(field), payload_hash(unsigned))

    def test_ties_are_preserved_with_split_outcome(self):
        result = adapt_boundary_dataset(self.lane, dataset(closes=("100", "100", "102")))
        self.assertEqual(1, result["direction_counts"]["tie"])
        self.assertEqual("Split", result["source_records"][0]["market_comparison_outcome"])

    def test_gaps_do_not_create_bridging_records(self):
        raw = dataset(closes=("100", "101", "102", "103"))
        raw["observations"].pop(1)
        result = adapt_boundary_dataset(self.lane, rehash(raw))
        self.assertFalse(result["complete"])
        self.assertEqual(["2026-09-28"], result["missing_boundary_local_dates"])
        self.assertEqual(2, len(result["unavailable_source_pairs"]))
        self.assertEqual(1, len(result["source_records"]))
        self.assertEqual("2026-09-29", result["source_records"][0]["start_local_date"])

    def test_empty_dataset_reports_entire_gap(self):
        raw = dataset()
        raw["observations"] = []
        result = adapt_boundary_dataset(self.lane, rehash(raw))
        self.assertEqual(3, len(result["missing_boundary_local_dates"]))
        self.assertEqual([], result["source_records"])

    def test_actual_retrieval_time_is_not_backdated(self):
        raw = dataset()
        for entry in raw["observations"]:
            entry["observation"]["observed_at_utc"] = "2026-10-04T20:00:00Z"
        result = adapt_boundary_dataset(self.lane, rehash(raw))
        for record in result["source_records"]:
            self.assertEqual("2026-10-04T20:00:00Z", record["observed_available_at_utc"])
            self.assertFalse(record["original_boundary_availability_proven"])

    def test_dst_and_winter_calendar_boundaries(self):
        for first, seconds in (("2026-03-07", 82800), ("2026-10-31", 90000), ("2026-12-14", 86400)):
            with self.subTest(first=first):
                result = adapt_boundary_dataset(self.lane, dataset(first, ("100", "101")))
                self.assertEqual(seconds, result["source_records"][0]["duration_seconds"])
        winter = adapt_boundary_dataset(self.lane, dataset("2026-12-14", ("100", "101")))
        self.assertEqual("2026-12-14T17:00:00Z", winter["source_records"][0]["start_at_utc"])

    def test_unfinished_candle_and_unzoned_time_reject(self):
        for observed in ("2026-09-27T16:00:59.999Z", "2026-09-27T16:05:00"):
            raw = dataset()
            raw["observations"][0]["observation"]["observed_at_utc"] = observed
            with self.assertRaises(ContractError):
                adapt_boundary_dataset(self.lane, rehash(raw))

    def test_exact_completion_boundary_allowed(self):
        raw = dataset()
        raw["observations"][0]["observation"]["observed_at_utc"] = "2026-09-27T16:01:00Z"
        self.assertTrue(adapt_boundary_dataset(self.lane, rehash(raw))["complete"])

    def test_payload_and_dataset_tampering_reject(self):
        raw = dataset()
        raw["observations"][0]["observation"]["payload"][0][4] = "999"
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            adapt_boundary_dataset(self.lane, raw)
        raw.pop("dataset_sha256")
        raw["dataset_sha256"] = payload_hash(raw)
        with self.assertRaisesRegex(ContractError, "payload hash mismatch"):
            adapt_boundary_dataset(self.lane, raw)

    def test_wrong_pair_interval_endpoint_and_request_time_reject(self):
        for key, value in (("symbol", "BTCUSD"), ("interval", "1d"), ("startTime", 1)):
            raw = dataset()
            raw["observations"][0]["observation"]["params"][key] = value
            with self.assertRaises(ContractError):
                adapt_boundary_dataset(self.lane, rehash(raw))
        raw = dataset()
        raw["observations"][0]["observation"]["endpoint"] = "https://api.coinbase.com"
        with self.assertRaises(ContractError):
            adapt_boundary_dataset(self.lane, rehash(raw))

    def test_wrong_candle_timestamp_and_bad_price_reject(self):
        for index, value in ((0, 1), (6, 1), (4, "NaN"), (4, "0")):
            raw = dataset()
            raw["observations"][0]["observation"]["payload"][0][index] = value
            with self.assertRaises(ContractError):
                adapt_boundary_dataset(self.lane, rehash(raw))

    def test_duplicates_order_and_out_of_range_reject(self):
        raw = dataset()
        raw["observations"][1] = copy.deepcopy(raw["observations"][0])
        with self.assertRaisesRegex(ContractError, "duplicate"):
            adapt_boundary_dataset(self.lane, rehash(raw))
        raw = dataset()
        raw["observations"].reverse()
        with self.assertRaisesRegex(ContractError, "ordered"):
            adapt_boundary_dataset(self.lane, rehash(raw))
        raw = dataset()
        raw["first_boundary_local_date"] = "2026-09-28"
        raw["observations"].pop()
        with self.assertRaisesRegex(ContractError, "outside"):
            adapt_boundary_dataset(self.lane, rehash(raw))

    def test_undeclared_evidence_class_or_lane_reject(self):
        for key, value in (("declaration_sha256", "0" * 64), ("evidence_class", "unknown"),
                           ("evidence_role", "prospective")):
            raw = dataset()
            raw[key] = value
            with self.assertRaises(ContractError):
                adapt_boundary_dataset(self.lane, rehash(raw))

    def test_cli_returns_audit_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(json.dumps(dataset()))
            result = subprocess.run([
                sys.executable, str(ROOT / "qcrl_execution_truth.py"), "research-source", str(SPEC), str(path)
            ], check=True, capture_output=True, text=True)
            self.assertEqual(2, len(json.loads(result.stdout)["source_records"]))


if __name__ == "__main__":
    unittest.main()
