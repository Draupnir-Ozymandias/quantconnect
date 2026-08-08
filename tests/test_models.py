import sys
import types
import unittest


sys.modules.setdefault("AlgorithmImports", types.ModuleType("AlgorithmImports"))

from entry_models import (
    CandleStreakEntryModel,
    EmaTrendEntryModel,
    MacdTrendEntryModel,
    RsiMeanReversionEntryModel
)
from filter_models import (
    AdxStrengthFilterModel,
    AtrVolatilityFilterModel,
    EmaTrendFilterModel
)
from metadata_models import ExperimentMetadataBuilder
from risk_models import RiskTracker
from stake_models import FlatStakeModel, MartingaleStakeModel
from stats_models import StatsTracker


class Bar:
    def __init__(self, open_price, close_price, high=None, low=None):
        self.Open = open_price
        self.Close = close_price
        self.High = high if high is not None else max(open_price, close_price)
        self.Low = low if low is not None else min(open_price, close_price)


class AlgorithmConfiguration:
    start_year = 2025
    start_month = 1
    start_day = 1
    end_year = 2025
    end_month = 12
    end_day = 31
    coin = "BTCUSD"
    timeframe = "1d"
    entry_model_name = "candle_streak"
    bias = "up"
    streak_length = 2
    streak_mode = "reverse"
    filter_model_name = "none"
    ema_fast = 5
    ema_slow = 10
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    adx_period = 14
    adx_threshold = 25
    atr_period = 14
    atr_min_pct = 1
    atr_max_pct = 10
    stake_mode = "flat"
    base_wager = 10.0
    initial_bankroll = 100000.0
    multiplier = 2.0
    max_steps = 10
    lab_version = "QCRL-2.2.0"
    git_commit = "abc123"
    git_branch = "main"
    campaign_id = "baseline"
    methodology_version = "qcrl.methodology.lookahead_free.v1"
    lookahead_status = "lookahead_free"
    record_status = "unvalidated"
    run_notes = ""


