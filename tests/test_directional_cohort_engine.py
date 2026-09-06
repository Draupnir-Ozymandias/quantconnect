import copy
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


def neighborhood_artifact():
    source = directional_artifact()["cohorts"][0]["records"]
    settings = {
        1: ([20, 20, 20, 20], 150),
        2: ([30, 30, 30, 30], 50),
        3: ([10, 10, 10, -5], 160)
    }
    cohorts = []
    for length, (profits, drawdown) in settings.items():
        records = copy.deepcopy(source)
        for index, record in enumerate(records):
            record["case_id"] = f"{record['label']}-length-{length}"
            record["run_id"] = f"run-{record['label']}-length-{length}"
            record["net_profit"] = profits[index]
            record["max_drawdown"] = drawdown
            record["drawdown_in_base_wagers"] = drawdown / 10
        cohorts.append({"group_key": length, "records": records})
    return {
        "schema_version": "qcrl.directional_cohort.v1",
        "campaign_id": "streak-neighborhood",
        "case_set_hash": "neighborhood123",
        "analysis_stage": "parameter_neighborhood",
        "group_field": "streak_length",
        "label_field": "start_year",
        "candidate_value": 2,
        "core_values": [1, 2, 3],
        "tail_values": [],
        "expected_labels": [2022, 2023, 2024, 2025],
        "validation": {"valid": True, "issue_count": 0, "issues": []},
        "cohorts": cohorts
    }


def single_gate_artifact():
    source = directional_artifact()["cohorts"][0]["records"]
    settings = {
        "none": {
            "profits": [120, 70, 90, 210],
            "wins": [95, 86, 88, 100],
            "trades": [178, 165, 167, 179],
            "drawdowns": [150, 80, 130, 50],
            "loss_streaks": [6, 6, 6, 5]
        },
        "adx_strength": {
            "profits": [-20, 60, 40, 130],
            "wins": [35, 52, 35, 45],
            "trades": [72, 98, 66, 77],
            "drawdowns": [100, 60, 50, 30],
            "loss_streaks": [5, 5, 4, 3]
        },
        "atr_volatility": {
            "profits": [130, 120, 70, 240],
            "wins": [92, 84, 85, 97],
            "trades": [171, 156, 163, 170],
            "drawdowns": [150, 60, 130, 50],
            "loss_streaks": [6, 6, 6, 5]
        }
    }
    cohorts = []
    for gate, values in settings.items():
        records = copy.deepcopy(source)
        for index, record in enumerate(records):
            trades = values["trades"][index]
            wins = values["wins"][index]
            drawdown = values["drawdowns"][index]
            record.update({
                "case_id": f"{record['label']}-{gate}",
                "run_id": f"run-{record['label']}-{gate}",
                "net_profit": values["profits"][index],
                "wins": wins,
                "trades": trades,
                "win_rate": wins / trades,
                "max_drawdown": drawdown,
                "drawdown_in_base_wagers": drawdown / 10,
                "max_loss_streak": values["loss_streaks"][index],
                "skipped_filter_not_ready": 0 if gate == "none" else 7,
                "skipped_filter_rejected": 0 if gate == "none" else 3
            })
        cohorts.append({"group_key": gate, "records": records})
    return {
        "schema_version": "qcrl.directional_cohort.v1",
        "campaign_id": "single-gate",
        "case_set_hash": "gate123",
        "analysis_stage": "single_gate",
        "group_field": "filter_model",
        "label_field": "start_year",
        "control_value": "none",
        "candidate_values": ["adx_strength", "atr_volatility"],
        "additional_metrics": [
            "skipped_filter_not_ready", "skipped_filter_rejected"
        ],
        "expected_labels": [2022, 2023, 2024, 2025],
        "validation": {"valid": True, "issue_count": 0, "issues": []},
        "cohorts": cohorts
    }


