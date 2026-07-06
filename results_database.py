# region imports
from AlgorithmImports import *
# endregion

# Your New Python File

import json


class ResultsDatabase:
    PREFIX = "qcrl/results/"

    @staticmethod
    def load_all(object_store, prefix=PREFIX):
        results = []

        for key in object_store.Keys:
            if key.startswith(prefix):
                try:
                    raw = object_store.Read(key)
                    report = json.loads(raw)
                    report["_object_store_key"] = key
                    results.append(report)
                except Exception as e:
                    results.append({
                        "_object_store_key": key,
                        "_load_error": str(e)
                    })

        return results

    @staticmethod
    def flatten(report):
        c = report.get("configuration", {})
        p = report.get("performance", {})
        r = report.get("risk", {})
        a = report.get("analytics", {})
        s = report.get("scores", {})

        return {
            "key": report.get("_object_store_key", ""),
            "coin": c.get("coin"),
            "timeframe": c.get("timeframe"),
            "entry_model": c.get("entry_model"),
            "filter_model": c.get("filter_model"),
            "stake_mode": c.get("stake_mode"),
            "streak_length": c.get("streak_length"),
            "streak_mode": c.get("streak_mode"),
            "ema_fast": c.get("ema_fast"),
            "ema_slow": c.get("ema_slow"),

            "net_profit": p.get("net_profit"),
            "trades": p.get("trades"),
            "win_rate": p.get("win_rate"),

            "ruined": r.get("ruined"),
            "max_drawdown": r.get("max_drawdown"),
            "max_loss_streak": r.get("max_loss_streak"),
            "max_recovery_depth": r.get("max_recovery_depth"),
            "max_single_wager": r.get("max_single_wager"),

            "signals_generated": a.get("signals_generated"),
            "signals_executed": a.get("signals_executed"),
            "execution_rate": a.get("execution_rate"),
            "filter_rate": a.get("filter_rate"),

            "risk_adjusted_score": s.get("risk_adjusted_score"),
            "tail_risk_score": s.get("tail_risk_score")
        }

    @staticmethod
    def flatten_all(results):
        return [ResultsDatabase.flatten(r) for r in results if "_load_error" not in r]

    @staticmethod
    def rank(rows, field="risk_adjusted_score", descending=True, limit=25):
        clean = [r for r in rows if r.get(field) is not None]
        return sorted(
            clean,
            key=lambda x: x.get(field),
            reverse=descending
        )[:limit]

    @staticmethod
    def survivors(rows):
        return [r for r in rows if r.get("ruined") is False]

    @staticmethod
    def filter_rows(
        rows,
        max_recovery_depth=None,
        max_drawdown=None,
        min_profit=None,
        min_trades=None,
        survived_only=True
    ):
        filtered = rows

        if survived_only:
            filtered = [r for r in filtered if r.get("ruined") is False]

        if max_recovery_depth is not None:
            filtered = [
                r for r in filtered
                if r.get("max_recovery_depth") is not None
                and r.get("max_recovery_depth") <= max_recovery_depth
            ]

        if max_drawdown is not None:
            filtered = [
                r for r in filtered
                if r.get("max_drawdown") is not None
                and r.get("max_drawdown") <= max_drawdown
            ]

        if min_profit is not None:
            filtered = [
                r for r in filtered
                if r.get("net_profit") is not None
                and r.get("net_profit") >= min_profit
            ]

        if min_trades is not None:
            filtered = [
                r for r in filtered
                if r.get("trades") is not None
                and r.get("trades") >= min_trades
            ]

        return filtered

    @staticmethod
    def print_rows(debug_fn, rows, title="RESULTS", limit=25):
        debug_fn(f"========== {title} ==========")

        for i, r in enumerate(rows[:limit], start=1):
            debug_fn(
                f"{i}. "
                f"profit={r.get('net_profit')}, "
                f"score={r.get('risk_adjusted_score')}, "
                f"tail={r.get('tail_risk_score')}, "
                f"ruined={r.get('ruined')}, "
                f"dd={r.get('max_drawdown')}, "
                f"depth={r.get('max_recovery_depth')}, "
                f"trades={r.get('trades')}, "
                f"win_rate={r.get('win_rate')}, "
                f"ema={r.get('ema_fast')}/{r.get('ema_slow')}, "
                f"streak={r.get('streak_length')} {r.get('streak_mode')}"
            )

    @staticmethod
    def to_csv(rows):
        if not rows:
            return ""

        headers = list(rows[0].keys())
        lines = [",".join(headers)]

        for r in rows:
            values = []
            for h in headers:
                value = r.get(h, "")
                value = str(value).replace(",", ";")
                values.append(value)
            lines.append(",".join(values))

        return "\n".join(lines)
