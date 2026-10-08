"""Checkpointed offline stage replay with separate bounded verification processes."""
import argparse
import gzip
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import verify_stream_log
from execution_truth.stream_segments import exclusive_json, file_hash
from infra.stream import recorder_stage_replay as stages

POLICY = dict(stages.POLICY, schema_version="qcrl.recorder_stage_replay_policy.v2",
              phases=["prepare", "measure", "verify_each_stage", "finalize"],
              checkpoint_status="unverified_until_separate_receipt",
              per_process_cpu_quota_percent=75, per_process_memory_max_bytes=512*1024**2,
              per_process_tasks_max=32, per_process_runtime_max_seconds=120)


def identity():
    return {"pid": os.getpid(), "python": platform.python_version(),
            "platform": platform.platform(),
            "cgroup": Path("/proc/self/cgroup").read_text() if Path("/proc/self/cgroup").exists() else None,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            if Path("/proc/sys/kernel/random/boot_id").exists() else None}


def inventory(root):
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob("*")) if p.is_file()}


def code_inventory():
    repo = Path(__file__).resolve().parents[2]
    files = ["infra/stream/recorder_stage_split.py", "infra/stream/recorder_stage_replay.py",
             "infra/stream/run_recorder_stage_split.sh"] + sorted(
        str(p.relative_to(repo)) for p in (repo/"execution_truth").glob("*.py"))
    return {name: file_hash(repo/name) for name in files}


def signed(path, value, field):
    value[field] = payload_hash(value)
    exclusive_json(Path(path), value)
    return value


def read(path, field):
    value = json.loads(Path(path).read_text())
    verify_artifact_hash(value, field, str(path))
    return value


def check_binding(source, root):
    prepared = read(Path(root)/"prepared.json", "prepared_sha256")
    if prepared["policy"] != POLICY or prepared["input_files"] != inventory(Path(source)):
        raise ContractError("prepared input or fixed policy changed")
    if prepared["source_files"] != code_inventory():
        raise ContractError("prepared implementation changed")
    return prepared


def source_rows(source):
    count, total = 0, 0
    for path in sorted(Path(source).glob("segment-*.gz")):
        with gzip.open(path, "rb") as handle:
            while True:
                line = handle.readline(4*1024**2+1)
                if not line:
                    break
                total += len(line); count += 1
                if len(line) > 4*1024**2 or total > POLICY["max_uncompressed_bytes"] or count > POLICY["max_records"]:
                    raise ContractError("source replay budget exceeded")
                yield json.loads(line)


def prepare(source, root):
    source, root = Path(source), Path(root)
    inputs, code = inventory(source), code_inventory()
    root.mkdir(parents=True, exist_ok=False)
    descriptors = sorted(source.glob("segment-*.json"))
    if not 1 <= len(descriptors) <= 32:
        raise ContractError("source segment budget invalid")
    declared = sum(json.loads(p.read_text())["uncompressed_bytes"] for p in descriptors)
    if not 0 < declared <= POLICY["max_uncompressed_bytes"]:
        raise ContractError("source byte budget invalid")
    # Full semantics checked with no retained measurement working data.
    verified = verify_stream_log(source)
    first = next(source_rows(source))
    spec = first["payload"]["spec"]
    if (spec.get("schema_version") != "qcrl.public_market_stream_spec.v7"
            or first["payload"].get("receive_path_contract", {}).get("clock_domain") != "localhost.burst"):
        raise ContractError("only synthetic localhost v7 input is allowed")
    manifest = read(source/"manifest.json", "manifest_sha256")
    if manifest["records"] > POLICY["max_records"]:
        raise ContractError("source record budget invalid")
    if inputs != inventory(source) or code != code_inventory():
        raise ContractError("source or implementation changed during preparation")
    return signed(root/"prepared.json", {"schema_version": "qcrl.recorder_stage_prepared.v2",
        "policy": POLICY, "input_files": inputs, "source_files": code, "spec": spec,
        "manifest": manifest, "verification": verified, "identity": identity(),
        "orders_authorized": False}, "prepared_sha256")


