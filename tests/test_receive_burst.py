"""Deterministic recorder-level burst boundaries under unchanged policy."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import verify_stream_log
from execution_truth.receive_path import POLICY, elapsed_bounds, validate_delivery
from execution_truth.stream_segments import SegmentedStreamLog
from tests.receive_burst_fixture import SCENARIOS, run_scenario
from tests.test_market_stream import Clock
from tests.test_receive_capture import rows


class ReceiveBurstTests(unittest.TestCase):
    def test_size_independent_boundary_at_sixty_fifth_pending_message(self):
        for scenario in SCENARIOS[:10]:
            with self.subTest(scenario=scenario["name"]), tempfile.TemporaryDirectory() as root:
                report = run_scenario(scenario, Path(root) / "capture")
                burst = scenario["connections"][0]["burst"]
                expected = burst if burst <= 64 else 0
                connection = report["connections"]["1"]
                self.assertEqual(connection["available"], expected)
                self.assertEqual(connection["available_message_sequences"], list(range(1, expected + 1)))
                self.assertTrue(connection["library_diagnostics_unknown"])
                self.assertLessEqual(report["observation"]["max_pending_markers"], 64)
                self.assertEqual(report["observation"]["overflow_callback_message"], {"1": 65} if burst > 64 else {})
                self.assertEqual(report["verification"]["connection_gaps"], 0)
                self.assertTrue(report["delivered_raw_unchanged"])

    def test_prefix_is_retained_but_queued_markers_are_invalidated_on_overflow(self):
        with tempfile.TemporaryDirectory() as root:
            report = run_scenario(SCENARIOS[10], Path(root) / "capture")
            self.assertEqual(report["connections"]["1"]["available"], 25)
            self.assertEqual(report["connections"]["1"]["unavailable"], 65)
            self.assertEqual(report["observation"]["overflow_callback_message"], {"1": 90})
            self.assertEqual(report["verification"]["connection_gaps"], 0)

    def test_natural_reconnect_recovers_attribution_and_occurrence_ids(self):
        with tempfile.TemporaryDirectory() as root:
            report = run_scenario(SCENARIOS[11], Path(root) / "capture")
            self.assertEqual(report["connections"]["1"]["unavailable"], 65)
            self.assertEqual(report["connections"]["2"]["available_message_sequences"], [1, 2, 3])
            self.assertEqual(report["resets"][1]["previous_disabled_reason"], "pending_marker_budget")
            self.assertEqual(report["verification"]["connection_gaps"], 1)

    def test_fragments_and_protocol_controls_do_not_consume_message_budget(self):
        for scenario in SCENARIOS[12:14]:
            with self.subTest(scenario=scenario["name"]), tempfile.TemporaryDirectory() as root:
                path = Path(root) / "capture"
                report = run_scenario(scenario, path)
                expected = 64 if scenario["connections"][0]["burst"] == 64 else 0
                self.assertEqual(report["connections"]["1"]["available"], expected)
                if expected:
                    records = [row["payload"]["receive_path"] for row in rows(path / "stream") if row["kind"] == "frame"]
                    self.assertTrue(all(r["receive_marker"]["fragment_count"] == 2 for r in records))
                    self.assertEqual(records[-1]["receive_marker"]["last_frame_sequence"], 192)

    def test_undelivered_markers_and_incomplete_fragment_are_discarded_on_reconnect(self):
        with tempfile.TemporaryDirectory() as root:
            report = run_scenario(SCENARIOS[14], Path(root) / "capture")
            self.assertEqual(report["resets"][1]["discarded_pending_markers"], 63)
            self.assertTrue(report["resets"][1]["discarded_incomplete_fragment"])
            self.assertEqual(report["connections"]["2"]["available_message_sequences"], [1, 2, 3])

    def test_rehashed_attempt_to_resume_after_overflow_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "capture"
            run_scenario(SCENARIOS[10], path)
            original = rows(path / "stream")
            frames = [r for r in original if r["kind"] == "frame"]
            # Identical raw payload makes hash matching alone insufficient. Insert
            # a formerly valid marker after the first unavailable delivery.
            later_delivery = deepcopy(frames[-1]["payload"]["receive_path"]["application_delivery"])
            frames[-1]["payload"]["receive_path"] = deepcopy(frames[24]["payload"]["receive_path"])
            forged = frames[-1]["payload"]["receive_path"]
            forged["application_delivery"] = later_delivery
            marker = forged["receive_marker"]
            marker["message_sequence"] = 26
            marker["first_frame_sequence"] = marker["last_frame_sequence"] = 26
            for field, observation in (("first_observation_to_delivery", "first_receive_observation"),
                                       ("last_observation_to_delivery", "last_receive_observation")):
                forged[field] = elapsed_bounds(marker[observation], later_delivery, later_delivery["clock_domain"])
            forged["telemetry_sha256"] = payload_hash({k: v for k, v in forged.items() if k != "telemetry_sha256"})
            # Individually valid: only connection-wide sticky unavailability
            # rejects it, not a raw hash or elapsed-time calculation mismatch.
            validate_delivery(forged, original[0]["payload"]["receive_path_contract"], frames[-1]["payload"]["raw_text"])
            clock = Clock()
            log = SegmentedStreamLog(Path(root) / "tampered", clock.utc, clock.mono,
                                     original[0]["payload"]["spec"]["storage"])
            for row in original:
                log.append(row["kind"], row["payload"])
            log.close()
            with self.assertRaisesRegex(ContractError, "receive occurrence order mismatch"):
                verify_stream_log(Path(root) / "tampered")
            self.assertEqual(POLICY["max_pending_message_markers"], 64)
