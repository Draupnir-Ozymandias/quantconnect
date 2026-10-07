from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from execution_truth.connection_freshness import ConnectionFreshness, close_diagnostics
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log, StreamTransportError
from execution_truth.receive_path import sample_clock
from execution_truth.rolling_stream import pilot_plan, validate_plan
from execution_truth.stream_segments import SegmentedStreamLog
from tests.test_market_stream import Clock, Socket, book
from tests.test_receive_capture import rows
from tests.test_taker_replay import raw_bundle


def observe(tracker, now, age, kind="price_change", asset="up", missing=False):
    event = {} if missing else {"timestamp": str(int((1791389700 + now - age) * 1000))}
    from datetime import datetime, timezone
    stamp = {"utc": datetime.fromtimestamp(1791389700 + now, timezone.utc).isoformat(),
             "monotonic_before": now, "monotonic_after": now, "clock_domain": "test"}
    tracker.observe(json.dumps(event), [{"scope": "selected_market", "event_type": kind, "asset_ids": [asset]}],
                    {"application_delivery": stamp, "receive_marker": None})


class FreshnessTests(unittest.TestCase):
    def test_brief_stale_episode_clears_and_sustained_episode_persists(self):
        tracker = ConnectionFreshness(1, ["up", "down"])
        observe(tracker, 1, 8)
        observe(tracker, 2, .1)
        self.assertIsNone(tracker.stale_since)
        self.assertEqual(tracker.transition_count, 2)
        observe(tracker, 3, 8)
        observe(tracker, 14, 9)
        self.assertEqual(tracker.stale_since["monotonic_after"], 3)

    def test_unknown_and_negative_do_not_clear_stale_or_prove_state(self):
        tracker = ConnectionFreshness(1, ["up"])
        observe(tracker, 1, 8)
        observe(tracker, 2, 0, missing=True)
        observe(tracker, 3, -1)
        tracker.observe("PONG", [], {})
        self.assertEqual(tracker.stale_since["monotonic_after"], 1)
        self.assertEqual(tracker.counts["negative_age_events"], 1)
        self.assertEqual(tracker.counts["missing_or_invalid_timestamp_events"], 1)
        self.assertFalse(tracker.snapshot(4, "periodic")["state_freshness_proven"])

    def test_token_witnesses_reset_and_history_is_bounded(self):
        tracker = ConnectionFreshness(1, ["up", "down"])
        observe(tracker, 0, 0, kind="book")
        observe(tracker, 1, 0, asset="down")
        self.assertEqual(set(tracker.books), {"up"})
        self.assertEqual(set(tracker.updates), {"down"})
        for i in range(2, 32):
            observe(tracker, i, 8 if i % 2 == 0 else 0)
        sample = tracker.snapshot(32, "connection_end")
        self.assertEqual(len(sample["recent_transitions"]), 8)
        self.assertEqual(sample["omitted_earlier_transitions"], 22)
        fresh = ConnectionFreshness(2, ["up", "down"])
        self.assertFalse(fresh.books or fresh.updates or fresh.last_fresh)

    def test_close_diagnostics_follow_causes_but_never_parse_code_text(self):
        cause = RuntimeError("server text must not be retained")
        cause.rcvd, cause.sent, cause.rcvd_then_sent = SimpleNamespace(code=1013), SimpleNamespace(code=1000), True
        wrapped = StreamTransportError("ConnectionClosedError")
        wrapped.__cause__ = cause
        result = close_diagnostics(wrapped)
        self.assertEqual((result["received_code"], result["sent_code"]), (1013, 1000))
        self.assertNotIn("server text", json.dumps(result))
        unknown = close_diagnostics(StreamTransportError("rcvd_code=1013"))
        self.assertIsNone(unknown["received_code"])
        self.assertEqual(close_diagnostics(StreamTransportError("stale_timestamped_book_flow"))["origin"], "watchdog")

    def test_plan_versions_and_rehashed_policy_tampering(self):
        clock = Clock()
        plan = pilot_plan(int(clock.base.timestamp()) + 300, now=clock.utc(), profiling=True,
                          receive_path=True, deferred=True, resilient=True, freshness_telemetry=True, receive_policy="v2")
        self.assertEqual(plan["schema_version"], "qcrl.btc_5m_rolling_pilot.v7")
        self.assertEqual(validate_plan(plan), plan)
        plan["freshness_telemetry"]["fresh_seconds"] = 50
        plan["plan_sha256"] = payload_hash({k: v for k, v in plan.items() if k != "plan_sha256"})
        with self.assertRaises(ContractError):
            validate_plan(plan)
        with self.assertRaises(ContractError):
            stream_plan(raw_bundle(), freshness_telemetry=True)

    def test_callback_and_delivery_ages_are_distinct_and_unknown_stays_null(self):
        from datetime import datetime, timezone
        tracker = ConnectionFreshness(1, ["up"])
        stamp = {"utc": datetime.fromtimestamp(1791389708, timezone.utc).isoformat(),
                 "monotonic_before": 8, "monotonic_after": 8, "clock_domain": "test"}
        callback = dict(stamp, utc=datetime.fromtimestamp(1791389707, timezone.utc).isoformat())
        tracker.observe(json.dumps({"timestamp": "1791389700000"}),
            [{"scope": "selected_market", "event_type": "book", "asset_ids": ["up"]}],
            {"application_delivery": stamp, "receive_marker": {"last_receive_observation": callback},
             "first_observation_to_delivery": {"timing_eligible": False},
             "last_observation_to_delivery": {"timing_eligible": True}})
        self.assertEqual(tracker.latest["nominal_callback_age_seconds"], 7)
        self.assertEqual(tracker.latest["nominal_delivery_age_seconds"], 8)
        self.assertFalse(tracker.latest["callback_age_timing_eligible"])
        observe(tracker, 9, .1)
        self.assertIsNone(tracker.latest["nominal_callback_age_seconds"])

    def test_periodic_samples_are_bounded_and_snapshot_is_a_deep_copy(self):
        tracker = ConnectionFreshness(1, ["up"])
        class Log:
            def __init__(self): self.records = []
            def append(self, kind, payload): self.records.append(payload)
        log = Log()
        tracker.emit(log, 0, "subscribed", force=True)
        tracker.emit(log, 1)
        self.assertEqual(len(log.records), 1)
        observe(tracker, 2, 8)
        tracker.emit(log, 5)
        log.records[-1]["counts"]["stale_events"] = 99
        self.assertEqual(tracker.counts["stale_events"], 1)
        tracker.samples = 123
        with self.assertRaises(ContractError): tracker.emit(log, 6, "connection_end", force=True)

    def test_real_library_close_object_retains_codes_without_server_reason(self):
        from websockets.exceptions import ConnectionClosedError
        from websockets.frames import Close
        error = ConnectionClosedError(Close(1013, "private server text"), Close(1013, "private server text"), True)
        result = close_diagnostics(error)
        self.assertEqual(result["received_code"], 1013)
        self.assertEqual(result["sent_code"], 1013)
        self.assertNotIn("private", json.dumps(result))

    def capture(self, root):
        clock = Clock()
        spec = stream_plan(raw_bundle(), segmented=True, profiling=True, receive_path=True, resilient=True,
                           source_plan_sha256="a" * 64, receive_policy="v2", freshness_telemetry=True,
                           max_seconds=12, max_frames=4)
        def connector(tracker, number, **kwargs):
            frames = [json.dumps(book(spec, asset)) for asset in spec["asset_ids"]]
            if number == 1:
                frames.append(StreamTransportError("stale_timestamped_book_flow"))
            class Instrumented(Socket):
                def recv(self, timeout):
                    raw = super().recv(timeout)
                    tracker.observe_frame(number, 1, True, raw.encode(), sample_clock(clock.utc, clock.mono, tracker.domain))
                    return raw, tracker.deliver(number, raw, sample_clock(clock.utc, clock.mono, tracker.domain))
            socket = Instrumented(clock, frames)
            socket.reset = tracker.begin_connection(number)
            return socket
        collect_market_stream(raw_bundle(), spec, root, connector=connector, clock=clock.utc,
                              monotonic=clock.mono, pause=clock.pause, clock_domain="fixture.freshness")
        return clock, spec

    def test_capture_replay_verifies_reconnect_and_structured_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stream"
            self.capture(root)
            verified = verify_stream_log(root)
            self.assertEqual(verified["frames"], 4)
            snapshots = [r["payload"] for r in rows(root) if r["kind"] == "connection_freshness"]
            self.assertEqual([s["connection"] for s in snapshots if s["reason"] == "connection_end"], [1, 2])
            self.assertTrue(all(not s["counts"] for s in snapshots if s["reason"] == "subscribed"))
            gap = next(r["payload"] for r in rows(root) if r["kind"] == "connection_gap")
            self.assertEqual(gap["close_diagnostics"]["origin"], "watchdog")

    def test_rehashed_snapshot_tampering_is_rejected_by_raw_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            clock, spec = self.capture(source)
            altered = rows(source)
            sample = next(r["payload"] for r in altered if r["kind"] == "connection_freshness" and r["payload"]["reason"] == "connection_end")
            sample["counts"]["fresh_events"] = 999
            sample["sample_sha256"] = payload_hash({k: v for k, v in sample.items() if k != "sample_sha256"})
            target = Path(tmp) / "tampered"
            log = SegmentedStreamLog(target, clock.utc, clock.mono, spec["storage"])
            for row in altered:
                log.append(row["kind"], row["payload"])
            log.close()
            with self.assertRaisesRegex(ContractError, "freshness sample differs"):
                verify_stream_log(target)

    def test_missing_terminal_sample_and_malformed_close_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            clock, spec = self.capture(source)
            original = rows(source)
            for mode in ("missing_final", "invented_code", "quota_final"):
                altered = deepcopy(original)
                if mode in ("missing_final", "quota_final"):
                    altered = [r for r in altered if not (r["kind"] == "connection_freshness"
                        and r["payload"]["reason"] == "connection_end" and r["payload"]["connection"] == 2)]
                    if mode == "quota_final":
                        altered[-1]["payload"]["status"] = "storage_limit"
                else:
                    next(r["payload"] for r in altered if r["kind"] == "connection_gap")["close_diagnostics"]["received_code"] = 1013
                target = Path(tmp) / mode
                log = SegmentedStreamLog(target, clock.utc, clock.mono, spec["storage"])
                for row in altered: log.append(row["kind"], row["payload"])
                log.close()
                if mode == "quota_final":
                    self.assertFalse(verify_stream_log(target)["freshness_verification"]["all_final_snapshots_present"])
                else:
                    with self.assertRaises(ContractError): verify_stream_log(target)


if __name__ == "__main__":
    unittest.main()
