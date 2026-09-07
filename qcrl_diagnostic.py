"""Build a provenance-checked post-hoc forward localization report."""

import json

from discovery.forward_diagnostic_engine import (
    ForwardDiagnosticEngine, ForwardDiagnosticError
)


SPEC_SCHEMA_VERSION = "qcrl.forward_diagnostic_synthesis_spec.v1"


class QcrlDiagnosticError(ValueError):
    pass


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QcrlDiagnosticError(f"Cannot read {path}: {exc}") from exc


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_forward_diagnostic_synthesis(spec, root):
    diagnostic_id = spec["diagnostic_campaign_id"]
    forward_id = spec["locked_forward_campaign_id"]
    state = _read(root / ".qcrl" / "campaigns" / diagnostic_id / "state.json")
    forward = _read(
        root / ".qcrl" / "campaigns" / forward_id / "directional_cohort.json"
    )
    if state.get("campaign_id") != diagnostic_id:
        raise QcrlDiagnosticError("Diagnostic campaign identity mismatch")
    if forward.get("campaign_id") != forward_id:
        raise QcrlDiagnosticError("Locked forward campaign identity mismatch")
    forward_records = forward.get("cohorts", [{}])[0].get("records", [])
    if len(forward_records) != 1:
        raise QcrlDiagnosticError("Locked forward evidence must contain one record")
    required_metrics = {
        "run_id", "bars_seen", "trades", "wins", "win_rate", "net_profit",
        "max_drawdown", "max_loss_streak", "up_trades", "up_wins",
        "up_net_profit", "down_trades", "down_wins", "down_net_profit"
    }
    by_sample = {}
    for run in state.get("runs", {}).values():
        sample = run.get("parameters", {}).get(spec["sample_field"])
        if run.get("status") != "collected" or run.get(
            "metrics_source"
        ) != "quantconnect_api" or not run.get("collected_at_utc"):
            raise QcrlDiagnosticError(f"Diagnostic case is not authoritative: {sample}")
        for key, expected in spec["required_signal_parameters"].items():
            if run["parameters"].get(key) != expected:
                raise QcrlDiagnosticError(f"Diagnostic signal mismatch: {key}")
        metrics = run.get("metrics", {})
        missing = required_metrics - set(metrics)
        if missing:
            raise QcrlDiagnosticError(
                "Diagnostic metrics missing: " + ", ".join(sorted(missing))
            )
        by_sample[sample] = {
            "sample": sample,
            "case_id": run["case_id"],
            "run_id": metrics["run_id"],
            "base_wager": run["parameters"]["base_wager"],
            **{field: metrics[field] for field in sorted(required_metrics)}
        }
    expected = spec["expected_samples"]
    if set(by_sample) != set(expected):
        raise QcrlDiagnosticError("Diagnostic sample coverage mismatch")
    locked_record = forward_records[0]
    locked_parameters = forward.get("required_parameters", {})
    for key, expected_value in spec["required_locked_signal_parameters"].items():
        if locked_parameters.get(key) != expected_value:
            raise QcrlDiagnosticError(f"Locked forward signal mismatch: {key}")
    evidence = {
        "schema_version": ForwardDiagnosticEngine.INPUT_SCHEMA_VERSION,
        "synthesis_id": spec["synthesis_id"],
        "diagnostic_campaign_id": diagnostic_id,
        "diagnostic_case_set_hash": state["case_set_hash"],
        "locked_forward_campaign_id": forward_id,
        "locked_forward_case_set_hash": forward["case_set_hash"],
        "expected_samples": expected,
        "records": [by_sample[sample] for sample in expected],
        "locked_forward": {
            key: locked_record[key]
            for key in ["trades", "wins", "win_rate", "net_profit"]
        },
        "thresholds": spec["thresholds"],
        "limitations": spec.get("limitations", [])
    }
    try:
        report = ForwardDiagnosticEngine().analyze(evidence)
    except ForwardDiagnosticError as exc:
        raise QcrlDiagnosticError(str(exc)) from exc
    output = root / ".qcrl" / "syntheses" / spec["synthesis_id"]
    evidence_path = output / "forward_diagnostic_evidence.json"
    report_path = output / "forward_diagnostic_report.json"
    _write(evidence_path, evidence)
    _write(report_path, report)
    print(
        f"Forward diagnostic: localization={report['localization']} "
        f"aggregate_profit={report['aggregate']['net_profit']:+g} "
        f"aggregate_win_rate={report['aggregate']['win_rate']:.2%}"
    )
    for segment in report["segments"]:
        print(
            f"  {segment['sample']}: profit={segment['net_profit']:+g} "
            f"win_rate={segment['win_rate']:.2%} trades={segment['trades']}"
        )
    print(f"Decision: {report['decision']}")
    print(f"Next action: {report['next_action']}")
    print(f"Diagnostic evidence: {evidence_path}")
    print(f"Diagnostic report:   {report_path}")
    return report
