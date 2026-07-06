# region imports
from AlgorithmImports import *
# endregion

# Your New Python File

from results_database import ResultsDatabase


class QRLResearch:
    @staticmethod
    def load(qb, prefix="qcrl/results/"):
        results = ResultsDatabase.load_all(qb.ObjectStore, prefix)
        return ResultsDatabase.flatten_all(results)

    @staticmethod
    def survivors(rows):
        return [r for r in rows if r.get("ruined") is False]

    @staticmethod
    def summary(rows):
        survivors = QRLResearch.survivors(rows)
        ruined = [r for r in rows if r.get("ruined") is True]

        return {
            "experiments": len(rows),
            "survivors": len(survivors),
            "ruined": len(ruined),
            "best_profit": max([r.get("net_profit", 0) for r in rows], default=0),
            "best_score": max([r.get("risk_adjusted_score", 0) for r in rows], default=0),
            "lowest_drawdown": min([r.get("max_drawdown", 0) for r in survivors], default=0),
            "lowest_recovery_depth": min([r.get("max_recovery_depth", 0) for r in survivors], default=0),
        }

    @staticmethod
    def print_summary(rows):
        s = QRLResearch.summary(rows)

        print("========== QRL SUMMARY ==========")
        print(f"Experiments: {s['experiments']}")
        print(f"Survivors: {s['survivors']}")
        print(f"Ruined: {s['ruined']}")
        print(f"Best profit: {s['best_profit']}")
        print(f"Best risk-adjusted score: {s['best_score']}")
        print(f"Lowest drawdown: {s['lowest_drawdown']}")
        print(f"Lowest recovery depth: {s['lowest_recovery_depth']}")

    @staticmethod
    def top(rows, field="risk_adjusted_score", descending=True, limit=10):
        clean = [r for r in rows if r.get(field) is not None]

        return sorted(
            clean,
            key=lambda r: r.get(field),
            reverse=descending
        )[:limit]

    @staticmethod
    def print_top(rows, field="risk_adjusted_score", descending=True, limit=10):
        ranked = QRLResearch.top(rows, field, descending, limit)

        print(f"========== TOP {limit} BY {field.upper()} ==========")

        for i, r in enumerate(ranked, start=1):
            print(
                f"{i}. "
                f"ema={r.get('ema_fast')}/{r.get('ema_slow')} | "
                f"profit={r.get('net_profit')} | "
                f"score={r.get('risk_adjusted_score')} | "
                f"tail={r.get('tail_risk_score')} | "
                f"dd={r.get('max_drawdown')} | "
                f"depth={r.get('max_recovery_depth')} | "
                f"trades={r.get('trades')} | "
                f"win_rate={r.get('win_rate')}"
            )

    @staticmethod
    def matrix(rows, value_field, fast_field="ema_fast", slow_field="ema_slow"):
        fast_values = sorted(set(r.get(fast_field) for r in rows if r.get(fast_field) is not None))
        slow_values = sorted(set(r.get(slow_field) for r in rows if r.get(slow_field) is not None))

        grid = {}

        for fast in fast_values:
            grid[fast] = {}

            for slow in slow_values:
                matches = [
                    r for r in rows
                    if r.get(fast_field) == fast
                    and r.get(slow_field) == slow
                ]

                if matches:
                    grid[fast][slow] = matches[0].get(value_field)
                else:
                    grid[fast][slow] = None

        return fast_values, slow_values, grid

    @staticmethod
    def print_matrix(rows, value_field):
        fast_values, slow_values, grid = QRLResearch.matrix(rows, value_field)

        print(f"========== MATRIX: {value_field.upper()} ==========")
        header = "fast\\slow".ljust(10)

        for slow in slow_values:
            header += str(slow).rjust(12)

        print(header)

        for fast in fast_values:
            line = str(fast).ljust(10)

            for slow in slow_values:
                value = grid[fast][slow]

                if value is None:
                    cell = "-"
                elif isinstance(value, float):
                    cell = f"{value:.3f}"
                else:
                    cell = str(value)

                line += cell.rjust(12)

            print(line)

    @staticmethod
    def correlations(rows, fields=None):
        if fields is None:
            fields = [
                "net_profit",
                "win_rate",
                "trades",
                "max_drawdown",
                "max_loss_streak",
                "max_recovery_depth",
                "max_single_wager",
                "execution_rate",
                "filter_rate",
                "risk_adjusted_score",
                "tail_risk_score"
            ]

        try:
            import pandas as pd

            data = [
                {field: r.get(field) for field in fields}
                for r in rows
            ]

            df = pd.DataFrame(data)
            return df.corr(numeric_only=True)

        except Exception as e:
            return f"Correlation analysis unavailable: {e}"

    @staticmethod
    def dataframe(rows):
        try:
            import pandas as pd
            return pd.DataFrame(rows)
        except Exception as e:
            return f"DataFrame unavailable: {e}"
