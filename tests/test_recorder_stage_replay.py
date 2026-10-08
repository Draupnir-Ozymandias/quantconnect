from datetime import timedelta
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import collect_market_stream, stream_plan
from execution_truth.receive_path import sample_clock
from infra.stream import recorder_stage_replay as replay
from tests.test_reader_comparison import corpus


def fixture(root, domain="localhost.burst"):
    data = corpus()
    spec = stream_plan(data["bundle"], max_seconds=15, max_frames=8, segmented=True,
                       profiling=True, resilient=True, receive_path=True,
                       freshness_telemetry=True, receive_policy="v3", source_plan_sha256="a"*64)
    base, origin = _time(spec["event_start_at_utc"]), time.monotonic()
    def clock():
        return base + timedelta(seconds=time.monotonic()-origin)
    raw = json.loads(data["book_template"])
    for event in raw:
        event["timestamp"] = str(int(base.timestamp()*1000))
    raw = json.dumps(raw)
    def connector(tracker, number, **kwargs):
        class Socket:
            reset = tracker.begin_connection(number)
            def send(self, message): pass
            def recv(self, timeout):
                tracker.observe_frame(number, 1, True, raw.encode(),
                                      sample_clock(clock, time.monotonic, tracker.domain))
                return raw, tracker.deliver(number, raw,
                                           sample_clock(clock, time.monotonic, tracker.domain))
            def close(self): pass
        return Socket()
    collect_market_stream(data["bundle"], spec, root, connector=connector,
                          clock=clock, clock_domain=domain)


class RecorderStageReplayTests(unittest.TestCase):
    def test_real_writer_identity_all_stages_and_exclusive_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root/"source")
            result = replay.run(root/"source", root/"output")
            verify_artifact_hash(result, "report_sha256", "report")
            self.assertEqual(len(result["results"]), 15)
            self.assertFalse(result["component_times_additive"])
            self.assertFalse(result["socket_delay_causality_proven"])
            for entry in result["results"]:
                self.assertGreaterEqual(entry["cpu_seconds"], 0)
                if entry["stage"] == "freshness":
                    self.assertEqual(entry["detail"]["messages"], 8)
                if entry["stage"] == "gzip_write":
                    self.assertEqual(entry["detail"]["fsync_calls"], 0)
                if entry["stage"] == "gzip_write_fsync":
                    self.assertGreater(entry["detail"]["fsync_calls"], 0)
            with self.assertRaises(FileExistsError):
                replay.run(root/"source", root/"output")

    def test_non_localhost_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"source"
            fixture(source, "synthetic.other")
            with self.assertRaisesRegex(ContractError, "localhost"):
                replay.load_rows(source)

    def test_budget_checked_before_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"source"
            fixture(source)
            with patch.dict(replay.POLICY, max_uncompressed_bytes=1), patch.object(replay, "verify_stream_log") as verify:
                with self.assertRaisesRegex(ContractError, "byte budget"):
                    replay.load_rows(source)
                verify.assert_not_called()

    def test_chain_and_freshness_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"source"
            fixture(source)
            rows, spec, _ = replay.load_rows(source)
            rows[-1]["record_sha256"] = "0"*64
            with self.assertRaisesRegex(ContractError, "digest"):
                replay.encode_rows(rows)
            sample = next(r for r in rows if r["kind"] == "connection_freshness")
            sample["payload"]["counts"]["messages"] = 999
            with self.assertRaisesRegex(ContractError, "freshness"):
                replay.freshness_rows(rows, spec)
