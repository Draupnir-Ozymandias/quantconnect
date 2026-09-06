# region imports
from AlgorithmImports import *
# endregion


class NoRegimeModel:
    def is_ready(self):
        return False

    def update(self, bar):
        pass

    def regime(self):
        return "unobserved"

    def telemetry_value(self):
        return None

    def name(self):
        return "none"


class RocSignRegimeModel:
    """Classify prior-state momentum without controlling trade eligibility."""

    def __init__(self, lookback, threshold_percent=0):
        if lookback < 1:
            raise ValueError("ROC regime lookback must be >= 1")
        self.lookback = int(lookback)
        self.threshold_percent = float(threshold_percent)
        self.closes = []

    def is_ready(self):
        return len(self.closes) == self.lookback + 1

    def update(self, bar):
        self.closes.append(float(bar.Close))
        if len(self.closes) > self.lookback + 1:
            self.closes.pop(0)

    def telemetry_value(self):
        if not self.is_ready() or self.closes[0] == 0:
            return None
        return (self.closes[-1] / self.closes[0] - 1) * 100

    def regime(self):
        value = self.telemetry_value()
        if value is None:
            return "not_ready"
        if value > self.threshold_percent:
            return "positive"
        return "nonpositive"

    def name(self):
        return (
            f"roc_sign_{self.lookback}_"
            f"{self.threshold_percent:g}"
        )


class RegimeModelFactory:
    @staticmethod
    def create(model_name, lookback=20, threshold_percent=0):
        name = str(model_name).lower()
        if name == "none":
            return NoRegimeModel()
        if name == "roc_sign":
            return RocSignRegimeModel(lookback, threshold_percent)
        raise ValueError(f"Unknown regime model: {model_name}")
