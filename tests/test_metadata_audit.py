import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.metadata_audit import analyze_metadata_batch, store_metadata_audit
from qcrl_execution_truth import build_parser
from tests.test_book_sequence import acquirer


def sequence():
    source, _ = acquirer()
    return source.acquire_book_sequence("123456", 3, 1, sleeper=lambda _: None)


def rehash(raw):
    for bundle in raw["samples"]:
        for observation in [bundle["observations"]["gamma_market"],
                            bundle["observations"]["clob_market"],
                            *bundle["observations"]["order_books"]]:
            observation["payload_sha256"] = payload_hash(observation["payload"])
        bundle.pop("bundle_sha256", None)
        bundle["bundle_sha256"] = payload_hash(bundle)
    raw.pop("sequence_sha256", None)
    raw["sequence_sha256"] = payload_hash(raw)
    return raw


def cohort(raw):
    return {"fixture": {"early": raw, "middle": None, "late": None}}


class MetadataAuditTests(unittest.TestCase):
    def test_hash_determinism_nonmutation_and_missing_phases(self):
        raw = sequence()
        before = copy.deepcopy(raw)
        result = analyze_metadata_batch(cohort(raw))
        self.assertEqual(before, raw)
        self.assertEqual(result, analyze_metadata_batch(cohort(raw)))
        self.assertEqual(3, result["observation_count"])
        self.assertEqual(2, result["missing_phase_count"])
        self.assertEqual([], result["observed_changes"])
        self.assertFalse(result["replay_gate_changed"])
        unsigned = dict(result)
        self.assertEqual(unsigned.pop("audit_sha256"), payload_hash(unsigned))

    def test_unknown_counts_do_not_use_reward_age(self):
        raw = sequence()
        for bundle in raw["samples"]:
            clob = bundle["observations"]["clob_market"]["payload"]
            clob.pop("itode", None)
            clob.pop("oas", None)
            clob["r"] = {"moas": 30}
        result = analyze_metadata_batch(cohort(rehash(raw)))
        for field in result["field_counts"].values():
            self.assertEqual(3, field["observation_basis_counts"]["unknown"])
            self.assertEqual(1, field["markets_with_any_unknown"])
        self.assertIsNone(result["observations"][0]["metadata"]["constraints"]["minimum_order_age_seconds"])

    def test_detects_fee_state_and_explicit_delay_changes(self):
        raw = sequence()
        raw["samples"][1]["observations"]["clob_market"]["payload"]["itode"] = True
        raw["samples"][1]["observations"]["clob_market"]["payload"]["fd"]["r"] = 0.08
        result = analyze_metadata_batch(cohort(rehash(raw)))
        self.assertEqual(2, len(result["observed_changes"]))
        fields = {item["field"] for item in result["observed_changes"][0]["changes"]}
        self.assertIn("constraints.fee_curve", fields)
        self.assertIn("interpreted_fields.taker_order_delay_enabled", fields)

    def test_historical_documentation_declaration_fails_closed(self):
        with self.assertRaisesRegex(ContractError, "pre-review"):
            analyze_metadata_batch(cohort(sequence()), apply_current_documentation=True)

    def test_current_default_is_sidecar_only_and_null_is_not_absence(self):
        raw = json.loads(json.dumps(sequence()).replace("2026-05-04T", "2026-10-04T"))
        for bundle in raw["samples"]:
            bundle["observations"]["clob_market"]["payload"].pop("itode", None)
        raw["samples"][1]["observations"]["clob_market"]["payload"]["itode"] = None
        result = analyze_metadata_batch(cohort(rehash(raw)), apply_current_documentation=True)
        counts = result["field_counts"]["taker_order_delay_enabled"]["observation_basis_counts"]
        self.assertEqual(2, counts["documented_omission_default"])
        self.assertEqual(1, counts["unknown"])
        metadata = result["observations"][0]["metadata"]
        self.assertIsNone(metadata["constraints"]["taker_order_delay_enabled"])
        self.assertIs(metadata["interpreted_fields"]["taker_order_delay_enabled"]["value"], False)

    def test_between_phase_change_with_missing_middle(self):
        raw = sequence()
        late = json.loads(json.dumps(raw).replace("2026-05-04T", "2026-05-05T"))
        for bundle in late["samples"]:
            bundle["observations"]["clob_market"]["payload"]["itode"] = True
        result = analyze_metadata_batch({"one": {"early": raw, "middle": None, "late": rehash(late)}})
        self.assertEqual(1, result["missing_phase_count"])
        self.assertEqual(1, len(result["observed_changes"]))
        self.assertEqual("between_phases", result["observed_changes"][0]["comparison"])

    def test_rejects_relabelled_same_condition(self):
        raw = sequence()
        later = rehash(json.loads(json.dumps(raw).replace("2026-05-04T", "2026-05-05T")))
        with self.assertRaisesRegex(ContractError, "same condition"):
            analyze_metadata_batch({"one": cohort(raw)["fixture"], "two": cohort(later)["fixture"]})

    def test_rejects_tampered_source(self):
        raw = sequence()
        raw["samples"][0]["observations"]["clob_market"]["payload"]["itode"] = True
        with self.assertRaisesRegex(ContractError, "hash mismatch"):
            analyze_metadata_batch(cohort(raw))

    def test_rejects_duplicate_sources_and_unobserved_markets(self):
        raw = sequence()
        with self.assertRaisesRegex(ContractError, "duplicate raw bundle"):
            analyze_metadata_batch({"one": cohort(raw)["fixture"], "two": cohort(raw)["fixture"]})
        with self.assertRaisesRegex(ContractError, "at least one observed"):
            analyze_metadata_batch({"none": dict.fromkeys(("early", "middle", "late"))})

    def test_requires_explicit_phase_gaps_and_boolean_applicability(self):
        with self.assertRaisesRegex(ContractError, "declare early"):
            analyze_metadata_batch({"one": {"early": sequence()}})
        with self.assertRaisesRegex(ContractError, "boolean"):
            analyze_metadata_batch(cohort(sequence()), apply_current_documentation="false")

    def test_rejects_reversed_phase_chronology(self):
        raw = sequence()
        later = copy.deepcopy(raw)
        # Shift every observation timestamp, preserving each sequence's order.
        def shift(value):
            if isinstance(value, dict):
                return {key: shift(item) for key, item in value.items()}
            if isinstance(value, list):
                return [shift(item) for item in value]
            if isinstance(value, str) and value.startswith("2026-05-04T"):
                return value.replace("2026-05-04T", "2026-05-05T")
            return value
        later = rehash(shift(later))
        with self.assertRaisesRegex(ContractError, "phase observations"):
            analyze_metadata_batch({"one": {"early": later, "middle": None, "late": raw}})

    def test_cli_cohort_pin_rejects_before_loading_sources(self):
        with tempfile.TemporaryDirectory() as root:
            spec = Path(root) / "spec.json"
            target = Path(root) / "cohort.json"
            target.write_text("{}")
            spec.write_text(json.dumps({
                "schema_version": "qcrl.batch_metadata_audit_spec.v1",
                "policy_id": "qcrl.clob_documentation_policy.20261003.v1",
                "cohort": "cohort.json", "cohort_file_sha256": "0" * 64,
                "apply_current_documentation": False,
            }))
            args = build_parser().parse_args(["metadata-audit", str(spec)])
            with self.assertRaisesRegex(ContractError, "cohort file hash"):
                args.handler(args)

    def test_live_declaration_runs_offline(self):
        path = Path(__file__).resolve().parents[1] / "execution_truth/specs/metadata_audit_daily_20260915_20260930.json"
        args = build_parser().parse_args(["metadata-audit", str(path)])
        output = StringIO()
        with redirect_stdout(output):
            args.handler(args)
        result = json.loads(output.getvalue())
        self.assertEqual(5, result["market_count"])
        self.assertEqual(13, result["sequence_count"])
        self.assertEqual(2, result["missing_phase_count"])
        unsigned = dict(result)
        self.assertEqual(unsigned.pop("audit_sha256"), payload_hash(unsigned))

    def test_storage_is_hashed_and_idempotent(self):
        result = analyze_metadata_batch(cohort(sequence()))
        with tempfile.TemporaryDirectory() as root:
            path = store_metadata_audit(result, root)
            self.assertEqual(result, json.loads(path.read_text()))
            self.assertEqual(path, store_metadata_audit(result, root))
            result["market_count"] = 100
            with self.assertRaisesRegex(ContractError, "hash mismatch"):
                store_metadata_audit(result, root)


if __name__ == "__main__":
    unittest.main()
