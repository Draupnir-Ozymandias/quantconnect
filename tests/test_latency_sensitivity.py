import copy
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import subprocess
import unittest

from execution_truth import ContractError, PublicPolymarketAcquirer
from execution_truth import evaluate_latency_sensitivity
from execution_truth.contracts import payload_hash, verify_artifact_hash
from tests.test_book_sequence import ChangingBookTransport
from tests.test_execution_truth_acquisition import fixture


ROOT = Path(__file__).parents[1]


class SecondClock:
    def __init__(self):
        self.value = datetime(2026, 5, 4, 23, 52, tzinfo=timezone.utc)

    def __call__(self):
        current = self.value
        self.value += timedelta(seconds=1)
        return current


def sequence():
    gamma = fixture("gamma_market.json")
    gamma["feesEnabled"] = True
    clob = fixture("clob_market_info.json")
    clob["itode"] = False
    clob["oas"] = 0
    clob["fd"] = {"r": 0.07, "e": 1, "to": True}
    up = fixture("up_order_book.json")
    down = copy.deepcopy(up)
    down["asset_id"] = "10002"
    transport = ChangingBookTransport(
        gamma, clob, {"10001": up, "10002": down}
    )
    acquirer = PublicPolymarketAcquirer(transport=transport, clock=SecondClock())
    return acquirer.acquire_book_sequence("123456", 3, 1, sleeper=lambda _: None)


def request(**updates):
    value = {
        "schema_version": "qcrl.taker_replay_request.v1",
        "side": "BUY",
        "token_id": "10001",
        "shares": "5",
        "limit_price": "0.99",
        "time_in_force": "FAK",
        "cash_budget": "100",
        "hypothetical_at_utc": "2026-05-04T23:52:00Z",
    }
    return dict(value, **updates)


def replay_policy():
    return {
        "schema_version": "qcrl.taker_replay_policy.v1",
        "depth_assumption": "frozen_snapshot",
        "fee_model": "cash_equivalent_per_level_half_up_5dp",
        "max_book_age_seconds": 10,
        "max_market_age_seconds": 10,
        "max_exchange_age_seconds": 30,
    }


def latency_policy(**updates):
    value = {
        "schema_version": "qcrl.latency_sensitivity_policy.v1",
        "selection_rule": "first_selected_book_observed_at_or_after_arrival",
        "latencies_seconds": [0, 5, 9, 15],
        "max_observation_lag_seconds": 5,
    }
    return dict(value, **updates)


