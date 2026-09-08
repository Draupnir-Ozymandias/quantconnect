import copy
import json
from pathlib import Path
import tempfile
import unittest

from execution_truth import (
    AcquisitionError,
    ContractError,
    PublicPolymarketAcquirer,
    promote_raw_evidence,
    store_raw_slug_resolution,
    verify_live_evidence_inventory,
    verify_raw_slug_resolution,
)
from execution_truth.contracts import payload_hash
from qcrl_execution_truth import build_parser
from tests.test_execution_truth_acquisition import SequenceClock, fixture


SLUG = "btc-updown-fixture-1777938600"


class SlugTransport:
    def __init__(self, event=None, market=None):
        self.market = market or fixture("gamma_market.json")
        self.event = event or {"id": "event-1", "slug": SLUG,
                               "markets": [{"id": "123456"}]}
        self.calls = []

    def get_json(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        return copy.deepcopy(self.event if "/events/" in url else self.market)


def acquire(kind="event", transport=None, slug=SLUG):
    transport = transport or SlugTransport()
    acquirer = PublicPolymarketAcquirer(transport=transport, clock=SequenceClock())
    return acquirer.resolve_market_slug(slug, kind), transport


class SlugResolutionTests(unittest.TestCase):
    def test_event_slug_resolves_one_market_through_documented_public_route(self):
        raw, transport = acquire()
        self.assertEqual("123456", raw["resolved_market_id"])
        self.assertEqual("event", raw["reference_kind"])
        self.assertEqual(
            f"https://gamma-api.polymarket.com/events/slug/{SLUG}",
            transport.calls[0][0],
        )
        self.assertEqual({}, transport.calls[0][1])
        self.assertEqual(raw["resolution_sha256"], verify_raw_slug_resolution(raw))

    def test_market_slug_uses_distinct_documented_route(self):
        raw, transport = acquire("market")
        self.assertEqual("123456", raw["resolved_market_id"])
        self.assertEqual(
            f"https://gamma-api.polymarket.com/markets/slug/{SLUG}",
            transport.calls[0][0],
        )

    def test_event_slug_never_guesses_among_multiple_markets(self):
        event = {"id": "event-1", "slug": SLUG,
                 "markets": [{"id": "123456"}, {"id": "654321"}]}
        with self.assertRaisesRegex(AcquisitionError, "found 2"):
            acquire(transport=SlugTransport(event=event))

    def test_invalid_slug_and_kind_fail_before_network(self):
        for slug, kind in [("BTC Up", "event"), ("../market", "event"),
                           ("btc_up", "event"), (SLUG, "guess")]:
            transport = SlugTransport()
            with self.subTest(slug=slug, kind=kind), self.assertRaises(AcquisitionError):
                acquire(kind=kind, transport=transport, slug=slug)
            self.assertEqual([], transport.calls)

    def test_response_slug_and_numeric_id_are_exact(self):
        event = {"id": "event-1", "slug": "different", "markets": [{"id": "123456"}]}
        with self.assertRaisesRegex(AcquisitionError, "different event slug"):
            acquire(transport=SlugTransport(event=event))
        event = {"id": "event-1", "slug": SLUG, "markets": [{"id": "not-numeric"}]}
        with self.assertRaisesRegex(AcquisitionError, "must be numeric"):
            acquire(transport=SlugTransport(event=event))

    def test_rehashed_tampering_still_fails_semantic_verification(self):
        raw, _ = acquire()
        raw["resolved_market_id"] = "654321"
        raw.pop("resolution_sha256")
        raw["resolution_sha256"] = payload_hash(raw)
        with self.assertRaisesRegex(ContractError, "disagrees"):
            verify_raw_slug_resolution(raw)
        raw, _ = acquire()
        raw["observation"]["endpoint"] = "https://example.invalid"
        raw.pop("resolution_sha256")
        raw["resolution_sha256"] = payload_hash(raw)
        with self.assertRaisesRegex(ContractError, "endpoint"):
            verify_raw_slug_resolution(raw)

    def test_storage_promotion_and_inventory_are_content_addressed(self):
        raw, _ = acquire()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = store_raw_slug_resolution(raw, root / "local")
            self.assertEqual(source, store_raw_slug_resolution(raw, root / "local"))
            promoted = promote_raw_evidence(source, root / "raw")
            inventory = {
                "schema_version": "qcrl.polymarket_live_evidence_inventory.v1",
                "artifacts": [{
                    "path": f"raw/{promoted.name}",
                    "schema_version": raw["schema_version"],
                    "artifact_sha256": raw["resolution_sha256"],
                    "captured_at_utc": raw["acquired_at_utc"],
                    "evidence_role": "test_slug_resolution",
                    "limitations": ["synthetic test response"],
                }],
            }
            (root / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
            self.assertEqual(1, verify_live_evidence_inventory(root))

    def test_cli_defaults_to_event_slug_and_keeps_market_kind_explicit(self):
        event = build_parser().parse_args(["capture-sequence-slug", SLUG])
        market = build_parser().parse_args(["resolve-slug", SLUG,
                                            "--kind", "market"])
        self.assertEqual("event", event.kind)
        self.assertEqual(5, event.samples)
        self.assertEqual("market", market.kind)


if __name__ == "__main__":
    unittest.main()
