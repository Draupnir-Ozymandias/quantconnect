"""Cross-sample analysis for flat-sized directional signal cohorts."""

from datetime import datetime, timezone
import math
import statistics


class DirectionalCohortError(ValueError):
    pass


class DirectionalCohortEngine:
    """Score signal generators across independent labels such as years."""

    INPUT_SCHEMA_VERSION = "qcrl.directional_cohort.v1"
    REPORT_SCHEMA_VERSION = "qcrl.directional_cohort_report.v1"
    SCORE_VERSION = "qcrl.directional_cohort_score.v2"
    NEIGHBORHOOD_VERSION = "qcrl.directional_neighborhood_interpretation.v1"
    SINGLE_GATE_VERSION = "qcrl.single_gate_interpretation.v1"
    ATTRIBUTION_VERSION = "qcrl.gate_attribution_interpretation.v1"
    SINGLE_GATE_THRESHOLDS = {
        "minimum_trade_retention_ratio": 0.50,
        "minimum_profit_improvement_ratio": 0.75
    }
    SCORE_WEIGHTS = {
        "profitable_sample_ratio": 0.30,
        "nonnegative_sample_ratio": 0.20,
        "win_rate_consistency": 0.25,
        "win_rate_at_or_above_half_ratio": 0.15,
        "profit_balance": 0.10
    }
    RISK_WEIGHTS = {
        "worst_drawdown_in_base_wagers": 0.50,
        "worst_loss_streak": 0.50
    }
    CLASSIFICATION_THRESHOLDS = {"stable": 70, "mixed": 50}
    DEFAULT_THRESHOLDS = {
        "minimum_samples": 4,
        "minimum_total_trades": 100,
        "minimum_trades_per_sample": 20,
        "win_rate_std_tolerance": 0.10,
        "drawdown_base_wager_limit": 64.0,
        "loss_streak_limit": 10.0
    }

    def __init__(self, thresholds=None):
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            unknown = set(thresholds) - set(self.thresholds)
            if unknown:
                raise DirectionalCohortError(
                    "Unknown directional thresholds: "
                    + ", ".join(sorted(unknown))
                )
            self.thresholds.update(thresholds)
        for name, value in self.thresholds.items():
            if float(value) <= 0:
                raise DirectionalCohortError(
                    f"Threshold {name} must be positive"
                )

    def analyze(self, artifact):
        self._validate_artifact(artifact)
        results = [
            self._analyze_cohort(cohort, artifact["expected_labels"])
            for cohort in artifact["cohorts"]
        ]
        results.sort(
            key=lambda item: (-item["final_score"], item["group_key"])
        )
        for rank, result in enumerate(results, 1):
            result["rank"] = rank

        advance = [
            result["group_key"] for result in results
            if result["disposition"] == "advance"
        ]
        hold = [
            result["group_key"] for result in results
            if result["disposition"] == "hold"
        ]
        reject = [
            result["group_key"] for result in results
            if result["disposition"] == "reject"
        ]
        stage = artifact.get("analysis_stage", "generator_screen")
        neighborhood = None
        single_gate = None
        attribution = None
        if stage == "parameter_neighborhood":
            neighborhood = self._interpret_neighborhood(results, artifact)
            next_action = neighborhood["next_action"]
        elif stage == "single_gate":
            single_gate = self._interpret_single_gates(results, artifact)
            next_action = single_gate["next_action"]
        elif stage == "gate_attribution":
            attribution = self._interpret_gate_attribution(results, artifact)
            next_action = attribution["next_action"]
        elif advance:
            next_action = "advance_candidates_to_single_gate_stage"
        elif hold:
            next_action = "run_parameter_neighborhood_validation"
        else:
            next_action = "redesign_directional_hypotheses"

        report = {
            "schema_version": self.REPORT_SCHEMA_VERSION,
            "score_version": self.SCORE_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).replace(
                microsecond=0
            ).isoformat().replace("+00:00", "Z"),
            "campaign_id": artifact.get("campaign_id"),
            "case_set_hash": artifact.get("case_set_hash"),
            "scope": "flat_directional_research_not_live_authorization",
            "group_field": artifact["group_field"],
            "label_field": artifact["label_field"],
            "analysis_stage": stage,
            "expected_labels": artifact["expected_labels"],
            "cohorts": results,
            "decision_summary": {
                "advance": advance,
                "hold": hold,
                "reject": reject,
                "next_action": next_action
            },
            "thresholds": dict(self.thresholds),
            "score_weights": dict(self.SCORE_WEIGHTS),
            "risk_weights": dict(self.RISK_WEIGHTS),
            "classification_thresholds": dict(
                self.CLASSIFICATION_THRESHOLDS
            ),
            "limitations": self._unique([
                "validation_cohort_not_universal_evidence",
                "transaction_costs_not_modeled_by_qcrl_wager_accounting",
                *artifact.get("limitations", [])
            ])
        }
        if neighborhood is not None:
            report["neighborhood_interpretation"] = neighborhood
            report["decision_summary"]["selected_candidates"] = (
                [neighborhood["selected_value"]]
                if neighborhood["decision"] == "advance"
                else []
            )
        if single_gate is not None:
            report["single_gate_interpretation"] = single_gate
            report["decision_summary"]["selected_candidates"] = (
                single_gate["selected_candidates"]
            )
        if attribution is not None:
            report["gate_attribution_interpretation"] = attribution
            report["decision_summary"]["selected_candidates"] = (
                attribution["selected_candidates"]
            )
        return report

    def _validate_artifact(self, artifact):
        if not isinstance(artifact, dict):
            raise DirectionalCohortError("Directional artifact must be an object")
        if artifact.get("schema_version") != self.INPUT_SCHEMA_VERSION:
            raise DirectionalCohortError(
                f"DirectionalCohortEngine requires {self.INPUT_SCHEMA_VERSION}"
            )
        if not artifact.get("validation", {}).get("valid"):
            raise DirectionalCohortError(
                "Directional artifact must pass evidence validation"
            )
        cohorts = artifact.get("cohorts")
        if not isinstance(cohorts, list) or not cohorts:
            raise DirectionalCohortError(
                "Directional artifact must contain cohorts"
            )
        keys = [cohort.get("group_key") for cohort in cohorts]
        if len(keys) != len(set(keys)):
            raise DirectionalCohortError(
                "Directional artifact contains duplicate cohort keys"
            )
        if artifact.get("analysis_stage") == "parameter_neighborhood":
            candidate = artifact.get("candidate_value")
            core = artifact.get("core_values")
            tail = artifact.get("tail_values")
            if not isinstance(core, list) or not core:
                raise DirectionalCohortError(
                    "Parameter neighborhood requires core_values"
                )
            if not isinstance(tail, list):
                raise DirectionalCohortError(
                    "Parameter neighborhood requires tail_values"
                )
            if candidate not in core:
                raise DirectionalCohortError(
                    "Neighborhood candidate_value must be a core value"
                )
            declared = set(core) | set(tail)
            if set(keys) != declared:
                raise DirectionalCohortError(
                    "Neighborhood cohorts must exactly match core and tail values"
                )
        if artifact.get("analysis_stage") == "single_gate":
            control = artifact.get("control_value")
            candidates = artifact.get("candidate_values")
            if not isinstance(candidates, list) or not candidates:
                raise DirectionalCohortError(
                    "Single-gate analysis requires candidate_values"
                )
            if control in candidates:
                raise DirectionalCohortError(
                    "Single-gate control cannot also be a candidate"
                )
            if set(keys) != {control, *candidates}:
                raise DirectionalCohortError(
                    "Single-gate cohorts must exactly match control and candidates"
                )
        if artifact.get("analysis_stage") == "gate_attribution":
            control = artifact.get("control_value")
            diagnostic = artifact.get("diagnostic_value")
            candidates = artifact.get("candidate_values")
            if not isinstance(candidates, list) or not candidates:
                raise DirectionalCohortError(
                    "Gate attribution requires candidate_values"
                )
            declared = {control, diagnostic, *candidates}
            if len(declared) != len(candidates) + 2:
                raise DirectionalCohortError(
                    "Attribution control, diagnostic, and candidates must differ"
                )
            if set(keys) != declared:
                raise DirectionalCohortError(
                    "Attribution cohorts must match control, diagnostic, "
                    "and candidates"
                )

    def _interpret_neighborhood(self, results, artifact):
        """Select a core candidate only when both adjacent sides support it."""
        by_key = {result["group_key"]: result for result in results}
        candidate_value = artifact["candidate_value"]
        core_values = artifact["core_values"]
        tail_values = artifact["tail_values"]
        candidate = by_key[candidate_value]

        def supports_region(result):
            return (
                result["coverage"]["coverage_ratio"] == 1
                and result["sample_size_sufficient"]
                and result["ruined_samples"] == 0
                and result["profitable_samples"] >= 3
                and result["weighted_win_rate"] > 0.5
                and result["total_net_profit"] > 0
            )

        eligible_core = [
            by_key[value] for value in core_values
            if supports_region(by_key[value])
        ]
        supporting_values = [
            result["group_key"] for result in eligible_core
            if result["group_key"] != candidate_value
        ]
        try:
            lower_support = any(
                value < candidate_value for value in supporting_values
            )
            upper_support = any(
                value > candidate_value for value in supporting_values
            )
        except TypeError as exc:
            raise DirectionalCohortError(
                "Neighborhood values must be mutually ordered"
            ) from exc
        best_core_score = max(
            (result["final_score"] for result in eligible_core),
            default=None
        )
        candidate_is_best = (
            best_core_score is not None
            and math.isclose(candidate["final_score"], best_core_score)
        )
        candidate_supported = supports_region(candidate)
        advance = (
            candidate_supported
            and candidate_is_best
            and lower_support
            and upper_support
        )

        rationale = []
        blockers = []
        if candidate_supported:
            rationale.append("candidate_has_sufficient_positive_evidence")
        else:
            blockers.append("candidate_lacks_sufficient_positive_evidence")
        if candidate_is_best:
            rationale.append("candidate_best_core_final_score")
        else:
            blockers.append("candidate_not_best_eligible_core_value")
        if lower_support and upper_support:
            rationale.append("supported_by_lower_and_upper_core_neighbors")
        else:
            blockers.append("missing_two_sided_core_neighbor_support")

        excluded_tail = []
        for value in tail_values:
            result = by_key[value]
            reasons = []
            if not result["sample_size_sufficient"]:
                reasons.append("sparse_evidence")
            if result["total_net_profit"] <= 0:
                reasons.append("nonpositive_total_profit")
            if result["profitable_samples"] < 3:
                reasons.append("profit_not_consistent_across_samples")
            if result["ruined_samples"]:
                reasons.append("ruin_observed")
            excluded_tail.append({
                "value": value,
                "reasons": reasons or ["exploratory_tail_not_selection_core"]
            })

        return {
            "schema_version": self.NEIGHBORHOOD_VERSION,
            "decision": "advance" if advance else "hold",
            "selected_value": candidate_value,
            "core_values": core_values,
            "supporting_values": supporting_values,
            "lower_neighbor_support": lower_support,
            "upper_neighbor_support": upper_support,
            "rationale": rationale,
            "blockers": blockers,
            "excluded_tail_values": excluded_tail,
            "next_action": (
                "advance_selected_candidate_to_single_gate_stage"
                if advance
                else "refine_parameter_neighborhood_evidence"
            )
        }

    def _interpret_single_gates(self, results, artifact):
        """Compare each isolated gate with the same-label unfiltered control."""
        by_key = {result["group_key"]: result for result in results}
        control_value = artifact["control_value"]
        control = by_key[control_value]
        cohort_records = {
            cohort["group_key"]: {
                record["label"]: record for record in cohort["records"]
            }
            for cohort in artifact["cohorts"]
        }
        control_records = cohort_records[control_value]
        minimum_improved_labels = math.ceil(
            len(artifact["expected_labels"])
            * self.SINGLE_GATE_THRESHOLDS[
                "minimum_profit_improvement_ratio"
            ]
        )
        comparisons = []
        for candidate_value in artifact["candidate_values"]:
            candidate = by_key[candidate_value]
            paired_labels = []
            improved_labels = 0
            for label in artifact["expected_labels"]:
                baseline = control_records.get(label)
                compared = cohort_records[candidate_value].get(label)
                if baseline is None or compared is None:
                    continue
                profit_delta = (
                    float(compared["net_profit"])
                    - float(baseline["net_profit"])
                )
                if profit_delta > 0:
                    improved_labels += 1
                paired = {
                    "label": label,
                    "control_case_id": baseline["case_id"],
                    "candidate_case_id": compared["case_id"],
                    "net_profit_delta": profit_delta,
                    "win_rate_delta": (
                        float(compared["win_rate"])
                        - float(baseline["win_rate"])
                    ),
                    "trade_retention_ratio": self._safe_ratio(
                        compared["trades"], baseline["trades"]
                    ),
                    "max_drawdown_delta": (
                        float(compared["max_drawdown"])
                        - float(baseline["max_drawdown"])
                    ),
                    "max_loss_streak_delta": (
                        float(compared["max_loss_streak"])
                        - float(baseline["max_loss_streak"])
                    )
                }
                paired["additional_metrics"] = {
                    field: {
                        "control": baseline[field],
                        "candidate": compared[field],
                        "delta": (
                            float(compared[field]) - float(baseline[field])
                        )
                    }
                    for field in artifact.get("additional_metrics", [])
                }
                paired_labels.append(paired)

            total_profit_delta = (
                candidate["total_net_profit"] - control["total_net_profit"]
            )
            win_rate_delta = (
                candidate["weighted_win_rate"] - control["weighted_win_rate"]
            )
            trade_retention = self._safe_ratio(
                candidate["total_trades"], control["total_trades"]
            )
            checks = {
                "complete_and_sufficient_evidence": (
                    candidate["coverage"]["coverage_ratio"] == 1
                    and candidate["sample_size_sufficient"]
                ),
                "no_ruin": candidate["ruined_samples"] == 0,
                "profitable_in_every_label": (
                    candidate["profitable_samples"]
                    == candidate["run_count"]
                ),
                "aggregate_profit_improved": total_profit_delta > 0,
                "weighted_win_rate_improved": win_rate_delta > 0,
                "profit_improved_in_required_labels": (
                    improved_labels >= minimum_improved_labels
                ),
                "trade_retention_sufficient": (
                    trade_retention
                    >= self.SINGLE_GATE_THRESHOLDS[
                        "minimum_trade_retention_ratio"
                    ]
                ),
                "worst_drawdown_not_increased": (
                    candidate["worst_max_drawdown"]
                    <= control["worst_max_drawdown"]
                )
            }
            if all(checks.values()):
                decision = "advance"
                next_action = "run_gate_parameter_neighborhood"
            elif not checks["complete_and_sufficient_evidence"]:
                decision = "hold"
                next_action = "complete_single_gate_evidence"
            elif (
                total_profit_delta <= 0
                or improved_labels < 2
                or candidate["profitable_samples"] < 3
            ):
                decision = "reject"
                next_action = "reject_tested_gate_default"
            else:
                decision = "hold"
                next_action = "expand_single_gate_evidence"
            comparisons.append({
                "candidate_value": candidate_value,
                "decision": decision,
                "next_action": next_action,
                "checks": checks,
                "paired_label_count": len(paired_labels),
                "profit_improved_labels": improved_labels,
                "required_profit_improved_labels": minimum_improved_labels,
                "total_net_profit_delta": total_profit_delta,
                "weighted_win_rate_delta": win_rate_delta,
                "total_trade_retention_ratio": trade_retention,
                "worst_max_drawdown_delta": (
                    candidate["worst_max_drawdown"]
                    - control["worst_max_drawdown"]
                ),
                "final_score_delta": (
                    candidate["final_score"] - control["final_score"]
                ),
                "paired_labels": paired_labels,
                "supporting_case_ids": candidate["supporting_case_ids"],
                "supporting_run_ids": candidate["supporting_run_ids"]
            })

        selected = [
            item["candidate_value"] for item in comparisons
            if item["decision"] == "advance"
        ]
        return {
            "schema_version": self.SINGLE_GATE_VERSION,
            "control_value": control_value,
            "selected_candidates": selected,
            "comparisons": comparisons,
            "thresholds": dict(self.SINGLE_GATE_THRESHOLDS),
            "next_action": (
                "run_selected_gate_parameter_neighborhood"
                if selected
                else "retain_unfiltered_signal_and_reject_tested_gates"
            )
        }

    def _interpret_gate_attribution(self, results, artifact):
        """Separate indicator-readiness effects from active gate effects."""
        diagnostic_value = artifact["diagnostic_value"]
        comparison_artifact = dict(artifact)
        comparison_artifact["candidate_values"] = [
            diagnostic_value, *artifact["candidate_values"]
        ]
        control_comparison = self._interpret_single_gates(
            results, comparison_artifact
        )
        comparisons = {
            item["candidate_value"]: item
            for item in control_comparison["comparisons"]
        }
        records = {
            cohort["group_key"]: {
                record["label"]: record for record in cohort["records"]
            }
            for cohort in artifact["cohorts"]
        }
        diagnostic_records = records[diagnostic_value]
        not_ready_field = "skipped_filter_not_ready"
        rejected_field = "skipped_filter_rejected"
        diagnostic_not_ready = sum(
            float(record.get(not_ready_field, 0))
            for record in diagnostic_records.values()
        )
        diagnostic_rejected = sum(
            float(record.get(rejected_field, 0))
            for record in diagnostic_records.values()
        )
        outcome_fields = [
            "net_profit", "win_rate", "trades", "wins", "max_drawdown",
            "max_loss_streak", "ruined", not_ready_field, rejected_field
        ]
        candidate_results = []
        for candidate_value in artifact["candidate_values"]:
            candidate_records = records[candidate_value]
            equivalent = all(
                self._records_equivalent(
                    diagnostic_records.get(label),
                    candidate_records.get(label),
                    outcome_fields
                )
                for label in artifact["expected_labels"]
            )
            rejected_total = sum(
                float(record.get(rejected_field, 0))
                for record in candidate_records.values()
            )
            base_decision = comparisons[candidate_value]["decision"]
            if equivalent:
                decision = "no_incremental_effect"
                next_action = "do_not_tune_inert_gate_bounds"
            elif rejected_total <= 0:
                decision = "no_active_gate_evidence"
                next_action = "collect_signal_time_filter_telemetry"
            elif base_decision == "advance":
                decision = "advance"
                next_action = "run_active_component_parameter_neighborhood"
            elif base_decision == "reject":
                decision = "reject"
                next_action = "reject_tested_component"
            else:
                decision = "hold"
                next_action = "expand_component_attribution_evidence"
            candidate_results.append({
                "candidate_value": candidate_value,
                "decision": decision,
                "next_action": next_action,
                "equivalent_to_diagnostic": equivalent,
                "rejected_signal_total": rejected_total,
                "control_comparison": comparisons[candidate_value]
            })

        selected = [
            item["candidate_value"] for item in candidate_results
            if item["decision"] == "advance"
        ]
        all_inert = all(
            item["decision"] in {
                "no_incremental_effect", "no_active_gate_evidence"
            }
            for item in candidate_results
        )
        return {
            "schema_version": self.ATTRIBUTION_VERSION,
            "control_value": artifact["control_value"],
            "diagnostic_value": diagnostic_value,
            "diagnostic_decision": "diagnostic_only",
            "diagnostic_not_ready_total": diagnostic_not_ready,
            "diagnostic_rejected_total": diagnostic_rejected,
            "diagnostic_control_comparison": comparisons[diagnostic_value],
            "candidates": candidate_results,
            "selected_candidates": selected,
            "next_action": (
                "collect_signal_time_filter_telemetry"
                if all_inert
                else (
                    "run_selected_component_parameter_neighborhood"
                    if selected
                    else "review_mixed_gate_attribution"
                )
            )
        }

    @staticmethod
    def _records_equivalent(first, second, fields):
        if first is None or second is None:
            return False
        for field in fields:
            left = first.get(field)
            right = second.get(field)
            if isinstance(left, bool) or isinstance(right, bool):
                if left is not right:
                    return False
            elif left is None or right is None:
                if left != right:
                    return False
            elif not math.isclose(float(left), float(right)):
                return False
        return True

    def _analyze_cohort(self, cohort, expected_labels):
        records = cohort.get("records", [])
        if not records:
            raise DirectionalCohortError(
                f"Cohort {cohort.get('group_key')} has no records"
            )
        labels = [record["label"] for record in records]
        if len(labels) != len(set(labels)):
            raise DirectionalCohortError(
                f"Cohort {cohort.get('group_key')} has duplicate labels"
            )
        expected_set = set(expected_labels)
        present_set = set(labels)
        present_count = len(expected_set & present_set)
        coverage_ratio = present_count / len(expected_labels)
        missing_labels = [
            label for label in expected_labels if label not in present_set
        ]
        unexpected_labels = [
            label for label in labels if label not in expected_set
        ]

        profits = [float(record["net_profit"]) for record in records]
        win_rates = [float(record["win_rate"]) for record in records]
        trades = [float(record["trades"]) for record in records]
        wins = [float(record["wins"]) for record in records]
        drawdowns = [float(record["max_drawdown"]) for record in records]
        drawdown_wagers = [
            float(record["drawdown_in_base_wagers"]) for record in records
        ]
        loss_streaks = [
            float(record["max_loss_streak"]) for record in records
        ]
        ruined = [bool(record["ruined"]) for record in records]
        n = len(records)
        total_trades = sum(trades)
        minimum_sample_trades = min(trades)
        sample_size_sufficient = (
            total_trades >= self.thresholds["minimum_total_trades"]
            and minimum_sample_trades
            >= self.thresholds["minimum_trades_per_sample"]
        )
        profitable_ratio = sum(value > 0 for value in profits) / n
        nonnegative_ratio = sum(value >= 0 for value in profits) / n
        above_half_ratio = sum(value >= 0.5 for value in win_rates) / n
        win_consistency = self._clamp(
            1
            - self._std(win_rates)
            / self.thresholds["win_rate_std_tolerance"]
        )
        profit_balance = self._balance_score(profits)
        components = {
            "profitable_sample_ratio": profitable_ratio,
            "nonnegative_sample_ratio": nonnegative_ratio,
            "win_rate_consistency": win_consistency,
            "win_rate_at_or_above_half_ratio": above_half_ratio,
            "profit_balance": profit_balance
        }
        stability_score = 100 * sum(
            self.SCORE_WEIGHTS[name] * value
            for name, value in components.items()
        )
        risk_penalty = (
            100
            if any(ruined)
            else 100 * self._clamp(
                0.5
                * max(drawdown_wagers)
                / self.thresholds["drawdown_base_wager_limit"]
                + 0.5
                * max(loss_streaks)
                / self.thresholds["loss_streak_limit"]
            )
        )
        final_score = stability_score * coverage_ratio * (
            1 - risk_penalty / 100
        )
        classification = self._classification(final_score)
        if (
            coverage_ratio < 1
            or n < int(self.thresholds["minimum_samples"])
        ):
            disposition = "hold"
            next_action = "complete_expected_validation_labels"
        elif not sample_size_sufficient:
            disposition = "hold"
            next_action = "expand_sparse_signal_evidence"
        elif any(ruined):
            disposition = "reject"
            next_action = "reject_ruined_configuration"
        elif classification == "stable":
            disposition = "advance"
            next_action = "advance_to_single_gate_stage"
        elif classification == "mixed":
            disposition = "hold"
            next_action = "run_parameter_neighborhood_validation"
        else:
            disposition = "reject"
            next_action = "reject_default_configuration"

        warnings = []
        if missing_labels:
            warnings.append("incomplete_expected_label_coverage")
        if unexpected_labels:
            warnings.append("unexpected_validation_labels")
        if n < int(self.thresholds["minimum_samples"]):
            warnings.append("insufficient_independent_samples")
        if total_trades < self.thresholds["minimum_total_trades"]:
            warnings.append("insufficient_total_trades")
        if (
            minimum_sample_trades
            < self.thresholds["minimum_trades_per_sample"]
        ):
            warnings.append("insufficient_trades_in_one_or_more_samples")
        if profitable_ratio < 0.75:
            warnings.append("profit_not_consistent_across_samples")
        if max(win_rates) - min(win_rates) >= 0.10:
            warnings.append("win_rate_regime_variation")
        if self._coefficient_of_variation(trades) >= 0.25:
            warnings.append("trade_frequency_regime_variation")
        if max(drawdown_wagers) >= 15:
            warnings.append("substantial_flat_drawdown")
        if any(ruined):
            warnings.append("cohort_ruin_observed")

        return {
            "group_key": cohort["group_key"],
            "run_count": n,
            "coverage": {
                "expected_count": len(expected_labels),
                "present_count": present_count,
                "coverage_ratio": coverage_ratio,
                "present_labels": labels,
                "missing_labels": missing_labels,
                "unexpected_labels": unexpected_labels
            },
            "profitable_samples": sum(value > 0 for value in profits),
            "nonnegative_samples": sum(value >= 0 for value in profits),
            "ruined_samples": sum(ruined),
            "profit_consistency_ratio": profitable_ratio,
            "nonnegative_ratio": nonnegative_ratio,
            "total_net_profit": sum(profits),
            "mean_net_profit": self._mean(profits),
            "std_net_profit": self._std(profits),
            "profit_balance_score": profit_balance,
            "weighted_win_rate": (
                sum(wins) / sum(trades) if sum(trades) else 0
            ),
            "mean_win_rate": self._mean(win_rates),
            "std_win_rate": self._std(win_rates),
            "min_win_rate": min(win_rates),
            "max_win_rate": max(win_rates),
            "win_rate_at_or_above_half_ratio": above_half_ratio,
            "total_trades": total_trades,
            "minimum_sample_trades": minimum_sample_trades,
            "sample_size_sufficient": sample_size_sufficient,
            "mean_trades": self._mean(trades),
            "trade_count_cv": self._coefficient_of_variation(trades),
            "mean_max_drawdown": self._mean(drawdowns),
            "worst_max_drawdown": max(drawdowns),
            "worst_drawdown_in_base_wagers": max(drawdown_wagers),
            "worst_max_loss_streak": max(loss_streaks),
            "stability_score": stability_score,
            "score_components": components,
            "risk_penalty": risk_penalty,
            "coverage_penalty": 100 * (1 - coverage_ratio),
            "final_score": final_score,
            "classification": classification,
            "disposition": disposition,
            "next_action": next_action,
            "warnings": warnings,
            "supporting_run_ids": [
                record["run_id"] for record in records
            ],
            "supporting_case_ids": [
                record["case_id"] for record in records
            ]
        }

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
        return statistics.pstdev(values) if len(values) > 1 else 0

    @staticmethod
    def _coefficient_of_variation(values):
        mean = statistics.fmean(values)
        if math.isclose(mean, 0):
            return 0
        return statistics.pstdev(values) / abs(mean)

    @staticmethod
    def _safe_ratio(numerator, denominator):
        denominator = float(denominator)
        if math.isclose(denominator, 0):
            return 0
        return float(numerator) / denominator

    @staticmethod
    def _balance_score(values):
        absolute = [abs(value) for value in values]
        total = sum(absolute)
        if math.isclose(total, 0):
            return 1
        if len(values) <= 1:
            return 0
        dominance = max(absolute) / total
        ideal = 1 / len(values)
        return DirectionalCohortEngine._clamp(
            (1 - dominance) / (1 - ideal)
        )

    @staticmethod
    def _clamp(value):
        return max(0, min(1, float(value)))

    @staticmethod
    def _unique(values):
        result = []
        for value in values:
            if value not in result:
                result.append(value)
        return result
