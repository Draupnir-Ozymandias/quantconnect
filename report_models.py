# region imports
from AlgorithmImports import *
# endregion

# Your New Python File
import json


class ResearchReport:
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

        return {
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
                "start": f"{algo.start_year}-{algo.start_month}-{algo.start_day}",
                "end": f"{algo.end_year}-{algo.end_month}-{algo.end_day}"
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
    def tail_risk_score(loss_streak_histogram):
        score = 0

        for streak_length, count in loss_streak_histogram.items():
            score += (2 ** int(streak_length)) * int(count)

        return score

    @staticmethod
    def compact_json(report):
        return json.dumps(report, separators=(",", ":"))

    @staticmethod
    def pretty_json(report):
        return json.dumps(report, indent=2)

    @staticmethod
    def object_store_key(report):
        c = report["configuration"]

        return (
            "qcrl/results/"
            f"{c['coin']}_"
            f"{c['timeframe']}_"
            f"{c['entry_model']}_"
            f"{c['filter_model']}_"
            f"{c['stake_mode']}_"
            f"streak{c['streak_length']}_{c['streak_mode']}_"
            f"ef{c['ema_fast']}_"
            f"es{c['ema_slow']}"
        )

    @staticmethod
    def summary_line(report):
        c = report["configuration"]
        p = report["performance"]
        r = report["risk"]
        s = report["scores"]

        return (
            "RESULT_JSON|"
            + ResearchReport.compact_json({
                "coin": c["coin"],
                "timeframe": c["timeframe"],
                "entry": c["entry_model"],
                "filter": c["filter_model"],
                "stake": c["stake_mode"],
                "streak_length": c["streak_length"],
                "streak_mode": c["streak_mode"],
                "ema_fast": c["ema_fast"],
                "ema_slow": c["ema_slow"],
                "net_profit": p["net_profit"],
                "win_rate": p["win_rate"],
                "trades": p["trades"],
                "ruined": r["ruined"],
                "max_drawdown": r["max_drawdown"],
                "max_loss_streak": r["max_loss_streak"],
                "max_recovery_depth": r["max_recovery_depth"],
                "max_single_wager": r["max_single_wager"],
                "risk_adjusted_score": s["risk_adjusted_score"],
                "tail_risk_score": s["tail_risk_score"]
            })
        )
