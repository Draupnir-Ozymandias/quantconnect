import copy
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from execution_truth.bundle import normalize_bundle
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.delayed_binding import bind_delayed_decision
from execution_truth.delayed_signal import materialize_delayed_signal
from execution_truth.research_lane import load_research_lane
from tests.test_binance_source import dataset, rehash as dataset_rehash, SPEC, ROOT
from tests.test_constraint_revalidation import rehash
from tests.test_taker_replay import raw_bundle


def inputs():
    lane = load_research_lane(SPEC)
    raw = dataset()
    for entry in raw["observations"]:
        entry["observation"]["observed_at_utc"] = entry["observation"]["observed_at_utc"].replace("16:05", "16:01")
    dataset_rehash(raw)
    decision = materialize_delayed_signal(lane, raw, "2026-09-30", "2026-09-29T16:01:00Z")
    bundle = raw_bundle()
    gamma = bundle["observations"]["gamma_market"]["payload"]
    gamma.update({"eventStartTime": "2026-09-29T16:00:00Z", "endDate": "2026-09-30T16:00:00Z",
                  "resolutionSource": lane["target"]["resolution_source"],
                  "description": "Synthetic BTCUSDT noon Eastern 1m close-to-close; equal closes split 50/50."})
    for obs in [bundle["observations"]["gamma_market"], bundle["observations"]["clob_market"],
                *bundle["observations"]["order_books"]]:
        obs["observed_at_utc"] = "2026-09-29T16:01:00Z"
    for obs in bundle["observations"]["order_books"]:
        obs["payload"]["timestamp"] = "1790697660000"
    rehash(bundle)
    market = normalize_bundle(bundle)["market_contract"]
    terms = {
        "schema_version": "qcrl.delayed_market_terms_declaration.v1",
        "declaration_sha256": lane["declaration_sha256"],
        "market_id": market["identity"]["market_id"], "condition_id": market["identity"]["condition_id"],
        "description_sha256": payload_hash(market["terms"]["description"]),
        "event_start_at_utc": market["terms"]["event_start_at_utc"], "end_at_utc": market["terms"]["end_at_utc"],
        "resolution_source": lane["target"]["resolution_source"], "instrument": "BTCUSDT",
        "timezone": "America/New_York", "candle_interval": "1m", "price_field": "close",
        "tie_settlement": "split_50_50", "basis": "explicit_terms_declared_for_offline_diagnostic",
    }
    terms["terms_sha256"] = payload_hash(terms)
    policy = json.loads((ROOT / "execution_truth/specs/delayed_binding_freshness.json").read_text())
    return lane, raw, decision, bundle, terms, policy


