from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.receive_path import (POLICY, ReceivePathTracker, declare, elapsed_bounds,
                                         sample_clock, validate_contract, validate_delivery, validate_stamp)


DOMAIN = "ohio:boot-123"


def stamp(before, after=None):
    return {"schema_version": "qcrl.bracketed_clock.v1", "clock_domain": DOMAIN,
            "utc": "2026-10-07T12:00:00Z", "monotonic_before": before,
            "monotonic_after": before if after is None else after}


def tracker():
    result = ReceivePathTracker(declare("a" * 64, DOMAIN, stream_spec_sha256="b" * 64))
    result.begin_connection(1)
    return result


class ReceivePathTests(unittest.TestCase):
    def test_policy_copy_hash_binding_and_rehashed_tampering(self):
        value = declare("a" * 64, DOMAIN, stream_spec_sha256="b" * 64)
        self.assertEqual(validate_contract(value), value)
        value["policy"]["library_queue_high_water_frames"] = 999
        self.assertEqual(POLICY["library_queue_high_water_frames"], 16)
        value["contract_sha256"] = payload_hash({k: v for k, v in value.items() if k != "contract_sha256"})
        with self.assertRaises(ContractError):
            validate_contract(value)
        for source, domain in (("A" * 64, DOMAIN), ("short", DOMAIN), ("a" * 64, "spaces forbidden")):
            with self.assertRaises(ContractError):
                declare(source, domain, stream_spec_sha256="b" * 64)

    def test_sampling_order_and_naive_clock_rejected(self):
        calls = []
        def mono():
            calls.append("mono")
            return len(calls)
        def clock():
            calls.append("utc")
            return datetime(2026, 10, 7, tzinfo=timezone.utc)
        result = sample_clock(clock, mono, DOMAIN)
        self.assertEqual(calls, ["mono", "utc", "mono"])
        self.assertEqual(result["monotonic_after"] - result["monotonic_before"], 2)
        with self.assertRaises(ContractError):
            sample_clock(lambda: datetime(2026, 10, 7), mono, DOMAIN)

    def test_invalid_monotonic_timezone_and_domains(self):
        for invalid in (True, float("nan"), float("inf"), -1):
            with self.assertRaises(ContractError):
                validate_stamp(stamp(invalid), DOMAIN)
        for changed in ({"monotonic_after": 0}, {"utc": "2026-10-07T12:00:00"},
                        {"clock_domain": "dublin:boot-123"}, {"extra": 1}):
            with self.assertRaises(ContractError):
                validate_stamp({**stamp(1), **changed}, DOMAIN)

    def test_elapsed_brackets_preserve_uncertainty_and_overlap(self):
        result = elapsed_bounds(stamp(1, 1.0001), stamp(2, 2.0002), DOMAIN)
        self.assertAlmostEqual(result["lower_seconds"], .9999)
        self.assertAlmostEqual(result["upper_seconds"], 1.0002)
        self.assertTrue(result["timing_eligible"])
        result = elapsed_bounds(stamp(1, 1.05), stamp(1.04, 1.06), DOMAIN)
        self.assertLess(result["lower_seconds"], 0)
        self.assertIn("wide_clock_bracket", result["warnings"])
        self.assertIn("overlapping_clock_brackets", result["warnings"])
        self.assertFalse(result["timing_eligible"])
        with self.assertRaises(ContractError):
            elapsed_bounds(stamp(2), stamp(1), DOMAIN)

    def test_duplicate_messages_have_distinct_occurrences_not_hash_lookup(self):
        t = tracker()
        for at in (1, 2):
            self.assertTrue(t.observe_frame(1, 1, True, b"same", stamp(at)))
        first = t.deliver(1, "same", stamp(3))
        second = t.deliver(1, "same", stamp(4))
        self.assertEqual(first["receive_marker"]["raw_message_sha256"], second["receive_marker"]["raw_message_sha256"])
        self.assertEqual([r["receive_marker"]["message_sequence"] for r in (first, second)], [1, 2])
        self.assertIsNone(first["library_queue_depth"])
        self.assertIsNone(first["library_backpressure_active"])
        self.assertEqual(first["pending_marker_depth"], 1)
        verify_artifact_hash(first, "telemetry_sha256", "delivery telemetry")

    def test_fragmented_utf8_and_interleaved_protocol_control(self):
        t = tracker()
        raw = "€".encode()
        t.observe_frame(1, 1, False, raw[:1], stamp(1))
        t.observe_frame(1, 9, True, b"ping", stamp(2))
        t.observe_frame(1, 0, True, raw[1:], stamp(3))
        result = t.deliver(1, "€", stamp(4))
        marker = result["receive_marker"]
        self.assertEqual(marker["fragment_count"], 2)
        self.assertEqual(marker["last_frame_sequence"], 3)
        self.assertEqual(marker["raw_message_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["last_observation_to_delivery"]["lower_seconds"], 1)
        self.assertEqual(result["first_observation_to_delivery"]["lower_seconds"], 3)

    def test_binary_and_text_types_are_not_interchangeable(self):
        t = tracker()
        t.observe_frame(1, 2, True, b"abc", stamp(1))
        self.assertTrue(t.deliver(1, b"abc", stamp(2))["telemetry_available"])
        t.observe_frame(1, 2, True, b"abc", stamp(3))
        result = t.deliver(1, "abc", stamp(4))
        self.assertFalse(result["telemetry_available"])
        self.assertEqual(result["unavailable_reason"], "fifo_message_mismatch")

    def test_fifo_mismatch_never_searches_a_later_marker(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"a", stamp(1))
        t.observe_frame(1, 1, True, b"b", stamp(2))
        result = t.deliver(1, "b", stamp(3))
        self.assertFalse(result["telemetry_available"])
        self.assertFalse(t.observe_frame(1, 1, True, b"b", stamp(4)))

    def test_reconnect_discards_pending_and_partial_fragment(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"old", stamp(1))
        t.observe_frame(1, 1, False, b"partial", stamp(2))
        reset = t.begin_connection(2)
        self.assertEqual(reset["discarded_pending_markers"], 1)
        self.assertTrue(reset["discarded_incomplete_fragment"])
        with self.assertRaises(ContractError):
            t.deliver(1, "old", stamp(3))
        t.observe_frame(2, 1, True, b"new", stamp(3))
        result = t.deliver(2, "new", stamp(4))
        self.assertEqual(result["connection"], 2)
        self.assertEqual(result["receive_marker"]["message_sequence"], 1)

    def test_budget_overflow_disables_only_metadata_until_reconnect(self):
        t = tracker()
        with patch.dict(POLICY, {"max_pending_message_markers": 1}):
            t.observe_frame(1, 1, True, b"a", stamp(1))
            self.assertFalse(t.observe_frame(1, 1, True, b"b", stamp(2)))
        result = t.deliver(1, "a", stamp(3))
        self.assertEqual(result["unavailable_reason"], "pending_marker_budget")
        self.assertFalse(result["wire_arrival_measured"])
        self.assertFalse(result["orders_authorized"])
        t.begin_connection(2)
        self.assertIsNone(t.disabled_reason)

    def test_fragment_and_byte_budgets(self):
        for limit in ("max_fragments_per_message", "max_message_bytes"):
            t = tracker()
            with patch.dict(POLICY, {limit: 1}):
                t.observe_frame(1, 1, False, b"a", stamp(1))
                self.assertFalse(t.observe_frame(1, 0, True, b"b", stamp(2)))
            self.assertEqual(t.disabled_reason, "message_telemetry_budget")

    def test_bad_fragment_order_and_regression_are_explicit(self):
        for frames in (((0, True, 1),), ((1, False, 1), (1, True, 2)), ((1, True, 2), (1, True, 1))):
            t = tracker()
            for opcode, final, at in frames:
                t.observe_frame(1, opcode, final, b"a", stamp(at))
            self.assertIsNotNone(t.disabled_reason)

    def test_invalid_delivery_time_does_not_consume_marker(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"a", stamp(2))
        with self.assertRaises(ContractError):
            t.deliver(1, "a", stamp(1))
        self.assertEqual(len(t.pending), 1)
        self.assertTrue(t.deliver(1, "a", stamp(3))["telemetry_available"])

    def test_external_measured_diagnostics_never_inferred_from_marker_depth(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"a", stamp(1))
        result = t.deliver(1, "a", stamp(2), library_queue_depth=17,
                           library_backpressure_active=True, reader_loop_stall_seconds=.5)
        self.assertEqual(result["library_queue_depth"], 17)  # High-water isn't a hard bound.
        self.assertEqual(result["pending_marker_depth"], 0)
        for kw in ({"library_queue_depth": True}, {"library_backpressure_active": 1},
                   {"reader_loop_stall_seconds": float("nan")}):
            with self.assertRaises(ContractError):
                t.deliver(1, "a", stamp(3), **kw)

    def test_input_stamps_and_contract_do_not_alias_stored_markers(self):
        contract = declare("a" * 64, DOMAIN, stream_spec_sha256="b" * 64)
        t = ReceivePathTracker(contract)
        t.begin_connection(1)
        original = stamp(1)
        t.observe_frame(1, 1, True, b"a", original)
        original["utc"] = "changed"
        contract["policy"]["max_message_bytes"] = 1
        result = t.deliver(1, "a", stamp(2))
        self.assertEqual(result["receive_marker"]["first_receive_observation"]["utc"], stamp(1)["utc"])
        self.assertEqual(t.contract["policy"]["max_message_bytes"], 262144)

    def test_archived_delivery_validator_rejects_rehashed_semantic_tampering(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"a", stamp(1))
        original = t.deliver(1, "a", stamp(2))
        self.assertEqual(validate_delivery(original, t.contract, "a"), original)
        changes = [{"orders_authorized": True}, {"connection": True},
                   {"contract_sha256": "b" * 64}, {"telemetry_available": False},
                   {"last_observation_to_delivery": {"lower_seconds": 0}},
                   {"library_queue_depth": True}, {"undocumented_latency_claim": True}]
        for change in changes:
            changed = {**deepcopy(original), **change}
            changed["telemetry_sha256"] = payload_hash({k: v for k, v in changed.items() if k != "telemetry_sha256"})
            with self.assertRaises(ContractError):
                validate_delivery(changed, t.contract, "a")
        with self.assertRaises(ContractError):
            validate_delivery(original, t.contract, "different")

    def test_fragmented_and_unknown_delivery_validate_without_invented_timing(self):
        t = tracker()
        t.observe_frame(1, 1, False, b"a", stamp(1))
        t.observe_frame(1, 0, True, b"b", stamp(2))
        result = t.deliver(1, "ab", stamp(3))
        validate_delivery(result, t.contract, "ab")
        missing = t.deliver(1, "unobserved", stamp(4))
        self.assertNotIn("last_observation_to_delivery", missing)
        validate_delivery(missing, t.contract, "unobserved")

    def test_parallel_market_specs_cannot_share_delivery_binding(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"a", stamp(1))
        result = t.deliver(1, "a", stamp(2))
        other = declare("a" * 64, DOMAIN, stream_spec_sha256="c" * 64)
        with self.assertRaisesRegex(ContractError, "binding"):
            validate_delivery(result, other, "a")

    def test_reconnect_does_not_hide_same_boot_monotonic_regression(self):
        t = tracker()
        t.observe_frame(1, 1, True, b"a", stamp(5))
        t.deliver(1, "a", stamp(6))
        t.begin_connection(2)
        self.assertFalse(t.observe_frame(2, 1, True, b"b", stamp(4)))
        self.assertEqual(t.disabled_reason, "receiver_monotonic_regression")
        with self.assertRaises(ContractError):
            t.deliver(2, "b", stamp(5))


if __name__ == "__main__":
    unittest.main()
