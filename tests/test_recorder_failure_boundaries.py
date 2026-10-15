"""Deterministic frozen-path failure reproductions; no native timing/transport run.

These tests preserve evidence of the current shortcomings. Prospective fixes must
be separately wired/frozen rather than weakening the old audit or these budgets.
"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from execution_truth.contracts import payload_hash
from execution_truth.market_stream import stream_plan
from infra.stream.recorder_application_budget import declare
from infra.stream.recorder_application_evaluator import timing_gate
from infra.stream.recorder_completion import CompletionWitnesses
from infra.stream.recorder_completion_lane import CompletionStreamLog, collect_with_completion
from infra.stream import recorder_application_worker as worker
from tests.test_market_stream import Clock
from tests.test_taker_replay import raw_bundle


class PersistenceBoundaryTests(unittest.TestCase):
    def log(self, root, clock):
        spec = stream_plan(raw_bundle(), segmented=True)
        witness = CompletionWitnesses(spec, 'offline.boundary', clock=clock.utc,
                                      monotonic=clock.mono, execute=True)
        witness.validate_spec(spec)
        log = CompletionStreamLog(root, clock.utc, clock.mono, spec['storage'],
                                  completion_observer=witness)
        log.append('session_start', {'spec': spec, 'spec_sha256': payload_hash(spec)})
        return log, witness

    def frame(self, log, witness):
        witness.application_return('PONG', 1)
        log.append('frame', {'connection': 1, 'raw_text': 'PONG', 'classification': []})

    def test_just_under_interval_then_full_receive_leaves_no_persistence_margin(self):
        clock = Clock()
        with tempfile.TemporaryDirectory() as tmp:
            log, witness = self.log(Path(tmp)/'archive', clock)
            try:
                # A prior fsync just finished. New frame immediately follows it.
                clock.seconds = .000001
                self.frame(log, witness)
                clock.seconds = .999999
                self.frame(log, witness)
                self.assertEqual(len(witness.barriers), 1)
                # The existing loop allows another full 1-s receive at this point.
                clock.pause(1)
                with patch.object(log.writer, 'flush', side_effect=lambda: clock.pause(.0002)), \
                     patch.object(log.raw, 'flush', side_effect=lambda: clock.pause(.0003)), \
                     patch('infra.stream.recorder_completion_lane.os.fsync',
                           side_effect=lambda fd: clock.pause(.0005)) as sync:
                    log.sync_if_due()
                self.assertEqual(sync.call_count, 1)
                delay = witness.barriers[-1]['end'] - witness.frames[0]['returned']['before']
                self.assertGreater(delay, 2)
                self.assertAlmostEqual(delay, 2.000998)
                self.assertAlmostEqual(witness.barriers[-1]['end']-witness.barriers[-1]['begin'], .0005)
                # The return-to-durable gate includes the two pre-fsync flushes.
                gate = timing_gate([{'append_upper_seconds': 0, 'durable_upper_seconds': delay}],
                                   witness.frames[:1], [0], declare()['budgets'])
                self.assertEqual(gate['verdict'], 'fail')
            finally:
                log.close()

    def test_exact_sync_interval_flushes_but_just_before_does_not(self):
        for at, expected in ((.999999, 0), (1, 1), (1.000001, 1)):
            with self.subTest(at=at), tempfile.TemporaryDirectory() as tmp:
                clock = Clock(); log, witness = self.log(Path(tmp)/'archive', clock)
                try:
                    self.frame(log, witness); clock.seconds = at
                    with patch.object(log, 'sync', wraps=log.sync) as sync:
                        log.sync_if_due()
                    self.assertEqual(sync.call_count, expected)
                finally:
                    log.close()

    def test_count_boundary_63_then_64_and_empty_timer(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock = Clock(); log, witness = self.log(Path(tmp)/'archive', clock)
            try:
                for _ in range(63): self.frame(log, witness)
                self.assertEqual(len(witness.barriers), 1)
                self.frame(log, witness)
                self.assertEqual(len(witness.barriers), 2)
                clock.pause(10)
                with patch.object(log, 'sync', wraps=log.sync) as sync:
                    log.sync_if_due()
                self.assertEqual(sync.call_count, 0)
            finally:
                log.close()

    def test_each_persistence_stage_fault_has_no_success_or_automatic_retry(self):
        for stage in ('gzip_flush', 'file_flush', 'fsync'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as tmp:
                clock = Clock(); log, witness = self.log(Path(tmp)/'archive', clock)
                self.frame(log, witness); clock.pause(1)
                before = len(witness.barriers)
                target = ('infra.stream.recorder_completion_lane.os.fsync' if stage == 'fsync'
                          else None)
                fault = (patch(target, side_effect=OSError(stage)) if target else
                         patch.object(log.writer if stage == 'gzip_flush' else log.raw,
                                      'flush', side_effect=OSError(stage)))
                try:
                    with fault as operation:
                        with self.assertRaises(OSError): log.sync_if_due()
                        self.assertEqual(operation.call_count, 1)
                    self.assertEqual(len(witness.barriers), before)
                    self.assertIn('sync_failed', witness.failure)
                finally:
                    log.close()

    def test_two_second_threshold_has_no_tolerance(self):
        for value, verdict in ((2, 'pass'), (2.000000001, 'fail')):
            result = timing_gate([{'append_upper_seconds': .001, 'durable_upper_seconds': value}],
                                 [{'returned': {'before': 0, 'after': 0}}], [0], declare()['budgets'])
            self.assertEqual(result['verdict'], verdict)

    def test_actual_loop_requests_full_timeout_with_pending_frame(self):
        clock = Clock(); timeouts = []
        class Socket:
            def send(self, value): pass
            def recv(self, timeout):
                timeouts.append(timeout)
                clock.pause(.000001 if len(timeouts) == 1 else timeout)
                if len(timeouts) == 1: return 'PONG'
                raise TimeoutError()
            def close(self): pass
        with tempfile.TemporaryDirectory() as tmp:
            spec = stream_plan(raw_bundle(), segmented=True, max_seconds=3)
            witness = CompletionWitnesses(spec, 'offline.loop', clock=clock.utc,
                                          monotonic=clock.mono, execute=True)
            collect_with_completion(raw_bundle(), spec, Path(tmp)/'archive', connector=Socket,
                                    clock=clock.utc, monotonic=clock.mono, pause=clock.pause,
                                    completion_observer=witness)
            self.assertEqual(timeouts[:2], [1, 1])


class DrainBoundaryTests(unittest.TestCase):
    def produce(self, mode, close_type='ConnectionClosedOK'):
        # Run the real producer handler/drain with synchronous deterministic
        # thread scheduling, fake connections/readers and an injected transmitter.
        # No WebSocket connection, Linux reader or real clock/sleep is exercised.
        events = [threading.Event() for _ in range(3)]
        drains = []
        clock = {'value': 10}
        from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
        from websockets.frames import Close
        failure = (OSError('read fault') if close_type == 'OSError' else
                   (ConnectionClosedOK if close_type == 'ConnectionClosedOK' else ConnectionClosedError)(
                       Close(1000 if close_type == 'ConnectionClosedOK' else 1011, ''),
                       Close(1000 if close_type == 'ConnectionClosedOK' else 1011, ''), True))
        case = dict(artifact_sha256='offline-case', case='steady-0', epoch=100,
                    spec={'subscription': {'type': 'market'}})
        conn = SimpleNamespace(calls=0)
        def recv(timeout):
            conn.calls += 1
            if conn.calls == 1: return json.dumps(case['spec']['subscription'])
            if mode == 'stop_during_recv': events[2].set()
            if mode == 'timeout_first' and conn.calls == 2: raise TimeoutError()
            if mode == 'unexpected_control' and conn.calls == 2: return 'NOT_PING'
            raise failure
        conn.recv = recv
        conn.close = lambda: None
        reader = SimpleNamespace(expected={'boot_id': 'boot', 'cgroup': '/producer'}, read=lambda **kw: {})
        ready = dict(case_sha256='offline-case', at=1,
                     identity={'boot_id': 'boot', 'cgroup': '/consumer'})
        class Thread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self):
                if self.target.__name__ == 'drain': drains.append(self.target)
                else: self.target()
            def join(self, **kwargs): pass
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('worker-ready', 'observer-ready', 'bindings-ready'):
                worker.publish(root/(name+'.json'), ready)
            server = SimpleNamespace(socket=SimpleNamespace(getsockname=lambda: ('127.0.0.1', 12345)),
                                     shutdown=lambda: None)
            def serve(handler, *args, **kwargs):
                server.serve_forever = lambda: handler(conn)
                class Scope:
                    def __enter__(self): return server
                    def __exit__(self, *args): pass
                return Scope()
            def transmit(*args):
                # Closure on either side of the final-send completion boundary.
                result = dict(rows=list(range(67 if mode == 'premature' else 68)),
                              complete=mode != 'premature', error='closed' if mode == 'premature' else None)
                drains[0]()
                if mode == 'missing_marker': clock['value'] = 286
                else: (root/'capture-closed.json').write_text('{}')
                return result
            with patch.object(worker, 'context', return_value=case), \
                 patch.object(worker, 'LinuxReader', return_value=reader), \
                 patch.object(worker.time, 'monotonic', side_effect=lambda: clock['value']), \
                 patch.object(worker.threading, 'Thread', Thread), \
                 patch.object(worker.threading, 'Event', side_effect=events), \
                 patch('websockets.sync.server.serve', side_effect=serve):
                worker.produce(root, {}, execute=True, transmitter=transmit)
            result = worker.control(root/'producer.json')
            return result, conn.calls

    def test_normal_close_after_all_sends_is_currently_reported_as_error(self):
        result, calls = self.produce('complete')
        self.assertTrue(result['result']['complete'])
        self.assertEqual(result['control_errors'], ['ConnectionClosedOK'])
        self.assertEqual(calls, 2)

    def test_premature_normal_close_is_not_safe_merely_because_code_is_normal(self):
        result, _ = self.produce('premature')
        self.assertFalse(result['result']['complete'])
        self.assertEqual(len(result['result']['rows']), 67)
        self.assertEqual(result['control_errors'], ['ConnectionClosedOK'])

    def test_abnormal_close_and_read_fault_remain_errors_after_all_sends(self):
        for name in ('ConnectionClosedError', 'OSError'):
            with self.subTest(name=name):
                result, _ = self.produce('complete', name)
                self.assertEqual(result['control_errors'], [name])

    def test_stop_race_currently_suppresses_unexpected_receive_exception(self):
        result, _ = self.produce('stop_during_recv', 'OSError')
        self.assertEqual(result['control_errors'], [])

    def test_timeout_is_not_closure_and_unexpected_control_is_preserved(self):
        result, calls = self.produce('timeout_first')
        self.assertEqual(calls, 3)
        self.assertEqual(result['control_errors'], ['ConnectionClosedOK'])
        result, _ = self.produce('unexpected_control')
        self.assertEqual([row['text'] for row in result['controls']], ['NOT_PING'])

    def test_capture_closed_marker_is_currently_presence_only_not_validated(self):
        # Every fixture above publishes an unsigned empty marker: the producer
        # adopts its presence. A successor must bind it and confirm full capture.
        result, _ = self.produce('complete')
        self.assertTrue(result['result']['complete'])
        self.assertEqual(result['control_errors'], ['ConnectionClosedOK'])

    def test_missing_capture_marker_deadline_currently_has_no_explicit_error(self):
        result, _ = self.produce('missing_marker')
        self.assertTrue(result['result']['complete'])
        self.assertIsNone(result['result']['error'])
        self.assertEqual(result['control_errors'], ['ConnectionClosedOK'])

    def test_failed_recorder_also_publishes_capture_closed_marker(self):
        class Thread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): self.target()
            def join(self, **kwargs): pass
            def is_alive(self): return False
        identity = {'boot_id': 'boot', 'cgroup': '/consumer'}
        reader = SimpleNamespace(expected=identity, read=lambda **kwargs: {})
        case = dict(artifact_sha256='offline-case', case='steady-0', epoch=100,
                    boot_id='boot', raw_bundle={}, spec={})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker.publish(root/'server-ready.json', dict(case_sha256='offline-case',
                uri='ws://127.0.0.1:12345', identity={'boot_id': 'boot', 'cgroup': '/producer'}))
            with patch.object(worker, 'context', return_value=case), \
                 patch.object(worker, 'LinuxReader', return_value=reader), \
                 patch.object(worker.threading, 'Thread', Thread), \
                 patch.object(worker.time, 'monotonic', return_value=10), \
                 patch.object(worker, 'CompletionWitnesses') as witness, \
                 patch.object(worker, 'collect_with_completion', side_effect=OSError('storage fault')):
                witness.return_value.snapshot.return_value = {'complete': False}
                worker.consume(root, {}, execute=True, resource_observer=lambda *args: {})
            closed = worker.control(root/'capture-closed.json')
            result = worker.control(root/'consumer.json')
            self.assertEqual(closed['case_sha256'], 'offline-case')
            self.assertIsNone(result['summary'])
            self.assertIn('OSError:storage fault', result['error'])
