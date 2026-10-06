"""Bounded opt-in recorder diagnostics, not network-latency attribution."""
import os
import math
from pathlib import Path
import time

POLICY = {"schema_version": "qcrl.stream_profiling.v1", "sample_seconds": 5,
          "max_samples": 121, "duration_bucket_seconds": [.001, .005, .01, .05, .1, .5, 1.0]}
STAGES = ("recv_wait", "classify", "append", "encode_hash", "compress_write", "fsync", "seal")


def read_resources():
    """Process metrics and service-wide cgroup counters; absent is not zero."""
    cpu = os.times()
    result = {"process_cpu_seconds": cpu.user + cpu.system, "rss_bytes": None,
              "cgroup_cpu_stat": None, "unavailable": []}
    try:
        status = Path("/proc/self/status").read_text()
        line = next(line for line in status.splitlines() if line.startswith("VmRSS:"))
        result["rss_bytes"] = int(line.split()[1]) * 1024
    except (OSError, ValueError, StopIteration):
        result["unavailable"].append("rss")
    try:
        entry = next(line for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::"))
        relative = entry[3:].lstrip("/")
        if ".." in Path(relative).parts:
            raise ValueError("invalid cgroup path")
        text = (Path("/sys/fs/cgroup") / relative / "cpu.stat").read_text()
        allowed = {"usage_usec", "user_usec", "system_usec", "nr_periods", "nr_throttled", "throttled_usec"}
        result["cgroup_cpu_stat"] = {key: int(value) for key, value in
                                   (line.split() for line in text.splitlines()) if key in allowed}
        if not result["cgroup_cpu_stat"]:
            raise ValueError("no supported cgroup counters")
    except (OSError, ValueError, StopIteration):
        result["cgroup_cpu_stat"] = None
        result["unavailable"].append("cgroup_cpu_stat")
    return result


class StreamProfiler:
    def __init__(self, monotonic=time.monotonic, resources=read_resources):
        self.monotonic, self.resources = monotonic, resources
        self.last = monotonic()
        self.samples, self.totals = 0, {}

    def record(self, stage, seconds):
        if stage not in STAGES or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("invalid profiler stage/duration")
        stats = self.totals.setdefault(stage, {"count": 0, "seconds": 0.0, "max_seconds": 0.0,
                                              "bucket_counts": [0] * 8})
        stats["count"] += 1
        stats["seconds"] += seconds
        stats["max_seconds"] = max(stats["max_seconds"], seconds)
        index = next((i for i, boundary in enumerate(POLICY["duration_bucket_seconds"])
                      if seconds <= boundary), 7)
        stats["bucket_counts"][index] += 1

    def sample(self, log, force=False):
        now = self.monotonic()
        if self.samples >= POLICY["max_samples"] or (not force and now - self.last < POLICY["sample_seconds"]):
            return
        # Snapshot excludes the sample's own append; those timings enter the next
        # sample. No recursion and no per-frame resource-file reads.
        payload = {"schema_version": POLICY["schema_version"], "sample": self.samples,
                   "window_seconds": now - self.last, "durations": self.totals,
                   "resources": self.resources(), "cgroup_scope": "whole_service_not_one_market",
                   "stages_overlap": True, "orders_authorized": False}
        self.totals = {}
        self.samples += 1
        self.last = now
        log.append("profiling_sample", payload)
