import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from execution_truth import (
    ContractError,
    PublicBinanceAcquirer,
    PublicPolymarketAcquirer,
    normalize_resolution_candles,
    reconcile_binance_cohort,
    reconcile_binance_settlement,
)
from execution_truth.contracts import payload_hash
from tests.test_execution_truth_acquisition import FakeTransport, SequenceClock, fixture


START = "2026-09-14T16:00:00Z"
END = "2026-09-15T16:00:00Z"
START_MS = 1789401600000
END_MS = 1789488000000


class KlineTransport:
    def __init__(self, prices=("77000.00", "76500.00")):
        self.prices = prices
        self.calls = []

    def get_json(self, url, params):
        self.calls.append((url, params))
        index = len(self.calls) - 1
        opened = (START_MS, END_MS)[index]
        return [[opened, "1", "1", "1", self.prices[index], "1",
                 opened + 59999, "1", 1, "1", "1", "0"]]


def raw_settlement(winner="Down"):
    gamma = fixture("gamma_market.json")
    gamma.update({
        "closed": True,
        "acceptingOrders": False,
        "umaResolutionStatus": "resolved",
        "outcomePrices": '["0", "1"]' if winner == "Down" else '["1", "0"]',
        "eventStartTime": START,
        "endDate": END,
        "resolutionSource": "https://www.binance.com/en/trade/BTC_USDT",
    })
    clob = fixture("clob_market_info.json")
    return PublicPolymarketAcquirer(
        transport=FakeTransport(gamma, clob, {}), clock=SequenceClock()
    ).acquire_market_settlement("123456")


class BinanceResolutionTests(unittest.TestCase):
    def raw_candles(self, prices=("77000.00", "76500.00")):
        clock = lambda: datetime(2026, 9, 23, 20, tzinfo=timezone.utc)
        return PublicBinanceAcquirer(
            transport=KlineTransport(prices), clock=clock
        ).acquire_resolution_candles("123456", START, END)

    def test_exact_boundary_candles_derive_down_outcome(self):
        result = normalize_resolution_candles(self.raw_candles())
        self.assertEqual("Down", result["computed_outcome"])
        self.assertEqual("77000", result["start_candle"]["close"])
        self.assertEqual("76500", result["end_candle"]["close"])
        self.assertEqual("-500", result["close_change"])

    def test_timestamp_or_request_drift_fails_closed(self):
        raw = self.raw_candles()
        raw["observations"]["start_candle"]["payload"][0][0] += 1
        observation = raw["observations"]["start_candle"]
        observation["payload_sha256"] = payload_hash(observation["payload"])
        raw.pop("resolution_candles_sha256")
        raw["resolution_candles_sha256"] = payload_hash(raw)
        with self.assertRaisesRegex(ContractError, "timestamps"):
            normalize_resolution_candles(raw)

    def test_reconciliation_matches_independent_direction_to_platform(self):
        result = reconcile_binance_settlement(self.raw_candles(), raw_settlement())
        self.assertEqual("match", result["verdict"])
        self.assertEqual("Down", result["computed_outcome"])
        self.assertEqual("Down", result["platform_outcome"])

    def test_cohort_rejects_duplicate_market_and_counts_verdicts(self):
        inputs = {"candles": self.raw_candles(), "settlement": raw_settlement()}
        result = reconcile_binance_cohort({"one": inputs})
        self.assertEqual({"match": 1, "mismatch": 0}, result["verdict_counts"])
        with self.assertRaisesRegex(ContractError, "duplicate"):
            reconcile_binance_cohort({"one": inputs, "two": copy.deepcopy(inputs)})

    def test_mismatch_is_reported_not_hidden(self):
        result = reconcile_binance_settlement(self.raw_candles(), raw_settlement("Up"))
        self.assertEqual("mismatch", result["verdict"])

    def test_reconciliation_rejects_market_term_drift(self):
        settlement = raw_settlement()
        observation = settlement["observations"]["gamma_market"]
        observation["payload"]["eventStartTime"] = "2026-09-14T16:01:00Z"
        observation["payload_sha256"] = payload_hash(observation["payload"])
        settlement.pop("settlement_sha256")
        settlement["settlement_sha256"] = payload_hash(settlement)
        with self.assertRaisesRegex(ContractError, "start differs"):
            reconcile_binance_settlement(self.raw_candles(), settlement)

    def test_live_cohort_is_reproducible_and_matches_all_settlements(self):
        root = Path(__file__).resolve().parents[1]
        spec_path = root / (
            "execution_truth/specs/"
            "binance_settlement_cohort_daily_20260915_20260922.json"
        )
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        markets = {
            label: {
                key: json.loads(
                    (spec_path.parent / paths[key]).resolve().read_text(encoding="utf-8")
                )
                for key in ("candles", "settlement")
            }
            for label, paths in spec["markets"].items()
        }
        result = reconcile_binance_cohort(markets)
        self.assertEqual({"match": 4, "mismatch": 0}, result["verdict_counts"])
        self.assertEqual(
            "abb31376d2b1afd7152cb34e6521104005528393c72675e533ceb6a7f88d31e5",
            result["cohort_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
