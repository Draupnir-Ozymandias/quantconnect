from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import qcrl_campaign


MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "campaigns"
    / "btcusd_1d_baseline_2022_2025.json"
)


class CampaignRunnerTests(unittest.TestCase):
    def setUp(self):
        self.manifest = qcrl_campaign.load_manifest(MANIFEST_PATH)
        self.cases = qcrl_campaign.expand_cases(self.manifest)

    def test_directional_stage1_manifest_is_flat_and_factor_isolated(self):
        manifest = qcrl_campaign.load_manifest(
            Path(__file__).parents[1]
            / "campaigns"
            / "btcusd_1d_directional_stage1_2022_2025.json"
        )
        cases = qcrl_campaign.expand_cases(manifest)

        self.assertEqual(16, len(cases))
        self.assertEqual(
            {"flat"},
            {case["parameters"]["stake_mode"] for case in cases}
        )
        self.assertEqual(
            {"none"},
            {case["parameters"]["filter_model"] for case in cases}
        )
        self.assertEqual(
            {
                "candle_streak",
                "ema_trend",
                "macd_trend",
                "rsi_mean_reversion"
            },
            {case["parameters"]["entry_model"] for case in cases}
        )

    def test_baseline_manifest_expands_to_four_pairs(self):
        self.assertEqual(8, len(self.cases))
        years = {case["parameters"]["start_year"] for case in self.cases}
        stakes = {case["parameters"]["stake_mode"] for case in self.cases}

        self.assertEqual({2022, 2023, 2024, 2025}, years)
        self.assertEqual({"flat", "martingale"}, stakes)
        self.assertEqual(8, len({case["case_id"] for case in self.cases}))

    def test_command_injects_provenance_and_sorted_parameters(self):
        command = qcrl_campaign.build_backtest_command(
            self.manifest, self.cases[0], "abc123", "main"
        )
        joined = " ".join(command)

        self.assertIn("lean cloud backtest 33239307", joined)
        self.assertIn("--parameter git_commit abc123", joined)
        self.assertIn("--parameter campaign_id btcusd-1d-baseline", joined)
        self.assertIn("--parameter stake_mode flat", joined)

    def test_extracts_nested_api_summary_statistics(self):
        payload = {
            "backtest": {
                "statistics": {
                    "QCRL Net Profit": "120.0",
                    "QCRL Ruined": "False",
                    "QCRL Trades": "58"
                }
            }
        }
        metrics = qcrl_campaign.extract_qcrl_metrics(payload)

        self.assertEqual(120, metrics["net_profit"])
        self.assertFalse(metrics["ruined"])
        self.assertEqual(58, metrics["trades"])

    def test_partial_terminal_metrics_are_not_collected(self):
        state = {
            "runs": {
                "case": {
                    "status": "collected",
                    "metrics": {"run_id": "run-1", "trades": 58}
                }
            }
        }

        qcrl_campaign.normalize_collection_status(self.manifest, state)

        self.assertEqual("completed", state["runs"]["case"]["status"])
        self.assertIn(
            "risk_adjusted_score",
            state["runs"]["case"]["collection_error"]
        )

    def test_rate_limit_detection_is_specific_to_throttle_output(self):
        self.assertTrue(qcrl_campaign.rate_limit_detected(
            "Error: Too many backtest requests; please slow down."
        ))
        self.assertTrue(qcrl_campaign.rate_limit_detected(
            "HTTP Error 429: Too Many Requests"
        ))
        self.assertFalse(qcrl_campaign.rate_limit_detected(
            "Successfully compiled project"
        ))

    def test_rate_backoff_doubles_and_caps(self):
        policy = qcrl_campaign.submission_policy(self.manifest)

        self.assertEqual(30, qcrl_campaign.rate_backoff_seconds(policy, 0))
        self.assertEqual(60, qcrl_campaign.rate_backoff_seconds(policy, 1))
        self.assertEqual(120, qcrl_campaign.rate_backoff_seconds(policy, 2))
        self.assertEqual(240, qcrl_campaign.rate_backoff_seconds(policy, 3))
        self.assertEqual(300, qcrl_campaign.rate_backoff_seconds(policy, 4))
        self.assertEqual(300, qcrl_campaign.rate_backoff_seconds(policy, 8))

    def test_submission_wait_respects_minimum_start_interval(self):
        self.assertEqual(
            20,
            qcrl_campaign.submission_wait_seconds(100, 110, 30)
        )
        self.assertEqual(
            0,
            qcrl_campaign.submission_wait_seconds(100, 135, 30)
        )
        self.assertEqual(
            0,
            qcrl_campaign.submission_wait_seconds(None, 110, 30)
        )

    def test_policy_supports_safe_manifest_and_cli_overrides(self):
        manifest = dict(self.manifest)
        manifest["submission_policy"] = {
            "min_interval_seconds": 45,
            "max_rate_retries": 5,
            "initial_backoff_seconds": 20,
            "max_backoff_seconds": 180
        }

        policy = qcrl_campaign.submission_policy(
            manifest,
            min_interval_seconds=60,
            max_rate_retries=2
        )

        self.assertEqual(60, policy["min_interval_seconds"])
        self.assertEqual(2, policy["max_rate_retries"])
        self.assertEqual(20, policy["initial_backoff_seconds"])
        self.assertEqual(180, policy["max_backoff_seconds"])

    def test_campaign_retries_rate_limit_then_records_success(self):
        rate_limit = "Error: Too many backtest requests; please slow down."
        success = (
            "Backtest url: https://www.quantconnect.com/project/33239307/"
            "959c6f2af8eb4844493cef66b907f56f"
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / ".qcrl" / "state.json"
            with (
                patch("qcrl_campaign.project_root", return_value=root),
                patch("qcrl_campaign.state_path", return_value=path),
                patch("qcrl_campaign.require_clean_tree"),
                patch("qcrl_campaign.git_value", side_effect=["abc", "main"]),
                patch("qcrl_campaign.wait_before_submission"),
                patch(
                    "qcrl_campaign.execute_backtest",
                    side_effect=[(1, rate_limit), (0, success)]
                ) as execute,
                patch("qcrl_campaign.time.sleep") as sleep
            ):
                with (
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO())
                ):
                    result = qcrl_campaign.run_campaign(
                        self.manifest,
                        self.cases[:1],
                        execute=True
                    )

            state = json.loads(path.read_text(encoding="utf-8"))
            run = state["runs"][self.cases[0]["case_id"]]

        self.assertEqual(0, result)
        self.assertEqual(2, execute.call_count)
        sleep.assert_called_once_with(30)
        self.assertEqual(2, run["attempts"])
        self.assertEqual(1, run["rate_limit_retries"])
        self.assertEqual("completed", run["status"])
        self.assertEqual(
            "959c6f2af8eb4844493cef66b907f56f",
            run["backtest_id"]
        )

    def test_campaign_does_not_retry_ordinary_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / ".qcrl" / "state.json"
            with (
                patch("qcrl_campaign.project_root", return_value=root),
                patch("qcrl_campaign.state_path", return_value=path),
                patch("qcrl_campaign.require_clean_tree"),
                patch("qcrl_campaign.git_value", side_effect=["abc", "main"]),
                patch("qcrl_campaign.wait_before_submission"),
                patch(
                    "qcrl_campaign.execute_backtest",
                    return_value=(1, "Compilation failed")
                ) as execute,
                patch("qcrl_campaign.time.sleep") as sleep
            ):
                with (
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO())
                ):
                    result = qcrl_campaign.run_campaign(
                        self.manifest,
                        self.cases[:1],
                        execute=True
                    )

            state = json.loads(path.read_text(encoding="utf-8"))
            run = state["runs"][self.cases[0]["case_id"]]

        self.assertEqual(1, result)
        self.assertEqual(1, execute.call_count)
        sleep.assert_not_called()
        self.assertEqual("failed", run["status"])
        self.assertEqual("lean_failure", run["error_type"])

    def test_parses_backtest_url(self):
        output = (
            "https://www.quantconnect.com/project/33239307/"
            "1c52783e44f28744737a541ecbe6829b"
        )
        backtest_id, url = qcrl_campaign.parse_backtest_reference(output)

        self.assertEqual("1c52783e44f28744737a541ecbe6829b", backtest_id)
        self.assertEqual(output, url)

    def test_pair_validation_accepts_matching_signal_metrics(self):
        invariant_fields = self.manifest["pair_validation"]["invariants"]
        metrics = {field: index for index, field in enumerate(invariant_fields)}
        for field in qcrl_campaign.required_metric_fields(self.manifest):
            metrics.setdefault(field, 1)
        metrics["ruined"] = False
        metrics["net_profit"] = 10
        metrics["max_drawdown"] = 5
        metrics["risk_adjusted_score"] = 0.5
        metrics["run_id"] = "test-run"

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            state = qcrl_campaign.load_state(self.manifest, self.cases)
            for run in state["runs"].values():
                run["status"] = "collected"
                run["metrics"] = dict(metrics)
            path.write_text(json.dumps(state), encoding="utf-8")

            with patch("qcrl_campaign.state_path", return_value=path):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = qcrl_campaign.validate_campaign(
                        self.manifest, self.cases
                    )
                artifact = json.loads(
                    (path.parent / "paired_comparison.json").read_text(
                        encoding="utf-8"
                    )
                )
                stability_output = io.StringIO()
                with redirect_stdout(stability_output):
                    stability_result = qcrl_campaign.run_stability(
                        self.manifest, self.cases
                    )
                stability = json.loads(
                    (path.parent / "stability_report.json").read_text(
                        encoding="utf-8"
                    )
                )

        self.assertEqual(0, result)
        self.assertIn("Flat signal ranking", output.getvalue())
        self.assertIn("Martingale capital ranking", output.getvalue())
        self.assertIn("Paired capital transformation", output.getvalue())
        self.assertNotIn("Ranking by risk_adjusted_score", output.getvalue())
        self.assertEqual("qcrl.paired_comparison.v1", artifact["schema_version"])
        self.assertEqual(4, len(artifact["pairs"]))
        self.assertTrue(artifact["validation"]["valid"])
        self.assertEqual(0, stability_result)
        self.assertIn("Evidence status", stability_output.getvalue())
        self.assertIn("Comparative verdict", stability_output.getvalue())
        self.assertEqual("qcrl.stability_report.v1", stability["schema_version"])
        self.assertIn("comparative_interpretation", stability)

    def test_cohort_scores_use_distinct_risk_models(self):
        flat = {
            "metrics": {
                "net_profit": 120,
                "max_drawdown": 50,
                "ruined": False
            }
        }
        martingale = {
            "metrics": {
                "risk_adjusted_score": 0.1875,
                "ruined": False
            }
        }

        self.assertAlmostEqual(
            120 / 51,
            qcrl_campaign.cohort_score("flat_profit_drawdown", flat)
        )
        self.assertEqual(
            0.1875,
            qcrl_campaign.cohort_score(
                "martingale_recovery_risk", martingale
            )
        )

    def test_pair_comparison_quantifies_capital_transformation(self):
        flat = dict(self.cases[0])
        martingale = dict(self.cases[1])
        flat["metrics"] = {
            "net_profit": -50,
            "win_rate": 33 / 71,
            "trades": 71,
            "max_drawdown": 150,
            "max_single_wager": 10,
            "max_recovery_depth": 6,
            "max_loss_streak": 6,
            "risk_adjusted_score": -0.0473,
            "ruined": False
        }
        martingale["metrics"] = {
            "net_profit": 330,
            "win_rate": 33 / 71,
            "trades": 71,
            "max_drawdown": 630,
            "max_single_wager": 640,
            "max_recovery_depth": 6,
            "max_loss_streak": 6,
            "risk_adjusted_score": 0.0747,
            "ruined": False
        }

        comparisons = qcrl_campaign.build_pair_comparisons(
            self.manifest, [flat, martingale]
        )

        self.assertEqual(1, len(comparisons))
        comparison = comparisons[0]
        self.assertEqual(2022, comparison["label"])
        self.assertEqual(380, comparison["deltas"]["net_profit"])
        self.assertEqual(
            4.2, comparison["deltas"]["drawdown_amplification"]
        )
        self.assertEqual(
            64, comparison["deltas"]["max_wager_multiple_of_base"]
        )
        self.assertEqual(
            "recovery-dependent-profit",
            comparison["interpretation"]["capital_transform"]
        )

    def test_analysis_revision_preserves_existing_case_state(self):
        previous = json.loads(json.dumps(self.manifest))
        previous.pop("cohort_rankings")
        previous["objective"] = {
            "field": "risk_adjusted_score",
            "direction": "max"
        }

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            with patch("qcrl_campaign.state_path", return_value=path):
                old_state = qcrl_campaign.load_state(previous, self.cases)
                qcrl_campaign.write_json(path, old_state)
                revised = qcrl_campaign.load_state(
                    self.manifest, self.cases
                )

        self.assertEqual(
            qcrl_campaign.case_set_hash(self.cases),
            revised["case_set_hash"]
        )
        self.assertEqual(1, len(revised["manifest_revisions"]))

    def test_case_revision_requires_a_new_campaign_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            with patch("qcrl_campaign.state_path", return_value=path):
                state = qcrl_campaign.load_state(self.manifest, self.cases)
                qcrl_campaign.write_json(path, state)

                changed = json.loads(json.dumps(self.manifest))
                changed["base_parameters"]["streak_length"] = 3
                changed_cases = qcrl_campaign.expand_cases(changed)

                with self.assertRaises(qcrl_campaign.CampaignError):
                    qcrl_campaign.load_state(changed, changed_cases)

    def test_duplicate_expansion_is_rejected(self):
        manifest = dict(self.manifest)
        manifest["variants"] = [
            {"start_year": 2024, "end_year": 2024},
            {"start_year": 2024, "end_year": 2024}
        ]

        with self.assertRaises(qcrl_campaign.CampaignError):
            qcrl_campaign.expand_cases(manifest)


if __name__ == "__main__":
    unittest.main()
