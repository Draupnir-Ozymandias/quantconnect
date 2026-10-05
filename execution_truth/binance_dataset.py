"""Assemble offline calendar datasets from pinned retained resolution artifacts."""

import copy
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .binance_resolution import normalize_resolution_candles
from .binance_source import adapt_boundary_dataset, _time
from .bundle import _store_json
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .research_lane import load_research_lane


SPEC_SCHEMA = "qcrl.binance_boundary_assembly_spec.v1"
RESULT_SCHEMA = "qcrl.binance_boundary_assembly.v1"


def assemble_boundary_evidence(spec_path):
    """Read-only verified assembly; preserve all gaps and contributing observations."""
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != SPEC_SCHEMA:
        raise ContractError("unsupported boundary assembly schema")
    lane = load_research_lane(spec_path.parent / spec["declaration_path"])
    if spec.get("declaration_sha256") != lane["declaration_sha256"]:
        raise ContractError("assembly declaration hash mismatch")
    sources = spec.get("sources")
    if not isinstance(sources, list) or not sources or len(sources) > 10000:
        raise ContractError("assembly requires a bounded nonempty source list")
    manifest, by_date, seen = [], {}, set()
    eastern = ZoneInfo(lane["source"]["timezone"])
    for source in sources:
        data = (spec_path.parent / source["path"]).read_bytes()
        file_hash = hashlib.sha256(data).hexdigest()
        if file_hash != source.get("file_sha256"):
            raise ContractError("assembly source file hash mismatch")
        raw = json.loads(data)
        normalized = normalize_resolution_candles(raw)
        artifact_hash = raw["resolution_candles_sha256"]
        if artifact_hash in seen:
            raise ContractError("duplicate assembly source artifact")
        seen.add(artifact_hash)
        if raw["market_id"] != source.get("market_id"):
            raise ContractError("assembly source market identity mismatch")
        manifest.append({"path": source["path"], "file_sha256": file_hash,
                         "artifact_sha256": artifact_hash, "market_id": raw["market_id"],
                         "normalized_resolution_sha256": normalized["resolution_record_sha256"]})
        for key in ("start_candle", "end_candle"):
            observation = copy.deepcopy(raw["observations"][key])
            at = _time(normalized[key]["boundary_at_utc"])
            local = at.astimezone(eastern)
            if (local.hour, local.minute, local.second, local.microsecond) != (12, 0, 0, 0):
                raise ContractError("assembly source boundary is not Eastern calendar noon")
            day = local.date().isoformat()
            reference = {"artifact_sha256": artifact_hash, "file_sha256": file_hash,
                         "observation_key": key, "observation_sha256": payload_hash(observation)}
            if day not in by_date:
                by_date[day] = {"boundary_local_date": day, "observation": observation,
                                "source_references": [reference]}
            else:
                entry = by_date[day]
                if entry["observation"]["payload_sha256"] != observation["payload_sha256"]:
                    raise ContractError("conflicting payloads for shared boundary candle")
                entry["source_references"].append(reference)
                # Conservatively retain the latest actual retrieval, never an invented time.
                if _time(observation["observed_at_utc"]) > _time(entry["observation"]["observed_at_utc"]):
                    entry["observation"] = observation
    dataset = {
        "schema_version": "qcrl.binance_boundary_dataset.v1",
        "declaration_sha256": lane["declaration_sha256"],
        "evidence_role": "historical_retrieval", "evidence_class": "captured_public_observation",
        "first_boundary_local_date": spec["first_boundary_local_date"],
        "last_boundary_local_date": spec["last_boundary_local_date"],
        "assembly_spec_sha256": payload_hash(spec), "source_manifest": manifest,
        "observations": [by_date[day] for day in sorted(by_date)],
    }
    dataset["dataset_sha256"] = payload_hash(dataset)
    audit = adapt_boundary_dataset(lane, dataset)
    result = {
        "schema_version": RESULT_SCHEMA, "assembly_spec_sha256": payload_hash(spec),
        "declaration_sha256": lane["declaration_sha256"], "source_count": len(manifest),
        "dataset": dataset, "source_audit": audit,
        "limitations": [
            "Retained settlement-check candles are sparse, not a strategy research sample.",
            "Source manifest paths are relative to the versioned assembly specification.",
            "Identical shared candles retain all references and the latest retrieval time.",
            "Conflicting shared payloads reject assembly rather than selecting a revision.",
            "No acquisition, signal emission, campaign, or trading authorization occurs.",
        ],
    }
    result["assembly_sha256"] = payload_hash(result)
    return result


def store_boundary_assembly(result, directory):
    if result.get("schema_version") != RESULT_SCHEMA:
        raise ContractError("unsupported boundary assembly result")
    verify_artifact_hash(result, "assembly_sha256", "boundary assembly")
    verify_artifact_hash(result["dataset"], "dataset_sha256", "boundary dataset")
    verify_artifact_hash(result["source_audit"], "audit_sha256", "source audit")
    return _store_json(result, Path(directory) / ("boundary-assembly-" + result["assembly_sha256"] + ".json"))
