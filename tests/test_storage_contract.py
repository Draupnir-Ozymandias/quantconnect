import sys
import types
import unittest


sys.modules.setdefault("AlgorithmImports", types.ModuleType("AlgorithmImports"))

from experiment_store import ExperimentStore
from report_models import ResearchReport
from research_tools import ResearchTools


class MemoryObjectStore:
    def __init__(self, save_result=True):
        self.values = {}
        self.save_result = save_result

    @property
    def keys(self):
        return list(self.values.keys())

    def contains_key(self, key):
        return key in self.values

    def read(self, key):
        return self.values[key]

    def save(self, key, value):
        if self.save_result is not False:
            self.values[key] = value
        return self.save_result


def sample_report(run_id="run-2025-flat"):
    return {
        "metadata": {
            "schema_version": ResearchReport.REPORT_SCHEMA_VERSION,
            "record_schema_version": ResearchReport.RECORD_SCHEMA_VERSION,
            "run_id": run_id,
            "generated_at_utc": "2026-08-07T12:00:00Z",
            "completed_at_algorithm_time": "2026-01-01 00:00:00",
            "engine_version": "LEAN-test",
            "lab_version": "QCRL-2.2.0",
            "git_commit": "abc123",
            "git_branch": "main",
            "campaign_id": "baseline",
            "methodology_version": "qcrl.methodology.lookahead_free.v1",
            "lookahead_status": "lookahead_free",
            "record_status": "unvalidated",
            "metadata_version": "qcrl.metadata.v1",
            "metadata_source": "runtime_generated",
            "configuration_hash": "abc123",
            "experiment_id": "exp_abc123",
            "experiment_group": "btcusd_2025_1d_flat",
            "experiment_name": "Control",
            "experiment_notes": "test",
            "experiment_tags": ["control"],
            "experiment_family": "candle_streak_reverse_ema_trend_flat"
        },
        "configuration": {
            "coin": "BTCUSD",
            "timeframe": "1d",
            "entry_model": "candle_streak",
            "bias": "up",
            "filter_model": "ema_trend_5_10",
            "filter_model_type": "ema_trend",
            "stake_mode": "flat",
            "streak_length": 2,
            "streak_mode": "reverse",
            "ema_fast": 5,
            "ema_slow": 10,
            "base_wager": 10,
            "bankroll": 100000,
            "multiplier": 2,
            "max_steps": 10,
            "start": "2025-01-01",
            "end": "2025-12-31"
        },
        "performance": {
            "initial_bankroll": 100000,
            "final_bankroll": 100120,
            "net_profit": 120,
            "trades": 58,
            "wins": 35,
            "losses": 23,
            "win_rate": 35 / 58
        },
        "risk": {
            "ruined": False,
            "ruin_time": None,
            "ruin_reason": "",
            "max_drawdown": 50,
            "max_single_wager": 10,
            "max_win_streak": 8,
            "max_loss_streak": 5,
            "average_recovery_depth": 1.77,
            "max_recovery_depth": 5,
            "win_streak_histogram": {"1": 7},
            "loss_streak_histogram": {"1": 8}
        },
        "analytics": {
            "bars_seen": 365,
            "signals_generated": 100,
            "signals_executed": 58,
            "execution_rate": 0.58,
            "filter_rate": 0.42,
            "executed_win_rate": 35 / 58,
            "total_wagered": 580,
            "average_wager": 10,
            "up_signals": 52,
            "down_signals": 48,
            "up_executed": 30,
            "down_executed": 28
        },
        "scores": {
            "survival_score": 1,
            "risk_adjusted_score": 0.39,
            "tail_risk_score": 5
        }
    }


class StorageContractTests(unittest.TestCase):
    def test_canonical_report_round_trip(self):
        object_store = MemoryObjectStore()
        store = ExperimentStore(object_store)
        report = sample_report()

        saved_record = store.save_report_and_record(report)
        loaded_records = store.load_all(include_legacy=False)

        self.assertTrue(saved_record["_persistence"]["report_saved"])
        self.assertEqual(1, len(object_store.values))
        self.assertEqual(1, len(loaded_records))
        self.assertEqual("run-2025-flat", loaded_records[0]["run_id"])
        self.assertEqual("abc123", loaded_records[0]["git_commit"])
        self.assertEqual("baseline", loaded_records[0]["campaign_id"])
        self.assertEqual(
            "qcrl.methodology.lookahead_free.v1",
            loaded_records[0]["methodology_version"]
        )
        self.assertEqual(report, store.load_report("run-2025-flat"))

    def test_qcrl_summary_statistics_expose_native_objectives(self):
        record = ResearchReport.normalized_record(sample_report())
        statistics = ResearchReport.summary_statistics(record)

        self.assertEqual(120, statistics["QCRL Net Profit"])
        self.assertEqual(0.39, statistics["QCRL Risk Adjusted Score"])
        self.assertEqual(52, statistics["QCRL Up Signals"])
        self.assertEqual("run-2025-flat", statistics["QCRL Run Id"])

    def test_explicit_save_failure_is_truthful(self):
        store = ExperimentStore(MemoryObjectStore(save_result=False))
        record = store.save_report_and_record(sample_report())

        self.assertFalse(record["_persistence"]["report_saved"])

    def test_research_tools_deduplicates_same_configuration(self):
        object_store = MemoryObjectStore()
        first = sample_report("older-run")
        second = sample_report("newer-run")
        second["metadata"]["generated_at_utc"] = "2026-08-08T12:00:00Z"

        store = ExperimentStore(object_store)
        store.save_report_and_record(first)
        store.save_report_and_record(second)

        tools = ResearchTools(store=store)
        tools.load(refresh=True, include_legacy=False)
        deduplicated = tools.dedupe()

        self.assertEqual(1, len(deduplicated))
        self.assertEqual("newer-run", deduplicated[0]["run_id"])


if __name__ == "__main__":
    unittest.main()
