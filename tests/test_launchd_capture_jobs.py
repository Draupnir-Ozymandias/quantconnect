from datetime import datetime, timezone
import json
from pathlib import Path
import plistlib
import tempfile
import unittest

from execution_truth import ContractError
from ops.launchd.generate_capture_jobs import generate_capture_jobs


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "execution_truth/protocols/btc_daily_phase_capture_20260925.json"


class LaunchdCaptureJobTests(unittest.TestCase):
    def test_jobs_are_unique_one_date_and_use_retry_worker(self):
        now = datetime(2026, 9, 23, 21, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            paths = generate_capture_jobs(
                PROTOCOL, directory, Path(__import__("sys").executable), now=now
            )
            self.assertEqual(3, len(paths))
            jobs = [plistlib.loads(path.read_bytes()) for path in paths]
            self.assertEqual(3, len({job["Label"] for job in jobs}))
            self.assertEqual({2026}, {
                job["StartCalendarInterval"]["Year"] for job in jobs
            })
            self.assertEqual({"early", "middle", "late"}, {
                job["ProgramArguments"][6] for job in jobs
            })
            self.assertTrue(all(
                "protocol-capture-retry" in job["ProgramArguments"]
                and "--execute" in job["ProgramArguments"]
                and job["ProgramArguments"][:2] == ["/usr/bin/caffeinate", "-dimsu"]
                for job in jobs
            ))

    def test_generation_after_any_target_is_rejected(self):
        now = datetime(2026, 9, 24, 17, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            ContractError, "before every capture target"
        ):
            generate_capture_jobs(
                PROTOCOL, directory, Path(__import__("sys").executable), now=now
            )

    def test_locked_protocol_is_valid_json_and_has_verified_market_id_context(self):
        value = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(
            "bitcoin-up-or-down-on-september-25-2026",
            value["market"]["slug"],
        )
        self.assertLess(value["locked_at_utc"], value["captures"][0]["scheduled_at_utc"])


if __name__ == "__main__":
    unittest.main()
