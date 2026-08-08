# region imports
from AlgorithmImports import *
# endregion

# Entry Models
# ============
# Logic for determining trade entry signals.


class FixedBiasEntryModel:
    def __init__(self, bias):
        self.bias = bias.lower()

        if self.bias not in ["up", "down"]:
            raise ValueError("Invalid bias. Use: up or down")

    def get_direction(self, bar):
        return self.bias


class CandleStreakEntryModel:
    def __init__(self, streak_length, streak_mode):
        self.streak_length = streak_length
        self.streak_mode = streak_mode.lower()
        self.recent_directions = []

        if self.streak_length < 1:
            raise ValueError("streak_length must be >= 1")

        if self.streak_mode not in ["follow", "reverse"]:
            raise ValueError("streak_mode must be follow or reverse")

    def get_direction(self, bar):
        signal = None

        if len(self.recent_directions) >= self.streak_length:
            recent = self.recent_directions[-self.streak_length:]

            all_up = all(direction == "up" for direction in recent)
            all_down = all(direction == "down" for direction in recent)

            if all_up:
                signal = (
                    "up"
                    if self.streak_mode == "follow"
                    else "down"
                )

            elif all_down:
                signal = (
                    "down"
                    if self.streak_mode == "follow"
                    else "up"
                )

        if bar.Close > bar.Open:
            self.recent_directions.append("up")
        elif bar.Close < bar.Open:
            self.recent_directions.append("down")

        if len(self.recent_directions) > self.streak_length:
            self.recent_directions = self.recent_directions[
                -self.streak_length:
            ]

        return signal


class PreviousCandleEntryModel:
    def __init__(self):
        self.previous_direction = None

    def get_direction(self, bar):
        direction = self.previous_direction

        if bar.Close > bar.Open:
            self.previous_direction = "up"
        elif bar.Close < bar.Open:
            self.previous_direction = "down"

        return direction


class PreviousCandleReverseEntryModel:
    def __init__(self):
        self.previous_direction = None

    def get_direction(self, bar):
        direction = None

        if self.previous_direction == "up":
            direction = "down"
        elif self.previous_direction == "down":
            direction = "up"

        if bar.Close > bar.Open:
            self.previous_direction = "up"
        elif bar.Close < bar.Open:
            self.previous_direction = "down"

        return direction


class EmaTrendEntryModel:
    def __init__(self, fast_period, slow_period):
        if fast_period < 1 or slow_period < 1:
            raise ValueError("EMA periods must be >= 1")
        if fast_period >= slow_period:
            raise ValueError("EMA fast period must be less than EMA slow period")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.fast_value = None
        self.slow_value = None
        self.fast_multiplier = 2 / (fast_period + 1)
        self.slow_multiplier = 2 / (slow_period + 1)
        self.samples = 0

    def get_direction(self, bar):
        direction = None
        if self.samples >= self.slow_period:
            if self.fast_value > self.slow_value:
                direction = "up"
            elif self.fast_value < self.slow_value:
                direction = "down"

        self.fast_value = self._update_ema(
            self.fast_value, bar.Close, self.fast_multiplier
        )
        self.slow_value = self._update_ema(
            self.slow_value, bar.Close, self.slow_multiplier
        )
        self.samples += 1
        return direction

    @staticmethod
    def _update_ema(current, price, multiplier):
        if current is None:
            return price
        return price * multiplier + current * (1 - multiplier)


class MacdTrendEntryModel:
    def __init__(self, fast_period, slow_period, signal_period):
        if min(fast_period, slow_period, signal_period) < 1:
            raise ValueError("MACD periods must be >= 1")
        if fast_period >= slow_period:
            raise ValueError("MACD fast period must be less than slow period")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.fast_value = None
        self.slow_value = None
        self.signal_value = None
        self.fast_multiplier = 2 / (fast_period + 1)
        self.slow_multiplier = 2 / (slow_period + 1)
        self.signal_multiplier = 2 / (signal_period + 1)
        self.samples = 0

    def get_direction(self, bar):
        direction = None
        if self.samples >= self.slow_period + self.signal_period - 1:
            macd_value = self.fast_value - self.slow_value
            if macd_value > self.signal_value:
                direction = "up"
            elif macd_value < self.signal_value:
                direction = "down"

        self.fast_value = EmaTrendEntryModel._update_ema(
            self.fast_value, bar.Close, self.fast_multiplier
        )
        self.slow_value = EmaTrendEntryModel._update_ema(
            self.slow_value, bar.Close, self.slow_multiplier
        )
        macd_value = self.fast_value - self.slow_value
        self.signal_value = EmaTrendEntryModel._update_ema(
            self.signal_value, macd_value, self.signal_multiplier
        )
        self.samples += 1
        return direction


class RsiMeanReversionEntryModel:
    def __init__(self, period, oversold, overbought):
        if period < 1:
            raise ValueError("RSI period must be >= 1")
        if not 0 <= oversold < overbought <= 100:
            raise ValueError(
                "RSI thresholds must satisfy 0 <= oversold < overbought <= 100"
            )

        self.period = period
        self.oversold = float(oversold)
        self.overbought = float(overbought)
        self.previous_close = None
        self.gains = []
        self.losses = []
        self.average_gain = None
        self.average_loss = None

    def get_direction(self, bar):
        direction = None
        if self.average_gain is not None:
            rsi = self._rsi()
            if rsi <= self.oversold:
                direction = "up"
            elif rsi >= self.overbought:
                direction = "down"

        if self.previous_close is not None:
            change = bar.Close - self.previous_close
            gain = max(change, 0)
            loss = max(-change, 0)
            if self.average_gain is None:
                self.gains.append(gain)
                self.losses.append(loss)
                if len(self.gains) == self.period:
                    self.average_gain = sum(self.gains) / self.period
                    self.average_loss = sum(self.losses) / self.period
            else:
                self.average_gain = (
                    self.average_gain * (self.period - 1) + gain
                ) / self.period
                self.average_loss = (
                    self.average_loss * (self.period - 1) + loss
                ) / self.period
        self.previous_close = bar.Close
        return direction

    def _rsi(self):
        if self.average_loss == 0:
            return 100.0 if self.average_gain > 0 else 50.0
        relative_strength = self.average_gain / self.average_loss
        return 100 - 100 / (1 + relative_strength)


class EntryModelFactory:
    @staticmethod
    def create(
        entry_model_name,
        bias,
        streak_length=2,
        streak_mode="follow",
        ema_fast=5,
        ema_slow=10,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70
    ):
        name = entry_model_name.lower()

        if name == "fixed_bias":
            return FixedBiasEntryModel(bias)

        if name == "previous_candle":
            return PreviousCandleEntryModel()

        if name == "previous_candle_reverse":
            return PreviousCandleReverseEntryModel()

        if name == "candle_streak":
            return CandleStreakEntryModel(
                streak_length,
                streak_mode
            )

        if name == "ema_trend":
            return EmaTrendEntryModel(ema_fast, ema_slow)

        if name == "macd_trend":
            return MacdTrendEntryModel(
                macd_fast,
                macd_slow,
                macd_signal
            )

        if name == "rsi_mean_reversion":
            return RsiMeanReversionEntryModel(
                rsi_period,
                rsi_oversold,
                rsi_overbought
            )

        raise ValueError(f"Unknown entry model: {entry_model_name}")
