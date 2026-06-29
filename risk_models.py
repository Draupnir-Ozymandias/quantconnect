# region imports
from AlgorithmImports import *
# endregion
# Risk Models
# ===========
# Logic for risk management and trade controls.

# from typing import Dict, Optional
# from QuantConnect import QCAlgorithm

class RiskTracker:
    def __init__(self, initial_bankroll, max_steps):
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.peak_bankroll = initial_bankroll

        self.max_steps = max_steps
        self.loss_step = 0

        self.trades = 0
        self.wins = 0
        self.losses = 0

        self.current_win_streak = 0
        self.current_loss_streak = 0
        self.max_win_streak = 0
        self.max_loss_streak = 0

        self.win_streak_histogram = {}
        self.loss_streak_histogram = {}

        self.recovery_depths = []

        self.max_drawdown = 0
        self.max_single_wager = 0

        self.ruined = False
        self.ruin_reason = ""

        self.ruin_time = None

    def can_place_wager(self, wager, timestamp=None):
        if wager > self.bankroll:
            self.ruined = True
            self.ruin_time = timestamp

            self.ruin_reason = (
                f"Needed wager={wager:.2f}, "
                f"Bankroll={self.bankroll:.2f}, "
                f"LossStep={self.loss_step}"
            )
            return False
        return True

    def _record_histogram(self, histogram, streak_length):
        if streak_length > 0:
            histogram[streak_length] = histogram.get(streak_length, 0) + 1

    def record_trade(self, won, wager, timestamp=None):
        self.trades += 1
        self.max_single_wager = max(self.max_single_wager, wager)

        if won:
            self.wins += 1
            self.bankroll += wager

            # A loss streak just ended
            if self.current_loss_streak > 0:
                self._record_histogram(
                    self.loss_streak_histogram,
                    self.current_loss_streak
                )
                self.recovery_depths.append(self.current_loss_streak)

            self.current_win_streak += 1
            self.current_loss_streak = 0

            self.max_win_streak = max(
                self.max_win_streak,
                self.current_win_streak
            )

            self.loss_step = 0

        else:
            self.losses += 1
            self.bankroll -= wager

            # A win streak just ended
            if self.current_win_streak > 0:
                self._record_histogram(
                    self.win_streak_histogram,
                    self.current_win_streak
                )

            self.current_loss_streak += 1
            self.current_win_streak = 0

            self.max_loss_streak = max(
                self.max_loss_streak,
                self.current_loss_streak
            )

            self.loss_step += 1

            if self.loss_step > self.max_steps:
                self.ruined = True
                self.ruin_time = timestamp
                self.ruin_reason = (
                    f"Max martingale step exceeded. "
                    f"LossStep={self.loss_step}, "
                    f"MaxSteps={self.max_steps}"
                )

        self.peak_bankroll = max(self.peak_bankroll, self.bankroll)
        drawdown = self.peak_bankroll - self.bankroll
        self.max_drawdown = max(self.max_drawdown, drawdown)

        return drawdown

    def finalize(self):
        self._record_histogram(
            self.win_streak_histogram,
            self.current_win_streak
        )

        self._record_histogram(
            self.loss_streak_histogram,
            self.current_loss_streak
        )

        if self.current_loss_streak > 0:
            self.recovery_depths.append(self.current_loss_streak)

    def win_rate(self):
        if self.trades == 0:
            return 0
        return self.wins / self.trades

    def net_profit(self):
        return self.bankroll - self.initial_bankroll

    def average_recovery_depth(self):
        if len(self.recovery_depths) == 0:
            return 0
        return sum(self.recovery_depths) / len(self.recovery_depths)

    def max_recovery_depth(self):
        if len(self.recovery_depths) == 0:
            return 0
        return max(self.recovery_depths)

    def streak_histogram_text(self, histogram):
        if len(histogram) == 0:
            return "None"

        parts = []
        for streak_length in sorted(histogram.keys()):
            parts.append(f"{streak_length}:{histogram[streak_length]}")

        return ", ".join(parts)

    def win_streak_histogram_text(self):
        return self.streak_histogram_text(self.win_streak_histogram)

    def loss_streak_histogram_text(self):
        return self.streak_histogram_text(self.loss_streak_histogram)
