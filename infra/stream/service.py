"""Run one locked pilot and replicate evidence to the existing runtime S3 prefix."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.rolling_stream import run_pilot, validate_plan


def upload(root, bucket, region):
    # Never delete, promote, or claim that a successfully uploaded prefix is complete.
    subprocess.run(["aws", "s3", "sync", str(root),
                    "s3://" + bucket + "/runtime/streams/" + root.name + "/",
                    "--region", region, "--sse", "AES256", "--only-show-errors"],
                   check=True, timeout=120)


def main():
    plan_path = Path(os.environ["QCRL_STREAM_PLAN"])
    root = Path(os.environ["QCRL_STREAM_ROOT"])
    bucket = os.environ["QCRL_STREAM_BUCKET"]
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
    if not bucket or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-." for c in bucket):
        raise ValueError("invalid artifact bucket")
    if root.parent != Path("/var/lib/qcrl-stream") or not root.name.startswith("pilot-"):
        raise ValueError("pilot root must be one dedicated /var/lib/qcrl-stream/pilot-* directory")
    plan = validate_plan(json.loads(plan_path.read_text()))
    stop = threading.Event()
    upload_failures = []

    def replicate():
        while not stop.wait(60):
            try:
                upload(root, bucket, region)
            except Exception as exc:
                upload_failures.append(type(exc).__name__)
                print("S3_REPLICATION_FAILURE " + type(exc).__name__, flush=True)

    thread = threading.Thread(target=replicate, daemon=True)
    thread.start()
    try:
        run_pilot(plan, root)
    finally:
        stop.set()
        thread.join(timeout=125)
        upload(root, bucket, region)
    # A past failed replication is visible even when a later sync repairs it.
    print(json.dumps({"pilot_finished": True, "upload_failures": upload_failures,
                      "orders_authorized": False}), flush=True)


if __name__ == "__main__":
    main()
