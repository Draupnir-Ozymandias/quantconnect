# region imports
from AlgorithmImports import *
# endregion

# Your New Python File

class StatsTracker:
    def __init__(self):
        self.bars_seen = 0

        self.signals_generated = 0
        self.signals_executed = 0

        self.signals_skipped_no_direction = 0
        self.signals_skipped_filter_not_ready = 0
        self.signals_skipped_filter_rejected = 0
        self.signals_skipped_tie = 0
        self.signals_skipped_ruined = 0

        self.up_signals = 0
        self.down_signals = 0
        self.up_executed = 0
        self.down_executed = 0

        self.executed_wins = 0
        self.executed_losses = 0

        self.total_wagered = 0
        self.max_wager_seen = 0

        self.recovery_level_counts = {}

        self.regime_stats = {}
        self.filter_signal_values = []
        self.direction_stats = {
            "up": self._new_direction_stats(),
            "down": self._new_direction_stats()
        }
        self.market_regime_stats = {
            direction: {
                regime: self._new_market_regime_stats()
                for regime in ["positive", "nonpositive", "not_ready"]
            }
            for direction in ["up", "down"]
        }

    @staticmethod
    def _new_direction_stats():
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "total_wagered": 0,
            "net_profit": 0,
            "peak_profit": 0,
            "max_drawdown": 0,
            "current_loss_streak": 0,
            "max_loss_streak": 0
        }

    @staticmethod
    def _new_market_regime_stats():
        return {"trades": 0, "wins": 0, "losses": 0, "net_profit": 0}

    def record_bar(self):
        self.bars_seen += 1

    def record_no_direction(self):
        self.signals_skipped_no_direction += 1

    def record_tie(self):
        self.signals_skipped_tie += 1

    def record_signal(self, direction):
        self.signals_generated += 1

        if direction == "up":
            self.up_signals += 1
        elif direction == "down":
            self.down_signals += 1

    def record_filter_not_ready(self):
        self.signals_skipped_filter_not_ready += 1

    def record_filter_rejected(self):
        self.signals_skipped_filter_rejected += 1

    def record_filter_signal_value(self, value):
        if value is None:
            return
        numeric = float(value)
        if numeric == numeric:
            self.filter_signal_values.append(numeric)

    def record_executed(self, direction):
        self.signals_executed += 1

        if direction == "up":
            self.up_executed += 1
        elif direction == "down":
            self.down_executed += 1

    def record_ruined_skip(self):
        self.signals_skipped_ruined += 1

    def record_trade_result(
        self,
        direction,
        won,
        wager,
        recovery_level,
        regime,
        market_regime="unobserved"
    ):
        if won:
            self.executed_wins += 1
        else:
            self.executed_losses += 1

        self.total_wagered += wager
        self.max_wager_seen = max(self.max_wager_seen, wager)

        side = self.direction_stats[direction]
        side["trades"] += 1
        side["total_wagered"] += wager
        if won:
            side["wins"] += 1
            side["net_profit"] += wager
            side["current_loss_streak"] = 0
        else:
            side["losses"] += 1
            side["net_profit"] -= wager
            side["current_loss_streak"] += 1
            side["max_loss_streak"] = max(
                side["max_loss_streak"],
                side["current_loss_streak"]
            )
        side["peak_profit"] = max(
            side["peak_profit"], side["net_profit"]
        )
        side["max_drawdown"] = max(
            side["max_drawdown"],
            side["peak_profit"] - side["net_profit"]
        )

        if market_regime in self.market_regime_stats[direction]:
            context = self.market_regime_stats[direction][market_regime]
            context["trades"] += 1
            if won:
                context["wins"] += 1
                context["net_profit"] += wager
            else:
                context["losses"] += 1
                context["net_profit"] -= wager

        self.recovery_level_counts[recovery_level] = (
            self.recovery_level_counts.get(recovery_level, 0) + 1
        )

        if regime not in self.regime_stats:
            self.regime_stats[regime] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "up": 0,
                "down": 0,
                "total_wagered": 0
            }

        r = self.regime_stats[regime]
        r["trades"] += 1
        r["total_wagered"] += wager

        if won:
            r["wins"] += 1
        else:
            r["losses"] += 1

        if direction == "up":
            r["up"] += 1
        elif direction == "down":
            r["down"] += 1

    def filter_rate(self):
        if self.signals_generated == 0:
            return 0

        skipped_by_filter = (
            self.signals_skipped_filter_not_ready
            + self.signals_skipped_filter_rejected
        )

        return skipped_by_filter / self.signals_generated

    def execution_rate(self):
        if self.signals_generated == 0:
            return 0

        return self.signals_executed / self.signals_generated

    def executed_win_rate(self):
        if self.signals_executed == 0:
            return 0

        return self.executed_wins / self.signals_executed

    def average_wager(self):
        if self.signals_executed == 0:
            return 0

        return self.total_wagered / self.signals_executed

    def filter_signal_value_quantile(self, probability):
        if not self.filter_signal_values:
            return None
        values = sorted(self.filter_signal_values)
        position = (len(values) - 1) * float(probability)
        lower = int(position)
        upper = min(lower + 1, len(values) - 1)
        fraction = position - lower
        return values[lower] + (values[upper] - values[lower]) * fraction

    def filter_signal_value_summary(self):
        return {
            "count": len(self.filter_signal_values),
            "min": self.filter_signal_value_quantile(0),
            "p10": self.filter_signal_value_quantile(0.10),
            "p25": self.filter_signal_value_quantile(0.25),
            "p50": self.filter_signal_value_quantile(0.50),
            "p75": self.filter_signal_value_quantile(0.75),
            "p90": self.filter_signal_value_quantile(0.90),
            "max": self.filter_signal_value_quantile(1)
        }

    def direction_summary(self):
        summary = {}
        for direction in ["up", "down"]:
            side = self.direction_stats[direction]
            trades = side["trades"]
            summary[direction] = {
                "trades": trades,
                "wins": side["wins"],
                "losses": side["losses"],
                "win_rate": side["wins"] / trades if trades else 0,
                "total_wagered": side["total_wagered"],
                "net_profit": side["net_profit"],
                "max_drawdown": side["max_drawdown"],
                "max_loss_streak": side["max_loss_streak"]
            }
        return summary

    def market_regime_summary(self):
        return {
            direction: {
                regime: dict(values)
                for regime, values in regimes.items()
            }
            for direction, regimes in self.market_regime_stats.items()
        }

    def recovery_level_text(self):
        if len(self.recovery_level_counts) == 0:
            return "None"

        parts = []

        for level in sorted(self.recovery_level_counts.keys()):
            count = self.recovery_level_counts[level]
            parts.append(f"{level}:{count}")

        return ", ".join(parts)

    def regime_text(self):
        if len(self.regime_stats) == 0:
            return "None"

        parts = []

        for regime in sorted(self.regime_stats.keys()):
            r = self.regime_stats[regime]
            win_rate = r["wins"] / r["trades"] if r["trades"] > 0 else 0

            parts.append(
                f"{regime} | "
                f"trades={r['trades']}, "
                f"wins={r['wins']}, "
                f"losses={r['losses']}, "
                f"win_rate={win_rate:.2%}, "
                f"up={r['up']}, "
                f"down={r['down']}, "
                f"wagered={r['total_wagered']:.2f}"
            )

        return " || ".join(parts)

    def regime_lines(self):
        if len(self.regime_stats) == 0:
            return ["None"]

        lines = []

        for regime in sorted(self.regime_stats.keys()):
            r = self.regime_stats[regime]
            win_rate = r["wins"] / r["trades"] if r["trades"] > 0 else 0

            lines.append(
                f"{regime} | "
                f"trades={r['trades']}, "
                f"wins={r['wins']}, "
                f"losses={r['losses']}, "
                f"win_rate={win_rate:.2%}, "
                f"up={r['up']}, "
                f"down={r['down']}, "
                f"wagered={r['total_wagered']:.2f}"
             )

        return lines

        
