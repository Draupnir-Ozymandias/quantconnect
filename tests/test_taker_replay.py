import copy
import json
from decimal import Decimal, localcontext
from pathlib import Path
import subprocess
import unittest

from execution_truth import ContractError, PublicPolymarketAcquirer, replay_taker_buy
from execution_truth.contracts import payload_hash, verify_artifact_hash
from tests.test_execution_truth_acquisition import FakeTransport, SequenceClock, fixture


ROOT = Path(__file__).parents[1]


def raw_bundle():
    gamma = fixture("gamma_market.json")
    gamma["feesEnabled"] = True
    clob = fixture("clob_market_info.json")
    clob["fd"] = {"r": 0.07, "e": 1, "to": True}
    clob["itode"] = False
    up = fixture("up_order_book.json")
    up["asks"] = [{"price": "0.60", "size": "200"}, {"price": "0.50", "size": "100"}]
    down = copy.deepcopy(up)
    down["asset_id"] = "10002"
    return PublicPolymarketAcquirer(
        FakeTransport(gamma, clob, {"10001": up, "10002": down}), SequenceClock()
    ).acquire_market_bundle("123456")


def request(**updates):
    value = {
        "schema_version": "qcrl.taker_replay_request.v1", "side": "BUY",
        "token_id": "10001", "shares": "100", "limit_price": "0.60",
        "time_in_force": "FAK", "cash_budget": "1000",
        "hypothetical_at_utc": "2026-05-04T23:52:01Z",
    }
    return dict(value, **updates)


def policy(**updates):
    return dict({
        "schema_version": "qcrl.taker_replay_policy.v1",
        "depth_assumption": "frozen_snapshot",
        "fee_model": "cash_equivalent_per_level_half_up_5dp",
        "max_book_age_seconds": 5, "max_market_age_seconds": 60,
        "max_exchange_age_seconds": 5,
    }, **updates)


def revise(raw, observation, **updates):
    """Create deliberately changed source evidence, with valid envelope hashes."""
    item = raw["observations"][observation]
    item["payload"].update(updates)
    item["payload_sha256"] = payload_hash(item["payload"])
    raw.pop("bundle_sha256")
    raw["bundle_sha256"] = payload_hash(raw)


