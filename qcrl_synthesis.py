"""Build versioned cross-regime QCRL synthesis artifacts."""

import json
from pathlib import Path

from discovery.cross_regime_side_engine import (
    CrossRegimeSideEngine,
    CrossRegimeSideError
)
from discovery.temporal_bridge_engine import (
    TemporalBridgeEngine,
    TemporalBridgeError
)


SPEC_SCHEMA_VERSION = "qcrl.cross_regime_side_synthesis_spec.v1"
TEMPORAL_SPEC_SCHEMA_VERSION = "qcrl.temporal_bridge_synthesis_spec.v1"


class QcrlSynthesisError(ValueError):
    pass


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QcrlSynthesisError(f"Cannot read {path}: {exc}") from exc


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8"
    )


def run_cross_regime_side_synthesis(spec_path, project_root):
    spec = _read_json(spec_path)
    if spec.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise QcrlSynthesisError(
            f"Synthesis spec must use {SPEC_SCHEMA_VERSION}"
        )
    synthesis_id = spec.get("synthesis_id")
    sources = spec.get("sources")
    if not synthesis_id or not isinstance(sources, list) or len(sources) < 2:
        raise QcrlSynthesisError(
            "Synthesis requires synthesis_id and at least two sources"
        )

    evidence_sources = []
    for source in sources:
        label = source.get("label")
        campaign_id = source.get("campaign_id")
        if not label or not campaign_id:
            raise QcrlSynthesisError(
                "Every synthesis source requires label and campaign_id"
            )
        directory = project_root / ".qcrl" / "campaigns" / campaign_id
        report = _read_json(directory / "directional_cohort_report.json")
        artifact = _read_json(directory / "directional_cohort.json")
        if report.get("campaign_id") != campaign_id:
            raise QcrlSynthesisError(
                f"Report campaign mismatch for {campaign_id}"
            )
        if artifact.get("case_set_hash") != report.get("case_set_hash"):
            raise QcrlSynthesisError(
                f"Evidence revision mismatch for {campaign_id}"
            )
        side = report.get("side_attribution_interpretation")
        if not side:
            raise QcrlSynthesisError(
                f"Campaign {campaign_id} has no side-attribution verdict"
            )
        evidence_sources.append({
            "label": label,
            "campaign_id": campaign_id,
            "case_set_hash": report["case_set_hash"],
            "expected_labels": report["expected_labels"],
            "required_parameters": artifact.get("required_parameters"),
            "side_attribution": side
        })

    evidence = {
        "schema_version": CrossRegimeSideEngine.INPUT_SCHEMA_VERSION,
        "synthesis_id": synthesis_id,
        "sources": evidence_sources,
        "limitations": spec.get("limitations", [])
    }
    try:
        report = CrossRegimeSideEngine().analyze(evidence)
    except CrossRegimeSideError as exc:
        raise QcrlSynthesisError(str(exc)) from exc

    output = project_root / ".qcrl" / "syntheses" / synthesis_id
    evidence_path = output / "cross_regime_side_evidence.json"
    report_path = output / "cross_regime_side_report.json"
    _write_json(evidence_path, evidence)
    _write_json(report_path, report)
    _print_report(report, evidence_path, report_path)
    return report


def run_synthesis(spec_path, project_root):
    spec = _read_json(spec_path)
    if spec.get("schema_version") == SPEC_SCHEMA_VERSION:
        return run_cross_regime_side_synthesis(spec_path, project_root)
    if spec.get("schema_version") == TEMPORAL_SPEC_SCHEMA_VERSION:
        return run_temporal_bridge_synthesis(spec, project_root)
    raise QcrlSynthesisError("Unsupported synthesis spec schema")


