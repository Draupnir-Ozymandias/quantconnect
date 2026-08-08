import unittest

from discovery.stability_engine import StabilityEngine, StabilityError


def paired_artifact(expected_labels=None):
    years = [2022, 2023, 2024, 2025]
    flat_profit = [-50, 0, 70, 120]
    martingale_profit = [330, 270, 300, 350]
    win_rates = [33 / 71, 0.5, 30 / 53, 35 / 58]
    trades = [71, 54, 53, 58]
    flat_drawdown = [150, 90, 60, 50]
    martingale_drawdown = [630, 150, 150, 310]
    wager_multiples = [64, 16, 16, 32]
    recovery_depth = [6, 4, 4, 5]
    loss_streak = [6, 4, 4, 5]
    labels = [
        "recovery-dependent-profit",
        "recovery-dependent-profit",
        "signal-supported-profit-amplification",
        "signal-supported-profit-amplification"
    ]
    pairs = []
    for index, year in enumerate(years):
        pairs.append({
            "label": year,
            "baseline_case_id": f"{year}-flat",
            "comparison_case_id": f"{year}-martingale",
            "baseline_run_id": f"run-{year}-flat",
            "comparison_run_id": f"run-{year}-martingale",
            "signal_invariants_match": True,
            "signal": {
                "trades": trades[index],
                "win_rate": win_rates[index],
                "max_loss_streak": loss_streak[index]
            },
            "baseline": {
                "net_profit": flat_profit[index],
                "max_drawdown": flat_drawdown[index],
                "drawdown_in_base_wagers": flat_drawdown[index] / 10
            },
            "comparison": {
                "net_profit": martingale_profit[index],
                "max_drawdown": martingale_drawdown[index],
                "max_recovery_depth": recovery_depth[index],
                "ruined": False
            },
            "deltas": {
                "net_profit": martingale_profit[index] - flat_profit[index],
                "drawdown_amplification": (
                    martingale_drawdown[index] / flat_drawdown[index]
                ),
                "max_wager_multiple_of_base": wager_multiples[index]
            },
            "interpretation": {
                "capital_transform": labels[index]
            }
        })
    return {
        "schema_version": "qcrl.paired_comparison.v1",
        "campaign_id": "baseline",
        "case_set_hash": "abc123",
        "expected_labels": expected_labels or years,
        "validation": {"valid": True, "pair_issue_count": 0},
        "pairs": pairs
    }


class StabilityEngineTests(unittest.TestCase):
    def test_clean_control_produces_separate_stability_results(self):
        report = StabilityEngine().analyze(paired_artifact())

        self.assertEqual("qcrl.stability_report.v1", report["schema_version"])
        self.assertEqual("validation_cohort_complete", report["evidence_status"])
        self.assertEqual(1.0, report["coverage"]["coverage_ratio"])
        self.assertEqual(2, report["flat_signal"]["profitable_years"])
        self.assertAlmostEqual(
            0.533568686026373,
            report["flat_signal"]["mean_win_rate"]
        )
        self.assertEqual(
            "fragile", report["flat_signal"]["classification"]
        )
        self.assertEqual(1.0, report["martingale_capital"]["survival_ratio"])
        self.assertEqual(
            0.5,
            report["martingale_capital"]["recovery_dependence_ratio"]
        )
        self.assertEqual(
            64, report["martingale_capital"]["worst_max_wager_multiple"]
        )
        self.assertEqual(
            "fragile", report["martingale_capital"]["classification"]
        )
        self.assertTrue(
            report["paired_evidence"]["all_signal_invariants_match"]
        )
        self.assertEqual(8, len(report["supporting_run_ids"]))

    def test_incomplete_expected_coverage_is_penalized(self):
        report = StabilityEngine().analyze(
            paired_artifact([2022, 2023, 2024, 2025, 2026])
        )

        self.assertEqual("incomplete", report["evidence_status"])
        self.assertEqual([2026], report["coverage"]["missing_labels"])
        self.assertEqual(0.8, report["coverage"]["coverage_ratio"])
        self.assertIn(
            "incomplete_expected_label_coverage", report["warnings"]
        )

    def test_recovery_and_regime_warnings_are_explicit(self):
        warnings = StabilityEngine().analyze(paired_artifact())["warnings"]

        self.assertIn(
            "flat_profit_not_consistent_across_samples", warnings
        )
        self.assertIn("flat_win_rate_regime_variation", warnings)
        self.assertIn(
            "martingale_profit_depends_on_recovery_sizing", warnings
        )
        self.assertIn("martingale_extreme_wager_escalation", warnings)
        self.assertIn(
            "terminal_loss_exposure_metrics_unavailable", warnings
        )

    def test_wrong_artifact_schema_is_rejected(self):
        artifact = paired_artifact()
        artifact["schema_version"] = "unknown"

        with self.assertRaises(StabilityError):
            StabilityEngine().analyze(artifact)


if __name__ == "__main__":
    unittest.main()
