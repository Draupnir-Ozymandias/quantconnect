import copy
import json
from pathlib import Path
import unittest

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.schema_interpretation import interpret_market_bundle


FIXTURE = Path(__file__).parent / "fixtures/polymarket/taker_replay_bundle.json"


def bundle(value="absent", observed_at="2026-10-03T19:00:00Z"):
    raw = json.loads(FIXTURE.read_text())
    observation = raw["observations"]["clob_market"]
    observation["observed_at_utc"] = observed_at
    if value == "absent":
        observation["payload"].pop("itode", None)
    else:
        observation["payload"]["itode"] = value
    observation["payload"].pop("oas", None)
    observation["payload"]["r"] = {"moas": 30}
    observation["payload_sha256"] = payload_hash(observation["payload"])
    raw.pop("bundle_sha256", None)
    raw["bundle_sha256"] = payload_hash(raw)
    return raw


class SchemaInterpretationTests(unittest.TestCase):
    def test_default_preserves_unknown_and_source(self):
        raw = bundle()
        before = copy.deepcopy(raw)
        result = interpret_market_bundle(raw)
        self.assertIsNone(result["fields"]["taker_order_delay_enabled"]["value"])
        self.assertEqual(before, raw)
        self.assertFalse(result["replay_gate_changed"])
        unsigned = dict(result)
        digest = unsigned.pop("interpretation_sha256")
        self.assertEqual(payload_hash(unsigned), digest)

    def test_documented_absence_requires_declaration(self):
        result = interpret_market_bundle(bundle(), apply_current_documentation=True)
        delay = result["fields"]["taker_order_delay_enabled"]
        self.assertIs(delay["value"], False)
        self.assertEqual("documented_omission_default", delay["basis"])
        self.assertEqual(250, result["documented_taker_delay_ms_when_enabled"])

    def test_null_is_not_omission_and_explicit_values_survive(self):
        for value in (None, True, False):
            with self.subTest(value=value):
                result = interpret_market_bundle(bundle(value), apply_current_documentation=True)
                self.assertIs(value, result["fields"]["taker_order_delay_enabled"]["value"])

    def test_old_capture_cannot_receive_current_default(self):
        raw = bundle(observed_at="2026-09-30T19:00:00Z")
        self.assertIsNone(interpret_market_bundle(raw)["fields"]["taker_order_delay_enabled"]["value"])
        with self.assertRaisesRegex(ContractError, "pre-review"):
            interpret_market_bundle(raw, apply_current_documentation=True)

    def test_reward_age_never_fills_missing_execution_age(self):
        result = interpret_market_bundle(bundle(), apply_current_documentation=True)
        age = result["fields"]["minimum_order_age_seconds"]
        self.assertIsNone(age["value"])
        self.assertEqual("unresolved", age["operational_scope"])

    def test_rejects_tampered_evidence(self):
        raw = bundle()
        raw["observations"]["clob_market"]["payload"]["itode"] = False
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            interpret_market_bundle(raw)

    def test_rejects_other_endpoint_even_when_hashes_agree(self):
        raw = bundle()
        raw["observations"]["clob_market"]["endpoint"] = "https://clob.polymarket.com/data/orders"
        raw.pop("bundle_sha256")
        raw["bundle_sha256"] = payload_hash(raw)
        with self.assertRaisesRegex(ContractError, "market-info endpoint"):
            interpret_market_bundle(raw, apply_current_documentation=True)


if __name__ == "__main__":
    unittest.main()
