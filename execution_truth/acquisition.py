"""Public-only acquisition for Polymarket execution-truth evidence."""

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .contracts import normalize_market_contract, payload_hash


RAW_BUNDLE_SCHEMA = "qcrl.polymarket_raw_bundle.v1"
RAW_DISCOVERY_SCHEMA = "qcrl.polymarket_raw_discovery.v1"
RAW_SLUG_RESOLUTION_SCHEMA = "qcrl.polymarket_raw_slug_resolution.v1"
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


class AcquisitionError(RuntimeError):
    """Raised when public evidence cannot be acquired completely."""


def utc_now():
    return datetime.now(timezone.utc)


def utc_text(value):
    if value.tzinfo is None:
        raise AcquisitionError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class UrllibJsonTransport:
    """Minimal unauthenticated JSON transport with no mutable session state."""

    def __init__(self, timeout_seconds=20):
        self.timeout_seconds = timeout_seconds

    def get_json(self, url, params=None):
        if params:
            url = f"{url}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "QCRL-execution-truth/1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                payload = json.loads(response.read().decode(charset))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AcquisitionError(f"public GET failed: {url}: {exc}") from exc
        if not isinstance(payload, dict):
            raise AcquisitionError(f"public GET did not return an object: {url}")
        return payload


class PublicPolymarketAcquirer:
    """Acquire one complete market bundle from fixed public GET endpoints."""

    def __init__(self, transport=None, clock=None):
        self.transport = transport or UrllibJsonTransport()
        self.clock = clock or utc_now

    def _observe(self, url, params=None):
        payload = self.transport.get_json(url, params=params)
        return {
            "observed_at_utc": utc_text(self.clock()),
            "endpoint": url,
            "params": dict(params or {}),
            "payload_sha256": payload_hash(payload),
            "payload": payload,
        }

    def acquire_market_bundle(self, market_id):
        market_id = str(market_id).strip()
        if not market_id:
            raise AcquisitionError("market_id is required")

        acquired_at = utc_text(self.clock())
        gamma = self._observe(f"{GAMMA_BASE}/markets/{market_id}")
        if str(gamma["payload"].get("id")) != market_id:
            raise AcquisitionError("Gamma returned a different market id")
        condition_id = str(gamma["payload"].get("conditionId") or "").strip()
        if not condition_id:
            raise AcquisitionError("Gamma market has no conditionId")

        clob = self._observe(f"{CLOB_BASE}/clob-markets/{condition_id}")
        contract = normalize_market_contract(
            gamma["payload"], clob["payload"], clob["observed_at_utc"]
        )

        books = []
        for outcome in contract["outcomes"]:
            books.append(self._observe(
                f"{CLOB_BASE}/book",
                params={"token_id": outcome["token_id"]},
            ))

        bundle = {
            "schema_version": RAW_BUNDLE_SCHEMA,
            "acquired_at_utc": acquired_at,
            "market_id_requested": market_id,
            "observations": {
                "gamma_market": gamma,
                "clob_market": clob,
                "order_books": books,
            },
        }
        bundle["bundle_sha256"] = payload_hash(bundle)
        return bundle

    def resolve_market_slug(self, slug, reference_kind="event"):
        """Resolve one exact event or market slug to one numeric market id."""
        slug = str(slug).strip()
        if (not slug or len(slug) > 120
                or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-"
                       for char in slug)):
            raise AcquisitionError("slug must contain only lowercase letters, digits, and hyphens")
        if reference_kind not in {"event", "market"}:
            raise AcquisitionError("reference_kind must be event or market")

        acquired_at = utc_text(self.clock())
        endpoint = f"{GAMMA_BASE}/{reference_kind}s/slug/{slug}"
        observation = self._observe(endpoint)
        payload = observation["payload"]
        if str(payload.get("slug") or "") != slug:
            raise AcquisitionError(f"Gamma returned a different {reference_kind} slug")
        if reference_kind == "market":
            candidates = [payload]
        else:
            candidates = payload.get("markets")
            if not isinstance(candidates, list):
                raise AcquisitionError("Gamma event has no markets array")
        if len(candidates) != 1 or not isinstance(candidates[0], dict):
            raise AcquisitionError(
                f"expected one market for {reference_kind} slug, found {len(candidates)}"
            )
        market_id = str(candidates[0].get("id") or "").strip()
        if not market_id.isdigit():
            raise AcquisitionError("resolved market id must be numeric")
        resolution = {
            "schema_version": RAW_SLUG_RESOLUTION_SCHEMA,
            "acquired_at_utc": acquired_at,
            "reference_kind": reference_kind,
            "slug_requested": slug,
            "resolved_market_id": market_id,
            "observation": observation,
        }
        resolution["resolution_sha256"] = payload_hash(resolution)
        return resolution

    def acquire_series_event(self, series_id, target_at_utc):
        """Acquire the unique series event whose explicit interval contains T."""
        series_id = str(series_id).strip()
        if not series_id or any(char not in "0123456789" for char in series_id):
            raise AcquisitionError("series_id must be numeric")
        if isinstance(target_at_utc, str):
            try:
                target = datetime.fromisoformat(
                    target_at_utc.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise AcquisitionError("target_at_utc is invalid") from exc
        else:
            target = target_at_utc
        if not isinstance(target, datetime):
            raise AcquisitionError("target_at_utc must be an ISO-8601 value")
        target_text = utc_text(target)
        target = datetime.fromisoformat(target_text.replace("Z", "+00:00"))

        acquired_at = utc_text(self.clock())
        series = self._observe(f"{GAMMA_BASE}/series/{series_id}")
        if str(series["payload"].get("id")) != series_id:
            raise AcquisitionError("Gamma returned a different series id")
        candidates = []
        for event in series["payload"].get("events") or []:
            try:
                start = datetime.fromisoformat(
                    str(event["startTime"]).replace("Z", "+00:00")
                )
                end = datetime.fromisoformat(
                    str(event["endDate"]).replace("Z", "+00:00")
                )
            except (KeyError, TypeError, ValueError):
                continue
            if start.tzinfo is None or end.tzinfo is None:
                continue
            if start <= target < end:
                candidates.append(str(event.get("id") or ""))
        candidates = sorted(set(value for value in candidates if value))
        if len(candidates) != 1:
            raise AcquisitionError(
                f"expected one series event at target time, found {len(candidates)}"
            )
        event = self._observe(f"{GAMMA_BASE}/events/{candidates[0]}")
        if str(event["payload"].get("id")) != candidates[0]:
            raise AcquisitionError("Gamma returned a different event id")

        discovery = {
            "schema_version": RAW_DISCOVERY_SCHEMA,
            "acquired_at_utc": acquired_at,
            "target_at_utc": target_text,
            "series_id_requested": series_id,
            "observations": {"series": series, "event": event},
        }
        discovery["discovery_sha256"] = payload_hash(discovery)
        return discovery

    def acquire_book_sequence(self, market_id, sample_count, interval_seconds, sleeper=None):
        """Capture a bounded series through the separately testable sequence contract."""
        from .book_sequence import acquire_book_sequence

        return acquire_book_sequence(
            self, market_id, sample_count, interval_seconds, sleeper=sleeper
        )
