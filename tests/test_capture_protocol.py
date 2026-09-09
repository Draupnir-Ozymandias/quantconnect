import copy
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from execution_truth import (
    ContractError,
    PublicPolymarketAcquirer,
    capture_protocol_status,
    execute_protocol_capture,
    load_capture_state,
    validate_capture_protocol,
)
from execution_truth.contracts import payload_hash
from qcrl_execution_truth import build_parser
from tests.test_book_sequence import ChangingBookTransport
from tests.test_execution_truth_acquisition import SequenceClock, fixture


def protocol(**updates):
    value = {
        "schema_version": "qcrl.book_sequence_capture_protocol.v1",
        "protocol_id": "btc-five-minute-phase-test-v1",
        "locked_at_utc": "2026-05-04T23:49:00Z",
        "evidence_role": "synthetic_phase_test",
        "market": {
            "slug": "btc-updown-fixture-1777938600",
            "reference_kind": "market",
            "event_start_at_utc": "2026-05-04T23:50:00Z",
            "event_end_at_utc": "2026-05-04T23:55:00Z",
            "resolution_source": "https://example.test/price-source",
            "research_compatibility": "synthetic_test_only",
        },
        "captures": [
            {"capture_id": "early", "phase": "early",
             "scheduled_at_utc": "2026-05-04T23:50:30Z",
             "start_tolerance_seconds": 20, "samples": 2,
             "interval_seconds": 1},
            {"capture_id": "middle", "phase": "middle",
             "scheduled_at_utc": "2026-05-04T23:52:00Z",
             "start_tolerance_seconds": 20, "samples": 2,
             "interval_seconds": 1},
            {"capture_id": "late", "phase": "late",
             "scheduled_at_utc": "2026-05-04T23:53:30Z",
             "start_tolerance_seconds": 20, "samples": 2,
             "interval_seconds": 1},
        ],
        "limitations": ["synthetic test protocol"],
    }
    return dict(value, **updates)


def acquirer(source="https://example.test/price-source"):
    gamma = fixture("gamma_market.json")
    gamma["resolutionSource"] = source
    gamma["feesEnabled"] = True
    clob = fixture("clob_market_info.json")
    clob["itode"] = False
    clob["oas"] = 0
    up = fixture("up_order_book.json")
    down = copy.deepcopy(up)
    down["asset_id"] = "10002"
    transport = ChangingBookTransport(
        gamma, clob, {"10001": up, "10002": down}
    )
    return PublicPolymarketAcquirer(transport=transport, clock=SequenceClock()), transport


class CaptureProtocolTests(unittest.TestCase):
    def test_protocol_requires_exact_ordered_market_phases(self):
        self.assertEqual("btc-five-minute-phase-test-v1",
                         validate_capture_protocol(protocol())["protocol_id"])
        cases = []
        missing = protocol()
        missing["captures"] = missing["captures"][:2]
        cases.append(missing)
        mislabeled = protocol()
        mislabeled["captures"][0]["phase"] = "late"
        cases.append(mislabeled)
        reordered = protocol()
        reordered["captures"] = list(reversed(reordered["captures"]))
        cases.append(reordered)
        post_lock = protocol(locked_at_utc="2026-05-04T23:52:01Z")
        cases.append(post_lock)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ContractError):
                validate_capture_protocol(value)

    def test_status_distinguishes_not_open_eligible_missed_and_collected(self):
        declaration = protocol()
        before = capture_protocol_status(
            declaration, now=datetime(2026, 5, 4, 23, 49, tzinfo=timezone.utc)
        )
        self.assertEqual(["not_open"] * 3,
                         [row["status"] for row in before["captures"]])
        middle = capture_protocol_status(
            declaration, now=datetime(2026, 5, 4, 23, 52, 10,
                                      tzinfo=timezone.utc)
        )
        self.assertEqual(["missed", "eligible", "not_open"],
                         [row["status"] for row in middle["captures"]])

    def test_eligible_capture_stores_complete_artifacts_and_resumable_state(self):
        declaration = protocol()
        source, transport = acquirer()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "state.json"
            result = execute_protocol_capture(
                declaration, "middle", root / "raw", state_path,
                acquirer=source,
                now=datetime(2026, 5, 4, 23, 52, 5, tzinfo=timezone.utc),
                sleeper=lambda _: None,
            )
            self.assertEqual("collected", result["status"])
            self.assertEqual(9, len(transport.calls))
            self.assertTrue(Path(result["resolution_path"]).is_file())
            self.assertTrue(Path(result["sequence_path"]).is_file())
            saved = load_capture_state(declaration, state_path)
            self.assertEqual(result, saved["captures"]["middle"])
            status = capture_protocol_status(
                declaration, saved,
                now=datetime(2026, 5, 4, 23, 53, tzinfo=timezone.utc),
            )
            self.assertEqual("collected", status["captures"][1]["status"])
            with self.assertRaisesRegex(ContractError, "collected, not eligible"):
                execute_protocol_capture(
                    declaration, "middle", root / "raw", state_path,
                    acquirer=source,
                    now=datetime(2026, 5, 4, 23, 52, 10,
                                 tzinfo=timezone.utc),
                    sleeper=lambda _: None,
                )

    def test_term_drift_fails_before_sequence_requests_or_storage(self):
        declaration = protocol()
        source, transport = acquirer(source="https://example.test/drift")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ContractError, "terms differ"):
                execute_protocol_capture(
                    declaration, "middle", root / "raw", root / "state.json",
                    acquirer=source,
                    now=datetime(2026, 5, 4, 23, 52, 5,
                                 tzinfo=timezone.utc),
                    sleeper=lambda _: None,
                )
            self.assertEqual(1, len(transport.calls))
            self.assertFalse((root / "raw").exists())

    def test_sequence_must_actually_start_inside_declared_window(self):
        declaration = protocol()
        source, _ = acquirer()
        source.clock.value = datetime(
            2026, 5, 4, 23, 52, 21, tzinfo=timezone.utc
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ContractError, "started outside"):
                execute_protocol_capture(
                    declaration, "middle", root / "raw", root / "state.json",
                    acquirer=source,
                    now=datetime(2026, 5, 4, 23, 52, 5,
                                 tzinfo=timezone.utc),
                    sleeper=lambda _: None,
                )
            self.assertFalse((root / "raw").exists())

    def test_state_hash_and_protocol_lock_detect_tampering(self):
        declaration = protocol()
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state = load_capture_state(declaration, state_path)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            state["protocol_id"] = "changed"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "hash mismatch"):
                load_capture_state(declaration, state_path)

            changed = protocol(evidence_role="changed_after_lock")
            state = load_capture_state(declaration, Path(directory) / "fresh.json")
            state["protocol_sha256"] = payload_hash(changed)
            state.pop("state_sha256")
            state["state_sha256"] = payload_hash(state)
            (Path(directory) / "fresh.json").write_text(
                json.dumps(state), encoding="utf-8"
            )
            with self.assertRaisesRegex(ContractError, "changed after state"):
                load_capture_state(declaration, Path(directory) / "fresh.json")

    def test_cli_requires_explicit_execute_flag(self):
        dry = build_parser().parse_args([
            "protocol-capture", "protocol.json", "early"
        ])
        live = build_parser().parse_args([
            "protocol-capture", "protocol.json", "early", "--execute"
        ])
        self.assertFalse(dry.execute)
        self.assertTrue(live.execute)


if __name__ == "__main__":
    unittest.main()
