"""Offline verification, normalization, and storage of Polymarket bundles."""

import json
from pathlib import Path

from .acquisition import RAW_BUNDLE_SCHEMA
from .contracts import (
    ContractError,
    normalize_market_contract,
    normalize_order_book,
    payload_hash,
)
from .discovery import verify_raw_discovery


NORMALIZED_BUNDLE_SCHEMA = "qcrl.polymarket_normalized_bundle.v2"
LIVE_INVENTORY_SCHEMA = "qcrl.polymarket_live_evidence_inventory.v1"


def _verify_observation(observation, name):
    if not isinstance(observation, dict):
        raise ContractError(f"{name} must be an observation object")
    payload = observation.get("payload")
    if not isinstance(payload, dict):
        raise ContractError(f"{name}.payload must be an object")
    if observation.get("payload_sha256") != payload_hash(payload):
        raise ContractError(f"{name} payload hash mismatch")
    if not observation.get("observed_at_utc"):
        raise ContractError(f"{name}.observed_at_utc is required")
    if not observation.get("endpoint"):
        raise ContractError(f"{name}.endpoint is required")
    return payload


def normalize_bundle(raw_bundle):
    """Verify raw evidence and derive a deterministic offline bundle."""
    if raw_bundle.get("schema_version") != RAW_BUNDLE_SCHEMA:
        raise ContractError("unsupported raw bundle schema")
    supplied_hash = raw_bundle.get("bundle_sha256")
    unhashed = dict(raw_bundle)
    unhashed.pop("bundle_sha256", None)
    if supplied_hash != payload_hash(unhashed):
        raise ContractError("raw bundle hash mismatch")

    observations = raw_bundle.get("observations")
    if not isinstance(observations, dict):
        raise ContractError("raw bundle observations are required")
    gamma_observation = observations.get("gamma_market")
    clob_observation = observations.get("clob_market")
    gamma = _verify_observation(gamma_observation, "gamma_market")
    clob = _verify_observation(clob_observation, "clob_market")

    contract = normalize_market_contract(
        gamma,
        clob,
        clob_observation["observed_at_utc"],
    )
    book_observations = observations.get("order_books")
    if not isinstance(book_observations, list) or len(book_observations) != 2:
        raise ContractError("raw bundle must contain exactly two order books")
    books = []
    for index, observation in enumerate(book_observations):
        payload = _verify_observation(observation, f"order_books[{index}]")
        books.append(normalize_order_book(
            payload, contract, observation["observed_at_utc"]
        ))
    expected_tokens = {item["token_id"] for item in contract["outcomes"]}
    actual_tokens = {item["token_id"] for item in books}
    if actual_tokens != expected_tokens:
        raise ContractError("normalized bundle does not cover both outcomes")

    normalized = {
        "schema_version": NORMALIZED_BUNDLE_SCHEMA,
        "raw_bundle_sha256": supplied_hash,
        "market_contract": contract,
        "order_books": books,
    }
    normalized["bundle_sha256"] = payload_hash(normalized)
    return normalized


def store_raw_bundle(raw_bundle, directory):
    """Store immutable raw evidence under a content-addressed filename."""
    supplied_hash = raw_bundle.get("bundle_sha256")
    unhashed = dict(raw_bundle)
    unhashed.pop("bundle_sha256", None)
    if supplied_hash != payload_hash(unhashed):
        raise ContractError("raw bundle hash mismatch")
    market_id = str(raw_bundle.get("market_id_requested") or "").strip()
    if not market_id or any(char not in "0123456789" for char in market_id):
        raise ContractError("raw bundle market id must be numeric")

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"market-{market_id}-{supplied_hash}.json"
    content = json.dumps(raw_bundle, sort_keys=True, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != content:
            raise ContractError("content-addressed bundle path has different data")
        return target
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)
    return target


def store_raw_discovery(raw_discovery, directory):
    """Store immutable discovery evidence under a content-addressed filename."""
    supplied_hash = verify_raw_discovery(raw_discovery)
    series_id = str(raw_discovery.get("series_id_requested") or "").strip()
    if not series_id or not series_id.isdigit():
        raise ContractError("raw discovery series id must be numeric")
    return _store_json(
        raw_discovery,
        Path(directory) / f"series-{series_id}-{supplied_hash}.json",
    )


