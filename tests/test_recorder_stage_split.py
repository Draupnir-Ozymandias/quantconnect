import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream import recorder_stage_split as split
from tests.test_recorder_stage_replay import fixture


class StageSplitTests(unittest.TestCase):
    def prepare_measure(self, root):
        fixture(root/"source")
        with patch.object(split, "identity", return_value={"pid": 1}):
            split.prepare(root/"source", root/"run")
        with patch.object(split, "identity", return_value={"pid": 2}):
            split.measure(root/"source", root/"run")

    def test_complete_separated_flow_all_receipts_and_output_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare_measure(root)
            with self.assertRaises(FileNotFoundError):
                split.finalize(root/"source", root/"run")
            self.assertFalse((root/"run/report.json").exists())
            for r, stage in split.case_order():
                with patch.object(split, "identity", return_value={"pid": 3}):
                    receipt = split.verify_stage(root/"source", root/"run", r, stage)
                self.assertTrue(receipt["verified"])
            result = split.finalize(root/"source", root/"run")
            verify_artifact_hash(result, "report_sha256", "report")
            self.assertEqual(len(result["results"]), 15)
            self.assertEqual(set(result["medians"]), set(split.POLICY["stages"]))
            self.assertTrue(all(not r["checkpoint"]["verified"] for r in result["results"]))
            with self.assertRaises(FileExistsError):
                split.finalize(root/"source", root/"run")

    def test_interruption_preserves_checkpoint_without_completed_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root/"source")
            split.prepare(root/"source", root/"run")
            with patch.object(split.stages, "freshness_rows", side_effect=RuntimeError("interrupted")):
                with self.assertRaises(RuntimeError):
                    split.measure(root/"source", root/"run")
            cp = split.read(root/"run/0-encode_hash.checkpoint.json", "checkpoint_sha256")
            self.assertFalse(cp["verified"])
            self.assertFalse((root/"run/measured.json").exists())
            self.assertFalse((root/"run/report.json").exists())
            with self.assertRaises(FileExistsError):
                split.measure(root/"source", root/"run")

    def test_measure_does_not_run_heavy_semantic_verifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root/"source")
            split.prepare(root/"source", root/"run")
            with patch.object(split, "verify_stream_log", side_effect=AssertionError("heavy audit in measurement")):
                split.measure(root/"source", root/"run")

    def test_changed_input_and_changed_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare_measure(root)
            path = root/"run/measurement/0-gzip_write/synthetic-000000.gz"
            with path.open("ab") as handle:
                handle.write(b"changed")
            with self.assertRaisesRegex(ContractError, "output files"):
                split.verify_stage(root/"source", root/"run", 0, "gzip_write")
            self.assertFalse((root/"run/0-gzip_write.verified.json").exists())
            (root/"source/unexpected.json").write_text("{}")
            with self.assertRaisesRegex(ContractError, "input"):
                split.check_binding(root/"source", root/"run")

    def test_resigned_false_checkpoint_and_nonfinite_time_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare_measure(root)
            path = root/"run/0-encode_hash.checkpoint.json"
            cp = split.read(path, "checkpoint_sha256")
            cp["detail"]["records"] += 1
            cp.pop("checkpoint_sha256")
            cp["checkpoint_sha256"] = payload_hash(cp)
            path.write_text(json.dumps(cp))
            with self.assertRaisesRegex(ContractError, "encoding"):
                split.verify_stage(root/"source", root/"run", 0, "encode_hash")
            cp["cpu_seconds"] = cp["wall_seconds"] = float("inf")
            cp.pop("checkpoint_sha256")
            cp["checkpoint_sha256"] = payload_hash(cp)
            path.write_text(json.dumps(cp))
            with self.assertRaisesRegex(ContractError, "timing"):
                split.verify_stage(root/"source", root/"run", 0, "encode_hash")

    def test_overlapping_processes_cannot_finalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare_measure(root)
            for r, stage in split.case_order():
                with patch.object(split, "identity", return_value={"pid": 2}):
                    split.verify_stage(root/"source", root/"run", r, stage)
            with self.assertRaisesRegex(ContractError, "identities overlap"):
                split.finalize(root/"source", root/"run")
            self.assertFalse((root/"run/report.json").exists())
