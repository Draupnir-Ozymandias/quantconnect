# region imports
from AlgorithmImports import *
# endregion
class LabConfig:
    START_YEAR = 2025
    START_MONTH = 1
    START_DAY = 1

    END_YEAR = 2025
    END_MONTH = 12
    END_DAY = 31

    COIN = "BTCUSD"
    TIMEFRAME = "1h"  # 5m, 15m, 1h, 1d

    FILTER_MODEL = "ema_trend"  # none, ema_trend
    EMA_FAST = 20
    EMA_SLOW = 50

    # fixed_bias, previous_candle, previous_candle_reverse, candle_streak
    ENTRY_MODEL = "candle_streak"  
    BIAS = "up"  # up, down

    STREAK_LENGTH = 2
    STREAK_MODE = "follow"  # follow, reverse

    STAKE_MODE = "martingale"  # flat, martingale
    BASE_WAGER = 10
    BANKROLL = 100000
    MULTIPLIER = 2
    MAX_STEPS = 10
