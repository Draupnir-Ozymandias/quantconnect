import json
from pathlib import Path
import unittest

from execution_truth import ContractError, evaluate_latency_phase_batch


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "execution_truth" / "specs" / "latency_batch_daily_20260915_20260922.json"


def load_inputs():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    cohort_path = (SPEC.parent / spec["cross_market_spec_path"]).resolve()
    cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    markets = {
        label: {
            phase: (
                json.loads((cohort_path.parent / path).resolve().read_text(encoding="utf-8"))
                if path is not None else None
            )
            for phase, path in phases.items()
        }
        for label, phases in cohort["markets"].items()
    }
    return markets, spec


class LatencyBatchTests(unittest.TestCase):
    def test_live_batch_is_deterministic_complete_and_fail_closed(self):
        markets, spec = load_inputs()
        first = evaluate_latency_phase_batch(
            markets, spec["request_template"], spec["replay_policy"],
            spec["latency_policy"],
        )
        second = evaluate_latency_phase_batch(
            markets, spec["request_template"], spec["replay_policy"],
            spec["latency_policy"],
        )
        self.assertEqual(first, second)
        self.assertEqual(10, first["summary"]["case_count"])
        self.assertEqual(60, first["summary"]["row_count"])
        self.assertEqual({"evaluated": 60}, first["summary"]["row_status_counts"])
        self.assertEqual({"rejected": 60}, first["summary"]["mechanics_status_counts"])
        self.assertEqual(60, first["summary"]["mechanics_reason_counts"]["unknown_taker_delay_state"])
        self.assertEqual(60, first["summary"]["mechanics_reason_counts"]["unknown_minimum_order_age"])
        self.assertEqual(1, first["summary"]["cadence_warning_case_count"])
        self.assertEqual(64, len(first["batch_sha256"]))

    def test_request_template_is_exact_and_fixed(self):
        markets, spec = load_inputs()
        bad = dict(spec["request_template"], token_id="post_hoc")
        with self.assertRaisesRegex(ContractError, "template fields"):
            evaluate_latency_phase_batch(
                markets, bad, spec["replay_policy"], spec["latency_policy"]
            )


if __name__ == "__main__":
    unittest.main()
