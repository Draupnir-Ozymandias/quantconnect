import copy
import json
from pathlib import Path
import unittest

from execution_truth import (
    ContractError,
    MARKET_CONTRACT_SCHEMA,
    ORDER_BOOK_SCHEMA,
    normalize_market_contract,
    normalize_order_book,
)


FIXTURES = Path(__file__).parent / "fixtures" / "polymarket"
OBSERVED_AT = "2026-05-04T23:52:00.151038+00:00"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class ExecutionTruthContractTests(unittest.TestCase):
    def market_contract(self):
        return normalize_market_contract(
            fixture("gamma_market.json"),
            fixture("clob_market_info.json"),
            OBSERVED_AT,
        )

    def test_market_contract_joins_identity_terms_tokens_and_constraints(self):
        contract = self.market_contract()
        self.assertEqual(MARKET_CONTRACT_SCHEMA, contract["schema_version"])
        self.assertEqual("10001", contract["outcomes"][0]["token_id"])
        self.assertEqual("Up", contract["outcomes"][0]["label"])
        self.assertEqual("5", contract["constraints"]["minimum_order_size"])
        self.assertEqual("0.01", contract["constraints"]["minimum_tick_size"])
        self.assertEqual("0.02", contract["constraints"]["fee_curve"]["rate"])
        self.assertEqual(
            "2026-05-04T23:50:00Z",
            contract["terms"]["event_start_at_utc"],
        )
        self.assertEqual(64, len(contract["contract_sha256"]))

    def test_contract_hash_is_deterministic_across_mapping_order(self):
        gamma = fixture("gamma_market.json")
        reordered = dict(reversed(list(gamma.items())))
        first = normalize_market_contract(
            gamma, fixture("clob_market_info.json"), OBSERVED_AT
        )
        second = normalize_market_contract(
            reordered, fixture("clob_market_info.json"), OBSERVED_AT
        )
        self.assertEqual(first, second)

    def test_market_contract_rejects_token_identity_drift(self):
        clob = fixture("clob_market_info.json")
        clob["t"][0]["t"] = "unexpected-token"
        with self.assertRaisesRegex(ContractError, "token ids disagree"):
            normalize_market_contract(
                fixture("gamma_market.json"), clob, OBSERVED_AT
            )

    def test_market_contract_rejects_condition_identity_drift(self):
        clob = fixture("clob_market_info.json")
        clob["c"] = "foreign-condition"
        with self.assertRaisesRegex(ContractError, "condition ids disagree"):
            normalize_market_contract(
                fixture("gamma_market.json"), clob, OBSERVED_AT
            )

    def test_market_contract_rejects_outcome_mapping_drift(self):
        clob = fixture("clob_market_info.json")
        clob["t"].reverse()
        for token, label in zip(clob["t"], ["Up", "Down"]):
            token["o"] = label
        with self.assertRaisesRegex(ContractError, "outcome labels disagree"):
            normalize_market_contract(
                fixture("gamma_market.json"), clob, OBSERVED_AT
            )

    def test_market_contract_requires_resolution_terms(self):
        gamma = fixture("gamma_market.json")
        gamma["resolutionSource"] = ""
        with self.assertRaisesRegex(ContractError, "resolutionSource is required"):
            normalize_market_contract(
                gamma, fixture("clob_market_info.json"), OBSERVED_AT
            )

    def test_market_contract_requires_explicit_event_start(self):
        gamma = fixture("gamma_market.json")
        del gamma["eventStartTime"]
        with self.assertRaisesRegex(ContractError, "eventStartTime is required"):
            normalize_market_contract(
                gamma, fixture("clob_market_info.json"), OBSERVED_AT
            )

    def test_order_book_is_sorted_defensively_and_bound_to_contract(self):
        snapshot = normalize_order_book(
            fixture("up_order_book.json"), self.market_contract(), OBSERVED_AT
        )
        self.assertEqual(ORDER_BOOK_SCHEMA, snapshot["schema_version"])
        self.assertEqual({"price": "0.45", "size": "100"}, snapshot["best_bid"])
        self.assertEqual({"price": "0.46", "size": "150"}, snapshot["best_ask"])
        self.assertEqual("Up", snapshot["outcome"])
        self.assertEqual(64, len(snapshot["snapshot_sha256"]))

    def test_order_book_rejects_foreign_token(self):
        book = fixture("up_order_book.json")
        book["asset_id"] = "foreign-token"
        with self.assertRaisesRegex(ContractError, "does not belong"):
            normalize_order_book(book, self.market_contract(), OBSERVED_AT)

    def test_order_book_rejects_constraint_drift(self):
        book = fixture("up_order_book.json")
        book["tick_size"] = "0.001"
        with self.assertRaisesRegex(ContractError, "tick size disagrees"):
            normalize_order_book(book, self.market_contract(), OBSERVED_AT)

    def test_order_book_rejects_crossed_book(self):
        book = fixture("up_order_book.json")
        book["asks"][1]["price"] = "0.45"
        with self.assertRaisesRegex(ContractError, "crossed or locked"):
            normalize_order_book(book, self.market_contract(), OBSERVED_AT)

    def test_normalization_does_not_mutate_raw_evidence(self):
        gamma = fixture("gamma_market.json")
        clob = fixture("clob_market_info.json")
        book = fixture("up_order_book.json")
        originals = copy.deepcopy((gamma, clob, book))
        contract = normalize_market_contract(gamma, clob, OBSERVED_AT)
        normalize_order_book(book, contract, OBSERVED_AT)
        self.assertEqual(originals, (gamma, clob, book))


if __name__ == "__main__":
    unittest.main()
