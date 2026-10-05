from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_truth.contracts import ContractError
from execution_truth.market_stream import stream_plan, classify_frame, collect_market_stream, verify_stream_log, StreamTransportError
from tests.test_taker_replay import raw_bundle


class Clock:
    def __init__(self):
        self.seconds = 0
        self.base = datetime(2026, 5, 4, 23, 50, tzinfo=timezone.utc)

    def utc(self):
        return self.base + timedelta(seconds=self.seconds)

    def mono(self):
        return self.seconds

    def pause(self, seconds):
        self.seconds += seconds


class Socket:
    def __init__(self, clock, frames):
        self.clock, self.frames, self.sent, self.closed = clock, frames, [], False

    def send(self, message):
        self.sent.append(message)

    def recv(self, timeout):
        self.clock.seconds += timeout
        if not self.frames:
            raise TimeoutError()
        value = self.frames.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.closed = True


def book(spec, asset):
    return {"event_type": "book", "market": spec["condition_id"], "asset_id": asset,
            "bids": [], "asks": [], "timestamp": "1777938600000"}


class MarketStreamTests(unittest.TestCase):
    def run_capture(self, path, frames, seconds=4, maximum=100):
        raw = raw_bundle()
        spec = stream_plan(raw, max_seconds=seconds, max_frames=maximum)
        clock = Clock()
        sockets = []
        def connector():
            socket = Socket(clock, frames)
            sockets.append(socket)
            return socket
        result = collect_market_stream(raw, spec, path, connector=connector,
                                       clock=clock.utc, monotonic=clock.mono, pause=clock.pause)
        return result, sockets

    def test_public_plan_is_bounded_and_has_both_outcomes(self):
        spec = stream_plan(raw_bundle())
        self.assertEqual(["10001", "10002"], spec["subscription"]["assets_ids"])
        self.assertEqual("market", spec["subscription"]["type"])
        self.assertFalse(spec["orders_authorized"])
        for seconds, frames in ((True, 100), (601, 100), (10, 100001)):
            with self.assertRaises(ContractError):
                stream_plan(raw_bundle(), max_seconds=seconds, max_frames=frames)

    def test_records_array_frames_both_books_raw_and_chain(self):
        spec = stream_plan(raw_bundle())
        frame = json.dumps([book(spec, a) for a in spec["asset_ids"]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.ndjson"
            result, sockets = self.run_capture(path, [frame, "PONG"])
            self.assertEqual(2, result["frames"])
            self.assertEqual(["10001", "10002"], result["book_snapshot_assets_by_connection"]["1"])
            self.assertFalse(result["continuous_coverage_proven"])
            self.assertTrue(verify_stream_log(path)["session_end_present"])
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(frame, next(r for r in rows if r["kind"] == "frame")["payload"]["raw_text"])
            self.assertTrue(sockets[0].closed)
            self.assertEqual("market", json.loads(sockets[0].sent[0])["type"])

    def test_scope_does_not_mix_market_assets_and_retains_unknown_frames(self):
        spec = stream_plan(raw_bundle())
        event = book(spec, "999")
        self.assertEqual("unconfirmed_or_other_market", classify_frame(json.dumps(event), spec)[0]["scope"])
        event = {"event_type": "price_change", "market": spec["condition_id"],
                 "price_changes": [{"asset_id": "10001"}, {"asset_id": "999"}]}
        self.assertEqual("unconfirmed_or_other_market", classify_frame(json.dumps(event), spec)[0]["scope"])
        self.assertEqual("unknown", classify_frame("not json", spec)[0]["scope"])
        with tempfile.TemporaryDirectory() as directory:
            result, _ = self.run_capture(Path(directory) / "stream.ndjson", ["not json"])
            self.assertEqual(1, result["event_counts"]["unknown:unparsed"])

    def test_reconnect_is_logged_and_book_baselines_not_carried_forward(self):
        spec = stream_plan(raw_bundle())
        frames = [json.dumps(book(spec, "10001")), StreamTransportError("test_disconnect"),
                  json.dumps(book(spec, "10002"))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.ndjson"
            result, sockets = self.run_capture(path, frames, seconds=8)
            self.assertEqual(2, result["connections"])
            self.assertEqual(["10001"], result["book_snapshot_assets_by_connection"]["1"])
            self.assertEqual(["10002"], result["book_snapshot_assets_by_connection"]["2"])
            self.assertIn('"kind": "connection_gap"', path.read_text())
            self.assertTrue(all(s.closed for s in sockets))

    def test_ping_only_and_missing_pong_produces_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.ndjson"
            result, sockets = self.run_capture(path, [], seconds=35)
            self.assertEqual(2, result["connections"])
            self.assertIn("PING", sockets[0].sent)
            self.assertIn("pong_timeout", path.read_text())
            for socket in sockets:
                for sent in socket.sent:
                    self.assertTrue(sent == "PING" or json.loads(sent)["type"] == "market")

    def test_existing_file_never_overwritten_and_partial_prefix_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.ndjson"
            self.run_capture(path, [])
            original = path.read_text()
            with self.assertRaises(FileExistsError):
                self.run_capture(path, [])
            self.assertEqual(original, path.read_text())
            path.write_text("\n".join(original.splitlines()[:-1]) + "\n")
            self.assertFalse(verify_stream_log(path)["session_end_present"])

    def test_tamper_reorder_and_truncated_line_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stream.ndjson"
            self.run_capture(path, ["PONG"])
            original = path.read_text()
            path.write_text(original.replace('"raw_text": "PONG"', '"raw_text": "FAKE"'))
            with self.assertRaises(ContractError):
                verify_stream_log(path)
            path.write_text(original[:-1])
            with self.assertRaisesRegex(ContractError, "truncated"):
                verify_stream_log(path)
            rows = original.splitlines()
            rows[1], rows[2] = rows[2], rows[1]
            path.write_text("\n".join(rows) + "\n")
            with self.assertRaisesRegex(ContractError, "chain"):
                verify_stream_log(path)

    def test_mutated_spec_and_expired_market_reject_before_connection(self):
        raw = raw_bundle()
        spec = stream_plan(raw)
        spec["subscription"]["type"] = "user"
        with self.assertRaisesRegex(ContractError, "public-only"):
            collect_market_stream(raw, spec, "/unused", connector=lambda: self.fail("must not connect"))
        with self.assertRaisesRegex(ContractError, "lifecycle"):
            collect_market_stream(raw, stream_plan(raw), "/unused", connector=lambda: self.fail("must not connect"),
                                  clock=lambda: datetime(2026, 5, 5, tzinfo=timezone.utc))

    def test_frame_quota_is_explicit_not_successful_full_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _ = self.run_capture(Path(directory) / "stream.ndjson", ["PONG", "PONG"], maximum=1)
            self.assertEqual("frame_limit", result["status"])
            self.assertEqual(1, result["frames"])
            self.assertFalse(result["continuous_coverage_proven"])

    def test_preview_cli_does_not_need_websocket_dependency_or_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.json"
            path.write_text(json.dumps(raw_bundle()))
            completed = subprocess.run([sys.executable, str(Path(__file__).parents[1] / "qcrl_execution_truth.py"),
                                        "market-stream", str(path)], check=True, capture_output=True, text=True)
            self.assertEqual("market", json.loads(completed.stdout)["subscription"]["type"])


if __name__ == "__main__":
    unittest.main()
