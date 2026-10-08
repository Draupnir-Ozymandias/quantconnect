"""Isolated diagnostic prototype; no recorder integration or benchmark launcher."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_contract import validate_contract


class ObservationBuffer:
    """Bounded metadata. Its lock is never held across a native operation."""
    def __init__(self, contract, *, clock=time.monotonic):
        validate_contract(contract)
        self.contract = deepcopy(contract)
        self.limits = dict(contract['policy'])
        self.clock, self.lock = clock, threading.Lock()
        self.reads, self.flows = [], []
        self.current = None
        self.frame_count = 0
        self.disabled_reason = None
        self.installed = self.finished = False
        self.claimed = False
        self.receiver_error_type = None

    def disable(self, reason):
        with self.lock:
            if self.disabled_reason is None: self.disabled_reason = reason

    def _stamp(self):
        stamp = self.clock()
        if type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp < 0:
            raise ValueError('invalid observer clock')
        return stamp

    def _observe(self, action):
        try:
            with self.lock:
                if self.disabled_reason is not None: return None
                return action()
        except Exception:
            self.disable('observer_error')
            return None

    def gate_begin(self):
        def action():
            if len(self.reads) >= self.limits['max_read_summaries']:
                self.disabled_reason = 'read_summary_budget'; return None
            row = {'iteration':len(self.reads)+1, 'receiver_thread':threading.get_ident(),
                   'gate_begin':self._stamp(), 'gate_end':None, 'gate_outcome':None,
                   'socket_begin':None, 'socket_end':None, 'socket_outcome':None,
                   'bytes_returned':None, 'frame_first':None, 'frame_last':None,
                   'frame_callbacks':0, 'nonframe_callbacks':0,
                   'dispatch_first_begin':None, 'dispatch_last_end':None}
            self.reads.append(row); self.current = row
            return row
        return self._observe(action)

    def gate_end(self, row, outcome):
        def action():
            if row is None: return
            end = self._stamp()
            if end < row['gate_begin']: raise ValueError('gate clock regressed')
            row.update(gate_end=end,gate_outcome=outcome)
        self._observe(action)

    def read_begin(self):
        def action():
            if self.current is None or self.current['socket_begin'] is not None:
                raise ValueError('unbound or repeated socket read')
            stamp = self._stamp()
            if self.current['gate_outcome'] != 'acquired' or stamp < self.current['gate_end']:
                raise ValueError('read precedes gate acquisition')
            self.current['socket_begin'] = stamp
            return self.current
        return self._observe(action)

    def read_end(self, row, data=None, error=None):
        def action():
            if row is None: return
            end = self._stamp()
            if end < row['socket_begin']: raise ValueError('read clock regressed')
            if error is None and not isinstance(data,bytes): raise ValueError('unexpected recv result')
            row.update(socket_end=end, socket_outcome='error' if error is not None else 'data' if data else 'eof',
                       bytes_returned=None if error is not None else len(data))
            if error is not None: row['socket_error_type'] = type(error).__name__[:128]
        self._observe(action)

    def flow_begin(self, kind, assembler):
        def action():
            if len(self.flows) >= self.limits['max_flow_edges']:
                self.disabled_reason = 'flow_edge_budget'; return None
            # Called under the assembler's existing mutex; never reacquire it.
            row = {'operation':len(self.flows)+1,'kind':kind,'thread':threading.get_ident(),
                   'begin':self._stamp(),'end':None,'outcome':None,
                   'assembler_closed':assembler.closed,'assembler_paused':assembler.paused,
                   'queue_depth':assembler.frames.qsize()}
            self.flows.append(row)
            return row
        return self._observe(action)

    def flow_end(self, row, error=None):
        def action():
            if row is None: return
            end = self._stamp()
            if end < row['begin']: raise ValueError('flow clock regressed')
            row.update(end=end,outcome='error' if error is not None else 'returned')
            if error is not None: row['error_type'] = type(error).__name__[:128]
        self._observe(action)

    def dispatch_begin(self, is_frame):
        def action():
            if self.current is None: raise ValueError('dispatch without read iteration')
            row = self.current
            stamp = self._stamp()
            if row['socket_end'] is None or stamp < row['socket_end']:
                raise ValueError('dispatch precedes completed socket read')
            if row['dispatch_first_begin'] is None: row['dispatch_first_begin'] = stamp
            if is_frame:
                self.frame_count += 1; row['frame_callbacks'] += 1
                if row['frame_first'] is None: row['frame_first'] = self.frame_count
                row['frame_last'] = self.frame_count
            else: row['nonframe_callbacks'] += 1
            return row
        return self._observe(action)

    def dispatch_end(self, row, error=None):
        def action():
            if row is None: return
            stamp = self._stamp()
            if stamp < row['dispatch_first_begin']: raise ValueError('dispatch clock regressed')
            row['dispatch_last_end'] = stamp
            if error is not None:
                row['dispatch_error_type'] = type(error).__name__[:128]
        self._observe(action)

    def loop_finished(self, error=None):
        with self.lock:
            self.finished = True
            self.receiver_error_type = None if error is None else type(error).__name__[:128]

    def snapshot(self):
        """Post-join only. Encoding occurs outside the measurement path."""
        with self.lock:
            if not self.finished: raise ContractError('receiver must finish before sideband snapshot')
            rows, flows = deepcopy(self.reads), deepcopy(self.flows)
            reason, installed = self.disabled_reason, self.installed
        complete = (reason is None and installed and all(r['gate_end'] is not None
                    and (r['gate_outcome'] != 'acquired' or r['socket_end'] is not None) for r in rows)
                    and all(f['end'] is not None for f in flows))
        out = {'schema_version':'qcrl.receive_loop_probe_sideband.prototype.v1',
               'contract_sha256':self.contract['contract_sha256'], 'reads':rows,'flows':flows,
               'installed_before_parent_loop':installed,'receiver_finished':True,
               'complete_observation':complete,'disabled_reason':reason,
               'receiver_error_type':self.receiver_error_type,
               'benchmark_performed':False,'overhead_acceptance_established':False,
               'public_rollout_authorized':False,'wire_arrival_measured':False,'orders_authorized':False,
               'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        out['sideband_sha256'] = payload_hash(out)
        if len(json.dumps(out,sort_keys=True).encode()) > self.limits['max_encoded_sideband_bytes']:
            self.disable('encoded_sideband_budget')
            raise ContractError('sideband exceeds bound; preserve buffers, do not emit success')
        return out


class GateProxy:
    def __init__(self, native, observer): self.native, self.observer = native, observer
    def __getattr__(self, name): return getattr(self.native,name)
    def _acquire(self, call, *args, **kwargs):
        token = self.observer.gate_begin()
        try: result = call(*args,**kwargs)
        except BaseException:
            self.observer.gate_end(token,'error'); raise
        self.observer.gate_end(token,'acquired' if result else 'not_acquired')
        return result
    def acquire(self, *args, **kwargs): return self._acquire(self.native.acquire,*args,**kwargs)
    def release(self): return self.native.release()
    def __enter__(self): return self._acquire(self.native.__enter__)
    def __exit__(self, *args): return self.native.__exit__(*args)


class SocketProxy:
    def __init__(self, native, observer): self.native, self.observer = native, observer
    def __getattr__(self, name): return getattr(self.native,name)
    def recv(self, *args, **kwargs):
        token = self.observer.read_begin()
        try: result = self.native.recv(*args,**kwargs)
        except BaseException as exc:
            self.observer.read_end(token,error=exc); raise
        self.observer.read_end(token,data=result)
        return result


def flow_callback(native, kind, assembler, observer):
    def wrapped(*args, **kwargs):
        token = observer.flow_begin(kind,assembler)
        try: result = native(*args,**kwargs)
        except BaseException as exc:
            observer.flow_end(token,error=exc); raise
        observer.flow_end(token)
        return result
    return wrapped


def install(connection, observer):
    """Instance-only wiring; no global class edits, threads, loop copies or I/O."""
    try:
        assembler = connection.recv_messages
        if (assembler.high,assembler.low,connection.recv_bufsize) != (16,4,65536) or assembler.closed:
            raise ContractError('unsupported assembler or pre-install close')
        socket_proxy = SocketProxy(connection.socket,observer)
        gate_proxy = GateProxy(connection.recv_flow_control,observer)
        pause = flow_callback(assembler.pause,'pause',assembler,observer)
        resume = flow_callback(assembler.resume,'resume',assembler,observer)
        connection.socket, connection.recv_flow_control = socket_proxy, gate_proxy
        assembler.pause, assembler.resume = pause, resume
        with observer.lock: observer.installed = True
    except Exception:
        observer.disable('installation_error')


def _connection_class(observer, *, _parent=None):
    from websockets.frames import Frame
    from websockets.sync.client import ClientConnection
    parent = ClientConnection if _parent is None else _parent
    if not isinstance(parent,type) or not issubclass(parent,ClientConnection):
        raise ContractError('diagnostic parent must preserve ClientConnection inheritance')
    for method in ('__init__','recv_events','close_socket'):
        if getattr(parent,method) is not getattr(ClientConnection,method):
            raise ContractError('diagnostic parent must retain native constructor, receive loop and close')
    class InstrumentedConnection(parent):
        def recv_events(self):
            install(self,observer)
            try: return super().recv_events()
            finally: observer.loop_finished(getattr(self,'recv_exc',None))
        def process_event(self, event):
            token = observer.dispatch_begin(isinstance(event,Frame))
            try: result = super().process_event(event)
            except BaseException as exc:
                observer.dispatch_end(token,error=exc); raise
            observer.dispatch_end(token)
            return result
    return InstrumentedConnection


def connect_loopback(uri, observer, *, _parent=None):
    if not isinstance(observer,ObservationBuffer): raise ContractError('explicit observation buffer required')
    try:
        parsed = urlsplit(uri)
        allowed = (parsed.scheme == 'ws' and parsed.hostname in ('127.0.0.1','::1')
                   and parsed.port is not None and 0 < parsed.port <= 65535
                   and parsed.username is None and parsed.password is None
                   and not parsed.query and not parsed.fragment and parsed.path in ('','/'))
    except (ValueError,TypeError): allowed = False
    if not allowed: raise ContractError('prototype permits numeric localhost only')
    with observer.lock:
        if observer.claimed or observer.finished or observer.installed:
            raise ContractError('prototype buffer permits one connection only')
        observer.claimed = True
    from websockets.sync.client import connect
    return connect(uri,create_connection=_connection_class(observer,_parent=_parent),open_timeout=10,close_timeout=5,
                   max_size=262144,max_queue=16,compression=None,ping_interval=None,proxy=None)
