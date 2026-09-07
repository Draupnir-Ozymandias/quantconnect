import copy
import json
from pathlib import Path
import unittest

from execution_truth import (
    ContractError,
    bind_signal_to_market,
    materialize_boundary_signal,
    normalize_bundle,
    normalize_source_bar,
    normalize_source_contract,
)


SPECS = Path(__file__).parents[1] / "execution_truth" / "specs"
LIVE_EVIDENCE = Path(__file__).parents[1] / "evidence" / "polymarket" / "live"


def spec(name):
    return json.loads((SPECS / name).read_text(encoding="utf-8"))


def source_contract():
    return normalize_source_contract(spec("qcrl_btcusd_1d_source.json"))


def signal_spec(**updates):
    value = spec("qcrl_candle_streak_2_reverse.json")
    value.update(updates)
    return value


def bar(day, open_price, close_price, *, available=None):
    start = f"2026-05-{day:02d}T00:00:00Z"
    end = f"2026-05-{day + 1:02d}T00:00:00Z"
    return {
        "schema_version": "qcrl.directional_source_bar.v1",
        "source_contract_sha256": source_contract()["contract_sha256"],
        "start_at_utc": start,
        "end_at_utc": end,
        "available_at_utc": available or end,
        "open": str(open_price),
        "close": str(close_price),
    }


class ExecutionTruthSignalTests(unittest.TestCase):
    def test_source_contract_declares_coinbase_midnight_utc_daily_bars(self):
        contract = source_contract()
        self.assertEqual("coinbase", contract["venue"])
        self.assertEqual("BTCUSD", contract["instrument"])
        self.assertEqual("UTC", contract["bar_anchor_timezone"])
        self.assertEqual(0, contract["bar_anchor_offset_seconds"])
        self.assertEqual(86400, contract["bar_duration_seconds"])
        self.assertEqual(64, len(contract["contract_sha256"]))

    def test_two_up_bars_emit_down_for_next_daily_window(self):
        result = materialize_boundary_signal(
            source_contract(), signal_spec(), [bar(1, 100, 110), bar(2, 110, 120)]
        )
        self.assertTrue(result["emitted"])
        self.assertEqual("down", result["intent"]["direction"])
        self.assertEqual("2026-05-03T00:00:00Z", result["boundary_at_utc"])
        self.assertEqual(
            "2026-05-04T00:00:00Z", result["intent"]["target_end_at_utc"]
        )

    def test_two_down_bars_emit_up(self):
        result = materialize_boundary_signal(
            source_contract(), signal_spec(), [bar(1, 120, 110), bar(2, 110, 100)]
        )
        self.assertEqual("up", result["intent"]["direction"])

    def test_tied_bar_is_ignored_like_research_entry_model(self):
        result = materialize_boundary_signal(
            source_contract(), signal_spec(), [
                bar(1, 100, 110),
                bar(2, 110, 110),
                bar(3, 110, 120),
            ]
        )
        self.assertEqual("down", result["intent"]["direction"])
        self.assertEqual("2026-05-04T00:00:00Z", result["boundary_at_utc"])

    def test_mixed_recent_directions_do_not_emit(self):
        result = materialize_boundary_signal(
            source_contract(), signal_spec(), [bar(1, 100, 110), bar(2, 110, 100)]
        )
        self.assertFalse(result["emitted"])
        self.assertEqual("streak_not_present", result["non_emission_reason"])
        self.assertIsNone(result["intent"])

    def test_late_source_bar_fails_closed_without_intent(self):
        result = materialize_boundary_signal(
            source_contract(), signal_spec(), [
                bar(1, 100, 110),
                bar(2, 110, 120, available="2026-05-03T00:00:01Z"),
            ]
        )
        self.assertFalse(result["emitted"])
        self.assertEqual(
            "source_bar_not_available_at_boundary",
            result["non_emission_reason"],
        )

    def test_source_bar_must_be_contiguous_and_anchor_aligned(self):
        shifted = bar(2, 110, 120)
        shifted["start_at_utc"] = "2026-05-02T01:00:00Z"
        shifted["end_at_utc"] = "2026-05-03T01:00:00Z"
        shifted["available_at_utc"] = shifted["end_at_utc"]
        with self.assertRaisesRegex(ContractError, "aligned"):
            normalize_source_bar(shifted, source_contract())

    def test_contract_and_decision_hashes_detect_drift_and_are_deterministic(self):
        contract = source_contract()
        first = materialize_boundary_signal(
            contract, signal_spec(), [bar(1, 100, 110), bar(2, 110, 120)]
        )
        second = materialize_boundary_signal(
            contract, signal_spec(), [bar(1, 100, 110), bar(2, 110, 120)]
        )
        self.assertEqual(first, second)
        tampered = copy.deepcopy(contract)
        tampered["venue"] = "binance"
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            materialize_boundary_signal(
                tampered, signal_spec(), [bar(1, 100, 110), bar(2, 110, 120)]
            )

    def test_qcrl_utc_daily_intent_rejects_live_noon_daily_market(self):
        contract = source_contract()
        raw_bars = [
            {
                "schema_version": "qcrl.directional_source_bar.v1",
                "source_contract_sha256": contract["contract_sha256"],
                "start_at_utc": "2026-09-05T00:00:00Z",
                "end_at_utc": "2026-09-06T00:00:00Z",
                "available_at_utc": "2026-09-06T00:00:00Z",
                "open": "78000",
                "close": "79000",
            },
            {
                "schema_version": "qcrl.directional_source_bar.v1",
                "source_contract_sha256": contract["contract_sha256"],
                "start_at_utc": "2026-09-06T00:00:00Z",
                "end_at_utc": "2026-09-07T00:00:00Z",
                "available_at_utc": "2026-09-07T00:00:00Z",
                "open": "79000",
                "close": "80000",
            },
        ]
        intent = materialize_boundary_signal(
            contract, signal_spec(), raw_bars
        )["intent"]
        live_path = next((LIVE_EVIDENCE / "raw").glob("market-4293892-*.json"))
        live = normalize_bundle(json.loads(live_path.read_text(encoding="utf-8")))
        market = live["market_contract"]
        result = bind_signal_to_market(
            intent,
            market,
            {
                "schema_version": "qcrl.polymarket_binding_policy.v2",
                "asset": "btc",
                "duration_seconds": 86400,
                "resolution_source": "https://www.binance.com/en/trade/BTC_USDT",
                "max_entry_delay_seconds": 86400,
                "entry_cutoff_seconds_before_end": 0,
                "signal_source_contract_sha256": contract["contract_sha256"],
            },
            market["observed_at_utc"],
        )
        self.assertFalse(result["eligible"])
        self.assertIn("target_window_mismatch", result["rejection_reasons"])


if __name__ == "__main__":
    unittest.main()
