"""Opt-in v2 bounded prefix draining; never changes v1 expectations."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import verify_stream_log
from execution_truth.market_stream import stream_plan, collect_market_stream
from execution_truth.receive_path import (ReceivePathTracker, declare, elapsed_bounds, policy_for, validate_contract, validate_delivery)
from execution_truth.rolling_stream import pilot_plan, validate_plan
from execution_truth.stream_segments import SegmentedStreamLog
from tests.receive_burst_fixture import SCENARIOS, run_scenario
from tests.test_market_stream import Clock
from tests.test_receive_capture import rows
from tests.test_receive_path import DOMAIN, stamp
from tests.test_receive_adapter import AVAILABLE, local_server
from execution_truth.receive_adapter import ObservedSocket, validate_adapter_failure
from tests.test_market_stream import book
from tests.test_taker_replay import raw_bundle
import json
import time


def saturated():
    tracker = ReceivePathTracker(declare("a" * 64, DOMAIN, stream_spec_sha256="b" * 64, policy_version="v2"))
    tracker.begin_connection(1)
    for number in range(1, 66):
        tracker.observe_frame(1, 1, True, b"same", stamp(number))
    return tracker


class DrainTests(unittest.TestCase):
    def test_v1_stays_default_and_v2_requires_explicit_policy(self):
        default = declare("a" * 64, DOMAIN, stream_spec_sha256="b" * 64)
        self.assertEqual(default["schema_version"], "qcrl.receive_path_contract.v1")
        v2 = declare("a" * 64, DOMAIN, stream_spec_sha256="b" * 64, policy_version="v2")
        self.assertEqual(validate_contract(v2), v2)
        self.assertEqual(policy_for("v2")["max_pending_message_markers"], 64)
        changed = deepcopy(v2)
        changed["policy"]["max_pending_message_markers"] = 65
        changed["contract_sha256"] = payload_hash({k: v for k, v in changed.items() if k != "contract_sha256"})
        with self.assertRaises(ContractError):
            validate_contract(changed)
        clock = Clock()
        plan = pilot_plan(int(clock.base.timestamp()) + 300, now=clock.utc(), profiling=True,
                          deferred=True, receive_path=True, receive_policy="v2")
        self.assertEqual(plan["schema_version"], "qcrl.btc_5m_rolling_pilot.v6")
        self.assertEqual(validate_plan(plan), plan)
        with self.assertRaises(ContractError):
            pilot_plan(int(clock.base.timestamp()) + 300, now=clock.utc(), receive_policy="v2")

    def test_saturation_drains_only_identified_prefix_then_stays_unknown(self):
        tracker = saturated()
        self.assertEqual(len(tracker.pending), 64)
        self.assertFalse(tracker.observe_frame(1, 1, True, b"same", stamp(66)))
        for index in range(64):
            record = tracker.deliver(1, "same", stamp(100 + index))
            validate_delivery(record, tracker.contract, "same")
            self.assertEqual(record["receive_marker"]["message_sequence"], index + 1)
            self.assertEqual(record["pending_marker_depth"], 63 - index)
        record = tracker.deliver(1, "same", stamp(200))
        self.assertFalse(record["telemetry_available"])
        self.assertEqual(record["unavailable_reason"], "pending_marker_budget")
        validate_delivery(record, tracker.contract, "same")
        self.assertFalse(tracker.observe_frame(1, 1, True, b"same", stamp(201)))
        self.assertEqual(tracker.begin_connection(2)["previous_disabled_reason"], "pending_marker_budget")
        self.assertTrue(tracker.observe_frame(2, 1, True, b"same", stamp(202)))
        self.assertEqual(tracker.deliver(2, "same", stamp(203))["receive_marker"]["message_sequence"], 1)

    def test_mismatch_and_invalid_delivery_timing_discard_retained_markers(self):
        tracker = saturated()
        record = tracker.deliver(1, "different", stamp(100))
        self.assertEqual(record["unavailable_reason"], "fifo_message_mismatch")
        self.assertEqual(len(tracker.pending), 0)
        validate_delivery(record, tracker.contract, "different")
        tracker = saturated()
        with self.assertRaises(ContractError):
            tracker.deliver(1, "same", stamp(0))
        self.assertEqual(len(tracker.pending), 0)
        self.assertEqual(tracker.disabled_reason, "delivery_timing_error")

    def test_fragment_budget_error_is_not_drainable_saturation(self):
        tracker = saturated()
        tracker.begin_connection(2)
        for index in range(64):
            tracker.observe_frame(2, 1, True, b"same", stamp(100 + index))
        for index in range(65):
            tracker.observe_frame(2, 1 if index == 0 else 0, index == 64, b"x", stamp(200 + index))
        self.assertEqual(tracker.disabled_reason, "message_telemetry_budget")
        self.assertEqual(len(tracker.pending), 0)
        self.assertIsNone(tracker.saturation)

    def test_receiver_clock_errors_discard_the_prefix_even_while_draining(self):
        tracker = saturated()
        self.assertFalse(tracker.observe_frame(1, 1, True, b"same", stamp(0)))
        self.assertEqual(tracker.disabled_reason, "receiver_monotonic_regression")
        self.assertEqual(len(tracker.pending), 0)
        tracker = saturated()
        invalid = stamp(70)
        invalid["clock_domain"] = "wrong"
        with self.assertRaises(ContractError):
            tracker.observe_frame(1, 1, True, b"same", invalid)
        self.assertEqual(tracker.disabled_reason, "invalid_receiver_clock")
        self.assertEqual(len(tracker.pending), 0)

    def test_entire_recorder_matrix_preserves_bounded_prefix_and_raw_messages(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["name"]), tempfile.TemporaryDirectory() as root:
                report = run_scenario(scenario, Path(root) / "capture", receive_policy="v2")
                self.assertEqual(report["verification"]["header_spec"]["schema_version"], "qcrl.public_market_stream_spec.v5")
                for index, settings in enumerate(scenario["connections"], 1):
                    detail = report["connections"][str(index)]
                    expected = settings.get("prefix", 0) + min(settings.get("deliver_burst", settings["burst"]), 64)
                    self.assertEqual(detail["available"], expected)
                    self.assertEqual(detail["available_message_sequences"], list(range(1, expected + 1)))
                self.assertLessEqual(report["observation"]["max_pending_markers"], 64)
                self.assertTrue(report["delivered_raw_unchanged"])

    def test_archive_rejects_changed_saturation_or_early_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "source"
            run_scenario(SCENARIOS[4], path, receive_policy="v2")
            original = rows(path / "stream")
            for case in ("changed", "early_unknown", "missing", "resume"):
                altered = deepcopy(original)
                frames = [row for row in altered if row["kind"] == "frame"]
                record = frames[1]["payload"]["receive_path"]
                if case == "changed":
                    record["saturation"]["overflow_frame_sequence"] += 1
                elif case == "missing":
                    record["saturation"] = None
                elif case == "resume":
                    later = frames[65]["payload"]["receive_path"]["application_delivery"]
                    record = deepcopy(frames[63]["payload"]["receive_path"])
                    record["saturation"] = None
                    record["application_delivery"] = later
                    record["receive_marker"]["message_sequence"] = 65
                    record["receive_marker"]["first_frame_sequence"] = 65
                    record["receive_marker"]["last_frame_sequence"] = 65
                    for field, source in (("first_observation_to_delivery", "first_receive_observation"),
                                          ("last_observation_to_delivery", "last_receive_observation")):
                        record[field] = elapsed_bounds(record["receive_marker"][source], later, later["clock_domain"])
                    frames[65]["payload"]["receive_path"] = record
                else:
                    record = deepcopy(frames[64]["payload"]["receive_path"])
                    record["application_delivery"] = frames[1]["payload"]["receive_path"]["application_delivery"]
                    frames[1]["payload"]["receive_path"] = record
                record["telemetry_sha256"] = payload_hash({k: v for k, v in record.items() if k != "telemetry_sha256"})
                validate_delivery(record, original[0]["payload"]["receive_path_contract"], frames[1]["payload"]["raw_text"])
                clock = Clock()
                log = SegmentedStreamLog(Path(root) / case, clock.utc, clock.mono, original[0]["payload"]["spec"]["storage"])
                for row in altered:
                    log.append(row["kind"], row["payload"])
                log.close()
                with self.assertRaises(ContractError):
                    verify_stream_log(Path(root) / case)

    @unittest.skipUnless(AVAILABLE, "requires pinned websockets runtime")
    def test_real_localhost_v2_recorder_and_archive(self):
        from websockets.exceptions import ConnectionClosed
        clock = Clock()
        plan = stream_plan(raw_bundle(), segmented=True, profiling=True, receive_path=True,
                           receive_policy="v2", source_plan_sha256="a" * 64, max_seconds=5, max_frames=3)
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
            def connector(tracker, number, **kwargs):
                return ObservedSocket(uri, tracker, number, **kwargs)
            path = Path(root) / "stream"
            collect_market_stream(raw_bundle(), plan, path, connector=connector, clock=clock.utc,
                                  monotonic=time.monotonic, clock_domain="local.recorder.v2")
            verified = verify_stream_log(path)
            self.assertEqual(verified["receive_path_verification"]["available"], 3)
            self.assertEqual([r["payload"]["raw_text"] for r in rows(path) if r["kind"] == "frame"], messages)

    @unittest.skipUnless(AVAILABLE, "requires pinned websockets runtime")
    def test_real_adapter_v2_and_metadata_failure_preserve_raw(self):
        def handler(connection):
            connection.send("first")
            connection.send("second")
            connection.recv(timeout=3)
        with local_server(handler) as uri:
            tracker = ReceivePathTracker(declare("a" * 64, "local.v2", stream_spec_sha256="b" * 64, policy_version="v2"))
            client = ObservedSocket(uri, tracker, 1)
            try:
                raw, record = client.recv(3)
                self.assertEqual(raw, "first")
                self.assertEqual(record["schema_version"], "qcrl.receive_path_delivery.v2")
                validate_delivery(record, tracker.contract, raw)
                with patch.object(client, "queue_snapshot", side_effect=RuntimeError("fixture")):
                    raw, record = client.recv(3)
                self.assertEqual(raw, "second")
                validate_adapter_failure(record, tracker.contract, raw)
                self.assertEqual(len(tracker.pending), 0)
                client.send("done")
            finally:
                client.close()
