"""Synthesize directional-side evidence across distinct market regimes."""

from datetime import datetime, timezone


class CrossRegimeSideError(ValueError):
    pass


class CrossRegimeSideEngine:
    INPUT_SCHEMA_VERSION = "qcrl.cross_regime_side_evidence.v1"
    REPORT_SCHEMA_VERSION = "qcrl.cross_regime_side_report.v1"
    SIDE_SCHEMA_VERSION = "qcrl.side_attribution_interpretation.v1"

    def analyze(self, evidence):
        self._validate(evidence)
        sources = [self._source_summary(item) for item in evidence["sources"]]
        pooled_sides = [
            self._pool_side(direction, sources) for direction in ["up", "down"]
        ]
        pooled = {item["direction"]: item for item in pooled_sides}
        annual = self._annual_synthesis(sources)
        dominant_sides = [
            {
                "label": source["label"],
                "direction": source["verdict"].split("_", 1)[0]
            }
            for source in sources
            if source["verdict"] in {"up_dominant", "down_dominant"}
        ]
        dominant_directions = {
            item["direction"] for item in dominant_sides
        }
        leadership_flip = len(dominant_directions) > 1
        if leadership_flip:
            decision = "retain_both_directions"
            next_action = (
                "define_prior_state_regime_hypotheses_without_side_restriction"
            )
        elif (
            len(dominant_sides) == len(sources)
            and len(dominant_directions) == 1
        ):
            decision = "hold_static_direction_candidate"
            next_action = "require_forward_direction_validation"
        else:
            decision = "retain_both_directions"
            next_action = "preserve_signal_and_test_next_isolated_hypothesis"

        total_profit = pooled["up"]["total_net_profit"] + pooled["down"][
            "total_net_profit"
        ]
        profit_gap = abs(
            pooled["up"]["total_net_profit"]
            - pooled["down"]["total_net_profit"]
        )
        return {
            "schema_version": self.REPORT_SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).replace(
                microsecond=0
            ).isoformat().replace("+00:00", "Z"),
            "synthesis_id": evidence["synthesis_id"],
            "scope": "cross_regime_research_not_live_authorization",
            "sources": sources,
            "source_count": len(sources),
            "leadership_flip": leadership_flip,
            "dominant_sides_by_source": dominant_sides,
            "pooled_sides": pooled_sides,
            "pooled_total": {
                "trades": sum(item["total_trades"] for item in pooled_sides),
                "wins": sum(item["total_wins"] for item in pooled_sides),
                "weighted_win_rate": self._safe_ratio(
                    sum(item["total_wins"] for item in pooled_sides),
                    sum(item["total_trades"] for item in pooled_sides)
                ),
                "net_profit": total_profit,
                "profitable_samples": sum(
                    item["net_profit"] > 0 for item in annual
                ),
                "sample_count": len(annual)
            },
            "side_balance": {
                "absolute_profit_gap": profit_gap,
                "profit_gap_ratio": self._safe_ratio(
                    profit_gap, abs(total_profit)
                ),
                "absolute_win_rate_gap": abs(
                    pooled["up"]["weighted_win_rate"]
                    - pooled["down"]["weighted_win_rate"]
                )
            },
            "annual_results": annual,
            "decision": decision,
            "static_direction_restriction": (
                "held_for_forward_validation"
                if decision == "hold_static_direction_candidate"
                else "rejected"
            ),
            "next_action": next_action,
            "limitations": list(evidence.get("limitations", []))
        }

    def _validate(self, evidence):
        if not isinstance(evidence, dict):
            raise CrossRegimeSideError("Cross-regime evidence must be an object")
        if evidence.get("schema_version") != self.INPUT_SCHEMA_VERSION:
            raise CrossRegimeSideError(
                f"Evidence must use {self.INPUT_SCHEMA_VERSION}"
            )
        if not evidence.get("synthesis_id"):
            raise CrossRegimeSideError("Evidence requires synthesis_id")
        sources = evidence.get("sources")
        if not isinstance(sources, list) or len(sources) < 2:
            raise CrossRegimeSideError("At least two regime sources are required")
        labels = [source.get("label") for source in sources]
        if any(not isinstance(label, str) or not label for label in labels):
            raise CrossRegimeSideError(
                "Every regime source requires a non-empty label"
            )
        if len(labels) != len(set(labels)):
            raise CrossRegimeSideError("Regime source labels must be unique")
        configurations = []
        all_period_labels = []
        for source in sources:
            if not source.get("campaign_id") or not source.get("case_set_hash"):
                raise CrossRegimeSideError(
                    f"{source.get('label')} lacks campaign evidence identity"
                )
            side = source.get("side_attribution", {})
            if side.get("schema_version") != self.SIDE_SCHEMA_VERSION:
                raise CrossRegimeSideError(
                    f"{source.get('label')} lacks versioned side attribution"
                )
            directions = {
                item.get("direction") for item in side.get("sides", [])
            }
            if directions != {"up", "down"}:
                raise CrossRegimeSideError(
                    f"{source.get('label')} must contain UP and DOWN evidence"
                )
            configuration = source.get("required_parameters")
            if not isinstance(configuration, dict) or not configuration:
                raise CrossRegimeSideError(
                    f"{source.get('label')} lacks required_parameters"
                )
            configurations.append(configuration)
            period_labels = source.get("expected_labels", [])
            if not isinstance(period_labels, list) or not period_labels:
                raise CrossRegimeSideError(
                    f"{source.get('label')} lacks expected labels"
                )
            if len(period_labels) != len(set(period_labels)):
                raise CrossRegimeSideError(
                    f"{source.get('label')} contains duplicate period labels"
                )
            for side_result in side["sides"]:
                self._validate_side_result(
                    source["label"], period_labels, side_result
                )
            all_period_labels.extend(period_labels)
        if any(item != configurations[0] for item in configurations[1:]):
            raise CrossRegimeSideError(
                "Regime sources do not share an identical signal configuration"
            )
        if len(all_period_labels) != len(set(all_period_labels)):
            raise CrossRegimeSideError(
                "Regime sources contain overlapping period labels"
            )

    @staticmethod
    def _validate_side_result(source_label, expected_labels, side):
        annual = side.get("annual_results")
        if not isinstance(annual, list):
            raise CrossRegimeSideError(
                f"{source_label} lacks annual side results"
            )
        labels = [item.get("label") for item in annual]
        if labels != expected_labels:
            raise CrossRegimeSideError(
                f"{source_label} side labels do not match expected labels"
            )
        checks = {
            "total_net_profit": sum(float(item["net_profit"]) for item in annual),
            "total_trades": sum(float(item["trades"]) for item in annual),
            "total_wins": sum(float(item["wins"]) for item in annual),
            "profitable_samples": sum(
                float(item["net_profit"]) > 0 for item in annual
            ),
            "run_count": len(annual)
        }
        for field, expected in checks.items():
            if field not in side:
                raise CrossRegimeSideError(
                    f"{source_label} side result lacks {field}"
                )
            actual = float(side[field])
            if abs(actual - float(expected)) > 1e-9:
                raise CrossRegimeSideError(
                    f"{source_label} side accounting mismatch for {field}"
                )

    @staticmethod
    def _source_summary(source):
        side = source["side_attribution"]
        return {
            "label": source["label"],
            "campaign_id": source["campaign_id"],
            "case_set_hash": source["case_set_hash"],
            "expected_labels": source["expected_labels"],
            "evidence_role": side.get("evidence_role", "discovery"),
            "verdict": side["verdict"],
            "hypothesis_side": side.get("hypothesis_side"),
            "hypothesis_result": side.get("hypothesis_result"),
            "sides": side["sides"]
        }

    @staticmethod
    def _pool_side(direction, sources):
        entries = [
            side
            for source in sources
            for side in source["sides"]
            if side["direction"] == direction
        ]
        total_trades = sum(float(item["total_trades"]) for item in entries)
        total_wins = sum(float(item["total_wins"]) for item in entries)
        return {
            "direction": direction,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "weighted_win_rate": CrossRegimeSideEngine._safe_ratio(
                total_wins, total_trades
            ),
            "total_net_profit": sum(
                float(item["total_net_profit"]) for item in entries
            ),
            "profitable_samples": sum(
                int(item["profitable_samples"]) for item in entries
            ),
            "sample_count": sum(int(item["run_count"]) for item in entries)
        }

    @staticmethod
    def _annual_synthesis(sources):
        annual = []
        for source in sources:
            side_records = {
                side["direction"]: {
                    item["label"]: item for item in side["annual_results"]
                }
                for side in source["sides"]
            }
            for label in source["expected_labels"]:
                up = side_records["up"][label]
                down = side_records["down"][label]
                annual.append({
                    "regime": source["label"],
                    "label": label,
                    "up_net_profit": up["net_profit"],
                    "down_net_profit": down["net_profit"],
                    "net_profit": (
                        float(up["net_profit"]) + float(down["net_profit"])
                    ),
                    "leading_side": (
                        "up"
                        if float(up["net_profit"]) > float(down["net_profit"])
                        else "down"
                        if float(down["net_profit"]) > float(up["net_profit"])
                        else "tie"
                    )
                })
        annual.sort(key=lambda item: item["label"])
        return annual

    @staticmethod
    def _safe_ratio(numerator, denominator):
        return float(numerator) / float(denominator) if denominator else 0
