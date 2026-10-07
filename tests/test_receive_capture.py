"""Versioned recorder integration: offline fixtures and real localhost only."""

from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import time
import unittest

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log, StreamTransportError
from execution_truth.receive_adapter import ObservedSocket
from execution_truth.receive_path import sample_clock
from execution_truth.rolling_stream import pilot_plan, validate_plan
from execution_truth.stream_segments import SegmentedStreamLog
from tests.test_market_stream import Clock, Socket, book
from tests.test_receive_adapter import AVAILABLE, local_server
from tests.test_taker_replay import raw_bundle


def spec():
    return stream_plan(raw_bundle(), segmented=True, profiling=True, receive_path=True,
                       source_plan_sha256="a" * 64, max_seconds=5, max_frames=3)


def rows(path):
    result = []
    for file in sorted(Path(path).glob("segment-*.gz")):
        with gzip.open(file, "rt") as handle:
            result.extend(json.loads(line) for line in handle)
    return result


class ReceiveCaptureTests(unittest.TestCase):
    def capture(self, path, *, reconnect=False, unavailable=False):
        clock, plan = Clock(), spec()
        def connector(tracker, number, **kwargs):
            frames = [json.dumps(book(plan, asset)) for asset in plan["asset_ids"]] + ["PONG"]
            if reconnect and number == 1:
                frames = [frames[0], StreamTransportError("fixture_gap")]
            class Instrumented(Socket):
                def recv(self, timeout):
                    message = super().recv(timeout)
                    if not unavailable:
                        tracker.observe_frame(number, 1, True, message.encode(),
                                              sample_clock(clock.utc, clock.mono, tracker.domain))
                    return message, tracker.deliver(number, message,
                                                   sample_clock(clock.utc, clock.mono, tracker.domain))
            socket = Instrumented(clock, frames)
            socket.reset = tracker.begin_connection(number)
            return socket
        if reconnect:
            plan["max_seconds"] = 10
        collect_market_stream(raw_bundle(), plan, path, connector=connector, clock=clock.utc,
                              monotonic=clock.mono, pause=clock.pause, clock_domain="fixture.capture")
        return verify_stream_log(path)

    def test_opt_in_and_default_versions(self):
        self.assertEqual(stream_plan(raw_bundle(), segmented=True)["schema_version"],
                         "qcrl.public_market_stream_spec.v3")
        self.assertEqual(spec()["schema_version"], "qcrl.public_market_stream_spec.v4")
        clock = Clock()
        plan = pilot_plan(int(clock.base.timestamp()) + 300, now=clock.utc(), profiling=True,
                          deferred=True, receive_path=True)
        self.assertEqual(plan["schema_version"], "qcrl.btc_5m_rolling_pilot.v5")
        self.assertEqual(validate_plan(plan), plan)
        for options in ({"receive_path": True}, {"receive_path": True, "profiling": True}):
            with self.assertRaises(ContractError):
                pilot_plan(int(clock.base.timestamp()) + 300, now=clock.utc(), **options)
        changed = deepcopy(plan)
        changed["receive_path"]["max_pending_message_markers"] = 65
        changed["plan_sha256"] = payload_hash({k: v for k, v in changed.items() if k != "plan_sha256"})
        with self.assertRaises(ContractError):
            validate_plan(changed)

    def test_available_reconnect_and_unknown_archives(self):
        for reconnect, unavailable in ((False, False), (True, False), (False, True)):
            with self.subTest(reconnect=reconnect, unavailable=unavailable), tempfile.TemporaryDirectory() as root:
                result = self.capture(Path(root) / "stream", reconnect=reconnect, unavailable=unavailable)
                telemetry = result["receive_path_verification"]
                self.assertEqual(result["frames"], 3)
                self.assertEqual(telemetry["unavailable"], 3 if unavailable else 0)
                self.assertEqual(telemetry["available"], 0 if unavailable else 3)
                self.assertEqual(result["connection_gaps"], int(reconnect))
                self.assertTrue(result["session_end_present"])

    def test_rehashed_semantic_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source"
            self.capture(source)
            original = rows(source)
            for kind in ("missing", "duplicate", "connection", "raw", "clock", "contract", "reset"):
                with self.subTest(kind=kind):
                    altered = deepcopy(original)
                    frames = [row for row in altered if row["kind"] == "frame"]
                    record = frames[1]["payload"]["receive_path"]
                    if kind == "missing":
                        del frames[1]["payload"]["receive_path"]
                    elif kind == "duplicate":
                        record["receive_marker"]["message_sequence"] = 1
                    elif kind == "connection":
                        record["connection"] = 2
                    elif kind == "raw":
                        frames[1]["payload"]["raw_text"] = "PONG"
                        frames[1]["payload"]["classification"] = [{"event_type": "PONG", "scope": "heartbeat"}]
                    elif kind == "clock":
                        record["application_delivery"]["clock_domain"] = "other.boot"
                    elif kind == "contract":
                        record["contract_sha256"] = "b" * 64
                    elif kind == "reset":
                        next(row for row in altered if row["kind"] == "receive_path_reset")["payload"]["new_connection"] = 2
                    if kind != "missing":
                        record["telemetry_sha256"] = payload_hash({k: v for k, v in record.items() if k != "telemetry_sha256"})
                    clock = Clock()
                    target = Path(root) / kind
                    log = SegmentedStreamLog(target, clock.utc, clock.mono, spec()["storage"])
                    for row in altered:
                        log.append(row["kind"], row["payload"])
                    log.close()
                    with self.assertRaises(ContractError):
                        verify_stream_log(target)

    @unittest.skipUnless(AVAILABLE, "requires pinned websockets runtime")
    def test_real_localhost_recorder_and_independent_archive_verifier(self):
        from websockets.exceptions import ConnectionClosed
        plan, clock = spec(), Clock()
        messages = [json.dumps(book(plan, asset)) for asset in plan["asset_ids"]] + ["PONG"]
        def handler(connection):
            self.assertEqual(json.loads(connection.recv()), plan["subscription"])
            for message in messages:
                connection.send(message)
            try:
                connection.recv(timeout=3)
            except ConnectionClosed:
                pass
        with local_server(handler) as uri, tempfile.TemporaryDirectory() as root:
            path = Path(root) / "stream"
            def connector(tracker, number, **kwargs):
                return ObservedSocket(uri, tracker, number, **kwargs)
            summary = collect_market_stream(raw_bundle(), plan, path, connector=connector,
                                            clock=clock.utc, monotonic=time.monotonic,
                                            clock_domain="localhost.capture")
            result = verify_stream_log(path)
            self.assertEqual(summary["frames"], 3)
            self.assertEqual(result["receive_path_verification"]["available"], 3)
            self.assertEqual(result["receive_path_verification"]["unavailable"], 0)
            self.assertEqual([row["payload"]["raw_text"] for row in rows(path) if row["kind"] == "frame"], messages)