def run_temporal_bridge_synthesis(spec, project_root):
    historical_id = spec.get("historical_campaign_id")
    forward_id = spec.get("forward_campaign_id")
    if not spec.get("synthesis_id") or not historical_id or not forward_id:
        raise QcrlSynthesisError(
            "Temporal bridge requires synthesis and source campaign IDs"
        )
    historical_dir = project_root / ".qcrl" / "campaigns" / historical_id
    forward_dir = project_root / ".qcrl" / "campaigns" / forward_id
    historical = _read_json(historical_dir / "temporal_stability_report.json")
    historical_audit = _read_json(historical_dir / "temporal_audit.json")
    forward = _read_json(forward_dir / "directional_cohort_report.json")
    forward_artifact = _read_json(forward_dir / "directional_cohort.json")
    if historical.get("campaign_id") != historical_id:
        raise QcrlSynthesisError("Historical campaign identity mismatch")
    if forward.get("campaign_id") != forward_id:
        raise QcrlSynthesisError("Forward campaign identity mismatch")
    if historical.get("case_set_hash") != historical_audit.get(
        "case_set_hash"
    ):
        raise QcrlSynthesisError("Historical temporal evidence revision mismatch")
    if forward.get("case_set_hash") != forward_artifact.get("case_set_hash"):
        raise QcrlSynthesisError("Forward evidence revision mismatch")
    cohorts = forward.get("cohorts", [])
    if len(cohorts) != 1:
        raise QcrlSynthesisError("Forward evidence must contain one locked cohort")
    cohort = cohorts[0]
    artifact_cohorts = forward_artifact.get("cohorts", [])
    if len(artifact_cohorts) != 1 or len(
        artifact_cohorts[0].get("records", [])
    ) != 1:
        raise QcrlSynthesisError("Forward artifact must contain one locked record")
    forward_record = artifact_cohorts[0]["records"][0]
    required = spec.get("required_signal_parameters", {})
    historical_parameters = historical_audit.get("required_parameters", {})
    forward_parameters = forward_artifact.get("required_parameters", {})
    for key, expected in required.items():
        if historical_parameters.get(key) != expected:
            raise QcrlSynthesisError(f"Historical signal mismatch: {key}")
        if forward_parameters.get(key) != expected:
            raise QcrlSynthesisError(f"Forward signal mismatch: {key}")
    historical_metrics = historical["aggregate"]
    evidence = {
        "schema_version": TemporalBridgeEngine.INPUT_SCHEMA_VERSION,
        "synthesis_id": spec["synthesis_id"],
        "historical": {
            "campaign_id": historical_id,
            "case_set_hash": historical["case_set_hash"],
            "classification": historical["verdict"]["classification"],
            "trades": historical_metrics["trades"],
            "wins": historical_metrics["wins"],
            "win_rate": historical_metrics["weighted_win_rate"],
            "net_profit": historical_metrics["net_profit"]
        },
        "forward": {
            "campaign_id": forward_id,
            "case_set_hash": forward["case_set_hash"],
            "classification": cohort["classification"],
            "trades": int(cohort["total_trades"]),
            "wins": forward_record["wins"],
            "win_rate": cohort["weighted_win_rate"],
            "net_profit": cohort["total_net_profit"]
        },
        "thresholds": spec["thresholds"],
        "declared_followups": spec.get("declared_followups", {}),
        "limitations": spec.get("limitations", [])
    }
    try:
        report = TemporalBridgeEngine().analyze(evidence)
    except TemporalBridgeError as exc:
        raise QcrlSynthesisError(str(exc)) from exc
    output = project_root / ".qcrl" / "syntheses" / spec["synthesis_id"]
    evidence_path = output / "temporal_bridge_evidence.json"
    report_path = output / "temporal_bridge_report.json"
    _write_json(evidence_path, evidence)
    _write_json(report_path, report)
    print(
        f"Temporal bridge: classification={report['classification']} "
        f"decision={report['decision']} "
        f"win_rate_change={report['comparison']['win_rate_change']:+.2%}"
    )
    failed = [key for key, value in report["checks"].items() if not value]
    print("Failed checks: " + (", ".join(failed) if failed else "none"))
    print(f"Next action: {report['next_action']}")
    print(f"Synthesis evidence: {evidence_path}")
    print(f"Synthesis report:   {report_path}")
    return report


def _print_report(report, evidence_path, report_path):
    print("Cross-regime side synthesis:")
    for source in report["sources"]:
        print(
            f"  {source['label']}: verdict={source['verdict']} "
            f"labels={source['expected_labels']}"
        )
    for side in report["pooled_sides"]:
        print(
            f"  pooled-{side['direction']}: "
            f"profit={side['total_net_profit']:+g} "
            f"win_rate={side['weighted_win_rate']:.2%} "
            f"trades={side['total_trades']:g} "
            f"profitable={side['profitable_samples']}/"
            f"{side['sample_count']}"
        )
    total = report["pooled_total"]
    print(
        f"  combined: profit={total['net_profit']:+g} "
        f"win_rate={total['weighted_win_rate']:.2%} "
        f"trades={total['trades']:g} "
        f"profitable={total['profitable_samples']}/"
        f"{total['sample_count']}"
    )
    print(f"Leadership flip: {report['leadership_flip']}")
    print(f"Decision: {report['decision']}")
    print(f"Next action: {report['next_action']}")
    print(f"Synthesis evidence: {evidence_path}")
    print(f"Synthesis report:   {report_path}")
