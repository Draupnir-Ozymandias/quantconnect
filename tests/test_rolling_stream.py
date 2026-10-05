from datetime import datetime, timezone
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.rolling_stream import pilot_plan, validate_plan, check_market, persist, observe_window, SOURCE, DESCRIPTION
from tests.test_taker_replay import raw_bundle


class RollingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 4, 23, 48, tzinfo=timezone.utc)
        self.start = int(self.now.timestamp()) + 120
        self.plan = pilot_plan(self.start, now=self.now)

    def test_prospective_aligned_bounded_plan(self):
        self.assertEqual(validate_plan(self.plan), self.plan)
        self.assertEqual(len(self.plan["market_starts"]), 6)
        self.assertEqual(self.plan["market_starts"][1] - self.start, 300)
        for start, count in ((self.start + 1, 6), (self.start - 300, 6), (self.start, 25), (self.start, True)):
            with self.assertRaises(ContractError):
                pilot_plan(start, count, now=self.now)

    def test_policy_mutation_rejected_even_rehashed(self):
        for key, value in (("orders_authorized", True), ("resolution_source", "other"),
                           ("max_spool_bytes", 999999999999)):
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            plan["plan_sha256"] = payload_hash({k: v for k, v in plan.items() if k != "plan_sha256"})
            with self.assertRaises(ContractError):
                validate_plan(plan)

    def test_exact_terms_and_interval(self):
        bundle = raw_bundle()
        gamma = bundle["observations"]["gamma_market"]
        gamma["payload"].update(slug="btc-updown-5m-" + str(self.start),
                                question="Bitcoin Up or Down - May 4", description=DESCRIPTION,
                                resolutionSource=SOURCE)
        gamma["payload_sha256"] = payload_hash(gamma["payload"])
        bundle["bundle_sha256"] = payload_hash({k: v for k, v in bundle.items() if k != "bundle_sha256"})
        # Fixture interval is midnight aligned and five minutes.
        spec = check_market(bundle, self.start, self.plan)
        self.assertEqual(spec["market_id"], bundle["market_id_requested"])
        for field, value in (("description", DESCRIPTION + " changed"), ("slug", "eth-updown-5m-0"),
                             ("resolutionSource", "https://example.org"), ("closed", True)):
            mutated = copy.deepcopy(bundle)
            obs = mutated["observations"]["gamma_market"]
            obs["payload"][field] = value
            obs["payload_sha256"] = payload_hash(obs["payload"])
            mutated["bundle_sha256"] = payload_hash({k: v for k, v in mutated.items() if k != "bundle_sha256"})
            with self.assertRaises(ContractError):
                check_market(mutated, self.start, self.plan)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "plan.json"
            persist(target, self.plan)
            with self.assertRaises(FileExistsError):
                persist(target, self.plan)

    def test_gamma_variable_fractional_precision(self):
        from execution_truth.contracts import _utc_text
        for fraction, normalized in (("1", "100000"), ("97781", "977810"),
                                     ("123456789", "123456")):
            self.assertEqual(_utc_text("2026-10-04T17:54:21." + fraction + "Z", "gamma.startDate"),
                             "2026-10-04T17:54:21." + normalized + "Z")
        with self.assertRaises(ContractError):
            _utc_text("2026-10-04T17:54:21.12345", "gamma.startDate")

    def test_not_yet_traded_book_price_is_unknown_not_zero(self):
        from execution_truth.bundle import normalize_bundle
        for value in (None, "", "MISSING"):
            bundle = raw_bundle()
            for obs in bundle["observations"]["order_books"]:
                if value == "MISSING":
                    obs["payload"].pop("last_trade_price")
                else:
                    obs["payload"]["last_trade_price"] = value
                obs["payload_sha256"] = payload_hash(obs["payload"])
            bundle["bundle_sha256"] = payload_hash({k: v for k, v in bundle.items() if k != "bundle_sha256"})
            normalized = normalize_bundle(bundle)
            self.assertTrue(all(book["last_trade_price"] is None for book in normalized["order_books"]))

    def test_missed_window_does_not_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("execution_truth.rolling_stream.utc_now", return_value=datetime(2026, 5, 5, tzinfo=timezone.utc)):
                observe_window(self.start, self.plan, Path(tmp))
            import json
            result = json.loads((Path(tmp) / str(self.start) / "result.json").read_text())
            self.assertEqual(result["status"], "missed_discovery_window")
            self.assertFalse(result["orders_authorized"])

    def test_replication_uses_runtime_prefix_without_delete(self):
        from infra.stream.service import upload
        with patch("infra.stream.service.subprocess.run") as call:
            upload(Path("/var/lib/qcrl-stream/pilot-test"), "test-bucket", "us-east-2")
        command = call.call_args.args[0]
        self.assertIn("s3://test-bucket/runtime/streams/pilot-test/", command)
        self.assertNotIn("--delete", command)
        self.assertIn("AES256", command)

    def test_replay_stops_before_worker_or_network(self):
        from execution_truth.rolling_stream import run_pilot
        with tempfile.TemporaryDirectory() as tmp:
            persist(Path(tmp) / "pilot.json", self.plan)
            with patch("execution_truth.rolling_stream.observe_window") as worker:
                with self.assertRaises(FileExistsError):
                    run_pilot(self.plan, tmp)
                worker.assert_not_called()

    def test_daily_sync_excludes_only_stream_namespace(self):
        from infra.stream.install import isolated_daily_sync
        source = ('str(runtime), "--only-show-errors",\n'
                  'f"s3://{bucket}/runtime/", "--sse", "AES256",\n        "--only-show-errors",')
        updated = isolated_daily_sync(source)
        self.assertEqual(updated.count('"--exclude", "streams/*"'), 2)
        with self.assertRaises(ValueError):
            isolated_daily_sync("unexpected wrapper")
        with self.assertRaises(ValueError):
            isolated_daily_sync(updated)
