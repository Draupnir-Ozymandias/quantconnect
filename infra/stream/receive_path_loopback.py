"""Finite real-library localhost throughput smoke; no Polymarket/AWS access."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import statistics
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.contracts import payload_hash
from execution_truth.receive_adapter import ObservedSocket, _load_library
from execution_truth.receive_path import ReceivePathTracker, declare, validate_delivery
from execution_truth.rolling_stream import persist


def run_case(payload, messages, observed, *, receive_policy="v1"):
    from websockets.sync.client import connect
    from websockets.sync.server import serve
    failures = []
    def handler(conn):
        try:
            for _ in range(messages):
                conn.send(payload)
            conn.recv(timeout=10)
        except Exception as exc:
            failures.append(type(exc).__name__)
    records = []
    t = ReceivePathTracker(declare(payload_hash({"synthetic": True, "messages": messages}),
                                  "loopback:synthetic-boot", stream_spec_sha256=payload_hash(payload), policy_version=receive_policy))
    with serve(handler, "127.0.0.1", 0, compression=None, ping_interval=None, close_timeout=1) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        uri = "ws://127.0.0.1:" + str(server.socket.getsockname()[1])
        client = (ObservedSocket(uri, t, 1) if observed else connect(uri, compression=None,
                  ping_interval=None, proxy=None, max_queue=16, max_size=262144, close_timeout=5))
        try:
            started = time.monotonic()
            for _ in range(messages):
                if observed:
                    message, record = client.recv(5)
                    records.append(record)
                else:
                    message = client.recv(timeout=5)
                if message != payload:
                    raise RuntimeError("raw message changed")
            elapsed = time.monotonic() - started
            client.send("done")
        finally:
            client.close()
            server.shutdown()
            thread.join(3)
        if thread.is_alive():
            raise RuntimeError("loopback server did not stop")
    if failures:
        raise RuntimeError("loopback server errors: " + repr(failures))
    for r in records:
        validate_delivery(r, t.contract, payload)
    return {"mode": "observed" if observed else "baseline", "messages": messages,
            "receive_batch_seconds": elapsed, "telemetry_available": sum(r["telemetry_available"] for r in records),
            "unavailable_reasons": sorted({r["unavailable_reason"] for r in records if r["unavailable_reason"]}),
            "timing_eligible": sum(r.get("last_observation_to_delivery", {}).get("timing_eligible", False) for r in records),
            "raw_messages_unchanged": True, "validation_outside_timed_batch": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--messages", type=int, default=300)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--receive-policy", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    if not 1 <= args.messages <= 1000 or not 1 <= args.rounds <= 5:
        parser.error("bounded smoke requires 1..1000 messages and 1..5 rounds")
    _load_library()
    cases = []
    for size in (512, 2048):
        payload = json.dumps({"synthetic": True, "padding": "x" * size}, separators=(",", ":"))
        runs = []
        for round_index in range(args.rounds):
            for observed in ((False, True) if round_index % 2 == 0 else (True, False)):
                runs.append({"round": round_index, **run_case(payload, args.messages, observed, receive_policy=args.receive_policy)})
        medians = {mode: statistics.median(r["receive_batch_seconds"] for r in runs if r["mode"] == mode)
                   for mode in ("baseline", "observed")}
        cases.append({"payload_bytes": len(payload.encode()), "runs": runs, "median_batch_seconds": medians,
                      "median_observed_to_baseline_ratio": medians["observed"] / medians["baseline"]})
    sources = {}
    for name in ("execution_truth/receive_adapter.py", "execution_truth/receive_path.py", __file__):
        path = Path(name)
        sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = {"schema_version": "qcrl.receive_path_loopback." + args.receive_policy, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "synthetic": True, "library_version": version("websockets"), "python": platform.python_version(),
              "platform": platform.platform(), "sources": sources, "cases": cases,
              "measurement": "localhost_batch_throughput_including_reader_and_receiver_observer_work",
              "not_calibrated_cpu_overhead_or_network_latency": True,
              "handshake_and_post_batch_validation_excluded": True,
              "orders_authorized": False, "external_services_contacted": False}
    if args.receive_policy == "v2":
        report["receive_policy"] = "v2"
    report["report_sha256"] = payload_hash(report)
    persist(args.output, report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
