import ast
from datetime import datetime, timezone
import gzip
import inspect
import json
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import verify_stream_log
from execution_truth.stream_segments import SegmentedStreamLog, StreamQuotaError
from infra.stream.single_pass_encoder import SinglePassStreamLog, encode_row
from infra.stream import recorder_stage_replay as replay
from tests.test_recorder_stage_replay import fixture


class SinglePassEncoderTests(unittest.TestCase):
    def test_logical_hash_and_fields_unicode_quotes_braces_numbers(self):
        digest, content = encode_row({})
        self.assertEqual(json.loads(content), {"record_sha256": payload_hash({})})
        for payload in ({}, {"text": '\"}\\\n é 🐉', "nested": [None, True, False, -0.0, 1e40]},
                        {"record_sha256": "nested is allowed", "values": [1, 2.5, {"a": "}"}]}):
            row = {"payload": payload, "ordinal": 0, "previous_sha256": None}
            digest, content = encode_row(row)
            self.assertEqual(digest, payload_hash(row))
            self.assertEqual(json.loads(content), dict(row, record_sha256=digest))
            self.assertNotIn("record_sha256", row)
            self.assertTrue(content.endswith(b'"}\n'))
        for invalid in ([], {"record_sha256": None}):
            with self.assertRaises(ContractError): encode_row(invalid)

    def test_candidate_append_is_reference_except_encoding(self):
        def body(method):
            return ast.parse(textwrap.dedent(inspect.getsource(method))).body[0].body
        reference, candidate = body(SegmentedStreamLog.append), body(SinglePassStreamLog.append)
        # Exactly two old assignments become one candidate assignment. Every
        # timing, quota, segmentation, integrity and fsync branch stays equal.
        self.assertEqual([ast.dump(n) for n in reference[:2]+reference[4:]],
                         [ast.dump(n) for n in candidate[:2]+candidate[3:]])

    def test_real_archive_fixed_clock_identical_decoded_rows_and_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root/"source")
            rows, spec, original = replay.load_rows(root/"source")
            replay.durable_rows(rows, spec, root/"reference")
            with patch.object(replay, "SegmentedStreamLog", SinglePassStreamLog):
                replay.durable_rows(rows, spec, root/"candidate")
            def decoded(path):
                return [json.loads(line) for segment in sorted(path.glob("*.gz"))
                        for line in gzip.open(segment, "rb")]
            self.assertEqual(decoded(root/"reference"), decoded(root/"candidate"))
            verified = verify_stream_log(root/"candidate")
            differing = {"segments", "compressed_bytes", "uncompressed_bytes"}
            self.assertEqual({k:v for k,v in original.items() if k not in differing},
                             {k:v for k,v in verified.items() if k not in differing})
            self.assertLess(verified["uncompressed_bytes"], original["uncompressed_bytes"])

    def test_fsync_cadence_and_exclusive_outputs_preserved(self):
        counts = []
        policy = {"segment_uncompressed_bytes": 8*1024**2, "max_uncompressed_bytes": 1024**3,
                  "max_compressed_bytes": 256*1024**2}
        with tempfile.TemporaryDirectory() as tmp:
            for index, cls in enumerate((SegmentedStreamLog, SinglePassStreamLog)):
                with patch("execution_truth.stream_segments.os.fsync") as sync:
                    log = cls(Path(tmp)/str(index), lambda: datetime(2026,1,1,tzinfo=timezone.utc), lambda: 1, policy)
                    log.append("session_start", {})
                    for _ in range(70): log.append("frame", {"value": 1})
                    log.append("session_end", {}); log.close()
                    counts.append(sync.call_count)
                with self.assertRaises(FileExistsError):
                    cls(Path(tmp)/str(index), lambda: None, lambda: 1, policy)
            self.assertEqual(counts[0], counts[1])

    def test_record_and_total_byte_limits_unchanged(self):
        base = {"segment_uncompressed_bytes": 8*1024**2, "max_uncompressed_bytes": 1024**3,
                "max_compressed_bytes": 256*1024**2}
        with tempfile.TemporaryDirectory() as tmp:
            for index, cls in enumerate((SegmentedStreamLog, SinglePassStreamLog)):
                for budget, payload in ((base, {"text": "x"*(4*1024**2)}),
                                        (dict(base,max_uncompressed_bytes=1), {}),
                                        (dict(base,max_compressed_bytes=4*1024**2), {})):
                    path = Path(tmp)/str(index)/str(len(list((Path(tmp)/str(index)).glob('*'))))
                    log = cls(path, lambda: datetime(2026,1,1,tzinfo=timezone.utc), lambda: 1, budget)
                    try:
                        with self.assertRaises(StreamQuotaError): log.append("frame", payload)
                    finally: log.close()
