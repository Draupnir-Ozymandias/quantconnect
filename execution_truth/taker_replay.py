"""Deterministic BUY/FAK/FOK mechanics estimates from one captured book.

This API does not accept a research signal or issue a strategy eligibility
verdict. Aggregate depth cannot establish real matches or settlement.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP, localcontext

from .bundle import normalize_bundle
from .contracts import ContractError, payload_hash


REQUEST_SCHEMA = "qcrl.taker_replay_request.v1"
POLICY_SCHEMA = "qcrl.taker_replay_policy.v1"
RESULT_SCHEMA = "qcrl.taker_replay_result.v2"
SHARE_STEP = Decimal("0.000001")
FEE_STEP = Decimal("0.00001")


def _decimal(value, name, *, zero=False):
    if not isinstance(value, str) or len(value) > 64:
        raise ContractError(f"{name} must be a decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ContractError(f"{name} must be decimal") from exc
    if not number.is_finite() or number < 0 or (not zero and number == 0):
        raise ContractError(f"{name} is outside its valid range")
    if number > Decimal("1e12") or number.as_tuple().exponent < -12:
        raise ContractError(f"{name} exceeds replay numeric precision bounds")
    return number


def _text(number):
    value = format(number, "f")
    return (value.rstrip("0").rstrip(".") if "." in value else value) or "0"


def _time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ContractError("replay timestamps must be ISO-8601 strings") from exc
    if result.tzinfo is None:
        raise ContractError("replay timestamps must include a timezone")
    return result.astimezone(timezone.utc)


def _age_limit(policy, name):
    value = policy.get(name)
    if type(value) is not int or not 0 <= value <= 86400:
        raise ContractError(f"{name} must be an integer between 0 and 86400")
    return value


def replay_taker_buy(raw_bundle, request, policy):
    """Return a hashed mechanics estimate, with no network or input mutation."""
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_UP
        return _replay(raw_bundle, request, policy)


def _replay(raw_bundle, request, policy):
    if request.get("schema_version") != REQUEST_SCHEMA:
        raise ContractError("unsupported taker replay request schema")
    if policy.get("schema_version") != POLICY_SCHEMA:
        raise ContractError("unsupported taker replay policy schema")
    if request.get("side") != "BUY" or request.get("time_in_force") not in {"FAK", "FOK"}:
        raise ContractError("replay supports only BUY with FAK or FOK")
    if policy.get("depth_assumption") != "frozen_snapshot":
        raise ContractError("explicit frozen_snapshot depth assumption is required")
    if policy.get("fee_model") != "cash_equivalent_per_level_half_up_5dp":
        raise ContractError("unsupported replay fee model")
    book_age_limit = _age_limit(policy, "max_book_age_seconds")
    market_age_limit = _age_limit(policy, "max_market_age_seconds")
    exchange_age_limit = _age_limit(policy, "max_exchange_age_seconds")
    requested = _decimal(request.get("shares"), "shares")
    limit = _decimal(request.get("limit_price"), "limit_price")
    budget = _decimal(request.get("cash_budget"), "cash_budget", zero=True)
    if requested % SHARE_STEP:
        raise ContractError("shares must use at most six decimal places")
    at = _time(request.get("hypothetical_at_utc"))

    bundle = normalize_bundle(raw_bundle)
    market = bundle["market_contract"]
    books = [b for b in bundle["order_books"] if b["token_id"] == request.get("token_id")]
    if len(books) != 1:
        raise ContractError("requested token does not belong to the captured market")
    book = books[0]
    constraints = market["constraints"]
    tick = _decimal(constraints["minimum_tick_size"], "tick")
    if not tick <= limit <= 1 - tick or limit % tick:
        raise ContractError("limit price must respect market tick and price bounds")
    minimum = _decimal(constraints["minimum_order_size"], "minimum_order_size")
    curve = constraints["fee_curve"]
    rate = _decimal(curve["rate"], "fee_rate", zero=True)
    if rate > 1:
        raise ContractError("fee rate exceeds supported range")

    reasons = []
    if requested < minimum:
        reasons.append("below_minimum_order_size")
    observations = raw_bundle["observations"]
    for label in ("gamma_market", "clob_market"):
        age = (at - _time(observations[label]["observed_at_utc"])).total_seconds()
        if age < 0:
            reasons.append(f"{label}_observed_after_replay_time")
        elif age > market_age_limit:
            reasons.append(f"{label}_stale")
    observed = _time(book["observed_at_utc"])
    age = (at - observed).total_seconds()
    if age < 0:
        reasons.append("book_observed_after_replay_time")
    elif age > book_age_limit:
        reasons.append("book_stale")
    timestamp = book["exchange_timestamp"]
    if not timestamp.isascii() or not timestamp.isdigit() or len(timestamp) > 15:
        raise ContractError("exchange timestamp must be integer epoch milliseconds")
    try:
        exchange = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=int(timestamp))
    except OverflowError as exc:
        raise ContractError("exchange timestamp is out of range") from exc
    if exchange > observed:
        reasons.append("exchange_timestamp_after_observation")
    if (at - exchange).total_seconds() > exchange_age_limit:
        reasons.append("exchange_book_stale")
    if not _time(market["terms"]["event_start_at_utc"]) <= at < _time(market["terms"]["end_at_utc"]):
        reasons.append("outside_market_window")
    state = market["state"]
    if (state["active"] is not True or state["closed"] is not False
            or state["order_book_enabled"] is not True or state["accepting_orders"] is not True):
        reasons.append("market_not_orderable")
    if state["accepting_orders"] is None:
        reasons.append("unknown_order_acceptance_state")
    if constraints["taker_order_delay_enabled"] is None:
        reasons.append("unknown_taker_delay_state")
    elif constraints["taker_order_delay_enabled"]:
        reasons.append("taker_delay_requires_temporal_replay")
    if constraints["minimum_order_age_seconds"] is None:
        reasons.append("unknown_minimum_order_age")
    elif constraints["minimum_order_age_seconds"] != 0:
        reasons.append("order_age_constraint_unsupported")
    if book["negative_risk"]:
        reasons.append("negative_risk_unsupported")
    if curve["exponent"] != "1":
        reasons.append("fee_curve_exponent_unsupported")
    if state["fees_enabled"] is None:
        reasons.append("fee_enablement_unknown")
    elif not state["fees_enabled"] and rate != 0:
        reasons.append("fee_enablement_disagrees_with_curve")

    fills = []
    stop_reason = None
    remaining = requested
    remaining_cash = budget
    if not reasons:
        for level in book["asks"]:
            price = _decimal(level["price"], "ask.price")
            depth = _decimal(level["size"], "ask.size")
            if price % tick or not tick <= price <= 1 - tick:
                raise ContractError("ask violates market tick or price bounds")
            if price > limit:
                stop_reason = "price_limit"
                break
            maximum = min(remaining, depth).quantize(SHARE_STEP, rounding=ROUND_DOWN)
            fee_per_share = rate * price * (1 - price)

            def fee_for(quantity):
                return (quantity * fee_per_share).quantize(FEE_STEP, rounding=ROUND_HALF_UP)

            # Integer search respects both share precision and rounded fees.
            low, high = 0, int(maximum / SHARE_STEP)
            while low < high:
                middle = (low + high + 1) // 2
                quantity = middle * SHARE_STEP
                if quantity * price + fee_for(quantity) <= remaining_cash:
                    low = middle
                else:
                    high = middle - 1
            quantity = low * SHARE_STEP
            if quantity:
                fee = fee_for(quantity)
                cash = quantity * price
                fills.append({"price": _text(price), "shares": _text(quantity),
                              "notional": _text(cash), "fee_estimate": _text(fee)})
                remaining -= quantity
                remaining_cash -= cash + fee
            if remaining == 0:
                break
            if quantity < maximum:
                stop_reason = "cash_budget"
                break
        if remaining and stop_reason is None:
            stop_reason = "insufficient_depth"
        if request["time_in_force"] == "FOK" and remaining:
            fills = []
            reasons.append("fok_not_fully_fillable")

    filled = sum((Decimal(f["shares"]) for f in fills), Decimal(0))
    notional = sum((Decimal(f["notional"]) for f in fills), Decimal(0))
    fees = sum((Decimal(f["fee_estimate"]) for f in fills), Decimal(0))
    status = ("rejected" if reasons and reasons != ["fok_not_fully_fillable"] else
              "unfilled" if not filled else "filled" if filled == requested else "partial")
    result = {
        "schema_version": RESULT_SCHEMA,
        "evidence_role": "snapshot_mechanics_only",
        "strategy_eligibility_evaluated": False,
        "raw_bundle_sha256": raw_bundle["bundle_sha256"],
        "market_contract_sha256": market["contract_sha256"],
        "snapshot_sha256": book["snapshot_sha256"],
        "request": dict(request), "policy": dict(policy),
        "request_sha256": payload_hash(request), "policy_sha256": payload_hash(policy),
        "outcome": book["outcome"], "status": status,
        "reasons": reasons, "liquidity_stop_reason": stop_reason,
        "fills": fills, "filled_shares": _text(filled),
        "unfilled_shares": _text(requested - filled),
        "notional": _text(notional), "fee_estimate": _text(fees),
        "cash_required_estimate": _text(notional + fees),
        "cash_remaining_estimate": _text(budget - notional - fees),
        "average_price": _text(notional / filled) if filled else None,
        "all_in_unit_cost_estimate": _text((notional + fees) / filled) if filled else None,
        "limitations": ["displayed_depth_assumed_available",
                        "no_competing_orders_or_latency_path",
                        "aggregate_levels_hide_individual_match_fee_rounding",
                        "cash_equivalent_fee_estimate_not_wallet_settlement",
                        "no_signal_validation_or_profit_or_settlement_verdict"],
    }
    result["result_sha256"] = payload_hash(result)
    return result
