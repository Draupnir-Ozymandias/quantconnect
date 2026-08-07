#!/usr/bin/env python3
"""Run and validate QCRL parameter campaigns through QuantConnect Cloud."""

import argparse
import base64
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib import error, request


SCHEMA_VERSION = "qcrl.campaign.v1"
STATE_VERSION = "qcrl.campaign_state.v1"
API_BASE_URL = "https://www.quantconnect.com/api/v2"
RESERVED_PARAMETERS = {"git_commit", "git_branch", "campaign_id"}
ALLOWED_PARAMETERS = {
    "start_year", "start_month", "start_day",
    "end_year", "end_month", "end_day",
    "coin", "timeframe", "entry_model", "bias",
    "streak_length", "streak_mode", "stake_mode",
    "base_wager", "bankroll", "multiplier", "max_steps",
    "filter_model", "ema_fast", "ema_slow",
    "enable_plots", "plot_every_n_bars", "lab_version", "run_notes"
}
QCRL_STATISTICS = {
    "QCRL Run Id": "run_id",
    "QCRL Experiment Id": "experiment_id",
    "QCRL Report Key": "objectstore_report_key",
    "QCRL Net Profit": "net_profit",
    "QCRL Win Rate": "win_rate",
    "QCRL Trades": "trades",
    "QCRL Wins": "wins",
    "QCRL Losses": "losses",
    "QCRL Ruined": "ruined",
    "QCRL Max Drawdown": "max_drawdown",
    "QCRL Max Wager": "max_single_wager",
    "QCRL Max Win Streak": "max_win_streak",
    "QCRL Max Loss Streak": "max_loss_streak",
    "QCRL Max Recovery Depth": "max_recovery_depth",
    "QCRL Risk Adjusted Score": "risk_adjusted_score",
    "QCRL Tail Risk Score": "tail_risk_score",
    "QCRL Signals Generated": "signals_generated",
    "QCRL Signals Executed": "signals_executed",
    "QCRL Up Signals": "up_signals",
    "QCRL Down Signals": "down_signals",
    "QCRL Up Executed": "up_executed",
    "QCRL Down Executed": "down_executed"
}


class CampaignError(RuntimeError):
    pass


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def canonical_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def slug(value):
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value).strip())
    return text.strip("-").lower() or "case"


