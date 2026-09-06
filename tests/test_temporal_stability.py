from pathlib import Path
import unittest

import qcrl_campaign
from qcrl_temporal import QcrlTemporalError, build_temporal_artifact
from discovery.temporal_stability_engine import TemporalStabilityEngine


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "campaigns" / "btcusd_1d_candle_streak_temporal_audit_2018_2025.json"


class TemporalStabilityTests(unittest.TestCase):
    def setUp(self):
        self.manifest = qcrl_campaign.load_manifest(MANIFEST)
        self.cases = qcrl_campaign.expand_cases(self.manifest)

    def test_manifest_declares_exact_nonoverlapping_quarters(self):
        self.assertEqual(32, len(self.cases))
        samples = [case["parameters"]["run_notes"] for case in self.cases]
        self.assertEqual(self.manifest["temporal_analysis"]["expected_samples"], samples)
        self.assertEqual(32, len(set(samples)))
        for case in self.cases:
            parameters = case["parameters"]
            start = tuple(parameters[f"start_{part}"] for part in ["year", "month", "day"])
            evaluation = tuple(parameters[f"evaluation_start_{part}"] for part in ["year", "month", "day"])
            self.assertLess(start, evaluation)
            self.assertEqual("none", parameters["filter_model"])
            self.assertEqual("none", parameters["regime_model"])
            self.assertEqual("flat", parameters["stake_mode"])

    def _state(self, profit=60, win_rate=0.6, trades=30, wins=18):
        state = {"case_set_hash": qcrl_campaign.case_set_hash(self.cases), "runs": {}}
        for case in self.cases:
            state["runs"][case["case_id"]] = {
                "status": "collected",
                "metrics_source": "quantconnect_api",
                "collected_at_utc": "2026-09-06T12:00:00Z",
                "metrics": {
                    "run_id": "run-" + case["case_id"],
                    "net_profit": profit,
                    "win_rate": win_rate,
                    "trades": trades,
                    "wins": wins,
                    "bars_seen": 90,
                    "max_drawdown": 30,
                    "max_loss_streak": 5,
                    "ruined": False
                }
            }
        return state

    def test_persistent_signal_passes_predeclared_gate(self):
        artifact = build_temporal_artifact(self.manifest, self.cases, self._state())
        report = TemporalStabilityEngine().analyze(artifact)
        self.assertEqual("persistent", report["verdict"]["classification"])
        self.assertEqual(29, len(report["rolling_four_quarter"]["windows"]))
        self.assertAlmostEqual(0.2, report["aggregate"]["break_even_cost_base_wager_pct"])
        self.assertTrue(all(report["checks"].values()))

    def test_unprofitable_signal_is_rejected_as_fragile(self):
        artifact = build_temporal_artifact(
            self.manifest, self.cases,
            self._state(profit=-20, win_rate=14 / 30, wins=14)
        )
        report = TemporalStabilityEngine().analyze(artifact)
        self.assertEqual("fragile", report["verdict"]["classification"])
        self.assertFalse(report["checks"]["weighted_win_rate"])
        self.assertFalse(report["checks"]["break_even_friction"])

    def test_artifact_rejects_non_api_evidence(self):
        state = self._state()
        first = self.cases[0]["case_id"]
        state["runs"][first]["metrics_source"] = "lean_cli"
        with self.assertRaisesRegex(QcrlTemporalError, "authoritative API"):
            build_temporal_artifact(self.manifest, self.cases, state)

    def test_artifact_rejects_flat_profit_accounting_drift(self):
        state = self._state()
        first = self.cases[0]["case_id"]
        state["runs"][first]["metrics"]["net_profit"] = 61
        with self.assertRaisesRegex(QcrlTemporalError, "flat-profit accounting drift"):
            build_temporal_artifact(self.manifest, self.cases, state)

    def test_parser_accepts_temporal_command(self):
        args = qcrl_campaign.build_parser().parse_args(["temporal", str(MANIFEST)])
        self.assertEqual("temporal", args.command)


if __name__ == "__main__":
    unittest.main()
