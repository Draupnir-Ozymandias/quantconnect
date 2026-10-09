from copy import deepcopy
from datetime import timedelta
import json
import gzip
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash
from execution_truth import market_stream
from execution_truth.receive_adapter import ObservedSocket
from execution_truth.receive_recovery import ReceiveRecoveryTracker
from execution_truth.stream_receive_analysis import _sealed_rows
from infra.stream import marker_cap_pair as cap, receive_loop_compact_lane as lane
from infra.stream import receive_loop_compact_transport as transport, receive_loop_lane as reference
from infra.stream.single_pass_encoder import SinglePassStreamLog
from infra.stream.receive_loop_contract import declare, runtime_receipt
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE, local_server


def rehash(obj, field):
    obj.pop(field, None); obj[field] = payload_hash(obj)


@unittest.skipUnless(AVAILABLE, 'pinned optional WebSocket library required')
class CompactLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract = declare('a' * 64, runtime_receipt())

    def fixture(self, root, *, observer_fault=False, tracker_fault=False, reconnect=False,
                storage_fault=None, application_fault=False, quota_fault=False):
        from websockets.exceptions import ConnectionClosed
        c = corpus()
        with cap.scope('cap128'):
            spec = market_stream.stream_plan(c['bundle'], max_seconds=15, max_frames=5,
                segmented=True, profiling=True, resilient=True, receive_path=True,
                freshness_telemetry=True, receive_policy='v3', source_plan_sha256='b' * 64)
        base = _time(spec['event_start_at_utc']); origin = time.monotonic()
        def clock(): return base + timedelta(seconds=time.monotonic() - origin)
        raw = c['book_template']; cut = len(raw) // 2
        messages = [raw, raw, [raw[:cut], raw[cut:]], c['price_templates'][0], 'PONG']
        counter = [0]; guards = threading.Lock()
        def handler(conn):
            self.assertEqual(json.loads(conn.recv(timeout=3))['type'], 'market')
            with guards:
                counter[0] += 1; number = counter[0]
            if reconnect and number == 1:
                conn.send(raw)
                conn.close(code=1013, reason='fixture transient')
                return
            try:
                for message in messages: conn.send(message)
                conn.recv(timeout=3)
            except ConnectionClosed: pass
        def broken_clock(): raise ValueError('observer clock fault')
        original = SinglePassStreamLog.append
        writes = [0]
        def failing_append(log, kind, payload):
            if kind == 'frame': raise storage_fault
            return original(log, kind, payload)
        def quota_append(log, kind, payload):
            from execution_truth.stream_segments import StreamQuotaError
            if kind == 'frame':
                writes[0] += 1
                if writes[0] == 3: raise StreamQuotaError('fixture quota')
            return original(log, kind, payload)
        from contextlib import ExitStack
        with ExitStack() as stack:
            if tracker_fault:
                stack.enter_context(patch.object(ReceiveRecoveryTracker, 'observe_frame', side_effect=ValueError('tracker fault')))
            if storage_fault is not None:
                stack.enter_context(patch.object(SinglePassStreamLog, 'append', failing_append))
            if quota_fault:
                stack.enter_context(patch.object(SinglePassStreamLog, 'append', quota_append))
            if application_fault:
                stack.enter_context(patch.object(ReceiveRecoveryTracker, 'deliver', side_effect=ValueError('application fault')))
            uri = stack.enter_context(local_server(handler))
            result = lane.collect_fixture(c['bundle'], spec, root / 'stream', uri, self.contract,
                clock=clock, _observer_clock=broken_clock if observer_fault else time.monotonic)
        return result

    def rows(self, root):
        with cap.scope('cap128'): verified = market_stream.verify_stream_log(root / 'stream')
        return list(_sealed_rows(root / 'stream', verified))

    def test_inherited_native_application_methods_and_parent_guard(self):
        for method in ('recv', 'queue_snapshot', 'send', 'close'):
            self.assertIs(getattr(lane.CompactDiagnosticSocket, method), getattr(ObservedSocket, method))
        from websockets.sync.client import ClientConnection
        class ChangedLoop(ClientConnection):
            def recv_events(self): pass
        class ChangedClose(ClientConnection):
            def close_socket(self): pass
        class ChangedConstructor(ClientConnection):
            def __init__(self): pass
        for parent in (object, ChangedLoop, ChangedClose, ChangedConstructor):
            observer = transport.TransportBuffer(self.contract)
            with self.assertRaises(ContractError):
                transport.connect_loopback('ws://127.0.0.1:9', observer, _parent=parent)
            self.assertFalse(observer.claimed)

    def test_duplicate_safe_fragment_and_heartbeat_archive_linkage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); summary, envelope = self.fixture(root)
            self.assertEqual(summary['status'], 'frame_limit')
            result = lane.verify_fixture(root / 'stream', envelope, self.contract)
            self.assertEqual(result['deliveries'], 5); self.assertEqual(result['linked_markers'], 5)
            self.assertEqual(result['unknown_markers'], 0)
            self.assertTrue(result['attribution_available']); self.assertTrue(result['raw_archive_integrity_verified'])
            frames = [r['payload'] for r in self.rows(root) if r['kind'] == 'frame']
            markers = [f['receive_path']['receive_marker'] for f in frames]
            self.assertEqual(len({m['first_frame_sequence'] for m in markers}), 5)
            self.assertGreater(markers[2]['last_frame_sequence'], markers[2]['first_frame_sequence'])
            self.assertEqual(frames[0]['raw_text'], frames[1]['raw_text'])
            with self.assertRaises(ContractError): reference.verify_fixture(root / 'stream', envelope, self.contract)

    def test_reconnect_keeps_connection_local_ordinals_and_archive_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); summary, envelope = self.fixture(root, reconnect=True)
            self.assertEqual(summary['connections'], 2)
            self.assertEqual([e['connection'] for e in envelope['connections']], [1, 2])
            result = lane.verify_fixture(root / 'stream', envelope, self.contract)
            self.assertEqual(result['linked_markers'], 5); self.assertTrue(result['attribution_available'])
            frames = [r['payload']['receive_path'] for r in self.rows(root) if r['kind'] == 'frame']
            self.assertEqual({r['connection'] for r in frames}, {1, 2})

    def test_observer_fault_preserves_archive_but_never_claims_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, envelope = self.fixture(root, observer_fault=True)
            result = lane.verify_fixture(root / 'stream', envelope, self.contract)
            self.assertTrue(result['raw_archive_integrity_verified'])
            self.assertEqual(result['deliveries'], 5)
            self.assertEqual(result['markers_with_incomplete_sideband'], 5)
            self.assertFalse(result['attribution_available'])

    def test_tracker_fault_preserves_unknown_raw_population(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, envelope = self.fixture(root, tracker_fault=True)
            result = lane.verify_fixture(root / 'stream', envelope, self.contract)
            self.assertTrue(result['raw_archive_integrity_verified'])
            self.assertEqual(result['unknown_markers'], 5)
            self.assertFalse(result['attribution_available'])
            self.assertEqual(len([r for r in self.rows(root) if r['kind'] == 'frame']), 5)

    def test_storage_error_preserves_partial_evidence_and_retires_receiver(self):
        clients = []; original = lane.CompactDiagnosticSocket
        def tracked(*args, **kwargs):
            client = original(*args, **kwargs); clients.append(client); return client
        error = OSError('injected recorder write fault')
        with tempfile.TemporaryDirectory() as tmp, patch.object(lane, 'CompactDiagnosticSocket', tracked):
            root = Path(tmp)
            with self.assertRaises(OSError) as caught: self.fixture(root, storage_fault=error)
            self.assertIs(caught.exception, error)
            self.assertTrue(list((root / 'stream').iterdir()))
            with cap.scope('cap128'):
                partial = market_stream.verify_stream_log(root / 'stream')
            self.assertFalse(partial['session_end_present'])
            self.assertEqual(len(clients), 1)
            self.assertFalse(clients[0].connection.recv_events_thread.is_alive())

    def test_application_telemetry_fault_preserves_raw_archive_but_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ContractError, 'recovery trajectory unavailable'):
                self.fixture(root, application_fault=True)
            rows = []
            for path in sorted((root / 'stream').glob('segment-*.gz')):
                with gzip.open(path, 'rt') as handle: rows.extend(json.loads(line) for line in handle)
            frames = [r['payload'] for r in rows if r['kind'] == 'frame']
            self.assertEqual(len(frames), 5)
            # Raw retained does NOT mean its v3 trajectory passed verification.
            from execution_truth.receive_adapter import validate_adapter_failure
            header = rows[0]['payload']
            with cap.scope('cap128'):
                for frame in frames:
                    validate_adapter_failure(frame['receive_path'], header['receive_path_contract'], frame['raw_text'])

    def test_quota_finalization_is_valid_partial_evidence_not_recorder_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); summary, envelope = self.fixture(root, quota_fault=True)
            self.assertEqual(summary['status'], 'storage_limit')
            result = lane.verify_fixture(root / 'stream', envelope, self.contract)
            self.assertTrue(result['raw_archive_integrity_verified'])
            self.assertEqual(result['deliveries'], 2)
            self.assertEqual(result['recorder_status'], 'storage_limit')
            self.assertFalse(result['recorder_completed_declared_bound'])
            self.assertFalse(result['attribution_available'])

    def test_cleanup_fault_does_not_replace_primary_recorder_error(self):
        primary = OSError('primary recorder fault'); calls = []; original = lane.CompactDiagnosticSocket.close
        def close(client):
            calls.append(client)
            original(client)
            if len(calls) == 2: raise RuntimeError('secondary cleanup fault')
        with tempfile.TemporaryDirectory() as tmp, patch.object(lane.CompactDiagnosticSocket, 'close', close):
            with self.assertRaises(OSError) as caught: self.fixture(Path(tmp), storage_fault=primary)
            self.assertIs(caught.exception, primary)
            self.assertEqual(len(calls), 2)
            self.assertFalse(calls[0].connection.recv_events_thread.is_alive())

    def test_sideband_snapshot_fault_does_not_discard_verified_raw_archive(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(transport.TransportBuffer, 'snapshot',
                side_effect=ContractError('snapshot fault')):
            root = Path(tmp)
            with self.assertRaisesRegex(ContractError, 'snapshot fault'): self.fixture(root)
            with cap.scope('cap128'): verified = market_stream.verify_stream_log(root / 'stream')
            self.assertTrue(verified['session_end_present']); self.assertEqual(verified['frames'], 5)

    def test_other_archive_same_payloads_cannot_borrow_occurrence_sideband(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a, b = Path(first), Path(second)
            _, envelope = self.fixture(a); _, other = self.fixture(b)
            envelope['stream_final_record_sha256'] = other['stream_final_record_sha256']
            rehash(envelope, 'envelope_sha256')
            with self.assertRaises(ContractError): lane.verify_fixture(b / 'stream', envelope, self.contract)

    def test_rehashed_source_spec_archive_and_connection_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, envelope = self.fixture(root)
            alterations = [lambda e: e.update(stream_final_record_sha256='c' * 64),
                lambda e: e.update(stream_spec_sha256='c' * 64), lambda e: e.update(integration_sources={}),
                lambda e: e['connections'].append(deepcopy(e['connections'][0])),
                lambda e: e['connections'][0].update(connection=2),
                lambda e: e.update(orders_authorized=True), lambda e: e.update(extra='no')]
            for alter in alterations:
                bad = deepcopy(envelope); alter(bad); rehash(bad, 'envelope_sha256')
                with self.assertRaises(ContractError): lane.verify_fixture(root / 'stream', bad, self.contract)

    def test_rehashed_callback_gap_false_completeness_and_marker_time_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, envelope = self.fixture(root)
            for fault in ('gap', 'complete', 'time', 'connection'):
                bad = deepcopy(envelope); band = bad['connections'][0]['sideband']
                row = next(r for r in band['reads'] if r['frame_callbacks'])
                if fault == 'gap': row['frame_first'] += 1
                elif fault == 'complete': band['complete_observation'] = False
                elif fault == 'connection':
                    band['connection_outcome'] = 'error'; band['connection_error_type'] = 'OSError'
                else: row['dispatch_first_begin'] = row['dispatch_last_end']
                rehash(band, 'sideband_sha256'); rehash(bad, 'envelope_sha256')
                with self.assertRaises(ContractError): lane.verify_fixture(root / 'stream', bad, self.contract)

    def test_sealed_compressed_archive_byte_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _, envelope = self.fixture(root)
            path = root / 'stream' / 'segment-000000.gz'
            # Fixture-local corruption only; never mutate retained origin evidence.
            raw = bytearray(path.read_bytes()); raw[len(raw) // 2] ^= 1; path.write_bytes(raw)
            with self.assertRaises((ContractError, OSError, EOFError)):
                lane.verify_fixture(root / 'stream', envelope, self.contract)
