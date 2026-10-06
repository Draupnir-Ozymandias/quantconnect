"""Install one future locked plan on a replica; do not start or alter Ohio."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.rolling_stream import validate_plan
from infra.stream.bootstrap_replica import validate_settings


def within_deadline(plan, metadata):
    # Reserve ten minutes for verification/replication before automatic stop.
    deadline = datetime.fromisoformat(metadata["stop_at_utc"]).timestamp()
    if plan["market_starts"][-1] + 420 + 600 >= deadline:
        raise ValueError("cohort would exceed replica stop deadline/reserve")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or Path(__file__).resolve().parents[2] != Path("/opt/qcrl-stream"):
        raise SystemExit("Run as root from the replica checkout")
    root = Path("/var/lib/qcrl-stream")
    metadata = json.loads((root / "replica-bootstrap.json").read_text())
    validate_settings(metadata["bucket"], metadata["region"], metadata["observer_label"], "", 48)
    if Path("/opt/qcrl").exists():
        raise SystemExit("Refuse an existing primary/daily collector")
    if subprocess.run(["systemctl", "is-active", "--quiet", "qcrl-stream-pilot.service"]).returncode == 0:
        raise SystemExit("Observer already active")
    plan = validate_plan(json.loads(Path(args.plan).read_text()))
    within_deadline(plan, metadata)
    from execution_truth.acquisition import utc_now
    if plan["market_starts"][0] < utc_now().timestamp() + 45:
        raise SystemExit("Plan is no longer prospective; declare a fresh shared cohort")
    target = root / ("plan-" + plan["plan_sha256"] + ".json")
    with target.open("x") as handle:
        json.dump(plan, handle, indent=2, sort_keys=True)
    shutil.chown(target, user="qcrl", group="qcrl")
    config = Path("/etc/qcrl-stream.env")
    if config.exists():
        previous = next(line.split("=", 1)[1] for line in config.read_text().splitlines() if line.startswith("QCRL_STREAM_ROOT="))
        backup = config.with_name(config.name + "." + Path(previous).name)
        with backup.open("x") as handle:
            handle.write(config.read_text())
    config.write_text("QCRL_STREAM_PLAN=" + str(target) + "\nQCRL_STREAM_ROOT=" + str(root / ("pilot-" + plan["plan_sha256"]))
        + "\nQCRL_STREAM_BUCKET=" + metadata["bucket"] + "\nAWS_DEFAULT_REGION=" + metadata["region"] + "\n")
    config.chmod(0o644)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print("Installed only. Verify clocks, identities and all observer plans before starting.")


if __name__ == "__main__":
    main()
