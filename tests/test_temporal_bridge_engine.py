import copy
import unittest

from discovery.temporal_bridge_engine import (
    TemporalBridgeEngine, TemporalBridgeError
)


def evidence():
    return {
        "schema_version": "qcrl.temporal_bridge_evidence.v1",
        "synthesis_id": "bridge-test-v1",
        "historical": {
            "classification": "persistent",
            "trades": 1000,
            "wins": 550,
            "win_rate": 0.55,
            "net_profit": 1000
        },
        "forward": {
            "classification": "mixed",
            "trades": 200,
            "wins": 108,
            "win_rate": 0.54,
            "net_profit": 160
        },
        "thresholds": {
            "minimum_forward_trades": 100,
            "minimum_forward_win_rate": 0.52,
            "maximum_historical_forward_win_rate_drop": 0.03
        }
    }


class TemporalBridgeEngineTests(unittest.TestCase):
    def test_forward_corroboration_advances_only_to_execution_realism(self):
        report = TemporalBridgeEngine().analyze(evidence())
        self.assertEqual("forward_corroborated", report["classification"])
        self.assertEqual("advance_to_execution_realism", report["decision"])
        self.assertTrue(all(report["checks"].values()))

    def test_forward_degradation_holds_feature_optimization(self):
        value = evidence()
        value["forward"].update({
            "wins": 94, "win_rate": 0.47, "net_profit": -120
        })
        report = TemporalBridgeEngine().analyze(value)
        self.assertEqual("forward_degraded", report["classification"])
        self.assertEqual("hold_feature_optimization", report["decision"])
        self.assertFalse(report["checks"]["forward_profit_positive"])

    def test_undersized_forward_sample_remains_inconclusive(self):
        value = evidence()
        value["forward"].update({
            "trades": 50, "wins": 28, "win_rate": 0.56, "net_profit": 60
        })
        report = TemporalBridgeEngine().analyze(value)
        self.assertEqual("forward_inconclusive", report["classification"])

    def test_wrong_schema_is_rejected(self):
        value = copy.deepcopy(evidence())
        value["schema_version"] = "wrong"
        with self.assertRaisesRegex(TemporalBridgeError, "Unsupported"):
            TemporalBridgeEngine().analyze(value)


if __name__ == "__main__":
    unittest.main()