class ModelTests(unittest.TestCase):
    def test_candle_streak_uses_prior_bars(self):
        model = CandleStreakEntryModel(2, "reverse")

        self.assertIsNone(model.get_direction(Bar(10, 11)))
        self.assertIsNone(model.get_direction(Bar(11, 12)))
        self.assertEqual("down", model.get_direction(Bar(12, 13)))

    def test_ema_filter_requires_slow_period_samples(self):
        model = EmaTrendFilterModel(2, 3)

        model.update(Bar(9, 10))
        model.update(Bar(10, 11))
        self.assertFalse(model.is_ready())

        model.update(Bar(11, 12))
        self.assertTrue(model.is_ready())
        self.assertEqual("bullish", model.regime())
        self.assertTrue(model.allow_trade("up"))
        self.assertFalse(model.allow_trade("down"))

    def test_ema_signal_uses_prior_bar_state(self):
        model = EmaTrendEntryModel(2, 3)

        for close in [10, 11, 12]:
            self.assertIsNone(model.get_direction(Bar(close - 1, close)))
        self.assertEqual("up", model.get_direction(Bar(12, 1)))

    def test_macd_signal_uses_prior_bar_state(self):
        model = MacdTrendEntryModel(2, 3, 2)

        for close in [10, 11, 12, 13]:
            self.assertIsNone(model.get_direction(Bar(close - 1, close)))
        self.assertEqual("up", model.get_direction(Bar(13, 1)))

    def test_rsi_mean_reversion_uses_prior_bar_state(self):
        model = RsiMeanReversionEntryModel(2, 30, 70)

        self.assertIsNone(model.get_direction(Bar(9, 10)))
        self.assertIsNone(model.get_direction(Bar(8, 9)))
        self.assertIsNone(model.get_direction(Bar(7, 8)))
        self.assertEqual("up", model.get_direction(Bar(8, 20)))

    def test_adx_filter_detects_prior_trend_strength(self):
        model = AdxStrengthFilterModel(2, 25)

        for close in [10, 11, 12, 13]:
            model.update(Bar(close - 1, close, close + 1, close - 2))
        self.assertTrue(model.is_ready())
        self.assertEqual("trend", model.regime())
        self.assertTrue(model.allow_trade("up"))

    def test_atr_filter_uses_normalized_prior_volatility(self):
        model = AtrVolatilityFilterModel(2, 1, 10)

        model.update(Bar(99, 100, 102, 98))
        model.update(Bar(100, 101, 103, 99))
        self.assertFalse(model.is_ready())
        model.update(Bar(101, 102, 104, 100))
        self.assertTrue(model.is_ready())
        self.assertEqual("eligible_volatility", model.regime())
        self.assertTrue(model.allow_trade("down"))

    def test_martingale_recovery_cycle_earns_one_base_wager(self):
        risk = RiskTracker(100000, max_steps=10)
        stake = MartingaleStakeModel(10, 2)

        for won in [False, False, True]:
            wager = stake.get_wager(risk.loss_step)
            risk.record_trade(won, wager, is_martingale=True)

        self.assertEqual(10, risk.net_profit())
        self.assertEqual(0, risk.loss_step)
        self.assertEqual(40, risk.max_single_wager)
        self.assertFalse(risk.ruined)

    def test_flat_stake_does_not_escalate(self):
        stake = FlatStakeModel(10)
        self.assertEqual([10, 10, 10], [stake.get_wager(i) for i in range(3)])

    def test_stats_accounting(self):
        stats = StatsTracker()
        stats.record_bar()
        stats.record_signal("down")
        stats.record_executed("down")
        stats.record_trade_result("down", True, 20, 1, "bearish")

        self.assertEqual(1, stats.signals_generated)
        self.assertEqual(1, stats.signals_executed)
        self.assertEqual(1.0, stats.execution_rate())
        self.assertEqual(20, stats.total_wagered)
        self.assertEqual(1, stats.regime_stats["bearish"]["wins"])

    def test_metadata_ignores_inactive_parameters(self):
        first = AlgorithmConfiguration()
        second = AlgorithmConfiguration()
        second.ema_fast = 50
        second.ema_slow = 200
        second.macd_signal = 5
        second.rsi_period = 7
        second.adx_threshold = 40
        second.atr_min_pct = 2
        second.multiplier = 9
        second.max_steps = 99

        first_metadata = ExperimentMetadataBuilder.build(first)
        second_metadata = ExperimentMetadataBuilder.build(second)

        self.assertEqual(
            first_metadata["configuration_hash"],
            second_metadata["configuration_hash"]
        )

    def test_metadata_changes_for_active_parameter(self):
        first = AlgorithmConfiguration()
        second = AlgorithmConfiguration()
        second.streak_length = 3

        self.assertNotEqual(
            ExperimentMetadataBuilder.build(first)["experiment_id"],
            ExperimentMetadataBuilder.build(second)["experiment_id"]
        )

    def test_metadata_tracks_active_directional_parameters(self):
        first = AlgorithmConfiguration()
        second = AlgorithmConfiguration()
        first.entry_model_name = "macd_trend"
        second.entry_model_name = "macd_trend"
        second.macd_signal = 5

        self.assertNotEqual(
            ExperimentMetadataBuilder.build(first)["experiment_id"],
            ExperimentMetadataBuilder.build(second)["experiment_id"]
        )

    def test_metadata_tracks_active_gate_parameters(self):
        first = AlgorithmConfiguration()
        second = AlgorithmConfiguration()
        first.filter_model_name = "adx_strength"
        second.filter_model_name = "adx_strength"
        second.adx_threshold = 30

        self.assertNotEqual(
            ExperimentMetadataBuilder.build(first)["experiment_id"],
            ExperimentMetadataBuilder.build(second)["experiment_id"]
        )

    def test_provenance_does_not_change_experiment_identity(self):
        first = AlgorithmConfiguration()
        second = AlgorithmConfiguration()
        second.git_commit = "different-commit"
        second.git_branch = "feature/research"
        second.campaign_id = "another-campaign"

        first_metadata = ExperimentMetadataBuilder.build(first)
        second_metadata = ExperimentMetadataBuilder.build(second)

        self.assertEqual(
            first_metadata["experiment_id"],
            second_metadata["experiment_id"]
        )
        self.assertNotEqual(
            first_metadata["git_commit"],
            second_metadata["git_commit"]
        )


if __name__ == "__main__":
    unittest.main()
