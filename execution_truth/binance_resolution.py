"""Independent Binance candle evidence for daily-market resolution checks."""

import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .acquisition import AcquisitionError, utc_now, utc_text
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .settlement import normalize_settlement


RAW_BINANCE_RESOLUTION_SCHEMA = "qcrl.binance_raw_resolution_candles.v1"
BINANCE_RESOLUTION_SCHEMA = "qcrl.binance_resolution_candles.v1"
BINANCE_RECONCILIATION_SCHEMA = "qcrl.binance_settlement_reconciliation.v1"
BINANCE_COHORT_SCHEMA = "qcrl.binance_settlement_cohort.v1"
BINANCE_KLINES_ENDPOINT = "https://data-api.binance.vision/api/v3/klines"
DECLARED_RESOLUTION_SOURCE = "https://www.binance.com/en/trade/BTC_USDT"


def _time(value, name):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _millis(value):
    return int(value.timestamp() * 1000)


def _decimal(value, name):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContractError(f"{name} must be decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ContractError(f"{name} must be finite and positive")
    return number


def _decimal_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


class BinanceJsonTransport:
    """Minimal public JSON transport that permits the array returned by klines."""

    def __init__(self, timeout_seconds=20):
        self.timeout_seconds = timeout_seconds

    def get_json(self, url, params):
        complete_url = f"{url}?{urlencode(params)}"
        request = Request(complete_url, headers={"User-Agent": "QCRL-execution-truth/1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AcquisitionError(f"public GET failed: {complete_url}: {exc}") from exc


class PublicBinanceAcquirer:
    """Acquire the two exact public one-minute candles named by a market."""

    def __init__(self, transport=None, clock=None):
        self.transport = transport or BinanceJsonTransport()
        self.clock = clock or utc_now

    def _observe_candle(self, boundary):
        start_ms = _millis(boundary)
        params = {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "startTime": start_ms,
            "endTime": start_ms + 59999,
            "limit": 1,
        }
        payload = self.transport.get_json(BINANCE_KLINES_ENDPOINT, params)
        return {
            "observed_at_utc": utc_text(self.clock()),
            "endpoint": BINANCE_KLINES_ENDPOINT,
            "params": params,
            "payload_sha256": payload_hash(payload),
            "payload": payload,
        }

    def acquire_resolution_candles(self, market_id, event_start_at_utc,
                                   event_end_at_utc):
        market_id = str(market_id).strip()
        if not market_id.isdigit():
            raise AcquisitionError("market_id must be numeric")
        try:
            start = _time(event_start_at_utc, "event start")
            end = _time(event_end_at_utc, "event end")
        except ContractError as exc:
            raise AcquisitionError(str(exc)) from exc
        if end <= start:
            raise AcquisitionError("event end must follow event start")
        artifact = {
            "schema_version": RAW_BINANCE_RESOLUTION_SCHEMA,
            "acquired_at_utc": utc_text(self.clock()),
            "market_id": market_id,
            "symbol": "BTCUSDT",
            "interval": "1m",
            "event_start_at_utc": utc_text(start),
            "event_end_at_utc": utc_text(end),
            "declared_resolution_source": DECLARED_RESOLUTION_SOURCE,
            "observations": {
                "start_candle": self._observe_candle(start),
                "end_candle": self._observe_candle(end),
            },
        }
        artifact["resolution_candles_sha256"] = payload_hash(artifact)
        normalize_resolution_candles(artifact)
        return artifact


def _normalize_observation(raw, key, boundary):
    observation = raw.get("observations", {}).get(key)
    if not isinstance(observation, dict):
        raise ContractError(f"{key} observation is required")
    if observation.get("endpoint") != BINANCE_KLINES_ENDPOINT:
        raise ContractError(f"{key} endpoint is not the locked Binance market-data endpoint")
    payload = observation.get("payload")
    if observation.get("payload_sha256") != payload_hash(payload):
        raise ContractError(f"{key} payload hash mismatch")
    if not observation.get("observed_at_utc"):
        raise ContractError(f"{key} observation time is required")
    expected_ms = _millis(boundary)
    expected_params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "startTime": expected_ms,
        "endTime": expected_ms + 59999,
        "limit": 1,
    }
    if observation.get("params") != expected_params:
        raise ContractError(f"{key} request parameters differ from the locked candle")
    if not isinstance(payload, list) or len(payload) != 1:
        raise ContractError(f"{key} must contain exactly one kline")
    row = payload[0]
    if not isinstance(row, list) or len(row) < 7:
        raise ContractError(f"{key} kline is malformed")
    if row[0] != expected_ms or row[6] != expected_ms + 59999:
        raise ContractError(f"{key} kline timestamps do not match the declared boundary")
    close = _decimal(row[4], f"{key} close")
    return {
        "boundary_at_utc": utc_text(boundary),
        "open_time_ms": row[0],
        "close_time_ms": row[6],
        "close": _decimal_text(close),
        "observed_at_utc": observation["observed_at_utc"],
        "payload_sha256": observation["payload_sha256"],
    }, close


def normalize_resolution_candles(raw):
    """Verify exact boundary candles and derive the resolution direction."""
    if not isinstance(raw, dict) or raw.get("schema_version") != RAW_BINANCE_RESOLUTION_SCHEMA:
        raise ContractError("unsupported raw Binance resolution schema")
    verify_artifact_hash(raw, "resolution_candles_sha256", "raw Binance resolution")
    if not str(raw.get("market_id") or "").isdigit():
        raise ContractError("Binance resolution market id must be numeric")
    if raw.get("symbol") != "BTCUSDT" or raw.get("interval") != "1m":
        raise ContractError("Binance resolution must use BTCUSDT one-minute candles")
    if raw.get("declared_resolution_source") != DECLARED_RESOLUTION_SOURCE:
        raise ContractError("declared Binance resolution source changed")
    start = _time(raw.get("event_start_at_utc"), "event start")
    end = _time(raw.get("event_end_at_utc"), "event end")
    if (end - start).total_seconds() != 86400:
        raise ContractError("daily Binance resolution window must be exactly 24 hours")
    start_candle, start_close = _normalize_observation(raw, "start_candle", start)
    end_candle, end_close = _normalize_observation(raw, "end_candle", end)
    if end_close > start_close:
        outcome = "Up"
    elif end_close < start_close:
        outcome = "Down"
    else:
        outcome = "Split"
    result = {
        "schema_version": BINANCE_RESOLUTION_SCHEMA,
        "raw_resolution_candles_sha256": raw["resolution_candles_sha256"],
        "market_id": raw["market_id"],
        "symbol": raw["symbol"],
        "interval": raw["interval"],
        "event_start_at_utc": raw["event_start_at_utc"],
        "event_end_at_utc": raw["event_end_at_utc"],
        "start_candle": start_candle,
        "end_candle": end_candle,
        "close_change": _decimal_text(end_close - start_close),
        "computed_outcome": outcome,
        "source": {
            "declared_market_source": DECLARED_RESOLUTION_SOURCE,
            "public_market_data_endpoint": BINANCE_KLINES_ENDPOINT,
        },
        "limitations": [
            "public Binance REST observations are independent of Polymarket payout metadata",
            "this reproduces the declared one-minute close comparison but not Polymarket's internal oracle procedure",
            "a later API response does not prove what data was available at the original resolution instant",
        ],
    }
    result["resolution_record_sha256"] = payload_hash(result)
    return result


def reconcile_binance_settlement(raw_candles, raw_settlement):
    candles = normalize_resolution_candles(raw_candles)
    settlement = normalize_settlement(raw_settlement)
    if candles["market_id"] != settlement["market_id"]:
        raise ContractError("Binance candles and settlement market ids disagree")
    gamma = raw_settlement["observations"]["gamma_market"]["payload"]
    if utc_text(_time(gamma.get("eventStartTime"), "settlement event start")) != candles[
        "event_start_at_utc"
    ]:
        raise ContractError("Binance candle start differs from settlement market terms")
    if utc_text(_time(gamma.get("endDate"), "settlement event end")) != candles[
        "event_end_at_utc"
    ]:
        raise ContractError("Binance candle end differs from settlement market terms")
    if gamma.get("resolutionSource") != DECLARED_RESOLUTION_SOURCE:
        raise ContractError("settlement market declares a different resolution source")
    if settlement["status"] != "resolved":
        raise ContractError("Binance reconciliation requires resolved settlement")
    platform_outcome = (
        settlement["winner"]["label"]
        if settlement["result_type"] == "single_winner" else "Split"
    )
    result = {
        "schema_version": BINANCE_RECONCILIATION_SCHEMA,
        "evidence_role": "independent_public_resolution_source_reconciliation",
        "market_id": settlement["market_id"],
        "slug": settlement["slug"],
        "computed_outcome": candles["computed_outcome"],
        "platform_outcome": platform_outcome,
        "verdict": "match" if candles["computed_outcome"] == platform_outcome else "mismatch",
        "resolution_candles": candles,
        "platform_settlement_sha256": settlement["settlement_record_sha256"],
        "limitations": [
            "matching public data supports outcome consistency but does not audit Polymarket's internal resolution process",
            "no order, fill, wallet settlement, redemption, or profitability is established",
        ],
    }
    result["reconciliation_sha256"] = payload_hash(result)
    return result


def reconcile_binance_cohort(markets):
    if not isinstance(markets, dict) or not markets:
        raise ContractError("Binance settlement cohort requires markets")
    results = {}
    seen = set()
    for label in sorted(markets):
        inputs = markets[label]
        if not isinstance(inputs, dict) or set(inputs) != {"candles", "settlement"}:
            raise ContractError("Binance cohort market inputs are invalid")
        item = reconcile_binance_settlement(inputs["candles"], inputs["settlement"])
        if item["market_id"] in seen:
            raise ContractError("Binance cohort contains a duplicate market")
        seen.add(item["market_id"])
        results[label] = item
    counts = {"match": 0, "mismatch": 0}
    for item in results.values():
        counts[item["verdict"]] += 1
    result = {
        "schema_version": BINANCE_COHORT_SCHEMA,
        "evidence_role": "independent_public_resolution_source_cohort",
        "market_count": len(results),
        "verdict_counts": counts,
        "markets": results,
        "limitations": [
            "the cohort is small and selected for execution-truth observation, not prediction testing",
            "agreement does not establish signal compatibility, execution quality, or profitability",
        ],
    }
    result["cohort_sha256"] = payload_hash(result)
    return result


def store_raw_resolution_candles(raw, directory):
    normalize_resolution_candles(raw)
    target = Path(directory) / (
        f"binance-resolution-market-{raw['market_id']}-{raw['resolution_candles_sha256']}.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(raw, sort_keys=True, indent=2) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != content:
            raise ContractError("content-addressed Binance evidence path has different data")
        return target
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)
    return target
