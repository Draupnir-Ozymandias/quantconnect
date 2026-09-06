"""Validation helpers for versioned QCRL campaign manifests."""


def validate_directional_analysis(manifest, metric_fields, error_type):
    analysis = manifest.get("directional_analysis")
    if analysis is None:
        return
    if not isinstance(analysis, dict):
        raise error_type("directional_analysis must be an object")
    for field in ["group_field", "label_field", "expected_labels"]:
        if field not in analysis:
            raise error_type(f"directional_analysis requires {field}")
    labels = analysis["expected_labels"]
    if not isinstance(labels, list) or not labels:
        raise error_type(
            "directional_analysis expected_labels must be a non-empty array"
        )
    if len(labels) != len(set(labels)):
        raise error_type(
            "directional_analysis expected_labels cannot contain duplicates"
        )
    if not isinstance(analysis.get("required_parameters", {}), dict):
        raise error_type(
            "directional_analysis required_parameters must be an object"
        )
    limitations = analysis.get("limitations", [])
    if not isinstance(limitations, list) or any(
        not isinstance(value, str) or not value.strip()
        for value in limitations
    ):
        raise error_type(
            "directional_analysis limitations must be an array of strings"
        )
    additional_metrics = analysis.get("additional_metrics", [])
    if not isinstance(additional_metrics, list) or any(
        not isinstance(value, str) for value in additional_metrics
    ):
        raise error_type(
            "directional_analysis additional_metrics must be an array of strings"
        )
    unknown_metrics = set(additional_metrics) - set(metric_fields)
    if unknown_metrics:
        raise error_type(
            "Unknown directional additional_metrics: "
            + ", ".join(sorted(unknown_metrics))
        )

    stage = analysis.get("analysis_stage", "generator_screen")
    if stage not in {
        "generator_screen", "parameter_neighborhood", "single_gate",
        "gate_attribution", "side_attribution", "regime_attribution"
    }:
        raise error_type(
            "directional_analysis analysis_stage must be generator_screen, "
            "parameter_neighborhood, single_gate, gate_attribution, or "
            "side_attribution, or regime_attribution"
        )
    if stage == "parameter_neighborhood":
        _validate_parameter_neighborhood(analysis, error_type)
    if stage == "single_gate":
        _validate_single_gate(analysis, error_type)
    if stage == "gate_attribution":
        _validate_gate_attribution(analysis, error_type)
    if stage == "side_attribution":
        _validate_side_attribution(analysis, error_type)
    if stage == "regime_attribution":
        _validate_regime_attribution(analysis, error_type)


def _validate_parameter_neighborhood(analysis, error_type):
    for field in ["candidate_value", "core_values", "tail_values"]:
        if field not in analysis:
            raise error_type(
                f"parameter_neighborhood analysis requires {field}"
            )
    core_values = analysis["core_values"]
    tail_values = analysis["tail_values"]
    if not isinstance(core_values, list) or not core_values:
        raise error_type("core_values must be a non-empty array")
    if not isinstance(tail_values, list):
        raise error_type("tail_values must be an array")
    if analysis["candidate_value"] not in core_values:
        raise error_type("candidate_value must be in core_values")
    if set(core_values) & set(tail_values):
        raise error_type("core_values and tail_values cannot overlap")


def _validate_single_gate(analysis, error_type):
    for field in ["control_value", "candidate_values"]:
        if field not in analysis:
            raise error_type(f"single_gate analysis requires {field}")
    candidates = analysis["candidate_values"]
    if not isinstance(candidates, list) or not candidates:
        raise error_type("candidate_values must be a non-empty array")
    if analysis["control_value"] in candidates:
        raise error_type("control_value cannot be a candidate_value")


def _validate_gate_attribution(analysis, error_type):
    for field in ["control_value", "diagnostic_value", "candidate_values"]:
        if field not in analysis:
            raise error_type(f"gate_attribution analysis requires {field}")
    candidates = analysis["candidate_values"]
    if not isinstance(candidates, list) or not candidates:
        raise error_type("candidate_values must be a non-empty array")
    reserved = {analysis["control_value"], analysis["diagnostic_value"]}
    if len(reserved) != 2 or reserved & set(candidates):
        raise error_type(
            "gate attribution control, diagnostic, and candidates must differ"
        )
    required_metrics = {
        "skipped_filter_not_ready", "skipped_filter_rejected"
    }
    if not required_metrics.issubset(analysis.get("additional_metrics", [])):
        raise error_type(
            "gate_attribution requires filter readiness and rejection metrics"
        )


def _validate_side_attribution(analysis, error_type):
    if "cohort_value" not in analysis:
        raise error_type("side_attribution analysis requires cohort_value")
    required = {
        f"{side}_{field}"
        for side in ["up", "down"]
        for field in [
            "trades", "wins", "losses", "win_rate", "net_profit",
            "max_drawdown", "max_loss_streak"
        ]
    }
    missing = required - set(analysis.get("additional_metrics", []))
    if missing:
        raise error_type(
            "side_attribution requires metrics: "
            + ", ".join(sorted(missing))
        )
    evidence_role = analysis.get("evidence_role", "discovery")
    if evidence_role not in {"discovery", "historical_regime_stress"}:
        raise error_type(
            "side_attribution evidence_role must be discovery or "
            "historical_regime_stress"
        )
    hypothesis_side = analysis.get("hypothesis_side")
    if evidence_role == "historical_regime_stress" and hypothesis_side not in {
        "up", "down"
    }:
        raise error_type(
            "historical_regime_stress requires hypothesis_side up or down"
        )


def _validate_regime_attribution(analysis, error_type):
    if "cohort_value" not in analysis:
        raise error_type("regime_attribution requires cohort_value")
    required = {
        f"{direction}_{regime}_regime_{field}"
        for direction in ["up", "down"]
        for regime in ["positive", "nonpositive", "not_ready"]
        for field in ["trades", "wins", "net_profit"]
    }
    required.update({
        f"{direction}_{field}"
        for direction in ["up", "down"]
        for field in ["trades", "wins", "net_profit"]
    })
    missing = required - set(analysis.get("additional_metrics", []))
    if missing:
        raise error_type(
            "regime_attribution requires metrics: "
            + ", ".join(sorted(missing))
        )
    hypothesis = analysis.get("regime_hypothesis")
    if not isinstance(hypothesis, dict):
        raise error_type("regime_attribution requires regime_hypothesis")
    if hypothesis.get("aligned_cells") != [
        "up:positive", "down:nonpositive"
    ]:
        raise error_type(
            "regime_hypothesis must predeclare ROC trend-aligned cells"
        )
    if hypothesis.get("counter_cells") != [
        "up:nonpositive", "down:positive"
    ]:
        raise error_type(
            "regime_hypothesis must predeclare ROC counter-trend cells"
        )
    for field in [
        "minimum_ready_ratio", "minimum_win_rate_edge",
        "minimum_supporting_labels", "minimum_cell_trades"
    ]:
        if field not in hypothesis or float(hypothesis[field]) <= 0:
            raise error_type(f"regime_hypothesis requires positive {field}")
    if float(hypothesis["minimum_ready_ratio"]) > 1:
        raise error_type("minimum_ready_ratio cannot exceed 1")
    if float(hypothesis["minimum_win_rate_edge"]) > 1:
        raise error_type("minimum_win_rate_edge cannot exceed 1")
    if int(hypothesis["minimum_supporting_labels"]) > len(
        analysis["expected_labels"]
    ):
        raise error_type(
            "minimum_supporting_labels exceeds expected label count"
        )
