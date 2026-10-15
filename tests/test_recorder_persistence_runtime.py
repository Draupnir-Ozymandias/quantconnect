"""Successor runtime tests: injected persistence clocks/faults and actual localhost workers."""
from copy import deepcopy
from datetime import timedelta
from execution_truth.acquisition import utc_now, utc_text
import json
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import stream_plan
from infra.stream import recorder_persistence_lane as lane
from infra.stream import recorder_persistence_worker as worker
from infra.stream import recorder_persistence_smoke as smoke
from infra.stream import recorder_persistence_smoke_audit as audit
from infra.stream.recorder_absolute_smoke_audit import archive_frames
from infra.stream.recorder_completion import CompletionWitnesses, verify_completion
from tests.test_market_stream import Clock
from tests.test_taker_replay import raw_bundle, revise
from tests import test_recorder_absolute_smoke as fixtures


def successor_fixture(root):
    old_properties = fixtures.properties
    def properties(*args):
        result = old_properties(*args)
        result['ExecStart'] = result['ExecStart'].replace('infra.stream.recorder_absolute_smoke',
                                                          'infra.stream.recorder_persistence_smoke')
        return result
    with patch.multiple(fixtures, smoke=smoke, audit=audit, worker=worker,
                        collect_with_completion=lane.collect_with_completion, properties=properties):
        f, _ = fixtures.fixture(root)
    p = root/'evidence/case/producer.json'
    fixtures.replace_control(p, lambda v: v.update(terminal_receive=[dict(
        at=87.0005, normal=True, type='ConnectionClosedOK', received_code=1000, sent_code=1000)]))
    return f, reseal(root,f)


