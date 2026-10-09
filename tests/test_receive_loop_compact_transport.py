import copy
import inspect
import socket
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import receive_loop_compact as model, receive_loop_compact_transport as transport
from infra.stream import receive_loop_probe as reference
from infra.stream.receive_loop_contract import declare, runtime_receipt
from tests.test_receive_adapter import AVAILABLE, local_server
from tests.test_receive_loop_probe import NativeSocket


@unittest.skipUnless(AVAILABLE, 'pinned optional WebSocket library required')
class CompactTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract = declare('a' * 64, runtime_receipt())

    def observer(self, **kwargs): return transport.TransportBuffer(self.contract, **kwargs)

    def finish(self, client):
        client.close()
        client.recv_events_thread.join(3)
        self.assertFalse(client.recv_events_thread.is_alive())

    def test_real_fragments_duplicates_binary_ping_timeout_and_close(self):
        from websockets.sync.connection import Connection
        original = inspect.getsource(Connection.recv_events)
        def handler(conn):
            conn.send([b'\xe2', b'\x82\xac'], text=True)
            conn.send('€'); conn.send(b'binary')
            conn.ping(b'control').wait(2)
            self.assertEqual(conn.recv(timeout=3), 'done')
        observer = self.observer()
        with local_server(handler) as uri:
            client = transport.connect_loopback(uri, observer)
            try:
                self.assertEqual([client.recv(timeout=3) for _ in range(3)], ['€', '€', b'binary'])
                with self.assertRaises(TimeoutError): client.recv(timeout=.01)
                with self.assertRaises(ContractError): observer.snapshot()
                client.send('done')
            finally: self.finish(client)
        result = observer.snapshot()
        self.assertTrue(result['complete_observation'])
        self.assertTrue(result['transport_installation_verified'])
        self.assertFalse(result['recorder_integration_verified'])
        self.assertEqual(result['connection_outcome'], 'connected')
        self.assertGreaterEqual(sum(r['frame_callbacks'] for r in result['reads']), 5)
        self.assertGreaterEqual(sum(r['nonframe_callbacks'] for r in result['reads']), 1)
        self.assertIsNotNone(result['reads'][0]['socket_end'])
        transport.scan_transport(result, self.contract)
        self.assertEqual(inspect.getsource(Connection.recv_events), original)
        with self.assertRaises(ContractError): transport.connect_loopback(uri, observer)
        with self.assertRaises(ContractError): model.scan_model(result, self.contract)

    def test_clock_failure_and_read_budget_keep_raw_transport_alive(self):
        def broken(): raise ValueError('clock fault')
        for kwargs, reason in (({'clock': broken}, 'observer_error'), ({}, 'read_summary_budget')):
            observer = self.observer(**kwargs)
            if not kwargs: observer.limits['max_read_summaries'] = 0
            def handler(conn):
                conn.send('raw unchanged'); self.assertEqual(conn.recv(timeout=3), 'done')
            with local_server(handler) as uri:
                client = transport.connect_loopback(uri, observer)
                try:
                    self.assertEqual(client.recv(timeout=3), 'raw unchanged'); client.send('done')
                finally: self.finish(client)
            out = observer.snapshot()
            self.assertFalse(out['complete_observation'])
            self.assertEqual(out['disabled_reason'], reason)
            transport.scan_transport(out, self.contract)

    def test_real_backpressure_close_unblocks_native_gate(self):
        from websockets.exceptions import ConnectionClosed
        sent = threading.Event()
        def handler(conn):
            for _ in range(40): conn.send('queued')
            sent.set()
            try: conn.recv(timeout=3)
            except ConnectionClosed: pass
        observer = self.observer()
        with local_server(handler) as uri:
            client = transport.connect_loopback(uri, observer)
            try:
                self.assertTrue(sent.wait(2))
                deadline = time.monotonic() + 2
                while not client.recv_messages.paused and time.monotonic() < deadline: time.sleep(.001)
                self.assertTrue(client.recv_messages.paused)
            finally: self.finish(client)
        out = observer.snapshot(); transport.scan_transport(out, self.contract)
        self.assertTrue(any(f['kind'] == 'pause' for f in out['flows']))
        self.assertTrue(any(f['kind'] == 'resume' and f['assembler_closed'] for f in out['flows']))

    def test_boundary_and_model_rejection_before_claim_or_network(self):
        observer = self.observer()
        for uri in ('wss://example.com', 'ws://localhost:9', 'ws://127.0.0.1:9/path',
                    'ws://u:p@127.0.0.1:9', 'ws://127.0.0.1:9?q=1', 'ws://127.0.0.1:9#x',
                    'ws://127.0.0.1:99999'):
            with self.assertRaises(ContractError): transport.connect_loopback(uri, observer)
        with self.assertRaises(ContractError): transport.connect_loopback('ws://127.0.0.1:9', model.CompactBuffer(self.contract))
        with self.assertRaises(ContractError): reference.connect_loopback('ws://127.0.0.1:9', observer)
        with patch('infra.stream.receive_loop_compact_transport.bindings', side_effect=ContractError('source fault')):
            with self.assertRaises(ContractError): transport.connect_loopback('ws://127.0.0.1:9', observer)
        with patch('infra.stream.receive_loop_compact_transport.bindings', return_value={}):
            with self.assertRaises(ContractError): transport.connect_loopback('ws://127.0.0.1:9', observer)
        self.assertFalse(observer.claimed)
        with self.assertRaises(ContractError): observer.snapshot()

    def test_failed_connection_is_not_reusable_or_success_evidence(self):
        observer = self.observer()
        with patch('websockets.sync.client.connect', side_effect=OSError('connect failed')):
            with self.assertRaises(OSError): transport.connect_loopback('ws://127.0.0.1:9', observer)
        self.assertTrue(observer.claimed)
        self.assertEqual(observer.connection_outcome, 'error')
        with self.assertRaises(ContractError): observer.snapshot()
        with self.assertRaises(ContractError): transport.connect_loopback('ws://127.0.0.1:9', observer)

    def test_native_loop_error_delegated_once_and_install_failure_preserved(self):
        from websockets.sync.client import ClientConnection
        from websockets.sync.messages import Assembler
        for high, reason in ((16, None), (32, 'installation_error')):
            observer = self.observer(); cls = transport._connection_class(observer)
            conn = cls.__new__(cls)
            native_socket = NativeSocket(); native_gate = threading.Lock()
            conn.socket, conn.recv_flow_control = native_socket, native_gate
            conn.recv_messages = Assembler(high, 4); conn.recv_bufsize = 65536
            error = OSError('native receiver'); conn.recv_exc = error
            calls, caught = [], []
            def native(instance):
                calls.append(instance)
                self.assertEqual(observer.installed, high == 16)
                self.assertTrue(observer.lock.acquire(False)); observer.lock.release()
                raise error
            def run():
                try: conn.recv_events()
                except OSError as exc: caught.append(exc)
            with patch.object(ClientConnection, 'recv_events', native):
                worker = threading.Thread(target=run); worker.start(); worker.join(2)
            self.assertFalse(worker.is_alive()); self.assertEqual(calls, [conn]); self.assertEqual(caught, [error])
            # This is an injected parent-loop unit fixture, not a real handshake.
            observer.connection_outcome = 'error'; observer.connection_error_type = 'OSError'
            self.assertEqual(observer.disabled_reason, reason)
            if reason:
                self.assertIs(conn.socket, native_socket); self.assertIs(conn.recv_flow_control, native_gate)
            out = observer.snapshot(); transport.scan_transport(out, self.contract)
            self.assertEqual(out['receiver_error_type'], 'OSError')
            self.assertEqual(out['transport_installation_verified'], high == 16)

    def test_native_dispatch_error_survives_observer_end_fault(self):
        from websockets.sync.client import ClientConnection
        from websockets.frames import Frame, OP_TEXT
        observer = self.observer()
        row = observer.gate_begin(); observer.gate_end(row, 'acquired')
        reference.SocketProxy(NativeSocket(), observer).recv(1)
        cls = transport._connection_class(observer); conn = cls.__new__(cls)
        error = RuntimeError('native dispatch'); calls = []
        def native(instance, event):
            calls.append(event); observer.clock = lambda: (_ for _ in ()).throw(ValueError('end fault'))
            raise error
        event = Frame(OP_TEXT, b'raw')
        with patch.object(ClientConnection, 'process_event', native):
            with self.assertRaises(RuntimeError) as caught: conn.process_event(event)
        self.assertIs(caught.exception, error); self.assertEqual(calls, [event])
        self.assertEqual(observer.disabled_reason, 'observer_error')

    def test_flow_budget_fault_does_not_deadlock_native_pause_resume(self):
        from websockets.sync.messages import Assembler
        from websockets.frames import Frame, OP_TEXT
        observer = self.observer(); observer.limits['max_flow_edges'] = 0
        gate = threading.Lock()
        assembler = Assembler(16, 4, pause=gate.acquire, resume=gate.release)
        conn = SimpleNamespace(socket=NativeSocket(), recv_flow_control=gate,
                               recv_messages=assembler, recv_bufsize=65536)
        reference.install(conn, observer)
        for _ in range(20): assembler.put(Frame(OP_TEXT, b'x'))
        self.assertTrue(gate.locked())
        for _ in range(16): self.assertEqual(assembler.get(timeout=.1), 'x')
        self.assertFalse(gate.locked())
        self.assertEqual(observer.disabled_reason, 'flow_edge_budget')
        assembler.close()

    def test_aborted_real_handshake_retains_failed_connection_lifecycle(self):
        observer = self.observer(); received = []
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen(1); listener.settimeout(3)
            def abort():
                with listener.accept()[0] as peer:
                    peer.settimeout(3); received.append(peer.recv(65536))
            worker = threading.Thread(target=abort); worker.start()
            try:
                with self.assertRaises(Exception):
                    transport.connect_loopback('ws://127.0.0.1:' + str(listener.getsockname()[1]), observer)
            finally: worker.join(3)
        self.assertFalse(worker.is_alive()); self.assertTrue(received[0].startswith(b'GET '))
        self.assertIsNotNone(observer.receiver_thread)
        observer.receiver_thread.join(3)
        out = observer.snapshot(); transport.scan_transport(out, self.contract)
        self.assertEqual(out['connection_outcome'], 'error')
        self.assertIsInstance(out['connection_error_type'], str)
        self.assertTrue(out['receiver_thread_exited'])
        with self.assertRaises(ContractError): transport.connect_loopback('ws://127.0.0.1:9', observer)

    def test_source_scope_lifecycle_tampering_and_encoded_budget(self):
        observer = self.observer()
        with local_server(lambda c: c.recv(timeout=3)) as uri:
            client = transport.connect_loopback(uri, observer); client.send('done'); self.finish(client)
        out = observer.snapshot()
        for key, value in (('parent_entries', True), ('parent_exits', 0), ('receiver_thread_exited', False),
                           ('recorder_integration_verified', True), ('model_only', True),
                           ('transport_installation_verified', 1), ('transport_sources', {}), ('extra', 1)):
            altered = copy.deepcopy(out); altered[key] = value
            altered['sideband_sha256'] = payload_hash({k: v for k, v in altered.items() if k != 'sideband_sha256'})
            with self.assertRaises(ContractError): transport.scan_transport(altered, self.contract)
        observer.limits['max_encoded_sideband_bytes'] = 1
        count = len(observer.reads)
        with self.assertRaises(ContractError): observer.snapshot()
        self.assertEqual(len(observer.reads), count)
        self.assertEqual(observer.disabled_reason, 'encoded_sideband_budget')
