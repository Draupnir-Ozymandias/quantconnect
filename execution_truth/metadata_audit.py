"""Offline descriptive metadata audit; never changes execution eligibility."""

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .book_sequence import normalize_book_sequence
from .bundle import normalize_bundle, _store_json
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .schema_interpretation import POLICY_ID, interpret_market_bundle


AUDIT_SCHEMA = "qcrl.batch_metadata_audit.v1"
SPEC_SCHEMA = "qcrl.batch_metadata_audit_spec.v1"
PHASES = ("early", "middle", "late")


def _moment(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def analyze_metadata_batch(markets, *, apply_current_documentation=False):
    """Audit declared sequences, preserving missing phases and raw provenance.

    Every supplied source must verify. No silent skipping, inferred defaults,
    pooled profitability verdict, or replay integration is permitted.
    """
    if type(apply_current_documentation) is not bool:
        raise ContractError("documentation applicability must be boolean")
    if not isinstance(markets, dict) or not markets:
        raise ContractError("metadata audit requires declared markets")
    rows, sources, coverage, changes = [], [], [], []
    seen_bundles, seen_conditions = set(), set()
    for label, phases in sorted(markets.items()):
        if not isinstance(label, str) or not label:
            raise ContractError("market labels must be nonempty strings")
        if not isinstance(phases, dict) or set(phases) != set(PHASES):
            raise ContractError("each market must declare early, middle, late; use null for gaps")
        market_rows, identities = [], []
        for phase in PHASES:
            raw = phases[phase]
            if raw is None:
                coverage.append({"market": label, "phase": phase, "status": "missing"})
                continue
            sequence = normalize_book_sequence(raw)
            identities.append(sequence["market_identity"])
            sources.append({
                "market": label, "phase": phase,
                "raw_sequence_sha256": raw["sequence_sha256"],
                "normalized_sequence_sha256": sequence["sequence_sha256"],
            })
            coverage.append({"market": label, "phase": phase, "status": "observed"})
            for index, bundle in enumerate(raw["samples"]):
                digest = bundle["bundle_sha256"]
                if digest in seen_bundles:
                    raise ContractError("duplicate raw bundle would inflate observation counts")
                seen_bundles.add(digest)
                normalized = normalize_bundle(bundle)
                contract = normalized["market_contract"]
                interpretation = interpret_market_bundle(
                    bundle, apply_current_documentation=apply_current_documentation
                )
                clob = bundle["observations"]["clob_market"]["payload"]
                metadata = {
                    "state": deepcopy(contract["state"]),
                    "constraints": deepcopy(contract["constraints"]),
                    "interpreted_fields": deepcopy(interpretation["fields"]),
                    "raw_features": {
                        key: {"present": key in clob, "value": deepcopy(clob.get(key))}
                        for key in ("r", "cbos", "aot", "ibce", "v")
                    },
                }
                market_rows.append({
                    "market": label, "phase": phase, "sample_index": index,
                    "condition_id": interpretation["condition_id"],
                    "observed_at_utc": interpretation["observed_at_utc"],
                    "raw_bundle_sha256": digest,
                    "clob_payload_sha256": interpretation["clob_payload_sha256"],
                    "interpretation_sha256": interpretation["interpretation_sha256"],
                    "metadata": metadata,
                })
        if not identities:
            raise ContractError("each declared market needs at least one observed phase")
        if any(identity != identities[0] for identity in identities):
            raise ContractError("market identity or outcome mapping differs across phases")
        condition = identities[0]["condition_id"]
        if condition in seen_conditions:
            raise ContractError("same condition declared under multiple market labels")
        seen_conditions.add(condition)
        market_rows.sort(key=lambda row: _moment(row["observed_at_utc"]))
        observed_phases = list(dict.fromkeys(row["phase"] for row in market_rows))
        if observed_phases != [phase for phase in PHASES if phases[phase] is not None]:
            raise ContractError("phase observations overlap or contradict declared order")
        for before, after in zip(market_rows, market_rows[1:]):
            if _moment(before["observed_at_utc"]) == _moment(after["observed_at_utc"]):
                raise ContractError("market metadata observations have ambiguous equal timestamps")
            changed = []
            for section, fields in before["metadata"].items():
                for field, old in fields.items():
                    new = after["metadata"][section][field]
                    if old != new:
                        changed.append({"field": section + "." + field,
                                        "before": old, "after": new})
            if changed:
                changes.append({
                    "market": label,
                    "comparison": "within_sequence" if before["phase"] == after["phase"] else "between_phases",
                    "from_phase": before["phase"], "to_phase": after["phase"],
                    "from_bundle_sha256": before["raw_bundle_sha256"],
                    "to_bundle_sha256": after["raw_bundle_sha256"],
                    "from_observed_at_utc": before["observed_at_utc"],
                    "to_observed_at_utc": after["observed_at_utc"],
                    "changes": changed,
                })
        rows.extend(market_rows)
    field_counts = {}
    for field in ("taker_order_delay_enabled", "minimum_order_age_seconds"):
        counts = Counter(row["metadata"]["interpreted_fields"][field]["basis"] for row in rows)
        field_counts[field] = {
            "observation_basis_counts": {
                basis: counts[basis] for basis in ("explicit_value", "documented_omission_default", "unknown")
            },
            "markets_with_any_unknown": len({row["market"] for row in rows
                if row["metadata"]["interpreted_fields"][field]["basis"] == "unknown"}),
        }
    market_summaries = []
    for label in sorted(markets):
        selected = [row for row in rows if row["market"] == label]
        market_summaries.append({
            "market": label, "condition_id": selected[0]["condition_id"],
            "observation_count": len(selected),
            "missing_phases": [phase for phase in PHASES if markets[label][phase] is None],
            "observed_change_count": sum(change["market"] == label for change in changes),
            "minimum_tick_sizes_observed": sorted({row["metadata"]["constraints"]["minimum_tick_size"] for row in selected}),
        })
    result = {
        "schema_version": AUDIT_SCHEMA, "policy_id": POLICY_ID,
        "apply_current_documentation": apply_current_documentation,
        "market_count": len(markets), "sequence_count": len(sources),
        "observation_count": len(rows),
        "missing_phase_count": sum(item["status"] == "missing" for item in coverage),
        "coverage": coverage, "sources": sources, "field_counts": field_counts,
        "market_summaries": market_summaries,
        "observations": rows, "observed_changes": changes,
        "replay_gate_changed": False,
        "limitations": [
            "Counts describe samples, not independent trials or success rates.",
            "No observed change does not establish continuous metadata stability.",
            "Missing phases remain evidence gaps; between-phase comparisons cross polling gaps.",
            "Raw rewards r.moas is not execution oas; reward features are descriptive only.",
            "Minimum order age operational scope remains unresolved even when explicit.",
            "Documentation defaults do not measure timing or establish historical settings.",
            "This report does not establish fills, profitability, or trading eligibility.",
        ],
    }
    result["audit_sha256"] = payload_hash(result)
    return result


def store_metadata_audit(result, directory):
    """Persist only a verified, content-addressed audit; never overwrite."""
    if result.get("schema_version") != AUDIT_SCHEMA:
        raise ContractError("unsupported metadata audit schema")
    verify_artifact_hash(result, "audit_sha256", "metadata audit")
    return _store_json(result, Path(directory) / ("metadata-audit-" + result["audit_sha256"] + ".json"))
