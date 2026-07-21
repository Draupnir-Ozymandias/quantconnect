# region imports
from AlgorithmImports import *
# endregion
class LabConfig:
    START_YEAR = 2026
    START_MONTH = 1
    START_DAY = 1

    END_YEAR = 2026
    END_MONTH = 7
    END_DAY = 7

    COIN = "BTCUSD"
    TIMEFRAME = "5m"  # 5m, 15m, 1h, 1d

    FILTER_MODEL = "ema_trend"  # none, ema_trend
    EMA_FAST = 5
    EMA_SLOW = 10

    # fixed_bias, previous_candle, previous_candle_reverse, candle_streak
    ENTRY_MODEL = "candle_streak"  
    BIAS = "up"  # up, down

    STREAK_LENGTH = 2
    STREAK_MODE = "reverse"  # follow, reverse

    STAKE_MODE = "martingale"  # flat, martingale
    BASE_WAGER = 10
    BANKROLL = 100000
    MULTIPLIER = 2
    MAX_STEPS = 10


    # ----------------------------
    # LAB / EXPERIMENT METADATA
    # ----------------------------
    LAB_VERSION = "QCRL-2.1.0"

    EXPERIMENT_ID = "exp_0015_btcusd_5m_2026_ema_streak_reverse"
    EXPERIMENT_GROUP = "btcusd_2026"
    EXPERIMENT_NAME = "BTCUSD 5m 2026 EMA Trend + 2-Bar Streak Reverse"
    EXPERIMENT_NOTES = "Baseline 5m BTCUSD optimization for EMA trend filter with candle_streak reverse."
    EXPERIMENT_TAGS = "btcusd,5m,2026,ema,candle_streak,martingale"

    EXPERIMENT_YEAR = 2026
    EXPERIMENT_ASSET = "BTCUSD"
    EXPERIMENT_TIMEFRAME = "5m"
    EXPERIMENT_FAMILY = "ema_streak_reverse"

    
    
