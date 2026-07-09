
from AlgorithmImports import *
from datetime import timedelta

from config import LabConfig
from entry_models import EntryModelFactory
from stake_models import StakeModelFactory
from risk_models import RiskTracker

from filter_models import FilterModelFactory
from stats_models import StatsTracker

from report_models import ResearchReport


class QuantConnectResearchLab(QCAlgorithm):

    def Param(self, name, default):
        value = self.get_parameter(name)

        if value is None or value == "":
            return default

        return value

    def Initialize(self):
        # ----------------------------
        # CONFIG / PARAMETERS
        # ----------------------------
        self.start_year = int(self.Param("start_year", LabConfig.START_YEAR))
        self.start_month = int(self.Param("start_month", LabConfig.START_MONTH))
        self.start_day = int(self.Param("start_day", LabConfig.START_DAY))

        self.end_year = int(self.Param("end_year", LabConfig.END_YEAR))
        self.end_month = int(self.Param("end_month", LabConfig.END_MONTH))
        self.end_day = int(self.Param("end_day", LabConfig.END_DAY))

        self.coin = self.Param("coin", LabConfig.COIN)
        self.timeframe = self.Param("timeframe", LabConfig.TIMEFRAME)

        self.entry_model_name = self.Param("entry_model", LabConfig.ENTRY_MODEL)
        self.bias = self.Param("bias", LabConfig.BIAS).lower()

        self.streak_length = int(
        self.Param("streak_length", LabConfig.STREAK_LENGTH))

        self.streak_mode = self.Param("streak_mode", LabConfig.STREAK_MODE).lower()

        self.stake_mode = self.Param("stake_mode", LabConfig.STAKE_MODE).lower()
        self.base_wager = float(self.Param("base_wager", LabConfig.BASE_WAGER))
        self.initial_bankroll = float(self.Param("bankroll", LabConfig.BANKROLL))
        self.multiplier = float(self.Param("multiplier", LabConfig.MULTIPLIER))
        self.max_steps = int(self.Param("max_steps", LabConfig.MAX_STEPS))

        self.filter_model_name = self.Param("filter_model", LabConfig.FILTER_MODEL).lower()

        self.ema_fast = int(
        self.Param("ema_fast", LabConfig.EMA_FAST))

        self.ema_slow = int(
        self.Param("ema_slow", LabConfig.EMA_SLOW))

        # ----------------------------
        # QUANTCONNECT SETUP
        # ----------------------------
        self.set_start_date(self.start_year, self.start_month, self.start_day)
        self.set_end_date(self.end_year, self.end_month, self.end_day)
        self.set_cash(self.initial_bankroll)


        self.set_brokerage_model(BrokerageName.COINBASE, AccountType.CASH)

        crypto = self.add_crypto(
            self.coin,
            Resolution.MINUTE,
            Market.COINBASE
        )

        self.crypto_symbol = crypto.Symbol

        # ----------------------------
        # MODELS
        # ----------------------------
        self.entry_model = EntryModelFactory.create(
            self.entry_model_name,
            self.bias,
            self.streak_length,
            self.streak_mode
        )

        self.stake_model = StakeModelFactory.create(
            self.stake_mode,
            self.base_wager,
            self.multiplier
        )

        self.risk = RiskTracker(
            self.initial_bankroll,
            self.max_steps
        )

        self.filter_model = FilterModelFactory.create(
            self.filter_model_name,
            self.ema_fast,
            self.ema_slow
        )

        self.stats = StatsTracker()

        # ----------------------------
        # CONSOLIDATOR
        # ----------------------------
        period = self.GetTimeframeDelta(self.timeframe)

        consolidator = TradeBarConsolidator(period)
        consolidator.DataConsolidated += self.OnPolymarketBar

        self.SubscriptionManager.AddConsolidator(
            self.crypto_symbol,
            consolidator
        )

        self.Debug(
            f"Started QuantConnect Research Lab | "
            f"Coin={self.coin}, "
            f"TF={self.timeframe}, "
            f"Entry={self.entry_model_name}, "
            f"Bias={self.bias}, "
            f"Stake={self.stake_mode}, "
            f"Base={self.base_wager}"
        )

        self.lab_version = self.Param("lab_version", LabConfig.LAB_VERSION)

        self.experiment_id = self.Param("experiment_id", LabConfig.EXPERIMENT_ID)
        self.experiment_group = self.Param("experiment_group", LabConfig.EXPERIMENT_GROUP)
        self.experiment_name = self.Param("experiment_name", LabConfig.EXPERIMENT_NAME)
        self.experiment_notes = self.Param("experiment_notes", LabConfig.EXPERIMENT_NOTES)
        self.experiment_tags = self.Param("experiment_tags", LabConfig.EXPERIMENT_TAGS)

        self.experiment_year = int(self.Param("experiment_year", LabConfig.EXPERIMENT_YEAR))
        self.experiment_asset = self.Param("experiment_asset", LabConfig.EXPERIMENT_ASSET)
        self.experiment_timeframe = self.Param("experiment_timeframe", LabConfig.EXPERIMENT_TIMEFRAME)
        self.experiment_family = self.Param("experiment_family", LabConfig.EXPERIMENT_FAMILY)


    def GetTimeframeDelta(self, tf):
        tf = tf.lower()

        if tf == "5m":
            return timedelta(minutes=5)

        if tf == "15m":
            return timedelta(minutes=15)

        if tf == "1h":
            return timedelta(hours=1)

        if tf == "1d":
            return timedelta(days=1)

        raise ValueError("Invalid timeframe. Use: 5m, 15m, 1h, or 1d")

    def OnPolymarketBar(self, sender, bar):
        self.stats.record_bar()

        if self.risk.ruined:
            self.stats.record_ruined_skip()
            return

        direction = self.entry_model.get_direction(bar)

        self.filter_model.update(bar)

        if direction is None:
            self.stats.record_no_direction()
            return

        self.stats.record_signal(direction)

        if not self.filter_model.is_ready():
            self.stats.record_filter_not_ready()
            return

        if not self.filter_model.allow_trade(direction):
            self.stats.record_filter_rejected()
            return

        if bar.Close == bar.Open:
            self.stats.record_tie()
            return

        if direction == "up":
            won = bar.Close > bar.Open
        elif direction == "down":
            won = bar.Close < bar.Open
        else:
            raise ValueError(f"Invalid direction: {direction}")


        recovery_level = self.risk.loss_step

        wager = self.stake_model.get_wager(
            recovery_level
        )

        if not self.risk.can_place_wager(wager, self.Time):
            self.Debug(f"RUIN at {self.Time} | {self.risk.ruin_reason}")
            return

        self.stats.record_executed(direction)

        drawdown = self.risk.record_trade(won, wager, self.Time)

        self.stats.record_trade_result(
            direction,
            won,
            wager,
            recovery_level,
            self.filter_model.regime()
        )


        if self.risk.ruined:
            self.Debug(f"RUIN at {self.Time} | {self.risk.ruin_reason}")

        self.Plot("Polymarket Lab", "Bankroll", self.risk.bankroll)
        self.Plot("Polymarket Lab", "Drawdown", drawdown)
        self.Plot("Polymarket Lab", "Loss Step", self.risk.loss_step)

    def OnEndOfAlgorithm(self):

        self.risk.finalize()

        self.Debug("========== FINAL RESULTS ==========")
        self.Debug(f"Coin: {self.coin}")
        self.Debug(f"Timeframe: {self.timeframe}")
        self.Debug(f"Entry model: {self.entry_model_name}")
        self.Debug(f"Bias: {self.bias}")
        self.Debug(f"Stake mode: {self.stake_mode}")
        self.Debug(f"Initial bankroll: {self.risk.initial_bankroll:.2f}")
        self.Debug(f"Final bankroll: {self.risk.bankroll:.2f}")
        self.Debug(f"Net profit: {self.risk.net_profit():.2f}")
        self.Debug(f"Trades: {self.risk.trades}")
        self.Debug(f"Wins: {self.risk.wins}")
        self.Debug(f"Losses: {self.risk.losses}")
        self.Debug(f"Win rate: {self.risk.win_rate():.2%}")
        self.Debug(f"Max drawdown: {self.risk.max_drawdown:.2f}")
        self.Debug(f"Max single wager: {self.risk.max_single_wager:.2f}")
        self.Debug(f"Final loss step: {self.risk.loss_step}")
        self.Debug(f"Ruined: {self.risk.ruined}")
        self.Debug(f"Max win streak: {self.risk.max_win_streak}")
        self.Debug(f"Max loss streak: {self.risk.max_loss_streak}")
        self.Debug(f"Average recovery depth: {self.risk.average_recovery_depth():.2f}")
        self.Debug(f"Max recovery depth: {self.risk.max_recovery_depth()}")
        self.Debug(f"Win streak histogram: {self.risk.win_streak_histogram_text()}")
        self.Debug(f"Loss streak histogram: {self.risk.loss_streak_histogram_text()}")
        self.Debug(f"End Time: {self.Time}")
        self.ruin_time = self.Time
        self.Debug(f"Ruin Time: {self.risk.ruin_time}")

        self.Debug("========== STATS ==========")
        self.Debug(f"Filter model: {self.filter_model.name()}")
        self.Debug(f"Bars seen: {self.stats.bars_seen}")
        self.Debug(f"Signals generated: {self.stats.signals_generated}")
        self.Debug(f"Signals executed: {self.stats.signals_executed}")
        self.Debug(f"Execution rate: {self.stats.execution_rate():.2%}")
        self.Debug(f"Filter rate: {self.stats.filter_rate():.2%}")
        self.Debug(f"Skipped - no direction: {self.stats.signals_skipped_no_direction}")
        self.Debug(f"Skipped - filter not ready: {self.stats.signals_skipped_filter_not_ready}")
        self.Debug(f"Skipped - filter rejected: {self.stats.signals_skipped_filter_rejected}")
        self.Debug(f"Skipped - tie: {self.stats.signals_skipped_tie}")
        self.Debug(f"Skipped - ruined: {self.stats.signals_skipped_ruined}")
        self.Debug(f"UP signals: {self.stats.up_signals}")
        self.Debug(f"DOWN signals: {self.stats.down_signals}")
        self.Debug(f"UP executed: {self.stats.up_executed}")
        self.Debug(f"DOWN executed: {self.stats.down_executed}")

        self.Debug(f"Executed wins: {self.stats.executed_wins}")
        self.Debug(f"Executed losses: {self.stats.executed_losses}")
        self.Debug(f"Executed win rate: {self.stats.executed_win_rate():.2%}")
        self.Debug(f"Total wagered: {self.stats.total_wagered:.2f}")
        self.Debug(f"Average wager: {self.stats.average_wager():.2f}")
        self.Debug(f"Max wager seen by StatsTracker: {self.stats.max_wager_seen:.2f}")
        self.Debug(f"Recovery level distribution: {self.stats.recovery_level_text()}")
        self.Debug("Regime stats:")

        for line in self.stats.regime_lines():
            self.Debug(line)

        report = ResearchReport.build(self)

        self.Debug(ResearchReport.summary_line(report))

        key = ResearchReport.object_store_key(report)
        self.ObjectStore.Save(
            key,
            ResearchReport.pretty_json(report)
        )

        self.Debug(f"Saved report: {key}")

        if self.risk.ruined:
            self.Debug(f"Ruin reason: {self.risk.ruin_reason}")
