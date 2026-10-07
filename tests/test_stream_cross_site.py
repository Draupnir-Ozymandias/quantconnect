from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_cross_site import (POLICY, _load_site, analyze_cohort, compare_events,
                                              resource_summary, scan_rows, scan_stream)
from execution_truth.stream_segments import SegmentedStreamLog
from test_stream_freshness import BASE, SPEC, frame, header


def socket_frame(seconds):
    value = frame(seconds, BASE * 1000)
    value["payload"]["socket_received_at_utc"] = value["received_at_utc"]
    value["payload"]["socket_received_monotonic_seconds"] = seconds
    return value


class CrossSiteTests(unittest.TestCase):
    def test_positive_delta_means_right_earlier(self):
        result = compare_events({"a": [1.1], "b": [2.1], "c": [3.1]},
                                {"a": [1.0], "b": [2.0], "c": [3.0]})
        self.assertEqual(result["unique_in_both_entire_streams_payload_matches"], 1)
        self.assertEqual(result["left_minus_right_socket_receipt_seconds"]["p50_seconds"], .1)
        self.assertFalse(result["one_way_network_latency_proven"])

    def test_duplicates_outside_overlap_still_excluded(self):
        result = compare_events({"a": [0, 2], "b": [3], "c": [4]},
                                {"a": [2], "b": [3], "c": [4]})
        self.assertEqual(result["duplicate_shared_fingerprints_excluded_from_timing"], 1)
        self.assertEqual(result["unique_in_both_entire_streams_payload_matches"], 2)
        self.assertEqual(result["multiplicity_matched_events"], 3)
        self.assertEqual(result["events_outside_interval"]["left"], 1)

    def test_unmatched_is_not_loss_and_no_overlap_is_explicit(self):
        result = compare_events({"a": [1], "extra": [2], "b": [3]}, {"a": [1], "b": [3]})
        self.assertEqual(result["unmatched_event_occurrences"]["left"], 1)
        self.assertTrue(result["unmatched_does_not_prove_message_loss"])
        self.assertEqual(compare_events({}, {"a": [1]})["reason"], "no_selected_events")
        self.assertEqual(compare_events({"a": [1]}, {"a": [2]})["reason"], "no_common_receipt_interval")

    def test_unknown_or_reset_resource_counters_not_zero(self):
        self.assertIsNone(resource_summary([])["cgroup_counter_change"]["nr_periods"])
        values = [{"resources": {"cgroup_cpu_stat": {"nr_periods": n}}} for n in (10, 5, 20)]
        self.assertIsNone(resource_summary(values)["cgroup_counter_change"]["nr_periods"])
        values = [{"resources": {"cgroup_cpu_stat": {"nr_periods": n}}} for n in (10, 20)]
        self.assertEqual(resource_summary(values)["cgroup_counter_change"]["nr_periods"], 10)
        self.assertIsNone(resource_summary(values)["cgroup_counter_change"]["nr_throttled"])

    def test_socket_not_postclassification_receipt_and_no_mutation(self):
        value = socket_frame(1)
        value["received_at_utc"] = datetime.fromtimestamp(BASE + 2, timezone.utc).isoformat()
        value["local_monotonic_seconds"] = 2
        original = deepcopy(value)
        summary, events = scan_rows([header(), value])
        self.assertEqual(summary["socket_receipt_age"]["p50_seconds"], 1)
        self.assertEqual(value, original)
        self.assertEqual(sum(map(len, events.values())), 1)

    def test_missing_nonfinite_and_backwards_socket_timestamps_rejected(self):
        value = frame(1, BASE * 1000)
        with self.assertRaises(ContractError):
            scan_rows([header(), value])
        for mono in (True, float("nan"), float("inf")):
            value = socket_frame(1)
            value["payload"]["socket_received_monotonic_seconds"] = mono
            with self.assertRaises(ContractError):
                scan_rows([header(), value])
        with self.assertRaises(ContractError):
            scan_rows([header(), socket_frame(2), socket_frame(1)])

    def test_budget_and_classification_mismatch_rejected(self):
        with patch.dict(POLICY, {"max_selected_events_per_stream": 1}):
            with self.assertRaises(ContractError):
                scan_rows([header(), socket_frame(1), socket_frame(2)])
        value = socket_frame(1)
        value["payload"]["classification"] = []
        with self.assertRaises(ContractError):
            scan_rows([header(), value])

    def test_heartbeat_and_unparsed_frames_are_preserved(self):
        values = []
        for text in ("PONG", "not-json"):
            value = socket_frame(len(values) + 1)
            value["payload"]["raw_text"] = text
            values.append(value)
        summary, events = scan_rows([header(), *values])
        self.assertEqual(summary["counts"]["heartbeat_frames"], 1)
        self.assertEqual(summary["counts"]["unparsed_frames"], 1)
        self.assertEqual(events, {})

    def test_cohort_comparability_and_partial_cases(self):
        plan = {"plan_sha256": "p", "market_starts": [BASE]}
        def site(identity):
            return (plan, {"health": {"healthy": False, "cases": []}, "cases": {},
                "preflight": {"instance_id": identity, "source_commit": "same",
                    "systemd_unit_sha256": "same", "systemd_resource_settings": "same",
                    "common_input_file_sha256": "same"}})
        with tempfile.TemporaryDirectory() as tmp:
            with patch("execution_truth.stream_cross_site._load_site", side_effect=[site("a"), site("b")]):
                result = analyze_cohort(Path(tmp) / "a", Path(tmp) / "b")
            self.assertFalse(result["comparisons"][0]["eligible"])
            self.assertFalse(result["sites"]["left"]["health"]["healthy"])
            self.assertEqual(result["report_sha256"], payload_hash({k: v for k, v in result.items()
                                                                  if k != "report_sha256"}))
            changed = site("b")
            changed[1]["preflight"]["source_commit"] = "different"
            with patch("execution_truth.stream_cross_site._load_site", side_effect=[site("a"), changed]):
                with self.assertRaisesRegex(ContractError, "site policy"):
                    analyze_cohort(tmp, tmp)

    def test_finalized_partial_is_descriptive_and_identity_mismatch_fails(self):
        plan = {"plan_sha256": "p", "market_starts": [BASE]}
        spec = {**SPEC, "event_start_at_utc": "start", "event_end_at_utc": "end"}
        def site(identity):
            return (plan, {"health": {"healthy": False,
                "cases": [{"market_start": BASE, "lifecycle_completed": False}]}, "cases": {},
                "preflight": {"instance_id": identity, "source_commit": "same",
                    "systemd_unit_sha256": "same", "systemd_resource_settings": "same",
                    "common_input_file_sha256": "same"}})
        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp) / side for side in ("left", "right")]
            def write_cases(specs):
                for root, value in zip(roots, specs):
                    directory = root / str(BASE)
                    (directory / "stream").mkdir(parents=True, exist_ok=True)
                    (directory / "stream/manifest.json").write_text("{}")
                    (directory / "market-1.json").write_text(json.dumps({"bundle_sha256": "raw"}))
                    result = {"verification": {"header_spec": value}, "raw_bundle_sha256": "raw"}
                    result["result_sha256"] = payload_hash(result)
                    (directory / "result.json").write_text(json.dumps(result))
            def run(specs):
                scans = [({"source": {}}, {"a": [1]}, {"header_spec": value}) for value in specs]
                with patch("execution_truth.stream_cross_site._load_site", side_effect=[site("a"), site("b")]), \
                        patch("execution_truth.stream_cross_site.scan_stream", side_effect=scans), \
                        patch("execution_truth.stream_cross_site.check_market", side_effect=specs):
                    return analyze_cohort(*roots)
            write_cases([spec, spec])
            result = run([spec, spec])
            self.assertTrue(result["comparisons"][0]["eligible"])
            self.assertFalse(result["sites"]["left"]["cases"][str(BASE)]["lifecycle_completed"])
            changed = {**spec, "condition_id": "different"}
            write_cases([spec, changed])
            with self.assertRaisesRegex(ContractError, "market binding"):
                run([spec, changed])
            write_cases([spec, spec])
            (roots[0] / str(BASE) / "market-1.json").write_text(json.dumps({"bundle_sha256": "tampered"}))
            with self.assertRaisesRegex(ContractError, "pinned source/result"):
                run([spec, spec])
            with patch("execution_truth.stream_cross_site._load_site", side_effect=[site("a"), site("a")]):
                with self.assertRaisesRegex(ContractError, "distinct observers"):
                    analyze_cohort(tmp, tmp)

    def test_verified_stream_provenance_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            seconds = [0]
            log = SegmentedStreamLog(root,
                lambda: datetime.fromtimestamp(BASE + seconds[0], timezone.utc),
                lambda: seconds[0], {"segment_uncompressed_bytes": 1500,
                    "max_uncompressed_bytes": 100000, "max_compressed_bytes": 8 * 1024**2})
            log.append("session_start", header()["payload"])
            seconds[0] = 1
            log.append("frame", socket_frame(1)["payload"])
            seconds[0] = 2
            log.append("session_end", {"status": "lifecycle_stop"})
            log.close()
            summary, events, verified = scan_stream(root)
            self.assertEqual(summary["source"]["final_record_sha256"], verified["final_record_sha256"])
            self.assertEqual(sum(map(len, events.values())), 1)
            segment = next(root.glob("*.gz"))
            segment.write_bytes(segment.read_bytes() + b"corrupt")
            with self.assertRaises(ContractError):
                scan_stream(root)

    def test_preflight_wrong_plan_and_stored_health_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = {"plan_sha256": "p"}
            health = {"healthy": False}
            health["health_sha256"] = payload_hash(health)
            preflight = {"schema_version": "qcrl.observer_preflight.v1", "plan_sha256": "wrong",
                         "orders_authorized": False}
            preflight["preflight_sha256"] = payload_hash(preflight)
            for name, value in (("pilot", plan), ("health", health), ("observer_preflight", preflight)):
                (root / (name + ".json")).write_text(json.dumps(value))
            with patch("execution_truth.stream_cross_site.validate_plan", return_value=plan), \
                    patch("execution_truth.stream_cross_site.cohort_health", return_value=health):
                with self.assertRaisesRegex(ContractError, "preflight"):
                    _load_site(root)
            with patch("execution_truth.stream_cross_site.validate_plan", return_value=plan), \
                    patch("execution_truth.stream_cross_site.cohort_health", return_value={}):
                with self.assertRaisesRegex(ContractError, "cohort verification"):
                    _load_site(root)


if __name__ == "__main__":
    unittest.main()
