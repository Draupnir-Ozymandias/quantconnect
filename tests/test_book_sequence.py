import copy
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from execution_truth import (
    AcquisitionError,
    ContractError,
    PublicPolymarketAcquirer,
    normalize_book_sequence,
    promote_raw_evidence,
    store_raw_book_sequence,
    verify_live_evidence_inventory,
)
from execution_truth.contracts import payload_hash
from qcrl_execution_truth import build_parser
from tests.test_execution_truth_acquisition import FakeTransport, SequenceClock, fixture


class ChangingBookTransport(FakeTransport):
    def get_json(self, url, params=None):
        result = super().get_json(url, params=params)
        if "/book" in url:
            sample_index = (len(self.calls) - 3) // 4
            result["timestamp"] = str(1777938720100 + sample_index * 1000)
            result["hash"] = f"0x{params['token_id']}-sample-{sample_index}"
            if params["token_id"] == "10001":
                low = 46 + sample_index * 2
                result["asks"] = [
                    {"price": f"0.{low + 1:02d}", "size": "250"},
                    {"price": f"0.{low:02d}", "size": "150"},
                ]
        return result


def acquirer(changing=False):
    gamma = fixture("gamma_market.json")
    gamma["feesEnabled"] = True
    clob = fixture("clob_market_info.json")
    clob["itode"] = False
    up = fixture("up_order_book.json")
    down = copy.deepcopy(up)
    down["asset_id"] = "10002"
    down["hash"] = "0xdownfixturebookhash"
    transport_type = ChangingBookTransport if changing else FakeTransport
    transport = transport_type(gamma, clob, {"10001": up, "10002": down})
    return PublicPolymarketAcquirer(transport=transport, clock=SequenceClock()), transport


