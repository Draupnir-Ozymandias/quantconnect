import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log
from execution_truth.stream_segments import SegmentedStreamLog, StreamQuotaError, verify_segments
from execution_truth.rolling_stream import cohort_health, pilot_plan, persist
from tests.test_market_stream import Clock, Socket
from tests.test_taker_replay import raw_bundle


class SegmentTests(unittest.TestCase):
    def make_log(self, root, **updates):
        clock = Clock()
        policy = {"segment_uncompressed_bytes": 1500, "max_uncompressed_bytes": 100000,
                  "max_compressed_bytes": 8 * 1024**2}
        policy.update(updates)
        log = SegmentedStreamLog(root, clock.utc, clock.mono, policy)
        log.append("session_start", {"spec": {}, "spec_sha256": payload_hash({})})
        return log

    def populate(self, root):
        log = self.make_log(root)
        for i in range(20):
            log.append("frame", {"raw_text": "sample" * 50, "index": i})
        log.append("session_end", {"status": "lifecycle_stop"})
        log.close()
        return verify_stream_log(root)

    def test_rotates_compresses_and_verifies_global_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            checked = self.populate(root)
            self.assertGreater(checked["segments"], 1)
            self.assertEqual(checked["records"], 22)
            self.assertTrue(checked["session_end_present"])
            self.assertTrue(checked["manifest_present"])
            self.assertLess(checked["compressed_bytes"], checked["uncompressed_bytes"])
            self.assertFalse(list(root.glob("*.partial")))
            with self.assertRaises(FileExistsError):
                self.make_log(root)

    def test_missing_footer_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            log = self.make_log(root)
            log.append("frame", {})
            log.close()
            self.assertFalse(verify_segments(root)["session_end_present"])

    def test_crash_prefix_has_no_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            log = self.make_log(root)
            log._seal()
            log._open()
            log.append("frame", {})
            log.writer.close()
            log.raw.close()
            checked = verify_segments(root)
            self.assertFalse(checked["manifest_present"])
            self.assertFalse(checked["session_end_present"])
            self.assertEqual(checked["records"], 1)

    def test_changed_compressed_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            self.populate(root)
            path = next(root.glob("*.gz"))
            data = bytearray(path.read_bytes())
            data[15] ^= 1
            path.write_bytes(data)
            with self.assertRaises(ContractError):
                verify_segments(root)

    def test_missing_segment_and_changed_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            self.populate(root)
            path = root / "manifest.json"
            manifest = json.loads(path.read_text())
            manifest["records"] += 1
            manifest["manifest_sha256"] = payload_hash({k: v for k, v in manifest.items() if k != "manifest_sha256"})
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ContractError):
                verify_segments(root)
            (root / "segment-000000.json").unlink()
            with self.assertRaises(ContractError):
                verify_segments(root)

    def test_quota_retains_room_for_terminal_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            log = self.make_log(root, max_uncompressed_bytes=1000)
            with self.assertRaises(StreamQuotaError):
                log.append("frame", {"raw_text": "x" * 2000})
            log.append("session_end", {"status": "storage_limit"})
            log.close()
            self.assertTrue(verify_segments(root)["session_end_present"])

    def test_real_collector_uses_segmented_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw, clock = raw_bundle(), Clock()
            spec = stream_plan(raw, segmented=True, max_seconds=4, max_frames=1000000)
            root = Path(tmp) / "stream"
            socket = Socket(clock, ["PONG", "PONG"])
            summary = collect_market_stream(raw, spec, root, connector=lambda: socket,
                                            clock=clock.utc, monotonic=clock.mono, pause=clock.pause)
            self.assertEqual(summary["status"], "duration_limit")
            self.assertTrue(verify_stream_log(root)["session_end_present"])

    def test_all_failed_cases_never_report_healthy(self):
        clock = Clock()
        from datetime import timedelta
        plan = pilot_plan(int(clock.base.timestamp()), 2, now=clock.base - timedelta(seconds=60))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for start in plan["market_starts"]:
                result = {"status": "failed", "market_start": start}
                result["result_sha256"] = payload_hash(result)
                persist(root / str(start) / "result.json", result)
            report = cohort_health(plan, root)
            self.assertFalse(report["healthy"])
            self.assertEqual(report["completed"], 0)
            self.assertEqual(len(report["problems"]), 2)

    def test_missing_results_unhealthy(self):
        from datetime import timedelta
        clock = Clock()
        plan = pilot_plan(int(clock.base.timestamp()), 1, now=clock.base - timedelta(seconds=60))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(cohort_health(plan, tmp)["healthy"])

    def test_zero_cli_frame_limit_is_not_replaced_with_default(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_text(json.dumps(raw_bundle()))
            result = subprocess.run([sys.executable, "qcrl_execution_truth.py", "market-stream", str(path),
                                     "--segmented", "--max-frames", "0"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_service_exits_nonzero_when_cohort_is_unhealthy(self):
        import os
        from datetime import timedelta
        from infra.stream import service
        clock = Clock()
        plan = pilot_plan(int(clock.base.timestamp()), 1, now=clock.base - timedelta(seconds=60))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            persist(path, plan)
            env = {"QCRL_STREAM_PLAN": str(path), "QCRL_STREAM_ROOT": "/var/lib/qcrl-stream/pilot-test",
                   "QCRL_STREAM_BUCKET": "test-bucket", "AWS_DEFAULT_REGION": "us-east-2"}
            with patch.dict(os.environ, env), patch("infra.stream.service.run_pilot", return_value={"healthy": False}), patch("infra.stream.service.upload") as upload, patch("execution_truth.rolling_stream.persist"):
                with self.assertRaises(SystemExit) as failure:
                    service.main()
                self.assertEqual(failure.exception.code, 1)
                upload.assert_called_once()

    def test_final_and_true_postclose_checkpoint_survive_reader_failure(self):
        from execution_truth.rolling_stream import observe_window
        clock, raw = Clock(), raw_bundle()
        start = int(clock.base.timestamp())
        from datetime import timedelta
        plan = pilot_plan(start, 1, now=clock.base - timedelta(seconds=60))
        checkpoint_times = []
        class Acquirer:
            def __init__(self, *args):
                pass
            def resolve_market_slug(self, *args):
                return {"resolved_market_id": "123456"}
            def acquire_market_bundle(self, *args):
                return raw
            def acquire_market_settlement(self, *args):
                checkpoint_times.append(clock.utc().timestamp())
                return {}
        with tempfile.TemporaryDirectory() as tmp, patch("execution_truth.rolling_stream.PublicPolymarketAcquirer", Acquirer), patch("execution_truth.rolling_stream.utc_now", clock.utc), patch("execution_truth.rolling_stream.time.sleep", clock.pause), patch("execution_truth.rolling_stream.store_raw_slug_resolution"), patch("execution_truth.rolling_stream.store_raw_settlement", side_effect=lambda a, d: Path(d) / ("checkpoint-%d.json" % len(checkpoint_times))), patch("execution_truth.rolling_stream.check_market", return_value=stream_plan(raw, segmented=True, max_frames=1000000)), patch("execution_truth.rolling_stream.collect_market_stream", side_effect=ContractError("simulated storage failure")):
            observe_window(start, plan, Path(tmp))
            result = json.loads((Path(tmp) / str(start) / "result.json").read_text())
            self.assertEqual(result["status"], "failed")
            self.assertEqual([c["label"] for c in result["metadata_checkpoints"]], ["final", "postclose_120s"])
            self.assertGreaterEqual(checkpoint_times[-1], start + 420)

    def test_collector_storage_quota_writes_footer(self):
        clock, raw = Clock(), raw_bundle()
        class LimitedLog(SegmentedStreamLog):
            def __init__(self, path, clock, mono, policy):
                policy = dict(policy, max_uncompressed_bytes=6000)
                super().__init__(path, clock, mono, policy)
        with tempfile.TemporaryDirectory() as tmp, patch("execution_truth.market_stream.SegmentedStreamLog", LimitedLog):
            root = Path(tmp) / "stream"
            spec = stream_plan(raw, segmented=True, max_seconds=5)
            socket = Socket(clock, ["x" * 6000])
            summary = collect_market_stream(raw, spec, root, connector=lambda: socket,
                                            clock=clock.utc, monotonic=clock.mono, pause=clock.pause)
            self.assertEqual(summary["status"], "storage_limit")
            self.assertTrue(verify_segments(root)["session_end_present"])

    def test_verified_full_lifecycle_can_report_healthy(self):
        from datetime import timedelta
        from execution_truth.rolling_stream import DESCRIPTION, SOURCE
        from execution_truth.bundle import store_raw_bundle, store_raw_settlement
        clock, raw = Clock(), raw_bundle()
        start = int(clock.base.timestamp())
        plan = pilot_plan(start, 1, now=clock.base - timedelta(seconds=60))
        gamma = raw["observations"]["gamma_market"]
        gamma["payload"].update(slug="btc-updown-5m-" + str(start), question="Bitcoin Up or Down - May 4",
                                description=DESCRIPTION, resolutionSource=SOURCE)
        gamma["payload_sha256"] = payload_hash(gamma["payload"])
        raw["bundle_sha256"] = payload_hash({k: v for k, v in raw.items() if k != "bundle_sha256"})
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / str(start)
            store_raw_bundle(raw, directory)
            spec = stream_plan(raw, max_frames=1000000, segmented=True)
            log = SegmentedStreamLog(directory / "stream", clock.utc, clock.mono, spec["storage"])
            log.append("session_start", {"spec": spec, "spec_sha256": payload_hash(spec)})
            from execution_truth.market_stream import classify_frame
            wire = json.dumps([{"event_type": "book", "market": spec["condition_id"], "asset_id": token,
                                "bids": [], "asks": []} for token in spec["asset_ids"]])
            log.append("frame", {"connection": 1, "raw_text": wire, "classification": classify_frame(wire, spec)})
            clock.seconds = 330
            summary = {"status": "lifecycle_stop", "connections": 1, "frames": 1,
                       "book_snapshot_assets_by_connection": {"1": spec["asset_ids"]}}
            log.append("session_end", summary)
            log.close()
            checkpoints = []
            for label, seconds in (("final", 330), ("postclose_120s", 420)):
                obs = copy.deepcopy(raw["observations"])
                obs.pop("order_books")
                obs["gamma_market"]["payload"]["outcomePrices"] = '["0.5", "0.5"]'
                obs["gamma_market"]["payload_sha256"] = payload_hash(obs["gamma_market"]["payload"])
                for item in obs.values():
                    item["observed_at_utc"] = (clock.base + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")
                artifact = {"schema_version": "qcrl.polymarket_raw_settlement.v1",
                            "acquired_at_utc": obs["gamma_market"]["observed_at_utc"],
                            "market_id_requested": raw["market_id_requested"], "observations": obs}
                artifact["settlement_sha256"] = payload_hash(artifact)
                path = store_raw_settlement(artifact, directory)
                checkpoints.append({"label": label, "file": path.name})
            result = {"market_start": start, "status": "observed_lifecycle_stop", "late_start": False,
                      "raw_bundle_sha256": raw["bundle_sha256"], "stream_summary": summary,
                      "verification": verify_segments(directory / "stream"), "metadata_checkpoints": checkpoints}
            result["result_sha256"] = payload_hash(result)
            persist(directory / "result.json", result)
            self.assertTrue(cohort_health(plan, tmp)["healthy"])
            manifest = directory / "stream" / "manifest.json"
            manifest.unlink()
            self.assertFalse(cohort_health(plan, tmp)["healthy"])
