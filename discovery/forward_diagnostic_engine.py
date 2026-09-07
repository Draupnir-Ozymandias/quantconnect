"""Localize an observed forward degradation without promoting a hypothesis."""


class ForwardDiagnosticError(RuntimeError):
    pass


class ForwardDiagnosticEngine:
    INPUT_SCHEMA_VERSION = "qcrl.forward_diagnostic_evidence.v1"
    REPORT_SCHEMA_VERSION = "qcrl.forward_diagnostic_report.v1"

    @staticmethod
    def _ratio(numerator, denominator):
        return numerator / denominator if denominator else 0.0

    def analyze(self, evidence):
        if evidence.get("schema_version") != self.INPUT_SCHEMA_VERSION:
            raise ForwardDiagnosticError("Unsupported forward diagnostic schema")
        records = evidence.get("records", [])
        expected = evidence.get("expected_samples", [])
        if [record.get("sample") for record in records] != expected:
            raise ForwardDiagnosticError("Diagnostic sample coverage or order differs")
        if len(records) < 2:
            raise ForwardDiagnosticError("At least two diagnostic segments are required")
        for record in records:
            trades = int(record["trades"])
            wins = int(record["wins"])
            if wins > trades or abs(
                self._ratio(wins, trades) - float(record["win_rate"])
            ) > 1e-9:
                raise ForwardDiagnosticError("Diagnostic win-rate accounting drift")
            if abs((2 * wins - trades) * float(record["base_wager"]) - float(
                record["net_profit"]
            )) > 1e-6:
                raise ForwardDiagnosticError("Diagnostic flat-profit accounting drift")

        trades = sum(int(record["trades"]) for record in records)
        wins = sum(int(record["wins"]) for record in records)
        profit = sum(float(record["net_profit"]) for record in records)
        locked = evidence["locked_forward"]
        drift = {
            "trades": trades - int(locked["trades"]),
            "wins": wins - int(locked["wins"]),
            "net_profit": profit - float(locked["net_profit"])
        }
        maximum_drift = int(evidence["thresholds"][
            "maximum_absolute_trade_count_drift"
        ])
        boundary_reconciliation = abs(drift["trades"]) <= maximum_drift

        negative_loss = sum(
            -min(0.0, float(record["net_profit"])) for record in records
        )
        segments = []
        for index, record in enumerate(records):
            previous = records[index - 1] if index else None
            segments.append({
                **record,
                "gross_loss_share": self._ratio(
                    -min(0.0, float(record["net_profit"])), negative_loss
                ),
                "win_rate_change_from_prior": (
                    float(record["win_rate"]) - float(previous["win_rate"])
                    if previous else None
                )
            })
        rates = [float(record["win_rate"]) for record in records]
        profits = [float(record["net_profit"]) for record in records]
        monotonic_recovery = all(
            rates[index] > rates[index - 1]
            and profits[index] > profits[index - 1]
            for index in range(1, len(records))
        )
        side_path = {}
        for side in ["up", "down"]:
            side_path[side] = {
                "net_profits": [
                    float(record[f"{side}_net_profit"]) for record in records
                ],
                "profitable_segments": sum(
                    float(record[f"{side}_net_profit"]) > 0
                    for record in records
                )
            }

        return {
            "schema_version": self.REPORT_SCHEMA_VERSION,
            "synthesis_id": evidence["synthesis_id"],
            "evidence_role": "post_hoc_localization_only",
            "aggregate": {
                "trades": trades,
                "wins": wins,
                "win_rate": self._ratio(wins, trades),
                "net_profit": profit
            },
            "locked_forward": locked,
            "boundary_reconciliation": {
                "acceptable": boundary_reconciliation,
                "difference": drift,
                "explanation": "segment_boundary_state_seeding_changes_eligibility"
            },
            "segments": segments,
            "side_path": side_path,
            "monotonic_recovery_pattern": monotonic_recovery,
            "localization": (
                "early_2026_loss_concentration_with_later_recovery"
                if monotonic_recovery else "nonmonotonic_forward_degradation"
            ),
            "decision": "diagnostic_only_hold_feature_optimization",
            "next_action": "preserve_locked_2026q4_prospective_baseline",
            "limitations": evidence.get("limitations", [])
        }
