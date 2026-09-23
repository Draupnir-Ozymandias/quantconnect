"""Offline normalization and reconciliation of public settlement evidence."""

import json
from decimal import Decimal, InvalidOperation

from .book_sequence import normalize_book_sequence
from .contracts import ContractError, payload_hash, verify_artifact_hash


RAW_SETTLEMENT_SCHEMA = "qcrl.polymarket_raw_settlement.v1"
SETTLEMENT_SCHEMA = "qcrl.polymarket_settlement.v1"
RECONCILIATION_SCHEMA = "qcrl.polymarket_settlement_reconciliation.v1"
COHORT_RECONCILIATION_SCHEMA = "qcrl.polymarket_settlement_cohort.v1"


def _array(value, name):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{name} is not valid JSON") from exc
    if not isinstance(value, list):
        raise ContractError(f"{name} must be an array or JSON array string")
    return value


def _observation(raw, key):
    value = raw.get("observations", {}).get(key)
    if not isinstance(value, dict) or not isinstance(value.get("payload"), dict):
        raise ContractError(f"settlement {key} observation is required")
    if value.get("payload_sha256") != payload_hash(value["payload"]):
        raise ContractError(f"settlement {key} payload hash mismatch")
    if not value.get("observed_at_utc") or not value.get("endpoint"):
        raise ContractError(f"settlement {key} observation metadata is required")
    return value


def _price(value, name):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{name} must be decimal") from exc
    if not number.is_finite() or not Decimal(0) <= number <= Decimal(1):
        raise ContractError(f"{name} must be between zero and one")
    text = format(number, "f")
    return (text.rstrip("0").rstrip(".") if "." in text else text) or "0"


def normalize_settlement(raw):
    """Verify Gamma/CLOB identity and derive the platform-reported payout state."""
    if raw.get("schema_version") != RAW_SETTLEMENT_SCHEMA:
        raise ContractError("unsupported raw settlement schema")
    verify_artifact_hash(raw, "settlement_sha256", "raw settlement")
    gamma_observation = _observation(raw, "gamma_market")
    clob_observation = _observation(raw, "clob_market")
    gamma = gamma_observation["payload"]
    clob = clob_observation["payload"]

    market_id = str(gamma.get("id") or "")
    if market_id != str(raw.get("market_id_requested") or ""):
        raise ContractError("settlement Gamma market id mismatch")
    condition_id = str(gamma.get("conditionId") or "")
    if not condition_id or str(clob.get("c") or "") != condition_id:
        raise ContractError("settlement Gamma and CLOB condition ids disagree")

    labels = _array(gamma.get("outcomes"), "gamma.outcomes")
    tokens = _array(gamma.get("clobTokenIds"), "gamma.clobTokenIds")
    prices = _array(gamma.get("outcomePrices"), "gamma.outcomePrices")
    clob_tokens = _array(clob.get("t"), "clob_market.t")
    if not len(labels) == len(tokens) == len(prices) == len(clob_tokens) == 2:
        raise ContractError("settlement evidence must describe two outcomes")

    outcomes = []
    for index, (label, token, price) in enumerate(zip(labels, tokens, prices)):
        item = clob_tokens[index]
        if not isinstance(item, dict):
            raise ContractError("settlement CLOB token must be an object")
        label = str(label).strip()
        token = str(token).strip()
        if str(item.get("o") or "").casefold() != label.casefold():
            raise ContractError("settlement Gamma and CLOB outcome labels disagree")
        if str(item.get("t") or "") != token:
            raise ContractError("settlement Gamma and CLOB token ids disagree")
        outcomes.append({"label": label, "token_id": token, "payout": _price(
            price, f"gamma.outcomePrices[{index}]"
        )})

    closed = gamma.get("closed")
    accepting = gamma.get("acceptingOrders")
    resolution = gamma.get("umaResolutionStatus")
    if not isinstance(closed, bool) or not isinstance(accepting, bool):
        raise ContractError("settlement orderability flags must be boolean")
    resolved = resolution == "resolved"
    result_type = None
    winner = None
    payout_vector = [item["payout"] for item in outcomes]
    if resolved:
        if not closed or accepting:
            raise ContractError("resolved settlement must be closed to orders")
        if sorted(payout_vector) == ["0", "1"]:
            result_type = "single_winner"
            winner = next(item for item in outcomes if item["payout"] == "1")
        elif payout_vector == ["0.5", "0.5"]:
            result_type = "split"
        else:
            raise ContractError("resolved settlement has unsupported payout vector")

    result = {
        "schema_version": SETTLEMENT_SCHEMA,
        "raw_settlement_sha256": raw["settlement_sha256"],
        "observed_at_utc": raw["acquired_at_utc"],
        "market_id": market_id,
        "condition_id": condition_id,
        "slug": str(gamma.get("slug") or ""),
        "closed": closed,
        "accepting_orders": accepting,
        "platform_resolution_status": resolution,
        "status": "resolved" if resolved else "pending",
        "result_type": result_type,
        "outcomes": outcomes,
        "winner": winner,
        "sources": {
            "gamma_market": {
                "endpoint": gamma_observation["endpoint"],
                "payload_sha256": gamma_observation["payload_sha256"],
            },
            "clob_market": {
                "endpoint": clob_observation["endpoint"],
                "payload_sha256": clob_observation["payload_sha256"],
            },
        },
        "limitations": [
            "platform-reported payout state is not independent verification of the resolution source",
            "settlement metadata does not establish order fill, wallet credit, or redemption",
        ],
    }
    result["settlement_record_sha256"] = payload_hash(result)
    return result


