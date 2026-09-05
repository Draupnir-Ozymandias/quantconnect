import unittest

from discovery.directional_cohort_engine import (
    DirectionalCohortEngine,
    DirectionalCohortError
)


RESULTS = {
    "candle_streak": {
        "profits": [120, 70, 90, 210],
        "wins": [95, 86, 88, 100],
        "trades": [178, 165, 167, 179],
        "drawdowns": [150, 80, 130, 50],
        "loss_streaks": [6, 6, 6, 5]
    },
    "ema_trend": {
        "profits": [-250, -130, 0, -30],
        "wins": [165, 171, 178, 176],
        "trades": [355, 355, 356, 355],
        "drawdowns": [310, 310, 270, 130],
        "loss_streaks": [10, 10, 8, 11]
    },
    "macd_trend": {
        "profits": [-230, -90, 40, 30],
        "wins": [154, 161, 168, 167],
        "trades": [331, 331, 332, 331],
        "drawdowns": [370, 250, 180, 160],
        "loss_streaks": [10, 7, 9, 8]
    },
    "rsi_mean_reversion": {
        "profits": [70, 60, -110, 50],
        "wins": [21, 44, 22, 16],
        "trades": [35, 82, 55, 27],
        "drawdowns": [40, 100, 120, 30],
        "loss_streaks": [4, 5, 5, 3]
    }
}


def directional_artifact():
    years = [2022, 2023, 2024, 2025]
    cohorts = []
    for model, values in RESULTS.items():
        records = []
        for index, year in enumerate(years):
            trades = values["trades"][index]
            wins = values["wins"][index]
            drawdown = values["drawdowns"][index]
            records.append({
                "label": year,
                "case_id": f"{year}-{model}",
                "run_id": f"run-{year}-{model}",
                "net_profit": values["profits"][index],
                "win_rate": wins / trades,
                "trades": trades,
                "wins": wins,
                "max_drawdown": drawdown,
                "max_loss_streak": values["loss_streaks"][index],
                "ruined": False,
                "base_wager": 10,
                "drawdown_in_base_wagers": drawdown / 10
            })
        cohorts.append({"group_key": model, "records": records})
    return {
        "schema_version": "qcrl.directional_cohort.v1",
        "campaign_id": "directional-stage1",
        "case_set_hash": "abc123",
        "group_field": "entry_model",
        "label_field": "start_year",
        "expected_labels": years,
        "validation": {"valid": True, "issue_count": 0, "issues": []},
        "cohorts": cohorts
    }


class DirectionalCohortEngineTests(unittest.TestCase):
    def test_real_stage1_shape_produces_family_decisions(self):
        report = DirectionalCohortEngine().analyze(directional_artifact())
        cohorts = {
            cohort["group_key"]: cohort for cohort in report["cohorts"]
        }

        self.assertEqual(
            "qcrl.directional_cohort_report.v1",
            report["schema_version"]
        )
        self.assertEqual(
            "qcrl.directional_cohort_score.v2",
            report["score_version"]
        )
        self.assertEqual(0.30, report["score_weights"][
            "profitable_sample_ratio"
        ])
        self.assertEqual("candle_streak", report["cohorts"][0]["group_key"])
        self.assertEqual("hold", cohorts["candle_streak"]["disposition"])
        self.assertEqual(4, cohorts["candle_streak"]["profitable_samples"])
        self.assertEqual("reject", cohorts["ema_trend"]["disposition"])
        self.assertEqual("reject", cohorts["macd_trend"]["disposition"])
        self.assertEqual(
            "run_parameter_neighborhood_validation",
            report["decision_summary"]["next_action"]
        )

    def test_incomplete_cohort_is_held_for_more_evidence(self):
        artifact = directional_artifact()
        artifact["cohorts"] = [artifact["cohorts"][0]]
        artifact["cohorts"][0]["records"].pop()

        cohort = DirectionalCohortEngine().analyze(artifact)["cohorts"][0]

        self.assertEqual("hold", cohort["disposition"])
        self.assertEqual([2025], cohort["coverage"]["missing_labels"])
        self.assertIn(
            "incomplete_expected_label_coverage", cohort["warnings"]
        )

    def test_wrong_schema_is_rejected(self):
        artifact = directional_artifact()
        artifact["schema_version"] = "unknown"

        with self.assertRaises(DirectionalCohortError):
            DirectionalCohortEngine().analyze(artifact)

    def test_ruin_forces_rejection(self):
        artifact = directional_artifact()
        artifact["cohorts"] = [artifact["cohorts"][0]]
        artifact["cohorts"][0]["records"][0]["ruined"] = True

        cohort = DirectionalCohortEngine().analyze(artifact)["cohorts"][0]

        self.assertEqual("reject", cohort["disposition"])
        self.assertEqual(100, cohort["risk_penalty"])
        self.assertIn("cohort_ruin_observed", cohort["warnings"])

    def test_sparse_cohort_is_held_even_when_score_is_attractive(self):
        artifact = directional_artifact()
        artifact["cohorts"] = [artifact["cohorts"][0]]
        for record in artifact["cohorts"][0]["records"]:
            record["trades"] = 10
            record["wins"] = 7
            record["win_rate"] = 0.7
            record["net_profit"] = 40

        cohort = DirectionalCohortEngine().analyze(artifact)["cohorts"][0]

        self.assertEqual("hold", cohort["disposition"])
        self.assertFalse(cohort["sample_size_sufficient"])
        self.assertEqual("expand_sparse_signal_evidence", cohort["next_action"])
        self.assertIn("insufficient_total_trades", cohort["warnings"])


if __name__ == "__main__":
    unittest.main()