class LatencySensitivityTests(unittest.TestCase):
    def test_selects_first_observed_book_at_or_after_each_arrival(self):
        result = evaluate_latency_sensitivity(
            sequence(), request(), replay_policy(), latency_policy()
        )
        rows = result["results"]
        self.assertEqual([0, 1, 1, None],
                         [row["selected_sample_index"] for row in rows])
        self.assertEqual(["4", "4", "0", None],
                         [row["observation_lag_seconds"] for row in rows])
        self.assertEqual([None, "5", "5", None],
                         [row["polling_bracket_seconds"] for row in rows])
        self.assertEqual("no_observation_at_or_after_arrival", rows[-1]["reason"])

    def test_supported_metadata_yields_guarded_snapshot_mechanics(self):
        result = evaluate_latency_sensitivity(
            sequence(), request(), replay_policy(), latency_policy()
        )
        evaluated = [row for row in result["results"] if row["status"] == "evaluated"]
        self.assertTrue(evaluated)
        self.assertTrue(all(row["mechanics_result"]["status"] == "filled"
                            for row in evaluated))
        self.assertEqual(["0.46", "0.48", "0.48"],
                         [row["selected_best_ask"]["price"] for row in evaluated])
        self.assertTrue(all(row["mechanics_result"]["strategy_eligibility_evaluated"]
                            is False for row in evaluated))

    def test_polling_lag_policy_prevents_using_a_distant_future_book(self):
        result = evaluate_latency_sensitivity(
            sequence(), request(), replay_policy(), latency_policy(
                latencies_seconds=[1], max_observation_lag_seconds=2
            )
        )
        row = result["results"][0]
        self.assertEqual("unobserved", row["status"])
        self.assertEqual("observation_lag_exceeds_policy", row["reason"])
        self.assertEqual("3", row["observation_lag_seconds"])
        self.assertIsNone(row["mechanics_result"])

    def test_policy_rejects_ambiguous_or_unbounded_latency_grids(self):
        bad = [[1, 0], [1, 1], [-1], [86401], [True], [], list(range(33))]
        for latencies in bad:
            with self.subTest(latencies=latencies), self.assertRaises(ContractError):
                evaluate_latency_sensitivity(
                    sequence(), request(), replay_policy(),
                    latency_policy(latencies_seconds=latencies),
                )
        with self.assertRaises(ContractError):
            evaluate_latency_sensitivity(
                sequence(), request(), replay_policy(),
                latency_policy(max_observation_lag_seconds=3601),
            )

    def test_request_is_validated_even_if_arrivals_exceed_capture(self):
        with self.assertRaises(ContractError):
            evaluate_latency_sensitivity(
                sequence(), request(shares="NaN"), replay_policy(),
                latency_policy(latencies_seconds=[15]),
            )
        with self.assertRaisesRegex(ContractError, "within sequence capture"):
            evaluate_latency_sensitivity(
                sequence(), request(hypothetical_at_utc="2026-05-04T23:51:59Z"),
                replay_policy(), latency_policy(),
            )

    def test_result_is_hashed_deterministic_and_inputs_are_unchanged(self):
        raw = sequence()
        req = request()
        rp = replay_policy()
        lp = latency_policy()
        before = copy.deepcopy((raw, req, rp, lp))
        first = evaluate_latency_sensitivity(raw, req, rp, lp)
        second = evaluate_latency_sensitivity(raw, req, rp, lp)
        self.assertEqual(first, second)
        self.assertEqual(before, (raw, req, rp, lp))
        verify_artifact_hash(first, "result_sha256", "latency result")
        self.assertEqual("sequence_observation_sensitivity_only", first["evidence_role"])
        self.assertFalse(first["strategy_eligibility_evaluated"])

    def test_live_examples_preserve_distinct_timing_rejections(self):
        cases = [
            ("latency_15m_live_20260909.json",
             {"taker_delay_requires_temporal_replay", "unknown_minimum_order_age"}),
            ("latency_daily_live_20260909.json",
             {"unknown_taker_delay_state", "unknown_minimum_order_age"}),
        ]
        for filename, expected in cases:
            with self.subTest(filename=filename):
                spec_path = ROOT / "execution_truth" / "specs" / filename
                spec = json.loads(spec_path.read_text())
                raw = json.loads((spec_path.parent / spec["raw_sequence_path"]).read_text())
                result = evaluate_latency_sensitivity(
                    raw, spec["request"], spec["replay_policy"], spec["latency_policy"]
                )
                evaluated = [row for row in result["results"]
                             if row["status"] == "evaluated"]
                self.assertEqual(6, len(evaluated))
                self.assertTrue(all(row["mechanics_result"]["status"] == "rejected"
                                    for row in evaluated))
                self.assertTrue(all(expected.issubset(
                    set(row["mechanics_result"]["reasons"])
                ) for row in evaluated))

    def test_cli_emits_the_same_hashed_live_result(self):
        spec = ROOT / "execution_truth" / "specs" / "latency_daily_live_20260909.json"
        first = subprocess.run(
            [str(ROOT / "synch.sh"), "evidence", "latency", str(spec)],
            check=True, capture_output=True, text=True,
        )
        second = subprocess.run(
            [str(ROOT / "synch.sh"), "evidence", "latency", str(spec)],
            check=True, capture_output=True, text=True,
        )
        one = json.loads(first.stdout)
        two = json.loads(second.stdout)
        self.assertEqual(one["result_sha256"], two["result_sha256"])
        self.assertEqual("qcrl.latency_sensitivity_result.v1", one["schema_version"])


if __name__ == "__main__":
    unittest.main()
