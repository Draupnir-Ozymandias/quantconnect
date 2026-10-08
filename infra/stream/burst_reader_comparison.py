"""Finite synthetic localhost bursts with separately launched producer/consumer."""
import argparse
from datetime import timedelta
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from infra.stream.reader_comparison import load_corpus, prepare_message
from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log
from execution_truth.receive_adapter import ObservedSocket, _load_library
from execution_truth.receive_path import ReceivePathTracker, declare, sample_clock, validate_delivery
from execution_truth.rolling_stream import persist
from execution_truth.stream_freshness import statistics

POLICY = {"schema_version": "qcrl.burst_reader_policy.v2", "cycles": 6,
          "phases": [{"seconds": 4, "rate": 500}, {"seconds": 1, "rate": 3000}],
          "rounds": 3, "modes": ["bare", "receive", "recorder"],
          "mode_order": "rotating_latin_order_by_round", "pacing": "absolute_deadlines_no_drops",
          "producer_cpu_quota_percent": 100, "consumer_cpu_quota_percent": 75,
          "memory_max_bytes_per_process_group": 536870912, "tasks_max": 32,
          "runtime_max_seconds_per_unit": 120,
          "isolation": "separate_process_and_cgroup_shared_host_no_core_affinity",
          "synthetic_workload_not_exchange_emission": True,
          "heartbeat": "replace_last_message_of_each_cycle_with_synthetic_text_PONG_all_modes",
          "orders_authorized": False}


def offsets(cycles=None, phases=None):
    cycles = POLICY["cycles"] if cycles is None else cycles
    phases = POLICY["phases"] if phases is None else phases
    if type(cycles) is not int or not 1 <= cycles <= 6:
        raise ContractError("cycle budget exceeded")
    out, elapsed = [], 0.0
    for _ in range(cycles):
        for phase_index, phase in enumerate(phases):
            seconds, rate = phase["seconds"], phase["rate"]
            if not 0 < seconds <= 4 or not 0 < rate <= 3000:
                raise ContractError("phase budget exceeded")
            for i in range(int(seconds * rate)):
                item = {"offset": elapsed + i / rate, "phase_rate": rate}
                if phase_index == len(phases)-1 and i == int(seconds*rate)-1:
                    item["synthetic_pong"] = True
                out.append(item)
            elapsed += seconds
    return out


def read(path, field):
    obj = json.loads(Path(path).read_text())
    verify_artifact_hash(obj, field, str(path))
    return obj


def signed(path, obj, field):
    obj[field] = payload_hash(obj)
    persist(path, obj)
    return obj


def declare_run(corpus_path, root):
    corpus = load_corpus(corpus_path)
    root = Path(root)
    source_root = Path(__file__).resolve().parents[2]
    names = ("infra/stream/burst_reader_comparison.py", "infra/stream/reader_comparison.py",
             "execution_truth/receive_adapter.py", "execution_truth/receive_path.py",
             "execution_truth/market_stream.py", "execution_truth/connection_freshness.py",
             "execution_truth/stream_segments.py")
    signed(root / "declaration.json", {"schema_version": "qcrl.burst_reader_declaration.v1",
           "policy": POLICY, "corpus_sha256": corpus["corpus_sha256"],
           "sources": {name: hashlib.sha256((source_root/name).read_bytes()).hexdigest() for name in names},
           "orders_authorized": False, "public_network_capture": False}, "plan_sha256")
    persist(root / "corpus.json", corpus)


def context(root, mode):
    root = Path(root)
    declaration = read(root / "declaration.json", "plan_sha256")
    if declaration.get("policy") != POLICY or mode not in POLICY["modes"]:
        raise ContractError("unsupported fixed burst declaration or mode")
    source_root = Path(__file__).resolve().parents[2]
    for name, digest in declaration["sources"].items():
        if hashlib.sha256((source_root/name).read_bytes()).hexdigest() != digest:
            raise ContractError("declared source bytes changed")
    corpus = load_corpus(root / "corpus.json")
    if corpus["corpus_sha256"] != declaration["corpus_sha256"]:
        raise ContractError("declaration corpus mismatch")
    spec = stream_plan(corpus["bundle"], segmented=True, profiling=True, resilient=True,
                       receive_path=True, freshness_telemetry=True, receive_policy="v2",
                       source_plan_sha256=declaration["plan_sha256"], max_seconds=90,
                       max_frames=len(offsets()))
    return declaration, corpus, spec


