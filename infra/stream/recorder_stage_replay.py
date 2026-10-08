"""Finite offline component costs; never a collector or a fill/latency model."""
import argparse
from datetime import datetime
import gzip
import json
import os
from pathlib import Path
import platform
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.connection_freshness import ConnectionFreshness
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import verify_stream_log
from execution_truth.rolling_stream import persist
from execution_truth.stream_segments import SegmentedStreamLog, file_hash

POLICY = {"schema_version": "qcrl.recorder_stage_replay_policy.v1", "rounds": 3,
          "max_uncompressed_bytes": 192 * 1024**2, "max_records": 40000,
          "stages": ["encode_hash", "freshness", "gzip_write", "gzip_write_fsync", "durable_log"],
          "order": "rotate_left_by_round", "gzip_level": 1,
          "input": "verified_sealed_synthetic_localhost_stream_v7",
          "pacing": "unpaced_offline_same_retained_records",
          "network_access": False, "orders_authorized": False,
          "component_times_additive": False, "socket_delay_causality_proven": False}


def load_rows(source):
    source = Path(source)
    descriptors = sorted(source.glob("segment-*.json"))
    if not descriptors or len(descriptors) > 32:
        raise ContractError("replay segment budget exceeded or missing")
    declared_bytes = sum(json.loads(p.read_text())["uncompressed_bytes"] for p in descriptors)
    if not 0 < declared_bytes <= POLICY["max_uncompressed_bytes"]:
        raise ContractError("replay byte budget exceeded")
    verification = verify_stream_log(source)
    rows, actual_bytes = [], 0
    for descriptor in descriptors:
        data = json.loads(descriptor.read_text())
        with gzip.open(source / data["file"], "rb") as handle:
            for line in handle:
                actual_bytes += len(line)
                if actual_bytes > POLICY["max_uncompressed_bytes"] or len(rows) >= POLICY["max_records"]:
                    raise ContractError("replay retained record budget exceeded")
                rows.append(json.loads(line))
    spec = rows[0]["payload"]["spec"]
    contract = rows[0]["payload"].get("receive_path_contract", {})
    if (spec.get("schema_version") != "qcrl.public_market_stream_spec.v7"
            or contract.get("clock_domain") != "localhost.burst"):
        raise ContractError("only retained synthetic localhost v7 streams are eligible")
    return rows, spec, verification


def encode_rows(rows, retain=True):
    encoded, previous, byte_count = [], None, 0
    for row in rows:
        value = {key: val for key, val in row.items() if key != "record_sha256"}
        if value["previous_sha256"] != previous:
            raise ContractError("replay row chain mismatch")
        previous = payload_hash(value)
        if previous != row["record_sha256"]:
            raise ContractError("replay row digest mismatch")
        value["record_sha256"] = previous
        content = (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")
        byte_count += len(content)
        if retain:
            encoded.append(content)
    return encoded if retain else {"records": len(rows), "encoded_bytes": byte_count,
                                   "final_record_sha256": previous}


def freshness_rows(rows, spec):
    states, snapshots = {}, 0
    for row in rows:
        payload = row["payload"]
        if row["kind"] == "frame":
            connection = payload["connection"]
            state = states.setdefault(connection, ConnectionFreshness(connection, spec["asset_ids"]))
            state.observe(payload["raw_text"], payload["classification"], payload["receive_path"])
        elif row["kind"] == "connection_freshness":
            connection = payload["connection"]
            state = states.setdefault(connection, ConnectionFreshness(connection, spec["asset_ids"]))
            sample = state.snapshot(payload["sample_monotonic_seconds"], payload["reason"])
            if sample != payload:
                raise ContractError("freshness replay differs from original sample")
            state.samples += 1
            state.last_sample = payload["sample_monotonic_seconds"]
            snapshots += 1
    return {"messages": sum(s.counts["messages"] for s in states.values()), "snapshots": snapshots}


def compressed_rows(rows, encoded, root, policy, durable):
    """Pre-encoded synthetic sink, not a stream archive. Matched flush/seal cadence."""
    root.mkdir(exist_ok=False)
    outputs, pending, size = [], 0, 0
    last_sync = rows[0]["local_monotonic_seconds"]
    raw = writer = None
    fsyncs = 0
    def seal():
        nonlocal fsyncs
        writer.close(); raw.flush()
        if durable:
            os.fsync(raw.fileno()); fsyncs += 1
        raw.close()
    for row, content in zip(rows, encoded):
        if raw is None or size + len(content) > policy["segment_uncompressed_bytes"]:
            if raw is not None:
                seal()
            path = root / ("synthetic-%06d.gz" % len(outputs))
            outputs.append(path)
            raw = path.open("xb")
            writer = gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=1, mtime=0)
            size = 0
        writer.write(content); pending += 1; size += len(content)
        now = row["local_monotonic_seconds"]
        if row["kind"] != "frame" or pending >= 64 or now - last_sync >= 1:
            writer.flush(); raw.flush()
            if durable:
                os.fsync(raw.fileno()); fsyncs += 1
            pending, last_sync = 0, now
    if raw is not None:
        seal()
    return {"files": [p.name for p in outputs], "fsync_calls": fsyncs}


