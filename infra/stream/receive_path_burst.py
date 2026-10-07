"""Finite deterministic offline recorder burst experiment, never a live capture."""

import argparse
import hashlib
from pathlib import Path
import platform
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.contracts import payload_hash
from execution_truth.rolling_stream import persist
from tests.receive_burst_fixture import SCENARIOS, run_scenario


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=False)
    code = Path(__file__).resolve().parents[2]
    files = ("infra/stream/receive_path_burst.py", "tests/receive_burst_fixture.py",
             "tests/test_receive_capture.py", "tests/test_market_stream.py", "tests/test_taker_replay.py",
             "execution_truth/receive_path.py", "execution_truth/market_stream.py", "execution_truth/stream_segments.py")
    report = {"schema_version": "qcrl.synthetic_receive_burst_experiment.v1", "python": platform.python_version(),
              "sources": {name: hashlib.sha256((code / name).read_bytes()).hexdigest() for name in files},
              "network_access": False, "orders_authorized": False, "synthetic_not_performance_benchmark": True,
              "scenarios": []}
    for scenario in SCENARIOS:
        result = run_scenario(scenario, args.root / scenario["name"])
        report["scenarios"].append({"name": scenario["name"], "report_sha256": result["report_sha256"],
                                    "connections": result["connections"], "observation": result["observation"]})
        print(scenario["name"], {key: (value["available"], value["unavailable"])
                                for key, value in result["connections"].items()}, flush=True)
    report["report_sha256"] = payload_hash(report)
    persist(args.root / "experiment.json", report)
    print("report_sha256=" + report["report_sha256"])


if __name__ == "__main__":
    main()
