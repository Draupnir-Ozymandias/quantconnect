from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import gzip

from execution_truth.contracts import ContractError
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log
from execution_truth.rolling_stream import pilot_plan, validate_plan
from execution_truth.stream_profiling import POLICY, StreamProfiler, read_resources
from tests.test_market_stream import Clock, Socket
from tests.test_taker_replay import raw_bundle


class ProfilingTests(unittest.TestCase):
    def test_fixed_buckets_and_stage_validation(self):
        profiler = StreamProfiler()
        for duration in (0, .003, 2):
            profiler.record("append", duration)
        stats = profiler.totals["append"]
        self.assertEqual(stats["bucket_counts"], [1, 1, 0, 0, 0, 0, 0, 1])
        self.assertEqual(stats["max_seconds"], 2)
        for stage, duration in (("unknown", 1), ("append", -1)):
            with self.assertRaises(ValueError):
                profiler.record(stage, duration)

    def test_cadence_reset_and_hard_sample_cap(self):
        now, recorded = [0], []
        class Log:
            def append(self, kind, payload):
                recorded.append(payload)
        profiler = StreamProfiler(lambda: now[0], lambda: {"rss_bytes": None})
        profiler.record("append", .1)
        profiler.sample(Log())
        self.assertEqual(recorded, [])
        now[0] = 5
        profiler.sample(Log())
        self.assertEqual(recorded[0]["durations"]["append"]["count"], 1)
        self.assertEqual(profiler.totals, {})
        for _ in range(200):
            profiler.sample(Log(), force=True)
        self.assertEqual(len(recorded), POLICY["max_samples"])

    def test_missing_linux_metrics_are_explicit(self):
        with patch("execution_truth.stream_profiling.Path.read_text", side_effect=OSError):
            values = read_resources()
        self.assertIsNone(values["rss_bytes"])
        self.assertIsNone(values["cgroup_cpu_stat"])
        self.assertEqual(values["unavailable"], ["rss", "cgroup_cpu_stat"])

    def test_linux_cgroup_and_process_scopes(self):
        def read(path):
            if str(path) == "/proc/self/status":
                return "VmRSS:\t123 kB\n"
            if str(path) == "/proc/self/cgroup":
                return "0::/system.slice/example.service\n"
            self.assertEqual(str(path), "/sys/fs/cgroup/system.slice/example.service/cpu.stat")
            return "usage_usec 999\nnr_throttled 3\nthrottled_usec 55\n"
        with patch.object(Path, "read_text", read):
            result = read_resources()
        self.assertEqual(result["rss_bytes"], 123 * 1024)
        self.assertEqual(result["cgroup_cpu_stat"]["nr_throttled"], 3)

    def test_plan_is_versioned_and_tamper_rejected(self):
        clock = Clock()
        start = int(clock.base.timestamp())
        legacy = pilot_plan(start, 1, now=clock.base - timedelta(seconds=60))
        plan = pilot_plan(start, 1, now=clock.base - timedelta(seconds=60), profiling=True)
        self.assertNotIn("profiling", legacy)
        self.assertEqual(plan["schema_version"], "qcrl.btc_5m_rolling_pilot.v3")
        self.assertEqual(validate_plan(plan), plan)
        plan["profiling"]["sample_seconds"] = 1
        with self.assertRaises(ContractError):
            validate_plan(plan)

    def test_profiling_cannot_silently_enable_for_legacy_logs(self):
        with self.assertRaises(ContractError):
            stream_plan(raw_bundle(), profiling=True)

    def test_plan_policy_does_not_alias_shared_defaults(self):
        plan = stream_plan(raw_bundle(), segmented=True, profiling=True)
        plan["profiling"]["duration_bucket_seconds"][0] = 999
        self.assertEqual(POLICY["duration_bucket_seconds"][0], .001)

    def test_profiled_collector_retains_verified_samples_and_receipt_times(self):
        raw, clock = raw_bundle(), Clock()
        spec = stream_plan(raw, segmented=True, profiling=True, max_seconds=8)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            socket = Socket(clock, ["PONG"] * 8)
            with patch("execution_truth.stream_profiling.read_resources", return_value={"rss_bytes": None}):
                summary = collect_market_stream(raw, spec, root, connector=lambda: socket,
                    clock=clock.utc, monotonic=clock.mono, pause=clock.pause)
            verification = verify_stream_log(root)
            self.assertEqual(summary["status"], "duration_limit")
            self.assertTrue(verification["session_end_present"])
            rows = []
            for file in root.glob("*.gz"):
                with gzip.open(file, "rt") as handle:
                    rows.extend(json.loads(line) for line in handle)
            samples = [r["payload"] for r in rows if r["kind"] == "profiling_sample"]
            self.assertGreaterEqual(len(samples), 2)
            self.assertIn("append", samples[-1]["durations"])
            self.assertTrue(all("socket_received_monotonic_seconds" in r["payload"]
                for r in rows if r["kind"] == "frame"))
            self.assertEqual(rows[-1]["kind"], "session_end")


if __name__ == "__main__":
    unittest.main()
