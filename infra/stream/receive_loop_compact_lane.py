"""Isolated compact recorder fixture and archive/sideband linkage verifier; no launcher."""
from bisect import bisect_left
import hashlib
import json
from pathlib import Path
import threading
import time
import sys
from unittest.mock import patch

from execution_truth import market_stream
from execution_truth.acquisition import utc_now
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.receive_adapter import ObservedSocket, _load_library
from execution_truth.receive_path import sample_clock
from execution_truth.receive_recovery import ReceiveRecoveryTracker
from execution_truth.stream_receive_analysis import _sealed_rows
from infra.stream import marker_cap_pair as cap, receive_loop_compact_transport as transport
from infra.stream.receive_loop_contract import validate_contract
from infra.stream.receive_loop_lane import integer
from infra.stream.single_pass_encoder import SinglePassStreamLog


def integration_sources():
    paths = [Path(__file__), Path(transport.__file__)]
    paths += [Path(__file__).with_name(name + '.py') for name in (
        'single_pass_encoder', 'marker_cap_pair', 'receive_loop_lane', 'receive_loop_compact',
        'receive_loop_probe', 'receive_loop_contract')]
    paths += sorted(Path(market_stream.__file__).parent.glob('*.py'))
    return {str(p.relative_to(Path(__file__).resolve().parents[2])):
            hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


class CompactDiagnosticSocket(ObservedSocket):
    """Retain native application recv/send/queue/close and scoped v3 recovery."""
    def __init__(self, uri, tracker, connection, *, loop_contract, clock=utc_now,
                 monotonic=time.monotonic, _observer_clock=time.monotonic):
        if not isinstance(tracker, ReceiveRecoveryTracker) or tracker.policy['max_pending_message_markers'] != 128:
            raise ContractError('compact fixture requires scoped 128-marker v3 tracker')
        Frame, ClientConnection, _ = _load_library()
        self.tracker, self.number, self.clock, self.monotonic = tracker, connection, clock, monotonic
        self.reader_lock = threading.Lock(); self.last_exit = None
        self.observer = transport.TransportBuffer(loop_contract, clock=_observer_clock)
        self.reset = tracker.begin_connection(connection)
        adapter = self

        class TrackedConnection(ClientConnection):
            def process_event(self, event):
                if isinstance(event, Frame):
                    try:
                        stamp = sample_clock(adapter.clock, adapter.monotonic, tracker.domain)
                        tracker.observe_frame(connection, int(event.opcode), bool(event.fin), bytes(event.data), stamp)
                    except Exception:
                        adapter.observer.disable('receiver_observation_error')
                        with tracker.lock:
                            if tracker.connection == connection: tracker._disable('receiver_observation_error')
                return super().process_event(event)

        self.connection = transport.connect_loopback(uri, self.observer, _parent=TrackedConnection)
        try: self.queue_snapshot()
        except BaseException:
            self.connection.close(); self.connection.recv_events_thread.join(5)
            raise


class RecorderTransport:
    """Match the recorder's transport-error boundary; leave adapter delivery intact."""
    def __init__(self, client): self.client, self.reset = client, client.reset
    def send(self, message):
        from websockets.exceptions import WebSocketException
        try: return self.client.send(message)
        except (OSError, WebSocketException) as exc:
            raise market_stream.StreamTransportError(market_stream.transport_reason(exc)) from exc
    def recv(self, timeout):
        from websockets.exceptions import WebSocketException
        try: return self.client.recv(timeout)
        except TimeoutError: raise
        except (OSError, WebSocketException) as exc:
            raise market_stream.StreamTransportError(market_stream.transport_reason(exc)) from exc
    def close(self): return self.client.close()


def collect_fixture(bundle, spec, stream, uri, loop_contract, *, clock=utc_now,
                    monotonic=time.monotonic, _observer_clock=time.monotonic):
    """Finite unit-fixture API only. Never emits an envelope after recorder failure."""
    validate_contract(loop_contract)
    clients = []
    def connector(tracker, number, **kwargs):
        if len(clients) >= spec['max_connections']: raise ContractError('compact fixture connection budget exceeded')
        from websockets.exceptions import WebSocketException
        try:
            client = CompactDiagnosticSocket(uri, tracker, number, loop_contract=loop_contract,
                                             _observer_clock=_observer_clock, **kwargs)
        except (OSError, WebSocketException) as exc:
            raise market_stream.StreamTransportError(market_stream.transport_reason(exc)) from exc
        clients.append(client)
        return RecorderTransport(client)
    try:
        with cap.scope('cap128'), patch.object(market_stream, 'SegmentedStreamLog', SinglePassStreamLog):
            summary = market_stream.collect_market_stream(bundle, spec, stream, connector=connector,
                clock=clock, monotonic=monotonic, clock_domain='localhost.receive_loop_compact_fixture')
            verified = market_stream.verify_stream_log(stream)
    finally:
        active_error = sys.exc_info()[1]; cleanup_error = None
        for client in clients:
            try: client.close()
            except BaseException as exc: cleanup_error = cleanup_error or exc
            finally:
                client.connection.recv_events_thread.join(5)
                if client.connection.recv_events_thread.is_alive():
                    cleanup_error = cleanup_error or ContractError('compact fixture receiver not finished')
        if cleanup_error is not None and active_error is None: raise cleanup_error
    if not verified['session_end_present']: raise ContractError('compact fixture archive is not finalized')
    snapshots = [{'connection': c.number, 'sideband': c.observer.snapshot()} for c in clients]
    envelope = {'schema_version': 'qcrl.receive_loop_compact_fixture_sideband.v1',
                'loop_contract_sha256': loop_contract['contract_sha256'],
                'stream_final_record_sha256': verified['final_record_sha256'],
                'stream_spec_sha256': payload_hash(spec), 'connections': snapshots,
                'integration_sources': integration_sources(), 'benchmark_performed': False,
                'public_rollout_authorized': False, 'orders_authorized': False}
    envelope['envelope_sha256'] = payload_hash(envelope)
    return summary, envelope


def verify_fixture(stream, envelope, loop_contract):
    """Verify the sealed archive first, then exact per-connection ordinal/time linkage."""
    validate_contract(loop_contract)
    verify_artifact_hash(envelope, 'envelope_sha256', 'compact fixture envelope')
    if (set(envelope) != {'schema_version', 'loop_contract_sha256', 'stream_final_record_sha256',
            'stream_spec_sha256', 'connections', 'integration_sources', 'benchmark_performed',
            'public_rollout_authorized', 'orders_authorized', 'envelope_sha256'}
            or envelope['schema_version'] != 'qcrl.receive_loop_compact_fixture_sideband.v1'
            or envelope['loop_contract_sha256'] != loop_contract['contract_sha256']
            or envelope['integration_sources'] != integration_sources()
            or any(envelope[k] is not False for k in ('benchmark_performed', 'public_rollout_authorized', 'orders_authorized'))
            or len(json.dumps(envelope, sort_keys=True).encode()) > loop_contract['policy']['max_encoded_sideband_bytes']):
        raise ContractError('compact fixture envelope source/scope/budget differs')
    with cap.scope('cap128'): verified = market_stream.verify_stream_log(stream)
    if not verified['session_end_present']: raise ContractError('compact archive lacks terminal session record')
    if envelope['stream_final_record_sha256'] != verified['final_record_sha256']:
        raise ContractError('compact sideband binds a different archive')
    rows = _sealed_rows(Path(stream), verified); header = next(rows)['payload']
    if (header['spec'].get('schema_version') != 'qcrl.public_market_stream_spec.v7'
            or header['spec'].get('receive_path', {}).get('max_pending_message_markers') != 128
            or header.get('receive_path_contract', {}).get('clock_domain') != 'localhost.receive_loop_compact_fixture'
            or envelope['stream_spec_sha256'] != header['spec_sha256']):
        raise ContractError('archive is not the source-bound compact private fixture')
    entries = envelope['connections']; scans = {}
    if not isinstance(entries, list) or not 1 <= len(entries) <= header['spec']['max_connections']:
        raise ContractError('compact sideband connection population invalid')
    for entry in entries:
        if set(entry) != {'connection', 'sideband'}: raise ContractError('unexpected compact connection fields')
        connection = integer(entry['connection'], 1)
        if connection in scans: raise ContractError('duplicate compact sideband connection')
        if entry['sideband']['connection_outcome'] != 'connected': raise ContractError('archive sideband lacks successful connection')
        scans[connection] = transport.scan_transport(entry['sideband'], loop_contract)
    linked = unknown = unavailable = ineligible = frames = 0; archive_connections = set()
    for row in rows:
        if row['kind'] != 'frame': continue
        frames += 1; record = row['payload']['receive_path']
        connection = record['connection']; archive_connections.add(connection)
        if connection not in scans: raise ContractError('archived connection has no compact sideband')
        scan = scans[connection]
        if scan['complete'] and scan['frame_callbacks'] < record['alignment']['observed_frames']:
            raise ContractError('compact sideband omits observed library callbacks')
        marker = record['receive_marker']
        if marker is None: unknown += 1; continue
        if not scan['complete']: unavailable += 1; continue
        for field, stamp_field in (('first_frame_sequence', 'first_receive_observation'),
                                  ('last_frame_sequence', 'last_receive_observation')):
            ordinal = marker[field]; position = bisect_left(scan['ends'], ordinal)
            if position >= len(scan['ranges']) or ordinal < scan['ranges'][position]['frame_first']:
                raise ContractError('compact receive marker ordinal has no dispatch range')
            dispatch = scan['ranges'][position]; stamp = marker[stamp_field]
            if not dispatch['dispatch_first_begin'] <= stamp['monotonic_before'] <= stamp['monotonic_after'] <= dispatch['dispatch_last_end']:
                raise ContractError('compact receive marker stamp outside callback dispatch')
        linked += 1
        ineligible += not (record['first_observation_to_delivery']['timing_eligible']
                           and record['last_observation_to_delivery']['timing_eligible'])
    if archive_connections != set(scans) or frames != verified['frames']:
        raise ContractError('compact archive/sideband denominator differs')
    status = verified['terminal_summary']['status']
    recorder_complete = status in ('frame_limit', 'duration_limit', 'lifecycle_stop')
    result = {'schema_version': 'qcrl.receive_loop_compact_fixture_verification.v1',
              'envelope_sha256': envelope['envelope_sha256'], 'final_record_sha256': verified['final_record_sha256'],
              'raw_archive_integrity_verified': True, 'deliveries': frames, 'linked_markers': linked,
              'unknown_markers': unknown, 'markers_with_incomplete_sideband': unavailable,
              'timing_ineligible_linked_markers': ineligible,
              'recorder_status': status, 'recorder_completed_declared_bound': recorder_complete,
              'attribution_available': recorder_complete and frames > 0 and linked == frames and ineligible == 0
                                      and all(v['complete'] for v in scans.values()),
              'benchmark_performed': False, 'public_rollout_authorized': False, 'orders_authorized': False}
    result['verification_sha256'] = payload_hash(result)
    return result
