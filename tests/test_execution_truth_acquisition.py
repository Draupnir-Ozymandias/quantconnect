import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from execution_truth import (
    ContractError,
    PublicPolymarketAcquirer,
    normalize_bundle,
    store_raw_bundle,
)


FIXTURES = Path(__file__).parent / "fixtures" / "polymarket"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeTransport:
    def __init__(self, gamma, clob, books):
        self.gamma = gamma
        self.clob = clob
        self.books = books
        self.calls = []

    def get_json(self, url, params=None):
        params = dict(params or {})
        self.calls.append((url, params))
        if "/markets/" in url:
            return copy.deepcopy(self.gamma)
        if "/clob-markets/" in url:
            return copy.deepcopy(self.clob)
        return copy.deepcopy(self.books[params["token_id"]])


class SequenceClock:
    def __init__(self):
        self.value = datetime(2026, 5, 4, 23, 52, tzinfo=timezone.utc)

    def __call__(self):
        current = self.value
        self.value += timedelta(milliseconds=10)
        return current


class ExecutionTruthAcquisitionTests(unittest.TestCase):
    def setUp(self):
        gamma = fixture("gamma_market.json")
        clob = fixture("clob_market_info.json")
        up = fixture("up_order_book.json")
        down = copy.deepcopy(up)
        down["asset_id"] = "10002"
        down["hash"] = "0xdownfixturebookhash"
        self.transport = FakeTransport(
            gamma, clob, {"10001": up, "10002": down}
        )
        self.acquirer = PublicPolymarketAcquirer(
            transport=self.transport, clock=SequenceClock()
        )

    def test_acquirer_uses_only_fixed_public_get_routes(self):
        bundle = self.acquirer.acquire_market_bundle("123456")
        self.assertEqual(4, len(self.transport.calls))
        self.assertEqual(
            "https://gamma-api.polymarket.com/markets/123456",
            self.transport.calls[0][0],
        )
        self.assertIn("/clob-markets/", self.transport.calls[1][0])
        self.assertEqual({"token_id": "10001"}, self.transport.calls[2][1])
        self.assertEqual({"token_id": "10002"}, self.transport.calls[3][1])
        self.assertNotIn("credential", json.dumps(bundle).lower())

    def test_raw_bundle_preserves_each_payload_and_observation_time(self):
        bundle = self.acquirer.acquire_market_bundle("123456")
        observations = bundle["observations"]
        self.assertEqual("123456", observations["gamma_market"]["payload"]["id"])
        self.assertEqual(2, len(observations["order_books"]))
        self.assertTrue(observations["clob_market"]["payload_sha256"])
        self.assertTrue(observations["order_books"][0]["observed_at_utc"])
        self.assertEqual(64, len(bundle["bundle_sha256"]))

    def test_bundle_replays_offline_through_contracts(self):
        raw = self.acquirer.acquire_market_bundle("123456")
        normalized = normalize_bundle(raw)
        self.assertEqual(
            "qcrl.polymarket_market_contract.v2",
            normalized["market_contract"]["schema_version"],
        )
        self.assertEqual({"Up", "Down"}, {
            book["outcome"] for book in normalized["order_books"]
        })
        self.assertEqual(64, len(normalized["bundle_sha256"]))

    def test_offline_replay_rejects_payload_tampering(self):
        raw = self.acquirer.acquire_market_bundle("123456")
        raw["observations"]["gamma_market"]["payload"]["slug"] = "tampered"
        with self.assertRaisesRegex(ContractError, "raw bundle hash mismatch"):
            normalize_bundle(raw)

    def test_raw_storage_is_content_addressed_and_idempotent(self):
        raw = self.acquirer.acquire_market_bundle("123456")
        with tempfile.TemporaryDirectory() as directory:
            first = store_raw_bundle(raw, directory)
            second = store_raw_bundle(raw, directory)
            self.assertEqual(first, second)
            self.assertIn(raw["bundle_sha256"], first.name)
            self.assertEqual(raw, json.loads(first.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
