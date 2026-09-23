"""Generate inert per-phase launchd jobs from one locked QCRL protocol."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import plistlib
import re
import sys


PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from execution_truth import validate_capture_protocol  # noqa: E402
from execution_truth.contracts import ContractError  # noqa: E402


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def generate_capture_jobs(protocol_path, output_directory, python_executable,
                          now=None):
    """Write deterministic, unique, one-date launchd job declarations."""
    protocol_path = Path(protocol_path).resolve()
    protocol = validate_capture_protocol(json.loads(
        protocol_path.read_text(encoding="utf-8")
    ))
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    python_executable = Path(python_executable).resolve()
    if not python_executable.is_absolute() or not python_executable.exists():
        raise ContractError("python executable must be an existing absolute path")
    if any(_time(item["scheduled_at_utc"]) <= now for item in protocol["captures"]):
        raise ContractError("launchd jobs must be generated before every capture target")

    output_directory = Path(output_directory).resolve() / protocol["protocol_id"]
    log_directory = output_directory / "logs"
    output_directory.mkdir(parents=True, exist_ok=True)
    log_directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for capture in protocol["captures"]:
        capture_id = capture["capture_id"]
        label_suffix = re.sub(r"[^a-z0-9-]", "-", protocol["protocol_id"])
        label = f"com.qcrl.capture.{label_suffix}.{capture_id}"
        local = _time(capture["scheduled_at_utc"]).astimezone()
        job = {
            "Label": label,
            "ProcessType": "Background",
            "ProgramArguments": [
                "/usr/bin/caffeinate",
                "-dimsu",
                str(python_executable),
                str(PROJECT_DIR / "qcrl_execution_truth.py"),
                "protocol-capture-retry",
                str(protocol_path),
                capture_id,
                "--max-attempts", "4",
                "--initial-backoff-seconds", "5",
                "--max-backoff-seconds", "30",
                "--execute",
            ],
            "WorkingDirectory": str(PROJECT_DIR),
            "EnvironmentVariables": {"PYTHONDONTWRITEBYTECODE": "1"},
            "StartCalendarInterval": {
                "Year": local.year,
                "Month": local.month,
                "Day": local.day,
                "Hour": local.hour,
                "Minute": local.minute,
            },
            "StandardOutPath": str(log_directory / f"{capture_id}.stdout.log"),
            "StandardErrorPath": str(log_directory / f"{capture_id}.stderr.log"),
        }
        target = output_directory / f"{label}.plist"
        content = plistlib.dumps(job, fmt=plistlib.FMT_XML, sort_keys=True)
        if target.exists() and target.read_bytes() != content:
            raise ContractError(f"launchd declaration already differs: {target}")
        if not target.exists():
            target.write_bytes(content)
        paths.append(target)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol")
    parser.add_argument(
        "--output-directory",
        default=PROJECT_DIR / ".qcrl" / "launchd",
        type=Path,
    )
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    for path in generate_capture_jobs(
        args.protocol, args.output_directory, args.python
    ):
        print(path)


if __name__ == "__main__":
    main()
