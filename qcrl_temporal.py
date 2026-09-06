"""Build and report the versioned QCRL temporal-persistence artifact."""

import json

from discovery.temporal_stability_engine import (
    TemporalStabilityEngine, TemporalStabilityError
)


class QcrlTemporalError(RuntimeError):
    pass


REQUIRED_METRICS = {
    "run_id", "net_profit", "win_rate", "trades", "wins",
    "max_drawdown", "max_loss_streak", "ruined", "bars_seen"
}


def _write_json(path, value):
    path.mkdir(parents=True, exist_ok=True)
    target = path / "temporal_audit.json"
    temporary = target.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(target)
    return target


def build_temporal_artifact(manifest, cases, state):
    config = manifest.get("temporal_analysis")
    if not config:
        raise QcrlTemporalError("Manifest does not declare temporal_analysis")
    rows = []
    runs = state.get("runs", {})
    for case in cases:
        run = runs.get(case["case_id"], {})
        if run.get("status") != "collected":
            raise QcrlTemporalError(f"Case is not collected: {case['case_id']}")
        if run.get("metrics_source") != "quantconnect_api" or not run.get("collected_at_utc"):
            raise QcrlTemporalError(f"Case lacks authoritative API evidence: {case['case_id']}")
        metrics = run.get("metrics", {})
        missing = REQUIRED_METRICS - set(metrics)
        if missing:
            raise QcrlTemporalError(
                f"Case {case['case_id']} lacks metrics: {', '.join(sorted(missing))}"
            )
        parameters = case["parameters"]
        for key, expected in config["required_parameters"].items():
            if parameters.get(key) != expected:
                raise QcrlTemporalError(f"Case {case['case_id']} violates {key}")
        trades = int(metrics["trades"])
        wins = int(metrics["wins"])
        if trades < 0 or wins < 0 or wins > trades:
            raise QcrlTemporalError(f"Case {case['case_id']} has invalid trade counts")
        measured_rate = wins / trades if trades else 0.0
        if abs(measured_rate - float(metrics["win_rate"])) > 1e-9:
            raise QcrlTemporalError(f"Case {case['case_id']} has win-rate accounting drift")
        expected_profit = (2 * wins - trades) * float(config["base_wager"])
        if abs(expected_profit - float(metrics["net_profit"])) > 1e-6:
            raise QcrlTemporalError(f"Case {case['case_id']} has flat-profit accounting drift")
        sample = parameters.get(config["sample_field"])
        rows.append({
            "sample": sample,
            "case_id": case["case_id"],
            "parameter_hash": case["parameter_hash"],
            "run_id": metrics["run_id"],
            "metrics_source": run["metrics_source"],
            "collected_at_utc": run["collected_at_utc"],
            **{field: metrics[field] for field in sorted(REQUIRED_METRICS - {"run_id"})}
        })
    expected = config["expected_samples"]
    by_sample = {row["sample"]: row for row in rows}
    if len(by_sample) != len(rows) or set(by_sample) != set(expected):
        raise QcrlTemporalError("Collected sample coverage does not match expected_samples")
    return {
        "schema_version": "qcrl.temporal_audit.v1",
        "campaign_id": manifest["campaign_id"],
        "case_set_hash": state["case_set_hash"],
        "sample_field": config["sample_field"],
        "expected_samples": expected,
        "base_wager": config["base_wager"],
        "friction_grid_base_wager_pct": config["friction_grid_base_wager_pct"],
        "thresholds": config["thresholds"],
        "limitations": config["limitations"],
        "records": [by_sample[sample] for sample in expected]
    }


def run_temporal_analysis(manifest, cases, state, directory):
    artifact = build_temporal_artifact(manifest, cases, state)
    artifact_path = _write_json(directory, artifact)
    try:
        report = TemporalStabilityEngine().analyze(artifact)
    except TemporalStabilityError as exc:
        raise QcrlTemporalError(str(exc)) from exc
    report_path = directory / "temporal_stability_report.json"
    temporary = report_path.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(report_path)
    aggregate = report["aggregate"]
    rolling = report["rolling_four_quarter"]
    print("Temporal persistence verdict:")
    print(
        f"classification={report['verdict']['classification']} "
        f"decision={report['verdict']['decision']} "
        f"profitable={aggregate['profitable_samples']}/{len(artifact['records'])} "
        f"weighted_win_rate={aggregate['weighted_win_rate']:.2%} "
        f"total_profit={aggregate['net_profit']:+g}"
    )
    print(
        f"rolling_4q_positive={rolling['positive_count']}/{len(rolling['windows'])} "
        f"break_even_cost={aggregate['break_even_cost_base_wager_pct']:.2%} "
        f"win_rate_std={aggregate['win_rate_std']:.2%}"
    )
    failed = [name for name, passed in report["checks"].items() if not passed]
    print("failed_checks=" + (", ".join(failed) if failed else "none"))
    print(f"Next action: {report['verdict']['next_action']}")
    print(f"Temporal evidence: {artifact_path}")
    print(f"Temporal report:   {report_path}")
    return 0
