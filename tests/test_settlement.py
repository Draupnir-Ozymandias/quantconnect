import copy
import json
from pathlib import Path
import unittest

from execution_truth import (
    ContractError,
    PublicPolymarketAcquirer,
    normalize_settlement,
    reconcile_settlement,
    reconcile_settlement_cohort,
)
from execution_truth.contracts import payload_hash
from tests.test_execution_truth_acquisition import FakeTransport, SequenceClock, fixture
from tests.test_latency_sensitivity import sequence


class SettlementTests(unittest.TestCase):
    def raw_settlement(self):
        gamma = fixture("gamma_market.json")
        gamma.update({
            "closed": True,
            "acceptingOrders": False,
            "umaResolutionStatus": "resolved",
            "outcomePrices": '["1", "0"]',
        })
        clob = fixture("clob_market_info.json")
        transport = FakeTransport(gamma, clob, {})
        acquirer = PublicPolymarketAcquirer(transport=transport, clock=SequenceClock())
        return acquirer.acquire_market_settlement("123456")

    def test_normalization_reconciles_platform_winner_and_tokens(self):
        raw = self.raw_settlement()
        result = normalize_settlement(raw)
        self.assertEqual("resolved", result["status"])
        self.assertEqual("single_winner", result["result_type"])
        self.assertEqual("Up", result["winner"]["label"])
        self.assertEqual(64, len(result["settlement_record_sha256"]))

    def test_resolved_state_rejects_nonterminal_or_orderable_payload(self):
        raw = self.raw_settlement()
        raw["observations"]["gamma_market"]["payload"]["outcomePrices"] = '["0.6", "0.4"]'
        observation = raw["observations"]["gamma_market"]
        observation["payload_sha256"] = payload_hash(observation["payload"])
        unhashed = dict(raw)
        unhashed.pop("settlement_sha256")
        raw["settlement_sha256"] = payload_hash(unhashed)
        with self.assertRaisesRegex(ContractError, "unsupported payout vector"):
            normalize_settlement(raw)

    def test_reconciliation_joins_latest_sequence_without_fill_claim(self):
        raw = self.raw_settlement()
        observed = sequence()
        result = reconcile_settlement(raw, [observed])
        self.assertEqual("123456", result["settlement"]["market_id"])
        self.assertEqual(1, result["observed_sequence_count"])
        self.assertEqual(2, len(result["latest_books"]))
        self.assertIn(
            "no order, fill, wallet settlement, redemption, or profitability is established",
            result["limitations"],
        )

    def test_reconciliation_rejects_cross_market_sequence(self):
        raw = self.raw_settlement()
        observed = sequence()
        changed = copy.deepcopy(observed)
        changed["market_id_requested"] = "999"
        changed["sequence_sha256"] = "invalid"
        with self.assertRaises(ContractError):
            reconcile_settlement(raw, [changed])

    def test_live_settlement_cohort_is_reproducible(self):
        root = Path(__file__).resolve().parents[1]
        spec_path = root / "execution_truth/specs/settlement_cohort_daily_20260915_20260922.json"
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        markets = {
            label: {
                "settlement": json.loads(
                    (spec_path.parent / paths["settlement"]).resolve().read_text(encoding="utf-8")
                ),
                "sequences": [json.loads(
                    (spec_path.parent / path).resolve().read_text(encoding="utf-8")
                ) for path in paths["sequences"]],
            }
            for label, paths in spec["markets"].items()
        }
        result = reconcile_settlement_cohort(markets)
        self.assertEqual({"Down": 2, "Up": 2}, result["winner_counts"])
        self.assertEqual(
            {"true": 4, "false": 0, "unknown": 0},
            result["latest_book_direction_consistency_counts"],
        )
        self.assertEqual(
            "0bc2068a79d7bde0dcfcc7938f2f186d1efac4fb9086ac986df3cb5b5af012cc",
            result["cohort_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
