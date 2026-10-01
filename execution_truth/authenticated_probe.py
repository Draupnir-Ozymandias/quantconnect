"""Fail-closed authenticated CLOB reads with no trading capability.

The probe deliberately exposes only named GET routes.  It never accepts an
HTTP method, URL, request body, order identifier, or arbitrary query mapping
from its caller, and it never serializes credentials or raw account payloads.
"""

import base64
import binascii
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .contracts import canonical_json, payload_hash


PROBE_SCHEMA = "qcrl.authenticated_execution_probe.v1"
CLOB_BASE = "https://clob.polymarket.com"
MAX_RESPONSE_BYTES = 2_000_000
READ_ONLY_ROUTES = {
    "open_orders_for_market": {
        "path": "/data/orders",
        "required_query": ("market",),
    },
    "closed_only_status": {
        "path": "/auth/ban-status/closed-only",
        "required_query": (),
    },
}
TARGET_FIELDS = ("itode", "oas")


class AuthenticatedProbeError(RuntimeError):
    """Raised when a probe request or response violates the read-only contract."""


def _utc_text(clock):
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise AuthenticatedProbeError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _condition_id(value):
    value = str(value or "").strip().lower()
    if (len(value) != 66 or not value.startswith("0x")
            or any(char not in "0123456789abcdef" for char in value[2:])):
        raise AuthenticatedProbeError("condition_id must be 0x plus 64 hexadecimal characters")
    return value


def normalize_probe_credentials(value):
    if not isinstance(value, dict):
        raise AuthenticatedProbeError("credential secret must be a JSON object")
    expected = {"address", "api_key", "secret", "passphrase"}
    if set(value) != expected:
        raise AuthenticatedProbeError(
            "credential secret must contain only address, api_key, secret, and passphrase"
        )
    credentials = {}
    for key in sorted(expected):
        item = value[key]
        if not isinstance(item, str) or not item.strip() or "\n" in item or "\r" in item:
            raise AuthenticatedProbeError(f"credential {key} must be one nonempty line")
        credentials[key] = item.strip()
    address = credentials["address"].lower()
    if (len(address) != 42 or not address.startswith("0x")
            or any(char not in "0123456789abcdef" for char in address[2:])):
        raise AuthenticatedProbeError("credential address must be an EVM address")
    credentials["address"] = address
    try:
        _decode_secret(credentials["secret"])
    except AuthenticatedProbeError:
        raise
    return credentials


def _decode_secret(value):
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AuthenticatedProbeError("credential secret must be base64 encoded") from exc
    if not decoded:
        raise AuthenticatedProbeError("credential secret decodes to an empty key")
    return decoded