def reseal(root,f):
    fixtures.reseal(root, f)
    path=root/'origin-inventory.json';value=json.loads(path.read_text())
    value['schema_version']='qcrl.recorder_persistence_smoke_inventory.v1'
    value.pop('inventory_sha256');value['inventory_sha256']=payload_hash(value)
    path.write_text(json.dumps(value)+'\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DeadlineTests(unittest.TestCase):
    def setup_log(self, root, clock):
        spec=stream_plan(raw_bundle(),segmented=True)
        witness=CompletionWitnesses(spec,'test',clock=clock.utc,monotonic=clock.mono,execute=True)
        witness.validate_spec(spec)
        log=lane.DeadlineStreamLog(root,clock.utc,clock.mono,spec['storage'],completion_observer=witness)
        log.append('session_start',{'spec':spec,'spec_sha256':payload_hash(spec)})
        return log,witness

    def frame(self, log, witness):
        witness.application_return('PONG',1)
        log.append('frame',dict(connection=1,raw_text='PONG',classification=[]))

    def test_explicit_reserve_and_receive_boundary(self):
        self.assertEqual(lane.PERSISTENCE_POLICY['persistence_reserve_seconds'],1)
        self.assertFalse(lane.PERSISTENCE_POLICY['reserve_is_guarantee'])
        with tempfile.TemporaryDirectory() as d:
            clock=Clock();log,witness=self.setup_log(Path(d)/'archive',clock)
            try:
                clock.seconds=.000001;self.frame(log,witness)
                clock.seconds=.999999;self.frame(log,witness)
                timeout=log.receive_timeout(1)
                self.assertAlmostEqual(timeout,.000001)
                clock.pause(timeout)
                with patch('infra.stream.recorder_completion_lane.os.fsync',side_effect=lambda fd:clock.pause(.001)):
                    log.sync_if_due()
                self.assertLess(witness.barriers[-1]['end']-witness.frames[0]['returned']['before'],2)
                self.assertEqual(log.receive_timeout(.25),.25)
            finally:log.close()

    def test_return_age_counts_processing_and_storage_can_still_exceed_reserve(self):
        with tempfile.TemporaryDirectory() as d:
            clock=Clock();log,witness=self.setup_log(Path(d)/'archive',clock)
            try:
                witness.application_return('PONG',1)
                clock.seconds=.8
                log.append('frame',dict(connection=1,raw_text='PONG',classification=[]))
                self.assertAlmostEqual(log.receive_timeout(1),.2)
                clock.seconds=1
                with patch('infra.stream.recorder_completion_lane.os.fsync',side_effect=lambda fd:clock.pause(1.1)):
                    log.receive_timeout(1)
                self.assertGreater(witness.barriers[-1]['end']-witness.frames[0]['returned']['before'],2)
            finally:log.close()

    def test_due_before_receive_and_count_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            clock=Clock();log,witness=self.setup_log(Path(d)/'archive',clock)
            try:
                for _ in range(63):self.frame(log,witness)
                self.assertEqual(len(witness.barriers),1)
                self.frame(log,witness);self.assertEqual(len(witness.barriers),2)
                self.frame(log,witness);clock.seconds=1
                self.assertEqual(log.receive_timeout(.5),.5)
                self.assertEqual(log.pending,0)
            finally:log.close()

    def test_actual_collector_caps_recv_and_preserves_archive(self):
        clock=Clock();timeouts=[]
        class Socket:
            def send(self,value):pass
            def close(self):pass
            def recv(self,timeout):
                timeouts.append(timeout)
                if len(timeouts)==1:clock.pause(.000001);return 'PONG'
                if len(timeouts)==2:clock.seconds=.999999;return 'PONG'
                clock.pause(timeout);raise TimeoutError()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'archive';spec=stream_plan(raw_bundle(),segmented=True,max_seconds=3)
            witness=CompletionWitnesses(spec,'test',clock=clock.utc,monotonic=clock.mono,execute=True)
            lane.collect_with_completion(raw_bundle(),spec,root,connector=Socket,clock=clock.utc,
                monotonic=clock.mono,pause=clock.pause,completion_observer=witness)
            self.assertAlmostEqual(timeouts[2],.000001)
            self.assertEqual(verify_completion(witness.snapshot(root),root,expected_domain='test')['frames'],2)

    def test_each_storage_fault_propagates_without_success_or_retry(self):
        for stage in ('gzip','file','fsync'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as d:
                clock=Clock();log,witness=self.setup_log(Path(d)/'archive',clock)
                self.frame(log,witness);clock.seconds=1;before=len(witness.barriers)
                fault=(patch('infra.stream.recorder_completion_lane.os.fsync',side_effect=OSError('fault')) if stage=='fsync'
                       else patch.object(log.writer if stage=='gzip' else log.raw,'flush',side_effect=OSError('fault')))
                try:
                    with fault as operation:
                        with self.assertRaises(OSError):log.receive_timeout(1)
                        self.assertEqual(operation.call_count,1)
                    self.assertEqual(len(witness.barriers),before)
                    self.assertIsNotNone(witness.failure)
                finally:log.close()


class ClosureTests(unittest.TestCase):
    def test_verified_fixture_and_tampered_closure_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);f,anchor=successor_fixture(root)
            result=audit.audit(root,expected_inventory_file_sha256=anchor,expected_freeze_sha256=f['freeze_sha256'])
            self.assertTrue(result['compatibility_verified'])
            c=root/'evidence/case';case=worker.control(c/'case.json');producer=worker.control(c/'producer.json')
            verified=worker.verify_recorder_completion(c,case)
            for change in ('premature','abnormal','missing','send_prefix','fault','bad_control'):
                p=deepcopy(producer)
                if change=='premature':p['terminal_receive'][0]['at']=86
                if change=='abnormal':p['terminal_receive'][0]['normal']=False
                if change=='missing':p['terminal_receive']=[]
                if change=='send_prefix':p['result']['rows'].pop()
                if change=='fault':p['control_errors']=['OSError']
                if change=='bad_control':p['controls']=[dict(text='NOT_PING')]
                with self.subTest(change=change),self.assertRaises(ContractError):
                    worker.verify_closure(p['result'],p['terminal_receive'],p['controls'],p['control_errors'],verified,case)
            fixtures.replace_control(c/'producer.json',lambda v:v.update(control_errors=['OSError']))
            result=audit.audit(root,expected_inventory_file_sha256=reseal(root,f),expected_freeze_sha256=f['freeze_sha256'])
            self.assertEqual(result['verdict'],'fail')
            self.assertFalse(result['compatibility_verified'])
            self.assertIn('producer_closure_or_recorder_completion',result['failures'])
            self.assertEqual(result['resources']['verdict'],'pass')

    def test_normal_close_cannot_replace_failed_or_unverified_recorder_completion(self):
        for mode in ('missing','failed','unsigned','wrong_case','archive'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=Path(d);successor_fixture(root);c=root/'evidence/case';case=worker.control(c/'case.json')
                if mode=='missing':(c/'completion.json').unlink()
                if mode=='failed':fixtures.replace_control(c/'consumer.json',lambda v:v.update(error='storage failure'))
                if mode=='unsigned':(c/'capture-closed.json').write_text('{}')
                if mode=='wrong_case':fixtures.replace_control(c/'capture-closed.json',lambda v:v.update(case_sha256='wrong'))
                if mode=='archive':(c/'archive/segment-000000.gz').write_bytes(b'corrupt')
                with self.assertRaises((ContractError,KeyError,FileNotFoundError,OSError,ValueError)):
                    worker.verify_recorder_completion(c,case)

    def test_actual_producer_and_consumer_localhost_paths(self):
        # Actual sync WebSockets, handler, drain and completion publication; only
        # Linux resource acquisition and native absolute observation are injected.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);clock=Clock();raw=raw_bundle();now=utc_now()
            revise(raw,'gamma_market',startDate=utc_text(now-timedelta(seconds=60)),
                eventStartTime=utc_text(now-timedelta(seconds=10)),endDate=utc_text(now+timedelta(seconds=290)))
            spec=stream_plan(raw,segmented=True,max_frames=68,max_seconds=8)
            case=dict(artifact_sha256='offline-case',case='steady-0',boot_id='offline',
                      epoch=time.monotonic()+1,raw_bundle=raw,spec=spec)
            def reader(*args,**kwargs):
                return SimpleNamespace(expected=dict(pid=os.getpid(),boot_id='offline',
                    cgroup='/producer' if threading.current_thread().name=='producer' else '/consumer'),read=lambda **kw:{})
            def transmit(conn,kind,epoch):
                time.sleep(max(0,epoch-time.monotonic()));rows=[]
                import hashlib
                for i in range(68):
                    begin=time.monotonic();raw=worker.message(i);conn.send(raw)
                    rows.append(dict(sequence=i,begin=begin,end=time.monotonic(),raw_sha256=hashlib.sha256(raw.encode()).hexdigest()))
                return dict(rows=rows,complete=True,error=None)
            errors=[]
            def produce():
                try:worker.produce(root,{},execute=True,transmitter=transmit)
                except BaseException as exc:errors.append(exc)
            with patch.object(worker,'context',return_value=case),patch.object(worker,'LinuxReader',side_effect=reader):
                thread=threading.Thread(target=produce,name='producer',daemon=True);thread.start()
                try:
                    deadline=time.monotonic()+3
                    while not (root/'server-ready.json').exists() and time.monotonic()<deadline:time.sleep(.01)
                    self.assertEqual(errors,[])
                    # Producer waits for the existing independent binding release.
                    worker.publish(root/'bindings-ready.json',dict(case_sha256='offline-case',at=time.monotonic()))
                    worker.consume(root,{},execute=True,resource_observer=lambda *args:{})
                finally:
                    if not (root/'consumer.json').exists():
                        # Bound fixture failure teardown without waiting 185 s.
                        worker.publish(root/'consumer.json',dict(error='fixture failed'))
                    thread.join(timeout=6)
            self.assertFalse(thread.is_alive());self.assertEqual(errors,[])
            p=worker.control(root/'producer.json');c=worker.control(root/'consumer.json')
            self.assertEqual(p['control_errors'],[],p)
            self.assertEqual(len(p['terminal_receive']),1)
            self.assertIsNone(c['error']);self.assertEqual(c['summary']['frames'],68)
            self.assertEqual(len(archive_frames(root/'archive')[0]),68)


class IdentityTests(unittest.TestCase):
    def test_prospective_policy_and_smoke_hashes_are_pinned(self):
        self.assertEqual(payload_hash(smoke.PLAN),'8aee41893efd0dfd19f0dab1a66f9b96ee460fe55a8b251eb8b3e60a6dd224e1')
        self.assertEqual(payload_hash(lane.PERSISTENCE_POLICY),'5f411e0c585062d8657f504ba7b97cdf5aff789d18a5766dec746bd4dc7bee65')
        self.assertFalse(smoke.PLAN['native_execution_authorized'])
        value=smoke.declaration()
        self.assertEqual(value['plan'],smoke.PLAN)
        self.assertEqual(value['observer_plan']['scope'],'isolated_recorder_resource_observer_only_not_receive_or_producer')
        self.assertEqual(value['plan_sha256'],payload_hash(smoke.PLAN))


class DrainRuntimeFaultTests(unittest.TestCase):
    def produce_fault(self, mode, close_type='ConnectionClosedOK'):
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
            def is_alive(self): return False
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
                else:
                    (root/'capture-closed.json').write_text('{}')
                    (root/'consumer.json').write_text('{}')
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

    def test_actual_drain_preserves_fault_across_stop_race(self):
        for kind in ('OSError','ConnectionClosedError'):
            with self.subTest(kind=kind):
                result,_=self.produce_fault('stop_during_recv',kind)
                self.assertIn(kind,result['control_errors'])
                self.assertEqual(result['terminal_receive'][0]['type'],kind)
                self.assertFalse(result['terminal_receive'][0]['normal'])

    def test_actual_normal_close_without_verified_completion_cannot_pass(self):
        result,_=self.produce_fault('complete')
        self.assertTrue(result['terminal_receive'][0]['normal'])
        self.assertTrue(result['control_errors'])


class PublicationTests(unittest.TestCase):
    def test_control_is_not_visible_until_serialization_finishes_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'consumer.json'
            real=worker.exclusive_json
            def write(p,value):
                self.assertFalse(path.exists())
                real(p,value)
                self.assertFalse(path.exists())
            with patch.object(worker,'exclusive_json',side_effect=write):worker.publish(path,dict(complete=True))
            self.assertTrue(worker.control(path)['complete'])
            before=path.read_bytes()
            with self.assertRaises(FileExistsError):worker.publish(path,dict(complete=False))
            self.assertEqual(path.read_bytes(),before)
            self.assertTrue(path.with_name(path.name+'.pending').exists())

    def test_partial_control_write_is_retained_without_publishing_success(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'consumer.json'
            def fail(p,value):
                p.write_bytes(b'{partial');raise OSError('injected serialization failure')
            with patch.object(worker,'exclusive_json',side_effect=fail):
                with self.assertRaises(OSError):worker.publish(path,dict(complete=True))
            self.assertFalse(path.exists())
            self.assertEqual(path.with_name(path.name+'.pending').read_bytes(),b'{partial')


class SmokeRoutingTests(unittest.TestCase):
    def test_successor_guard_commands_and_finite_fault_cleanup_paths(self):
        with patch.multiple(fixtures,smoke=smoke,worker=worker):
            fixtures.SmokeTests().test_guard_before_any_operation()
            fixtures.SmokeTests().test_fixed_production_commands_and_no_cohort_route()
            lifecycle=fixtures.LifecycleTests()
            lifecycle.test_failed_preflight_never_claims_or_starts()
            lifecycle.test_faults_stop_progress_capture_once_and_cleanup_only_submitted_units()
        ops=object.__new__(smoke.SmokeProduction);ops.root=Path(fixtures.STAGE);ops.specs={}
        with patch.object(smoke,'command',return_value='') as command:
            for role in ('producer','consumer'):ops.start(smoke.spec(fixtures.STAGE,role))
        for call in command.call_args_list:
            self.assertIn('infra.stream.recorder_persistence_smoke',call.args[0])
