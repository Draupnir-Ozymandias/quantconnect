# region imports
from AlgorithmImports import *
# endregion

# Your New Python File

import json
import math


class ResearchTools:
    PREFIX = "qcrl/results/"

    @staticmethod
    def load_reports(object_store, prefix=PREFIX):
        reports = []

        for key in object_store.Keys:
            if not key.startswith(prefix):
                continue

            raw = object_store.Read(key)
            report = json.loads(raw)
            report["_key"] = key
            reports.append(report)

        return reports

    @staticmethod
    def flatten(report):
        c = report.get("configuration", {})
        p = report.get("performance", {})
        r = report.get("risk", {})
        a = report.get("analytics", {})
        s = report.get("scores", {})

        return {
            "key": report.get("_key", ""),

            "coin": c.get("coin"),
            "timeframe": c.get("timeframe"),
            "entry_model": c.get("entry_model"),
            "filter_model": c.get("filter_model"),
            "stake_mode": c.get("stake_mode"),
            "streak_length": c.get("streak_length"),
            "streak_mode": c.get("streak_mode"),
            "ema_fast": c.get("ema_fast"),
            "ema_slow": c.get("ema_slow"),

            "net_profit": p.get("net_profit", 0),
            "trades": p.get("trades", 0),
            "wins": p.get("wins", 0),
            "losses": p.get("losses", 0),
            "win_rate": p.get("win_rate", 0),

            "ruined": r.get("ruined", False),
            "max_drawdown": r.get("max_drawdown", 0),
            "max_single_wager": r.get("max_single_wager", 0),
            "max_loss_streak": r.get("max_loss_streak", 0),
            "max_recovery_depth": r.get("max_recovery_depth", 0),

            "signals_generated": a.get("signals_generated", 0),
            "signals_executed": a.get("signals_executed", 0),
            "execution_rate": a.get("execution_rate", 0),
            "filter_rate": a.get("filter_rate", 0),
            "average_wager": a.get("average_wager", 0),
            "total_wagered": a.get("total_wagered", 0),

            "risk_adjusted_score": s.get("risk_adjusted_score", 0),
            "tail_risk_score": s.get("tail_risk_score", 0),
            "survival_score": s.get("survival_score", 0),
        }

    @staticmethod
    def flatten_all(reports):
        return [ResearchTools.flatten(r) for r in reports]

    @staticmethod
    def rank(rows, field="risk_adjusted_score", descending=True, limit=20):
        clean = [r for r in rows if r.get(field) is not None]

        return sorted(
            clean,
            key=lambda r: r.get(field),
            reverse=descending
        )[:limit]

    @staticmethod
    def filter_rows(
        rows,
        survived_only=True,
        min_profit=None,
        max_drawdown=None,
        max_recovery_depth=None,
        max_loss_streak=None,
        min_trades=None
    ):
        output = rows

        if survived_only:
            output = [r for r in output if r.get("ruined") is False]

        if min_profit is not None:
            output = [r for r in output if r.get("net_profit", 0) >= min_profit]

        if max_drawdown is not None:
            output = [r for r in output if r.get("max_drawdown", math.inf) <= max_drawdown]

        if max_recovery_depth is not None:
            output = [r for r in output if r.get("max_recovery_depth", math.inf) <= max_recovery_depth]

        if max_loss_streak is not None:
            output = [r for r in output if r.get("max_loss_streak", math.inf) <= max_loss_streak]

        if min_trades is not None:
            output = [r for r in output if r.get("trades", 0) >= min_trades]

        return output

    @staticmethod
    def print_table(rows, title="RESULTS", limit=20):
        print(f"\n========== {title} ==========")

        for i, r in enumerate(rows[:limit], start=1):
            print(
                f"{i:02d}. "
                f"EMA {r.get('ema_fast')}/{r.get('ema_slow')} | "
                f"profit={r.get('net_profit'):.2f} | "
                f"score={r.get('risk_adjusted_score'):.4f} | "
                f"tail={r.get('tail_risk_score')} | "
                f"dd={r.get('max_drawdown')} | "
                f"depth={r.get('max_recovery_depth')} | "
                f"wager={r.get('max_single_wager')} | "
                f"trades={r.get('trades')} | "
                f"win={r.get('win_rate'):.2%} | "
                f"exec={r.get('execution_rate'):.2%}"
            )

    @staticmethod
    def to_dataframe(rows):
        import pandas as pd
        return pd.DataFrame(rows)

    @staticmethod
    def pivot(rows, value_field):
        import pandas as pd

        df = pd.DataFrame(rows)

        return df.pivot_table(
            index="ema_fast",
            columns="ema_slow",
            values=value_field,
            aggfunc="max"
        )

    @staticmethod
    def heatmap(rows, value_field, title=None):
        import matplotlib.pyplot as plt

        pivot = ResearchTools.pivot(rows, value_field)

        plt.figure(figsize=(10, 6))
        plt.imshow(pivot, aspect="auto")
        plt.colorbar(label=value_field)

        plt.xticks(range(len(pivot.columns)), pivot.columns)
        plt.yticks(range(len(pivot.index)), pivot.index)

        plt.xlabel("EMA Slow")
        plt.ylabel("EMA Fast")
        plt.title(title or value_field)

        for y in range(len(pivot.index)):
            for x in range(len(pivot.columns)):
                value = pivot.iloc[y, x]
                if not math.isnan(value):
                    plt.text(
                        x,
                        y,
                        f"{value:.2f}",
                        ha="center",
                        va="center"
                    )

        plt.show()
    
    @staticmethod
    def best_candidates(rows, limit=5):
        survivors = ResearchTools.filter_rows(
            rows,
            survived_only=True
        )

        categories = [
            {
                "title": "Best risk-adjusted score",
                "field": "risk_adjusted_score",
                "descending": True
            },
            {
                "title": "Best net profit",
                "field": "net_profit",
                "descending": True
            },
            {
                "title": "Lowest tail risk",
                "field": "tail_risk_score",
                "descending": False
            },
            {
                "title": "Lowest drawdown",
                "field": "max_drawdown",
                "descending": False
            },
            {
                "title": "Lowest recovery depth",
                "field": "max_recovery_depth",
                "descending": False
            },
            {
                "title": "Lowest max single wager",
                "field": "max_single_wager",
                "descending": False
            },
            {
                "title": "Highest win rate",
                "field": "win_rate",
                "descending": True
            },
            {
                "title": "Highest execution rate",
                "field": "execution_rate",
                "descending": True
            }
        ]

        print("\n========== BEST CANDIDATES ==========")
        print(f"Total rows: {len(rows)}")
        print(f"Survivors: {len(survivors)}")

        for category in categories:
            ranked = ResearchTools.rank(
                survivors,
                field=category["field"],
                descending=category["descending"],
                limit=limit
            )

            print(f"\n--- {category['title']} ---")

            if not ranked:
                print("No candidates found.")
                continue

            for i, r in enumerate(ranked, start=1):
                print(
                    f"{i:02d}. "
                    f"EMA {r.get('ema_fast')}/{r.get('ema_slow')} | "
                    f"profit={r.get('net_profit'):.2f} | "
                    f"score={r.get('risk_adjusted_score'):.4f} | "
                    f"tail={r.get('tail_risk_score')} | "
                    f"dd={r.get('max_drawdown')} | "
                    f"depth={r.get('max_recovery_depth')} | "
                    f"wager={r.get('max_single_wager')} | "
                    f"trades={r.get('trades')} | "
                    f"win={r.get('win_rate'):.2%} | "
                    f"exec={r.get('execution_rate'):.2%}"
                )

    