def read_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError(f"Cannot read JSON {path}: {exc}") from exc


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def load_manifest(path):
    manifest = read_json(path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CampaignError(
            f"Manifest schema_version must be {SCHEMA_VERSION}"
        )
    campaign_id = manifest.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise CampaignError("Manifest campaign_id must be a non-empty string")
    if not isinstance(manifest.get("base_parameters", {}), dict):
        raise CampaignError("base_parameters must be an object")
    if not isinstance(manifest.get("variants", [{}]), list):
        raise CampaignError("variants must be an array")
    if not isinstance(manifest.get("matrix", {}), dict):
        raise CampaignError("matrix must be an object")
    return manifest


def validate_parameters(parameters):
    unknown = set(parameters) - ALLOWED_PARAMETERS
    reserved = set(parameters) & RESERVED_PARAMETERS
    if reserved:
        raise CampaignError(
            "Manifest cannot override provenance parameters: "
            + ", ".join(sorted(reserved))
        )
    if unknown:
        raise CampaignError(
            "Unknown algorithm parameters: " + ", ".join(sorted(unknown))
        )
    if int(parameters.get("start_year", 0)) > int(
        parameters.get("end_year", 9999)
    ):
        raise CampaignError("start_year cannot be later than end_year")
    if parameters.get("filter_model") == "ema_trend":
        if int(parameters.get("ema_fast", 0)) >= int(
            parameters.get("ema_slow", 0)
        ):
            raise CampaignError("ema_fast must be less than ema_slow")
    if float(parameters.get("base_wager", 1)) <= 0:
        raise CampaignError("base_wager must be positive")
    if float(parameters.get("bankroll", 1)) <= 0:
        raise CampaignError("bankroll must be positive")


def expand_cases(manifest):
    base = manifest.get("base_parameters", {})
    variants = manifest.get("variants") or [{}]
    matrix = manifest.get("matrix", {})
    matrix_keys = sorted(matrix)
    matrix_values = []
    for key in matrix_keys:
        values = matrix[key]
        if not isinstance(values, list) or not values:
            raise CampaignError(f"matrix.{key} must be a non-empty array")
        matrix_values.append(values)

    combinations = itertools.product(*matrix_values) if matrix_keys else [()]
    combinations = list(combinations)
    cases = []
    seen_parameters = set()
    seen_case_ids = set()
    label_fields = manifest.get(
        "case_name_fields", ["start_year", "stake_mode"]
    )

    for variant in variants:
        if not isinstance(variant, dict):
            raise CampaignError("Every variants entry must be an object")
        for values in combinations:
            parameters = dict(base)
            parameters.update(variant)
            parameters.update(dict(zip(matrix_keys, values)))
            validate_parameters(parameters)
            parameter_hash = canonical_hash(parameters)
            if parameter_hash in seen_parameters:
                raise CampaignError("Campaign expands to duplicate parameter sets")
            seen_parameters.add(parameter_hash)

            labels = [str(parameters[field]) for field in label_fields if field in parameters]
            case_id = slug("-".join(labels) + "-" + parameter_hash[:8])
            if case_id in seen_case_ids:
                raise CampaignError(f"Duplicate generated case_id: {case_id}")
            seen_case_ids.add(case_id)
            cases.append({
                "case_id": case_id,
                "parameter_hash": parameter_hash,
                "parameters": parameters
            })
    return cases


def project_root():
    return Path(__file__).resolve().parent


def cloud_project_id(manifest):
    if "project_id" in manifest:
        return int(manifest["project_id"])
    return int(read_json(project_root() / "config.json")["cloud-id"])


def git_value(*arguments):
    result = subprocess.run(
        ["git", "-C", str(project_root()), *arguments],
        check=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def require_clean_tree():
    if git_value("status", "--porcelain"):
        raise CampaignError(
            "Campaign execution requires a clean Git tree. Commit changes first."
        )


def state_path(manifest):
    return (
        project_root() / ".qcrl" / "campaigns"
        / slug(manifest["campaign_id"]) / "state.json"
    )


def load_state(manifest, cases):
    path = state_path(manifest)
    manifest_hash = canonical_hash(manifest)
    if path.exists():
        state = read_json(path)
        if state.get("manifest_hash") != manifest_hash:
            raise CampaignError(
                "Manifest changed after campaign state was created. "
                "Use a new campaign_id or archive the old local state."
            )
    else:
        state = {
            "schema_version": STATE_VERSION,
            "campaign_id": manifest["campaign_id"],
            "manifest_hash": manifest_hash,
            "created_at_utc": utc_now(),
            "updated_at_utc": utc_now(),
            "runs": {}
        }
    for case in cases:
        state["runs"].setdefault(case["case_id"], {
            "case_id": case["case_id"],
            "parameter_hash": case["parameter_hash"],
            "parameters": case["parameters"],
            "status": "pending",
            "attempts": 0
        })
    normalize_collection_status(manifest, state)
    return state


def save_state(manifest, state):
    state["updated_at_utc"] = utc_now()
    write_json(state_path(manifest), state)


def backtest_name(manifest, case):
    prefix = manifest.get("backtest_name_prefix", manifest["campaign_id"])
    return f"{slug(prefix)}--{case['case_id']}"[:120]


def build_backtest_command(manifest, case, git_commit, git_branch):
    command = [
        "lean", "cloud", "backtest", str(cloud_project_id(manifest)),
        "--name", backtest_name(manifest, case),
        "--parameter", "git_commit", git_commit,
        "--parameter", "git_branch", git_branch,
        "--parameter", "campaign_id", manifest["campaign_id"]
    ]
    for key in sorted(case["parameters"]):
        command.extend([
            "--parameter", key, str(case["parameters"][key]).lower()
            if isinstance(case["parameters"][key], bool)
            else str(case["parameters"][key])
        ])
    return command


def parse_backtest_reference(output):
    url_match = re.search(
        r"https://www\.quantconnect\.com/project/(\d+)/([A-Za-z0-9-]+)",
        output
    )
    if url_match:
        return url_match.group(2), url_match.group(0)
    id_match = re.search(
        r"(?:backtest(?:\s+id)?|backtestId)\s*[:=]\s*([A-Za-z0-9-]{16,})",
        output,
        re.IGNORECASE
    )
    if id_match:
        backtest_id = id_match.group(1)
        url = (
            f"https://www.quantconnect.com/project/"
            f"{cloud_project_id_from_output(output)}/{backtest_id}"
        ) if cloud_project_id_from_output(output) else None
        return backtest_id, url
    return None, None


def cloud_project_id_from_output(output):
    match = re.search(r"quantconnect\.com/project/(\d+)/", output)
    return match.group(1) if match else None


def parse_scalar(value):
    if not isinstance(value, str):
        return value
    text = value.strip().strip("│|").strip()
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"none", "null", ""}:
        return None
    is_percent = text.endswith("%")
    numeric = text[:-1] if is_percent else text
    numeric = numeric.replace(",", "").replace("$", "")
    try:
        number = float(numeric)
        if number.is_integer() and not is_percent:
            return int(number)
        return number / 100 if is_percent else number
    except ValueError:
        return text


def extract_qcrl_metrics(payload):
    metrics = {}

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in QCRL_STATISTICS:
                    metrics[QCRL_STATISTICS[key]] = parse_scalar(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return metrics


def parse_cli_metrics(output):
    metrics = {}
    for line in output.splitlines():
        for label, field in QCRL_STATISTICS.items():
            position = line.find(label)
            if position < 0:
                continue
            remainder = line[position + len(label):]
            remainder = re.sub(r"^[\s:│|=]+", "", remainder)
            remainder = re.split(r"[│|]", remainder, maxsplit=1)[0].strip()
            if remainder:
                metrics[field] = parse_scalar(remainder)
    return metrics


def required_metric_fields(manifest):
    fields = {"run_id"}
    objective = manifest.get("objective")
    if objective:
        fields.add(objective["field"])
    pair = manifest.get("pair_validation")
    if pair:
        fields.update(pair.get("invariants", []))
    return fields


def missing_metric_fields(manifest, metrics):
    return sorted(required_metric_fields(manifest) - set(metrics or {}))


def normalize_collection_status(manifest, state):
    for run in state.get("runs", {}).values():
        if run.get("status") == "collected":
            missing = missing_metric_fields(manifest, run.get("metrics", {}))
            if missing:
                run["status"] = "completed"
                run["collection_error"] = (
                    "Missing required QCRL metrics: " + ", ".join(missing)
                )


def api_headers():
    user_id = os.environ.get("QC_USER_ID")
    api_token = os.environ.get("QC_API_TOKEN")
    if not user_id or not api_token:
        raise CampaignError(
            "Set QC_USER_ID and QC_API_TOKEN to collect cloud backtest results."
        )
    timestamp = str(int(time.time()))
    token_hash = hashlib.sha256(
        f"{api_token}:{timestamp}".encode("utf-8")
    ).hexdigest()
    encoded = base64.b64encode(
        f"{user_id}:{token_hash}".encode("utf-8")
    ).decode("ascii")
    return {
        "Authorization": f"Basic {encoded}",
        "Timestamp": timestamp,
        "Content-Type": "application/json"
    }


def read_backtest(project_id, backtest_id):
    payload = json.dumps({
        "projectId": int(project_id),
        "backtestId": backtest_id
    }).encode("utf-8")
    api_request = request.Request(
        f"{API_BASE_URL}/backtests/read",
        data=payload,
        headers=api_headers(),
        method="POST"
    )
    try:
        with request.urlopen(api_request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (error.URLError, json.JSONDecodeError) as exc:
        raise CampaignError(f"QuantConnect API read failed: {exc}") from exc
    if not result.get("success"):
        raise CampaignError(
            "QuantConnect API rejected the read: "
            + "; ".join(result.get("errors", ["unknown error"]))
        )
    return result


def print_plan(manifest, cases):
    print(f"Campaign: {manifest['campaign_id']}")
    print(f"Project:  {cloud_project_id(manifest)}")
    print(f"Cases:    {len(cases)}")
    for case in cases:
        parameters = " ".join(
            f"{key}={value}" for key, value in sorted(case["parameters"].items())
        )
        print(f"  {case['case_id']}: {parameters}")


def run_campaign(manifest, cases, execute=False, limit=None, retry_failed=False):
    if not execute:
        print_plan(manifest, cases)
        print("\nDry run only. Add --execute to submit cloud backtests.")
        return 0

    require_clean_tree()
    git_commit = git_value("rev-parse", "HEAD")
    git_branch = git_value("branch", "--show-current") or "detached"
    state = load_state(manifest, cases)
    selected = []
    for case in cases:
        run = state["runs"][case["case_id"]]
        if run["status"] in {"completed", "collected"}:
            continue
        if run["status"] == "failed" and not retry_failed:
            continue
        selected.append(case)
    if limit is not None:
        selected = selected[:limit]
    if not selected:
        print("No eligible campaign cases remain.")
        return 0

    logs_dir = state_path(manifest).parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    for index, case in enumerate(selected, 1):
        run = state["runs"][case["case_id"]]
        run.update({
            "status": "running",
            "attempts": int(run.get("attempts", 0)) + 1,
            "started_at_utc": utc_now(),
            "git_commit": git_commit,
            "git_branch": git_branch,
            "backtest_name": backtest_name(manifest, case)
        })
        save_state(manifest, state)
        command = build_backtest_command(
            manifest, case, git_commit, git_branch
        )
        print(f"\n[{index}/{len(selected)}] {case['case_id']}", flush=True)
        process = subprocess.Popen(
            command,
            cwd=str(project_root().parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        output_lines = []
        for line in process.stdout:
            print(line, end="", flush=True)
            output_lines.append(line)
        return_code = process.wait()
        output = "".join(output_lines)
        log_path = logs_dir / f"{case['case_id']}.log"
        log_path.write_text(output, encoding="utf-8")
        backtest_id, backtest_url = parse_backtest_reference(output)
        run.update({
            "finished_at_utc": utc_now(),
            "return_code": return_code,
            "backtest_id": backtest_id,
            "backtest_url": backtest_url,
            "log_path": str(log_path.relative_to(project_root()))
        })
        cli_metrics = parse_cli_metrics(output)
        if cli_metrics:
            run["metrics"] = cli_metrics
        if return_code == 0 and backtest_id:
            missing = missing_metric_fields(manifest, cli_metrics)
            if missing:
                run["status"] = "completed"
                run["collection_error"] = (
                    "Awaiting API collection; terminal table omitted: "
                    + ", ".join(missing)
                )
            else:
                run["status"] = "collected"
        else:
            run["status"] = "failed"
            run["error"] = (
                f"LEAN exited with {return_code}"
                if return_code else "Backtest ID was not found in LEAN output"
            )
        save_state(manifest, state)
        if run["status"] == "failed":
            print(f"Campaign stopped: {run['error']}", file=sys.stderr)
            return 1
    return 0


def collect_campaign(manifest, cases):
    state = load_state(manifest, cases)
    project_id = cloud_project_id(manifest)
    collected = 0
    for case in cases:
        run = state["runs"][case["case_id"]]
        backtest_id = run.get("backtest_id")
        if not backtest_id or run.get("status") == "failed":
            continue
        payload = read_backtest(project_id, backtest_id)
        metrics = extract_qcrl_metrics(payload)
        if not metrics:
            run["collection_error"] = "No QCRL summary statistics found"
            continue
        run["metrics"] = metrics
        missing = missing_metric_fields(manifest, metrics)
        run["status"] = "completed" if missing else "collected"
        run["collected_at_utc"] = utc_now()
        if missing:
            run["collection_error"] = (
                "API result lacks required QCRL metrics: " + ", ".join(missing)
            )
        else:
            run.pop("collection_error", None)
            collected += 1
        save_state(manifest, state)
        print(f"Collected {case['case_id']}: {len(metrics)} QCRL metrics")
    save_state(manifest, state)
    print(f"Collected results for {collected} case(s).")
    return 0


def equal_metric(first, second):
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        return abs(float(first) - float(second)) <= 1e-9
    return first == second


def validate_campaign(manifest, cases):
    state = load_state(manifest, cases)
    runs = [state["runs"][case["case_id"]] for case in cases]
    failed = [run["case_id"] for run in runs if run["status"] == "failed"]
    incomplete = [
        run["case_id"] for run in runs
        if run["status"] not in {"completed", "collected"}
    ]
    uncollected = [
        run["case_id"] for run in runs
        if run["status"] == "completed"
    ]
    violations = []
    pair = manifest.get("pair_validation")
    if pair:
        dimension = pair["dimension"]
        expected = pair["expected_values"]
        group_by = pair["group_by"]
        invariants = pair.get("invariants", [])
        groups = {}
        for run in runs:
            key = tuple(run["parameters"].get(field) for field in group_by)
            groups.setdefault(key, {})[run["parameters"].get(dimension)] = run
        for key, members in groups.items():
            missing = [value for value in expected if value not in members]
            if missing:
                violations.append(f"pair {key} missing {missing}")
                continue
            baseline = members[expected[0]].get("metrics", {})
            for value in expected[1:]:
                compared = members[value].get("metrics", {})
                for field in invariants:
                    if field not in baseline or field not in compared:
                        violations.append(f"pair {key} lacks invariant {field}")
                    elif not equal_metric(baseline[field], compared[field]):
                        violations.append(
                            f"pair {key} differs on {field}: "
                            f"{baseline[field]} != {compared[field]}"
                        )

    print(f"Expected cases: {len(cases)}")
    print(f"Failed:         {len(failed)}")
    print(f"Incomplete:     {len(incomplete)}")
    print(f"Uncollected:    {len(uncollected)}")
    print(f"Pair issues:    {len(violations)}")
    for violation in violations:
        print(f"  - {violation}")

    objective = manifest.get("objective")
    if objective:
        field = objective["field"]
        reverse = objective.get("direction", "max") == "max"
        ranked = [
            run for run in runs if field in run.get("metrics", {})
        ]
        ranked.sort(key=lambda run: run["metrics"][field], reverse=reverse)
        if ranked:
            print(f"\nRanking by {field} ({objective.get('direction', 'max')}):")
            for position, run in enumerate(ranked, 1):
                print(
                    f"  {position}. {run['case_id']} "
                    f"{run['metrics'][field]}"
                )
    return 1 if failed or incomplete or uncollected or violations else 0


def show_status(manifest, cases):
    state = load_state(manifest, cases)
    counts = {}
    for run in state["runs"].values():
        counts[run["status"]] = counts.get(run["status"], 0) + 1
    print(f"Campaign: {manifest['campaign_id']}")
    print(f"State:    {state_path(manifest)}")
    for status in sorted(counts):
        print(f"{status:10} {counts[status]}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["plan", "status", "collect", "validate"]:
        child = subparsers.add_parser(command)
        child.add_argument("manifest", type=Path)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument(
        "--execute", action="store_true",
        help="Submit cloud backtests; without this flag run is a dry run"
    )
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--retry-failed", action="store_true")
    return parser


def main(arguments=None):
    args = build_parser().parse_args(arguments)
    try:
        manifest = load_manifest(args.manifest.resolve())
        cases = expand_cases(manifest)
        if args.command == "plan":
            print_plan(manifest, cases)
            return 0
        if args.command == "run":
            return run_campaign(
                manifest,
                cases,
                execute=args.execute,
                limit=args.limit,
                retry_failed=args.retry_failed
            )
        if args.command == "collect":
            return collect_campaign(manifest, cases)
        if args.command == "validate":
            return validate_campaign(manifest, cases)
        return show_status(manifest, cases)
    except CampaignError as exc:
        print(f"Campaign error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