def store_raw_book_sequence(raw_sequence, directory):
    """Store an immutable verified sequence under a content-addressed filename."""
    from .book_sequence import normalize_book_sequence

    normalize_book_sequence(raw_sequence)
    market_id = str(raw_sequence.get("market_id_requested") or "").strip()
    supplied_hash = raw_sequence["sequence_sha256"]
    return _store_json(
        raw_sequence,
        Path(directory) / f"sequence-market-{market_id}-{supplied_hash}.json",
    )


def promote_raw_evidence(source, directory):
    """Verify and copy one raw artifact into the durable evidence directory."""
    source = Path(source)
    try:
        artifact = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read raw evidence: {source}") from exc
    schema = artifact.get("schema_version")
    if schema == RAW_BUNDLE_SCHEMA:
        normalize_bundle(artifact)
        return store_raw_bundle(artifact, directory)
    if schema == "qcrl.polymarket_raw_discovery.v1":
        return store_raw_discovery(artifact, directory)
    if schema == "qcrl.polymarket_raw_book_sequence.v1":
        return store_raw_book_sequence(artifact, directory)
    raise ContractError("unsupported raw evidence schema")


def _store_json(value, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, sort_keys=True, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != content:
            raise ContractError("content-addressed evidence path has different data")
        return target
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)
    return target


def verify_live_evidence_inventory(directory):
    """Verify every durable artifact is declared, hashed, and replayable."""
    directory = Path(directory)
    inventory_path = directory / "inventory.json"
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("live evidence inventory is unreadable") from exc
    if inventory.get("schema_version") != LIVE_INVENTORY_SCHEMA:
        raise ContractError("unsupported live evidence inventory schema")
    entries = inventory.get("artifacts")
    if not isinstance(entries, list) or not entries:
        raise ContractError("live evidence inventory must declare artifacts")

    declared = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ContractError("inventory artifact declaration must be an object")
        relative = str(entry.get("path") or "")
        relative_path = Path(relative)
        if (
            not relative.startswith("raw/")
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.suffix != ".json"
        ):
            raise ContractError("inventory artifact path must be under raw/")
        if relative in declared:
            raise ContractError("inventory contains a duplicate artifact path")
        declared.add(relative)
        path = directory / relative
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"inventory artifact is unreadable: {relative}") from exc
        schema = artifact.get("schema_version")
        if schema != entry.get("schema_version"):
            raise ContractError(f"inventory schema mismatch: {relative}")
        if schema == RAW_BUNDLE_SCHEMA:
            normalized = normalize_bundle(artifact)
            artifact_hash = artifact.get("bundle_sha256")
            if normalized["bundle_sha256"] != entry.get("normalized_sha256"):
                raise ContractError(f"inventory normalized hash mismatch: {relative}")
        elif schema == "qcrl.polymarket_raw_discovery.v1":
            artifact_hash = verify_raw_discovery(artifact)
        elif schema == "qcrl.polymarket_raw_book_sequence.v1":
            from .book_sequence import normalize_book_sequence

            normalized = normalize_book_sequence(artifact)
            artifact_hash = artifact.get("sequence_sha256")
            if normalized["sequence_sha256"] != entry.get("normalized_sha256"):
                raise ContractError(f"inventory normalized hash mismatch: {relative}")
        else:
            raise ContractError(f"unsupported inventory artifact: {relative}")
        if artifact_hash != entry.get("artifact_sha256"):
            raise ContractError(f"inventory artifact hash mismatch: {relative}")
        captured_at = artifact.get("acquired_at_utc", artifact.get("capture_started_at_utc"))
        if entry.get("captured_at_utc") != captured_at:
            raise ContractError(f"inventory capture time mismatch: {relative}")
        if not str(entry.get("evidence_role") or "").strip():
            raise ContractError(f"inventory evidence_role is required: {relative}")
        limitations = entry.get("limitations")
        if not isinstance(limitations, list) or not limitations:
            raise ContractError(f"inventory limitations are required: {relative}")

    actual = {
        str(path.relative_to(directory))
        for path in (directory / "raw").glob("*.json")
    }
    if actual != declared:
        raise ContractError("live evidence files and inventory declarations differ")
    return len(entries)
