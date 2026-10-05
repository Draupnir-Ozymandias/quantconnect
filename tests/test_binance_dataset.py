import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_truth.binance_dataset import assemble_boundary_evidence, store_boundary_assembly
from execution_truth.contracts import ContractError, payload_hash
from tests.test_binance_source import dataset, ROOT, SPEC


LIVE_SPEC = ROOT / "execution_truth/specs/binance_boundary_assembly_retained_20260914_20260930.json"


def resolution(first, closes, market_id):
    source = dataset(first, closes)
    observations = source["observations"]
    raw = {
        "schema_version": "qcrl.binance_raw_resolution_candles.v1",
        "acquired_at_utc": "2026-10-05T20:00:00Z", "market_id": market_id,
        "symbol": "BTCUSDT", "interval": "1m",
        "declared_resolution_source": "https://www.binance.com/en/trade/BTC_USDT",
        "event_start_at_utc": observations[0]["observation"]["observed_at_utc"].replace("16:05:00", "16:00:00"),
        "event_end_at_utc": observations[1]["observation"]["observed_at_utc"].replace("16:05:00", "16:00:00"),
        "observations": {"start_candle": observations[0]["observation"],
                         "end_candle": observations[1]["observation"]},
    }
    return rehash(raw)


def rehash(raw):
    for observation in raw["observations"].values():
        observation["payload_sha256"] = payload_hash(observation["payload"])
    raw.pop("resolution_candles_sha256", None)
    raw["resolution_candles_sha256"] = payload_hash(raw)
    return raw


def write_spec(directory, records):
    spec = copy.deepcopy(json.loads(LIVE_SPEC.read_text()))
    spec["declaration_path"] = str(SPEC)
    spec["first_boundary_local_date"] = "2026-09-27"
    spec["last_boundary_local_date"] = "2026-09-29"
    spec["sources"] = []
    for index, raw in enumerate(records):
        path = Path(directory) / f"source-{index}.json"
        data = json.dumps(raw).encode()
        path.write_bytes(data)
        spec["sources"].append({"path": path.name, "market_id": raw["market_id"],
                                "file_sha256": hashlib.sha256(data).hexdigest()})
    path = Path(directory) / "spec.json"
    path.write_text(json.dumps(spec))
    return path


class BinanceDatasetTests(unittest.TestCase):
    def test_retained_assembly_has_explicit_gaps_and_provenance(self):
        result = assemble_boundary_evidence(LIVE_SPEC)
        audit = result["source_audit"]
        self.assertEqual(5, result["source_count"])
        self.assertEqual(10, audit["observed_boundary_count"])
        self.assertEqual(17, audit["expected_boundary_count"])
        self.assertEqual(7, len(audit["missing_boundary_local_dates"]))
        self.assertEqual(7, len(audit["source_records"]))
        self.assertFalse(audit["complete"])
        self.assertEqual("50149fcd0881cbad6f0e373b7737a2420b9e9c4f87f16024e779bb58b07dc600", result["assembly_sha256"])
        for entry in result["dataset"]["observations"]:
            self.assertEqual(1, len(entry["source_references"]))
            self.assertEqual(payload_hash(entry["observation"]), entry["source_references"][0]["observation_sha256"])

    def test_shared_identical_payload_preserves_both_references_latest_time(self):
        first = resolution("2026-09-27", ("100", "101"), "1")
        second = resolution("2026-09-28", ("101", "102"), "2")
        second["observations"]["start_candle"]["observed_at_utc"] = "2026-09-28T16:06:00Z"
        rehash(second)
        original = copy.deepcopy((first, second))
        with tempfile.TemporaryDirectory() as directory:
            result = assemble_boundary_evidence(write_spec(directory, [first, second]))
        middle = result["dataset"]["observations"][1]
        self.assertEqual(2, len(middle["source_references"]))
        self.assertEqual("2026-09-28T16:06:00Z", middle["observation"]["observed_at_utc"])
        self.assertTrue(result["source_audit"]["complete"])
        self.assertEqual(original, (first, second))

    def test_shared_conflicting_payload_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_spec(directory, [resolution("2026-09-27", ("100", "101"), "1"),
                                          resolution("2026-09-28", ("999", "102"), "2")])
            with self.assertRaisesRegex(ContractError, "conflicting"):
                assemble_boundary_evidence(path)

    def test_duplicate_source_rejects(self):
        raw = resolution("2026-09-27", ("100", "101"), "1")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ContractError, "duplicate"):
                assemble_boundary_evidence(write_spec(directory, [raw, raw]))

    def test_file_hash_and_market_identity_reject(self):
        for field, value, expected in (("file_sha256", "0" * 64, "file hash"),
                                       ("market_id", "999", "identity")):
            with tempfile.TemporaryDirectory() as directory:
                path = write_spec(directory, [resolution("2026-09-27", ("100", "101"), "1")])
                spec = json.loads(path.read_text())
                spec["sources"][0][field] = value
                path.write_text(json.dumps(spec))
                with self.assertRaisesRegex(ContractError, expected):
                    assemble_boundary_evidence(path)

    def test_declaration_and_range_mismatch_reject(self):
        for field, value in (("declaration_sha256", "0" * 64), ("first_boundary_local_date", "2026-09-28")):
            with tempfile.TemporaryDirectory() as directory:
                path = write_spec(directory, [resolution("2026-09-27", ("100", "101"), "1")])
                spec = json.loads(path.read_text())
                spec[field] = value
                path.write_text(json.dumps(spec))
                with self.assertRaises(ContractError):
                    assemble_boundary_evidence(path)

    def test_content_addressed_storage_is_idempotent_and_tamper_rejects(self):
        result = assemble_boundary_evidence(LIVE_SPEC)
        with tempfile.TemporaryDirectory() as directory:
            path = store_boundary_assembly(result, directory)
            self.assertEqual(path, store_boundary_assembly(result, directory))
            result["source_count"] = 99
            with self.assertRaisesRegex(ContractError, "hash mismatch"):
                store_boundary_assembly(result, directory)

    def test_cli_reproduces_live_assembly(self):
        result = subprocess.run([sys.executable, str(ROOT / "qcrl_execution_truth.py"),
                                 "research-dataset", str(LIVE_SPEC)],
                                check=True, capture_output=True, text=True)
        self.assertEqual(assemble_boundary_evidence(LIVE_SPEC), json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