def localhost_uri(uri):
    try:
        parsed = urlsplit(uri)
        valid = (parsed.scheme == "ws" and parsed.hostname == "127.0.0.1"
                 and parsed.port is not None and 0 < parsed.port < 65536
                 and parsed.username is None and parsed.password is None
                 and not parsed.path and not parsed.query and not parsed.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ContractError("synthetic producer URI must be numeric localhost only")


def identity():
    return {"pid": os.getpid(), "cgroup": Path("/proc/self/cgroup").read_text()
            if Path("/proc/self/cgroup").exists() else None,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            if Path("/proc/sys/kernel/random/boot_id").exists() else None}


def produce(root, case, mode):
    from websockets.sync.server import serve
    from websockets.exceptions import ConnectionClosed
    _load_library()
    declaration, corpus, spec = context(root, mode)
    case = Path(case)
    schedule = offsets()
    origin = time.monotonic()
    base = _time(spec["event_start_at_utc"])
    ready = {"plan_sha256": declaration["plan_sha256"], "mode": mode,
             "origin_monotonic": origin, "fixture_base_utc": base.isoformat(),
             "producer_identity": identity()}
    finished = threading.Event()
    errors = []
    def handler(conn):
        try:
            if json.loads(conn.recv(timeout=15)) != spec["subscription"]:
                raise ContractError("unexpected synthetic subscription")
            start = time.monotonic() + .1
            sent, observations = [], []
            cpu_start = time.process_time()
            for i, target in enumerate(schedule):
                deadline = start + target["offset"]
                time.sleep(max(0, deadline - time.monotonic()))
                begin = time.monotonic()
                raw = ("PONG" if target.get("synthetic_pong") else
                       prepare_message(corpus, i, begin, base + timedelta(seconds=begin-origin)))
                send_start = time.monotonic()
                conn.send(raw)
                end = time.monotonic()
                sent.append(raw)
                observations.append({"sequence": i, "phase_rate": target["phase_rate"],
                                     "deadline": deadline, "begin": begin,
                                     "send_start": send_start, "send_end": end})
            cpu_seconds = time.process_time() - cpu_start
            # Publication/validation are outside producer pacing.
            signed(case / "producer.json", {"mode": mode, "ready_sha256": ready["ready_sha256"],
                   "producer_identity": ready["producer_identity"], "messages": observations,
                   "raw_messages_sha256": payload_hash(sent), "timed_cpu_seconds": cpu_seconds},
                   "producer_sha256")
            try:
                conn.recv(timeout=45)
            except ConnectionClosed:
                pass
        except Exception as exc:
            errors.append(type(exc).__name__ + ": " + str(exc))
        finally:
            finished.set()
    with serve(handler, "127.0.0.1", 0, compression=None, ping_interval=None, close_timeout=1) as server:
        ready["uri"] = "ws://127.0.0.1:" + str(server.socket.getsockname()[1])
        signed(case / "ready.json", ready, "ready_sha256")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        if not finished.wait(100):
            server.shutdown()
            raise ContractError("finite producer timed out")
        server.shutdown()
        thread.join(3)
    if errors:
        raise ContractError("producer failed: " + repr(errors))


def consume(root, case, mode):
    from websockets.sync.client import connect
    _load_library()
    declaration, corpus, spec = context(root, mode)
    case = Path(case)
    ready = read(case / "ready.json", "ready_sha256")
    localhost_uri(ready["uri"])
    if ready["plan_sha256"] != declaration["plan_sha256"] or ready["mode"] != mode:
        raise ContractError("producer readiness binding mismatch")
    consumer_identity = identity()
    if consumer_identity["pid"] == ready["producer_identity"]["pid"]:
        raise ContractError("producer must be a separate process")
    if consumer_identity["boot_id"] != ready["producer_identity"]["boot_id"]:
        raise ContractError("monotonic comparison requires same boot")
    base = _time(ready["fixture_base_utc"])
    def clock():
        return base + timedelta(seconds=time.monotonic()-ready["origin_monotonic"])
    tracker = ReceivePathTracker(declare(declaration["plan_sha256"], "localhost.burst",
                                        stream_spec_sha256=payload_hash(spec), policy_version="v2"))
    raws, records, stamps, queues = [], [], [], []
    client = None
    summary = None
    cpu_start = time.process_time()
    try:
        if mode == "recorder":
            def connector(t, number, **kwargs):
                nonlocal client
                client = ObservedSocket(ready["uri"], t, number, **kwargs)
                class Traced:
                    reset = client.reset
                    def send(self, message): return client.send(message)
                    def recv(self, timeout):
                        raw, record = client.recv(timeout)
                        raws.append(raw); records.append(record)
                        stamps.append(record.get("application_delivery"))
                        return raw, record
                    def close(self): return client.close()
                return Traced()
            summary = collect_market_stream(corpus["bundle"], spec, case / "stream", connector=connector,
                    clock=clock, monotonic=time.monotonic, clock_domain="localhost.burst")
        else:
            client = (ObservedSocket(ready["uri"], tracker, 1, clock=clock) if mode == "receive" else
                      connect(ready["uri"], compression=None, ping_interval=None, proxy=None,
                              max_queue=16, max_size=262144, close_timeout=5))
            client.send(json.dumps(spec["subscription"]))
            for _ in range(len(offsets())):
                if mode == "receive":
                    raw, record = client.recv(45)
                    records.append(record); stamps.append(record.get("application_delivery"))
                else:
                    raw = client.recv(timeout=45)
                    stamps.append(sample_clock(clock, time.monotonic, "localhost.burst"))
                    assembler = client.recv_messages
                    with assembler.mutex:
                        queues.append({"library_queue_depth": None if assembler.closed else assembler.frames.qsize(),
                                       "library_backpressure_active": assembler.paused})
                raws.append(raw)
    finally:
        if client is not None:
            client.close()
    cpu_seconds = time.process_time()-cpu_start
    # Persist raw bodies for EVERY mode; independent identity audits need not
    # trust only the in-run aggregate equality. All writes here are post-loop.
    signed(case / "deliveries.json", {"consumer_identity": consumer_identity, "raws": raws,
           "stamps": stamps, "receive_records": records, "bare_queue_samples": queues,
           "timed_cpu_seconds": cpu_seconds, "recorder_summary": summary}, "delivery_sha256")


def verify_case(root, case, mode, *, require_isolation=False):
    declaration, _, _ = context(root, mode)
    case = Path(case)
    ready = read(case / "ready.json", "ready_sha256")
    producer = read(case / "producer.json", "producer_sha256")
    delivery = read(case / "deliveries.json", "delivery_sha256")
    if (ready["plan_sha256"] != declaration["plan_sha256"] or ready["mode"] != mode
            or producer["mode"] != mode or producer["ready_sha256"] != ready["ready_sha256"]
            or producer["producer_identity"] != ready["producer_identity"]):
        raise ContractError("case source binding mismatch")
    p, c = producer["producer_identity"], delivery["consumer_identity"]
    isolated = p["cgroup"] is not None and c["cgroup"] is not None and p["cgroup"] != c["cgroup"]
    if p["pid"] == c["pid"] or p["boot_id"] != c["boot_id"] or (require_isolation and not isolated):
        raise ContractError("process/boot/cgroup isolation failed")
    raws, stamps, observations = delivery["raws"], delivery["stamps"], producer["messages"]
    if len(raws) != len(offsets()) or len(stamps) != len(raws) or len(observations) != len(raws):
        raise ContractError("incomplete burst case")
    if payload_hash(raws) != producer["raw_messages_sha256"]:
        raise ContractError("producer/consumer raw identity mismatch")
    groups = {rate: {"ages": [], "lateness": [], "send": []} for rate in (500, 3000)}
    for i, (raw, stamp, obs, target) in enumerate(zip(raws, stamps, observations, offsets())):
        if target.get("synthetic_pong"):
            if raw != "PONG": raise ContractError("synthetic heartbeat mismatch")
            events = []
        else:
            events = json.loads(raw)
            events = events if isinstance(events, list) else [events]
        expected_deadline = observations[0]["deadline"] + target["offset"]
        if (obs["sequence"] != i or obs["phase_rate"] != target["phase_rate"]
                or abs(obs["deadline"]-expected_deadline) > 1e-8
                or any(e["_qcrl_probe"] != {"sequence": i, "producer_begin_monotonic": obs["begin"]} for e in events)):
            raise ContractError("sequence/probe identity mismatch")
        group = groups[obs["phase_rate"]]
        if stamp is not None:
            group["ages"].append(stamp["monotonic_after"]-obs["begin"])
        group["lateness"].append(obs["begin"]-obs["deadline"])
        group["send"].append(obs["send_end"]-obs["send_start"])
    records = delivery["receive_records"]
    if mode != "bare" and len(records) != len(raws):
        raise ContractError("incomplete receive telemetry")
    if mode == "receive":
        _, _, spec = context(root, mode)
        contract = declare(declaration["plan_sha256"], "localhost.burst",
                           stream_spec_sha256=payload_hash(spec), policy_version="v2")
        for raw, record in zip(raws, records):
            validate_delivery(record, contract, raw)
    verification = None
    if mode == "recorder":
        verification = verify_stream_log(case / "stream")
        if verification["frames"] != len(raws) or delivery["recorder_summary"]["status"] != "frame_limit":
            raise ContractError("recorder hit another bound")
        archived = []
        for segment in sorted((case / "stream").glob("segment-*.gz")):
            with gzip.open(segment, "rt") as handle:
                for line in handle:
                    row = json.loads(line)
                    if row["kind"] == "frame":
                        archived.append(row["payload"]["raw_text"])
        if archived != raws:
            raise ContractError("recorder archives differ from delivered raw bodies")
    q = records or delivery["bare_queue_samples"]
    phase_windows, position = [], 0
    for cycle in range(POLICY["cycles"]):
        for phase in POLICY["phases"]:
            n = int(phase["seconds"]*phase["rate"])
            first, last = observations[position], observations[position+n-1]
            phase_windows.append({"cycle": cycle, "target_rate": phase["rate"], "messages": n,
                "attained_begin_messages_per_second": (n-1)/(last["begin"]-first["begin"]) if n>1 else None,
                "first_begin": first["begin"], "last_begin": last["begin"],
                "first_deadline": first["deadline"], "last_deadline": last["deadline"]})
            position += n
    result = {"schema_version": "qcrl.burst_reader_case.v2", "mode": mode,
        "plan_sha256": declaration["plan_sha256"], "ready_sha256": ready["ready_sha256"],
        "producer_sha256": producer["producer_sha256"], "delivery_sha256": delivery["delivery_sha256"],
        "messages": len(raws), "raw_identity_verified": True, "separate_cgroups_observed": isolated,
        "quota_configuration_independently_verified": False,
        "producer_identity": p, "consumer_identity": c,
        "producer_attained_messages_per_second": (len(raws)-1)/(observations[-1]["begin"]-observations[0]["begin"]),
        "phase_windows": phase_windows,
        "phases": {str(rate): {"producer_begin_to_delivery_upper": statistics(g["ages"]),
                    "producer_deadline_lateness": statistics(g["lateness"]),
                    "producer_send_call_seconds": statistics(g["send"])} for rate, g in groups.items()},
        "consumer_timed_cpu_seconds": delivery["timed_cpu_seconds"],
        "producer_timed_cpu_seconds": producer["timed_cpu_seconds"],
        "missing_delivery_stamps": sum(s is None for s in stamps),
        "unknown_receive_records": sum(not r.get("receive_marker") for r in records),
        "max_sampled_queue_depth": max((r["library_queue_depth"] for r in q if r.get("library_queue_depth") is not None), default=None),
        "paused_delivered_samples": sum(r.get("library_backpressure_active") is True for r in q),
        "verification": verification, "orders_authorized": False, "public_network_capture": False}
    return signed(case / "report.json", result, "report_sha256")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("declare", "produce", "consume", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--mode", choices=POLICY["modes"])
    parser.add_argument("--require-isolation", action="store_true")
    args = parser.parse_args()
    if args.role == "declare":
        if args.corpus is None: parser.error("declaration requires corpus")
        declare_run(args.corpus, args.root)
    else:
        if args.case is None or args.mode is None: parser.error("case and mode required")
        if args.role == "produce": produce(args.root, args.case, args.mode)
        elif args.role == "consume": consume(args.root, args.case, args.mode)
        else:
            result = verify_case(args.root, args.case, args.mode, require_isolation=args.require_isolation)
            print(json.dumps(result), flush=True)


if __name__ == "__main__": main()
