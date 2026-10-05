import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_truth.binding import bind_signal_to_market
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.delayed_signal import materialize_delayed_signal
from execution_truth.research_lane import load_research_lane
from tests.test_binance_source import dataset, rehash, SPEC, ROOT


class DelayedSignalTests(unittest.TestCase):
    def setUp(self):
        self.lane = load_research_lane(SPEC)

    def signal(self, raw=None, end="2026-09-30", decision="2026-09-29T16:05:00Z"):
        return materialize_delayed_signal(self.lane, raw or dataset(), end, decision)

    def test_emits_reversal_without_backdating_or_mutation(self):
        raw = dataset()
        original = copy.deepcopy(raw)
        result = self.signal(raw)
        intent = result["intent"]
        self.assertTrue(result["emitted"])
        self.assertEqual("down", intent["direction"])
        self.assertEqual("2026-09-29T16:00:00Z", intent["target_start_at_utc"])
        self.assertEqual("2026-09-29T16:05:00Z", intent["available_at_utc"])
        self.assertEqual(300, intent["decision_delay_seconds"])
        self.assertFalse(intent["orders_authorized"])
        self.assertFalse(intent["original_boundary_availability_proven"])
        self.assertEqual(original, raw)
        for value, field in ((result, "decision_sha256"), (intent, "intent_sha256")):
            unsigned = dict(value)
            self.assertEqual(unsigned.pop(field), payload_hash(unsigned))

    def test_down_streak_emits_up(self):
        self.assertEqual("up", self.signal(dataset(closes=("102", "101", "100")))["intent"]["direction"])

    def test_before_completion_and_before_observation_reject(self):
        for decision, reason in (("2026-09-29T16:00:30Z", "decision_before_latest_input_completion"),
                                 ("2026-09-29T16:01:00Z", "inputs_not_observed_by_decision")):
            result = self.signal(decision=decision)
            self.assertFalse(result["emitted"])
            self.assertIn(reason, result["non_emission_reasons"])

    def test_later_historical_retrieval_cannot_create_past_intent(self):
        raw = dataset()
        for entry in raw["observations"]:
            entry["observation"]["observed_at_utc"] = "2026-10-05T20:00:00Z"
        result = self.signal(rehash(raw))
        self.assertIn("inputs_not_observed_by_decision", result["non_emission_reasons"])
        self.assertIsNone(result["intent"])

    def test_expired_window_rejects_at_exact_end(self):
        result = self.signal(decision="2026-09-30T16:00:00Z")
        self.assertIn("target_window_expired", result["non_emission_reasons"])

    def test_gap_cannot_be_skipped_like_a_tie(self):
        raw = dataset(closes=("100", "101", "102", "103", "104"))
        raw["observations"].pop(1)
        result = self.signal(rehash(raw), end="2026-10-02", decision="2026-10-01T16:05:00Z")
        self.assertIn("missing_exact_boundary_history", result["non_emission_reasons"])
        self.assertIsNone(result["intent"])

    def test_ties_skipped_only_with_complete_history(self):
        raw = dataset(closes=("100", "101", "101", "102"))
        result = self.signal(raw, end="2026-10-01", decision="2026-09-30T16:05:00Z")
        self.assertEqual("down", result["intent"]["direction"])
        self.assertEqual(2, len(result["intent"]["selected_source_record_sha256"]))

    def test_insufficient_and_mixed_history_do_not_emit(self):
        for closes, reason in ((("100", "100", "101"), "insufficient_non_tied_history"),
                               (("100", "101", "100"), "streak_not_present")):
            result = self.signal(dataset(closes=closes))
            self.assertIn(reason, result["non_emission_reasons"])
            self.assertIsNone(result["intent"])

    def test_future_data_and_wrong_target_reject(self):
        with self.assertRaisesRegex(ContractError, "end exactly"):
            self.signal(end="2026-09-29")
        with self.assertRaisesRegex(ContractError, "end exactly"):
            self.signal(end="2026-10-01")

    def test_dst_target_and_source_windows(self):
        for first, end, decision, seconds in (
            ("2026-10-29", "2026-11-01", "2026-10-31T16:05:00Z", 90000),
            ("2026-03-05", "2026-03-08", "2026-03-07T17:05:00Z", 82800),
        ):
            result = self.signal(dataset(first), end=end, decision=decision)
            self.assertEqual(seconds, result["intent"]["target_duration_seconds"])

    def test_legacy_binding_rejects_new_intent_schema(self):
        with self.assertRaisesRegex(ContractError, "unsupported signal intent schema"):
            bind_signal_to_market(self.signal()["intent"], {}, {}, "2026-09-29T16:05:00Z")

    def test_cli_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.json"
            path.write_text(json.dumps(dataset()))
            completed = subprocess.run([
                sys.executable, str(ROOT / "qcrl_execution_truth.py"), "delayed-signal", str(SPEC), str(path),
                "--target-end-date", "2026-09-30", "--decision-at-utc", "2026-09-29T16:05:00Z"
            ], check=True, capture_output=True, text=True)
            self.assertTrue(json.loads(completed.stdout)["emitted"])


if __name__ == "__main__":
    unittest.main()
