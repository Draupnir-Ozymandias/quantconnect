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


NORMALIZED_BUNDLE_SCHEMA = "qcrl.polymarket_normalized_bundle.v1"


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