def case_order():
    return [(r, s) for r in range(POLICY["rounds"])
            for s in POLICY["stages"][r:]+POLICY["stages"][:r]]


def measure(source, root):
    root = Path(root)
    prepared = check_binding(source, root)
    # No heavyweight verification here: exact file binding proves these are
    # the same bytes already verified by prepare in a separate process.
    (root/"measurement").mkdir(exist_ok=False)
    rows = list(source_rows(source))
    if len(rows) != prepared["manifest"]["records"]:
        raise ContractError("prepared record count changed")
    encoded = stages.encode_rows(rows)
    checkpoints = []
    for round_index, stage in case_order():
        name = str(round_index)+"-"+stage
        folder = root/"measurement"/name
        wall, cpu = time.perf_counter(), time.process_time()
        if stage == "encode_hash":
            detail = stages.encode_rows(rows, retain=False)
        elif stage == "freshness":
            detail = stages.freshness_rows(rows, prepared["spec"])
        elif stage.startswith("gzip_write"):
            detail = stages.compressed_rows(rows, encoded, folder, prepared["spec"]["storage"], stage.endswith("fsync"))
        else:
            detail = stages.durable_rows(rows, prepared["spec"], folder)
        cpu, wall = time.process_time()-cpu, time.perf_counter()-wall
        # Durable checkpoint AFTER timer but BEFORE any semantic output audit.
        checkpoint = signed(root/(name+".checkpoint.json"), {
            "schema_version": "qcrl.recorder_stage_checkpoint.v2", "prepared_sha256": prepared["prepared_sha256"],
            "round": round_index, "stage": stage, "cpu_seconds": cpu, "wall_seconds": wall,
            "detail": detail, "output_files": inventory(folder) if folder.exists() else {},
            "identity": identity(), "verified": False, "orders_authorized": False}, "checkpoint_sha256")
        checkpoints.append(checkpoint["checkpoint_sha256"])
    check_binding(source, root)
    return signed(root/"measured.json", {"schema_version": "qcrl.recorder_stage_measured.v2",
        "prepared_sha256": prepared["prepared_sha256"], "checkpoint_sha256": checkpoints,
        "verified": False, "identity": identity()}, "measured_sha256")


def checkpoint(root, prepared, round_index, stage):
    if (round_index, stage) not in case_order():
        raise ContractError("unknown fixed stage case")
    name = str(round_index)+"-"+stage
    value = read(Path(root)/(name+".checkpoint.json"), "checkpoint_sha256")
    if (value["prepared_sha256"] != prepared["prepared_sha256"] or value["round"] != round_index
            or value["stage"] != stage or value["verified"] is not False):
        raise ContractError("checkpoint binding mismatch")
    folder = Path(root)/"measurement"/name
    if value["output_files"] != (inventory(folder) if folder.exists() else {}):
        raise ContractError("checkpoint output files changed")
    if not (all(type(value[key]) in (int, float) and math.isfinite(value[key])
                for key in ("cpu_seconds", "wall_seconds"))
            and 0 <= value["wall_seconds"] and 0 <= value["cpu_seconds"] <= value["wall_seconds"]+.1):
        raise ContractError("checkpoint timing invalid")
    return value, folder