def _default_sender(method, url, headers, body, timeout_seconds):
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise AuthenticatedProbeError(
                    f"authenticated read returned HTTP {response.status}"
                )
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise AuthenticatedProbeError("authenticated response exceeds size limit")
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(raw.decode(charset))
    except (HTTPError, URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthenticatedProbeError("authenticated GET failed") from exc


class AuthenticatedReadTransport:
    """L2-signed transport whose public surface can issue only two fixed GETs."""

    def __init__(self, credentials, *, sender=None, timestamp_clock=None,
                 timeout_seconds=20):
        self._credentials = normalize_probe_credentials(credentials)
        self._sender = sender or _default_sender
        self._timestamp_clock = timestamp_clock or time.time
        self._timeout_seconds = timeout_seconds

    def get_named_route(self, route_name, query=None):
        route = READ_ONLY_ROUTES.get(route_name)
        if route is None:
            raise AuthenticatedProbeError("route is not in the read-only allowlist")
        query = dict(query or {})
        required = set(route["required_query"])
        if set(query) != required:
            raise AuthenticatedProbeError(
                f"{route_name} requires exactly these query keys: {sorted(required)}"
            )
        if "market" in query:
            query["market"] = _condition_id(query["market"])

        timestamp = str(int(self._timestamp_clock()))
        path = route["path"]
        message = f"{timestamp}GET{path}".encode("utf-8")
        signature = base64.urlsafe_b64encode(hmac.new(
            _decode_secret(self._credentials["secret"]),
            message,
            hashlib.sha256,
        ).digest()).decode("ascii")
        headers = {
            "Accept": "application/json",
            "User-Agent": "QCRL-authenticated-read-probe/1",
            "POLY_ADDRESS": self._credentials["address"],
            "POLY_API_KEY": self._credentials["api_key"],
            "POLY_PASSPHRASE": self._credentials["passphrase"],
            "POLY_SIGNATURE": signature,
            "POLY_TIMESTAMP": timestamp,
        }
        url = f"{CLOB_BASE}{path}"
        if query:
            url = f"{url}?{urlencode(sorted(query.items()))}"
        payload = self._sender("GET", url, headers, None, self._timeout_seconds)
        if not isinstance(payload, (dict, list, bool)):
            raise AuthenticatedProbeError("authenticated response has unsupported JSON shape")
        return payload


def probe_plan(condition_id):
    condition_id = _condition_id(condition_id)
    plan = {
        "schema_version": "qcrl.authenticated_execution_probe_plan.v1",
        "condition_id": condition_id,
        "host": CLOB_BASE,
        "method_allowlist": ["GET"],
        "requests": [
            {"route": "open_orders_for_market", "path": "/data/orders",
             "query": {"market": condition_id}},
            {"route": "closed_only_status",
             "path": "/auth/ban-status/closed-only", "query": {}},
        ],
        "forbidden_capabilities": [
            "POST", "PUT", "PATCH", "DELETE", "order_signing",
            "order_submission", "order_cancellation", "heartbeat",
        ],
    }
    plan["plan_sha256"] = payload_hash(plan)
    return plan


def _field_paths(value, target, prefix="$"):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}"
            if key == target:
                found.append((path, item))
            found.extend(_field_paths(item, target, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_field_paths(item, target, f"{prefix}[{index}]"))
    return found


def _shape(value):
    if isinstance(value, dict):
        return {"json_type": "object", "top_level_fields": sorted(value)}
    if isinstance(value, list):
        fields = sorted({key for item in value if isinstance(item, dict) for key in item})
        return {"json_type": "array", "item_fields": fields}
    return {"json_type": "boolean"}


def _target_result(payloads, field):
    matches = []
    for route_name, payload in payloads.items():
        matches.extend((route_name, path, value)
                       for path, value in _field_paths(payload, field))
    values = {canonical_json(value) for _, _, value in matches}
    if len(values) > 1:
        raise AuthenticatedProbeError(f"conflicting authenticated values for {field}")
    if not matches:
        return {"status": "unknown", "value": None, "observed_paths": []}
    value = matches[0][2]
    if field == "itode" and not isinstance(value, bool):
        raise AuthenticatedProbeError("authenticated itode must be boolean")
    if field == "oas" and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
        raise AuthenticatedProbeError("authenticated oas must be a nonnegative integer")
    return {
        "status": "observed",
        "value": value,
        "observed_paths": sorted(
            {f"{route}:{path}" for route, path, _ in matches}
        ),
    }


def run_authenticated_probe(condition_id, credentials, *, transport=None, clock=None):
    """Run fixed authenticated reads and return only a sanitized evidence record."""
    condition_id = _condition_id(condition_id)
    clock = clock or (lambda: datetime.now(timezone.utc))
    transport = transport or AuthenticatedReadTransport(credentials)
    payloads = {
        "open_orders_for_market": transport.get_named_route(
            "open_orders_for_market", {"market": condition_id}
        ),
        "closed_only_status": transport.get_named_route("closed_only_status"),
    }
    result = {
        "schema_version": PROBE_SCHEMA,
        "observed_at_utc": _utc_text(clock),
        "condition_id": condition_id,
        "evidence_role": "authenticated_non_trading_field_visibility",
        "authenticated_reads_succeeded": True,
        "request_plan_sha256": probe_plan(condition_id)["plan_sha256"],
        "response_shapes": {
            name: _shape(payload) for name, payload in sorted(payloads.items())
        },
        "execution_fields": {
            "taker_delay_enabled": _target_result(payloads, "itode"),
            "minimum_order_age_seconds": _target_result(payloads, "oas"),
        },
        "limitations": [
            "no order was signed, submitted, canceled, or modified",
            "raw authenticated account payloads were not persisted",
            "field absence preserves unknown and does not establish zero or false",
            "authenticated visibility does not prove matching-engine behavior",
        ],
    }
    result["probe_sha256"] = payload_hash(result)
    return result


def store_authenticated_probe(result, directory):
    if result.get("schema_version") != PROBE_SCHEMA:
        raise AuthenticatedProbeError("unsupported authenticated probe schema")
    supplied = result.get("probe_sha256")
    unhashed = dict(result)
    unhashed.pop("probe_sha256", None)
    if supplied != payload_hash(unhashed):
        raise AuthenticatedProbeError("authenticated probe hash mismatch")
    condition_id = _condition_id(result.get("condition_id"))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"authenticated-probe-{condition_id}-{supplied}.json"
    content = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != content:
            raise AuthenticatedProbeError("content-addressed probe path has different data")
        return target
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)
    return target
