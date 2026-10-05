import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.research_lane import load_research_lane, normalize_research_lane, plan_research_boundary
from execution_truth.signal_adapter import normalize_source_contract


ROOT = Path(__file__).parents[1]
SPEC = ROOT / "execution_truth/specs/binance_noon_eastern_research_lane.json"


class ResearchLaneTests(unittest.TestCase):
    def test_authority_verified_and_declaration_deterministic(self):
        raw = json.loads(SPEC.read_text())
        original = copy.deepcopy(raw)
        result = load_research_lane(SPEC)
        self.assertEqual(original, raw)
        self.assertEqual(normalize_research_lane(raw), result)
        unsigned = dict(result)
        self.assertEqual(unsigned.pop("declaration_sha256"), payload_hash(unsigned))
        self.assertFalse(result["activation"]["orders_authorized"])

    def test_summer_winter_and_dst_windows(self):
        lane = load_research_lane(SPEC)
        for end, start_utc, end_utc, seconds in [
            ("2026-09-30", "2026-09-29T16:00:00Z", "2026-09-30T16:00:00Z", 86400),
            ("2026-12-15", "2026-12-14T17:00:00Z", "2026-12-15T17:00:00Z", 86400),
            ("2026-03-08", "2026-03-07T17:00:00Z", "2026-03-08T16:00:00Z", 82800),
            ("2026-11-01", "2026-10-31T16:00:00Z", "2026-11-01T17:00:00Z", 90000),
        ]:
            with self.subTest(end=end):
                result = plan_research_boundary(lane, end)
                self.assertEqual(start_utc, result["target_start_at_utc"])
                self.assertEqual(end_utc, result["target_end_at_utc"])
                self.assertEqual(seconds, result["target_duration_seconds"])
                self.assertFalse(result["legacy_adapter_compatible"])

    def test_minute_close_is_not_available_at_noon(self):
        result = plan_research_boundary(load_research_lane(SPEC), "2026-09-30")
        self.assertEqual("2026-09-29T16:01:00Z", result["decision_not_before_utc"])
        self.assertTrue(result["availability_requires_actual_observation"])
        self.assertFalse(result["signal_emitted"])
        unsigned = dict(result)
        self.assertEqual(unsigned.pop("plan_sha256"), payload_hash(unsigned))

    def test_lane_cannot_be_used_as_legacy_source_contract(self):
        with self.assertRaisesRegex(ContractError, "schema"):
            normalize_source_contract(load_research_lane(SPEC))
        frozen = normalize_source_contract(json.loads(
            (ROOT / "execution_truth/specs/qcrl_btcusd_1d_source.json").read_text()))
        self.assertEqual("coinbase", frozen["venue"])
        self.assertEqual("UTC", frozen["bar_anchor_timezone"])
        self.assertEqual(0, frozen["bar_anchor_offset_seconds"])

    def test_changed_semantics_fail_closed(self):
        raw = json.loads(SPEC.read_text())
        updates = [
            ("source", "timezone", "UTC"), ("source", "price_field", "open"),
            ("source", "symbol", "BTCUSD"), ("source", "candle_duration_seconds", True),
            ("signal", "streak_length", 4), ("signal", "filter_model", "atr_volatility"),
            ("target", "tie_settlement", "down"),
            ("evaluation", "historical_results_transfer", True),
            ("activation", "orders_authorized", 0),
        ]
        for section, key, value in updates:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(raw)
                changed[section][key] = value
                with self.assertRaises(ContractError):
                    normalize_research_lane(changed)

    def test_invalid_dates_reject(self):
        lane = load_research_lane(SPEC)
        for value in ("2026-02-30", "20261005", "2026-10-05T12:00:00Z", None):
            with self.assertRaises(ContractError):
                plan_research_boundary(lane, value)

    def test_tampered_hashed_declaration_rejects(self):
        lane = load_research_lane(SPEC)
        lane["declared_on"] = "2026-10-05"
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            plan_research_boundary(lane, "2026-10-06")

    def test_tampered_authority_rejects(self):
        raw = json.loads(SPEC.read_text())
        raw["authority"]["market_terms_path"] = str(
            (SPEC.parent / raw["authority"]["market_terms_path"]).resolve())
        raw["authority"]["market_terms_file_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spec.json"
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ContractError, "file hash mismatch"):
                load_research_lane(path)

    def test_cli_plans_without_acquisition(self):
        completed = subprocess.run([
            sys.executable, str(ROOT / "qcrl_execution_truth.py"), "research-lane", str(SPEC),
            "--target-end-date", "2026-11-01"
        ], capture_output=True, text=True, check=True)
        result = json.loads(completed.stdout)
        self.assertEqual(90000, result["target_duration_seconds"])
        self.assertFalse(result["orders_authorized"])


if __name__ == "__main__":
    unittest.main()
