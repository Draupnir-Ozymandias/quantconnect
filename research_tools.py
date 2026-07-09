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

            "lab_version": c.get("lab_version"),
            "generated_at": c.get("generated_at"),

            "experiment_id": c.get("experiment_id"),
            "experiment_group": c.get("experiment_group"),
            "experiment_name": c.get("experiment_name"),
            "experiment_notes": c.get("experiment_notes"),
            "experiment_tags": c.get("experiment_tags"),
            "experiment_year": c.get("experiment_year"),
            "experiment_asset": c.get("experiment_asset"),
            "experiment_timeframe": c.get("experiment_timeframe"),
            "experiment_family": c.get("experiment_family"),

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

    @staticmethod
    def find_candidate(rows, ema_fast, ema_slow):
        matches = [
            r for r in rows
            if r.get("ema_fast") == ema_fast
            and r.get("ema_slow") == ema_slow
        ]

        if not matches:
            return None

        return ResearchTools.rank(
            matches,
            field="risk_adjusted_score",
            descending=True,
            limit=1
        )[0]


    @staticmethod
    def candidate_summary(rows, ema_fast, ema_slow):
        r = ResearchTools.find_candidate(
            rows,
            ema_fast,
            ema_slow
        )

        if r is None:
            print(f"No candidate found for EMA {ema_fast}/{ema_slow}")
            return

        print(f"\n========== CANDIDATE SUMMARY: EMA {ema_fast}/{ema_slow} ==========")
        print(f"Key: {r.get('key')}")
        print("")
        print("Configuration")
        print(f"  Coin: {r.get('coin')}")
        print(f"  Timeframe: {r.get('timeframe')}")
        print(f"  Entry model: {r.get('entry_model')}")
        print(f"  Filter model: {r.get('filter_model')}")
        print(f"  Stake mode: {r.get('stake_mode')}")
        print(f"  Streak: {r.get('streak_length')} {r.get('streak_mode')}")
        print("")
        print("Performance")
        print(f"  Net profit: {r.get('net_profit'):.2f}")
        print(f"  Trades: {r.get('trades')}")
        print(f"  Wins: {r.get('wins')}")
        print(f"  Losses: {r.get('losses')}")
        print(f"  Win rate: {r.get('win_rate'):.2%}")
        print("")
        print("Risk")
        print(f"  Ruined: {r.get('ruined')}")
        print(f"  Max drawdown: {r.get('max_drawdown')}")
        print(f"  Max loss streak: {r.get('max_loss_streak')}")
        print(f"  Max recovery depth: {r.get('max_recovery_depth')}")
        print(f"  Max single wager: {r.get('max_single_wager')}")
        print("")
        print("Signal Analytics")
        print(f"  Signals generated: {r.get('signals_generated')}")
        print(f"  Signals executed: {r.get('signals_executed')}")
        print(f"  Execution rate: {r.get('execution_rate'):.2%}")
        print(f"  Filter rate: {r.get('filter_rate'):.2%}")
        print("")
        print("Scores")
        print(f"  Risk-adjusted score: {r.get('risk_adjusted_score'):.4f}")
        print(f"  Tail risk score: {r.get('tail_risk_score')}")

    @staticmethod
    def parameter_neighborhood(
        rows,
        ema_fast,
        ema_slow,
        fast_radius=1,
        slow_radius=5,
        metric="risk_adjusted_score"
    ):
        neighbors = []

        for r in rows:
            f = r.get("ema_fast")
            s = r.get("ema_slow")

            if f is None or s is None:
                continue

            fast_close = abs(f - ema_fast) <= fast_radius
            slow_close = abs(s - ema_slow) <= slow_radius

            if fast_close and slow_close:
                neighbors.append(r)

        neighbors = sorted(
            neighbors,
            key=lambda r: (
                r.get("ema_fast"),
                r.get("ema_slow")
            )
        )

        print(
            f"\n========== PARAMETER NEIGHBORHOOD: "
            f"EMA {ema_fast}/{ema_slow} =========="
        )
        print(f"Metric: {metric}")
        print(f"Fast radius: {fast_radius}")
        print(f"Slow radius: {slow_radius}")
        print(f"Neighbors found: {len(neighbors)}")

        for r in neighbors:
            marker = "★" if (
                r.get("ema_fast") == ema_fast
                and r.get("ema_slow") == ema_slow
            ) else " "

            print(
                f"{marker} EMA {r.get('ema_fast')}/{r.get('ema_slow')} | "
                f"{metric}={r.get(metric):.4f} | "
                f"profit={r.get('net_profit'):.2f} | "
                f"dd={r.get('max_drawdown')} | "
                f"depth={r.get('max_recovery_depth')} | "
                f"tail={r.get('tail_risk_score')} | "
                f"win={r.get('win_rate'):.2%} | "
                f"exec={r.get('execution_rate'):.2%}"
            )

        return neighbors

    @staticmethod
    def plateau_analysis(
        neighbors,
        metric="risk_adjusted_score",
        center_fast=None,
        center_slow=None,
        safe_recovery_depth=8,
        safe_drawdown=2550
    ):
        if not neighbors:
            print("\n========== PLATEAU ANALYSIS ==========")
            print("No neighbors supplied.")
            return None

        values = [r.get(metric) for r in neighbors if r.get(metric) is not None]
        profits = [r.get("net_profit") for r in neighbors if r.get("net_profit") is not None]
        drawdowns = [r.get("max_drawdown") for r in neighbors if r.get("max_drawdown") is not None]
        depths = [r.get("max_recovery_depth") for r in neighbors if r.get("max_recovery_depth") is not None]
        tails = [r.get("tail_risk_score") for r in neighbors if r.get("tail_risk_score") is not None]

        def avg(items):
            if not items:
                return 0
            return sum(items) / len(items)

        def std(items):
            if len(items) <= 1:
                return 0

            mean = avg(items)
            variance = sum((x - mean) ** 2 for x in items) / len(items)
            return variance ** 0.5

        robust_neighbors = [
            r for r in neighbors
            if r.get("ruined") is False
            and r.get("max_recovery_depth", 999999) <= safe_recovery_depth
            and r.get("max_drawdown", 999999) <= safe_drawdown
        ]

        risky_neighbors = [
            r for r in neighbors
            if r.get("ruined") is True
            or r.get("max_recovery_depth", 999999) > safe_recovery_depth
            or r.get("max_drawdown", 999999) > safe_drawdown
        ]

        avg_metric = avg(values)
        std_metric = std(values)
        avg_profit = avg(profits)
        std_profit = std(profits)
        avg_drawdown = avg(drawdowns)
        avg_depth = avg(depths)
        avg_tail = avg(tails)

        robust_ratio = len(robust_neighbors) / len(neighbors)

        stability_score = avg_metric / (1 + std_metric)

        risk_penalty = (
            (avg_drawdown / (1 + safe_drawdown))
            + (avg_depth / (1 + safe_recovery_depth))
            + (avg_tail / 10000)
        )

        plateau_score = stability_score * robust_ratio / (1 + risk_penalty)

        result = {
            "center_fast": center_fast,
            "center_slow": center_slow,
            "metric": metric,
            "neighbors": len(neighbors),
            "robust_neighbors": len(robust_neighbors),
            "risky_neighbors": len(risky_neighbors),
            "robust_ratio": robust_ratio,
            "average_metric": avg_metric,
            "metric_std_dev": std_metric,
            "average_profit": avg_profit,
            "profit_std_dev": std_profit,
            "average_drawdown": avg_drawdown,
            "average_recovery_depth": avg_depth,
            "average_tail_risk": avg_tail,
            "stability_score": stability_score,
            "risk_penalty": risk_penalty,
            "plateau_score": plateau_score
        }

        title = "PLATEAU ANALYSIS"
        if center_fast is not None and center_slow is not None:
            title += f": EMA {center_fast}/{center_slow}"

        print(f"\n========== {title} ==========")
        print(f"Metric: {metric}")
        print(f"Neighbors evaluated: {len(neighbors)}")
        print(f"Robust neighbors: {len(robust_neighbors)}")
        print(f"Risky neighbors: {len(risky_neighbors)}")
        print(f"Robust ratio: {robust_ratio:.2%}")
        print("")
        print("Metric Stability")
        print(f"  Average {metric}: {avg_metric:.4f}")
        print(f"  {metric} std dev: {std_metric:.4f}")
        print(f"  Stability score: {stability_score:.4f}")
        print("")
        print("Performance Stability")
        print(f"  Average profit: {avg_profit:.2f}")
        print(f"  Profit std dev: {std_profit:.2f}")
        print("")
        print("Risk Profile")
        print(f"  Average drawdown: {avg_drawdown:.2f}")
        print(f"  Average recovery depth: {avg_depth:.2f}")
        print(f"  Average tail risk: {avg_tail:.2f}")
        print(f"  Risk penalty: {risk_penalty:.4f}")
        print("")
        print(f"Plateau score: {plateau_score:.4f}")

        if risky_neighbors:
            print("")
            print("Risky neighbors:")
            for r in risky_neighbors:
                print(
                    f"  EMA {r.get('ema_fast')}/{r.get('ema_slow')} | "
                    f"profit={r.get('net_profit'):.2f} | "
                    f"score={r.get('risk_adjusted_score'):.4f} | "
                    f"dd={r.get('max_drawdown')} | "
                    f"depth={r.get('max_recovery_depth')} | "
                    f"wager={r.get('max_single_wager')}"
                )

        return result

    @staticmethod
    def find_plateaus(
        rows,
        metric="risk_adjusted_score",
        fast_radius=1,
        slow_radius=5,
        safe_recovery_depth=8,
        safe_drawdown=2550,
        min_neighbors=3
    ):
        plateaus = []

        for r in rows:
            ema_fast = r.get("ema_fast")
            ema_slow = r.get("ema_slow")

            if ema_fast is None or ema_slow is None:
                continue

            neighbors = []

            for candidate in rows:
                f = candidate.get("ema_fast")
                s = candidate.get("ema_slow")

                if f is None or s is None:
                    continue

                if (
                    abs(f - ema_fast) <= fast_radius
                    and abs(s - ema_slow) <= slow_radius
                ):
                    neighbors.append(candidate)

            if len(neighbors) < min_neighbors:
                continue

            plateau = ResearchTools.plateau_analysis_silent(
                neighbors,
                metric=metric,
                center_fast=ema_fast,
                center_slow=ema_slow,
                safe_recovery_depth=safe_recovery_depth,
                safe_drawdown=safe_drawdown
            )

            center_metric = r.get(metric, 0)
            center_profit = r.get("net_profit", 0)
            center_drawdown = r.get("max_drawdown", 0)
            center_depth = r.get("max_recovery_depth", 0)
            center_tail = r.get("tail_risk_score", 0)

            plateau["center_metric"] = center_metric
            plateau["center_profit"] = center_profit
            plateau["center_drawdown"] = center_drawdown
            plateau["center_recovery_depth"] = center_depth
            plateau["center_tail_risk"] = center_tail
            plateau["center_win_rate"] = r.get("win_rate", 0)
            plateau["center_execution_rate"] = r.get("execution_rate", 0)
            plateau["center_trades"] = r.get("trades", 0)

            plateaus.append(plateau)

        return sorted(
            plateaus,
            key=lambda p: p.get("plateau_score", 0),
            reverse=True
        )


    @staticmethod
    def plateau_analysis_silent(
        neighbors,
        metric="risk_adjusted_score",
        center_fast=None,
        center_slow=None,
        safe_recovery_depth=8,
        safe_drawdown=2550
    ):
        values = [r.get(metric) for r in neighbors if r.get(metric) is not None]
        profits = [r.get("net_profit") for r in neighbors if r.get("net_profit") is not None]
        drawdowns = [r.get("max_drawdown") for r in neighbors if r.get("max_drawdown") is not None]
        depths = [r.get("max_recovery_depth") for r in neighbors if r.get("max_recovery_depth") is not None]
        tails = [r.get("tail_risk_score") for r in neighbors if r.get("tail_risk_score") is not None]

        def avg(items):
            if not items:
                return 0
            return sum(items) / len(items)

        def std(items):
            if len(items) <= 1:
                return 0

            mean = avg(items)
            variance = sum((x - mean) ** 2 for x in items) / len(items)
            return variance ** 0.5

        robust_neighbors = [
            r for r in neighbors
            if r.get("ruined") is False
            and r.get("max_recovery_depth", 999999) <= safe_recovery_depth
            and r.get("max_drawdown", 999999) <= safe_drawdown
        ]

        risky_neighbors = [
            r for r in neighbors
            if r.get("ruined") is True
            or r.get("max_recovery_depth", 999999) > safe_recovery_depth
            or r.get("max_drawdown", 999999) > safe_drawdown
        ]

        avg_metric = avg(values)
        std_metric = std(values)
        avg_profit = avg(profits)
        std_profit = std(profits)
        avg_drawdown = avg(drawdowns)
        avg_depth = avg(depths)
        avg_tail = avg(tails)

        robust_ratio = len(robust_neighbors) / len(neighbors)

        stability_score = avg_metric / (1 + std_metric)

        risk_penalty = (
            (avg_drawdown / (1 + safe_drawdown))
            + (avg_depth / (1 + safe_recovery_depth))
            + (avg_tail / 10000)
        )

        plateau_score = stability_score * robust_ratio / (1 + risk_penalty)

        return {
            "center_fast": center_fast,
            "center_slow": center_slow,
            "metric": metric,
            "neighbors": len(neighbors),
            "robust_neighbors": len(robust_neighbors),
            "risky_neighbors": len(risky_neighbors),
            "robust_ratio": robust_ratio,
            "average_metric": avg_metric,
            "metric_std_dev": std_metric,
            "average_profit": avg_profit,
            "profit_std_dev": std_profit,
            "average_drawdown": avg_drawdown,
            "average_recovery_depth": avg_depth,
            "average_tail_risk": avg_tail,
            "stability_score": stability_score,
            "risk_penalty": risk_penalty,
            "plateau_score": plateau_score
        }

    @staticmethod
    def print_plateaus(plateaus, limit=20):
        print("\n========== TOP PLATEAUS ==========")

        for i, p in enumerate(plateaus[:limit], start=1):
            print(
                f"{i:02d}. "
                f"EMA {p.get('center_fast')}/{p.get('center_slow')} | "
                f"plateau={p.get('plateau_score'):.4f} | "
                f"center_score={p.get('center_metric'):.4f} | "
                f"avg_score={p.get('average_metric'):.4f} | "
                f"robust={p.get('robust_neighbors')}/{p.get('neighbors')} | "
                f"profit={p.get('center_profit'):.2f} | "
                f"avg_profit={p.get('average_profit'):.2f} | "
                f"dd={p.get('center_drawdown')} | "
                f"avg_dd={p.get('average_drawdown'):.2f} | "
                f"depth={p.get('center_recovery_depth')} | "
                f"avg_depth={p.get('average_recovery_depth'):.2f} | "
                f"tail={p.get('center_tail_risk')}"
            )

    @staticmethod
    def parameter_heatmap(
        rows,
        value_field,
        title=None,
        value_format=".2f"
    ):
        import math
        import pandas as pd
        import matplotlib.pyplot as plt

        df = pd.DataFrame(rows)

        pivot = df.pivot_table(
            index="ema_fast",
            columns="ema_slow",
            values=value_field,
            aggfunc="max"
        )

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

                if pd.notna(value):
                    plt.text(
                        x,
                        y,
                        format(value, value_format),
                        ha="center",
                        va="center"
                    )

        plt.show()

        return pivot


    @staticmethod
    def plateau_heatmap(
        plateaus,
        value_field="plateau_score",
        title=None,
        value_format=".3f"
    ):
        import math
        import pandas as pd
        import matplotlib.pyplot as plt

        df = pd.DataFrame(plateaus)

        pivot = df.pivot_table(
            index="center_fast",
            columns="center_slow",
            values=value_field,
            aggfunc="max"
        )

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

                if pd.notna(value):
                    plt.text(
                        x,
                        y,
                        format(value, value_format),
                        ha="center",
                        va="center"
                    )

        plt.show()

        return pivot

    @staticmethod
    def correlation_dashboard(
        rows,
        fields=None,
        title="Correlation Dashboard",
        top_n=15
    ):
        import pandas as pd
        import matplotlib.pyplot as plt

        if fields is None:
            fields = [
                "net_profit",
                "risk_adjusted_score",
                "tail_risk_score",
                "max_drawdown",
                "max_recovery_depth",
                "max_single_wager",
                "max_loss_streak",
                "trades",
                "win_rate",
                "execution_rate",
                "filter_rate",
                "signals_executed",
                "average_wager",
                "total_wagered",
            ]

        df = pd.DataFrame(rows)

        available_fields = [
            field for field in fields
            if field in df.columns
        ]

        numeric_df = df[available_fields].apply(
            pd.to_numeric,
            errors="coerce"
        )

        corr = numeric_df.corr()

        print(f"\n========== {title.upper()} ==========")
        print(f"Rows analyzed: {len(df)}")
        print(f"Fields analyzed: {len(available_fields)}")

        plt.figure(figsize=(12, 9))
        plt.imshow(corr, aspect="auto", vmin=-1, vmax=1)
        plt.colorbar(label="Correlation")

        plt.xticks(
            range(len(corr.columns)),
            corr.columns,
            rotation=45,
            ha="right"
        )

        plt.yticks(
            range(len(corr.index)),
            corr.index
        )

        plt.title(title)

        for y in range(len(corr.index)):
            for x in range(len(corr.columns)):
                value = corr.iloc[y, x]

                if pd.notna(value):
                    plt.text(
                        x,
                        y,
                        f"{value:.2f}",
                        ha="center",
                        va="center"
                    )

        plt.tight_layout()
        plt.show()

        pairs = []

        for i, field_a in enumerate(corr.columns):
            for j, field_b in enumerate(corr.columns):
                if j <= i:
                    continue

                value = corr.loc[field_a, field_b]

                if pd.notna(value):
                    pairs.append({
                        "field_a": field_a,
                        "field_b": field_b,
                        "correlation": value,
                        "abs_correlation": abs(value)
                    })

        pairs = sorted(
            pairs,
            key=lambda p: p["abs_correlation"],
            reverse=True
        )

        print("\n--- Strongest correlations ---")

        for i, pair in enumerate(pairs[:top_n], start=1):
            print(
                f"{i:02d}. "
                f"{pair['field_a']} vs {pair['field_b']} | "
                f"corr={pair['correlation']:.4f}"
            )

        return corr, pairs

    @staticmethod
    def experiment_dashboard(rows):
        import pandas as pd

        df = pd.DataFrame(rows)

        if df.empty:
            print("\n========== EXPERIMENT DASHBOARD ==========")
            print("No rows found.")
            return df

        required = [
            "experiment_id",
            "coin",
            "timeframe",
            "net_profit",
            "ruined",
            "trades",
            "win_rate",
            "execution_rate",
            "filter_rate",
            "max_drawdown",
            "max_recovery_depth",
            "max_single_wager",
            "risk_adjusted_score",
            "tail_risk_score",
            "ema_fast",
            "ema_slow"
        ]

        for field in required:
            if field not in df.columns:
                df[field] = None

        grouped = []

        for experiment_id, g in df.groupby("experiment_id", dropna=False):
            reports = len(g)
            survivors = len(g[g["ruined"] == False])
            ruined = len(g[g["ruined"] == True])

            duplicate_params = g.duplicated(
                subset=["ema_fast", "ema_slow"],
                keep=False
            ).sum()

            unique_fast = sorted(g["ema_fast"].dropna().unique().tolist())
            unique_slow = sorted(g["ema_slow"].dropna().unique().tolist())

            best_score_row = g.sort_values(
                "risk_adjusted_score",
                ascending=False
            ).iloc[0]

            best_profit_row = g.sort_values(
                "net_profit",
                ascending=False
            ).iloc[0]

            grouped.append({
                "experiment_id": experiment_id,
                "coin": g["coin"].dropna().iloc[0] if len(g["coin"].dropna()) else None,
                "timeframe": g["timeframe"].dropna().iloc[0] if len(g["timeframe"].dropna()) else None,
                "reports": reports,
                "survivors": survivors,
                "ruined": ruined,
                "survival_rate": survivors / reports if reports else 0,
                "duplicate_params": int(duplicate_params),

                "ema_fast_count": len(unique_fast),
                "ema_slow_count": len(unique_slow),
                "ema_fast_values": unique_fast,
                "ema_slow_values": unique_slow,

                "avg_profit": g["net_profit"].mean(),
                "median_profit": g["net_profit"].median(),
                "best_profit": g["net_profit"].max(),
                "worst_profit": g["net_profit"].min(),

                "avg_drawdown": g["max_drawdown"].mean(),
                "max_drawdown": g["max_drawdown"].max(),
                "avg_recovery_depth": g["max_recovery_depth"].mean(),
                "max_recovery_depth": g["max_recovery_depth"].max(),

                "avg_win_rate": g["win_rate"].mean(),
                "avg_execution_rate": g["execution_rate"].mean(),
                "avg_filter_rate": g["filter_rate"].mean(),

                "best_score": g["risk_adjusted_score"].max(),
                "avg_score": g["risk_adjusted_score"].mean(),
                "avg_tail_risk": g["tail_risk_score"].mean(),

                "best_score_ema": f"{int(best_score_row['ema_fast'])}/{int(best_score_row['ema_slow'])}",
                "best_profit_ema": f"{int(best_profit_row['ema_fast'])}/{int(best_profit_row['ema_slow'])}",
            })

        dashboard = pd.DataFrame(grouped)

        dashboard = dashboard.sort_values(
            by=["coin", "timeframe", "experiment_id"],
            ascending=True
        )

        print("\n========== EXPERIMENT DASHBOARD ==========")
        print(f"Total reports: {len(df)}")
        print(f"Experiments discovered: {len(dashboard)}")
        print("")

        display_cols = [
            "experiment_id",
            "coin",
            "timeframe",
            "reports",
            "survivors",
            "ruined",
            "survival_rate",
            "duplicate_params",
            "ema_fast_count",
            "ema_slow_count",
            "avg_profit",
            "best_profit",
            "avg_drawdown",
            "max_recovery_depth",
            "best_score",
            "best_score_ema",
            "best_profit_ema"
        ]

        print(
            dashboard[display_cols].to_string(
                index=False,
                formatters={
                    "survival_rate": lambda x: f"{x:.2%}",
                    "avg_profit": lambda x: f"{x:.2f}",
                    "best_profit": lambda x: f"{x:.2f}",
                    "avg_drawdown": lambda x: f"{x:.2f}",
                    "best_score": lambda x: f"{x:.4f}",
                }
            )
        )

        return dashboard