def attribution_artifact():
    source = single_gate_artifact()
    by_key = {
        cohort["group_key"]: cohort for cohort in source["cohorts"]
    }
    control = copy.deepcopy(by_key["none"])
    diagnostic = copy.deepcopy(by_key["atr_volatility"])
    diagnostic["group_key"] = "atr_warmup_only"
    candidates = []
    for name in ["atr_lower_only", "atr_upper_only", "atr_default_1_10"]:
        cohort = copy.deepcopy(diagnostic)
        cohort["group_key"] = name
        for record in cohort["records"]:
            year = record["label"]
            record["case_id"] = f"{year}-{name}"
            record["run_id"] = f"run-{year}-{name}"
            record["skipped_filter_rejected"] = 0
        candidates.append(cohort)
    for record in diagnostic["records"]:
        year = record["label"]
        record["case_id"] = f"{year}-atr-warmup-only"
        record["run_id"] = f"run-{year}-atr-warmup-only"
        record["skipped_filter_rejected"] = 0
    return {
        "schema_version": "qcrl.directional_cohort.v1",
        "campaign_id": "atr-attribution",
        "case_set_hash": "attribution123",
        "analysis_stage": "gate_attribution",
        "group_field": "run_notes",
        "label_field": "start_year",
        "control_value": "none",
        "diagnostic_value": "atr_warmup_only",
        "candidate_values": [
            "atr_lower_only", "atr_upper_only", "atr_default_1_10"
        ],
        "additional_metrics": [
            "skipped_filter_not_ready", "skipped_filter_rejected"
        ],
        "expected_labels": [2022, 2023, 2024, 2025],
        "validation": {"valid": True, "issue_count": 0, "issues": []},
        "cohorts": [control, diagnostic, *candidates]
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

    def test_neighborhood_selects_best_candidate_with_two_sided_support(self):
        report = DirectionalCohortEngine().analyze(neighborhood_artifact())
        decision = report["neighborhood_interpretation"]

        self.assertEqual(
            "qcrl.directional_neighborhood_interpretation.v1",
            decision["schema_version"]
        )
        self.assertEqual("advance", decision["decision"])
        self.assertEqual(2, decision["selected_value"])
        self.assertEqual([1, 3], decision["supporting_values"])
        self.assertEqual(
            "advance_selected_candidate_to_single_gate_stage",
            report["decision_summary"]["next_action"]
        )
        self.assertEqual([2], report["decision_summary"]["selected_candidates"])

    def test_neighborhood_holds_candidate_without_upper_support(self):
        artifact = neighborhood_artifact()
        for record in artifact["cohorts"][2]["records"]:
            record["net_profit"] = -10

        report = DirectionalCohortEngine().analyze(artifact)
        decision = report["neighborhood_interpretation"]

        self.assertEqual("hold", decision["decision"])
        self.assertFalse(decision["upper_neighbor_support"])
        self.assertIn(
            "missing_two_sided_core_neighbor_support",
            decision["blockers"]
        )

    def test_single_gate_stage_requires_control_comparison(self):
        report = DirectionalCohortEngine().analyze(single_gate_artifact())
        interpretation = report["single_gate_interpretation"]
        comparisons = {
            item["candidate_value"]: item
            for item in interpretation["comparisons"]
        }

        self.assertEqual(
            "run_selected_gate_parameter_neighborhood",
            report["decision_summary"]["next_action"]
        )
        self.assertEqual(["atr_volatility"], interpretation["selected_candidates"])
        self.assertEqual("advance", comparisons["atr_volatility"]["decision"])
        self.assertEqual(70, comparisons["atr_volatility"]["total_net_profit_delta"])
        self.assertEqual(
            7,
            comparisons["atr_volatility"]["paired_labels"][0]
            ["additional_metrics"]["skipped_filter_not_ready"]["candidate"]
        )
        self.assertEqual("reject", comparisons["adx_strength"]["decision"])

    def test_attribution_rejects_inert_bounds_and_requests_telemetry(self):
        report = DirectionalCohortEngine().analyze(attribution_artifact())
        interpretation = report["gate_attribution_interpretation"]

        self.assertEqual(
            "qcrl.gate_attribution_interpretation.v1",
            interpretation["schema_version"]
        )
        self.assertEqual(28, interpretation["diagnostic_not_ready_total"])
        self.assertEqual(0, interpretation["diagnostic_rejected_total"])
        self.assertEqual([], interpretation["selected_candidates"])
        self.assertEqual(
            "collect_signal_time_filter_telemetry",
            report["decision_summary"]["next_action"]
        )
        for candidate in interpretation["candidates"]:
            self.assertEqual("no_incremental_effect", candidate["decision"])
            self.assertTrue(candidate["equivalent_to_diagnostic"])
            self.assertEqual(0, candidate["rejected_signal_total"])

    def test_attribution_judges_active_component_against_diagnostic(self):
        artifact = attribution_artifact()
        candidate = next(
            cohort for cohort in artifact["cohorts"]
            if cohort["group_key"] == "atr_lower_only"
        )
        for record in candidate["records"]:
            record["skipped_filter_rejected"] = 1

        report = DirectionalCohortEngine().analyze(artifact)
        interpretation = report["gate_attribution_interpretation"]
        result = next(
            item for item in interpretation["candidates"]
            if item["candidate_value"] == "atr_lower_only"
        )

        self.assertEqual("reject", result["decision"])
        self.assertEqual(
            "atr_warmup_only",
            result["diagnostic_comparison"]["control_value"]
        )
        self.assertEqual(
            0, result["diagnostic_comparison"]["total_net_profit_delta"]
        )
        self.assertEqual(4, result["rejected_signal_delta"])

    def test_attribution_rejects_an_all_rejected_candidate_field(self):
        artifact = attribution_artifact()
        for cohort in artifact["cohorts"]:
            if cohort["group_key"] in {
                "control", "atr_warmup_only"
            }:
                continue
            for record in cohort["records"]:
                record["skipped_filter_rejected"] = 1

        report = DirectionalCohortEngine().analyze(artifact)

        self.assertEqual(
            "reject_tested_active_gate_bounds",
            report["decision_summary"]["next_action"]
        )


if __name__ == "__main__":
    unittest.main()
