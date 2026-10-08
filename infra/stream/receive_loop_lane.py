"""Private fixture recorder and independent sideband/archive validator; no launcher."""
from bisect import bisect_left
import hashlib
import json
import math
from pathlib import Path
import threading
import time

from execution_truth import market_stream
from execution_truth.acquisition import utc_now
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.receive_adapter import ObservedSocket, _load_library
from execution_truth.receive_path import sample_clock
from execution_truth.receive_recovery import ReceiveRecoveryTracker
from execution_truth.stream_receive_analysis import _sealed_rows
from infra.stream import marker_cap_pair as cap, receive_loop_probe as probe
from infra.stream.receive_loop_contract import validate_contract
from infra.stream.single_pass_encoder import SinglePassStreamLog
from unittest.mock import patch


class DiagnosticSocket(ObservedSocket):
    """Inherit the original recv/queue/send/close implementations unchanged."""
    def __init__(self, uri, tracker, connection, *, loop_contract, clock=utc_now,
                 monotonic=time.monotonic, _observer_clock=time.monotonic):
        if not isinstance(tracker,ReceiveRecoveryTracker) or tracker.policy['max_pending_message_markers'] != 128:
            raise ContractError('private loop lane requires scoped 128-marker v3 tracker')
        Frame, _, _ = _load_library()
        from websockets.sync.client import ClientConnection
        self.tracker,self.number,self.clock,self.monotonic = tracker,connection,clock,monotonic
        self.reader_lock = threading.Lock(); self.last_exit = None
        self.observer = probe.ObservationBuffer(loop_contract,clock=_observer_clock)
        self.reset = tracker.begin_connection(connection)
        adapter = self
        class TrackedConnection(ClientConnection):
            def process_event(self, event):
                if isinstance(event,Frame):
                    try:
                        stamp = sample_clock(adapter.clock,adapter.monotonic,tracker.domain)
                        tracker.observe_frame(connection,int(event.opcode),bool(event.fin),bytes(event.data),stamp)
                    except Exception:
                        adapter.observer.disable('receiver_observation_error')
                        with tracker.lock:
                            if tracker.connection == connection: tracker._disable('receiver_observation_error')
                return super().process_event(event)
        self.connection = probe.connect_loopback(uri,self.observer,_parent=TrackedConnection)
        try: self.queue_snapshot()
        except Exception:
            self.connection.close(); raise


