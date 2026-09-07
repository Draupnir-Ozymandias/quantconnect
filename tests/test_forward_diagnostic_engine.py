import copy
import unittest

from discovery.forward_diagnostic_engine import (
    ForwardDiagnosticEngine, ForwardDiagnosticError
)


def _record(sample, trades, wins, up_profit, down_profit):
    return {
        "sample": sample,
        "base_wager": 10,
        "trades": trades,
        "wins": wins,
        "win_rate": wins / trades,
        "net_profit": (2 * wins - trades) * 10,
        "up_net_profit": up_profit,
        "down_net_profit": down_profit
    }


def evidence():
    records = [
        _record("Q1", 50, 19, -60, -60),
        _record("Q2", 48, 23, -40, 20),
        _record("JUL_AUG", 29, 17, 20, 30)
    ]
    return {
        "schema_version": "qcrl.forward_diagnostic_evidence.v1",
        "synthesis_id": "diagnostic-test-v1",
        "expected_samples": ["Q1", "Q2", "JUL_AUG"],
        "records": records,
        "locked_forward": {
            "trades": 128, "wins": 60, "win_rate": 60 / 128,
            "net_profit": -80
        },
        "thresholds": {"maximum_absolute_trade_count_drift": 3}
    }


class ForwardDiagnosticEngineTests(unittest.TestCase):
    def test_monotonic_recovery_remains_diagnostic_only(self):
        report = ForwardDiagnosticEngine().analyze(evidence())
        self.assertTrue(report["monotonic_recovery_pattern"])
        self.assertEqual(
            "early_2026_loss_concentration_with_later_recovery",
            report["localization"]
        )
        self.assertEqual(
            "diagnostic_only_hold_feature_optimization", report["decision"]
        )
        self.assertTrue(report["boundary_reconciliation"]["acceptable"])

    def test_nonmonotonic_path_is_not_called_recovery(self):
        value = evidence()
        value["records"][2] = _record("JUL_AUG", 30, 14, -10, -10)
        report = ForwardDiagnosticEngine().analyze(value)
        self.assertFalse(report["monotonic_recovery_pattern"])
        self.assertEqual("nonmonotonic_forward_degradation", report["localization"])

    def test_flat_profit_accounting_drift_is_rejected(self):
        value = copy.deepcopy(evidence())
        value["records"][0]["net_profit"] += 10
        with self.assertRaisesRegex(ForwardDiagnosticError, "flat-profit"):
            ForwardDiagnosticEngine().analyze(value)


if __name__ == "__main__":
    unittest.main()