def verify_stage(source, root, round_index, stage):
    prepared = check_binding(source, root)
    value, folder = checkpoint(root, prepared, round_index, stage)
    manifest = prepared["manifest"]
    if stage == "encode_hash":
        encoded_bytes = sum(len((json.dumps(row, sort_keys=True)+"\n").encode("utf-8"))
                            for row in source_rows(source))
        expected = {"records": manifest["records"], "encoded_bytes": encoded_bytes,
                    "final_record_sha256": manifest["final_record_sha256"]}
        if value["detail"] != expected:
            raise ContractError("encoding checkpoint differs from input")
    elif stage == "freshness":
        if value["detail"] != stages.freshness_rows(source_rows(source), prepared["spec"]):
            raise ContractError("freshness checkpoint differs from input")
    else:
        expected = ((json.dumps(row, sort_keys=True)+"\n").encode("utf-8") for row in source_rows(source))
        count = 0
        paths = sorted(folder.glob("*.gz"))
        for path in paths:
            with gzip.open(path, "rb") as handle:
                while True:
                    line = handle.readline(4*1024**2+1)
                    if not line:
                        break
                    if line != next(expected, None):
                        raise ContractError("output record bytes differ from input")
                    count += 1
        if next(expected, None) is not None or count != manifest["records"]:
            raise ContractError("output record count differs from input")
        if stage == "durable_log":
            if verify_stream_log(folder) != prepared["verification"]:
                raise ContractError("durable verification differs from prepared input")
            if value["detail"] != {"records": manifest["records"], "final_record_sha256": manifest["final_record_sha256"]}:
                raise ContractError("durable checkpoint summary mismatch")
        else:
            pending, last_sync, flushes = 0, None, 0
            for row in source_rows(source):
                now = row["local_monotonic_seconds"]
                if last_sync is None:
                    last_sync = now
                pending += 1
                if row["kind"] != "frame" or pending >= 64 or now-last_sync >= 1:
                    flushes += 1
                    pending, last_sync = 0, now
            expected_detail = {"files": [p.name for p in paths],
                               "fsync_calls": flushes+len(paths) if stage.endswith("fsync") else 0}
            if value["detail"] != expected_detail:
                raise ContractError("compression checkpoint summary mismatch")
    check_binding(source, root)
    checkpoint(root, prepared, round_index, stage)
    return signed(Path(root)/(str(round_index)+"-"+stage+".verified.json"), {
        "schema_version": "qcrl.recorder_stage_verified.v2", "prepared_sha256": prepared["prepared_sha256"],
        "checkpoint_sha256": value["checkpoint_sha256"], "verified": True,
        "identity": identity(), "orders_authorized": False}, "verification_sha256")


def finalize(source, root):
    root = Path(root)
    prepared = check_binding(source, root)
    measured = read(root/"measured.json", "measured_sha256")
    if measured["identity"]["pid"] == prepared["identity"]["pid"]:
        raise ContractError("preparation and measurement must use separate processes")
    results, checkpoints = [], []
    for round_index, stage in case_order():
        cp, _ = checkpoint(root, prepared, round_index, stage)
        receipt = read(root/(str(round_index)+"-"+stage+".verified.json"), "verification_sha256")
        if (receipt["prepared_sha256"] != prepared["prepared_sha256"]
                or receipt["checkpoint_sha256"] != cp["checkpoint_sha256"] or receipt["verified"] is not True):
            raise ContractError("stage verification receipt mismatch")
        if cp["identity"] != measured["identity"] or receipt["identity"]["pid"] == measured["identity"]["pid"]:
            raise ContractError("measurement and verification process identities overlap")
        results.append({"checkpoint": cp, "verification": receipt})
        checkpoints.append(cp["checkpoint_sha256"])
    if measured["prepared_sha256"] != prepared["prepared_sha256"] or measured["checkpoint_sha256"] != checkpoints:
        raise ContractError("measurement completion binding mismatch")
    medians = {stage: {key: statistics.median(r["checkpoint"][key] for r in results
                      if r["checkpoint"]["stage"] == stage) for key in ("cpu_seconds", "wall_seconds")}
               for stage in POLICY["stages"]}
    return signed(root/"report.json", {"schema_version": "qcrl.recorder_stage_replay.v2",
        "prepared_sha256": prepared["prepared_sha256"], "measured_sha256": measured["measured_sha256"],
        "results": results, "medians": medians, "all_output_identity_checks_passed": True,
        "component_times_additive": False, "socket_delay_causality_proven": False,
        "orders_authorized": False}, "report_sha256")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "measure", "verify", "finalize"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--round", type=int)
    parser.add_argument("--stage", choices=POLICY["stages"])
    args = parser.parse_args()
    if args.phase == "verify":
        value = verify_stage(args.source, args.output, args.round, args.stage)
    else:
        value = {"prepare": prepare, "measure": measure, "finalize": finalize}[args.phase](args.source, args.output)
    print(json.dumps({key: val for key, val in value.items() if key.endswith("sha256")}, sort_keys=True))
