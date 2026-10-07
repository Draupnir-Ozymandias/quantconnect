from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.bundle import store_raw_bundle
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import collect_market_stream, verify_stream_log, StreamTransportError
from execution_truth.receive_path import elapsed_bounds, policy_for, sample_clock
from execution_truth.rolling_stream import DESCRIPTION, SOURCE, check_market, persist, pilot_plan
from execution_truth.stream_receive_analysis import POLICY, _sealed_rows, analyze_capture, analyze_rows
from execution_truth.stream_segments import SegmentedStreamLog
from execution_truth.stream_profiling import POLICY as PROFILE_POLICY
from tests.receive_burst_fixture import SCENARIOS, run_scenario
from tests.test_market_stream import Clock, Socket, book
from tests.test_receive_capture import rows
from tests.test_taker_replay import raw_bundle


def _source_bundle(start):
    bundle = raw_bundle()
    gamma = bundle["observations"]["gamma_market"]
    gamma["payload"].update(slug="btc-updown-5m-" + str(start), question="Bitcoin Up or Down - May 4",
                            description=DESCRIPTION, resolutionSource=SOURCE)
    gamma["payload_sha256"] = payload_hash(gamma["payload"])
    bundle["bundle_sha256"] = payload_hash({k: v for k, v in bundle.items() if k != "bundle_sha256"})
    return bundle


def public_capture(root, *, pilot=False):
    clock = Clock()
    start = int(clock.base.timestamp())
    if pilot:
        declaration = pilot_plan(start, 1, now=clock.utc() - timedelta(seconds=120), profiling=True,
                                 deferred=True, receive_path=True, receive_policy="v2")
        persist(root / "pilot.json", declaration)
        root = root / str(start)
    else:
        declaration = {"schema_version": "qcrl.receive_path_smoke_declaration.v1", "market_start": start,
                       "max_seconds": 35, "resolution_source": SOURCE, "description_sha256": payload_hash(DESCRIPTION),
                       "receive_path": policy_for("v2"), "profiling": deepcopy(PROFILE_POLICY), "orders_authorized": False}
        declaration["plan_sha256"] = payload_hash(declaration)
        persist(root / "declaration.json", declaration)
    bundle = _source_bundle(start)
    store_raw_bundle(bundle, root)
    spec = check_market(bundle, start, declaration)
    if not pilot:
        spec["max_seconds"] = 35

    def connector(tracker, number, **kwargs):
        messages = [json.dumps(book(spec, asset)) for asset in spec["asset_ids"]] + ["PONG"]
        if not pilot and number == 1:
            messages += [StreamTransportError("ConnectionClosedError:rcvd_code=1013:sent_code=1013")]
        class Observed(Socket):
            def recv(self, timeout):
                if pilot and not self.frames:
                    self.frames.append("PONG")
                message = super().recv(timeout)
                tracker.observe_frame(number, 1, True, message.encode(), sample_clock(clock.utc, clock.mono, tracker.domain))
                return message, tracker.deliver(number, message, sample_clock(clock.utc, clock.mono, tracker.domain))
        socket = Observed(clock, messages)
        socket.reset = tracker.begin_connection(number)
        return socket
    summary = collect_market_stream(bundle, spec, root / "stream", connector=connector, clock=clock.utc,
                                    monotonic=clock.mono, pause=clock.pause, clock_domain="fixture.analysis")
    verified = verify_stream_log(root / "stream")
    if pilot:
        capture = {"market_start": start, "raw_bundle_sha256": bundle["bundle_sha256"], "stream_summary": summary,
                   "status": "observed_" + summary["status"], "orders_authorized": False}
        capture["result_sha256"] = payload_hash(capture)
        persist(root / "capture_result.json", capture)
        result = {**capture, "capture_result_sha256": capture["result_sha256"], "verification": verified}
        result["result_sha256"] = payload_hash({k: v for k, v in result.items() if k != "result_sha256"})
        persist(root / "result.json", result)
    else:
        result = {"passed": False, "summary": summary, "verification": verified}
        result["report_sha256"] = payload_hash(result)
        persist(root / "smoke-report.json", result)
    return root


