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
        regime
    ):
        if won:
            self.executed_wins += 1
        else:
            self.executed_losses += 1

        self.total_wagered += wager
        self.max_wager_seen = max(self.max_wager_seen, wager)

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

        
