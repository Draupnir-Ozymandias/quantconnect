"""Compact closure-free model buffer; intentionally not a transport-compatible subclass."""
import hashlib
import json
from pathlib import Path
import threading
import time

from execution_truth.contracts import ContractError,payload_hash,verify_artifact_hash
from infra.stream import receive_loop_probe as reference,receive_loop_lane as lane
from infra.stream.receive_loop_contract import validate_contract

READ_FIELDS=('iteration','receiver_thread','gate_begin','gate_end','gate_outcome','socket_begin',
    'socket_end','socket_outcome','bytes_returned','frame_first','frame_last','frame_callbacks',
    'nonframe_callbacks','dispatch_first_begin','dispatch_last_end')
READ_ERRORS=('socket_error_type','dispatch_error_type')
FLOW_FIELDS=('operation','kind','thread','begin','end','outcome','assembler_closed','assembler_paused','queue_depth')


class ReadRow:
    __slots__=READ_FIELDS+READ_ERRORS
    def __init__(self,iteration,thread,begin):
        self.iteration,self.receiver_thread,self.gate_begin=iteration,thread,begin
        self.gate_end=self.gate_outcome=self.socket_begin=self.socket_end=self.socket_outcome=None
        self.bytes_returned=self.frame_first=self.frame_last=None
        self.frame_callbacks=self.nonframe_callbacks=0
        self.dispatch_first_begin=self.dispatch_last_end=None
        self.socket_error_type=self.dispatch_error_type=None


class FlowRow:
    __slots__=FLOW_FIELDS+('error_type',)
    def __init__(self,operation,kind,thread,begin,assembler):
        self.operation,self.kind,self.thread,self.begin=operation,kind,thread,begin
        self.end=self.outcome=self.error_type=None
        self.assembler_closed,self.assembler_paused=assembler.closed,assembler.paused
        self.queue_depth=assembler.frames.qsize()


def row_dict(row,fields,optional):
    out={name:getattr(row,name) for name in fields}
    out.update({name:getattr(row,name) for name in optional if getattr(row,name) is not None})
    return out


