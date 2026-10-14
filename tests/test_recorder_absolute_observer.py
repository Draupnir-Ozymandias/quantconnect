from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import threading
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_absolute_wait import AbsoluteWait, NS, target_nanoseconds
from infra.stream import recorder_absolute_observer as integration
from infra.stream.recorder_absolute_budget import PLAN, PARENT, declaration, validate
from infra.stream.recorder_application_budget import declare as parent
from infra.stream import recorder_application_worker as worker
from tests.test_recorder_application_components import sample, OWNER


class Clock:
    def __init__(self, value=0, shift=0, code=0):
        self.value, self.shift, self.code = value, shift, code
        self.calls = []

    def now(self):
        return self.value

    def syscall(self, clock_id, flags, sec, nsec):
        target = sec*NS+nsec
        self.calls.append(target)
        self.value = target+self.shift
        if isinstance(self.code, BaseException):
            raise self.code
        return self.code

    def wait(self):
        return AbsoluteWait(clock_ns=self.now, syscall=self.syscall)


class Reader:
    def __init__(self, clock, fail_at=None, cost=100_000):
        self.clock, self.fail_at, self.cost = clock, fail_at, cost
        self.calls = []
        self.rss_flags = []

    def read(self, *, rss):
        self.calls.append(self.clock.value)
        self.rss_flags.append(rss)
        if len(self.calls) == self.fail_at:
            raise OSError('read fault')
        before = self.clock.value/NS
        value = sample(before, self.clock.value//1_000_000)
        self.clock.value += self.cost
        value['after'] = self.clock.value/NS
        return value


class ObserverTests(unittest.TestCase):
    def run_observer(self, clock=None, reader=None, capacity=62, stop_at=60):
        clock = Clock() if clock is None else clock
        reader = Reader(clock) if reader is None else reader
        stop = SimpleNamespace(is_set=lambda: clock.value >= (30+stop_at)*NS)
        value = integration.observe_absolute(reader, 30., stop, execute=True,
                    wait=clock.wait(), clock_ns=clock.now, capacity=capacity)
        return value, clock, reader

    def test_enclosed_window_and_integer_targets_use_real_adapter_with_fake_syscall(self):
        value, clock, reader = self.run_observer()
        self.assertEqual(len(value['rows']), 61)
        self.assertFalse(value['overflow'])
        self.assertEqual(clock.calls[:2], [30*NS-50_000_000, 30*NS])
        self.assertEqual(clock.calls[-2:], [90*NS-50_000_000, 90*NS])
        self.assertEqual(len(reader.calls), 63)
        self.assertEqual(reader.rss_flags.count(False), 2)
        self.assertEqual(reader.rss_flags.count(True), 61)
        result = integration.audit_resources(value, 30., 60, 90., parent()['budgets'], OWNER)
        self.assertEqual(result['verdict'], 'pass', result)
        self.assertEqual(len(result['windows']), 1)
        self.assertFalse(value['acceptance_demonstrated'])

    def test_already_missed_pre_and_rss_slots_are_not_read_or_reanchored(self):
        value, clock, reader = self.run_observer(Clock(32*NS), capacity=4, stop_at=3)
        self.assertEqual([r['target_ns'] for r in value['rows']], [30*NS,31*NS,32*NS,33*NS])
        self.assertEqual(clock.calls, [33*NS])
        self.assertEqual(len(reader.calls), 1)
        self.assertTrue(all(r['sample'] is None for r in value['rows'][:3]))
        result = integration.audit_resources(value, 30., 3, 33., parent()['budgets'], OWNER)
        self.assertEqual(result['verdict'], 'unknown')

    def test_missed_pre_endpoint_does_not_cancel_future_rss(self):
        value, clock, reader = self.run_observer(Clock(30*NS-25_000_000), capacity=1, stop_at=0)
        self.assertIsNone(value['rows'][0]['cpu_before'])
        self.assertIsNotNone(value['rows'][0]['sample'])
        self.assertEqual(clock.calls, [30*NS])
        self.assertEqual(len(reader.calls), 1)

    def test_late_wake_no_read_continues_original_grid(self):
        value, clock, reader = self.run_observer(Clock(shift=60_000_000), capacity=3, stop_at=2)
        self.assertEqual(reader.calls, [])
        self.assertEqual(clock.calls, [30*NS-50_000_000,31*NS,32*NS])
        self.assertIsNone(value['error'])
        self.assertEqual(value['rows'][0]['waits']['rss']['error'], 'target_already_missed_no_catch_up')
        self.assertIn('late_wake', value['rows'][1]['error'])

    def test_wait_errno_early_return_and_interrupt_stop_without_retry(self):
        for clock in [Clock(code=4), Clock(code=22), Clock(shift=-1), Clock(code=KeyboardInterrupt('x'*300))]:
            with self.subTest(code=clock.code, shift=clock.shift):
                value, clock, reader = self.run_observer(clock)
                self.assertIsNotNone(value['error'])
                self.assertLessEqual(len(value['error']), 160)
                self.assertEqual(len(value['rows']), 1)
                self.assertEqual(len(clock.calls), 1)
                self.assertEqual(reader.calls, [])

    def test_reader_fault_retains_unknown_and_continues_without_retry(self):
        clock = Clock(); reader = Reader(clock, fail_at=1)
        value, clock, reader = self.run_observer(clock, reader, capacity=2, stop_at=1)
        self.assertEqual(len(reader.calls), 3)
        self.assertIn('OSError', value['rows'][0]['cpu_before_error'])
        self.assertIsNotNone(value['rows'][0]['sample'])
        self.assertIsNotNone(value['rows'][1]['sample'])
        self.assertIsNone(value['error'])
        clock = Clock(); reader = Reader(clock)
        with patch.object(reader, 'read', side_effect=KeyboardInterrupt('read interrupted')) as read:
            value, _, _ = self.run_observer(clock, reader)
        self.assertIn('KeyboardInterrupt', value['error'])
        self.assertEqual(len(value['rows']), 1)
        self.assertEqual(len(clock.calls), 1)
        read.assert_called_once()

    def test_fatal_wait_after_success_retains_prefix_and_stops_future_calls(self):
        clock = Clock(); call = clock.syscall
        def syscall(*args):
            if len(clock.calls) == 3:
                clock.code = 4
            return call(*args)
        wait = AbsoluteWait(clock_ns=clock.now, syscall=syscall)
        reader = Reader(clock)
        value = integration.observe_absolute(reader, 30., SimpleNamespace(is_set=lambda: False),
                    execute=True, wait=wait, clock_ns=clock.now, capacity=5)
        self.assertEqual(len(value['rows']), 3)
        self.assertEqual(len(clock.calls), 4)
        self.assertEqual(len(reader.calls), 3)
        self.assertTrue(all(row['sample'] is not None for row in value['rows'][:2]))
        self.assertIsNone(value['rows'][2]['sample'])
        self.assertEqual(value['error'], 'clock_nanosleep_error_4_no_retry')

    def test_rss_read_error_is_unknown_and_next_original_slot_continues(self):
        clock = Clock();reader = Reader(clock, fail_at=3)
        value, _, _ = self.run_observer(clock, reader, capacity=3, stop_at=2)
        self.assertIsNone(value['rows'][1]['sample'])
        self.assertIn('OSError', value['rows'][1]['error'])
        self.assertEqual(value['rows'][2]['target_ns'],32*NS)
        self.assertIsNotNone(value['rows'][2]['sample'])
        self.assertIsNone(value['error'])

    def test_before_read_clock_deadline_or_regression_does_not_read(self):
        for shift in (-1, 60_000_001):
            clock = Clock(); reader = Reader(clock)
            stop = SimpleNamespace(is_set=lambda: True)
            value = integration.observe_absolute(reader, 30., stop, execute=True,
                      wait=clock.wait(), clock_ns=lambda: clock.value+shift, capacity=1)
            self.assertIsNone(value['rows'][0]['cpu_before'])
            if shift < 0:
                self.assertEqual(value['error'], 'observer_clock_regressed')
                self.assertEqual(reader.calls, [])
            else:
                self.assertEqual(value['rows'][0]['cpu_before_error'], 'read_deadline_missed_no_catch_up')

    def test_read_crossing_boundary_remains_unknown_not_repaired(self):
        clock = Clock(); reader = Reader(clock, cost=60_000_000)
        value, _, _ = self.run_observer(clock, reader, capacity=1, stop_at=0)
        self.assertIsNotNone(value['rows'][0]['cpu_before'])
        self.assertIsNone(value['rows'][0]['sample'])
        self.assertGreater(value['rows'][0]['cpu_before']['after'], 30)
        self.assertEqual(value['rows'][0]['waits']['rss']['error'], 'target_already_missed_no_catch_up')

    def test_capacity_overflow_and_guard_before_native_binding(self):
        value, _, _ = self.run_observer(capacity=2, stop_at=10)
        self.assertTrue(value['overflow'])
        with patch.object(integration, 'native') as bind:
            with self.assertRaises(ContractError): integration.observe_absolute(None, 30, None)
            for capacity in (False, 0, 185):
                with self.assertRaises(ContractError):
                    integration.observe_absolute(None, 30, None, execute=True, capacity=capacity)
            with self.assertRaises(ContractError): integration.observe_absolute(None, 0, None, execute=True)
            bind.assert_not_called()

    def test_binding_failure_preserves_unavailable_population(self):
        with patch.object(integration, 'native', side_effect=OSError('ABI')):
            value = integration.observe_absolute(None, 30, None, execute=True)
        self.assertEqual(value['rows'], [])
        self.assertIn('ABI', value['error'])
        self.assertEqual(integration.audit_resources(value, 30., 60, 90., parent()['budgets'], OWNER)['verdict'], 'unknown')

    def test_rehashed_wait_or_shifted_target_and_fabricated_read_rejected(self):
        value, _, _ = self.run_observer()
        for field in ('target', 'wait_target', 'retry', 'return', 'authority', 'read_start', 'reason', 'overflow'):
            bad = deepcopy(value); row = bad['rows'][1]; wait = row['waits']['rss']
            if field == 'target': row['target_ns'] += 1
            if field == 'wait_target': wait['target_ns'] += 1
            if field == 'retry': wait['retries'] = 1
            if field == 'return': wait['lateness_ns'] += 1
            if field == 'authority': wait['native_origin_verified'] = True
            if field == 'read_start': row['sample']['before'] = 0
            if field == 'reason': bad['rows'][0]['cpu_before_error'] = 'unavailable'
            if field == 'overflow': bad['overflow'] = 1
            wait.pop('wait_sha256'); wait['wait_sha256'] = payload_hash(wait)
            with self.subTest(field=field), self.assertRaises(ContractError):
                integration.audit_resources(bad, 30., 60, 90., parent()['budgets'], OWNER)

    def test_known_budget_failure_survives_missing_slot(self):
        value, _, _ = self.run_observer()
        value['rows'][1]['sample']['actors'][0]['rss_bytes'] = 500000000
        value['rows'][1]['sample']['rss_bytes'] = 500000000
        value['rows'][2]['sample'] = None; value['rows'][2]['error'] = 'read fault'
        result = integration.audit_resources(value, 30., 60, 90., parent()['budgets'], OWNER)
        self.assertEqual(result['verdict'], 'fail')
        self.assertTrue(result['unknowns'])


class IntegrationTests(unittest.TestCase):
    def test_real_loopback_recorder_with_injected_absolute_syscalls(self):
        """Functional wiring only: burst transport, fake resource time, no native budget claim."""
        from websockets.sync.server import serve
        from execution_truth.acquisition import utc_now, utc_text
        from execution_truth.market_stream import stream_plan
        from infra.stream.recorder_completion import verify_completion
        from tests.test_taker_replay import raw_bundle, revise
        raw = raw_bundle(); now = utc_now()
        revise(raw, 'gamma_market', startDate=utc_text(now-timedelta(seconds=60)),
               eventStartTime=utc_text(now-timedelta(seconds=10)),
               endDate=utc_text(now+timedelta(seconds=290)))
        spec = stream_plan(raw, segmented=True, max_seconds=5, max_frames=68)
        errors, subscriptions = [], []
        def handler(conn):
            try:
                subscriptions.append(json.loads(conn.recv(timeout=2)))
                for i in range(68): conn.send(worker.message(i))
                try: conn.recv(timeout=2)
                except Exception: pass  # Normal bounded client close.
            except Exception as exc: errors.append(str(exc))
        with TemporaryDirectory() as directory:
            root = Path(directory); closed = threading.Event(); clock = Clock()
            read = Reader(clock); read.expected = deepcopy(OWNER)
            call = clock.syscall
            def syscall(*args):
                if args[2]*NS+args[3] >= 31*NS and not closed.wait(3):
                    raise TimeoutError('functional fixture capture did not close')
                return call(*args)
            wait = AbsoluteWait(clock_ns=clock.now, syscall=syscall)
            case = worker.publish(root/'case.json', dict(case='steady-0',epoch=30.,
                boot_id=OWNER['boot_id'],raw_bundle=raw,spec=spec))
            worker.publish(root/'absolute-wait-plan.json',
                dict(case_sha256=case['artifact_sha256'],declaration=declaration()))
            publish = worker.publish
            def published(path, value):
                result = publish(path, value)
                if path.name == 'capture-closed.json': closed.set()
                return result
            with serve(handler,'127.0.0.1',0,compression=None,ping_interval=None,
                       max_size=262144,max_queue=16,close_timeout=1) as server:
                thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                worker.publish(root/'server-ready.json',dict(case_sha256=case['artifact_sha256'],
                    uri='ws://127.0.0.1:'+str(server.socket.getsockname()[1]),
                    identity=dict(boot_id=OWNER['boot_id'],cgroup='/producer')))
                with patch.object(worker,'context',return_value=case), patch.object(worker,'LinuxReader',return_value=read), patch.object(worker,'publish',side_effect=published):
                    integration.consume_absolute(root,execute=True,wait=wait,clock_ns=clock.now)
                server.shutdown();thread.join(timeout=2)
            consumer = worker.control(root/'consumer.json')
            report = json.loads((root/'completion.json').read_text())
            verified = verify_completion(report,root/'archive',expected_domain='localhost.'+OWNER['boot_id'])
            self.assertEqual(verified['frames'],68)
            self.assertEqual(consumer['summary']['status'],'frame_limit')
            self.assertIsNone(consumer['error'])
            self.assertEqual(consumer['resources']['schema_version'],'qcrl.recorder_absolute_resources.v1')
            self.assertIsNone(consumer['resources']['error'])
            self.assertFalse(consumer['observer_thread_alive'])
            self.assertGreaterEqual(len(clock.calls),2)
            self.assertTrue(all(row['waits'] for row in consumer['resources']['rows']))
            self.assertEqual(subscriptions,[spec['subscription']])
            self.assertEqual(errors,[])
            self.assertFalse(verified['acceptance_demonstrated'])

    def test_case_controls_bind_new_policy_and_callback_before_binding(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); case = worker.publish(root/'case.json', {'case':'steady-0'})
            worker.publish(root/'absolute-wait-plan.json', dict(case_sha256=case['artifact_sha256'], declaration=declaration()))
            with patch.object(worker, 'consume') as consume, patch.object(integration, 'native') as bind:
                integration.consume_absolute(root, execute=True)
                callback = consume.call_args.kwargs['resource_observer']
                clock = Clock(); reader = Reader(clock)
                with patch.object(integration, 'observe_absolute', return_value={'rows':[]}) as observe:
                    callback(reader, 30, None)
                    self.assertIs(observe.call_args.args[0], reader)
                    self.assertTrue(observe.call_args.kwargs['execute'])
                bind.assert_not_called()
            changed = worker.load(root/'absolute-wait-plan.json');changed['case_sha256']='0'*64
            changed.pop('artifact_sha256');changed['artifact_sha256']=payload_hash(changed)
            (root/'absolute-wait-plan.json').write_text(json.dumps(changed))
            with patch.object(worker, 'consume') as consume, self.assertRaises(ContractError):
                integration.consume_absolute(root, execute=True)
            consume.assert_not_called()

    def test_worker_retains_injected_observer_payload_in_consumer(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);case=dict(artifact_sha256='a'*64,boot_id='fixture',epoch=30,
                spec={},raw_bundle={})
            worker.publish(root/'server-ready.json',dict(case_sha256='a'*64,uri='ws://127.0.0.1:1234',
                identity=dict(boot_id='fixture',cgroup='/producer')))
            reader=SimpleNamespace(expected=dict(boot_id='fixture',cgroup='/recorder'),read=lambda **k: {})
            resources=dict(schema_version='injected-absolute',rows=[{'error':'missed'}],overflow=False)
            observed=[]
            def observe(reader,epoch,stop):observed.append(epoch);return resources
            with patch.object(worker,'context',return_value=case), patch.object(worker,'LinuxReader',return_value=reader), patch.object(worker,'CompletionWitnesses') as witness, patch.object(worker,'collect_with_completion',return_value={'stopped':'frame_limit'}):
                witness.return_value.snapshot.return_value={}
                worker.consume(root,{},execute=True,resource_observer=observe)
            self.assertEqual(observed,[30])
            self.assertEqual(worker.control(root/'consumer.json')['resources'],resources)

    def test_prepare_is_exclusive_and_guarded(self):
        with patch.object(worker,'prepare') as prepare:
            with self.assertRaises(ContractError):integration.prepare_absolute('/absent','steady-0')
            with self.assertRaises(ContractError):integration.consume_absolute('/absent')
            prepare.assert_not_called()
        with TemporaryDirectory() as directory:
            root=Path(directory);worker.publish(root/'case.json',{'case':'steady-0'})
            with patch.object(worker,'prepare',return_value=root):
                integration.prepare_absolute(root,'steady-0',execute=True)
                with self.assertRaises(FileExistsError):integration.prepare_absolute(root,'steady-0',execute=True)


class DeclarationTests(unittest.TestCase):
    def test_parent_unchanged_and_successor_sources_bound(self):
        value=declaration();self.assertEqual(parent()['plan_sha256'],PARENT)
        self.assertEqual(value['budgets'],parent()['budgets'])
        self.assertEqual(value['case_order'],parent()['policy']['case_order'])
        self.assertEqual(value['corpus_sha256'],parent()['corpus_sha256'])
        self.assertEqual(validate(value),value)
        value['plan']['cpu_lead_ns']=2_000_000
        value.pop('declaration_sha256');value['declaration_sha256']=payload_hash(value)
        with self.assertRaises(ContractError):validate(value)

    def test_literal_policy_hash(self):
        self.assertEqual(payload_hash(PLAN),'bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f')

    def test_shared_epoch_ceiling_never_repeated_float_offsets(self):
        epoch=30.0000000004;clock=Clock();reader=Reader(clock)
        stop=SimpleNamespace(is_set=lambda:clock.value>=31*NS)
        value=integration.observe_absolute(reader,epoch,stop,execute=True,
            wait=clock.wait(),clock_ns=clock.now,capacity=2)
        self.assertEqual(value['epoch_ns'],target_nanoseconds(epoch))
        self.assertEqual(value['epoch_ns'],30*NS+1)
        self.assertEqual(value['rows'][1]['target_ns']-value['rows'][0]['target_ns'],NS)