class TakerReplayTests(unittest.TestCase):
    def test_documented_100_shares_at_half_price_fee(self):
        result = replay_taker_buy(raw_bundle(), request(), policy())
        self.assertEqual("filled", result["status"])
        self.assertEqual("50", result["notional"])
        self.assertEqual("1.75", result["fee_estimate"])
        self.assertEqual("51.75", result["cash_required_estimate"])
        self.assertEqual("0.5175", result["all_in_unit_cost_estimate"])

    def test_multiple_levels_are_consumed_cheapest_first(self):
        result = replay_taker_buy(raw_bundle(), request(shares="150"), policy())
        self.assertEqual(["0.5", "0.6"], [x["price"] for x in result["fills"]])
        self.assertEqual("80", result["notional"])
        self.assertEqual("2.59", result["fee_estimate"])

    def test_price_limit_gives_partial_fak_but_zero_fok(self):
        for tif, status, quantity in [("FAK", "partial", "100"), ("FOK", "unfilled", "0")]:
            with self.subTest(tif=tif):
                result = replay_taker_buy(raw_bundle(), request(
                    shares="150", limit_price="0.50", time_in_force=tif), policy())
                self.assertEqual(status, result["status"])
                self.assertEqual(quantity, result["filled_shares"])
                self.assertEqual("price_limit", result["liquidity_stop_reason"])
                if tif == "FOK":
                    self.assertEqual("0", result["fee_estimate"])
                    self.assertEqual("1000", result["cash_remaining_estimate"])

    def test_insufficient_depth_and_nonmarketable_limit(self):
        result = replay_taker_buy(raw_bundle(), request(shares="400"), policy())
        self.assertEqual("300", result["filled_shares"])
        self.assertEqual("insufficient_depth", result["liquidity_stop_reason"])
        result = replay_taker_buy(raw_bundle(), request(limit_price="0.49"), policy())
        self.assertEqual("unfilled", result["status"])
        self.assertEqual("0", result["cash_required_estimate"])

    def test_cash_budget_includes_fees_and_rounding(self):
        for budget in ["0", "0.01", "50", "51.74999", "51.75"]:
            with self.subTest(budget=budget):
                result = replay_taker_buy(raw_bundle(), request(cash_budget=budget), policy())
                self.assertLessEqual(Decimal(result["cash_required_estimate"]), Decimal(budget))
                if budget == "51.75":
                    self.assertEqual("100", result["filled_shares"])
                else:
                    self.assertLess(Decimal(result["filled_shares"]), 100)

    def test_below_minimum_order_size_is_rejected(self):
        result = replay_taker_buy(raw_bundle(), request(shares="4"), policy())
        self.assertEqual("rejected", result["status"])
        self.assertIn("below_minimum_order_size", result["reasons"])

    def test_invalid_numbers_ticks_and_tokens_fail(self):
        for changes in [{"shares": "NaN"}, {"shares": "1.0000001"},
                        {"cash_budget": -1}, {"limit_price": "0.501"},
                        {"token_id": "foreign"}, {"side": "SELL"}]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replay_taker_buy(raw_bundle(), request(**changes), policy())

    def test_stale_or_future_evidence_is_rejected(self):
        for at, reason in [("2026-05-04T23:52:10Z", "book_stale"),
                           ("2026-05-04T23:51:59Z", "book_observed_after_replay_time")]:
            result = replay_taker_buy(raw_bundle(), request(hypothetical_at_utc=at), policy())
            self.assertEqual("rejected", result["status"])
            self.assertIn(reason, result["reasons"])

    def test_closed_market_and_delay_and_unknown_fee_are_rejected(self):
        cases = [("gamma_market", {"closed": True}, "market_not_orderable"),
                 ("clob_market", {"itode": True}, "taker_delay_requires_temporal_replay"),
                 ("gamma_market", {"feesEnabled": None}, "fee_enablement_unknown"),
                 ("clob_market", {"fd": {"r": 0.07, "e": 2, "to": True}},
                  "fee_curve_exponent_unsupported")]
        for name, updates, reason in cases:
            raw = raw_bundle()
            revise(raw, name, **updates)
            result = replay_taker_buy(raw, request(), policy())
            self.assertEqual("rejected", result["status"])
            self.assertIn(reason, result["reasons"])

    def test_zero_fee_market(self):
        raw = raw_bundle()
        revise(raw, "gamma_market", feesEnabled=False)
        revise(raw, "clob_market", fd={"r": 0, "e": 1, "to": True})
        self.assertEqual("0", replay_taker_buy(raw, request(), policy())["fee_estimate"])

    def test_empty_asks_produce_no_fill(self):
        raw = raw_bundle()
        item = raw["observations"]["order_books"][0]
        item["payload"]["asks"] = []
        item["payload_sha256"] = payload_hash(item["payload"])
        raw.pop("bundle_sha256")
        raw["bundle_sha256"] = payload_hash(raw)
        result = replay_taker_buy(raw, request(), policy())
        self.assertEqual("unfilled", result["status"])
        self.assertEqual("insufficient_depth", result["liquidity_stop_reason"])

    def test_exchange_clock_is_checked_separately(self):
        for timestamp, reason in [("1777938600000", "exchange_book_stale"),
                                  ("1777938780000", "exchange_timestamp_after_observation")]:
            raw = raw_bundle()
            item = raw["observations"]["order_books"][0]
            item["payload"]["timestamp"] = timestamp
            item["payload_sha256"] = payload_hash(item["payload"])
            raw.pop("bundle_sha256")
            raw["bundle_sha256"] = payload_hash(raw)
            result = replay_taker_buy(raw, request(), policy())
            self.assertEqual("rejected", result["status"])
            self.assertIn(reason, result["reasons"])

    def test_market_freshness_and_window_are_independent_checks(self):
        result = replay_taker_buy(raw_bundle(), request(
            hypothetical_at_utc="2026-05-04T23:53:02Z"),
            policy(max_book_age_seconds=120, max_exchange_age_seconds=120))
        self.assertIn("gamma_market_stale", result["reasons"])
        self.assertNotIn("book_stale", result["reasons"])
        result = replay_taker_buy(raw_bundle(), request(
            hypothetical_at_utc="2026-05-04T23:55:00Z"),
            policy(max_book_age_seconds=600, max_exchange_age_seconds=600,
                   max_market_age_seconds=600))
        self.assertIn("outside_market_window", result["reasons"])

    def test_fok_budget_failure_rolls_back_every_level(self):
        result = replay_taker_buy(raw_bundle(), request(
            shares="150", cash_budget="60", time_in_force="FOK"), policy())
        self.assertEqual("unfilled", result["status"])
        self.assertEqual("cash_budget", result["liquidity_stop_reason"])
        self.assertEqual("60", result["cash_remaining_estimate"])
        self.assertEqual([], result["fills"])

    def test_declared_fee_rounding_at_half_unit(self):
        raw = raw_bundle()
        revise(raw, "clob_market", fd={"r": 0.000004, "e": 1, "to": True})
        result = replay_taker_buy(raw, request(shares="5"), policy())
        self.assertEqual("0.00001", result["fee_estimate"])

    def test_tampering_rejected_and_inputs_unchanged(self):
        raw = raw_bundle()
        before = copy.deepcopy(raw)
        replay_taker_buy(raw, request(), policy())
        self.assertEqual(before, raw)
        raw["observations"]["gamma_market"]["payload"]["closed"] = True
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            replay_taker_buy(raw, request(), policy())

    def test_ambient_decimal_precision_does_not_change_result(self):
        first = replay_taker_buy(raw_bundle(), request(shares="150"), policy())
        with localcontext() as ctx:
            ctx.prec = 8
            second = replay_taker_buy(raw_bundle(), request(shares="150"), policy())
        self.assertEqual(first, second)
        verify_artifact_hash(first, "result_sha256", "result")
        self.assertFalse(first["strategy_eligibility_evaluated"])

    def test_synthetic_example_cli_covers_four_outcomes(self):
        result = subprocess.run([str(ROOT / "synch.sh"), "evidence", "replay",
                                 str(ROOT / "execution_truth/specs/synthetic_taker_replay.json")],
                                check=True, capture_output=True, text=True)
        rows = json.loads(result.stdout)
        self.assertEqual(["filled", "partial", "unfilled", "unfilled"],
                         [row["status"] for row in rows])
        self.assertEqual("100", rows[1]["filled_shares"])
        self.assertTrue(all(row["evidence_role"] == "snapshot_mechanics_only" for row in rows))

    def test_live_daily_capture_requires_explicit_delay_evidence(self):
        path = ROOT / "execution_truth/specs/daily_taker_replay.json"
        spec = json.loads(path.read_text())
        raw = json.loads((path.parent / spec["raw_bundle_path"]).read_text())
        for req in spec["requests"]:
            result = replay_taker_buy(raw, req, spec["policy"])
            self.assertEqual("rejected", result["status"])
            self.assertIn("unknown_taker_delay_state", result["reasons"])
            self.assertEqual([], result["fills"])


if __name__ == "__main__":
    unittest.main()
