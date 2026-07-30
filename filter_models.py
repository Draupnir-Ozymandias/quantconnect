# region imports
from AlgorithmImports import *
# endregion

# Filter Models
# =============
# Logic for deciding whether a previously generated signal may trade.


class NoFilterModel:
    def is_ready(self):
        return True

    def update(self, bar):
        pass

    def allow_trade(self, direction):
        return True

    def name(self):
        return "none"

    def regime(self):
        return "none"


class EmaTrendFilterModel:
    def __init__(self, fast_period, slow_period):
        if fast_period < 1:
            raise ValueError("fast_period must be >= 1")

        if slow_period < 1:
            raise ValueError("slow_period must be >= 1")

        if fast_period >= slow_period:
            raise ValueError(
                "EMA fast period must be less than EMA slow period"
            )

        self.fast_period = fast_period
        self.slow_period = slow_period

        self.fast_value = None
        self.slow_value = None

        self.fast_multiplier = 2 / (fast_period + 1)
        self.slow_multiplier = 2 / (slow_period + 1)

        self.samples = 0

    def is_ready(self):
        return self.samples >= self.slow_period

    def update(self, bar):
        price = bar.Close

        if self.fast_value is None:
            self.fast_value = price
        else:
            self.fast_value = (
                price * self.fast_multiplier
                + self.fast_value * (1 - self.fast_multiplier)
            )

        if self.slow_value is None:
            self.slow_value = price
        else:
            self.slow_value = (
                price * self.slow_multiplier
                + self.slow_value * (1 - self.slow_multiplier)
            )

        self.samples += 1

    def allow_trade(self, direction):
        if not self.is_ready():
            return False

        if direction == "up":
            return self.fast_value > self.slow_value

        if direction == "down":
            return self.fast_value < self.slow_value

        return False

    def name(self):
        return f"ema_trend_{self.fast_period}_{self.slow_period}"

    def regime(self):
        if not self.is_ready():
            return "not_ready"

        if self.fast_value > self.slow_value:
            return "bullish"

        if self.fast_value < self.slow_value:
            return "bearish"

        return "neutral"


class FilterModelFactory:
    @staticmethod
    def create(filter_model_name, ema_fast, ema_slow):
        name = filter_model_name.lower()

        if name == "none":
            return NoFilterModel()

        if name == "ema_trend":
            return EmaTrendFilterModel(
                ema_fast,
                ema_slow
            )

        raise ValueError(f"Unknown filter model: {filter_model_name}")
