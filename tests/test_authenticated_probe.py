import base64
import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from execution_truth.authenticated_probe import (
    AuthenticatedProbeError,
    AuthenticatedReadTransport,
    probe_plan,
    run_authenticated_probe,
    store_authenticated_probe,
)


CONDITION_ID = "0x" + "ab" * 32
CREDENTIALS = {
    "address": "0x" + "12" * 20,
    "api_key": "test-api-key",
    "secret": base64.b64encode(b"test-hmac-secret").decode("ascii"),
    "passphrase": "test-passphrase",
}


class FakeSender:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, method, url, headers, body, timeout_seconds):
        self.calls.append((method, url, dict(headers), body, timeout_seconds))
        return self.responses.pop(0)


class FakeTransport:
    def __init__(self, open_orders, closed_only=False):
        self.responses = {
            "open_orders_for_market": open_orders,
            "closed_only_status": closed_only,
        }
        self.calls = []

    def get_named_route(self, name, query=None):
        self.calls.append((name, dict(query or {})))
        return self.responses[name]


class AuthenticatedProbeTests(unittest.TestCase):
    def test_plan_is_mechanically_get_only(self):
        plan = probe_plan(CONDITION_ID)
        self.assertEqual(["GET"], plan["method_allowlist"])
        self.assertEqual(
            {"POST", "PUT", "PATCH", "DELETE", "order_signing",
             "order_submission", "order_cancellation", "heartbeat"},
            set(plan["forbidden_capabilities"]),
        )
        self.assertEqual(
            ["/data/orders", "/auth/ban-status/closed-only"],
            [item["path"] for item in plan["requests"]],
        )

    def test_transport_signs_fixed_path_and_excludes_query_from_signature(self):
        sender = FakeSender([[]])
        transport = AuthenticatedReadTransport(
            CREDENTIALS, sender=sender, timestamp_clock=lambda: 1_700_000_000
        )
        self.assertEqual([], transport.get_named_route(
            "open_orders_for_market", {"market": CONDITION_ID}
        ))
        method, url, headers, body, timeout = sender.calls[0]
        expected = base64.urlsafe_b64encode(hmac.new(
            b"test-hmac-secret",
            b"1700000000GET/data/orders",
            hashlib.sha256,
        ).digest()).decode("ascii")
        self.assertEqual("GET", method)
        self.assertEqual(
            f"https://clob.polymarket.com/data/orders?market={CONDITION_ID}", url
        )
        self.assertEqual(expected, headers["POLY_SIGNATURE"])
        self.assertIsNone(body)
        self.assertEqual(20, timeout)

    def test_transport_rejects_unlisted_route_and_query(self):
        transport = AuthenticatedReadTransport(CREDENTIALS, sender=FakeSender([]))
        with self.assertRaisesRegex(AuthenticatedProbeError, "allowlist"):
            transport.get_named_route("cancel_all")
        with self.assertRaisesRegex(AuthenticatedProbeError, "exactly"):
            transport.get_named_route(
                "open_orders_for_market",
                {"market": CONDITION_ID, "order_id": "anything"},
            )

    def test_absent_fields_remain_unknown_and_credentials_are_not_serialized(self):
        result = run_authenticated_probe(
            CONDITION_ID,
            CREDENTIALS,
            transport=FakeTransport([{"id": "redacted-by-probe"}]),
            clock=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(
            "unknown", result["execution_fields"]["taker_delay_enabled"]["status"]
        )
        self.assertEqual(
            "unknown",
            result["execution_fields"]["minimum_order_age_seconds"]["status"],
        )
        serialized = json.dumps(result, sort_keys=True)
        for value in CREDENTIALS.values():
            self.assertNotIn(value, serialized)
        self.assertNotIn("redacted-by-probe", serialized)

    def test_explicit_execution_fields_are_preserved_without_inference(self):
        result = run_authenticated_probe(
            CONDITION_ID,
            CREDENTIALS,
            transport=FakeTransport([{"itode": False, "oas": 0}]),
            clock=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        delay = result["execution_fields"]["taker_delay_enabled"]
        age = result["execution_fields"]["minimum_order_age_seconds"]
        self.assertEqual(("observed", False), (delay["status"], delay["value"]))
        self.assertEqual(("observed", 0), (age["status"], age["value"]))

    def test_malformed_or_conflicting_execution_fields_fail_closed(self):
        with self.assertRaisesRegex(AuthenticatedProbeError, "itode must be boolean"):
            run_authenticated_probe(
                CONDITION_ID, CREDENTIALS,
                transport=FakeTransport([{"itode": "false"}]),
            )
        with self.assertRaisesRegex(AuthenticatedProbeError, "conflicting"):
            run_authenticated_probe(
                CONDITION_ID, CREDENTIALS,
                transport=FakeTransport([{"oas": 0}, {"nested": {"oas": 1}}]),
            )

    def test_store_is_content_addressed_and_idempotent(self):
        result = run_authenticated_probe(
            CONDITION_ID,
            CREDENTIALS,
            transport=FakeTransport([]),
            clock=lambda: datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        with tempfile.TemporaryDirectory() as directory:
            first = store_authenticated_probe(result, directory)
            second = store_authenticated_probe(result, directory)
            self.assertEqual(first, second)
            self.assertEqual(result, json.loads(Path(first).read_text()))


if __name__ == "__main__":
    unittest.main()