def durable_rows(rows, spec, path):
    current = rows[0]
    def clock():
        return datetime.fromisoformat(current["received_at_utc"].replace("Z", "+00:00"))
    log = SegmentedStreamLog(path, clock, lambda: current["local_monotonic_seconds"], spec["storage"])
    try:
        for current in rows:
            log.append(current["kind"], current["payload"])
            if log.previous != current["record_sha256"]:
                raise ContractError("durable replay changed row identity")
    finally:
        log.close()
    return {"records": log.ordinal, "final_record_sha256": log.previous}


def run(source, output):
    rows, spec, verification = load_rows(source)
    encoded = encode_rows(rows)  # Prepare identical compressor inputs outside timing.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    source = Path(source)
    repo = Path(__file__).resolve().parents[2]
    names = ["infra/stream/recorder_stage_replay.py"] + sorted(
        str(p.relative_to(repo)) for p in (repo/"execution_truth").glob("*.py"))
    declaration = {"policy": POLICY, "input_files": {p.name: file_hash(p) for p in sorted(source.iterdir())
                   if p.is_file()}, "source_files": {n: file_hash(repo/n) for n in names},
                   "records": len(rows), "input_verification_sha256": payload_hash(verification)}
    declaration["plan_sha256"] = payload_hash(declaration)
    persist(output/"declaration.json", declaration)
    results = []
    for round_index in range(POLICY["rounds"]):
        stages = POLICY["stages"][round_index:] + POLICY["stages"][:round_index]
        for stage in stages:
            root = output / (str(round_index) + "-" + stage)
            start_wall, start_cpu = time.perf_counter(), time.process_time()
            if stage == "encode_hash":
                detail = encode_rows(rows, retain=False)
            elif stage == "freshness":
                detail = freshness_rows(rows, spec)
            elif stage in ("gzip_write", "gzip_write_fsync"):
                detail = compressed_rows(rows, encoded, root, spec["storage"], stage.endswith("fsync"))
            else:
                detail = durable_rows(rows, spec, root)
            cpu, wall = time.process_time()-start_cpu, time.perf_counter()-start_wall
            # Verification and hashing outputs are outside each measured stage.
            if stage == "encode_hash" and detail["encoded_bytes"] != sum(map(len, encoded)):
                raise ContractError("encoded replay byte count changed")
            if stage.startswith("gzip_write"):
                ordinal = 0
                for name in detail["files"]:
                    with gzip.open(root/name, "rb") as handle:
                        for line in handle:
                            if ordinal >= len(encoded) or line != encoded[ordinal]:
                                raise ContractError("compressed replay identity mismatch")
                            ordinal += 1
                if ordinal != len(encoded):
                    raise ContractError("compressed replay truncated")
                detail["compressed_sha256"] = {name: file_hash(root/name) for name in detail["files"]}
            if stage == "durable_log":
                replay_verification = verify_stream_log(root)
                if replay_verification != verification:
                    raise ContractError("durable verification differs from source")
            results.append({"round": round_index, "stage": stage, "cpu_seconds": cpu,
                            "wall_seconds": wall, "detail": detail})
    if declaration["input_files"] != {p.name: file_hash(p) for p in sorted(source.iterdir()) if p.is_file()}:
        raise ContractError("source changed during replay")
    if declaration["source_files"] != {n: file_hash(repo/n) for n in names}:
        raise ContractError("implementation changed during replay")
    report = {"schema_version": "qcrl.recorder_stage_replay.v1", "plan_sha256": declaration["plan_sha256"],
              "python": platform.python_version(), "platform": platform.platform(), "results": results,
              "pid": os.getpid(), "cgroup": Path("/proc/self/cgroup").read_text()
              if Path("/proc/self/cgroup").exists() else None,
              "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()
              if Path("/proc/sys/kernel/random/boot_id").exists() else None,
              "all_output_identity_checks_passed": True, "socket_delay_causality_proven": False,
              "component_times_additive": False, "orders_authorized": False}
    report["report_sha256"] = payload_hash(report)
    persist(output/"report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), sort_keys=True))
