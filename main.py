from AlgorithmImports import *

import calendar
from datetime import timedelta

from config import LabConfig
from entry_models import EntryModelFactory
from stake_models import StakeModelFactory
from risk_models import RiskTracker
from filter_models import FilterModelFactory
from stats_models import StatsTracker
from metadata_models import ExperimentMetadataBuilder
from report_models import ResearchReport
from experiment_store import ExperimentStore


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
        self.start_year = int(
            self.Param("start_year", LabConfig.START_YEAR)
        )
        self.start_month = int(
            self.Param("start_month", LabConfig.START_MONTH)
        )
        self.start_day = int(
            self.Param("start_day", LabConfig.START_DAY)
        )

        self.end_year = int(
            self.Param("end_year", LabConfig.END_YEAR)
        )
        self.end_month = int(
            self.Param("end_month", LabConfig.END_MONTH)
        )
        self.end_day = int(
            self.Param("end_day", LabConfig.END_DAY)
        )

        last_valid_end_day = calendar.monthrange(
            self.end_year,
            self.end_month
        )[1]

        if self.end_day > last_valid_end_day:
            self.Debug(
                f"Adjusted invalid end date: "
                f"{self.end_year}-{self.end_month:02d}-{self.end_day:02d} "
                f"to {self.end_year}-{self.end_month:02d}-{last_valid_end_day:02d}"
        )

            self.end_day = last_valid_end_day

        self.coin = self.Param(
            "coin",
            LabConfig.COIN
        )
        self.timeframe = self.Param(
            "timeframe",
            LabConfig.TIMEFRAME
        ).lower()

        self.entry_model_name = self.Param(
            "entry_model",
            LabConfig.ENTRY_MODEL
        ).lower()
        self.bias = self.Param(
            "bias",
            LabConfig.BIAS
        ).lower()

        self.streak_length = int(
            self.Param(
                "streak_length",
                LabConfig.STREAK_LENGTH
            )
        )
        self.streak_mode = self.Param(
            "streak_mode",
            LabConfig.STREAK_MODE
        ).lower()

        self.stake_mode = self.Param(
            "stake_mode",
            LabConfig.STAKE_MODE
        ).lower()
        self.base_wager = float(
            self.Param(
                "base_wager",
                LabConfig.BASE_WAGER
            )
        )
        self.initial_bankroll = float(
            self.Param(
                "bankroll",
                LabConfig.BANKROLL
            )
        )
        self.multiplier = float(
            self.Param(
                "multiplier",
                LabConfig.MULTIPLIER
            )
        )
        self.max_steps = int(
            self.Param(
                "max_steps",
                LabConfig.MAX_STEPS
            )
        )

        self.filter_model_name = self.Param(
            "filter_model",
            LabConfig.FILTER_MODEL
        ).lower()
        self.ema_fast = int(
            self.Param(
                "ema_fast",
                LabConfig.EMA_FAST
            )
        )
        self.ema_slow = int(
            self.Param(
                "ema_slow",
                LabConfig.EMA_SLOW
            )
        )

        self.enable_plots = (
            str(
                self.Param(
                    "enable_plots",
                    LabConfig.ENABLE_PLOTS
                )
            ).lower()
            == "true"
        )

        self.plot_every_n_bars = max(
            1,
            int(
                self.Param(
                    "plot_every_n_bars",
                    LabConfig.PLOT_EVERY_N_BARS
                )
            )
        )

        self.lab_version = self.Param(
            "lab_version",
            LabConfig.LAB_VERSION
        )

        self.run_notes = self.Param(
            "run_notes",
            LabConfig.RUN_NOTES
        )

        self.git_commit = self.Param(
            "git_commit",
            LabConfig.GIT_COMMIT
        )
        self.git_branch = self.Param(
            "git_branch",
            LabConfig.GIT_BRANCH
        )
        self.campaign_id = self.Param(
            "campaign_id",
            LabConfig.CAMPAIGN_ID
        )

        self.methodology_version = (
            "qcrl.methodology.lookahead_free.v1"
        )
        self.lookahead_status = "lookahead_free"
        self.record_status = "unvalidated"

        self.engine_version = "LEAN"

        # ----------------------------
        # QUANTCONNECT SETUP
        # ----------------------------
        self.set_start_date(
            self.start_year,
            self.start_month,
            self.start_day
        )
        self.set_end_date(
            self.end_year,
            self.end_month,
            self.end_day
        )
        self.set_cash(self.initial_bankroll)

        self.set_brokerage_model(
            BrokerageName.COINBASE,
            AccountType.CASH
        )

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

        # Factual metadata is generated from the resolved runtime values.
        self.experiment_metadata = (
            ExperimentMetadataBuilder.build(self)
        )

        # ----------------------------
        # CONSOLIDATOR
        # ----------------------------
        period = self.GetTimeframeDelta(
            self.timeframe
        )

        consolidator = TradeBarConsolidator(period)
        consolidator.DataConsolidated += (
            self.OnPolymarketBar
        )

        self.SubscriptionManager.AddConsolidator(
            self.crypto_symbol,
            consolidator
        )

        self.Debug(
            f"Started QuantConnect Research Lab | "
            f"Coin={self.coin}, "
            f"TF={self.timeframe}, "
            f"Entry={self.entry_model_name}, "
            f"Filter={self.filter_model.name()}, "
            f"Stake={self.stake_mode}, "
            f"Base={self.base_wager}"
        )

        self.Debug(
            f"Experiment ID: "
            f"{self.experiment_metadata['experiment_id']} | "
            f"Group: "
            f"{self.experiment_metadata['experiment_group']} | "
            f"Family: "
            f"{self.experiment_metadata['experiment_family']}"
        )

    def GetTimeframeDelta(self, timeframe):
        timeframe = timeframe.lower()

        if timeframe == "5m":
            return timedelta(minutes=5)

        if timeframe == "15m":
            return timedelta(minutes=15)

        if timeframe == "1h":
            return timedelta(hours=1)

        if timeframe == "1d":
            return timedelta(days=1)

        raise ValueError(
            "Invalid timeframe. Use: 5m, 15m, 1h, or 1d"
        )

    def PlotStateIfDue(self):
        if not self.enable_plots:
            return

        if (
            self.stats.bars_seen
            % self.plot_every_n_bars
            != 0
        ):
            return

        current_drawdown = (
            self.risk.peak_bankroll
            - self.risk.bankroll
        )

        self.Plot(
            "Polymarket Lab",
            "Bankroll",
            self.risk.bankroll
        )
        self.Plot(
            "Polymarket Lab",
            "Drawdown",
            current_drawdown
        )
        self.Plot(
            "Polymarket Lab",
            "Loss Step",
            self.risk.loss_step
        )

    def OnPolymarketBar(self, sender, bar):
        self.stats.record_bar()
        self.PlotStateIfDue()

        if self.risk.ruined:
            self.stats.record_ruined_skip()
            return

        # Entry models decide using their state from prior bars, then update
        # themselves with the current bar for the next decision.
        direction = self.entry_model.get_direction(bar)

        # Capture the filter decision BEFORE updating it with the current
        # bar. This prevents current-close look-ahead bias.
        filter_ready = self.filter_model.is_ready()
        filter_regime = self.filter_model.regime()

        filter_allowed = False

        if direction is not None and filter_ready:
            filter_allowed = (
                self.filter_model.allow_trade(direction)
            )

        # Current bar updates filter state only for the next bar.
        self.filter_model.update(bar)

        if direction is None:
            self.stats.record_no_direction()
            return

        self.stats.record_signal(direction)

        if not filter_ready:
            self.stats.record_filter_not_ready()
            return

        if not filter_allowed:
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
            raise ValueError(
                f"Invalid direction: {direction}"
            )

        recovery_level = self.risk.loss_step

        wager = self.stake_model.get_wager(
            recovery_level
        )

        if not self.risk.can_place_wager(
            wager,
            self.Time
        ):
            self.Debug(
                f"RUIN at {self.Time} | "
                f"{self.risk.ruin_reason}"
            )
            return

        self.stats.record_executed(direction)

        is_martingale = (
            self.stake_mode == "martingale"
        )

        self.risk.record_trade(
            won,
            wager,
            self.Time,
            is_martingale=is_martingale
        )

        self.stats.record_trade_result(
            direction,
            won,
            wager,
            recovery_level,
            filter_regime
        )

        if self.risk.ruined:
            self.Debug(
                f"RUIN at {self.Time} | "
                f"{self.risk.ruin_reason}"
            )

    def OnEndOfAlgorithm(self):
        self.risk.finalize()

        self.Debug(
            "========== FINAL RESULTS =========="
        )
        self.Debug(f"Coin: {self.coin}")
        self.Debug(f"Timeframe: {self.timeframe}")
        self.Debug(
            f"Entry model: {self.entry_model_name}"
        )
        self.Debug(f"Bias: {self.bias}")
        self.Debug(f"Stake mode: {self.stake_mode}")
        self.Debug(
            f"Initial bankroll: "
            f"{self.risk.initial_bankroll:.2f}"
        )
        self.Debug(
            f"Final bankroll: "
            f"{self.risk.bankroll:.2f}"
        )
        self.Debug(
            f"Net profit: "
            f"{self.risk.net_profit():.2f}"
        )
        self.Debug(f"Trades: {self.risk.trades}")
        self.Debug(f"Wins: {self.risk.wins}")
        self.Debug(f"Losses: {self.risk.losses}")
        self.Debug(
            f"Win rate: {self.risk.win_rate():.2%}"
        )
        self.Debug(
            f"Max drawdown: "
            f"{self.risk.max_drawdown:.2f}"
        )
        self.Debug(
            f"Max single wager: "
            f"{self.risk.max_single_wager:.2f}"
        )
        self.Debug(
            f"Final loss step: "
            f"{self.risk.loss_step}"
        )
        self.Debug(f"Ruined: {self.risk.ruined}")
        self.Debug(
            f"Max win streak: "
            f"{self.risk.max_win_streak}"
        )
        self.Debug(
            f"Max loss streak: "
            f"{self.risk.max_loss_streak}"
        )
        self.Debug(
            f"Average recovery depth: "
            f"{self.risk.average_recovery_depth():.2f}"
        )
        self.Debug(
            f"Max recovery depth: "
            f"{self.risk.max_recovery_depth()}"
        )
        self.Debug(
            f"Win streak histogram: "
            f"{self.risk.win_streak_histogram_text()}"
        )
        self.Debug(
            f"Loss streak histogram: "
            f"{self.risk.loss_streak_histogram_text()}"
        )
        self.Debug(f"End Time: {self.Time}")
        self.Debug(
            f"Ruin Time: {self.risk.ruin_time}"
        )

        self.Debug("========== STATS ==========")
        self.Debug(
            f"Filter model: "
            f"{self.filter_model.name()}"
        )
        self.Debug(
            f"Bars seen: {self.stats.bars_seen}"
        )
        self.Debug(
            f"Signals generated: "
            f"{self.stats.signals_generated}"
        )
        self.Debug(
            f"Signals executed: "
            f"{self.stats.signals_executed}"
        )
        self.Debug(
            f"Execution rate: "
            f"{self.stats.execution_rate():.2%}"
        )
        self.Debug(
            f"Filter rate: "
            f"{self.stats.filter_rate():.2%}"
        )
        self.Debug(
            f"Skipped - no direction: "
            f"{self.stats.signals_skipped_no_direction}"
        )
        self.Debug(
            f"Skipped - filter not ready: "
            f"{self.stats.signals_skipped_filter_not_ready}"
        )
        self.Debug(
            f"Skipped - filter rejected: "
            f"{self.stats.signals_skipped_filter_rejected}"
        )
        self.Debug(
            f"Skipped - tie: "
            f"{self.stats.signals_skipped_tie}"
        )
        self.Debug(
            f"Skipped - ruined: "
            f"{self.stats.signals_skipped_ruined}"
        )
        self.Debug(
            f"UP signals: {self.stats.up_signals}"
        )
        self.Debug(
            f"DOWN signals: {self.stats.down_signals}"
        )
        self.Debug(
            f"UP executed: {self.stats.up_executed}"
        )
        self.Debug(
            f"DOWN executed: "
            f"{self.stats.down_executed}"
        )
        self.Debug(
            f"Executed wins: "
            f"{self.stats.executed_wins}"
        )
        self.Debug(
            f"Executed losses: "
            f"{self.stats.executed_losses}"
        )
        self.Debug(
            f"Executed win rate: "
            f"{self.stats.executed_win_rate():.2%}"
        )
        self.Debug(
            f"Total wagered: "
            f"{self.stats.total_wagered:.2f}"
        )
        self.Debug(
            f"Average wager: "
            f"{self.stats.average_wager():.2f}"
        )
        self.Debug(
            f"Max wager seen by StatsTracker: "
            f"{self.stats.max_wager_seen:.2f}"
        )
        self.Debug(
            f"Recovery level distribution: "
            f"{self.stats.recovery_level_text()}"
        )
        self.Debug("Regime stats:")

        for line in self.stats.regime_lines():
            self.Debug(line)

        report = ResearchReport.build(self)

        self.Debug(
            ResearchReport.summary_line(report)
        )

        store = ExperimentStore(self.ObjectStore)
        record = store.save_report_and_record(
            report
        )

        persistence = record.get(
            "_persistence",
            {}
        )

        if persistence.get("report_saved"):
            self.Debug(
                f"Saved canonical report: "
                f"{record['objectstore_report_key']}"
            )
            self.Debug(
                "Normalized record will be generated "
                "from the report during retrieval."
            )
        else:
            error = persistence.get("error")

            self.Error(
                f"REPORT NOT SAVED | "
                f"Run ID={record['run_id']} | "
                f"Error={error or 'ObjectStore save failed'}"
            )

        self.Debug(
            f"Run ID: {record['run_id']}"
        )

        if self.risk.ruined:
            self.Debug(
                f"Ruin reason: "
                f"{self.risk.ruin_reason}"
            )
