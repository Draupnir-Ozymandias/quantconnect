"""Build versioned cross-regime QCRL synthesis artifacts."""

import json
from pathlib import Path

from discovery.cross_regime_side_engine import (
    CrossRegimeSideEngine,
    CrossRegimeSideError
)


SPEC_SCHEMA_VERSION = "qcrl.cross_regime_side_synthesis_spec.v1"


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
