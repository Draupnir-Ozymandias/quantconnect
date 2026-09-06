# region imports
from AlgorithmImports import *
# endregion


class LabConfig:
    START_YEAR = 2024
    START_MONTH = 1
    START_DAY = 1

    END_YEAR = 2024
    END_MONTH = 12
    END_DAY = 31

    COIN = "BTCUSD"
    TIMEFRAME = "1d"  # 5m, 15m, 1h, 1d

    # none, ema_trend, adx_strength, atr_volatility
    FILTER_MODEL = "ema_trend"
    EMA_FAST = 5
    EMA_SLOW = 10
    ADX_PERIOD = 14
    ADX_THRESHOLD = 25
    ATR_PERIOD = 14
    ATR_MIN_PCT = 1
    ATR_MAX_PCT = 10

    # Observational only: records prior-state market context without gating.
    # none, roc_sign
    REGIME_MODEL = "none"
    REGIME_LOOKBACK = 20
    REGIME_THRESHOLD_PCT = 0

    # fixed_bias, previous_candle, previous_candle_reverse, candle_streak,
    # ema_trend, macd_trend, rsi_mean_reversion
    ENTRY_MODEL = "candle_streak"
    BIAS = "up"  # up, down

    STREAK_LENGTH = 2
    STREAK_MODE = "reverse"  # follow, reverse
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    STAKE_MODE = "flat"  # flat, martingale
    BASE_WAGER = 10
    BANKROLL = 100000
    MULTIPLIER = 2
    MAX_STEPS = 10

    # Disable during optimizations. Enable only for visual inspection.
    ENABLE_PLOTS = False
    PLOT_EVERY_N_BARS = 100

    # Metadata facts are generated from runtime values.
    LAB_VERSION = "QCRL-2.3.0"

    # The synchronization script overrides these for CLI backtests.
    GIT_COMMIT = "unknown"
    GIT_BRANCH = "unknown"
    CAMPAIGN_ID = "manual"

    # Optional analyst note only. Do not repeat factual configuration here.
    RUN_NOTES = ""
