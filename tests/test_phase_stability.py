import json
from pathlib import Path
import unittest

from execution_truth import ContractError, analyze_phase_sequences


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "execution_truth" / "specs" / "phase_stability_daily_20260915.json"


def load_sequences():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    return {
        phase: json.loads((SPEC.parent / path).resolve().read_text(encoding="utf-8"))
        for phase, path in spec["phases"].items()
    }


class PhaseStabilityTests(unittest.TestCase):
    def test_live_phase_analysis_is_deterministic_and_complete(self):
        first = analyze_phase_sequences(load_sequences())
        self.assertEqual(first, analyze_phase_sequences(load_sequences()))
        self.assertEqual("4528044", first["market_identity"]["market_id"])
        self.assertEqual(["early", "middle", "late"], list(first["phases"]))
        self.assertTrue(all(item["sample_count"] == 12 for item in first["phases"].values()))
        self.assertTrue(all(item["execution_metadata_stable"] for item in first["phases"].values()))
        up = next(item for item in first["cross_phase_outcomes"].values() if item["outcome"] == "Up")
        self.assertIsNotNone(up["displacement_from_early"]["middle"])
        self.assertIsNone(up["displacement_from_early"]["late"])
        self.assertEqual(64, len(first["analysis_sha256"]))

    def test_missing_phase_is_rejected_without_imputation(self):
        sequences = load_sequences()
        sequences.pop("middle")
        with self.assertRaisesRegex(ContractError, "exact early, middle, and late"):
            analyze_phase_sequences(sequences)


if __name__ == "__main__":
    unittest.main()
