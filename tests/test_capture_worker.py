from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth import AcquisitionError, ContractError, run_capture_with_retries
from tests.test_capture_protocol import protocol


class MutableClock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value

    def sleep(self, seconds):
        self.value += timedelta(seconds=seconds)


class CaptureWorkerTests(unittest.TestCase):
    def test_retries_only_acquisition_error_then_collects(self):
        clock = MutableClock(datetime(2026, 5, 4, 23, 52, 5, tzinfo=timezone.utc))
        result = {"status": "collected", "market_id": "123456"}
        with tempfile.TemporaryDirectory() as directory, patch(
            "execution_truth.capture_worker.execute_protocol_capture",
            side_effect=[AcquisitionError("temporary DNS failure"), result],
        ) as execute:
            report = run_capture_with_retries(
                protocol(), "middle", Path(directory) / "raw",
                Path(directory) / "state.json", clock=clock, sleeper=clock.sleep,
                acquirer_factory=lambda: object(),
            )
        self.assertEqual("collected", report["status"])
        self.assertEqual(2, execute.call_count)
        self.assertEqual("acquisition_error", report["attempts"][0]["outcome"])
        self.assertEqual(5, report["attempts"][0]["backoff_seconds"])
        self.assertEqual("collected", report["attempts"][1]["outcome"])

    def test_contract_failure_is_not_retried(self):
        clock = MutableClock(datetime(2026, 5, 4, 23, 52, 5, tzinfo=timezone.utc))
        with tempfile.TemporaryDirectory() as directory, patch(
            "execution_truth.capture_worker.execute_protocol_capture",
            side_effect=ContractError("market terms changed"),
        ) as execute, self.assertRaisesRegex(ContractError, "terms changed"):
            run_capture_with_retries(
                protocol(), "middle", Path(directory) / "raw",
                Path(directory) / "state.json", clock=clock, sleeper=clock.sleep,
                acquirer_factory=lambda: object(),
            )
        self.assertEqual(1, execute.call_count)

    def test_does_not_back_off_past_deadline(self):
        clock = MutableClock(datetime(2026, 5, 4, 23, 52, 19, tzinfo=timezone.utc))
        with tempfile.TemporaryDirectory() as directory, patch(
            "execution_truth.capture_worker.execute_protocol_capture",
            side_effect=AcquisitionError("temporary DNS failure"),
        ) as execute:
            report = run_capture_with_retries(
                protocol(), "middle", Path(directory) / "raw",
                Path(directory) / "state.json", clock=clock, sleeper=clock.sleep,
                acquirer_factory=lambda: object(),
            )
        self.assertEqual("window_closed", report["status"])
        self.assertEqual(1, execute.call_count)
        self.assertNotIn("backoff_seconds", report["attempts"][0])

    def test_invalid_retry_policy_fails_before_capture(self):
        with self.assertRaisesRegex(ContractError, "max_attempts"):
            run_capture_with_retries(
                protocol(), "middle", "/tmp/raw", "/tmp/state",
                max_attempts=0,
            )


if __name__ == "__main__":
    unittest.main()
