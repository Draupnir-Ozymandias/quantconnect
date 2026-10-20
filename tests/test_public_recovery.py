"""Offline prospective recovery through actual recorder/witness/archive paths."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.frames import Close
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import stream_plan
from infra.stream import recorder_public_capture as capture
from infra.stream import recorder_public_recovery as recovery
from infra.stream.recorder_completion import CompletionWitnesses, verify_completion
from tests.test_market_stream import Clock, book
from tests.test_recorder_public_study import DummyInterrupt
from tests.test_taker_replay import raw_bundle


def closed(ok=False):
    return (ConnectionClosedOK(Close(1000,''),Close(1000,''),True) if ok
            else ConnectionClosedError(None,None,None))


class Harness:
    def __init__(self, root, scripts=None):
        self.root=root;self.clock=Clock();self.raw=raw_bundle()
        self.spec=stream_plan(self.raw,segmented=True,max_seconds=90,max_frames=60000,resilient=True)
        self.witness=CompletionWitnesses(self.spec,'test.recovery',clock=self.clock.utc,monotonic=self.clock.mono,execute=True)
        self.scripts=scripts or [{}];self.connections=[];self.calls=0;self.guards=[]

    def event(self, asset=None, kind='book', age=0, **updates):
        value=book(self.spec,asset or self.spec['asset_ids'][0]);value['event_type']=kind
        value['timestamp']=str(int((self.clock.utc().timestamp()-age)*1000));value.update(updates)
        return json.dumps(value)

    def connect(self,*args,**kwargs):
        assert all(c.closed for c in self.connections),'sockets overlapped'
        self.calls+=1;script=self.scripts[min(self.calls-1,len(self.scripts)-1)]
        if 'connect_error' in script:raise script['connect_error']
        harness=self
        class Conn:
            state=capture.State.OPEN;socket=None
            def __init__(self):
                self.closed=False;self.sent=[];self.n=0;self.pong=False
            def send(self,value):
                self.sent.append(value)
                if 'send_error' in script:raise script['send_error']
                if value=='PING':
                    if 'ping_error' in script:raise script['ping_error']
                    self.pong=True
            def recv(self,timeout):
                self.n+=1
                if 'recv' in script:return script['recv'](self,timeout,harness)
                if self.n<=2:
                    harness.clock.pause(.01)
                    return harness.event(harness.spec['asset_ids'][self.n-1])
                harness.clock.pause(timeout)
                if self.pong:self.pong=False;return 'PONG'
                return harness.event(kind='price_change',price_changes=[{'asset_id':harness.spec['asset_ids'][0]}])
            def close(self):
                self.closed=True
                if 'close_error' in script:raise script['close_error']
        conn=Conn();self.connections.append(conn);return conn

    def run(self,**options):
        def guard(*a,**kw):
            value=DummyInterrupt(*a,**kw);self.guards.append(value);return value
        args=dict(epoch_ns=20_000_000_000,observer=self.witness,execute=True,clock=self.clock.utc,
            monotonic=self.clock.mono,connect_factory=self.connect,guard=SimpleNamespace(check=lambda:None),
            interrupt_factory=guard,connect_guard_factory=guard,recovery_policy=recovery.policy(),
            pause=self.clock.pause,uniform=lambda a,b:a)
        args.update(options)
        self.result=capture.collect(self.raw,self.spec,self.root,**args)
        self.completion=self.witness.snapshot(self.root)
        return self.result

    def report(self):
        return recovery.describe_archive(self.result,self.completion,self.root,expected_domain='test.recovery')


class RecoveryTests(unittest.TestCase):
    def test_policy_identity_and_old_plan_still_single_attempt(self):
        from infra.stream.recorder_public_counts import PLAN
        self.assertEqual(payload_hash(recovery.POLICY),'437621e12790da88843eb418b649af6a00972566b21a86d94e11a43b266c6f04')
        self.assertEqual((PLAN['connection_attempts'],PLAN['reconnects']),(1,0))
        changed=recovery.policy();changed['max_connections']=4
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'archive')
            with self.assertRaisesRegex(ContractError,'policy drift'):h.run(recovery_policy=changed)

    def test_normal_local_acquisition_and_book_bootstrap_boundaries(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'archive');r=h.run();v=h.report()
            self.assertIsNone(r['error']);self.assertEqual(h.calls,1)
            self.assertTrue(v['normal_acquisition_end_proven'])
            self.assertTrue(r['connection_epochs'][0]['normal'])
            self.assertEqual(r['summary']['connections'],1)
            self.assertEqual(r['connection_epochs'][0]['eligible_after'],.02)
            self.assertEqual(h.clock.seconds,85)
            self.assertGreater(v['eligible_population'],0)
            self.assertTrue(all(x['feed_activity_upper'] is None for x in v['rows']))
            self.assertFalse(v['missed_messages_recovered'])
            self.assertIsNone(v['study_plan_sha256'])
            self.assertNotIn('plan_sha256',v)
            self.assertEqual(json.loads(h.connections[0].sent[0]),h.spec['subscription'])

    def test_reconnect_preserves_fault_duplicates_and_resets_books(self):
        def first(c,t,h):
            h.clock.pause(.1)
            if c.n<=2:return h.event(h.spec['asset_ids'][c.n-1])
            if c.n==3:return 'duplicate'
            h.clock.pause(20)
            raise closed()
        def second(c,t,h):
            h.clock.pause(.1 if c.n<=4 else t)
            if c.n==1:return 'duplicate'
            if c.n==2:return h.event(kind='price_change')
            if c.n in (3,4):return h.event(h.spec['asset_ids'][c.n-3])
            if c.pong:c.pong=False;return 'PONG'
            return h.event(kind='price_change')
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'archive',[dict(recv=first),dict(recv=second)]);r=h.run();v=h.report()
            self.assertEqual(h.calls,2);self.assertTrue(all(c.closed for c in h.connections))
            self.assertIn('ConnectionClosedError',r['error'])
            self.assertEqual(r['summary']['status'],'scheduled_stop')
            self.assertFalse(capture.normal_completion_proven(r))
            self.assertEqual(len(r['terminal_receive']),1)
            self.assertGreater(r['connection_epochs'][1]['eligible_after'],r['connection_epochs'][1]['subscribed'])
            self.assertEqual(len(r['connection_epochs'][1]['books']),2)
            self.assertEqual(v['population'],len(h.completion['frames']))
            self.assertLess(v['eligible_population'],v['population'])
            self.assertTrue(any(x['acquisition']=='unavailable_or_boundary' for x in v['rows'][:1]))
            for c in h.connections:self.assertEqual(json.loads(c.sent[0]),h.spec['subscription'])

    def test_peer_ok_close_is_retained_fault_not_normal_success(self):
        with TemporaryDirectory() as d:
            def fail(c,t,h):h.clock.pause(.1);raise closed(True)
            h=Harness(Path(d)/'a',[dict(recv=fail),{}]);r=h.run();h.report()
            self.assertIn('ConnectionClosedOK',r['error']);self.assertEqual(h.calls,2)
            self.assertFalse(capture.normal_completion_proven(r))

    def test_connect_failures_exhaust_exactly_three_attempts_with_zero_not_coverage(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(connect_error=OSError('connect refused'))]);r=h.run();v=h.report()
            self.assertEqual(h.calls,3);self.assertEqual(r['summary']['status'],'connection_limit')
            self.assertEqual(h.clock.seconds,3)
            self.assertTrue(all(x['silence']=='unknown' for x in v['rows']))
            self.assertEqual(v['eligible_population'],0)

    def test_subscription_and_ping_write_failures_are_bounded(self):
        for key in ('send_error','ping_error'):
            with self.subTest(key=key),TemporaryDirectory() as d:
                h=Harness(Path(d)/'a',[{key:OSError('write failed')},{}]);r=h.run();h.report()
                self.assertEqual(h.calls,2);self.assertIn('write failed',r['error'])
                self.assertTrue(all(c.closed for c in h.connections))

    def test_pong_only_partial_books_stale_future_malformed_and_updates_do_not_bootstrap(self):
        for mode in ('pong','partial','stale','future','malformed','missing_timestamp','updates'):
            def receive(c,t,h):
                h.clock.pause(t)
                if mode=='pong':return 'PONG'
                if mode=='partial':return h.event()
                if mode=='stale':return h.event(h.spec['asset_ids'][c.n%2],age=6)
                if mode=='future':return h.event(h.spec['asset_ids'][c.n%2],age=-10)
                if mode=='missing_timestamp':return h.event(h.spec['asset_ids'][c.n%2],timestamp=None)
                if mode=='malformed':return h.event(h.spec['asset_ids'][c.n%2],bids=[{'price':'NaN','size':'1'}])
                return h.event(kind='price_change')
            with self.subTest(mode=mode),TemporaryDirectory() as d:
                h=Harness(Path(d)/'a',[dict(recv=receive)]);r=h.run();v=h.report()
                self.assertEqual(h.calls,3)
                self.assertTrue(all(e['eligible_after'] is None for e in r['connection_epochs']))
                self.assertTrue(all('initial_books_timeout' in e['error'] for e in r['connection_epochs']))
                self.assertEqual(v['eligible_population'],0)

    def test_corrupt_linkage_and_clock_cannot_be_repaired_by_recovery(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a');h.run()
            original=deepcopy(h.result)
            h.result['connection_epochs'][0]['eligible_after']=0
            with self.assertRaisesRegex(ContractError,'lifecycle differs'):h.report()
            h.result=original;h.completion['frames'][0]['connection']=2
            with self.assertRaises(ContractError):h.report()

    def test_foreign_binding_quota_and_clock_faults_never_retry(self):
        for mode in ('foreign','quota','clock'):
            with self.subTest(mode=mode),TemporaryDirectory() as d:
                h=Harness(Path(d)/'a')
                if mode=='foreign':h.scripts=[dict(recv=lambda c,t,h:h.event(asset_id='foreign'))]
                elif mode=='clock':
                    original=h.witness.application_return
                    def fail(*args):original(*args);h.witness.disable('clock fault')
                    h.witness.application_return=fail
                else:
                    original=capture.StudyLog.append
                    def quota(log,kind,payload):
                        if kind=='frame':raise OSError('disk full')
                        return original(log,kind,payload)
                with patch.object(capture.StudyLog,'append',quota if mode=='quota' else capture.StudyLog.append):r=h.run()
                self.assertEqual(h.calls,1);self.assertIsNotNone(r['error'])

    def test_failed_retry_close_is_fatal_and_previous_receive_fault_survives(self):
        with TemporaryDirectory() as d:
            def fail(c,t,h):raise closed()
            h=Harness(Path(d)/'a',[dict(recv=fail,close_error=OSError('close failed')),{}]);r=h.run()
            self.assertEqual(h.calls,1)
            self.assertTrue(any('ConnectionClosedError' in x['error'] for x in r['terminal_receive']))
            self.assertTrue(r['close_errors'])

    def test_emergency_subscription_or_receive_never_retry(self):
        for phase in ('subscription','acquisition'):
            with self.subTest(phase=phase),TemporaryDirectory() as d:
                h=Harness(Path(d)/'a')
                def alarm(*args,**kw):
                    value=DummyInterrupt(*args,**kw)
                    if kw.get('phase')==phase:value.fired.set()
                    return value
                r=h.run(interrupt_factory=alarm)
                self.assertEqual(h.calls,1);self.assertIsNotNone(r['error'])
                self.assertFalse(capture.normal_completion_proven(r))


    def test_silence_is_observed_only_inside_available_interval_not_after_fault(self):
        def receive(c,t,h):
            h.clock.pause(t)
            if c.n==1:return h.event(h.spec['asset_ids'][0])
            if c.n==2:return h.event(h.spec['asset_ids'][1])
            if c.n in (23,26):return h.event(kind='price_change')
            if c.n==27:raise closed()
            if c.pong:c.pong=False;return 'PONG'
            raise TimeoutError('idle')
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=receive),dict(connect_error=OSError('no connection'))]);r=h.run();v=h.report()
            self.assertTrue(any(x['silence']=='observed_zero_archived_texts' for x in v['rows']))
            self.assertEqual(v['rows'][59]['silence'],'unknown')
            self.assertEqual(v['rows'][59]['acquisition'],'unavailable_or_boundary')
            self.assertEqual(v['unavailable_intervals'][-1]['end'],r['acquisition_deadline'])

    def test_backoff_and_reconnect_do_not_extend_common_deadline_or_guard(self):
        def receive(c,t,h):
            h.clock.seconds=84.5
            raise closed()
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=receive),{}]);r=h.run();h.report()
            self.assertEqual(h.calls,1);self.assertEqual(h.clock.seconds,85)
            self.assertEqual(r['acquisition_deadline'],85)
            self.assertEqual(h.guards[0].deadline,90)

    def test_transport_fault_racing_emergency_cannot_retry_or_clear_fired_state(self):
        def receive(c,t,h):
            alarms[-1].fired.set();raise closed()
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=receive),{}]);alarms=[]
            def alarm(*args,**kw):
                value=DummyInterrupt(*args,**kw);alarms.append(value);return value
            r=h.run(interrupt_factory=alarm)
            self.assertEqual(h.calls,1);self.assertIn('ConnectionClosedError',r['error'])
            self.assertTrue(r['deadline_interrupts'][-1]['fired'])

    def test_real_loopback_resubscription_archive_and_connection_closed_faults(self):
        from websockets.sync.server import serve
        from websockets.sync.client import connect
        from execution_truth.acquisition import utc_now
        import threading,time
        raw=raw_bundle();spec=stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000,resilient=True)
        subscriptions=[]
        def handler(conn):
            subscriptions.append(json.loads(conn.recv(timeout=2)))
            stamp=str(int(utc_now().timestamp()*1000))
            for asset in spec['asset_ids']:
                value=book(spec,asset);value['timestamp']=stamp;conn.send(json.dumps(value))
            conn.send('retained duplicate');conn.close()
        with TemporaryDirectory() as d,serve(handler,'127.0.0.1',0,compression=None,ping_interval=None) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            root=Path(d)/'a';witness=CompletionWitnesses(spec,'loopback.recovery',clock=utc_now,monotonic=time.monotonic,execute=True)
            uri='ws://127.0.0.1:'+str(server.socket.getsockname()[1])
            try:
                with patch.object(capture,'ENDPOINT',uri):
                    r=capture.collect(raw,spec,root,epoch_ns=int((time.monotonic()+20)*1e9),observer=witness,
                        execute=True,connect_factory=connect,guard=SimpleNamespace(check=lambda:None),
                        recovery_policy=recovery.policy(),uniform=lambda a,b:a)
                completion=witness.snapshot(root)
                v=recovery.describe_archive(r,completion,root,expected_domain='loopback.recovery')
            finally:server.shutdown();thread.join(3)
            self.assertEqual(len(subscriptions),3)
            self.assertTrue(all(x==spec['subscription'] for x in subscriptions))
            self.assertEqual(v['population'],9)
            self.assertEqual(r['summary']['status'],'connection_limit')
            self.assertTrue(all(e['eligible_after'] is not None for e in r['connection_epochs']))
            self.assertTrue(all('ConnectionClosedOK' in e['error'] for e in r['connection_epochs']))
            self.assertFalse(capture.normal_completion_proven(r))


    def test_clock_failure_and_invalid_tls_are_fatal_not_retry_candidates(self):
        import ssl
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(connect_error=ssl.SSLCertVerificationError('invalid CA'))]);r=h.run()
            self.assertEqual(h.calls,1);self.assertIn('SSLCertVerificationError',r['error'])
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a');original=h.witness.application_return
            def invalidate(*args):
                with patch.object(h.witness,'clock',return_value=None):original(*args)
            h.witness.application_return=invalidate;r=h.run()
            self.assertEqual(h.calls,1);self.assertIsNotNone(h.witness.failure)
            with self.assertRaises(ContractError):h.report()

    def test_silence_watchdog_reuses_existing_control_and_books_do_not_carry(self):
        def receive(c,t,h):
            h.clock.pause(t)
            if c.n<=2:return h.event(h.spec['asset_ids'][c.n-1])
            return 'PONG'
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=receive),dict(recv=lambda c,t,h:(h.clock.pause(t) or 'PONG'))]);r=h.run();v=h.report()
            self.assertIn('selected_book_data_silence',r['connection_epochs'][0]['error'])
            self.assertIsNotNone(r['connection_epochs'][0]['eligible_after'])
            self.assertTrue(all(e['eligible_after'] is None for e in r['connection_epochs'][1:]))
            self.assertFalse(v['normal_acquisition_end_proven'])

    def test_normal_deadline_and_peer_close_simultaneous_does_not_reconnect(self):
        def receive(c,t,h):h.clock.seconds=85;raise closed(True)
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=receive),{}]);r=h.run();v=h.report()
            self.assertEqual(h.calls,1);self.assertFalse(v['normal_acquisition_end_proven'])
            self.assertIn('ConnectionClosedOK',r['error'])

    def test_cancel_race_preserves_fired_state_after_normal_socket_is_closed(self):
        # Exact retry ownership must inspect the post-cancel receipt, not just the exception type.
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=lambda *a:(_ for _ in ()).throw(closed())),{}])
            class Race(DummyInterrupt):
                def cancel(self):
                    if self.phase=='acquisition':self.fired.set();self.owner='emergency'
                    super().cancel()
            r=h.run(interrupt_factory=Race)
            self.assertEqual(h.calls,1);self.assertTrue(r['deadline_interrupts'][-1]['fired'])

    def test_backoff_storage_fault_is_fatal_without_opening_another_socket(self):
        def receive(*args):state['backoff']=True;raise closed()
        state={'backoff':False}
        def check():
            if state['backoff']:raise OSError('reserve unavailable')
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=receive),{}])
            # First lifecycle/gap writes also check storage: fail immediately, never retry storage.
            r=h.run(guard=SimpleNamespace(check=check))
            self.assertEqual(h.calls,1);self.assertIn('reserve unavailable',r['error'])


    def test_actual_blocked_io_emergency_stops_without_reconnecting(self):
        import socket,threading
        from tests.test_recorder_public_study import ManualTimer
        for phase in ('subscription','acquisition'):
            with self.subTest(phase=phase),TemporaryDirectory() as d:
                left,right=socket.socketpair();entered=threading.Event();armed=threading.Event();alarms=[];calls=[]
                h=Harness(Path(d)/'a')
                class Conn:
                    state=capture.State.OPEN;socket=left
                    def send(self,value):
                        if phase=='subscription':self.block()
                    def recv(self,timeout):return self.block()
                    def block(self):
                        entered.set();left.recv(1);raise OSError('interrupted blocked IO')
                    def close(self):left.close()
                def connect(*args,**kw):calls.append(1);return Conn()
                def alarm(*args,**kw):
                    value=capture.DeadlineInterrupt(*args,**kw,timer_factory=ManualTimer)
                    if kw.get('phase')==phase:alarms.append(value);armed.set()
                    return value
                def interrupt():
                    if armed.wait(2) and entered.wait(2):alarms[0].interrupt()
                thread=threading.Thread(target=interrupt,daemon=True);thread.start()
                try:
                    r=h.run(connect_factory=connect,interrupt_factory=alarm)
                    thread.join(3)
                    self.assertFalse(thread.is_alive());self.assertEqual(len(calls),1)
                    self.assertTrue(any(x['fired'] for x in r['deadline_interrupts']))
                    self.assertIn('interrupted blocked IO',r['error'])
                    self.assertFalse(capture.normal_completion_proven(r))
                finally:left.close();right.close()

    def test_eligible_interval_edges_and_gap_bins_do_not_filter_raw_population(self):
        def row(i,start,sub,eligible,end):
            return dict(connection=i,attempted=start,subscribed=sub,eligible_after=eligible,
                ended=end,available_until=end,error='retained fault',normal=False)
        frames=[dict(sequence=i,connection=c,returned=dict(before=a,after=b)) for i,(c,a,b) in enumerate(
            [(1,1,1),(1,1.1,1.2),(1,2.8,3.1),(1,4.9,5),(2,7,7),(2,7.1,7.2)])]
        result=dict(recovery_policy_sha256=payload_hash(recovery.POLICY),connection_epochs=[
            row(1,0,0,1,5),row(2,6,6,7,10)],epoch_ns=2_000_000_000,attempted=0,
            acquisition_deadline=67,summary=dict(frames=len(frames)),deadline_interrupts=[],
            close_completed=True,terminal_receive=[dict(error='retained fault')])
        value=recovery.describe(result,dict(frames=frames))
        self.assertEqual(value['population'],6);self.assertEqual(value['eligible_population'],3)
        self.assertEqual(value['rows'][3]['acquisition'],'unavailable_or_boundary')
        self.assertEqual(value['rows'][3]['silence'],'unknown')
        self.assertEqual(value['ambiguous'][0]['sequence'],2)
        self.assertEqual(value['rows'][0]['eligible_upper_archived'],1)
        self.assertEqual(value['rows'][1]['eligible_upper_archived'],1)
        self.assertTrue(all(r['feed_activity_upper'] is None for r in value['rows']))
