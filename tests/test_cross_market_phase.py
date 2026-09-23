import json
from pathlib import Path
import unittest

from execution_truth import ContractError, analyze_cross_market_phases


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "execution_truth" / "specs" / "cross_market_phase_daily_20260915_20260922.json"


def load_markets():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    return {
        label: {
            phase: (
                json.loads((SPEC.parent / path).resolve().read_text(encoding="utf-8"))
                if path is not None else None
            )
            for phase, path in phases.items()
        }
        for label, phases in spec["markets"].items()
    }


class CrossMarketPhaseTests(unittest.TestCase):
    def test_live_cross_market_analysis_is_deterministic_and_coverage_aware(self):
        first = analyze_cross_market_phases(load_markets())
        self.assertEqual(first, analyze_cross_market_phases(load_markets()))
        reordered = dict(reversed(list(load_markets().items())))
        self.assertEqual(first, analyze_cross_market_phases(reordered))
        self.assertEqual(4, first["coverage"]["market_count"])
        self.assertEqual(2, first["coverage"]["complete_market_count"])
        self.assertEqual(2, first["coverage"]["partial_market_count"])
        self.assertEqual(10, first["coverage"]["available_sequence_count"])
        self.assertEqual(
            {"early": 4, "middle": 2, "late": 4},
            first["coverage"]["phase_market_counts"],
        )
        self.assertEqual(
            {"2026-09-20": ["middle"], "2026-09-22": ["middle"]},
            first["coverage"]["missing_phases_by_market"],
        )
        self.assertEqual(
            ["2026-09-18"],
            first["phase_aggregates"]["late"]["cadence_warning_markets"],
        )
        self.assertEqual(3, first["descriptive_findings"]["late_directional_extreme_market_count"])
        self.assertEqual(64, len(first["analysis_sha256"]))

    def test_less_than_two_complete_markets_is_rejected(self):
        markets = load_markets()
        markets["2026-09-18"]["middle"] = None
        with self.assertRaisesRegex(ContractError, "at least two complete markets"):
            analyze_cross_market_phases(markets)

    def test_duplicate_market_is_rejected(self):
        markets = load_markets()
        markets["duplicate"] = dict(markets["2026-09-15"])
        with self.assertRaisesRegex(ContractError, "duplicate market"):
            analyze_cross_market_phases(markets)

    def test_missing_phase_key_is_rejected_without_imputation(self):
        markets = load_markets()
        markets["2026-09-20"].pop("middle")
        with self.assertRaisesRegex(ContractError, "exact early, middle, and late keys"):
            analyze_cross_market_phases(markets)


if __name__ == "__main__":
    unittest.main()
