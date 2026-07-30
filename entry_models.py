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


class EntryModelFactory:
    @staticmethod
    def create(
        entry_model_name,
        bias,
        streak_length=2,
        streak_mode="follow"
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

        raise ValueError(f"Unknown entry model: {entry_model_name}")