def reconcile_settlement(raw_settlement, raw_sequences):
    """Join platform settlement to the latest observed phase book without fill claims."""
    settlement = normalize_settlement(raw_settlement)
    if settlement["status"] != "resolved":
        raise ContractError("settlement reconciliation requires resolved evidence")
    if not isinstance(raw_sequences, list) or not raw_sequences:
        raise ContractError("settlement reconciliation requires observed sequences")

    sequences = [normalize_book_sequence(raw) for raw in raw_sequences]
    if any(item["market_identity"]["market_id"] != settlement["market_id"]
           for item in sequences):
        raise ContractError("settlement and sequence market ids disagree")
    expected = {(item["label"], item["token_id"]) for item in settlement["outcomes"]}
    if any({(item["label"], item["token_id"])
            for item in sequence["market_identity"]["outcomes"]} != expected
           for sequence in sequences):
        raise ContractError("settlement and sequence outcomes disagree")

    latest_index = max(
        range(len(raw_sequences)),
        key=lambda index: raw_sequences[index]["capture_completed_at_utc"],
    )
    latest_raw = raw_sequences[latest_index]
    latest = sequences[latest_index]
    sample = latest["samples"][-1]
    books = []
    reference_prices = {}
    for outcome in settlement["outcomes"]:
        book = next(item for item in sample["books"] if item["token_id"] == outcome["token_id"])
        if book["best_bid"] and book["best_ask"]:
            reference = (
                Decimal(book["best_bid"]["price"]) + Decimal(book["best_ask"]["price"])
            ) / Decimal(2)
        elif book["best_bid"]:
            reference = Decimal(book["best_bid"]["price"])
        elif book["best_ask"]:
            reference = Decimal(book["best_ask"]["price"])
        else:
            reference = None
        reference_prices[outcome["label"]] = reference
        books.append({
            "outcome": outcome["label"],
            "token_id": outcome["token_id"],
            "best_bid": book["best_bid"],
            "best_ask": book["best_ask"],
            "reference_price": _price(reference, "reference price") if reference is not None else None,
            "snapshot_sha256": book["snapshot_sha256"],
        })

    direction_consistent = None
    if settlement["result_type"] == "single_winner":
        winner_label = settlement["winner"]["label"]
        loser_label = next(item["label"] for item in settlement["outcomes"]
                           if item["label"] != winner_label)
        if reference_prices[winner_label] is not None and reference_prices[loser_label] is not None:
            direction_consistent = reference_prices[winner_label] > reference_prices[loser_label]

    result = {
        "schema_version": RECONCILIATION_SCHEMA,
        "evidence_role": "platform_settlement_to_last_observed_book_reconciliation",
        "settlement": settlement,
        "observed_sequence_count": len(sequences),
        "latest_sequence_sha256": latest_raw["sequence_sha256"],
        "latest_normalized_sequence_sha256": latest["sequence_sha256"],
        "latest_capture_completed_at_utc": latest["capture_completed_at_utc"],
        "latest_books": books,
        "winning_direction_consistent_with_latest_reference_prices": direction_consistent,
        "limitations": [
            "latest public book is not necessarily the terminal pre-resolution book",
            "book direction consistency is descriptive and is not a prediction score",
            "platform settlement is not independently reconciled to Binance candles",
            "no order, fill, wallet settlement, redemption, or profitability is established",
        ],
    }
    result["reconciliation_sha256"] = payload_hash(result)
    return result


def reconcile_settlement_cohort(markets):
    """Reconcile multiple resolved markets without treating outcomes as forecasts."""
    if not isinstance(markets, dict) or not markets:
        raise ContractError("settlement cohort requires markets")
    results = {}
    seen_market_ids = set()
    for label in sorted(markets):
        inputs = markets[label]
        if not isinstance(inputs, dict) or set(inputs) != {"settlement", "sequences"}:
            raise ContractError("settlement cohort market inputs are invalid")
        result = reconcile_settlement(inputs["settlement"], inputs["sequences"])
        market_id = result["settlement"]["market_id"]
        if market_id in seen_market_ids:
            raise ContractError("settlement cohort contains a duplicate market")
        seen_market_ids.add(market_id)
        results[label] = result

    winner_counts = {}
    consistency_counts = {"true": 0, "false": 0, "unknown": 0}
    for result in results.values():
        winner = result["settlement"]["winner"]
        if winner:
            winner_counts[winner["label"]] = winner_counts.get(winner["label"], 0) + 1
        consistent = result["winning_direction_consistent_with_latest_reference_prices"]
        key = "unknown" if consistent is None else str(consistent).lower()
        consistency_counts[key] += 1

    result = {
        "schema_version": COHORT_RECONCILIATION_SCHEMA,
        "evidence_role": "platform_settlement_cohort_reconciliation",
        "market_count": len(results),
        "winner_counts": dict(sorted(winner_counts.items())),
        "latest_book_direction_consistency_counts": consistency_counts,
        "markets": results,
        "limitations": [
            "winner counts are realized outcomes and must not be used to tune the frozen signal",
            "latest observed books are sparse phase samples rather than terminal price paths",
            "platform settlement is not independent Binance resolution-source verification",
            "no order, fill, wallet settlement, redemption, or profitability is established",
        ],
    }
    result["cohort_sha256"] = payload_hash(result)
    return result
