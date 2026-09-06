"""Deterministic temporal-persistence analysis for flat-signal campaigns."""

import math


class TemporalStabilityError(RuntimeError):
    pass


class TemporalStabilityEngine:
    SCHEMA_VERSION = "qcrl.temporal_stability_report.v1"

    @staticmethod
    def _ratio(numerator, denominator):
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _std(values):
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))

    def analyze(self, artifact):
        if artifact.get("schema_version") != "qcrl.temporal_audit.v1":
            raise TemporalStabilityError("Unsupported temporal audit schema")
        records = artifact.get("records", [])
        expected = artifact.get("expected_samples", [])
        if not records or len(records) != len(expected):
            raise TemporalStabilityError("Temporal audit coverage is incomplete")

        base_wager = float(artifact["base_wager"])
        thresholds = artifact["thresholds"]
        trades = sum(int(row["trades"]) for row in records)
        wins = sum(int(row["wins"]) for row in records)
        profit = sum(float(row["net_profit"]) for row in records)
        win_rates = [float(row["win_rate"]) for row in records]
        profitable = sum(float(row["net_profit"]) > 0 for row in records)

        rolling = []
        for index in range(len(records) - 3):
            window = records[index:index + 4]
            window_trades = sum(int(row["trades"]) for row in window)
            window_wins = sum(int(row["wins"]) for row in window)
            rolling.append({
                "start_sample": window[0]["sample"],
                "end_sample": window[-1]["sample"],
                "trades": window_trades,
                "wins": window_wins,
                "win_rate": self._ratio(window_wins, window_trades),
                "net_profit": sum(float(row["net_profit"]) for row in window)
            })

        positive_rolling = sum(row["net_profit"] > 0 for row in rolling)
        break_even = self._ratio(profit, trades * base_wager)
        friction = []
        for rate in artifact["friction_grid_base_wager_pct"]:
            rate = float(rate)
            adjusted = [
                float(row["net_profit"]) - int(row["trades"]) * base_wager * rate
                for row in records
            ]
            friction.append({
                "base_wager_pct": rate,
                "aggregate_net_profit": sum(adjusted),
                "profitable_sample_ratio": self._ratio(
                    sum(value > 0 for value in adjusted), len(adjusted)
                )
            })

        positive_profits = sorted(
            (max(0.0, float(row["net_profit"])) for row in records), reverse=True
        )
        positive_total = sum(positive_profits)
        concentration = {
            "top_one_positive_profit_share": self._ratio(
                sum(positive_profits[:1]), positive_total
            ),
            "top_four_positive_profit_share": self._ratio(
                sum(positive_profits[:4]), positive_total
            )
        }
        checks = {
            "complete_sample_coverage": len(records) >= int(thresholds["minimum_samples"]),
            "no_ruined_samples": not any(bool(row["ruined"]) for row in records),
            "minimum_trades_each_sample": min(int(row["trades"]) for row in records) >= int(thresholds["minimum_trades_per_sample"]),
            "profitable_sample_ratio": self._ratio(profitable, len(records)) >= float(thresholds["minimum_profitable_sample_ratio"]),
            "weighted_win_rate": self._ratio(wins, trades) >= float(thresholds["minimum_weighted_win_rate"]),
            "win_rate_dispersion": self._std(win_rates) <= float(thresholds["maximum_win_rate_std"]),
            "positive_rolling_four_quarter_ratio": self._ratio(positive_rolling, len(rolling)) >= float(thresholds["minimum_positive_rolling_four_quarter_ratio"]),
            "break_even_friction": break_even >= float(thresholds["minimum_break_even_cost_base_wager_pct"]),
            "maximum_loss_streak": max(int(row["max_loss_streak"]) for row in records) <= int(thresholds["maximum_loss_streak"]),
            "profit_concentration": concentration["top_four_positive_profit_share"] <= float(thresholds["maximum_top_four_positive_profit_share"])
        }
        all_checks_pass = all(checks.values())
        verdict = "persistent" if all_checks_pass else "fragile"
        return {
            "schema_version": self.SCHEMA_VERSION,
            "campaign_id": artifact["campaign_id"],
            "case_set_hash": artifact["case_set_hash"],
            "evidence_role": "historical_temporal_persistence_gate",
            "coverage": {
                "expected_count": len(expected),
                "present_count": len(records),
                "coverage_ratio": self._ratio(len(records), len(expected))
            },
            "aggregate": {
                "trades": trades,
                "wins": wins,
                "net_profit": profit,
                "weighted_win_rate": self._ratio(wins, trades),
                "profitable_samples": profitable,
                "profitable_sample_ratio": self._ratio(profitable, len(records)),
                "win_rate_mean": sum(win_rates) / len(win_rates),
                "win_rate_std": self._std(win_rates),
                "win_rate_min": min(win_rates),
                "win_rate_max": max(win_rates),
                "max_quarter_drawdown": max(float(row["max_drawdown"]) for row in records),
                "max_loss_streak": max(int(row["max_loss_streak"]) for row in records),
                "break_even_cost_base_wager_pct": break_even
            },
            "rolling_four_quarter": {
                "windows": rolling,
                "positive_count": positive_rolling,
                "positive_ratio": self._ratio(positive_rolling, len(rolling)),
                "worst_net_profit": min(row["net_profit"] for row in rolling)
            },
            "friction_capacity": friction,
            "profit_concentration": concentration,
            "thresholds": thresholds,
            "checks": checks,
            "verdict": {
                "classification": verdict,
                "decision": "advance" if all_checks_pass else "reject",
                "next_action": (
                    "compare_locked_forward_evidence_before_feature_work"
                    if all_checks_pass else
                    "redesign_signal_without_indicator_optimization"
                )
            },
            "limitations": artifact["limitations"]
        }
