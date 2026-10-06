from datetime import timedelta
import copy
import gzip
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import stream_plan, collect_market_stream, verify_stream_log
from execution_truth.rolling_stream import pilot_plan, validate_plan, finalize_cases, persist, run_pilot, observe_window
from execution_truth.stream_resilience import DataWatchdog, retry_delay
from tests.test_market_stream import Clock, Socket, book
from tests.test_taker_replay import raw_bundle


def observe(watchdog, age, now, kind="price_change", scope="selected_market", asset="up"):
    event = {"timestamp": str(int((1791295200 + now - age) * 1000))}
    watchdog.observe(json.dumps(event), [{"scope": scope, "event_type": kind, "asset_ids": [asset]}], now, 1791295200 + now)


class ResilienceTests(unittest.TestCase):
    def test_initial_deadline_is_not_satisfied_by_pongs(self):
        watchdog = DataWatchdog(["up", "down"], 0)
        watchdog.observe("PONG", [{"scope": "heartbeat", "event_type": "PONG"}], 9, 1791295209)
        self.assertEqual(watchdog.reason(10, True), "initial_books_timeout")

    def test_both_books_required_and_silence_ignores_unrelated_events(self):
        watchdog = DataWatchdog(["up", "down"], 0)
        observe(watchdog, .05, 1, "book", asset="up")
        self.assertEqual(watchdog.reason(10, True), "initial_books_timeout")
        observe(watchdog, .05, 2, "book", asset="down")
        observe(watchdog, .05, 31, scope="unconfirmed_or_other_market")
        self.assertIsNone(watchdog.reason(32, False))
        self.assertEqual(watchdog.reason(32, True), "selected_book_data_silence")

    def test_stale_flow_and_fresh_event_reset(self):
        watchdog = DataWatchdog(["up", "down"], 0)
        observe(watchdog, 8, 1, "book", asset="up")
        observe(watchdog, 8, 2, "book", asset="down")
        observe(watchdog, 8, 10)
        self.assertEqual(watchdog.reason(11, True), "stale_timestamped_book_flow")
        observe(watchdog, .1, 12)
        self.assertIsNone(watchdog.reason(12, True))

    def test_future_timestamp_does_not_clear_suspicion(self):
        watchdog = DataWatchdog(["up"], 0)
        observe(watchdog, 8, 1, "book")
        observe(watchdog, -5, 3)
        self.assertEqual(watchdog.reason(11, True), "stale_timestamped_book_flow")

    def test_equal_jitter_is_bounded_and_increases(self):
        for attempt, expected in ((1, (1, 2)), (2, (2, 4)), (3, (4, 8)), (9, (4, 8))):
            self.assertEqual(retry_delay(attempt, uniform=lambda a, b: a), expected[0])
            self.assertEqual(retry_delay(attempt, uniform=lambda a, b: b), expected[1])

    def test_deferred_only_plan_keeps_live_recovery_policy_unchanged(self):
        clock=Clock()
        start=int(clock.base.timestamp())
        old=pilot_plan(start,1,now=clock.base-timedelta(seconds=60),profiling=True)
        new=pilot_plan(start,1,now=clock.base-timedelta(seconds=60),profiling=True,deferred=True)
        self.assertNotIn("resilience",new)
        self.assertEqual(new["profiling"],old["profiling"])
        self.assertEqual(validate_plan(new),new)
        new["verification_phase"]="during_capture"
        new["plan_sha256"]=payload_hash({k:v for k,v in new.items() if k!="plan_sha256"})
        with self.assertRaises(ContractError):validate_plan(new)

    def test_versioned_plan_and_rehashed_policy_tamper(self):
        clock = Clock()
        plan = pilot_plan(int(clock.base.timestamp()), 1, now=clock.base-timedelta(seconds=60), profiling=True, resilient=True)
        self.assertEqual(plan["schema_version"], "qcrl.btc_5m_rolling_pilot.v4")
        self.assertEqual(validate_plan(plan), plan)
        plan["resilience"]["initial_books_seconds"] = 1
        plan["plan_sha256"] = payload_hash({k:v for k,v in plan.items() if k != "plan_sha256"})
        with self.assertRaises(ContractError):
            validate_plan(plan)
        with self.assertRaises(ContractError):
            stream_plan(raw_bundle(), resilient=True)

    def test_pong_only_socket_closes_and_retry_does_not_stack(self):
        raw, clock = raw_bundle(), Clock()
        spec = stream_plan(raw, max_seconds=60, segmented=True, resilient=True)
        sockets=[]
        def connector():
            self.assertTrue(all(s.closed for s in sockets))
            socket=Socket(clock,["PONG"]*100)
            sockets.append(socket)
            return socket
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"stream"
            result=collect_market_stream(raw,spec,root,connector=connector,clock=clock.utc,monotonic=clock.mono,pause=clock.pause)
            self.assertEqual(result["status"],"connection_limit")
            self.assertEqual(len(sockets),3)
            self.assertTrue(all(s.closed for s in sockets))
            rows=[]
            for segment in sorted(root.glob("*.gz")):
                with gzip.open(segment,"rt") as f:rows.extend(json.loads(line) for line in f)
            self.assertEqual([r["payload"]["reason"] for r in rows if r["kind"]=="connection_gap"], ["initial_books_timeout"]*3)
            self.assertEqual(len([r for r in rows if r["kind"]=="retry_wait"]),2)
            self.assertTrue(verify_stream_log(root)["session_end_present"])

    def test_finalize_retains_capture_and_failure_as_unhealthy_evidence(self):
        clock=Clock()
        plan=pilot_plan(int(clock.base.timestamp()),1,now=clock.base-timedelta(seconds=60),resilient=True)
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)/str(plan["market_starts"][0])
            capture={"status":"failed","error_type":"example"}
            capture["result_sha256"]=payload_hash(capture)
            persist(directory/"capture_result.json",capture)
            before=(directory/"capture_result.json").read_bytes()
            with patch("execution_truth.rolling_stream.verify_stream_log",side_effect=ContractError("bad prefix")):
                finalize_cases(plan,tmp)
            result=json.loads((directory/"result.json").read_text())
            self.assertEqual(result["verification_error_type"],"ContractError")
            self.assertEqual(result["capture_result_sha256"],capture["result_sha256"])
            self.assertEqual((directory/"capture_result.json").read_bytes(),before)
            with self.assertRaises(FileExistsError):
                finalize_cases(plan,tmp)

    def test_finalization_runs_only_after_workers_join(self):
        clock=Clock();start=int(clock.base.timestamp())
        plan=pilot_plan(start,2,now=clock.base-timedelta(seconds=60),resilient=True)
        finished=[]
        barrier=threading.Barrier(2)
        def observe_mock(start,plan,root):
            barrier.wait(timeout=3)
            finished.append(start)
        def finalize_mock(plan,root):
            self.assertEqual(set(finished),set(plan["market_starts"]))
        with tempfile.TemporaryDirectory() as tmp, patch("execution_truth.rolling_stream.utc_now",return_value=clock.base+timedelta(seconds=1000)), patch("execution_truth.rolling_stream.observe_window",side_effect=observe_mock), patch("execution_truth.rolling_stream.finalize_cases",side_effect=finalize_mock) as finalize, patch("execution_truth.rolling_stream.cohort_health",return_value={"healthy":False}):
            run_pilot(plan,tmp)
            finalize.assert_called_once()

    def test_failed_worker_does_not_verify_and_keeps_postclose_checkpoint(self):
        clock=Clock();raw=raw_bundle();start=int(clock.base.timestamp())
        plan=pilot_plan(start,1,now=clock.base-timedelta(seconds=60),resilient=True)
        class Acquirer:
            def __init__(self,*args):pass
            def resolve_market_slug(self,*args):return {"resolved_market_id":"123"}
            def acquire_market_bundle(self,*args):return raw
            def acquire_market_settlement(self,*args):return {}
        with tempfile.TemporaryDirectory() as tmp, patch("execution_truth.rolling_stream.PublicPolymarketAcquirer",Acquirer), patch("execution_truth.rolling_stream.utc_now",clock.utc), patch("execution_truth.rolling_stream.time.sleep",clock.pause), patch("execution_truth.rolling_stream.store_raw_slug_resolution"), patch("execution_truth.rolling_stream.store_raw_bundle"), patch("execution_truth.rolling_stream.store_raw_settlement",return_value=Path("checkpoint.json")), patch("execution_truth.rolling_stream.check_market",return_value={}), patch("execution_truth.rolling_stream.collect_market_stream",side_effect=ContractError("quota")), patch("execution_truth.rolling_stream.verify_stream_log") as verify:
            observe_window(start,plan,Path(tmp))
            verify.assert_not_called()
            result=json.loads((Path(tmp)/str(start)/"capture_result.json").read_text())
            self.assertEqual(result["status"],"failed")
            self.assertEqual([c["label"] for c in result["metadata_checkpoints"]],["final","postclose_120s"])
            self.assertGreaterEqual(clock.utc().timestamp(),start+420)

    def test_successful_worker_also_defers_verification(self):
        clock=Clock();raw=raw_bundle();start=int(clock.base.timestamp())
        plan=pilot_plan(start,1,now=clock.base-timedelta(seconds=60),deferred=True)
        class Acquirer:
            def __init__(self,*args):pass
            def resolve_market_slug(self,*args):return {"resolved_market_id":"123"}
            def acquire_market_bundle(self,*args):return raw
            def acquire_market_settlement(self,*args):return {}
        with tempfile.TemporaryDirectory() as tmp, patch("execution_truth.rolling_stream.PublicPolymarketAcquirer",Acquirer), patch("execution_truth.rolling_stream.utc_now",clock.utc), patch("execution_truth.rolling_stream.time.sleep",clock.pause), patch("execution_truth.rolling_stream.store_raw_slug_resolution"), patch("execution_truth.rolling_stream.store_raw_bundle"), patch("execution_truth.rolling_stream.store_raw_settlement",return_value=Path("checkpoint.json")), patch("execution_truth.rolling_stream.check_market",return_value={}), patch("execution_truth.rolling_stream.collect_market_stream",return_value={"status":"lifecycle_stop"}), patch("execution_truth.rolling_stream.verify_stream_log") as verify:
            observe_window(start,plan,Path(tmp))
            verify.assert_not_called()
            result=json.loads((Path(tmp)/str(start)/"capture_result.json").read_text())
            self.assertEqual(result["status"],"observed_lifecycle_stop")
            self.assertNotIn("verification",result)
            self.assertFalse((Path(tmp)/str(start)/"result.json").exists())


if __name__=="__main__":unittest.main()
