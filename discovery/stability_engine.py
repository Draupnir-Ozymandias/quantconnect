"""Cross-sample stability analysis for QCRL paired campaign evidence."""

from datetime import datetime, timezone
import math
import statistics


class StabilityError(ValueError):
    pass


class StabilityEngine:
    """Analyze flat signal and martingale capital stability separately."""

    SCHEMA_VERSION = "qcrl.stability_report.v1"
    SCORE_VERSION = "qcrl.stability_score.v1"
    INTERPRETATION_VERSION = "qcrl.comparative_interpretation.v1"
    DEFAULT_THRESHOLDS = {
        "minimum_samples": 4,
        "win_rate_std_tolerance": 0.10,
        "flat_drawdown_base_wager_limit": 64.0,
        "flat_loss_streak_limit": 10.0,
        "martingale_drawdown_amplification_limit": 10.0,
        "martingale_wager_multiple_limit": 64.0,
        "martingale_recovery_depth_limit": 10.0
    }

    def __init__(self, thresholds=None):
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            unknown = set(thresholds) - set(self.thresholds)
            if unknown:
                raise StabilityError(
                    "Unknown stability thresholds: "
                    + ", ".join(sorted(unknown))
                )
            self.thresholds.update(thresholds)
        for name, value in self.thresholds.items():
            if float(value) <= 0:
                raise StabilityError(f"Threshold {name} must be positive")

    def analyze(self, paired_artifact):
        self._validate_artifact(paired_artifact)
        pairs = paired_artifact["pairs"]
        expected = paired_artifact.get(
            "expected_labels", [pair.get("label") for pair in pairs]
        )
        labels = [pair.get("label") for pair in pairs]
        coverage = self._coverage(expected, labels)
        flat = self._flat_stability(pairs, coverage)
        martingale = self._martingale_stability(pairs, coverage)
        warnings = self._warnings(pairs, coverage, flat, martingale)
        paired_evidence = self._paired_evidence(pairs)
        interpretation = self._comparative_interpretation(
            coverage,
            flat,
            martingale,
            paired_evidence,
            warnings
        )
        run_ids = self._unique(
            pair.get(field)
            for pair in pairs
            for field in ["baseline_run_id", "comparison_run_id"]
        )
        case_ids = self._unique(
            pair.get(field)
            for pair in pairs
            for field in ["baseline_case_id", "comparison_case_id"]
        )

        return {
            "schema_version": self.SCHEMA_VERSION,
            "score_version": self.SCORE_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).replace(
                microsecond=0
            ).isoformat().replace("+00:00", "Z"),
            "campaign_id": paired_artifact.get("campaign_id"),
            "case_set_hash": paired_artifact.get("case_set_hash"),
            "evidence_status": self._evidence_status(coverage, len(pairs)),
            "coverage": coverage,
            "flat_signal": flat,
            "martingale_capital": martingale,
            "paired_evidence": paired_evidence,
            "comparative_interpretation": interpretation,
            "thresholds": dict(self.thresholds),
            "warnings": warnings,
            "supporting_run_ids": run_ids,
            "supporting_case_ids": case_ids
        }

    def _comparative_interpretation(
        self,
        coverage,
        flat,
        martingale,
        paired_evidence,
        warnings
    ):
        signal_reasons = []
        if flat["classification"] == "fragile":
            signal_reasons.append("flat_signal_fragile")
        if flat["profit_consistency_ratio"] < 0.75:
            signal_reasons.append("flat_profit_inconsistent")
        if flat["mean_win_rate"] < 0.5:
            signal_reasons.append("mean_win_rate_below_half")
        signal_disposition = self._component_disposition(
            flat["classification"], coverage
        )

        capital_reasons = []
        if martingale["classification"] == "fragile":
            capital_reasons.append("martingale_capital_fragile")
        if martingale["recovery_dependence_ratio"] > 0:
            capital_reasons.append("profit_recovery_dependent")
        if martingale["worst_max_wager_multiple"] >= 32:
            capital_reasons.append("extreme_wager_escalation")
        if martingale["worst_drawdown_amplification"] >= 5:
            capital_reasons.append("substantial_drawdown_amplification")
        capital_disposition = self._component_disposition(
            martingale["classification"], coverage
        )
        if any(reason in capital_reasons for reason in [
            "extreme_wager_escalation",
            "substantial_drawdown_amplification"
        ]):
            capital_disposition = "reject"

        confidence = self._evidence_confidence(
            coverage, paired_evidence, warnings
        )
        gate = self._advancement_gate(
            signal_disposition,
            capital_disposition,
            confidence,
            signal_reasons,
            capital_reasons
        )
        return {
            "interpretation_version": self.INTERPRETATION_VERSION,
            "scope": "research_progression_not_live_trading_authorization",
            "signal_stability": {
                "score": flat["final_score"],
                "classification": flat["classification"],
                "disposition": signal_disposition,
                "reason_codes": signal_reasons
            },
            "capital_recovery_stability": {
                "score": martingale["final_score"],
                "classification": martingale["classification"],
                "disposition": capital_disposition,
                "reason_codes": capital_reasons
            },
            "recovery_dependence": {
                "ratio": martingale["recovery_dependence_ratio"],
                "level": self._recovery_dependence_level(
                    martingale["recovery_dependence_ratio"]
                )
            },
            "risk_amplification": {
                "level": self._risk_amplification_level(martingale),
                "worst_drawdown_multiple": (
                    martingale["worst_drawdown_amplification"]
                ),
                "worst_wager_multiple": (
                    martingale["worst_max_wager_multiple"]
                )
            },
            "evidence_confidence": confidence,
            "advancement_gate": gate
        }

    @staticmethod
    def _component_disposition(classification, coverage):
        if coverage["coverage_ratio"] < 1:
            return "hold"
        return {
            "stable": "advance",
            "mixed": "hold",
            "fragile": "reject"
        }[classification]

    def _evidence_confidence(self, coverage, paired_evidence, warnings):
        sample_factor = min(
            1.0,
            paired_evidence["pair_count"]
            / float(self.thresholds["minimum_samples"])
        )
        invariant_factor = (
            paired_evidence["invariant_pair_count"]
            / paired_evidence["pair_count"]
        )
        score = 100 * coverage["coverage_ratio"] * sample_factor
        score *= invariant_factor
        limitations = []
        if "terminal_loss_exposure_metrics_unavailable" in warnings:
            score -= 15
            limitations.append("terminal_loss_exposure_metrics_unavailable")
        if "validation_cohort_not_universal_evidence" in warnings:
            score -= 10
            limitations.append("validation_cohort_only")
        score = max(0.0, score)
        if score >= 80:
            level = "high"
        elif score >= 60:
            level = "moderate"
        else:
            level = "low"
        return {
            "score": score,
            "level": level,
            "limitations": limitations
        }

    @staticmethod
    def _recovery_dependence_level(ratio):
        if ratio >= 0.5:
            return "high"
        if ratio > 0:
            return "present"
        return "none"

    @staticmethod
    def _risk_amplification_level(martingale):
        if (
            martingale["worst_max_wager_multiple"] >= 32
            or martingale["worst_drawdown_amplification"] >= 5
        ):
            return "extreme"
        if (
            martingale["worst_max_wager_multiple"] >= 8
            or martingale["worst_drawdown_amplification"] >= 2
        ):
            return "elevated"
        return "contained"

    @staticmethod
    def _advancement_gate(
        signal_disposition,
        capital_disposition,
        confidence,
        signal_reasons,
        capital_reasons
    ):
        blockers = list(signal_reasons) + list(capital_reasons)
        if confidence["level"] == "low":
            return {
                "decision": "hold",
                "target": "current_signal_and_sizing_pair",
                "blockers": ["insufficient_evidence_confidence"] + blockers,
                "next_action": "expand_or_repair_validation_evidence"
            }
        if "reject" in [signal_disposition, capital_disposition]:
            if signal_disposition == "reject" and capital_disposition == "reject":
                next_action = "redesign_signal_and_reject_current_recovery_sizing"
            elif signal_disposition == "reject":
                next_action = "redesign_signal_before_sizing_optimization"
            else:
                next_action = "retain_signal_research_and_reject_current_sizing"
            return {
                "decision": "reject",
                "target": "current_signal_and_sizing_pair",
                "blockers": blockers,
                "next_action": next_action
            }
        if "hold" in [signal_disposition, capital_disposition]:
            return {
                "decision": "hold",
                "target": "current_signal_and_sizing_pair",
                "blockers": blockers or ["component_requires_more_evidence"],
                "next_action": "expand_validation_before_advancement"
            }
        return {
            "decision": "advance",
            "target": "current_signal_and_sizing_pair",
            "blockers": [],
            "next_action": "advance_to_parameter_neighborhood_validation"
        }

    def _validate_artifact(self, artifact):
        if not isinstance(artifact, dict):
            raise StabilityError("Paired artifact must be an object")
        if artifact.get("schema_version") != "qcrl.paired_comparison.v1":
            raise StabilityError(
                "StabilityEngine requires qcrl.paired_comparison.v1"
            )
        pairs = artifact.get("pairs")
        if not isinstance(pairs, list) or not pairs:
            raise StabilityError("Paired artifact must contain evidence pairs")
        labels = [pair.get("label") for pair in pairs]
        if len(labels) != len(set(labels)):
            raise StabilityError("Paired artifact contains duplicate labels")

    def _coverage(self, expected, present):
        expected_unique = self._unique(expected)
        present_unique = self._unique(present)
        expected_set = set(expected_unique)
        present_set = set(present_unique)
        denominator = len(expected_unique)
        ratio = (
            len(expected_set & present_set) / denominator
            if denominator else 0.0
        )
        return {
            "expected_labels": expected_unique,
            "present_labels": present_unique,
            "missing_labels": [
                label for label in expected_unique if label not in present_set
            ],
            "unexpected_labels": [
                label for label in present_unique if label not in expected_set
            ],
            "expected_count": denominator,
            "present_count": len(present_unique),
            "coverage_ratio": ratio,
            "coverage_penalty": 1.0 - ratio
        }

    def _flat_stability(self, pairs, coverage):
        profits = [float(pair["baseline"]["net_profit"]) for pair in pairs]
        win_rates = [float(pair["signal"]["win_rate"]) for pair in pairs]
        trades = [float(pair["signal"]["trades"]) for pair in pairs]
        drawdowns = [
            float(pair["baseline"]["max_drawdown"]) for pair in pairs
        ]
        drawdown_wagers = [
            float(pair["baseline"]["drawdown_in_base_wagers"])
            for pair in pairs
        ]
        loss_streaks = [
            float(pair["signal"]["max_loss_streak"]) for pair in pairs
        ]
        n = len(pairs)
        profitable_ratio = sum(value > 0 for value in profits) / n
        nonnegative_ratio = sum(value >= 0 for value in profits) / n
        above_half_ratio = sum(value >= 0.5 for value in win_rates) / n
        win_consistency = self._clamp(
            1.0
            - self._std(win_rates)
            / self.thresholds["win_rate_std_tolerance"]
        )
        profit_balance = self._balance_score(profits)
        stability = 100 * (
            0.30 * profitable_ratio
            + 0.20 * nonnegative_ratio
            + 0.25 * win_consistency
            + 0.15 * above_half_ratio
            + 0.10 * profit_balance
        )
        risk_penalty = 100 * self._clamp(
            0.5
            * max(drawdown_wagers)
            / self.thresholds["flat_drawdown_base_wager_limit"]
            + 0.5
            * max(loss_streaks)
            / self.thresholds["flat_loss_streak_limit"]
        )
        final_score = stability * coverage["coverage_ratio"] * (
            1.0 - risk_penalty / 100
        )
        return {
            "run_count": n,
            "profitable_years": sum(value > 0 for value in profits),
            "nonnegative_years": sum(value >= 0 for value in profits),
            "profit_consistency_ratio": profitable_ratio,
            "nonnegative_ratio": nonnegative_ratio,
            "mean_win_rate": self._mean(win_rates),
            "std_win_rate": self._std(win_rates),
            "min_win_rate": min(win_rates),
            "max_win_rate": max(win_rates),
            "win_rate_at_or_above_half_ratio": above_half_ratio,
            "win_rate_trend_per_label": self._linear_slope(
                [pair["label"] for pair in pairs], win_rates
            ),
            "mean_trades": self._mean(trades),
            "std_trades": self._std(trades),
            "mean_net_profit": self._mean(profits),
            "std_net_profit": self._std(profits),
            "coefficient_of_variation": self._coefficient_of_variation(
                profits
            ),
            "profit_balance_score": profit_balance,
            "mean_max_drawdown": self._mean(drawdowns),
            "worst_max_drawdown": max(drawdowns),
            "worst_drawdown_in_base_wagers": max(drawdown_wagers),
            "mean_max_loss_streak": self._mean(loss_streaks),
            "worst_max_loss_streak": max(loss_streaks),
            "stability_score": stability,
            "risk_penalty": risk_penalty,
            "coverage_penalty": 100 * coverage["coverage_penalty"],
            "final_score": final_score,
            "classification": self._classification(final_score)
        }

    def _martingale_stability(self, pairs, coverage):
        profits = [float(pair["comparison"]["net_profit"]) for pair in pairs]
        drawdowns = [
            float(pair["comparison"]["max_drawdown"]) for pair in pairs
        ]
        drawdown_multiples = [
            float(pair["deltas"]["drawdown_amplification"])
            for pair in pairs
        ]
        wager_multiples = [
            float(pair["deltas"]["max_wager_multiple_of_base"])
            for pair in pairs
        ]
        recovery_depths = [
            float(pair["comparison"]["max_recovery_depth"])
            for pair in pairs
        ]
        ruined = [bool(pair["comparison"]["ruined"]) for pair in pairs]
        n = len(pairs)
        survival_ratio = sum(not value for value in ruined) / n
        profit_ratio = sum(value > 0 for value in profits) / n
        recovery_dependent_ratio = sum(
            pair["interpretation"]["capital_transform"]
            == "recovery-dependent-profit"
            for pair in pairs
        ) / n
        drawdown_consistency = 1.0 - self._clamp(
            self._coefficient_of_variation(drawdown_multiples)
        )
        wager_consistency = 1.0 - self._clamp(
            self._coefficient_of_variation(wager_multiples)
        )
        recovery_consistency = 1.0 - self._clamp(
            self._coefficient_of_variation(recovery_depths)
        )
        stability = 100 * (
            0.25 * survival_ratio
            + 0.20 * profit_ratio
            + 0.20 * drawdown_consistency
            + 0.20 * wager_consistency
            + 0.15 * recovery_consistency
        )
        risk_penalty = 100 * self._clamp(
            0.35
            * max(drawdown_multiples)
            / self.thresholds[
                "martingale_drawdown_amplification_limit"
            ]
            + 0.35
            * max(wager_multiples)
            / self.thresholds["martingale_wager_multiple_limit"]
            + 0.15
            * max(recovery_depths)
            / self.thresholds["martingale_recovery_depth_limit"]
            + 0.15 * recovery_dependent_ratio
        )
        final_score = stability * coverage["coverage_ratio"] * (
            1.0 - risk_penalty / 100
        )
        return {
            "run_count": n,
            "profitable_years": sum(value > 0 for value in profits),
            "profit_consistency_ratio": profit_ratio,
            "surviving_years": sum(not value for value in ruined),
            "survival_ratio": survival_ratio,
            "mean_net_profit": self._mean(profits),
            "std_net_profit": self._std(profits),
            "coefficient_of_variation": self._coefficient_of_variation(
                profits
            ),
            "mean_max_drawdown": self._mean(drawdowns),
            "worst_max_drawdown": max(drawdowns),
            "mean_drawdown_amplification": self._mean(
                drawdown_multiples
            ),
            "worst_drawdown_amplification": max(drawdown_multiples),
            "drawdown_amplification_cv": self._coefficient_of_variation(
                drawdown_multiples
            ),
            "mean_max_wager_multiple": self._mean(wager_multiples),
            "worst_max_wager_multiple": max(wager_multiples),
            "max_wager_multiple_cv": self._coefficient_of_variation(
                wager_multiples
            ),
            "mean_recovery_depth": self._mean(recovery_depths),
            "worst_recovery_depth": max(recovery_depths),
            "recovery_depth_cv": self._coefficient_of_variation(
                recovery_depths
            ),
            "recovery_dependent_years": sum(
                pair["interpretation"]["capital_transform"]
                == "recovery-dependent-profit"
                for pair in pairs
            ),
            "recovery_dependence_ratio": recovery_dependent_ratio,
            "mean_profit_uplift": self._mean([
                float(pair["deltas"]["net_profit"]) for pair in pairs
            ]),
            "stability_score": stability,
            "risk_penalty": risk_penalty,
            "coverage_penalty": 100 * coverage["coverage_penalty"],
            "final_score": final_score,
            "classification": self._classification(final_score)
        }

    def _paired_evidence(self, pairs):
        return {
            "pair_count": len(pairs),
            "invariant_pair_count": sum(
                bool(pair.get("signal_invariants_match")) for pair in pairs
            ),
            "all_signal_invariants_match": all(
                bool(pair.get("signal_invariants_match")) for pair in pairs
            ),
            "recovery_dependent_labels": [
                pair["label"] for pair in pairs
                if pair["interpretation"]["capital_transform"]
                == "recovery-dependent-profit"
            ],
            "signal_supported_labels": [
                pair["label"] for pair in pairs
                if pair["interpretation"]["capital_transform"]
                == "signal-supported-profit-amplification"
            ]
        }

    def _warnings(self, pairs, coverage, flat, martingale):
        warnings = []
        if coverage["coverage_ratio"] < 1:
            warnings.append("incomplete_expected_label_coverage")
        if len(pairs) < int(self.thresholds["minimum_samples"]):
            warnings.append("insufficient_independent_samples")
        if not all(pair.get("signal_invariants_match") for pair in pairs):
            warnings.append("signal_pair_invariant_violation")
        if flat["profit_consistency_ratio"] < 0.75:
            warnings.append("flat_profit_not_consistent_across_samples")
        if flat["max_win_rate"] - flat["min_win_rate"] >= 0.10:
            warnings.append("flat_win_rate_regime_variation")
        if martingale["recovery_dependence_ratio"] > 0:
            warnings.append("martingale_profit_depends_on_recovery_sizing")
        if martingale["worst_max_wager_multiple"] >= 32:
            warnings.append("martingale_extreme_wager_escalation")
        if martingale["worst_drawdown_amplification"] >= 5:
            warnings.append("martingale_substantial_drawdown_amplification")
        warnings.append("terminal_loss_exposure_metrics_unavailable")
        warnings.append("validation_cohort_not_universal_evidence")
        return warnings

    def _evidence_status(self, coverage, sample_count):
        if sample_count < int(self.thresholds["minimum_samples"]):
            return "insufficient"
        if coverage["coverage_ratio"] < 1:
            return "incomplete"
        return "validation_cohort_complete"

    @staticmethod
    def _classification(score):
        if score >= 70:
            return "stable"
        if score >= 50:
            return "mixed"
        return "fragile"

    @staticmethod
    def _mean(values):
        return statistics.fmean(values)

    @staticmethod
    def _std(values):
        return statistics.pstdev(values) if len(values) > 1 else 0.0

    @staticmethod
    def _coefficient_of_variation(values):
        mean = statistics.fmean(values)
        if math.isclose(mean, 0.0):
            return None
        return statistics.pstdev(values) / abs(mean)

    @staticmethod
    def _balance_score(values):
        absolute = [abs(value) for value in values]
        total = sum(absolute)
        if math.isclose(total, 0.0):
            return 1.0
        count = len(values)
        if count <= 1:
            return 0.0
        dominance = max(absolute) / total
        ideal = 1.0 / count
        return StabilityEngine._clamp(
            (1.0 - dominance) / (1.0 - ideal)
        )

    @staticmethod
    def _linear_slope(labels, values):
        try:
            x = [float(label) for label in labels]
        except (TypeError, ValueError):
            return None
        x_mean = statistics.fmean(x)
        y_mean = statistics.fmean(values)
        denominator = sum((value - x_mean) ** 2 for value in x)
        if math.isclose(denominator, 0.0):
            return None
        return sum(
            (x_value - x_mean) * (y_value - y_mean)
            for x_value, y_value in zip(x, values)
        ) / denominator

    @staticmethod
    def _clamp(value):
        if value is None:
            return 1.0
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _unique(values):
        result = []
        for value in values:
            if value is not None and value not in result:
                result.append(value)
        return result
