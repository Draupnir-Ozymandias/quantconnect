import copy
import unittest

from discovery.cross_regime_side_engine import (
    CrossRegimeSideEngine,
    CrossRegimeSideError
)


def _side(direction, years, profits, trades, wins, disposition):
    return {
        "direction": direction,
        "disposition": disposition,
        "total_net_profit": sum(profits),
        "total_trades": sum(trades),
        "total_wins": sum(wins),
        "profitable_samples": sum(value > 0 for value in profits),
        "run_count": len(profits),
        "annual_results": [
            {
                "label": year,
                "net_profit": profit,
                "trades": trade_count,
                "wins": win_count
            }
            for year, profit, trade_count, win_count in zip(
                years, profits, trades, wins
            )
        ]
    }


def evidence():
    configuration = {
        "entry_model": "candle_streak",
        "filter_model": "none",
        "stake_mode": "flat",
        "streak_length": 2,
        "streak_mode": "reverse"
    }
    early = {
        "schema_version": "qcrl.side_attribution_interpretation.v1",
        "evidence_role": "historical_regime_stress",
        "hypothesis_side": "down",
        "hypothesis_result": "inconclusive",
        "verdict": "up_dominant",
        "sides": [
            _side("up", range(2018, 2022), [130, 90, 200, 120],
                  [83, 83, 50, 76],
                  [48, 46, 35, 44], "supported"),
            _side("down", range(2018, 2022), [190, -110, -90, 130],
                  [81, 97, 103, 85],
                  [50, 43, 47, 49], "hold")
        ]
    }
    mature = {
        "schema_version": "qcrl.side_attribution_interpretation.v1",
        "verdict": "down_dominant",
        "sides": [
            _side("up", range(2022, 2026), [-100, -10, 170, 0],
                  [102, 85, 75, 90],
                  [46, 42, 46, 45], "reject"),
            _side("down", range(2022, 2026), [220, 80, -80, 210],
                  [76, 80, 92, 89],
                  [49, 44, 42, 55], "supported")
        ]
    }
    return {
        "schema_version": "qcrl.cross_regime_side_evidence.v1",
        "synthesis_id": "cross-regime-test-v1",
        "sources": [
            {
                "label": "early_adoption_2018_2021",
                "campaign_id": "early",
                "case_set_hash": "early-hash",
                "expected_labels": [2018, 2019, 2020, 2021],
                "required_parameters": configuration,
                "side_attribution": early
            },
            {
                "label": "maturing_market_2022_2025",
                "campaign_id": "mature",
                "case_set_hash": "mature-hash",
                "expected_labels": [2022, 2023, 2024, 2025],
                "required_parameters": copy.deepcopy(configuration),
                "side_attribution": mature
            }
        ]
    }


class CrossRegimeSideEngineTests(unittest.TestCase):
    def test_leadership_flip_rejects_static_side_restriction(self):
        report = CrossRegimeSideEngine().analyze(evidence())
        sides = {
            item["direction"]: item for item in report["pooled_sides"]
        }

        self.assertTrue(report["leadership_flip"])
        self.assertEqual("retain_both_directions", report["decision"])
        self.assertEqual("rejected", report["static_direction_restriction"])
        self.assertEqual(600, sides["up"]["total_net_profit"])
        self.assertEqual(644, sides["up"]["total_trades"])
        self.assertEqual(352 / 644, sides["up"]["weighted_win_rate"])
        self.assertEqual(550, sides["down"]["total_net_profit"])
        self.assertEqual(703, sides["down"]["total_trades"])
        self.assertEqual(379 / 703, sides["down"]["weighted_win_rate"])
        self.assertEqual(1150, report["pooled_total"]["net_profit"])
        self.assertEqual(1347, report["pooled_total"]["trades"])
        self.assertEqual(7, report["pooled_total"]["profitable_samples"])
        self.assertEqual(50, report["side_balance"]["absolute_profit_gap"])

    def test_mismatched_signal_configuration_is_rejected(self):
        value = evidence()
        value["sources"][1]["required_parameters"]["streak_length"] = 3
        with self.assertRaisesRegex(
            CrossRegimeSideError, "identical signal configuration"
        ):
            CrossRegimeSideEngine().analyze(value)

    def test_overlapping_periods_are_rejected(self):
        value = evidence()
        value["sources"][1]["expected_labels"][0] = 2021
        for side in value["sources"][1]["side_attribution"]["sides"]:
            side["annual_results"][0]["label"] = 2021
        with self.assertRaisesRegex(CrossRegimeSideError, "overlapping"):
            CrossRegimeSideEngine().analyze(value)


if __name__ == "__main__":
    unittest.main()