class BookSequenceTests(unittest.TestCase):
    def test_capture_is_bounded_and_uses_complete_public_bundles(self):
        source, transport = acquirer()
        waits = []
        raw = source.acquire_book_sequence("123456", 3, 2, sleeper=waits.append)
        self.assertEqual([2, 2], waits)
        self.assertEqual(12, len(transport.calls))
        self.assertEqual(3, len(raw["samples"]))
        self.assertEqual("qcrl.polymarket_raw_book_sequence.v1", raw["schema_version"])
        self.assertTrue(all(sample["schema_version"] == "qcrl.polymarket_raw_bundle.v1"
                            for sample in raw["samples"]))
        self.assertNotIn("credential", json.dumps(raw).casefold())

    def test_invalid_bounds_fail_before_any_request_or_sleep(self):
        for count, interval in [(1, 1), (121, 1), (2, 0), (2, 61),
                                (62, 60), (True, 1), (2, False)]:
            with self.subTest(count=count, interval=interval):
                source, transport = acquirer()
                waits = []
                with self.assertRaises(AcquisitionError):
                    source.acquire_book_sequence("123456", count, interval,
                                                 sleeper=waits.append)
                self.assertEqual([], transport.calls)
                self.assertEqual([], waits)

    def test_normalization_summarizes_each_independently_timed_book(self):
        source, _ = acquirer(changing=True)
        raw = source.acquire_book_sequence("123456", 3, 1, sleeper=lambda _: None)
        result = normalize_book_sequence(raw)
        self.assertEqual("qcrl.polymarket_book_sequence.v1", result["schema_version"])
        self.assertEqual("qcrl.polymarket_normalized_bundle.v2",
                         result["samples"][0]["normalized_bundle_schema"])
        up_rows = [next(book for book in sample["books"] if book["outcome"] == "Up")
                   for sample in result["samples"]]
        self.assertEqual(["0.46", "0.48", "0.5"],
                         [row["best_ask"]["price"] for row in up_rows])
        self.assertEqual(3, len({row["exchange_book_hash"] for row in up_rows}))
        self.assertEqual(False, result["samples"][0]["execution_metadata"]
                         ["taker_order_delay_enabled"])
        self.assertEqual(64, len(result["sequence_sha256"]))

    def test_unchanged_payloads_remain_distinct_timed_observations(self):
        source, _ = acquirer()
        raw = source.acquire_book_sequence("123456", 2, 1, sleeper=lambda _: None)
        result = normalize_book_sequence(raw)
        first, second = result["samples"]
        self.assertEqual(first["gamma_payload_sha256"], second["gamma_payload_sha256"])
        self.assertNotEqual(first["market_contract_sha256"],
                            second["market_contract_sha256"])
        self.assertNotEqual(first["books"][0]["observed_at_utc"],
                            second["books"][0]["observed_at_utc"])

    def test_sequence_rejects_tampering_count_order_and_identity_drift(self):
        source, _ = acquirer()
        original = source.acquire_book_sequence("123456", 2, 1, sleeper=lambda _: None)
        cases = []
        tampered = copy.deepcopy(original)
        tampered["samples"][0]["observations"]["gamma_market"]["payload"]["slug"] = "x"
        cases.append((tampered, "hash mismatch"))
        count = copy.deepcopy(original)
        count["requested_sample_count"] = 3
        count["sequence_sha256"] = payload_hash({k: v for k, v in count.items()
                                                  if k != "sequence_sha256"})
        cases.append((count, "sample count"))
        order = copy.deepcopy(original)
        order["samples"].reverse()
        order["sequence_sha256"] = payload_hash({k: v for k, v in order.items()
                                                  if k != "sequence_sha256"})
        cases.append((order, "strictly increase"))
        identity = copy.deepcopy(original)
        identity["samples"][1]["market_id_requested"] = "999"
        identity["samples"][1].pop("bundle_sha256")
        identity["samples"][1]["bundle_sha256"] = payload_hash(identity["samples"][1])
        identity.pop("sequence_sha256")
        identity["sequence_sha256"] = payload_hash(identity)
        cases.append((identity, "different market id"))
        impossible = copy.deepcopy(original)
        observation = impossible["samples"][1]["observations"]["gamma_market"]
        observation["observed_at_utc"] = "2026-05-04T23:51:00Z"
        impossible["samples"][1].pop("bundle_sha256")
        impossible["samples"][1]["bundle_sha256"] = payload_hash(
            impossible["samples"][1]
        )
        impossible.pop("sequence_sha256")
        impossible["sequence_sha256"] = payload_hash(impossible)
        cases.append((impossible, "precedes the prior capture observation"))
        for value, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ContractError, message):
                normalize_book_sequence(value)

    def test_storage_and_promotion_are_content_addressed_and_idempotent(self):
        source, _ = acquirer()
        raw = source.acquire_book_sequence("123456", 2, 1, sleeper=lambda _: None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = store_raw_book_sequence(raw, root / "local")
            second = store_raw_book_sequence(raw, root / "local")
            self.assertEqual(first, second)
            self.assertIn(raw["sequence_sha256"], first.name)
            promoted = promote_raw_evidence(first, root / "durable")
            self.assertEqual(raw, json.loads(promoted.read_text(encoding="utf-8")))

    def test_live_inventory_can_verify_a_declared_sequence(self):
        source, _ = acquirer()
        raw = source.acquire_book_sequence("123456", 2, 1, sleeper=lambda _: None)
        normalized = normalize_book_sequence(raw)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stored = store_raw_book_sequence(raw, root / "raw")
            inventory = {
                "schema_version": "qcrl.polymarket_live_evidence_inventory.v1",
                "artifacts": [{
                    "path": f"raw/{stored.name}",
                    "schema_version": raw["schema_version"],
                    "artifact_sha256": raw["sequence_sha256"],
                    "normalized_sha256": normalized["sequence_sha256"],
                    "captured_at_utc": raw["capture_started_at_utc"],
                    "evidence_role": "test_sequence",
                    "limitations": ["synthetic test data"],
                }],
            }
            (root / "inventory.json").write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            self.assertEqual(1, verify_live_evidence_inventory(root))

    def test_cli_declares_finite_defaults_and_rejects_bad_numbers(self):
        args = build_parser().parse_args(["capture-sequence", "123456"])
        self.assertEqual(5, args.samples)
        self.assertEqual(5, args.interval_seconds)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["capture-sequence", "123456", "--samples", "five"])


if __name__ == "__main__":
    unittest.main()
