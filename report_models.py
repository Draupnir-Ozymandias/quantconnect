# region imports
from AlgorithmImports import *
# endregion

# Research Report Models
# ======================
# Builds full experiment reports and normalized experiment records.

import hashlib
import json
import uuid
from datetime import datetime


class ResearchReport:
    REPORT_SCHEMA_VERSION = "qcrl.research_report.v2"
    RECORD_SCHEMA_VERSION = "qcrl.experiment_record.v1"

    REPORT_PREFIX = "qcrl/v2/experiments"
    RECORD_PREFIX = "qcrl/v2/records"
    LEGACY_REPORT_PREFIX = "qcrl/results"

    @staticmethod
    def utc_now_iso():
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    @staticmethod
    def utc_now_slug():
        return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def safe_text(value):
        if value is None:
            return "none"

        text = str(value).strip()

        if text == "":
            return "none"

        allowed = []
        for ch in text:
            if ch.isalnum() or ch in ["-", "_", "."]:
                allowed.append(ch)
            else:
                allowed.append("-")

        return "".join(allowed)

    @staticmethod
    def build_run_id(algo):
        timestamp = ResearchReport.utc_now_slug()
        suffix = uuid.uuid4().hex[:12]

        parts = [
            ResearchReport.safe_text(getattr(algo, "coin", "coin")),
            ResearchReport.safe_text(getattr(algo, "timeframe", "tf")),
            ResearchReport.safe_text(getattr(algo, "entry_model_name", "entry")),
            ResearchReport.safe_text(getattr(algo, "stake_mode", "stake")),
            timestamp,
            suffix
        ]

        return "_".join(parts)

    @staticmethod
    def parse_tags(value):
        if value is None:
            return []

        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip() != ""]

        text = str(value).strip()

        if text == "":
            return []

        return [part.strip() for part in text.split(",") if part.strip() != ""]

    @staticmethod
    def build(algo):
        risk = algo.risk
        stats = algo.stats

        net_profit = risk.net_profit()
        max_drawdown = risk.max_drawdown
        max_recovery_depth = risk.max_recovery_depth()

        survival_score = 1 if not risk.ruined else 0

        risk_adjusted_score = (
            net_profit
            / (1 + max_drawdown)
            / (1 + max_recovery_depth)
        )

        if risk.ruined:
            risk_adjusted_score -= 1000

        tail_risk_score = ResearchReport.tail_risk_score(
            risk.loss_streak_histogram
        )

        run_id = ResearchReport.build_run_id(algo)
        generated_at_utc = ResearchReport.utc_now_iso()

        start = (
            f"{int(algo.start_year):04d}-"
            f"{int(algo.start_month):02d}-"
            f"{int(algo.start_day):02d}"
        )

        end = (
            f"{int(algo.end_year):04d}-"
            f"{int(algo.end_month):02d}-"
            f"{int(algo.end_day):02d}"
        )

        return {
            "metadata": {
                "schema_version": ResearchReport.REPORT_SCHEMA_VERSION,
                "record_schema_version": ResearchReport.RECORD_SCHEMA_VERSION,
                "run_id": run_id,
                "generated_at_utc": generated_at_utc,
                "completed_at_algorithm_time": str(getattr(algo, "Time", None)),
                "algorithm_name": algo.__class__.__name__,
                "engine_version": getattr(algo, "engine_version", "qcrl.v2"),
                "experiment_group": getattr(algo, "experiment_group", "default"),
                "experiment_name": getattr(algo, "experiment_name", ""),
                "experiment_tags": ResearchReport.parse_tags(
                    getattr(algo, "experiment_tags", [])
                )
            },

            "configuration": {
                "coin": algo.coin,
                "timeframe": algo.timeframe,
                "entry_model": algo.entry_model_name,
                "filter_model": algo.filter_model.name(),
                "stake_mode": algo.stake_mode,
                "streak_length": algo.streak_length,
                "streak_mode": algo.streak_mode,
                "ema_fast": algo.ema_fast,
                "ema_slow": algo.ema_slow,
                "base_wager": algo.base_wager,
                "bankroll": algo.initial_bankroll,
                "multiplier": algo.multiplier,
                "max_steps": algo.max_steps,
                "start": start,
                "end": end
            },

            "performance": {
                "initial_bankroll": risk.initial_bankroll,
                "final_bankroll": risk.bankroll,
                "net_profit": net_profit,
                "trades": risk.trades,
                "wins": risk.wins,
                "losses": risk.losses,
                "win_rate": risk.win_rate()
            },

            "risk": {
                "ruined": risk.ruined,
                "ruin_time": str(risk.ruin_time),
                "ruin_reason": risk.ruin_reason,
                "max_drawdown": max_drawdown,
                "max_single_wager": risk.max_single_wager,
                "max_win_streak": risk.max_win_streak,
                "max_loss_streak": risk.max_loss_streak,
                "average_recovery_depth": risk.average_recovery_depth(),
                "max_recovery_depth": max_recovery_depth,
                "win_streak_histogram": risk.win_streak_histogram,
                "loss_streak_histogram": risk.loss_streak_histogram
            },

            "analytics": {
                "bars_seen": stats.bars_seen,
                "signals_generated": stats.signals_generated,
                "signals_executed": stats.signals_executed,
                "execution_rate": stats.execution_rate(),
                "filter_rate": stats.filter_rate(),
                "skipped_no_direction": stats.signals_skipped_no_direction,
                "skipped_filter_not_ready": stats.signals_skipped_filter_not_ready,
                "skipped_filter_rejected": stats.signals_skipped_filter_rejected,
                "skipped_tie": stats.signals_skipped_tie,
                "skipped_ruined": stats.signals_skipped_ruined,
                "up_signals": stats.up_signals,
                "down_signals": stats.down_signals,
                "up_executed": stats.up_executed,
                "down_executed": stats.down_executed,
                "executed_wins": stats.executed_wins,
                "executed_losses": stats.executed_losses,
                "executed_win_rate": stats.executed_win_rate(),
                "total_wagered": stats.total_wagered,
                "average_wager": stats.average_wager(),
                "recovery_level_counts": stats.recovery_level_counts,
                "regime_stats": stats.regime_stats
            },

            "scores": {
                "survival_score": survival_score,
                "risk_adjusted_score": risk_adjusted_score,
                "tail_risk_score": tail_risk_score
            }
        }

    @staticmethod
    def legacy_run_id(report):
        raw = ResearchReport.compact_json(report)
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]

        c = report.get("configuration", {})
        parts = [
            "legacy",
            ResearchReport.safe_text(c.get("coin", "coin")),
            ResearchReport.safe_text(c.get("timeframe", "tf")),
            digest
        ]

        return "_".join(parts)

    @staticmethod
    def get_metadata(report):
        metadata = report.get("metadata", {})

        if metadata is None:
            metadata = {}

        if "run_id" not in metadata or metadata.get("run_id") in [None, ""]:
            metadata["run_id"] = ResearchReport.legacy_run_id(report)

        if "schema_version" not in metadata:
            metadata["schema_version"] = "qcrl.research_report.legacy"

        if "record_schema_version" not in metadata:
            metadata["record_schema_version"] = ResearchReport.RECORD_SCHEMA_VERSION

        return metadata

    @staticmethod
    def report_year(report):
        c = report.get("configuration", {})
        start = c.get("start", "")

        try:
            return int(str(start)[0:4])
        except Exception:
            return 0

    @staticmethod
    def tail_risk_score(loss_streak_histogram):
        score = 0

        for streak_length, count in loss_streak_histogram.items():
            score += (2 ** int(streak_length)) * int(count)

        return score

    @staticmethod
    def compact_json(report):
        return json.dumps(report, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def pretty_json(report):
        return json.dumps(report, indent=2, sort_keys=True)

    @staticmethod
    def object_store_report_key(report):
        metadata = ResearchReport.get_metadata(report)
        c = report.get("configuration", {})

        coin = ResearchReport.safe_text(c.get("coin", "coin"))
        timeframe = ResearchReport.safe_text(c.get("timeframe", "tf"))
        year = ResearchReport.report_year(report)
        run_id = ResearchReport.safe_text(metadata.get("run_id"))

        return (
            f"{ResearchReport.REPORT_PREFIX}/"
            f"{coin}/"
            f"{timeframe}/"
            f"{year}/"
            f"{run_id}.json"
        )

    @staticmethod
    def object_store_record_key(report_or_record):
        if "run_id" in report_or_record:
            run_id = report_or_record.get("run_id")
        else:
            run_id = ResearchReport.get_metadata(report_or_record).get("run_id")

        run_id = ResearchReport.safe_text(run_id)

        return f"{ResearchReport.RECORD_PREFIX}/{run_id}.json"

    @staticmethod
    def object_store_key(report):
        # Backward-compatible alias. New code should call object_store_report_key().
        return ResearchReport.object_store_report_key(report)

    @staticmethod
    def normalized_record(report):
        metadata = ResearchReport.get_metadata(report)
        c = report.get("configuration", {})
        p = report.get("performance", {})
        r = report.get("risk", {})
        a = report.get("analytics", {})
        s = report.get("scores", {})

        record = {
            "schema_version": ResearchReport.RECORD_SCHEMA_VERSION,

            "run_id": metadata.get("run_id"),
            "generated_at_utc": metadata.get("generated_at_utc"),
            "completed_at_algorithm_time": metadata.get(
                "completed_at_algorithm_time"
            ),
            "engine_version": metadata.get("engine_version"),

            "experiment_group": metadata.get("experiment_group", "default"),
            "experiment_name": metadata.get("experiment_name", ""),
            "experiment_tags": metadata.get("experiment_tags", []),

            "coin": c.get("coin"),
            "timeframe": c.get("timeframe"),
            "year": ResearchReport.report_year(report),
            "start": c.get("start"),
            "end": c.get("end"),

            "entry_model": c.get("entry_model"),
            "filter_model": c.get("filter_model"),
            "stake_mode": c.get("stake_mode"),

            "streak_length": c.get("streak_length"),
            "streak_mode": c.get("streak_mode"),
            "ema_fast": c.get("ema_fast"),
            "ema_slow": c.get("ema_slow"),
            "base_wager": c.get("base_wager"),
            "bankroll": c.get("bankroll"),
            "multiplier": c.get("multiplier"),
            "max_steps": c.get("max_steps"),

            "initial_bankroll": p.get("initial_bankroll"),
            "final_bankroll": p.get("final_bankroll"),
            "net_profit": p.get("net_profit"),
            "trades": p.get("trades"),
            "wins": p.get("wins"),
            "losses": p.get("losses"),
            "win_rate": p.get("win_rate"),

            "ruined": r.get("ruined"),
            "ruin_time": r.get("ruin_time"),
            "ruin_reason": r.get("ruin_reason"),
            "max_drawdown": r.get("max_drawdown"),
            "max_single_wager": r.get("max_single_wager"),
            "max_win_streak": r.get("max_win_streak"),
            "max_loss_streak": r.get("max_loss_streak"),
            "average_recovery_depth": r.get("average_recovery_depth"),
            "max_recovery_depth": r.get("max_recovery_depth"),

            "bars_seen": a.get("bars_seen"),
            "signals_generated": a.get("signals_generated"),
            "signals_executed": a.get("signals_executed"),
            "execution_rate": a.get("execution_rate"),
            "filter_rate": a.get("filter_rate"),
            "executed_win_rate": a.get("executed_win_rate"),
            "total_wagered": a.get("total_wagered"),
            "average_wager": a.get("average_wager"),

            "survival_score": s.get("survival_score"),
            "risk_adjusted_score": s.get("risk_adjusted_score"),
            "tail_risk_score": s.get("tail_risk_score")
        }

        record["objectstore_report_key"] = ResearchReport.object_store_report_key(
            report
        )
        record["objectstore_record_key"] = ResearchReport.object_store_record_key(
            record
        )

        return record

    @staticmethod
    def summary_line(report):
        record = ResearchReport.normalized_record(report)

        return (
            "RESULT_JSON|"
            + ResearchReport.compact_json({
                "run_id": record["run_id"],
                "coin": record["coin"],
                "timeframe": record["timeframe"],
                "entry": record["entry_model"],
                "filter": record["filter_model"],
                "stake": record["stake_mode"],
                "streak_length": record["streak_length"],
                "streak_mode": record["streak_mode"],
                "ema_fast": record["ema_fast"],
                "ema_slow": record["ema_slow"],
                "net_profit": record["net_profit"],
                "win_rate": record["win_rate"],
                "trades": record["trades"],
                "ruined": record["ruined"],
                "max_drawdown": record["max_drawdown"],
                "max_loss_streak": record["max_loss_streak"],
                "max_recovery_depth": record["max_recovery_depth"],
                "max_single_wager": record["max_single_wager"],
                "risk_adjusted_score": record["risk_adjusted_score"],
                "tail_risk_score": record["tail_risk_score"]
            })
        )
