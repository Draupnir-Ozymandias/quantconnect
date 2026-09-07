"""Strict normalization contracts for public Polymarket observations.

The execution-truth layer treats remote payloads as evidence, not trusted
objects.  These functions contain no networking, credentials, or order logic.
They fail closed when two public sources disagree about market identity,
outcome-token mapping, or trading constraints.
"""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


MARKET_CONTRACT_SCHEMA = "qcrl.polymarket_market_contract.v2"
ORDER_BOOK_SCHEMA = "qcrl.polymarket_order_book.v1"

GAMMA_MARKET_ENDPOINT = "https://gamma-api.polymarket.com/markets/{id}"
CLOB_MARKET_ENDPOINT = (
    "https://clob.polymarket.com/clob-markets/{condition_id}"
)
CLOB_BOOK_ENDPOINT = "https://clob.polymarket.com/book?token_id={token_id}"


class ContractError(ValueError):
    """Raised when public evidence cannot satisfy a QCRL contract."""


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def payload_hash(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _required(mapping, key, context):
    value = mapping.get(key)
    if value is None or value == "":
        raise ContractError(f"{context}.{key} is required")
    return value


def _array(value, name):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractError(f"{name} is not valid JSON") from exc
    if not isinstance(value, list):
        raise ContractError(f"{name} must be an array or JSON array string")
    return value


def _utc_text(value, name):
    if not isinstance(value, str):
        raise ContractError(f"{name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _decimal_text(value, name, *, allow_zero=False, maximum=None):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{name} must be decimal") from exc
    if not number.is_finite():
        raise ContractError(f"{name} must be finite")
    if number < 0 or (number == 0 and not allow_zero):
        raise ContractError(f"{name} must be positive")
    if maximum is not None and number > Decimal(str(maximum)):
        raise ContractError(f"{name} exceeds {maximum}")
    text = format(number, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _bool(mapping, key, context):
    value = _required(mapping, key, context)
    if not isinstance(value, bool):
        raise ContractError(f"{context}.{key} must be boolean")
    return value


def _outcomes_from_gamma(payload):
    labels = _array(_required(payload, "outcomes", "gamma"), "gamma.outcomes")
    token_ids = _array(
        _required(payload, "clobTokenIds", "gamma"),
        "gamma.clobTokenIds",
    )
    if len(labels) != 2 or len(token_ids) != 2:
        raise ContractError("a binary market must expose exactly two outcomes")
    pairs = []
    for label, token_id in zip(labels, token_ids):
        label = str(label).strip()
        token_id = str(token_id).strip()
        if not label or not token_id:
            raise ContractError("outcome labels and token ids must be non-empty")
        pairs.append({"label": label, "token_id": token_id})
    if len({item["label"].casefold() for item in pairs}) != 2:
        raise ContractError("outcome labels must be unique")
    if len({item["token_id"] for item in pairs}) != 2:
        raise ContractError("outcome token ids must be unique")
    return pairs


def _outcomes_from_clob(payload):
    tokens = _array(_required(payload, "t", "clob_market"), "clob_market.t")
    if len(tokens) != 2:
        raise ContractError("CLOB market must expose exactly two tokens")
    result = []
    for index, token in enumerate(tokens):
        if not isinstance(token, dict):
            raise ContractError(f"clob_market.t[{index}] must be an object")
        result.append({
            "label": str(_required(token, "o", f"clob_market.t[{index}]")).strip(),
            "token_id": str(_required(token, "t", f"clob_market.t[{index}]")).strip(),
        })
    return result


def normalize_market_contract(gamma_payload, clob_payload, observed_at_utc):
    """Join Gamma identity/terms to CLOB V2 constraints and validate both."""
    if not isinstance(gamma_payload, dict) or not isinstance(clob_payload, dict):
        raise ContractError("market source payloads must be objects")

    gamma_outcomes = _outcomes_from_gamma(gamma_payload)
    clob_outcomes = _outcomes_from_clob(clob_payload)
    gamma_by_token = {item["token_id"]: item["label"] for item in gamma_outcomes}
    clob_by_token = {item["token_id"]: item["label"] for item in clob_outcomes}
    if set(gamma_by_token) != set(clob_by_token):
        raise ContractError("Gamma and CLOB token ids disagree")
    for token_id, gamma_label in gamma_by_token.items():
        if gamma_label.casefold() != clob_by_token[token_id].casefold():
            raise ContractError("Gamma and CLOB outcome labels disagree")

    clob_condition_id = str(
        _required(clob_payload, "c", "clob_market")
    )
    gamma_condition_id = str(
        _required(gamma_payload, "conditionId", "gamma")
    )
    if clob_condition_id != gamma_condition_id:
        raise ContractError("Gamma and CLOB condition ids disagree")

    listed_at = _utc_text(_required(gamma_payload, "startDate", "gamma"), "gamma.startDate")
    event_start_at = _utc_text(
        _required(gamma_payload, "eventStartTime", "gamma"),
        "gamma.eventStartTime",
    )
    end_at = _utc_text(_required(gamma_payload, "endDate", "gamma"), "gamma.endDate")
    if _utc_datetime(end_at) <= _utc_datetime(event_start_at):
        raise ContractError("market end must be after event start")
    if _utc_datetime(event_start_at) < _utc_datetime(listed_at):
        raise ContractError("event start must not precede Gamma startDate")

    fee = _required(clob_payload, "fd", "clob_market")
    if not isinstance(fee, dict):
        raise ContractError("clob_market.fd must be an object")

    contract = {
        "schema_version": MARKET_CONTRACT_SCHEMA,
        "observed_at_utc": _utc_text(observed_at_utc, "observed_at_utc"),
        "identity": {
            "market_id": str(_required(gamma_payload, "id", "gamma")),
            "condition_id": gamma_condition_id,
            "question_id": str(
                _required(gamma_payload, "questionID", "gamma")
            ),
            "slug": str(_required(gamma_payload, "slug", "gamma")),
        },
        "terms": {
            "question": str(_required(gamma_payload, "question", "gamma")),
            "description": str(
                _required(gamma_payload, "description", "gamma")
            ),
            "resolution_source": str(
                _required(gamma_payload, "resolutionSource", "gamma")
            ),
            "gamma_start_at_utc": listed_at,
            "event_start_at_utc": event_start_at,
            "end_at_utc": end_at,
        },
        "state": {
            "active": _bool(gamma_payload, "active", "gamma"),
            "closed": _bool(gamma_payload, "closed", "gamma"),
            "order_book_enabled": _bool(
                gamma_payload, "enableOrderBook", "gamma"
            ),
            "accepting_orders": bool(gamma_payload.get("acceptingOrders", False)),
        },
        "outcomes": gamma_outcomes,
        "constraints": {
            "minimum_order_size": _decimal_text(
                _required(clob_payload, "mos", "clob_market"),
                "clob_market.mos",
            ),
            "minimum_tick_size": _decimal_text(
                _required(clob_payload, "mts", "clob_market"),
                "clob_market.mts",
                maximum=1,
            ),
            "maker_base_fee_bps": int(
                _required(clob_payload, "mbf", "clob_market")
            ),
            "taker_base_fee_bps": int(
                _required(clob_payload, "tbf", "clob_market")
            ),
            "fee_curve": {
                "rate": _decimal_text(
                    _required(fee, "r", "clob_market.fd"),
                    "clob_market.fd.r",
                    allow_zero=True,
                ),
                "exponent": _decimal_text(
                    _required(fee, "e", "clob_market.fd"),
                    "clob_market.fd.e",
                    allow_zero=True,
                ),
                "taker_only": _bool(fee, "to", "clob_market.fd"),
            },
            "taker_order_delay_enabled": bool(clob_payload.get("itode", False)),
            "minimum_order_age_seconds": int(clob_payload.get("oas", 0)),
        },
        "sources": {
            "gamma": {
                "endpoint": GAMMA_MARKET_ENDPOINT.format(
                    id=gamma_payload["id"]
                ),
                "payload_sha256": payload_hash(gamma_payload),
            },
            "clob_market": {
                "endpoint": CLOB_MARKET_ENDPOINT.format(
                    condition_id=gamma_payload["conditionId"]
                ),
                "payload_sha256": payload_hash(clob_payload),
            },
        },
    }
    contract["contract_sha256"] = payload_hash(contract)
    return contract


def _levels(payload, side):
    values = _array(_required(payload, side, "order_book"), f"order_book.{side}")
    levels = []
    seen = set()
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ContractError(f"order_book.{side}[{index}] must be an object")
        price = _decimal_text(
            _required(value, "price", f"order_book.{side}[{index}]"),
            f"order_book.{side}[{index}].price",
            maximum=1,
        )
        size = _decimal_text(
            _required(value, "size", f"order_book.{side}[{index}]"),
            f"order_book.{side}[{index}].size",
        )
        if price in seen:
            raise ContractError(f"order_book.{side} contains duplicate prices")
        seen.add(price)
        levels.append({"price": price, "size": size})
    reverse = side == "bids"
    return sorted(levels, key=lambda item: Decimal(item["price"]), reverse=reverse)


def normalize_order_book(book_payload, market_contract, observed_at_utc):
    """Normalize a full CLOB book and bind it to a validated market contract."""
    if market_contract.get("schema_version") != MARKET_CONTRACT_SCHEMA:
        raise ContractError("unsupported market contract schema")
    condition_id = str(_required(book_payload, "market", "order_book"))
    token_id = str(_required(book_payload, "asset_id", "order_book"))
    if condition_id != market_contract["identity"]["condition_id"]:
        raise ContractError("order book condition id does not match market")
    token_ids = {item["token_id"] for item in market_contract["outcomes"]}
    if token_id not in token_ids:
        raise ContractError("order book token id does not belong to market")

    tick_size = _decimal_text(
        _required(book_payload, "tick_size", "order_book"),
        "order_book.tick_size",
        maximum=1,
    )
    minimum_order_size = _decimal_text(
        _required(book_payload, "min_order_size", "order_book"),
        "order_book.min_order_size",
    )
    constraints = market_contract["constraints"]
    if tick_size != constraints["minimum_tick_size"]:
        raise ContractError("order book tick size disagrees with market contract")
    if minimum_order_size != constraints["minimum_order_size"]:
        raise ContractError("order book minimum size disagrees with market contract")

    bids = _levels(book_payload, "bids")
    asks = _levels(book_payload, "asks")
    if bids and asks and Decimal(bids[0]["price"]) >= Decimal(asks[0]["price"]):
        raise ContractError("order book is crossed or locked")

    snapshot = {
        "schema_version": ORDER_BOOK_SCHEMA,
        "observed_at_utc": _utc_text(observed_at_utc, "observed_at_utc"),
        "market_contract_sha256": market_contract["contract_sha256"],
        "condition_id": condition_id,
        "token_id": token_id,
        "outcome": next(
            item["label"] for item in market_contract["outcomes"]
            if item["token_id"] == token_id
        ),
        "exchange_timestamp": str(
            _required(book_payload, "timestamp", "order_book")
        ),
        "exchange_book_hash": str(_required(book_payload, "hash", "order_book")),
        "bids": bids,
        "asks": asks,
        "best_bid": bids[0] if bids else None,
        "best_ask": asks[0] if asks else None,
        "last_trade_price": _decimal_text(
            _required(book_payload, "last_trade_price", "order_book"),
            "order_book.last_trade_price",
            maximum=1,
        ),
        "minimum_order_size": minimum_order_size,
        "tick_size": tick_size,
        "negative_risk": _bool(book_payload, "neg_risk", "order_book"),
        "source": {
            "endpoint": CLOB_BOOK_ENDPOINT.format(token_id=token_id),
            "payload_sha256": payload_hash(book_payload),
        },
    }
    snapshot["snapshot_sha256"] = payload_hash(snapshot)
    return snapshot