class DelayedBindingTests(unittest.TestCase):
    def bind(self, values=None, at="2026-09-29T16:01:01Z"):
        return bind_delayed_decision(*(values or inputs()), at)

    def test_fresh_binding_is_diagnostic_only(self):
        values = inputs()
        original = copy.deepcopy(values)
        result = self.bind(values)
        self.assertTrue(result["binding_checks_passed"], result["rejection_reasons"])
        self.assertEqual("10002", result["selected_token_id"])
        self.assertFalse(result["orders_authorized"])
        self.assertTrue(result["constraint_revalidation_required"])
        self.assertEqual(original, values)
        unsigned = dict(result)
        self.assertEqual(unsigned.pop("result_sha256"), payload_hash(unsigned))

    def test_exact_book_age_limit_passes_but_fraction_over_rejects(self):
        self.assertTrue(self.bind(at="2026-09-29T16:01:02Z")["binding_checks_passed"])
        result = self.bind(at="2026-09-29T16:01:02.001Z")
        self.assertIn("book_10001_stale", result["rejection_reasons"])
        self.assertIn("book_10002_exchange_stale", result["rejection_reasons"])

    def test_metadata_sources_aged_independently(self):
        for key in ("gamma_market", "clob_market"):
            values = inputs()
            values[3]["observations"][key]["observed_at_utc"] = "2026-09-29T16:00:55Z"
            rehash(values[3])
            result = self.bind(values)
            self.assertIn(key + "_stale", result["rejection_reasons"])
            self.assertIn(key + "_predates_signal_decision", result["rejection_reasons"])

    def test_future_metadata_and_exchange_timestamp_reject(self):
        values = inputs()
        values[3]["observations"]["gamma_market"]["observed_at_utc"] = "2026-09-29T16:01:02Z"
        rehash(values[3])
        self.assertIn("gamma_market_observed_after_binding", self.bind(values)["rejection_reasons"])
        values = inputs()
        values[3]["observations"]["order_books"][0]["payload"]["timestamp"] = "1790697661000"
        rehash(values[3])
        self.assertIn("book_10001_exchange_timestamp_after_local_observation", self.bind(values)["rejection_reasons"])

    def test_unknown_execution_fields_and_enabled_delay_remain_blocked(self):
        for update, reason in (({"itode": None}, "unknown_taker_order_delay_enabled"),
                               ({"oas": None}, "unknown_minimum_order_age_seconds"),
                               ({"itode": True}, "enabled_taker_delay_requires_temporal_execution_model"),
                               ({"oas": 30}, "nonzero_order_age_requires_execution_model")):
            values = inputs()
            values[3]["observations"]["clob_market"]["payload"].update(update)
            rehash(values[3])
            self.assertIn(reason, self.bind(values)["rejection_reasons"])

    def test_terms_description_and_lane_mismatch_reject(self):
        values = inputs()
        values[4]["description_sha256"] = "0" * 64
        values[4].pop("terms_sha256")
        values[4]["terms_sha256"] = payload_hash(values[4])
        self.assertIn("explicit_market_terms_declaration_mismatch", self.bind(values)["rejection_reasons"])
        values = inputs()
        values[5]["declaration_sha256"] = "0" * 64
        self.assertIn("policy_lane_mismatch", self.bind(values)["rejection_reasons"])

    def test_rehashed_forged_decision_is_not_trusted(self):
        values = inputs()
        decision = values[2]
        decision["intent"]["direction"] = "up"
        decision["intent"].pop("intent_sha256")
        decision["intent"]["intent_sha256"] = payload_hash(decision["intent"])
        decision.pop("decision_sha256")
        decision["decision_sha256"] = payload_hash(decision)
        with self.assertRaisesRegex(ContractError, "does not reproduce"):
            self.bind(values)

    def test_entry_delay_intent_age_and_expiry_reject(self):
        self.assertNotIn("entry_delay_exceeded", self.bind(at="2026-09-29T16:05:00Z")["rejection_reasons"])
        result = self.bind(at="2026-09-29T16:05:00.001Z")
        self.assertIn("entry_delay_exceeded", result["rejection_reasons"])
        self.assertIn("intent_stale", result["rejection_reasons"])
        self.assertIn("entry_cutoff_reached", self.bind(at="2026-09-30T16:00:00Z")["rejection_reasons"])

    def test_dst_window_binds_exact_calendar_terms(self):
        values = list(inputs())
        raw = dataset("2026-10-29")
        for entry in raw["observations"]:
            entry["observation"]["observed_at_utc"] = entry["observation"]["observed_at_utc"].replace("16:05", "16:01")
        dataset_rehash(raw)
        values[1] = raw
        values[2] = materialize_delayed_signal(values[0], raw, "2026-11-01", "2026-10-31T16:01:00Z")
        gamma = values[3]["observations"]["gamma_market"]["payload"]
        gamma["eventStartTime"] = "2026-10-31T16:00:00Z"
        gamma["endDate"] = "2026-11-01T17:00:00Z"
        for observation in [values[3]["observations"]["gamma_market"], values[3]["observations"]["clob_market"],
                            *values[3]["observations"]["order_books"]]:
            observation["observed_at_utc"] = "2026-10-31T16:01:00Z"
        for observation in values[3]["observations"]["order_books"]:
            observation["payload"]["timestamp"] = str(int(datetime.fromisoformat("2026-10-31T16:01:00+00:00").timestamp() * 1000))
        rehash(values[3])
        values[4]["event_start_at_utc"] = gamma["eventStartTime"]
        values[4]["end_at_utc"] = gamma["endDate"]
        values[4].pop("terms_sha256")
        values[4]["terms_sha256"] = payload_hash(values[4])
        result = self.bind(values, at="2026-10-31T16:01:01Z")
        self.assertTrue(result["binding_checks_passed"], result["rejection_reasons"])
        self.assertEqual(90000, values[2]["intent"]["target_duration_seconds"])

    def test_boolean_or_missing_limits_and_order_authorization_reject(self):
        for field, value in (("max_book_age_seconds", True), ("max_intent_age_seconds", None),
                              ("orders_authorized", True)):
            values = inputs()
            values[5][field] = value
            with self.assertRaises(ContractError):
                self.bind(values)

    def test_closed_market_and_wrong_window_reject(self):
        values = inputs()
        gamma = values[3]["observations"]["gamma_market"]["payload"]
        gamma["closed"] = True
        gamma["endDate"] = "2026-09-30T16:02:00Z"
        rehash(values[3])
        result = self.bind(values)
        self.assertIn("market_state_closed_unsupported", result["rejection_reasons"])
        self.assertIn("target_window_mismatch", result["rejection_reasons"])

    def test_binding_before_signal_and_nonemitted_decision_reject(self):
        result = self.bind(at="2026-09-29T16:00:59Z")
        self.assertIn("binding_precedes_signal_decision", result["rejection_reasons"])
        values = list(inputs())
        raw = dataset(closes=("100", "101", "100"))
        for entry in raw["observations"]:
            entry["observation"]["observed_at_utc"] = entry["observation"]["observed_at_utc"].replace("16:05", "16:01")
        dataset_rehash(raw)
        values[1] = raw
        values[2] = materialize_delayed_signal(values[0], raw, "2026-09-30", "2026-09-29T16:01:00Z")
        result = self.bind(values)
        self.assertIn("diagnostic_signal_not_emitted", result["rejection_reasons"])
        self.assertIsNone(result["selected_token_id"])

    def test_cli_explicit_file_spec(self):
        lane, raw, decision, bundle, terms, policy = inputs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = {"schema_version": "qcrl.delayed_binding_example.v1", "declaration_path": str(SPEC),
                    "binding_at_utc": "2026-09-29T16:01:01Z"}
            for key, value in (("dataset", raw), ("decision", decision), ("raw_bundle", bundle),
                                ("terms_declaration", terms), ("policy", policy)):
                path = root / (key + ".json")
                path.write_text(json.dumps(value))
                spec[key + "_path"] = path.name
            path = root / "spec.json"
            path.write_text(json.dumps(spec))
            completed = subprocess.run([sys.executable, str(ROOT / "qcrl_execution_truth.py"),
                                        "delayed-binding", str(path)], check=True, capture_output=True, text=True)
            self.assertTrue(json.loads(completed.stdout)["binding_checks_passed"])


if __name__ == "__main__":
    unittest.main()
