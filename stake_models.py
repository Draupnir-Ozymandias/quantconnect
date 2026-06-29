# region imports
from AlgorithmImports import *
# endregion
# Stake Models
# ============
# Logic for position sizing and capital allocation.

# from typing import Dict
# from QuantConnect import QCAlgorithm

class FlatStakeModel:
    def __init__(self, base_wager):
        self.base_wager = base_wager

    def get_wager(self, loss_step):
        return self.base_wager


class MartingaleStakeModel:
    def __init__(self, base_wager, multiplier):
        self.base_wager = base_wager
        self.multiplier = multiplier

    def get_wager(self, loss_step):
        return self.base_wager * (self.multiplier ** loss_step)


class StakeModelFactory:
    @staticmethod
    def create(stake_mode, base_wager, multiplier):
        mode = stake_mode.lower()

        if mode == "flat":
            return FlatStakeModel(base_wager)

        if mode == "martingale":
            return MartingaleStakeModel(base_wager, multiplier)

        raise ValueError(f"Unknown stake mode: {stake_mode}")
