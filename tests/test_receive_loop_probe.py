import inspect
from types import SimpleNamespace
import threading
import time
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, verify_artifact_hash
from infra.stream import receive_loop_probe as probe
from infra.stream.receive_loop_contract import declare, runtime_receipt
from tests.test_receive_adapter import AVAILABLE, local_server


class NativeSocket:
    def __init__(self, result=b'raw', error=None):
        self.result,self.error,self.calls = result,error,[]
    def recv(self,*args,**kwargs):
        self.calls.append(('recv',args,kwargs))
        if self.error: raise self.error
        return self.result
    def settimeout(self,*args): self.calls.append(('settimeout',args)); return 'timeout-set'
    def shutdown(self,*args): self.calls.append(('shutdown',args))
    def close(self): self.calls.append(('close',))


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class ReceiveLoopProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract=declare('a'*64,runtime_receipt())
    def observer(self,**kwargs): return probe.ObservationBuffer(self.contract,**kwargs)
    def ready_read(self,observer):
        row=observer.gate_begin(); observer.gate_end(row,'acquired'); return row

    def test_recv_success_and_forwarded_socket_methods(self):
        observer=self.observer(); self.ready_read(observer)
        native=NativeSocket(); wrapped=probe.SocketProxy(native,observer)
        self.assertIs(wrapped.recv(65536,0),native.result)
        self.assertEqual(native.calls,[('recv',(65536,0),{})])
        self.assertEqual(wrapped.settimeout(.5),'timeout-set')
        wrapped.shutdown(2); wrapped.close()
        self.assertEqual(observer.reads[0]['bytes_returned'],3)

    def test_recv_eof_timeout_and_error_exactly_once(self):
        for error in (None,TimeoutError('native timeout'),OSError('native error')):
            observer=self.observer(); self.ready_read(observer)
            native=NativeSocket(b'',error); wrapped=probe.SocketProxy(native,observer)
            if error:
                with self.assertRaises(type(error)) as caught: wrapped.recv(17)
                self.assertIs(caught.exception,error)
            else: self.assertEqual(wrapped.recv(17),b'')
            self.assertEqual(len(native.calls),1)
            self.assertEqual(observer.reads[0]['socket_outcome'],'error' if error else 'eof')

    def test_observer_begin_failure_does_not_skip_recv(self):
        observer=self.observer(); self.ready_read(observer)
        with patch.object(observer,'_stamp',side_effect=RuntimeError('observer failure')):
            native=NativeSocket(); self.assertEqual(probe.SocketProxy(native,observer).recv(4),b'raw')
        self.assertEqual(len(native.calls),1)
        self.assertEqual(observer.disabled_reason,'observer_error')

    def test_observer_end_failure_does_not_replace_native_error(self):
        observer=self.observer(); self.ready_read(observer)
        values=iter([1,RuntimeError('end failure')])
        def clock():
            v=next(values)
            if isinstance(v,Exception): raise v
            return v
        observer.clock=clock
        error=TimeoutError('native'); native=NativeSocket(error=error)
        with self.assertRaises(TimeoutError) as caught: probe.SocketProxy(native,observer).recv(3)
        self.assertIs(caught.exception,error)
        self.assertEqual(len(native.calls),1)
        self.assertEqual(observer.disabled_reason,'observer_error')

    def test_gate_arguments_return_and_exception_preserved(self):
        observer=self.observer(); native=threading.Lock(); wrapper=probe.GateProxy(native,observer)
        self.assertTrue(wrapper.acquire(blocking=False))
        self.assertFalse(wrapper.acquire(blocking=False))
        wrapper.release()
        with wrapper as result: self.assertTrue(result)
        self.assertFalse(native.locked())
        with self.assertRaises(RuntimeError): wrapper.release()

    def test_gate_native_exception_and_observer_failure(self):
        error=RuntimeError('native gate')
        calls=[]
        def fail(*args,**kwargs): calls.append((args,kwargs)); raise error
        observer=self.observer()
        with patch.object(observer,'_stamp',side_effect=RuntimeError('observer')):
            with self.assertRaises(RuntimeError) as caught:
                probe.GateProxy(SimpleNamespace(acquire=fail),observer).acquire(False)
        self.assertIs(caught.exception,error); self.assertEqual(calls,[((False,),{})])

    def test_no_telemetry_lock_held_across_native_operations(self):
        observer=self.observer(); self.ready_read(observer)
        def native_recv(*args):
            self.assertTrue(observer.lock.acquire(blocking=False)); observer.lock.release(); return b'x'
        self.assertEqual(probe.SocketProxy(SimpleNamespace(recv=native_recv),observer).recv(1),b'x')
        def native_acquire(*args):
            self.assertTrue(observer.lock.acquire(blocking=False)); observer.lock.release(); return True
        self.assertTrue(probe.GateProxy(SimpleNamespace(acquire=native_acquire),observer).acquire())

    def test_pause_drain_and_close_under_existing_assembler_mutex(self):
        from websockets.sync.messages import Assembler
        from websockets.frames import Frame, OP_TEXT
        observer=self.observer(); native=threading.Lock()
        assembler=Assembler(16,4,pause=native.acquire,resume=native.release)
        conn=SimpleNamespace(socket=NativeSocket(),recv_messages=assembler,
                             recv_flow_control=native,recv_bufsize=65536)
        probe.install(conn,observer)
        for i in range(20): assembler.put(Frame(OP_TEXT,b'x'))
        self.assertTrue(native.locked())
        for i in range(16): self.assertEqual(assembler.get(timeout=1),'x')
        self.assertFalse(native.locked())
        for i in range(20): assembler.put(Frame(OP_TEXT,b'x'))
        self.assertTrue(native.locked()); assembler.close(); self.assertFalse(native.locked())
        self.assertEqual([e['kind'] for e in observer.flows],['pause','resume','pause','resume'])
        self.assertFalse(observer.flows[1]['assembler_closed'])
        self.assertEqual(observer.flows[1]['queue_depth'],4)
        self.assertTrue(observer.flows[-1]['assembler_closed'])

    def test_flow_callback_native_return_error_and_observer_failure(self):
        import queue
        assembler=SimpleNamespace(closed=False,paused=True,frames=queue.SimpleQueue())
        sentinel=object(); calls=[]; observer=self.observer()
        def native(*args,**kwargs): calls.append((args,kwargs)); return sentinel
        with patch.object(observer,'_stamp',side_effect=RuntimeError('observer')):
            result=probe.flow_callback(native,'pause',assembler,observer)(7,key=8)
        self.assertIs(result,sentinel); self.assertEqual(calls,[((7,),{'key':8})])
        error=OSError('native'); observer=self.observer()
        def fail(): calls.append('fail'); raise error
        with self.assertRaises(OSError) as caught: probe.flow_callback(fail,'resume',assembler,observer)()
        self.assertIs(caught.exception,error)
        self.assertEqual(observer.flows[0]['outcome'],'error')

    def test_read_and_flow_budget_disable_only_observation(self):
        import queue
        observer=self.observer(); observer.limits['max_read_summaries']=0
        native=threading.Lock(); gate=probe.GateProxy(native,observer)
        with gate: self.assertTrue(native.locked())
        self.assertFalse(native.locked()); self.assertEqual(observer.disabled_reason,'read_summary_budget')
        observer=self.observer(); observer.limits['max_flow_edges']=0; calls=[]
        assembler=SimpleNamespace(closed=False,paused=True,frames=queue.SimpleQueue())
        probe.flow_callback(lambda:calls.append('native'),'pause',assembler,observer)()
        self.assertEqual(calls,['native']); self.assertEqual(observer.disabled_reason,'flow_edge_budget')

    def test_snapshot_budget_and_incomplete_prefix_do_not_claim_success(self):
        observer=self.observer(); observer.installed=True; self.ready_read(observer)
        with self.assertRaises(ContractError): observer.snapshot()
        observer.loop_finished()
        self.assertFalse(observer.snapshot()['complete_observation'])
        observer.limits['max_encoded_sideband_bytes']=1
        with self.assertRaises(ContractError): observer.snapshot()
        self.assertEqual(observer.disabled_reason,'encoded_sideband_budget')
        self.assertEqual(len(observer.reads),1)

    def test_clock_regression_disables_observer_not_transport(self):
        observer=self.observer(clock=iter([2,1]).__next__)
        native=threading.Lock(); wrapper=probe.GateProxy(native,observer)
        self.assertTrue(wrapper.acquire()); wrapper.release()
        self.assertEqual(observer.disabled_reason,'observer_error')

    def test_unsupported_installation_keeps_native_objects(self):
        observer=self.observer(); native=NativeSocket(); gate=threading.Lock()
        conn=SimpleNamespace(socket=native,recv_flow_control=gate,
            recv_messages=SimpleNamespace(high=32,low=8,closed=False),recv_bufsize=65536)
        probe.install(conn,observer)
        self.assertIs(conn.socket,native); self.assertIs(conn.recv_flow_control,gate)
        self.assertFalse(observer.installed); self.assertEqual(observer.disabled_reason,'installation_error')

    def test_numeric_guard_rejects_public_dns_and_credentials_before_connect(self):
        observer=self.observer()
        for uri in ('wss://ws-subscriptions-clob.polymarket.com/ws/market','ws://localhost:9',
                    'ws://example.com:9','ws://user:pass@127.0.0.1:9','ws://127.0.0.1:9?q=x'):
            with self.assertRaises(ContractError): probe.connect_loopback(uri,observer)
        self.assertFalse(observer.claimed)

    def test_real_loopback_raw_fragments_duplicates_control_timeout_and_shutdown(self):
        done=threading.Event(); ready=threading.Event()
        def handler(conn):
            conn.send([b'\xe2',b'\x82\xac'],text=True)
            conn.send('€'); conn.send(b'binary')
            conn.ping(b'control').wait(2)
            ready.set(); self.assertEqual(conn.recv(timeout=3),'done'); done.set()
        observer=self.observer()
        with local_server(handler) as uri:
            client=probe.connect_loopback(uri,observer)
            try:
                self.assertEqual([client.recv(timeout=3) for _ in range(3)],['€','€',b'binary'])
                self.assertTrue(ready.wait(2))
                with self.assertRaises(TimeoutError): client.recv(timeout=.01)
                client.send('done'); self.assertTrue(done.wait(2))
            finally: client.close(); client.recv_events_thread.join(3)
            self.assertFalse(client.recv_events_thread.is_alive())
        result=observer.snapshot(); verify_artifact_hash(result,'sideband_sha256','probe')
        self.assertTrue(result['complete_observation'])
        self.assertGreaterEqual(sum(r['frame_callbacks'] for r in result['reads']),5)
        self.assertGreaterEqual(sum(r['nonframe_callbacks'] for r in result['reads']),1)
        self.assertEqual(result['reads'][0]['iteration'],1)
        with self.assertRaises(ContractError): probe.connect_loopback('ws://127.0.0.1:9',observer)

    def test_parent_loop_unchanged_and_installation_before_first_read(self):
        from websockets.sync.connection import Connection
        source=inspect.getsource(Connection.recv_events)
        with local_server(lambda conn:conn.recv(timeout=3)) as uri:
            observer=self.observer(); client=probe.connect_loopback(uri,observer)
            client.send('done'); client.close(); client.recv_events_thread.join(3)
        self.assertEqual(inspect.getsource(Connection.recv_events),source)
        self.assertTrue(observer.installed)
        self.assertIsNotNone(observer.reads[0]['gate_end'])
        self.assertIsNotNone(observer.reads[0]['socket_end'])

    def test_real_handshake_and_raw_delivery_survive_observer_clock_failure(self):
        def handler(conn):
            conn.send('unchanged'); self.assertEqual(conn.recv(timeout=3),'done')
        def fail_clock(): raise RuntimeError('observer only')
        observer=self.observer(clock=fail_clock)
        with local_server(handler) as uri:
            client=probe.connect_loopback(uri,observer)
            try:
                self.assertEqual(client.recv(timeout=3),'unchanged'); client.send('done')
            finally: client.close(); client.recv_events_thread.join(3)
        snapshot=observer.snapshot()
        self.assertFalse(snapshot['complete_observation'])
        self.assertEqual(snapshot['disabled_reason'],'observer_error')

    def test_blocked_gate_allows_other_thread_to_resume_without_telemetry_deadlock(self):
        observer=self.observer(); native=threading.Lock(); native.acquire()
        gate=probe.GateProxy(native,observer); finished=threading.Event()
        def reader():
            with gate: finished.set()
        worker=threading.Thread(target=reader); worker.start()
        try:
            deadline=time.monotonic()+2
            while not observer.reads and time.monotonic()<deadline: time.sleep(.001)
            self.assertTrue(observer.reads)
            self.assertFalse(finished.is_set())
            self.assertTrue(observer.lock.acquire(blocking=False)); observer.lock.release()
            native.release(); self.assertTrue(finished.wait(2))
        finally:
            if native.locked() and not finished.is_set(): native.release()
            worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertGreater(observer.reads[0]['gate_end'],observer.reads[0]['gate_begin'])

    def test_end_observer_failure_preserves_completed_native_flow_operation(self):
        import queue
        observer=self.observer(); assembler=SimpleNamespace(closed=False,paused=True,frames=queue.SimpleQueue())
        calls=[]; sequence=iter([1,RuntimeError('observer finish')])
        def clock():
            value=next(sequence)
            if isinstance(value,Exception): raise value
            return value
        observer.clock=clock
        result=probe.flow_callback(lambda:calls.append('once') or 42,'pause',assembler,observer)()
        self.assertEqual(result,42); self.assertEqual(calls,['once'])
        self.assertEqual(observer.disabled_reason,'observer_error')

    def test_parent_loop_delegated_once_after_install_and_finished_on_native_error(self):
        from websockets.sync.client import ClientConnection
        from websockets.sync.messages import Assembler
        observer=self.observer(); cls=probe._connection_class(observer)
        instance=cls.__new__(cls)
        instance.socket=NativeSocket(); instance.recv_flow_control=threading.Lock()
        instance.recv_messages=Assembler(16,4); instance.recv_exc=None
        error=OSError('native loop'); calls=[]
        def native(self):
            calls.append('once'); self_test.assertTrue(observer.installed); raise error
        self_test=self
        with patch.object(ClientConnection,'recv_events',native):
            with self.assertRaises(OSError) as caught: instance.recv_events()
        self.assertIs(caught.exception,error); self.assertEqual(calls,['once'])
        self.assertTrue(observer.finished)

    def test_native_process_event_error_is_not_replaced_by_observer_finish_error(self):
        from websockets.sync.client import ClientConnection
        from websockets.frames import Frame, OP_TEXT
        observer=self.observer(); self.ready_read(observer)
        probe.SocketProxy(NativeSocket(),observer).recv(4)
        cls=probe._connection_class(observer); instance=cls.__new__(cls)
        base=time.monotonic(); values=iter([base,RuntimeError('finish')])
        def clock():
            value=next(values)
            if isinstance(value,Exception): raise value
            return value
        observer.clock=clock; error=RuntimeError('native callback'); calls=[]
        def native(self,event): calls.append(event); raise error
        event=Frame(OP_TEXT,b'x')
        with patch.object(ClientConnection,'process_event',native):
            with self.assertRaises(RuntimeError) as caught: instance.process_event(event)
        self.assertIs(caught.exception,error); self.assertEqual(calls,[event])
        self.assertEqual(observer.disabled_reason,'observer_error')


if __name__ == '__main__': unittest.main()
