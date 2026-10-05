import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_truth.constraint_revalidation import replay_taker_buy_revalidated
from execution_truth.contracts import ContractError, payload_hash
from tests.test_taker_replay import raw_bundle, request, policy


GUARD = {"schema_version": "qcrl.constraint_revalidation_policy.v1",
         "mode": "reject_any_observed_change"}


def current(origin, *, tick=None, fee=None, accepting=None, delay="unchanged", age="unchanged"):
    raw = copy.deepcopy(origin)
    clob = raw["observations"]["clob_market"]
    clob["observed_at_utc"] = "2026-05-04T23:52:00.500000Z"
    if tick is not None:
        clob["payload"]["mts"] = tick
        for book in raw["observations"]["order_books"]:
            book["payload"]["tick_size"] = tick
    if fee is not None:
        clob["payload"]["fd"]["r"] = fee
    if accepting is not None:
        raw["observations"]["gamma_market"]["payload"]["acceptingOrders"] = accepting
    if delay != "unchanged":
        clob["payload"]["itode"] = delay
    if age != "unchanged":
        clob["payload"]["oas"] = age
    return rehash(raw)


def rehash(raw):
    for observation in [raw["observations"]["gamma_market"], raw["observations"]["clob_market"],
                        *raw["observations"]["order_books"]]:
        observation["payload_sha256"] = payload_hash(observation["payload"])
    raw.pop("bundle_sha256", None)
    raw["bundle_sha256"] = payload_hash(raw)
    return raw


class ConstraintRevalidationTests(unittest.TestCase):
    def test_cli_uses_declared_sources_and_rejects_changed_grid(self):
        origin = raw_bundle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "origin.json").write_text(json.dumps(origin))
            (root / "current.json").write_text(json.dumps(current(origin, tick="0.001")))
            spec = {
                "schema_version": "qcrl.constraint_revalidated_replay_example.v1",
                "origin_raw_bundle_path": "origin.json",
                "current_raw_bundle_path": "current.json",
                "requests": [request()], "replay_policy": policy(),
                "revalidation_policy": GUARD,
            }
            (root / "spec.json").write_text(json.dumps(spec))
            completed = subprocess.run([
                sys.executable, str(Path(__file__).parents[1] / "qcrl_execution_truth.py"),
                "replay-revalidated", str(root / "spec.json")
            ], check=True, capture_output=True, text=True)
            result = json.loads(completed.stdout)[0]
            self.assertFalse(result["metadata_revalidation_passed"])
            self.assertIsNone(result["replay"])
            self.assertEqual(origin["bundle_sha256"], result["origin_raw_bundle_sha256"])

    def test_book_depth_change_uses_current_book_without_metadata_rejection(self):
        origin = raw_bundle()
        latest = current(origin)
        for book in latest["observations"]["order_books"]:
            for level in book["payload"]["asks"]:
                level["size"] = "1"
        rehash(latest)
        result = replay_taker_buy_revalidated(origin, latest, request(), policy(), GUARD)
        self.assertTrue(result["metadata_revalidation_passed"])
        self.assertEqual("partial", result["replay"]["status"])

    def test_unchanged_metadata_passes_only_to_existing_replay(self):
        origin = raw_bundle()
        latest = current(origin)
        inputs = copy.deepcopy((origin, latest, request(), policy(), GUARD))
        result = replay_taker_buy_revalidated(origin, latest, request(), policy(), GUARD)
        self.assertTrue(result["metadata_revalidation_passed"])
        self.assertEqual("filled", result["replay"]["status"])
        self.assertFalse(result["request_modified"])
        self.assertEqual(inputs, (origin, latest, request(), policy(), GUARD))
        unsigned = dict(result)
        self.assertEqual(unsigned.pop("result_sha256"), payload_hash(unsigned))

    def test_finer_and_coarser_grids_reject_even_if_price_is_still_valid(self):
        origin = raw_bundle()
        for tick in ("0.001", "0.1"):
            result = replay_taker_buy_revalidated(origin, current(origin, tick=tick), request(), policy(), GUARD)
            self.assertFalse(result["metadata_revalidation_passed"])
            self.assertIn("tick_grid_changed_requires_new_request", result["rejection_reasons"])
            self.assertIsNone(result["replay"])

    def test_fee_acceptance_delay_and_age_changes_reject(self):
        origin = raw_bundle()
        for update in ({"fee": 0.08}, {"accepting": False}, {"delay": True}, {"age": 30}):
            with self.subTest(update=update):
                result = replay_taker_buy_revalidated(origin, current(origin, **update), request(), policy(), GUARD)
                self.assertFalse(result["metadata_revalidation_passed"])
                self.assertIsNone(result["replay"])

    def test_unknown_fields_still_reject_when_metadata_is_unchanged(self):
        origin = raw_bundle()
        clob = origin["observations"]["clob_market"]["payload"]
        clob.pop("itode", None)
        clob.pop("oas", None)
        rehash(origin)
        result = replay_taker_buy_revalidated(origin, current(origin), request(), policy(), GUARD)
        self.assertTrue(result["metadata_revalidation_passed"])
        self.assertEqual("rejected", result["replay"]["status"])
        self.assertIn("unknown_taker_delay_state", result["replay"]["reasons"])
        self.assertIn("unknown_minimum_order_age", result["replay"]["reasons"])

    def test_stale_current_snapshot_remains_rejected(self):
        origin = raw_bundle()
        result = replay_taker_buy_revalidated(origin, current(origin),
            request(hypothetical_at_utc="2026-05-04T23:53:02Z"), policy(), GUARD)
        self.assertTrue(result["metadata_revalidation_passed"])
        self.assertEqual("rejected", result["replay"]["status"])
        self.assertIn("clob_market_stale", result["replay"]["reasons"])

    def test_reversed_time_and_tampered_sources_fail(self):
        origin = raw_bundle()
        with self.assertRaisesRegex(ContractError, "precedes"):
            replay_taker_buy_revalidated(current(origin), origin, request(), policy(), GUARD)
        latest = current(origin)
        latest["observations"]["clob_market"]["payload"]["mts"] = "0.001"
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            replay_taker_buy_revalidated(origin, latest, request(), policy(), GUARD)

    def test_future_metadata_cannot_revalidate_request(self):
        origin = raw_bundle()
        latest = current(origin)
        latest["observations"]["clob_market"]["observed_at_utc"] = "2026-05-04T23:52:02Z"
        rehash(latest)
        result = replay_taker_buy_revalidated(origin, latest, request(), policy(), GUARD)
        self.assertIn("current_metadata_observed_after_replay_time", result["rejection_reasons"])
        self.assertIsNone(result["replay"])

    def test_invalid_origin_price_is_not_rounded(self):
        origin = raw_bundle()
        with self.assertRaisesRegex(ContractError, "tick"):
            replay_taker_buy_revalidated(origin, current(origin), request(limit_price="0.501"), policy(), GUARD)

    def test_book_market_grid_mismatch_stops_before_guard(self):
        origin = raw_bundle()
        latest = current(origin)
        latest["observations"]["clob_market"]["payload"]["mts"] = "0.001"
        rehash(latest)
        with self.assertRaisesRegex(ContractError, "tick size disagrees"):
            replay_taker_buy_revalidated(origin, latest, request(), policy(), GUARD)

    def test_policy_does_not_allow_automatic_adoption(self):
        origin = raw_bundle()
        with self.assertRaisesRegex(ContractError, "policy"):
            replay_taker_buy_revalidated(origin, current(origin), request(), policy(),
                dict(GUARD, mode="round_to_latest_tick"))


if __name__ == "__main__":
    unittest.main()