class CompactBuffer:
    # Reuse unchanged construction, clock validation and cross-thread disable/finish.
    # Not inheritance: the original connect_loopback must reject this model object.
    __init__=reference.ObservationBuffer.__init__
    disable=reference.ObservationBuffer.disable
    _stamp=reference.ObservationBuffer._stamp
    loop_finished=reference.ObservationBuffer.loop_finished

    def gate_begin(self):
        try:
            with self.lock:
                if self.disabled_reason is not None: return None
                if len(self.reads)>=self.limits['max_read_summaries']:
                    self.disabled_reason='read_summary_budget'; return None
                row=ReadRow(len(self.reads)+1,threading.get_ident(),self._stamp())
                self.reads.append(row); self.current=row
                return row
        except Exception: self.disable('observer_error')

    def gate_end(self,row,outcome):
        try:
            with self.lock:
                if self.disabled_reason is not None or row is None: return
                end=self._stamp()
                if end<row.gate_begin: raise ValueError('gate clock regressed')
                row.gate_end,row.gate_outcome=end,outcome
        except Exception: self.disable('observer_error')

    def read_begin(self):
        try:
            with self.lock:
                if self.disabled_reason is not None: return None
                row=self.current
                if row is None or row.socket_begin is not None: raise ValueError('unbound or repeated socket read')
                stamp=self._stamp()
                if row.gate_outcome!='acquired' or stamp<row.gate_end: raise ValueError('read precedes gate acquisition')
                row.socket_begin=stamp
                return row
        except Exception: self.disable('observer_error')

    def read_end(self,row,data=None,error=None):
        try:
            with self.lock:
                if self.disabled_reason is not None or row is None: return
                end=self._stamp()
                if end<row.socket_begin: raise ValueError('read clock regressed')
                if error is None and not isinstance(data,bytes): raise ValueError('unexpected recv result')
                row.socket_end=end
                row.socket_outcome='error' if error is not None else 'data' if data else 'eof'
                row.bytes_returned=None if error is not None else len(data)
                if error is not None: row.socket_error_type=type(error).__name__[:128]
        except Exception: self.disable('observer_error')

    def flow_begin(self,kind,assembler):
        try:
            with self.lock:
                if self.disabled_reason is not None: return None
                if len(self.flows)>=self.limits['max_flow_edges']:
                    self.disabled_reason='flow_edge_budget'; return None
                row=FlowRow(len(self.flows)+1,kind,threading.get_ident(),self._stamp(),assembler)
                self.flows.append(row)
                return row
        except Exception: self.disable('observer_error')

    def flow_end(self,row,error=None):
        try:
            with self.lock:
                if self.disabled_reason is not None or row is None: return
                end=self._stamp()
                if end<row.begin: raise ValueError('flow clock regressed')
                row.end=end; row.outcome='error' if error is not None else 'returned'
                if error is not None: row.error_type=type(error).__name__[:128]
        except Exception: self.disable('observer_error')

    def dispatch_begin(self,is_frame):
        try:
            with self.lock:
                if self.disabled_reason is not None: return None
                row=self.current
                if row is None: raise ValueError('dispatch without read iteration')
                stamp=self._stamp()
                if row.socket_end is None or stamp<row.socket_end: raise ValueError('dispatch precedes completed socket read')
                if row.dispatch_first_begin is None: row.dispatch_first_begin=stamp
                if is_frame:
                    self.frame_count+=1; row.frame_callbacks+=1
                    if row.frame_first is None: row.frame_first=self.frame_count
                    row.frame_last=self.frame_count
                else: row.nonframe_callbacks+=1
                return row
        except Exception: self.disable('observer_error')

    def dispatch_end(self,row,error=None):
        try:
            with self.lock:
                if self.disabled_reason is not None or row is None: return
                stamp=self._stamp()
                if stamp<row.dispatch_first_begin: raise ValueError('dispatch clock regressed')
                row.dispatch_last_end=stamp
                if error is not None: row.dispatch_error_type=type(error).__name__[:128]
        except Exception: self.disable('observer_error')

    def snapshot(self):
        with self.lock:
            if not self.finished: raise ContractError('receiver must finish before sideband snapshot')
            rows=[row_dict(r,READ_FIELDS,READ_ERRORS) for r in self.reads]
            flows=[row_dict(f,FLOW_FIELDS,('error_type',)) for f in self.flows]
            reason,installed,error=self.disabled_reason,self.installed,self.receiver_error_type
        complete=(reason is None and installed and all(r['gate_end'] is not None
            and (r['gate_outcome']!='acquired' or r['socket_end'] is not None) for r in rows)
            and all(f['end'] is not None for f in flows))
        out={'schema_version':'qcrl.receive_loop_compact_sideband.model.v1',
            'contract_sha256':self.contract['contract_sha256'],'reads':rows,'flows':flows,
            'installed_before_parent_loop':installed,'receiver_finished':True,'complete_observation':complete,
            'disabled_reason':reason,'receiver_error_type':error,'benchmark_performed':False,
            'overhead_acceptance_established':False,'public_rollout_authorized':False,
            'wire_arrival_measured':False,'orders_authorized':False,'model_only':True,
            'transport_installation_verified':False,
            'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        out['sideband_sha256']=payload_hash(out)
        if len(json.dumps(out,sort_keys=True).encode())>self.limits['max_encoded_sideband_bytes']:
            self.disable('encoded_sideband_budget')
            raise ContractError('sideband exceeds bound; preserve buffers, do not emit success')
        return out


def scan_model(sideband,contract):
    """Source-bound model check, with explicit in-memory structural projection only."""
    validate_contract(contract)
    verify_artifact_hash(sideband,'sideband_sha256','compact model sideband')
    if (sideband.get('schema_version')!='qcrl.receive_loop_compact_sideband.model.v1'
            or sideband.get('model_only') is not True or sideband.get('transport_installation_verified') is not False
            or sideband.get('implementation_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or len(json.dumps(sideband,sort_keys=True).encode())>contract['policy']['max_encoded_sideband_bytes']):
        raise ContractError('compact model source/scope/budget differs')
    # Reuse independently implemented ordering/range/flow rules. Never persist this
    # projected view or call it a reference implementation / transport receipt.
    view={k:v for k,v in sideband.items() if k not in ('model_only','transport_installation_verified','sideband_sha256')}
    view['schema_version']='qcrl.receive_loop_probe_sideband.prototype.v1'
    view['implementation_sha256']=hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest()
    view['sideband_sha256']=payload_hash(view)
    result=lane.scan_sideband(view,contract)
    return dict(result,model_only=True,transport_installation_verified=False)
