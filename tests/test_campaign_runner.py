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
        metrics["risk_adjusted_score"] = 1.0
        metrics["run_id"] = "test-run"

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            state = qcrl_campaign.load_state(self.manifest, self.cases)
            for run in state["runs"].values():
                run["status"] = "collected"
                run["metrics"] = dict(metrics)
            path.write_text(json.dumps(state), encoding="utf-8")

            with patch("qcrl_campaign.state_path", return_value=path):
                result = qcrl_campaign.validate_campaign(
                    self.manifest, self.cases
                )

        self.assertEqual(0, result)

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