def rewrite_fixture(root, mutate):
    records = rows(root / "stream")
    mutate(records)
    (root / "stream").rename(root / "original-stream")
    clock = Clock()
    log = SegmentedStreamLog(root / "stream", clock.utc, clock.mono, records[0]["payload"]["spec"]["storage"])
    for record in records:
        clock.seconds = max(clock.seconds, record["local_monotonic_seconds"])
        log.append(record["kind"], record["payload"])
    log.close()
    result = json.loads((root / "report.json").read_text())
    result["verification"] = verify_stream_log(root / "stream")
    result["report_sha256"] = payload_hash({k: v for k, v in result.items() if k != "report_sha256"})
    (root / "report.json").write_text(json.dumps(result))


class ReceiveAnalysisTests(unittest.TestCase):
    def test_v1_v2_matrix_phases_denominators_and_saturation(self):
        for version in ("v1", "v2"):
            available = total = 0
            for scenario in SCENARIOS:
                with self.subTest(version=version, scenario=scenario["name"]), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory) / "capture"
                    source = run_scenario(scenario, root, receive_policy=version)
                    result = analyze_capture(root)
                    verify_artifact_hash(result, "analysis_sha256", "analysis")
                    self.assertEqual(result["total"]["available"], source["verification"]["receive_path_verification"]["available"])
                    self.assertEqual(sum(p["messages"] for p in result["phases"].values()), result["total"]["messages"])
                    self.assertEqual(result["source"]["raw_bundle_verification"], "not_available_in_synthetic_evidence")
                    self.assertEqual(result["total"]["tail_population_is_censored"], result["total"]["unknown"] > 0)
                    if scenario["name"] == "prefix25-then65":
                        self.assertEqual(result["phases"]["normal"]["messages"], 25)
                        self.assertEqual(result["phases"]["draining"]["messages"], 64 if version == "v2" else 0)
                        self.assertEqual(result["phases"]["unknown"]["messages"], 1 if version == "v2" else 65)
                    available += result["total"]["available"]
                    total += result["total"]["messages"]
            self.assertEqual((total, available), (1208, 283 if version == "v1" else 731))

    def test_public_failed_acceptance_and_fresh_books_recovery_remain_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = public_capture(Path(directory))
            result = analyze_capture(root)
            self.assertFalse(result["source"]["source_acceptance_passed"])
            self.assertTrue(result["artifact_verification_complete"])
            self.assertTrue(result["full_locally_eligible_timing_coverage"])
            self.assertFalse(result["transport_gap_free"])
            self.assertTrue(result["gaps"][0]["recovered_book_baselines"])
            self.assertEqual(result["gaps"][0]["both_token_books"]["gap_log_to_delivery_lower_seconds"], 4)
            self.assertEqual(len(result["connections"]["2"]["initial_book_observations"]), 2)
            self.assertFalse(result["continuous_coverage_proven"])

    def test_cohort_requires_explicit_root_and_immutable_capture_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            pilot = Path(directory)
            root = public_capture(pilot, pilot=True)
            result = analyze_capture(root, pilot_root=pilot)
            self.assertEqual(result["source"]["role"], "locked_pilot_window_not_cohort_verdict")
            capture = json.loads((root / "capture_result.json").read_text())
            capture["status"] = "changed"
            capture["result_sha256"] = payload_hash({k: v for k, v in capture.items() if k != "result_sha256"})
            (root / "capture_result.json").write_text(json.dumps(capture))
            with self.assertRaisesRegex(ContractError, "immutable capture"):
                analyze_capture(root, pilot_root=pilot)

    def test_ineligible_clock_bounds_are_not_in_conditional_percentiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario({"name": "clock", "payload_bytes": 543, "connections": [{"burst": 3}]}, root, receive_policy="v2")
            def mutate(records):
                frame = [r for r in records if r["kind"] == "frame"][-1]
                record = frame["payload"]["receive_path"]
                record["application_delivery"]["monotonic_after"] += .002
                frame["local_monotonic_seconds"] = record["application_delivery"]["monotonic_after"]
                for field, source in (("first_observation_to_delivery", "first_receive_observation"),
                                      ("last_observation_to_delivery", "last_receive_observation")):
                    record[field] = elapsed_bounds(record["receive_marker"][source], record["application_delivery"], record["application_delivery"]["clock_domain"])
                record["telemetry_sha256"] = payload_hash({k: v for k, v in record.items() if k != "telemetry_sha256"})
            rewrite_fixture(root, mutate)
            result = analyze_capture(root)
            self.assertEqual(result["total"]["available_but_timing_ineligible"], 1)
            self.assertEqual(result["total"]["conditional_callback_to_delivery_upper"]["count"], 2)
            self.assertEqual(result["total"]["coverage_denominator"], 3)
            self.assertTrue(result["total"]["tail_population_is_censored"])

    def test_adapter_failure_has_unknown_delivery_time_not_old_socket_substitution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario({"name": "failure", "payload_bytes": 543, "connections": [{"burst": 3}]}, root, receive_policy="v2")
            def mutate(records):
                frames = [r for r in records if r["kind"] == "frame"]
                first = frames[0]["payload"]
                failure = {"schema_version": "qcrl.receive_adapter_failure.v1", "contract_sha256": first["receive_path"]["contract_sha256"],
                    "connection": 1, "raw_message_sha256": hashlib.sha256(first["raw_text"].encode()).hexdigest(),
                    "unavailable_reason": "application_telemetry_error", "error_type": "RuntimeError",
                    "wire_arrival_measured": False, "orders_authorized": False}
                failure["telemetry_sha256"] = payload_hash(failure)
                first["receive_path"] = failure
                first["socket_received_monotonic_seconds"] = 999999
                for row in frames[1:]:
                    record = row["payload"]["receive_path"]
                    record.update(receive_marker=None, telemetry_available=False, unavailable_reason="application_telemetry_error", pending_marker_depth=0)
                    record.pop("first_observation_to_delivery")
                    record.pop("last_observation_to_delivery")
                    record["telemetry_sha256"] = payload_hash({k: v for k, v in record.items() if k != "telemetry_sha256"})
            rewrite_fixture(root, mutate)
            result = analyze_capture(root)
            self.assertEqual(result["total"]["unknown"], 3)
            self.assertEqual(result["total"]["delivery_stamp_missing"], 1)
            self.assertEqual(result["total"]["conditional_callback_to_delivery_upper"], {"count": 0})

    def test_consecutive_failed_attempts_remain_unrecovered_and_unpooled(self):
        header = {"kind": "session_start", "payload": {}, "ordinal": 0, "received_at_utc": Clock().utc().isoformat(), "local_monotonic_seconds": 0}
        records = [header]
        for connection in (1, 2):
            for kind, payload in (("connect_attempt", {"connection": connection}), ("connection_gap", {"connection": connection, "reason": "fixture"})):
                records.append({**header, "ordinal": len(records), "kind": kind, "payload": payload, "local_monotonic_seconds": len(records)})
        result = analyze_rows(records, {"max_connections": 3, "asset_ids": ["a", "b"]}, {"clock_domain": "fixture"})
        self.assertEqual(len(result["gaps"]), 2)
        self.assertTrue(all(gap["both_token_books"] is None for gap in result["gaps"]))
        self.assertEqual(result["total"]["timing_coverage_fraction"], None)
        self.assertIsNone(result["resources"]["cgroup_counter_change"]["throttled_usec"])

    def test_partial_publication_and_bad_provenance_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario(SCENARIOS[0], root, receive_policy="v2")
            actual = verify_stream_log(root / "stream")
            with patch("execution_truth.stream_receive_analysis.verify_stream_log", return_value={**actual, "session_end_present": False}):
                with self.assertRaises(ContractError):
                    analyze_capture(root)
            declaration = json.loads((root / "declaration.json").read_text())
            declaration["name"] = "different"
            declaration["plan_sha256"] = payload_hash({k: v for k, v in declaration.items() if k != "plan_sha256"})
            (root / "declaration.json").write_text(json.dumps(declaration))
            with self.assertRaisesRegex(ContractError, "does not bind"):
                analyze_capture(root)

    def test_budget_and_outer_clock_regression_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario(SCENARIOS[1], root, receive_policy="v2")
            with patch.dict(POLICY, {"max_messages": 1}):
                with self.assertRaisesRegex(ContractError, "message budget"):
                    analyze_capture(root)
            def mutate(records):
                records[-1]["local_monotonic_seconds"] = -1
            rewrite_fixture(root, mutate)
            # Rewriter uses a monotonic fake clock; exercise scan regression explicitly.
            records = rows(root / "stream")
            records[-1]["local_monotonic_seconds"] = -1
            with self.assertRaises(ContractError):
                analyze_rows(records, records[0]["payload"]["spec"], records[0]["payload"]["receive_path_contract"])

    def test_cli_preserves_sources_and_refuses_output_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario(SCENARIOS[3], root, receive_policy="v2")
            before = {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            output = Path(directory) / "analysis.json"
            command = [sys.executable, "-m", "execution_truth.stream_receive_analysis", str(root), "--output", str(output)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            contents = output.read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), contents)
            self.assertEqual(before, {str(p): p.read_bytes() for p in root.rglob("*") if p.is_file()})

    def test_wall_clock_jump_is_reported_without_correcting_elapsed_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario({"name": "wall", "payload_bytes": 543, "connections": [{"burst": 3}]}, root, receive_policy="v2")
            original = analyze_capture(root)
            def mutate(records):
                record = [row for row in records if row["kind"] == "frame"][-1]["payload"]["receive_path"]
                record["application_delivery"]["utc"] = (Clock().base - timedelta(seconds=10)).isoformat()
                record["telemetry_sha256"] = payload_hash({k: v for k, v in record.items() if k != "telemetry_sha256"})
            rewrite_fixture(root, mutate)
            result = analyze_capture(root)
            self.assertEqual(result["clock"]["application_utc_regressions"], 1)
            self.assertGreaterEqual(result["clock"]["max_application_wall_minus_monotonic_interval_separation_seconds"], 10)
            self.assertFalse(result["clock"]["clock_correction_applied"])
            self.assertEqual(result["total"]["conditional_callback_to_delivery_upper"], original["total"]["conditional_callback_to_delivery_upper"])

    def test_second_scan_rejects_rehashed_replacement_after_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "capture"
            run_scenario(SCENARIOS[0], root, receive_policy="v2")
            anchor = verify_stream_log(root / "stream")
            def mutate(records):
                records[-1]["payload"]["status"] = "fake_limits"  # Same byte length as frame_limit.
            rewrite_fixture(root, mutate)
            self.assertEqual(verify_stream_log(root / "stream")["uncompressed_bytes"], anchor["uncompressed_bytes"])
            with self.assertRaisesRegex(ContractError, "verified stream anchor"):
                list(_sealed_rows(root / "stream", anchor))

    def test_books_from_failed_connections_are_not_combined_for_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = public_capture(Path(directory))
            records = rows(root / "stream")
            frames = [r for r in records if r["kind"] == "frame" and r["payload"]["connection"] == 2]
            # Internal scan of a controlled fixture: omit the second token's book.
            removed = frames[1]["ordinal"]
            records = [r for r in records if r["ordinal"] != removed]
            result = analyze_rows(records, records[0]["payload"]["spec"], records[0]["payload"]["receive_path_contract"])
            self.assertIsNotNone(result["gaps"][0]["first_selected_message"])
            self.assertIsNone(result["gaps"][0]["both_token_books"])
            self.assertFalse(result["gaps"][0]["recovered_book_baselines"])
