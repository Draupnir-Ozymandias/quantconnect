import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from execution_truth import (
    AcquisitionError,
    ContractError,
    PublicPolymarketAcquirer,
    normalize_discovery,
)


FIXTURES = Path(__file__).parent / "fixtures" / "polymarket"
TARGET = "2026-05-04T23:52:00Z"
SPEC = {
    "schema_version": "qcrl.polymarket_discovery_spec.v1",
    "series_id": "10684",
    "recurrence": "5m",
    "asset": "btc",
    "duration": "5m",
    "twap_enabled": True,
    "twap_lookback_seconds": 60,
    "resolution_source": "https://data.chain.link/streams/btc-usd-twap-60s-streams",
    "outcomes": ["Up", "Down"],
}


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeDiscoveryTransport:
    def __init__(self, series=None, event=None):
        self.series = series or fixture("series.json")
        self.event = event or fixture("event.json")
        self.calls = []

    def get_json(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        if "/series/" in url:
            return copy.deepcopy(self.series)
        if "/events/" in url:
            event = copy.deepcopy(self.event)
            requested_id = url.rsplit("/", 1)[-1]
            if requested_id != event["id"]:
                summary = next(
                    item for item in self.series["events"]
                    if item["id"] == requested_id
                )
                event["id"] = requested_id
                event["startTime"] = summary["startTime"]
                event["endDate"] = summary["endDate"]
                for market in event["markets"]:
                    market["eventStartTime"] = summary["startTime"]
                    market["endDate"] = summary["endDate"]
            return event
        raise AssertionError(f"unexpected route: {url}")


class SequenceClock:
    def __init__(self):
        self.value = datetime(2026, 5, 4, 23, 52, tzinfo=timezone.utc)

    def __call__(self):
        current = self.value
        self.value += timedelta(milliseconds=10)
        return current


class ExecutionTruthDiscoveryTests(unittest.TestCase):
    def acquire(self, transport=None, target=TARGET):
        transport = transport or FakeDiscoveryTransport()
        acquirer = PublicPolymarketAcquirer(
            transport=transport, clock=SequenceClock()
        )
        return acquirer.acquire_series_event("10684", target), transport

    def test_acquisition_selects_by_explicit_interval_not_list_order(self):
        raw, transport = self.acquire()
        self.assertEqual(2, len(transport.calls))
        self.assertEqual(
            "https://gamma-api.polymarket.com/series/10684",
            transport.calls[0][0],
        )
        self.assertEqual(
            "https://gamma-api.polymarket.com/events/event-current",
            transport.calls[1][0],
        )
        self.assertNotIn("slug", json.dumps(raw).casefold())

    def test_discovery_selects_exact_configured_market(self):
        raw, _ = self.acquire()
        result = normalize_discovery(raw, SPEC)
        self.assertEqual("123456", result["selected_market_id"])
        self.assertEqual("event-current", result["event_id"])
        self.assertEqual(TARGET, result["target_at_utc"])
        self.assertEqual(64, len(result["result_sha256"]))

    def test_event_intervals_are_half_open(self):
        raw, transport = self.acquire(target="2026-05-04T23:55:00Z")
        self.assertEqual(
            "https://gamma-api.polymarket.com/events/event-next",
            transport.calls[1][0],
        )
        self.assertEqual("event-next", raw["observations"]["event"]["payload"]["id"])

    def test_acquisition_rejects_overlapping_event_intervals(self):
        series = fixture("series.json")
        duplicate = copy.deepcopy(series["events"][1])
        duplicate["id"] = "event-duplicate"
        series["events"].append(duplicate)
        with self.assertRaisesRegex(AcquisitionError, "found 2"):
            self.acquire(FakeDiscoveryTransport(series=series))

    def test_acquisition_rejects_non_datetime_target(self):
        with self.assertRaisesRegex(AcquisitionError, "ISO-8601"):
            self.acquire(target=12345)

    def test_discovery_rejects_asset_drift(self):
        event = fixture("event.json")
        event["markets"][0]["cryptoMarketConfig"]["asset"] = "eth"
        raw, _ = self.acquire(FakeDiscoveryTransport(event=event))
        with self.assertRaisesRegex(ContractError, "found 0"):
            normalize_discovery(raw, SPEC)

    def test_discovery_rejects_ambiguous_eligible_markets(self):
        event = fixture("event.json")
        duplicate = copy.deepcopy(event["markets"][0])
        duplicate["id"] = "654321"
        duplicate["conditionId"] = "second-condition"
        event["markets"].append(duplicate)
        raw, _ = self.acquire(FakeDiscoveryTransport(event=event))
        with self.assertRaisesRegex(ContractError, "found 2"):
            normalize_discovery(raw, SPEC)

    def test_discovery_rejects_event_outside_series(self):
        event = fixture("event.json")
        event["series"] = [{"id": "other-series"}]
        raw, _ = self.acquire(FakeDiscoveryTransport(event=event))
        with self.assertRaisesRegex(ContractError, "not a member"):
            normalize_discovery(raw, SPEC)

    def test_discovery_rejects_raw_tampering(self):
        raw, _ = self.acquire()
        raw["observations"]["event"]["payload"]["id"] = "tampered"
        with self.assertRaisesRegex(ContractError, "raw discovery hash mismatch"):
            normalize_discovery(raw, SPEC)

    def test_discovery_rejects_malformed_twap_lookback(self):
        event = fixture("event.json")
        event["markets"][0]["cryptoMarketConfig"]["twapLookbackSeconds"] = None
        raw, _ = self.acquire(FakeDiscoveryTransport(event=event))
        with self.assertRaisesRegex(ContractError, "found 0"):
            normalize_discovery(raw, SPEC)

    def test_discovery_rejects_series_event_interval_drift(self):
        event = fixture("event.json")
        event["startTime"] = "2026-05-04T23:49:00Z"
        raw, _ = self.acquire(FakeDiscoveryTransport(event=event))
        with self.assertRaisesRegex(ContractError, "intervals disagree"):
            normalize_discovery(raw, SPEC)


if __name__ == "__main__":
    unittest.main()
