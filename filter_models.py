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


class AdxStrengthFilterModel:
    def __init__(self, period, threshold):
        if period < 2:
            raise ValueError("ADX period must be >= 2")
        if not 0 <= threshold <= 100:
            raise ValueError("ADX threshold must be between 0 and 100")

        self.period = period
        self.threshold = float(threshold)
        self.previous_high = None
        self.previous_low = None
        self.previous_close = None
        self.true_ranges = []
        self.positive_dm = []
        self.negative_dm = []
        self.dx_values = []
        self.smoothed_true_range = None
        self.smoothed_positive_dm = None
        self.smoothed_negative_dm = None
        self.adx_value = None

    def is_ready(self):
        return self.adx_value is not None

    def update(self, bar):
        if self.previous_close is not None:
            upward_move = bar.High - self.previous_high
            downward_move = self.previous_low - bar.Low
            positive_dm = (
                upward_move
                if upward_move > downward_move and upward_move > 0
                else 0
            )
            negative_dm = (
                downward_move
                if downward_move > upward_move and downward_move > 0
                else 0
            )
            true_range = max(
                bar.High - bar.Low,
                abs(bar.High - self.previous_close),
                abs(bar.Low - self.previous_close)
            )
            if self.smoothed_true_range is None:
                self.true_ranges.append(true_range)
                self.positive_dm.append(positive_dm)
                self.negative_dm.append(negative_dm)
                if len(self.true_ranges) == self.period:
                    self.smoothed_true_range = sum(self.true_ranges)
                    self.smoothed_positive_dm = sum(self.positive_dm)
                    self.smoothed_negative_dm = sum(self.negative_dm)
                    self.dx_values.append(self._directional_index())
            else:
                self.smoothed_true_range = (
                    self.smoothed_true_range
                    - self.smoothed_true_range / self.period
                    + true_range
                )
                self.smoothed_positive_dm = (
                    self.smoothed_positive_dm
                    - self.smoothed_positive_dm / self.period
                    + positive_dm
                )
                self.smoothed_negative_dm = (
                    self.smoothed_negative_dm
                    - self.smoothed_negative_dm / self.period
                    + negative_dm
                )
                dx = self._directional_index()
                if self.adx_value is None:
                    self.dx_values.append(dx)
                    if len(self.dx_values) == self.period:
                        self.adx_value = sum(self.dx_values) / self.period
                else:
                    self.adx_value = (
                        self.adx_value * (self.period - 1) + dx
                    ) / self.period

        self.previous_high = bar.High
        self.previous_low = bar.Low
        self.previous_close = bar.Close

    def _directional_index(self):
        if not self.smoothed_true_range:
            return 0
        positive_di = (
            100 * self.smoothed_positive_dm / self.smoothed_true_range
        )
        negative_di = (
            100 * self.smoothed_negative_dm / self.smoothed_true_range
        )
        denominator = positive_di + negative_di
        if denominator == 0:
            return 0
        return 100 * abs(positive_di - negative_di) / denominator

    def allow_trade(self, direction):
        return self.is_ready() and self.adx_value >= self.threshold

    def name(self):
        return f"adx_strength_{self.period}_{self.threshold:g}"

    def regime(self):
        if not self.is_ready():
            return "not_ready"
        return "trend" if self.adx_value >= self.threshold else "range"


class AtrVolatilityFilterModel:
    def __init__(self, period, minimum_percent, maximum_percent):
        if period < 1:
            raise ValueError("ATR period must be >= 1")
        if minimum_percent < 0:
            raise ValueError("ATR minimum percent must be >= 0")
        if maximum_percent <= minimum_percent:
            raise ValueError(
                "ATR maximum percent must be greater than minimum percent"
            )

        self.period = period
        self.minimum_percent = float(minimum_percent)
        self.maximum_percent = float(maximum_percent)
        self.previous_close = None
        self.true_ranges = []
        self.atr_value = None
        self.atr_percent = None

    def is_ready(self):
        return self.atr_percent is not None

    def update(self, bar):
        if self.previous_close is not None:
            true_range = max(
                bar.High - bar.Low,
                abs(bar.High - self.previous_close),
                abs(bar.Low - self.previous_close)
            )
            if self.atr_value is None:
                self.true_ranges.append(true_range)
                if len(self.true_ranges) == self.period:
                    self.atr_value = sum(self.true_ranges) / self.period
            else:
                self.atr_value = (
                    self.atr_value * (self.period - 1) + true_range
                ) / self.period
            if self.atr_value is not None and bar.Close > 0:
                self.atr_percent = self.atr_value / bar.Close * 100
        self.previous_close = bar.Close

    def allow_trade(self, direction):
        return (
            self.is_ready()
            and self.minimum_percent <= self.atr_percent
            < self.maximum_percent
        )

    def name(self):
        return (
            f"atr_volatility_{self.period}_"
            f"{self.minimum_percent:g}_{self.maximum_percent:g}"
        )

    def regime(self):
        if not self.is_ready():
            return "not_ready"
        if self.atr_percent < self.minimum_percent:
            return "low_volatility"
        if self.atr_percent >= self.maximum_percent:
            return "high_volatility"
        return "eligible_volatility"


class FilterModelFactory:
    @staticmethod
    def create(
        filter_model_name,
        ema_fast,
        ema_slow,
        adx_period=14,
        adx_threshold=25,
        atr_period=14,
        atr_min_pct=1,
        atr_max_pct=10
    ):
        name = filter_model_name.lower()

        if name == "none":
            return NoFilterModel()

        if name == "ema_trend":
            return EmaTrendFilterModel(
                ema_fast,
                ema_slow
            )

        if name == "adx_strength":
            return AdxStrengthFilterModel(
                adx_period,
                adx_threshold
            )

        if name == "atr_volatility":
            return AtrVolatilityFilterModel(
                atr_period,
                atr_min_pct,
                atr_max_pct
            )

        raise ValueError(f"Unknown filter model: {filter_model_name}")
