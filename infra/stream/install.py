"""Install the separate service configuration; does not start any capture."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.rolling_stream import validate_plan


def isolated_daily_sync(source):
    """Exclude observer-owned objects from both daily sync directions."""
    download = 'str(runtime), "--only-show-errors",'
    upload = 'f"s3://{bucket}/runtime/", "--sse", "AES256",\n        "--only-show-errors",'
    if source.count(download) != 1 or source.count(upload) != 1:
        raise ValueError("Unexpected daily sync wrapper; review before installation")
    return source.replace(download, 'str(runtime), "--exclude", "streams/*", "--only-show-errors",').replace(
        upload, 'f"s3://{bucket}/runtime/", "--sse", "AES256",\n        "--exclude", "streams/*", "--only-show-errors",')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or Path(__file__).resolve().parents[2] != Path("/opt/qcrl-stream"):
        raise SystemExit("Run as root from the isolated /opt/qcrl-stream checkout")
    if not args.bucket or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-." for c in args.bucket):
        raise SystemExit("Invalid bucket")
    plan = validate_plan(json.loads(Path(args.plan).read_text()))
    daily = Path("/usr/local/bin/qcrl-collector-cycle")
    daily_backup = Path("/usr/local/bin/qcrl-collector-cycle.pre-stream")
    updated_daily = isolated_daily_sync(daily.read_text())
    if daily_backup.exists() or Path("/etc/qcrl-stream.env").exists():
        raise SystemExit("Existing stream installation/backup: inspect before updating")
    root = Path("/var/lib/qcrl-stream")
    root.mkdir(mode=0o700, exist_ok=True)
    shutil.chown(root, user="qcrl", group="qcrl")
    target = root / ("plan-" + plan["plan_sha256"] + ".json")
    with target.open("x") as handle:
        json.dump(plan, handle, indent=2)
    shutil.chown(target, user="qcrl", group="qcrl")
    state = root / ("pilot-" + plan["plan_sha256"])
    config = Path("/etc/qcrl-stream.env")
    if config.exists():
        raise SystemExit("Existing stream environment: inspect before updating")
    config.write_text("QCRL_STREAM_PLAN=" + str(target) + "\nQCRL_STREAM_ROOT=" + str(state)
                      + "\nQCRL_STREAM_BUCKET=" + args.bucket + "\nAWS_DEFAULT_REGION=us-east-2\n")
    config.chmod(0o644)
    shutil.copy2(daily, daily_backup)
    replacement = daily.with_name("qcrl-collector-cycle.stream-new")
    with replacement.open("x") as handle:
        handle.write(updated_daily)
    replacement.chmod(daily.stat().st_mode & 0o777)
    replacement.replace(daily)
    shutil.copyfile(Path(__file__).parent / "qcrl-stream-pilot.service",
                    "/etc/systemd/system/qcrl-stream-pilot.service")
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print("Installed only. Review config and start qcrl-stream-pilot.service explicitly.")


if __name__ == "__main__":
    main()
