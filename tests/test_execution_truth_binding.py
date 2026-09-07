import json
from pathlib import Path
import unittest

from execution_truth import ContractError, bind_signal_to_market
from execution_truth.contracts import normalize_market_contract


FIXTURES = Path(__file__).parent / "fixtures" / "polymarket"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def signal(**updates):
    value = {
        "schema_version": "qcrl.directional_signal_intent.v1",
        "signal_id": "signal-fixture",
        "asset": "btc",
        "source_timeframe": "5m",
        "direction": "up",
        "available_at_utc": "2026-05-04T23:50:00Z",
        "target_start_at_utc": "2026-05-04T23:50:00Z",
        "target_end_at_utc": "2026-05-04T23:55:00Z",
        "methodology_version": "qcrl.methodology.lookahead_free.v1",
    }
    value.update(updates)
    return value


def policy(**updates):
    value = {
        "schema_version": "qcrl.polymarket_binding_policy.v1",
        "asset": "btc",
        "duration_seconds": 300,
        "resolution_source": "Documented fixture price source",
        "max_entry_delay_seconds": 30,
        "entry_cutoff_seconds_before_end": 30,
    }
    value.update(updates)
    return value


def contract(observed_at="2026-05-04T23:50:10Z"):
    return normalize_market_contract(
        fixture("gamma_market.json"),
        fixture("clob_market_info.json"),
        observed_at,
    )


def closed_contract(observed_at="2026-05-04T23:50:10Z"):
    gamma = fixture("gamma_market.json")
    gamma["closed"] = True
    return normalize_market_contract(
        gamma, fixture("clob_market_info.json"), observed_at
    )


class ExecutionTruthBindingTests(unittest.TestCase):
    def test_eligible_signal_maps_to_explicit_outcome_token(self):
        result = bind_signal_to_market(
            signal(), contract(), policy(), "2026-05-04T23:50:12Z"
        )
        self.assertTrue(result["eligible"])
        self.assertEqual("Up", result["selected_outcome"])
        self.assertEqual("10001", result["selected_token_id"])
        self.assertEqual([], result["rejection_reasons"])

    def test_late_decision_is_rejected_not_raised(self):
        result = bind_signal_to_market(
            signal(), contract("2026-05-04T23:52:00Z"), policy(),
            "2026-05-04T23:52:01Z",
        )
        self.assertFalse(result["eligible"])
        self.assertIn("entry_delay_exceeded", result["rejection_reasons"])

    def test_daily_signal_cannot_bind_to_five_minute_market(self):
        daily = signal(
            source_timeframe="1d",
            target_end_at_utc="2026-05-05T23:50:00Z",
        )
        result = bind_signal_to_market(
            daily, contract(), policy(), "2026-05-04T23:50:12Z"
        )
        self.assertFalse(result["eligible"])
        self.assertIn("target_window_mismatch", result["rejection_reasons"])

    def test_signal_must_be_available_by_target_start(self):
        late = signal(available_at_utc="2026-05-04T23:50:01Z")
        with self.assertRaisesRegex(ContractError, "available by its target start"):
            bind_signal_to_market(
                late, contract(), policy(), "2026-05-04T23:50:12Z"
            )

    def test_decision_cannot_precede_observation(self):
        with self.assertRaisesRegex(ContractError, "precede market observation"):
            bind_signal_to_market(
                signal(), contract(), policy(), "2026-05-04T23:50:09Z"
            )

    def test_closed_market_is_rejected(self):
        result = bind_signal_to_market(
            signal(), closed_contract(), policy(), "2026-05-04T23:50:12Z"
        )
        self.assertFalse(result["eligible"])
        self.assertIn("market_closed", result["rejection_reasons"])

    def test_wrong_resolution_source_is_rejected(self):
        result = bind_signal_to_market(
            signal(), contract(), policy(resolution_source="Coinbase"),
            "2026-05-04T23:50:12Z",
        )
        self.assertFalse(result["eligible"])
        self.assertIn("resolution_source_mismatch", result["rejection_reasons"])

    def test_binding_result_is_deterministic(self):
        first = bind_signal_to_market(
            signal(), contract(), policy(), "2026-05-04T23:50:12Z"
        )
        second = bind_signal_to_market(
            signal(), contract(), policy(), "2026-05-04T23:50:12Z"
        )
        self.assertEqual(first, second)

    def test_signal_identity_and_methodology_are_required(self):
        for field in ["signal_id", "asset", "source_timeframe", "methodology_version"]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ContractError, f"signal.{field}"):
                    bind_signal_to_market(
                        signal(**{field: ""}), contract(), policy(),
                        "2026-05-04T23:50:12Z",
                    )

    def test_policy_duration_must_be_an_integer(self):
        with self.assertRaisesRegex(ContractError, "timing values must be integers"):
            bind_signal_to_market(
                signal(), contract(), policy(duration_seconds=None),
                "2026-05-04T23:50:12Z",
            )


if __name__ == "__main__":
    unittest.main()