def collect_fixture(bundle, spec, stream, uri, loop_contract, *, clock=utc_now,
                    monotonic=time.monotonic, _observer_clock=time.monotonic):
    """Unit-fixture API only: no producer, schedule, cgroup or benchmark selection."""
    validate_contract(loop_contract)
    clients = []
    def connector(tracker, number, **kwargs):
        if len(clients) >= spec['max_connections']: raise ContractError('fixture connection budget exceeded')
        client = DiagnosticSocket(uri,tracker,number,loop_contract=loop_contract,
                                  _observer_clock=_observer_clock,**kwargs)
        clients.append(client)
        return client
    with cap.scope('cap128'), patch.object(market_stream,'SegmentedStreamLog',SinglePassStreamLog):
        summary = market_stream.collect_market_stream(bundle,spec,stream,connector=connector,
                    clock=clock,monotonic=monotonic,clock_domain='localhost.receive_loop_fixture')
        verified = market_stream.verify_stream_log(stream)
    snapshots = []
    for client in clients:
        client.connection.recv_events_thread.join(5)
        if client.connection.recv_events_thread.is_alive(): raise ContractError('fixture receiver not finished')
        snapshots.append({'connection':client.number,'sideband':client.observer.snapshot()})
    envelope = {'schema_version':'qcrl.receive_loop_fixture_sideband.v1',
                'loop_contract_sha256':loop_contract['contract_sha256'],
                'stream_final_record_sha256':verified['final_record_sha256'],
                'stream_spec_sha256':payload_hash(spec),'connections':snapshots,
                'integration_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'benchmark_performed':False,'public_rollout_authorized':False,'orders_authorized':False}
    envelope['envelope_sha256'] = payload_hash(envelope)
    return summary,envelope


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
        raise ContractError('invalid sideband monotonic value')
    return value


def integer(value, minimum=0):
    if type(value) is not int or value < minimum: raise ContractError('invalid sideband counter')
    return value


def scan_sideband(sideband, contract):
    """Independent shape/order/range checks, not the producer's completeness flag."""
    verify_artifact_hash(sideband,'sideband_sha256','loop sideband')
    expected = {'schema_version','contract_sha256','reads','flows','installed_before_parent_loop',
                'receiver_finished','complete_observation','disabled_reason','receiver_error_type',
                'benchmark_performed','overhead_acceptance_established','public_rollout_authorized',
                'wire_arrival_measured','orders_authorized','implementation_sha256','sideband_sha256'}
    if set(sideband) != expected or type(sideband['complete_observation']) is not bool:
        raise ContractError('unexpected sideband fields')
    if type(sideband['installed_before_parent_loop']) is not bool:
        raise ContractError('installation status must be boolean')
    for key in ('disabled_reason','receiver_error_type'):
        value=sideband[key]
        if value is not None and (not isinstance(value,str) or not 1<=len(value)<=128):
            raise ContractError('invalid bounded observer/error reason')
    if len(json.dumps(sideband,sort_keys=True).encode()) > contract['policy']['max_encoded_sideband_bytes']:
        raise ContractError('encoded sideband exceeds contract bound')
    if (sideband.get('schema_version') != 'qcrl.receive_loop_probe_sideband.prototype.v1'
            or sideband.get('contract_sha256') != contract['contract_sha256']
            or sideband.get('implementation_sha256') != hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest()
            or sideband.get('receiver_finished') is not True
            or sideband.get('orders_authorized') is not False
            or sideband.get('public_rollout_authorized') is not False
            or sideband.get('wire_arrival_measured') is not False
            or sideband.get('benchmark_performed') is not False
            or sideband.get('overhead_acceptance_established') is not False):
        raise ContractError('sideband source/policy binding mismatch')
    reads,flows = sideband['reads'],sideband['flows']
    if (not isinstance(reads,list) or not isinstance(flows,list)
            or len(reads)>contract['policy']['max_read_summaries']
            or len(flows)>contract['policy']['max_flow_edges']):
        raise ContractError('sideband population exceeds bound')
    complete = (sideband['disabled_reason'] is None and sideband['installed_before_parent_loop'] is True)
    frame = 0; ranges = []; previous_end = 0; receiver_thread = None
    for index,row in enumerate(reads,1):
        required = {'iteration','receiver_thread','gate_begin','gate_end','gate_outcome','socket_begin',
                    'socket_end','socket_outcome','bytes_returned','frame_first','frame_last',
                    'frame_callbacks','nonframe_callbacks','dispatch_first_begin','dispatch_last_end'}
        if not required <= set(row) or set(row)-required-{'socket_error_type','dispatch_error_type'}:
            raise ContractError('unexpected read summary fields')
        if integer(row['iteration'],1) != index: raise ContractError('read iterations must be contiguous')
        for key in ('socket_error_type','dispatch_error_type'):
            if key in row and (not isinstance(row[key],str) or not 1<=len(row[key])<=128):
                raise ContractError('invalid bounded read error type')
        thread = integer(row['receiver_thread'],1)
        if receiver_thread not in (None,thread): raise ContractError('multiple receiver threads in one sideband')
        receiver_thread = thread
        begin = number(row['gate_begin'])
        if begin < previous_end: raise ContractError('receiver operation order regressed')
        if row['gate_end'] is None:
            complete = False; continue
        end = number(row['gate_end'])
        if end < begin: raise ContractError('gate interval regressed')
        previous_end = end
        if row['gate_outcome'] not in ('acquired','not_acquired','error'):
            raise ContractError('unsupported gate outcome')
        if row['socket_end'] is None:
            if row['gate_outcome']=='acquired': complete=False
            continue
        read_begin,read_end = number(row['socket_begin']),number(row['socket_end'])
        if row['gate_outcome'] != 'acquired' or not end <= read_begin <= read_end:
            raise ContractError('read interval differs from gate order')
        if row['socket_outcome'] not in ('data','eof','error'): raise ContractError('unsupported read outcome')
        size = row['bytes_returned']
        if row['socket_outcome']=='error':
            if size is not None or 'socket_error_type' not in row: raise ContractError('error read has invalid metadata')
        elif not 0 <= integer(size) <= 65536 or (row['socket_outcome']=='data') != (size>0):
            raise ContractError('read byte count differs from outcome')
        count = integer(row['frame_callbacks']); nonframe = integer(row['nonframe_callbacks'])
        if count+nonframe:
            if row['dispatch_last_end'] is None:
                complete=False
                continue
            first,last = number(row['dispatch_first_begin']),number(row['dispatch_last_end'])
            if not read_end <= first <= last: raise ContractError('dispatch interval precedes socket return')
            previous_end = last
        else: previous_end = read_end
        if count:
            if integer(row['frame_first'],1) != frame+1 or integer(row['frame_last'],1) != frame+count:
                raise ContractError('callback ordinal ranges skip or overlap')
            ranges.append(row); frame += count
        elif row['frame_first'] is not None or row['frame_last'] is not None:
            raise ContractError('empty dispatch has frame ordinals')
    paused = False; flow_end = 0
    for index,row in enumerate(flows,1):
        required={'operation','kind','thread','begin','end','outcome','assembler_closed','assembler_paused','queue_depth'}
        if not required <= set(row) or set(row)-required-{'error_type'}:
            raise ContractError('unexpected flow fields')
        if integer(row['operation'],1) != index or row['kind'] not in ('pause','resume'):
            raise ContractError('invalid flow operation order')
        integer(row['thread'],1)
        begin = number(row['begin'])
        if begin < flow_end: raise ContractError('flow callbacks regress under assembler mutex')
        if row['end'] is None: complete=False; continue
        end = number(row['end'])
        if end < begin: raise ContractError('flow interval regressed')
        flow_end = end
        if row['outcome'] not in ('returned','error'): raise ContractError('unsupported flow outcome')
        if row['outcome']=='error': continue
        depth = integer(row['queue_depth'])
        if type(row['assembler_closed']) is not bool or type(row['assembler_paused']) is not bool:
            raise ContractError('flow context must be explicit booleans')
        if row['kind']=='pause':
            if paused or row['assembler_closed'] or not row['assembler_paused'] or depth<=16:
                raise ContractError('pause differs from native high-water rule')
            paused=True
        else:
            if not paused or row['assembler_paused'] or (not row['assembler_closed'] and depth>4):
                raise ContractError('resume differs from native low-water/close rule')
            paused=False
    if paused: complete=False
    if bool(sideband['complete_observation']) != complete:
        raise ContractError('sideband completeness assertion disagrees with independent scan')
    return {'complete':complete,'ranges':ranges,'ends':[r['frame_last'] for r in ranges],'frame_callbacks':frame,
            'read_iterations':len(reads),'flow_operations':len(flows)}


def verify_fixture(stream, envelope, loop_contract):
    validate_contract(loop_contract)
    verify_artifact_hash(envelope,'envelope_sha256','fixture sideband envelope')
    if set(envelope) != {'schema_version','loop_contract_sha256','stream_final_record_sha256',
        'stream_spec_sha256','connections','integration_sha256','benchmark_performed',
        'public_rollout_authorized','orders_authorized','envelope_sha256'}:
        raise ContractError('unexpected sideband envelope fields')
    if len(json.dumps(envelope,sort_keys=True).encode()) > loop_contract['policy']['max_encoded_sideband_bytes']:
        raise ContractError('fixture envelope exceeds sideband byte bound')
    if (envelope.get('schema_version') != 'qcrl.receive_loop_fixture_sideband.v1'
            or envelope.get('loop_contract_sha256') != loop_contract['contract_sha256']
            or envelope.get('integration_sha256') != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or envelope.get('orders_authorized') is not False
            or envelope.get('public_rollout_authorized') is not False
            or envelope.get('benchmark_performed') is not False):
        raise ContractError('fixture envelope differs from private implementation')
    with cap.scope('cap128'): verified = market_stream.verify_stream_log(stream)
    if envelope['stream_final_record_sha256'] != verified['final_record_sha256']:
        raise ContractError('sideband binds a different archive')
    rows = _sealed_rows(Path(stream),verified); header = next(rows)['payload']
    if (header['spec'].get('schema_version') != 'qcrl.public_market_stream_spec.v7'
            or header['spec'].get('receive_path',{}).get('max_pending_message_markers') != 128
            or header.get('receive_path_contract',{}).get('clock_domain') != 'localhost.receive_loop_fixture'):
        raise ContractError('archive is not the fixed private 128-marker fixture lane')
    if envelope['stream_spec_sha256'] != header['spec_sha256']:
        raise ContractError('sideband binds a different stream specification')
    scans = {}
    if not isinstance(envelope['connections'],list) or not 1 <= len(envelope['connections']) <= header['spec']['max_connections']:
        raise ContractError('sideband connection population invalid')
    for entry in envelope['connections']:
        if set(entry) != {'connection','sideband'}: raise ContractError('unexpected connection sideband fields')
        connection = integer(entry['connection'],1)
        if connection in scans: raise ContractError('duplicate sideband connection')
        scans[connection] = scan_sideband(entry['sideband'],loop_contract)
    linked=unknown=unavailable=ineligible=frames=0; archive_connections=set()
    last_observed={}
    for row in rows:
        if row['kind'] != 'frame': continue
        frames += 1; payload=row['payload']; record=payload['receive_path']
        connection=record['connection']; archive_connections.add(connection)
        if connection not in scans: raise ContractError('archived connection has no sideband')
        scan=scans[connection]; last_observed[connection]=record['alignment']['observed_frames']
        if scan['complete'] and scan['frame_callbacks'] < last_observed[connection]:
            raise ContractError('sideband omits observed library callbacks')
        marker=record['receive_marker']
        if marker is None: unknown+=1; continue
        if not scan['complete']: unavailable+=1; continue
        ranges=scan['ranges']; ends=scan['ends']
        for field,stamp_field in [('first_frame_sequence','first_receive_observation'),
                                 ('last_frame_sequence','last_receive_observation')]:
            ordinal=marker[field]; position=bisect_left(ends,ordinal)
            if position>=len(ranges) or ordinal<ranges[position]['frame_first']:
                raise ContractError('receive marker ordinal has no dispatch range')
            dispatch=ranges[position]; stamp=marker[stamp_field]
            if not dispatch['dispatch_first_begin'] <= stamp['monotonic_before'] <= stamp['monotonic_after'] <= dispatch['dispatch_last_end']:
                raise ContractError('receive marker stamp outside bound callback dispatch')
        linked += 1
        ineligible += not (record['first_observation_to_delivery']['timing_eligible']
                           and record['last_observation_to_delivery']['timing_eligible'])
    if archive_connections != set(scans) or frames != verified['frames']:
        raise ContractError('archive/sideband connection or frame denominator differs')
    result = {'schema_version':'qcrl.receive_loop_fixture_verification.v1',
              'envelope_sha256':envelope['envelope_sha256'],'final_record_sha256':verified['final_record_sha256'],
              'raw_archive_integrity_verified':True,'deliveries':frames,'linked_markers':linked,
              'unknown_markers':unknown,'markers_with_incomplete_sideband':unavailable,
              'timing_ineligible_linked_markers':ineligible,
              'attribution_available':linked==frames and ineligible==0 and all(v['complete'] for v in scans.values()),
              'benchmark_performed':False,'public_rollout_authorized':False,'orders_authorized':False}
    result['verification_sha256']=payload_hash(result)
    return result
