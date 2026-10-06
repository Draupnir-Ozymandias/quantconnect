"""Bootstrap a clean public-only observer, without starting a capture."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def validate_settings(bucket, region, label, ssh_key, hours):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{2,62}", bucket):
        raise ValueError("invalid artifact bucket")
    if region not in ("eu-west-1", "eu-central-1"):
        raise ValueError("replica region must be Ireland or Frankfurt")
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", label):
        raise ValueError("invalid observer label")
    if ssh_key and not re.fullmatch(r"(?:ssh-ed25519|ssh-rsa) [A-Za-z0-9+/=]+", ssh_key):
        raise ValueError("use only public key type and base64, without comment")
    if type(hours) is not int or not 1 <= hours <= 168:
        raise ValueError("runtime must be 1..168 hours")


def stop_units(deadline):
    return ("[Unit]\nDescription=Stop diagnostic replica at its declared deadline\n"
            "[Service]\nType=oneshot\nExecStart=/usr/sbin/shutdown -h now\n",
            "[Unit]\nDescription=Bounded diagnostic replica runtime\n[Timer]\n"
            "OnCalendar=" + deadline.strftime("%Y-%m-%d %H:%M:%S UTC") + "\n"
            "Persistent=true\nUnit=qcrl-replica-stop.service\n[Install]\nWantedBy=timers.target\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--ssh-key", default="")
    parser.add_argument("--runtime-hours", type=int, default=48)
    args = parser.parse_args()
    validate_settings(args.bucket, args.region, args.label, args.ssh_key, args.runtime_hours)
    code = Path(__file__).resolve().parents[2]
    if os.geteuid() != 0 or code != Path("/opt/qcrl-stream"):
        raise SystemExit("Run as root only from the clean /opt/qcrl-stream replica checkout")
    # Refuse a primary host or an already bootstrapped replica.
    root = Path("/var/lib/qcrl-stream")
    if Path("/opt/qcrl").exists() or root.exists():
        raise SystemExit("Existing collector/runtime: do not bootstrap over it")
    subprocess.run(["useradd", "--system", "--home-dir", str(root), "--shell", "/sbin/nologin", "qcrl"], check=True)
    root.mkdir(mode=0o700)
    shutil.chown(root, user="qcrl", group="qcrl")
    shutil.copyfile(code / "infra/stream/qcrl-stream-pilot.service", "/etc/systemd/system/qcrl-stream-pilot.service")
    # No environment file, timer, declaration or capture is installed here.
    if args.ssh_key:
        ssh = Path("/home/ec2-user/.ssh")
        ssh.mkdir(mode=0o700, exist_ok=True)
        shutil.chown(ssh, user="ec2-user", group="ec2-user")
        target = ssh / "authorized_keys"
        existing = target.read_text().splitlines() if target.exists() else []
        if args.ssh_key not in existing:
            with target.open("a") as handle:
                if existing:
                    handle.write("\n")
                handle.write(args.ssh_key + "\n")
        target.chmod(0o600)
        shutil.chown(target, user="ec2-user", group="ec2-user")
    hardening = Path("/etc/ssh/sshd_config.d/90-qcrl-replica.conf")
    with hardening.open("x") as handle:
        handle.write("PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\nPubkeyAuthentication yes\nAllowUsers ec2-user\n")
    subprocess.run(["sshd", "-t"], check=True)
    subprocess.run(["systemctl", "restart", "sshd"], check=True)
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(hours=args.runtime_hours)
    service, timer = stop_units(deadline)
    for name, content in (("qcrl-replica-stop.service", service), ("qcrl-replica-stop.timer", timer)):
        with (Path("/etc/systemd/system") / name).open("x") as handle:
            handle.write(content)
    revision = subprocess.check_output(["git", "-C", str(code), "rev-parse", "HEAD"], text=True).strip()
    clock = subprocess.run(["chronyc", "tracking"], capture_output=True, text=True, timeout=5)
    metadata = {"schema_version": "qcrl.replica_bootstrap.v1", "observer_label": args.label,
                "region": args.region, "bucket": args.bucket, "source_commit": revision,
                "bootstrapped_at_utc": now.isoformat(), "stop_at_utc": deadline.isoformat(),
                "clock_tracking": clock.stdout[:4096] if clock.returncode == 0 else None,
                "clock_tracking_returncode": clock.returncode, "orders_authorized": False}
    with (root / "replica-bootstrap.json").open("x") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
    subprocess.run(["systemd-analyze", "verify", "/etc/systemd/system/qcrl-stream-pilot.service",
                    "/etc/systemd/system/qcrl-replica-stop.timer"], check=True)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "--now", "qcrl-replica-stop.timer"], check=True)
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
