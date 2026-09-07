"""Adjudicate historical temporal persistence against locked forward evidence."""

import math


class TemporalBridgeError(RuntimeError):
    pass


class TemporalBridgeEngine:
    INPUT_SCHEMA_VERSION = "qcrl.temporal_bridge_evidence.v1"
    REPORT_SCHEMA_VERSION = "qcrl.temporal_bridge_report.v1"

    @staticmethod
    def _normal_interval(wins, trades):
        if not trades:
            return [0.0, 0.0]
        rate = wins / trades
        margin = 1.96 * math.sqrt(rate * (1 - rate) / trades)
        return [max(0.0, rate - margin), min(1.0, rate + margin)]

    def analyze(self, evidence):
        if evidence.get("schema_version") != self.INPUT_SCHEMA_VERSION:
            raise TemporalBridgeError("Unsupported temporal bridge schema")
        historical = evidence.get("historical", {})
        forward = evidence.get("forward", {})
        thresholds = evidence.get("thresholds", {})
        for source, fields in [
            (historical, ["classification", "trades", "wins", "win_rate", "net_profit"]),
            (forward, ["classification", "trades", "wins", "win_rate", "net_profit"])
        ]:
            missing = set(fields) - set(source)
            if missing:
                raise TemporalBridgeError(
                    "Temporal bridge source lacks: " + ", ".join(sorted(missing))
                )

        historical_trades = int(historical["trades"])
        forward_trades = int(forward["trades"])
        historical_wins = int(historical["wins"])
        forward_wins = int(forward["wins"])
        historical_rate = historical_wins / historical_trades
        forward_rate = forward_wins / forward_trades if forward_trades else 0.0
        if abs(historical_rate - float(historical["win_rate"])) > 1e-9:
            raise TemporalBridgeError("Historical win-rate accounting drift")
        if abs(forward_rate - float(forward["win_rate"])) > 1e-9:
            raise TemporalBridgeError("Forward win-rate accounting drift")
        pooled_rate = (historical_wins + forward_wins) / (
            historical_trades + forward_trades
        )
        difference_error = math.sqrt(
            pooled_rate * (1 - pooled_rate)
            * (1 / historical_trades + 1 / forward_trades)
        ) if forward_trades else 0.0
        z_score = (
            (forward_rate - historical_rate) / difference_error
            if difference_error else 0.0
        )
        checks = {
            "historical_gate_persistent": historical["classification"] == "persistent",
            "forward_sample_sufficient": forward_trades >= int(thresholds["minimum_forward_trades"]),
            "forward_profit_positive": float(forward["net_profit"]) > 0,
            "forward_win_rate_sufficient": forward_rate >= float(thresholds["minimum_forward_win_rate"]),
            "historical_forward_drop_tolerable": historical_rate - forward_rate <= float(thresholds["maximum_historical_forward_win_rate_drop"])
        }
        if not checks["historical_gate_persistent"]:
            classification = "historically_fragile"
            decision = "reject_feature_optimization"
            next_action = "redesign_signal_without_indicator_optimization"
        elif not checks["forward_sample_sufficient"]:
            classification = "forward_inconclusive"
            decision = "hold_feature_optimization"
            next_action = "collect_locked_prospective_baseline"
        elif all(checks.values()):
            classification = "forward_corroborated"
            decision = "advance_to_execution_realism"
            next_action = "model_target_market_execution_and_costs"
        else:
            classification = "forward_degraded"
            decision = "hold_feature_optimization"
            next_action = "collect_locked_prospective_2026q4_baseline"

        return {
            "schema_version": self.REPORT_SCHEMA_VERSION,
            "synthesis_id": evidence["synthesis_id"],
            "evidence_role": "historical_forward_signal_adjudication",
            "historical": historical,
            "forward": forward,
            "comparison": {
                "win_rate_change": forward_rate - historical_rate,
                "approximate_two_sided_p_value": math.erfc(abs(z_score) / math.sqrt(2)),
                "pooled_z_score": z_score,
                "historical_win_rate_95_interval": self._normal_interval(
                    historical_wins, historical_trades
                ),
                "forward_win_rate_95_interval": self._normal_interval(
                    forward_wins, forward_trades
                )
            },
            "thresholds": thresholds,
            "checks": checks,
            "classification": classification,
            "decision": decision,
            "next_action": next_action,
            "declared_followups": evidence.get("declared_followups", {}),
            "limitations": evidence.get("limitations", [])
        }
