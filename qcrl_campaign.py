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
DEFAULT_SUBMISSION_POLICY = {
    "min_interval_seconds": 30.0,
    "max_rate_retries": 4,
    "initial_backoff_seconds": 30.0,
    "max_backoff_seconds": 300.0
}
RANKING_SCORE_MODELS = {
    "flat_profit_drawdown": {
        "required_fields": {"net_profit", "max_drawdown", "ruined"}
    },
    "martingale_recovery_risk": {
        "required_fields": {"risk_adjusted_score", "ruined"}
    }
}
PAIR_COMPARISON_FIELDS = {
    "net_profit", "win_rate", "trades", "max_drawdown",
    "max_single_wager", "max_recovery_depth", "max_loss_streak",
    "risk_adjusted_score", "ruined"
}
RESERVED_PARAMETERS = {"git_commit", "git_branch", "campaign_id"}
ENTRY_MODELS = {
    "fixed_bias", "previous_candle", "previous_candle_reverse",
    "candle_streak", "ema_trend", "macd_trend", "rsi_mean_reversion"
}
FILTER_MODELS = {"none", "ema_trend", "adx_strength", "atr_volatility"}
STAKE_MODES = {"flat", "martingale"}
ALLOWED_PARAMETERS = {
    "start_year", "start_month", "start_day",
    "end_year", "end_month", "end_day",
    "coin", "timeframe", "entry_model", "bias",
    "streak_length", "streak_mode", "stake_mode",
    "base_wager", "bankroll", "multiplier", "max_steps",
    "filter_model", "ema_fast", "ema_slow",
    "macd_fast", "macd_slow", "macd_signal",
    "rsi_period", "rsi_oversold", "rsi_overbought",
    "adx_period", "adx_threshold",
    "atr_period", "atr_min_pct", "atr_max_pct",
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
    submission_policy(manifest)
    validate_cohort_rankings(manifest)
    validate_pair_comparison(manifest)
    return manifest


def validate_cohort_rankings(manifest):
    rankings = manifest.get("cohort_rankings", [])
    if not isinstance(rankings, list):
        raise CampaignError("cohort_rankings must be an array")
    names = set()
    for ranking in rankings:
        if not isinstance(ranking, dict):
            raise CampaignError("Every cohort_rankings entry must be an object")
        name = str(ranking.get("name", "")).strip()
        if not name:
            raise CampaignError("Every cohort ranking requires a name")
        if name in names:
            raise CampaignError(f"Duplicate cohort ranking name: {name}")
        names.add(name)
        filters = ranking.get("filters", {})
        if not isinstance(filters, dict) or not filters:
            raise CampaignError(
                f"Cohort ranking {name} requires non-empty filters"
            )
        score_model = ranking.get("score_model")
        if score_model not in RANKING_SCORE_MODELS:
            raise CampaignError(
                f"Unknown score_model for {name}: {score_model}"
            )
        if ranking.get("direction", "max") not in {"max", "min"}:
            raise CampaignError(
                f"Cohort ranking {name} direction must be max or min"
            )
        display_fields = ranking.get("display_fields", [])
        if not isinstance(display_fields, list):
            raise CampaignError(
                f"Cohort ranking {name} display_fields must be an array"
            )


def validate_pair_comparison(manifest):
    comparison = manifest.get("pair_comparison")
    if comparison is None:
        return
    if not isinstance(comparison, dict):
        raise CampaignError("pair_comparison must be an object")
    validation = manifest.get("pair_validation")
    if not validation:
        raise CampaignError("pair_comparison requires pair_validation")
    expected = validation.get("expected_values", [])
    for field in [
        "baseline_value", "comparison_value", "label_field",
        "baseline_score_model", "comparison_score_model"
    ]:
        if field not in comparison:
            raise CampaignError(f"pair_comparison requires {field}")
    if comparison["baseline_value"] not in expected:
        raise CampaignError(
            "pair_comparison baseline_value must be an expected pair value"
        )
    if comparison["comparison_value"] not in expected:
        raise CampaignError(
            "pair_comparison comparison_value must be an expected pair value"
        )
    if comparison["baseline_value"] == comparison["comparison_value"]:
        raise CampaignError(
            "pair_comparison baseline and comparison values must differ"
        )
    for field in ["baseline_score_model", "comparison_score_model"]:
        if comparison[field] not in RANKING_SCORE_MODELS:
            raise CampaignError(
                f"pair_comparison {field} is not a known score model"
            )
    expected_labels = comparison.get("expected_labels")
    if expected_labels is not None:
        if not isinstance(expected_labels, list) or not expected_labels:
            raise CampaignError(
                "pair_comparison expected_labels must be a non-empty array"
            )
        if len(expected_labels) != len(set(expected_labels)):
            raise CampaignError(
                "pair_comparison expected_labels cannot contain duplicates"
            )


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
    entry_model = str(parameters.get("entry_model", "")).lower()
    filter_model = str(parameters.get("filter_model", "none")).lower()
    if entry_model not in ENTRY_MODELS:
        raise CampaignError(f"Unknown entry_model: {entry_model}")
    if filter_model not in FILTER_MODELS:
        raise CampaignError(f"Unknown filter_model: {filter_model}")
    stake_mode = str(parameters.get("stake_mode", "")).lower()
    if stake_mode not in STAKE_MODES:
        raise CampaignError(f"Unknown stake_mode: {stake_mode}")
    if entry_model == "fixed_bias" and str(
        parameters.get("bias", "")
    ).lower() not in {"up", "down"}:
        raise CampaignError("bias must be up or down")
    if entry_model == "candle_streak":
        if int(parameters.get("streak_length", 0)) < 1:
            raise CampaignError("streak_length must be positive")
        if str(parameters.get("streak_mode", "")).lower() not in {
            "follow", "reverse"
        }:
            raise CampaignError("streak_mode must be follow or reverse")
    if int(parameters.get("start_year", 0)) > int(
        parameters.get("end_year", 9999)
    ):
        raise CampaignError("start_year cannot be later than end_year")
    if parameters.get("filter_model") == "ema_trend":
        ema_fast = int(parameters.get("ema_fast", 0))
        ema_slow = int(parameters.get("ema_slow", 0))
        if min(ema_fast, ema_slow) < 1 or ema_fast >= ema_slow:
            raise CampaignError("ema_fast must be less than ema_slow")
    if parameters.get("entry_model") == "ema_trend":
        ema_fast = int(parameters.get("ema_fast", 0))
        ema_slow = int(parameters.get("ema_slow", 0))
        if min(ema_fast, ema_slow) < 1 or ema_fast >= ema_slow:
            raise CampaignError("ema_fast must be less than ema_slow")
    if parameters.get("entry_model") == "macd_trend":
        macd_fast = int(parameters.get("macd_fast", 0))
        macd_slow = int(parameters.get("macd_slow", 0))
        if min(macd_fast, macd_slow) < 1 or macd_fast >= macd_slow:
            raise CampaignError("macd_fast must be less than macd_slow")
        if int(parameters.get("macd_signal", 0)) < 1:
            raise CampaignError("macd_signal must be positive")
    if parameters.get("entry_model") == "rsi_mean_reversion":
        if int(parameters.get("rsi_period", 0)) < 1:
            raise CampaignError("rsi_period must be positive")
        oversold = float(parameters.get("rsi_oversold", -1))
        overbought = float(parameters.get("rsi_overbought", 101))
        if not 0 <= oversold < overbought <= 100:
            raise CampaignError(
                "RSI thresholds must satisfy "
                "0 <= rsi_oversold < rsi_overbought <= 100"
            )
    if parameters.get("filter_model") == "adx_strength":
        if int(parameters.get("adx_period", 0)) < 2:
            raise CampaignError("adx_period must be at least 2")
        if not 0 <= float(parameters.get("adx_threshold", -1)) <= 100:
            raise CampaignError("adx_threshold must be between 0 and 100")
    if parameters.get("filter_model") == "atr_volatility":
        minimum = float(parameters.get("atr_min_pct", -1))
        maximum = float(parameters.get("atr_max_pct", -1))
        if int(parameters.get("atr_period", 0)) < 1:
            raise CampaignError("atr_period must be positive")
        if minimum < 0 or maximum <= minimum:
            raise CampaignError(
                "ATR thresholds must satisfy "
                "0 <= atr_min_pct < atr_max_pct"
            )
    if float(parameters.get("base_wager", 1)) <= 0:
        raise CampaignError("base_wager must be positive")
    if float(parameters.get("bankroll", 1)) <= 0:
        raise CampaignError("bankroll must be positive")
    if stake_mode == "martingale":
        if float(parameters.get("multiplier", 0)) <= 1:
            raise CampaignError("martingale multiplier must be greater than 1")
        if int(parameters.get("max_steps", 0)) < 1:
            raise CampaignError("martingale max_steps must be positive")


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


def case_set_hash(cases):
    identity = [
        {
            "case_id": case["case_id"],
            "parameter_hash": case["parameter_hash"]
        }
        for case in sorted(cases, key=lambda item: item["case_id"])
    ]
    return canonical_hash(identity)


def state_case_set_hash(state):
    identity = [
        {
            "case_id": run["case_id"],
            "parameter_hash": run["parameter_hash"]
        }
        for run in sorted(
            state.get("runs", {}).values(),
            key=lambda item: item["case_id"]
        )
    ]
    return canonical_hash(identity)


def load_state(manifest, cases):
    path = state_path(manifest)
    manifest_hash = canonical_hash(manifest)
    expected_case_set_hash = case_set_hash(cases)
    if path.exists():
        state = read_json(path)
        stored_case_set_hash = state.get(
            "case_set_hash",
            state_case_set_hash(state)
        )
        if stored_case_set_hash != expected_case_set_hash:
            raise CampaignError(
                "Campaign cases changed after state was created. "
                "Use a new campaign_id for a different parameter set."
            )
        if state.get("manifest_hash") != manifest_hash:
            state.setdefault("manifest_revisions", []).append({
                "previous_manifest_hash": state.get("manifest_hash"),
                "manifest_hash": manifest_hash,
                "case_set_hash": expected_case_set_hash,
                "accepted_at_utc": utc_now(),
                "reason": "analysis_or_operational_configuration_changed"
            })
            state["manifest_hash"] = manifest_hash
        state["case_set_hash"] = expected_case_set_hash
    else:
        state = {
            "schema_version": STATE_VERSION,
            "campaign_id": manifest["campaign_id"],
            "manifest_hash": manifest_hash,
            "case_set_hash": expected_case_set_hash,
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


def submission_policy(
    manifest,
    min_interval_seconds=None,
    max_rate_retries=None
):
    configured = manifest.get("submission_policy", {})
    if not isinstance(configured, dict):
        raise CampaignError("submission_policy must be an object")
    unknown = set(configured) - set(DEFAULT_SUBMISSION_POLICY)
    if unknown:
        raise CampaignError(
            "Unknown submission_policy fields: " + ", ".join(sorted(unknown))
        )
    policy = dict(DEFAULT_SUBMISSION_POLICY)
    policy.update(configured)
    if min_interval_seconds is not None:
        policy["min_interval_seconds"] = min_interval_seconds
    if max_rate_retries is not None:
        policy["max_rate_retries"] = max_rate_retries

    numeric_fields = [
        "min_interval_seconds",
        "initial_backoff_seconds",
        "max_backoff_seconds"
    ]
    for field in numeric_fields:
        try:
            policy[field] = float(policy[field])
        except (TypeError, ValueError) as exc:
            raise CampaignError(f"submission_policy.{field} must be numeric") from exc
        if policy[field] < 0:
            raise CampaignError(
                f"submission_policy.{field} cannot be negative"
            )
    try:
        policy["max_rate_retries"] = int(policy["max_rate_retries"])
    except (TypeError, ValueError) as exc:
        raise CampaignError(
            "submission_policy.max_rate_retries must be an integer"
        ) from exc
    if policy["max_rate_retries"] < 0:
        raise CampaignError(
            "submission_policy.max_rate_retries cannot be negative"
        )
    if policy["max_backoff_seconds"] < policy["initial_backoff_seconds"]:
        raise CampaignError(
            "submission_policy.max_backoff_seconds cannot be less than "
            "initial_backoff_seconds"
        )
    return policy


def rate_limit_detected(output):
    normalized = str(output).lower()
    signals = [
        "too many backtest requests",
        "please slow down",
        "too many requests",
        "rate limit",
        "http error 429"
    ]
    return any(signal in normalized for signal in signals)


def rate_backoff_seconds(policy, retry_number):
    delay = policy["initial_backoff_seconds"] * (2 ** retry_number)
    return min(delay, policy["max_backoff_seconds"])


def submission_wait_seconds(last_started, now, minimum_interval):
    if last_started is None:
        return 0.0
    return max(0.0, float(minimum_interval) - (float(now) - last_started))


def wait_before_submission(last_started, policy):
    wait_seconds = submission_wait_seconds(
        last_started,
        time.monotonic(),
        policy["min_interval_seconds"]
    )
    if wait_seconds > 0:
        print(
            f"Submission throttle: waiting {wait_seconds:.1f}s before "
            "the next QuantConnect request.",
            flush=True
        )
        time.sleep(wait_seconds)


def execute_backtest(command):
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
    return process.wait(), "".join(output_lines)


def required_metric_fields(manifest):
    fields = {"run_id"}
    objective = manifest.get("objective")
    if objective:
        fields.add(objective["field"])
    pair = manifest.get("pair_validation")
    if pair:
        fields.update(pair.get("invariants", []))
    for ranking in manifest.get("cohort_rankings", []):
        model = RANKING_SCORE_MODELS[ranking["score_model"]]
        fields.update(model["required_fields"])
        fields.update(ranking.get("display_fields", []))
    if manifest.get("pair_comparison"):
        fields.update(PAIR_COMPARISON_FIELDS)
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


def run_campaign(
    manifest,
    cases,
    execute=False,
    limit=None,
    retry_failed=False,
    min_interval_seconds=None,
    max_rate_retries=None
):
    if not execute:
        print_plan(manifest, cases)
        print("\nDry run only. Add --execute to submit cloud backtests.")
        return 0

    require_clean_tree()
    git_commit = git_value("rev-parse", "HEAD")
    git_branch = git_value("branch", "--show-current") or "detached"
    policy = submission_policy(
        manifest,
        min_interval_seconds=min_interval_seconds,
        max_rate_retries=max_rate_retries
    )
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
    last_submission_started = None
    for index, case in enumerate(selected, 1):
        run = state["runs"][case["case_id"]]
        run.update({
            "status": "running",
            "started_at_utc": utc_now(),
            "git_commit": git_commit,
            "git_branch": git_branch,
            "backtest_name": backtest_name(manifest, case),
            "submission_policy": policy
        })
        run.pop("error", None)
        run.pop("error_type", None)
        save_state(manifest, state)
        command = build_backtest_command(
            manifest, case, git_commit, git_branch
        )
        log_path = logs_dir / f"{case['case_id']}.log"
        rate_retry = 0

        while True:
            wait_before_submission(last_submission_started, policy)
            run["attempts"] = int(run.get("attempts", 0)) + 1
            attempt_number = run["attempts"]
            run["status"] = "running"
            run["attempt_started_at_utc"] = utc_now()
            save_state(manifest, state)
            print(
                f"\n[{index}/{len(selected)}] {case['case_id']} "
                f"(attempt {attempt_number})",
                flush=True
            )
            last_submission_started = time.monotonic()
            return_code, output = execute_backtest(command)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    f"\n===== attempt {attempt_number} | {utc_now()} =====\n"
                )
                handle.write(output)
            backtest_id, backtest_url = parse_backtest_reference(output)

            if (
                not backtest_id
                and rate_limit_detected(output)
                and rate_retry < policy["max_rate_retries"]
            ):
                backoff = rate_backoff_seconds(policy, rate_retry)
                rate_retry += 1
                event = {
                    "detected_at_utc": utc_now(),
                    "attempt": attempt_number,
                    "retry_number": rate_retry,
                    "backoff_seconds": backoff
                }
                run.setdefault("rate_limit_events", []).append(event)
                run["rate_limit_retries"] = int(
                    run.get("rate_limit_retries", 0)
                ) + 1
                run["status"] = "rate_limited"
                run["last_rate_limit_at_utc"] = event["detected_at_utc"]
                save_state(manifest, state)
                print(
                    "QuantConnect rate limit detected. "
                    f"Retry {rate_retry}/{policy['max_rate_retries']} in "
                    f"{backoff:.1f}s.",
                    flush=True
                )
                time.sleep(backoff)
                continue
            break

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
            if rate_limit_detected(output):
                run["error_type"] = "rate_limit_exhausted"
                run["error"] = (
                    "QuantConnect rate limit persisted after "
                    f"{policy['max_rate_retries']} automatic retries"
                )
            else:
                run["error_type"] = "lean_failure"
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


def cohort_matches(run, filters):
    for field, expected in filters.items():
        actual = run.get("parameters", {}).get(field)
        if actual is None:
            actual = run.get("metrics", {}).get(field)
        if actual != expected:
            return False
    return True


def cohort_score(score_model, run):
    metrics = run.get("metrics", {})
    required = RANKING_SCORE_MODELS[score_model]["required_fields"]
    if not required.issubset(metrics):
        return None
    if score_model == "flat_profit_drawdown":
        score = float(metrics["net_profit"]) / (
            1 + float(metrics["max_drawdown"])
        )
        if metrics["ruined"]:
            score -= 1000
        return score
    if score_model == "martingale_recovery_risk":
        return float(metrics["risk_adjusted_score"])
    raise CampaignError(f"Unsupported ranking score model: {score_model}")


def print_cohort_rankings(manifest, runs):
    rankings = manifest.get("cohort_rankings", [])
    for ranking in rankings:
        scored = []
        for run in runs:
            if not cohort_matches(run, ranking["filters"]):
                continue
            score = cohort_score(ranking["score_model"], run)
            if score is not None:
                scored.append((score, run))
        reverse = ranking.get("direction", "max") == "max"
        scored.sort(key=lambda item: item[0], reverse=reverse)
        print(
            f"\n{ranking['name']} — {ranking['score_model']} "
            f"({ranking.get('direction', 'max')}):"
        )
        if not scored:
            print("  No complete records for this cohort.")
            continue
        for position, (score, run) in enumerate(scored, 1):
            details = []
            for field in ranking.get("display_fields", []):
                value = run.get("metrics", {}).get(field)
                details.append(f"{field}={value}")
            suffix = " | " + " ".join(details) if details else ""
            print(
                f"  {position}. {run['case_id']} score={score:.12g}{suffix}"
            )


def safe_ratio(numerator, denominator):
    if numerator is None or denominator in {None, 0}:
        return None
    return float(numerator) / float(denominator)


def outcome_label(net_profit, ruined=False):
    if ruined:
        return "ruined"
    if net_profit > 0:
        return "positive"
    if net_profit < 0:
        return "negative"
    return "neutral"


def capital_transform_label(baseline_profit, comparison_profit, ruined):
    if ruined:
        return "capital-transform-ruined"
    if baseline_profit <= 0 < comparison_profit:
        return "recovery-dependent-profit"
    if baseline_profit > 0 and comparison_profit > baseline_profit:
        return "signal-supported-profit-amplification"
    if comparison_profit > baseline_profit:
        return "profit-amplification"
    return "no-profit-uplift"


def amplification_label(value, measure):
    if value is None:
        return f"{measure}-undefined"
    if value >= 32:
        level = "extreme"
    elif value >= 16:
        level = "high"
    elif value >= 5:
        level = "substantial"
    elif value >= 2:
        level = "elevated"
    elif value > 1:
        level = "moderate"
    else:
        level = "none"
    return f"{level}-{measure}-amplification"


def build_pair_comparisons(manifest, runs):
    config = manifest.get("pair_comparison")
    validation = manifest.get("pair_validation")
    if not config or not validation:
        return []

    dimension = validation["dimension"]
    group_by = validation["group_by"]
    invariants = validation.get("invariants", [])
    groups = {}
    for run in runs:
        key = tuple(run["parameters"].get(field) for field in group_by)
        groups.setdefault(key, {})[run["parameters"].get(dimension)] = run

    comparisons = []
    baseline_value = config["baseline_value"]
    comparison_value = config["comparison_value"]
    label_field = config["label_field"]
    for key, members in groups.items():
        if baseline_value not in members or comparison_value not in members:
            continue
        baseline = members[baseline_value]
        comparison = members[comparison_value]
        baseline_metrics = baseline.get("metrics", {})
        comparison_metrics = comparison.get("metrics", {})
        if not PAIR_COMPARISON_FIELDS.issubset(baseline_metrics):
            continue
        if not PAIR_COMPARISON_FIELDS.issubset(comparison_metrics):
            continue

        baseline_profit = baseline_metrics["net_profit"]
        comparison_profit = comparison_metrics["net_profit"]
        drawdown_amplification = safe_ratio(
            comparison_metrics["max_drawdown"],
            baseline_metrics["max_drawdown"]
        )
        base_wager = comparison["parameters"].get("base_wager")
        wager_multiple = safe_ratio(
            comparison_metrics["max_single_wager"],
            base_wager
        )
        invariants_match = all(
            field in baseline_metrics
            and field in comparison_metrics
            and equal_metric(
                baseline_metrics[field], comparison_metrics[field]
            )
            for field in invariants
        )

        comparisons.append({
            "label": baseline["parameters"].get(label_field),
            "group": dict(zip(group_by, key)),
            "baseline_value": baseline_value,
            "comparison_value": comparison_value,
            "baseline_case_id": baseline["case_id"],
            "comparison_case_id": comparison["case_id"],
            "baseline_run_id": baseline_metrics.get("run_id"),
            "comparison_run_id": comparison_metrics.get("run_id"),
            "signal_invariants_match": invariants_match,
            "signal": {
                "trades": baseline_metrics["trades"],
                "win_rate": baseline_metrics["win_rate"],
                "max_loss_streak": baseline_metrics["max_loss_streak"]
            },
            "baseline": {
                "outcome": outcome_label(
                    baseline_profit, baseline_metrics["ruined"]
                ),
                "net_profit": baseline_profit,
                "max_drawdown": baseline_metrics["max_drawdown"],
                "max_single_wager": baseline_metrics["max_single_wager"],
                "base_wager": baseline["parameters"].get("base_wager"),
                "drawdown_in_base_wagers": safe_ratio(
                    baseline_metrics["max_drawdown"],
                    baseline["parameters"].get("base_wager")
                ),
                "score": cohort_score(
                    config["baseline_score_model"], baseline
                )
            },
            "comparison": {
                "outcome": outcome_label(
                    comparison_profit, comparison_metrics["ruined"]
                ),
                "net_profit": comparison_profit,
                "max_drawdown": comparison_metrics["max_drawdown"],
                "max_single_wager": comparison_metrics["max_single_wager"],
                "max_recovery_depth": comparison_metrics[
                    "max_recovery_depth"
                ],
                "score": cohort_score(
                    config["comparison_score_model"], comparison
                ),
                "ruined": comparison_metrics["ruined"]
            },
            "deltas": {
                "net_profit": comparison_profit - baseline_profit,
                "max_drawdown": (
                    comparison_metrics["max_drawdown"]
                    - baseline_metrics["max_drawdown"]
                ),
                "drawdown_amplification": drawdown_amplification,
                "max_wager_multiple_of_base": wager_multiple
            },
            "interpretation": {
                "capital_transform": capital_transform_label(
                    baseline_profit,
                    comparison_profit,
                    comparison_metrics["ruined"]
                ),
                "drawdown": amplification_label(
                    drawdown_amplification, "drawdown"
                ),
                "wager": amplification_label(wager_multiple, "wager")
            }
        })

    comparisons.sort(
        key=lambda item: (item["label"] is None, str(item["label"]))
    )
    return comparisons


def print_pair_comparisons(comparisons):
    if not comparisons:
        return
    print("\nPaired capital transformation:")
    for comparison in comparisons:
        deltas = comparison["deltas"]
        drawdown_multiple = deltas["drawdown_amplification"]
        wager_multiple = deltas["max_wager_multiple_of_base"]
        drawdown_text = (
            f"{drawdown_multiple:.2f}x"
            if drawdown_multiple is not None else "n/a"
        )
        wager_text = (
            f"{wager_multiple:.2f}x"
            if wager_multiple is not None else "n/a"
        )
        print(
            f"  {comparison['label']}: "
            f"flat={comparison['baseline']['net_profit']} "
            f"martingale={comparison['comparison']['net_profit']} "
            f"profit_delta={deltas['net_profit']:+g} "
            f"drawdown={drawdown_text} wager={wager_text} "
            f"recovery_depth={comparison['comparison']['max_recovery_depth']} "
            f"{comparison['interpretation']['capital_transform']}"
        )


def write_pair_comparison_artifact(manifest, state, comparisons, violations):
    if not manifest.get("pair_comparison"):
        return None
    artifact = {
        "schema_version": "qcrl.paired_comparison.v1",
        "campaign_id": manifest["campaign_id"],
        "case_set_hash": state["case_set_hash"],
        "generated_at_utc": utc_now(),
        "expected_labels": manifest["pair_comparison"].get(
            "expected_labels",
            [comparison["label"] for comparison in comparisons]
        ),
        "validation": {
            "pair_issue_count": len(violations),
            "valid": len(violations) == 0
        },
        "pairs": comparisons
    }
    path = state_path(manifest).parent / "paired_comparison.json"
    write_json(path, artifact)
    return path


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
    if manifest.get("cohort_rankings"):
        print_cohort_rankings(manifest, runs)
    elif objective:
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
    comparisons = build_pair_comparisons(manifest, runs)
    print_pair_comparisons(comparisons)
    artifact_path = write_pair_comparison_artifact(
        manifest, state, comparisons, violations
    )
    if artifact_path is not None:
        print(f"\nPaired comparison artifact: {artifact_path}")
    save_state(manifest, state)
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


def run_stability(manifest, cases):
    from discovery.stability_engine import StabilityEngine, StabilityError

    state = load_state(manifest, cases)
    paired_path = state_path(manifest).parent / "paired_comparison.json"
    if not paired_path.exists():
        raise CampaignError(
            "Paired comparison artifact is missing. Run campaign validate first."
        )
    paired_artifact = read_json(paired_path)
    if paired_artifact.get("case_set_hash") != state["case_set_hash"]:
        raise CampaignError(
            "Paired comparison case set does not match current campaign state. "
            "Run campaign validate again."
        )
    if not paired_artifact.get("validation", {}).get("valid"):
        raise CampaignError(
            "Paired comparison contains validation issues; stability aborted."
        )
    try:
        report = StabilityEngine().analyze(paired_artifact)
    except StabilityError as exc:
        raise CampaignError(f"Stability analysis failed: {exc}") from exc

    path = state_path(manifest).parent / "stability_report.json"
    write_json(path, report)
    coverage = report["coverage"]
    flat = report["flat_signal"]
    martingale = report["martingale_capital"]
    interpretation = report["comparative_interpretation"]
    gate = interpretation["advancement_gate"]
    print(f"Evidence status: {report['evidence_status']}")
    print(
        f"Coverage: {coverage['present_count']}/{coverage['expected_count']} "
        f"({coverage['coverage_ratio']:.0%})"
    )
    print(
        "Flat signal: "
        f"score={flat['final_score']:.2f} "
        f"classification={flat['classification']} "
        f"profitable={flat['profitable_years']}/{flat['run_count']} "
        f"mean_win_rate={flat['mean_win_rate']:.2%}"
    )
    print(
        "Martingale capital: "
        f"score={martingale['final_score']:.2f} "
        f"classification={martingale['classification']} "
        f"survival={martingale['survival_ratio']:.0%} "
        f"recovery_dependence={martingale['recovery_dependence_ratio']:.0%}"
    )
    print(
        "Comparative verdict: "
        f"decision={gate['decision']} "
        f"signal={interpretation['signal_stability']['disposition']} "
        f"capital={interpretation['capital_recovery_stability']['disposition']} "
        f"confidence={interpretation['evidence_confidence']['level']} "
        f"risk={interpretation['risk_amplification']['level']}"
    )
    print(f"Next action: {gate['next_action']}")
    print("Warnings:")
    for warning in report["warnings"]:
        print(f"  - {warning}")
    print(f"Stability artifact: {path}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["plan", "status", "collect", "validate", "stability"]:
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
    run_parser.add_argument(
        "--min-interval-seconds",
        type=float,
        help="Override the manifest delay between submission start times"
    )
    run_parser.add_argument(
        "--max-rate-retries",
        type=int,
        help="Override automatic QuantConnect rate-limit retries per case"
    )
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
                retry_failed=args.retry_failed,
                min_interval_seconds=args.min_interval_seconds,
                max_rate_retries=args.max_rate_retries
            )
        if args.command == "collect":
            return collect_campaign(manifest, cases)
        if args.command == "validate":
            return validate_campaign(manifest, cases)
        if args.command == "stability":
            return run_stability(manifest, cases)
        return show_status(manifest, cases)
    except CampaignError as exc:
        print(f"Campaign error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
