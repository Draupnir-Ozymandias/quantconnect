"""Finite synthetic observer-call microprofile; no sockets, recorder or rollout gate."""
import argparse
import cProfile
import json
from pathlib import Path
import pstats
import queue
import statistics
import threading
import time
import tracemalloc
from types import SimpleNamespace

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_probe as probe, receive_loop_lane as lane
from infra.stream import receive_loop_contract as contract

POLICY={'schema_version':'qcrl.receive_loop_call_cost_policy.v1','reads':4096,
    'frames_per_read':2,'flow_every_reads':16,'cpu_repetitions':3,
    'mode_order':['native_only','observer_direct','observer_wrapped'],
    'cpu_window':'workload_only_excludes_construction_snapshot_and_serialization',
    'profile_and_tracemalloc':'separate_passes_never_used_as_unprofiled_cpu_measurements',
    'native_model':'uncontended_lock_fixed_one_byte_fake_recv_no_protocol_or_network',
    'public_rollout_authorized':False,'benchmark_acceptance_established':False,'orders_authorized':False}


class StepClock:
    def __init__(self): self.calls=0
    def __call__(self): self.calls+=1; return self.calls/1000000


class NativeSocket:
    def __init__(self): self.calls=0
    def recv(self,size):
        if size!=65536: raise ContractError('fixed native model read size required')
        self.calls+=1; return b'x'


def prepare(mode,loop_contract,clock=time.monotonic):
    if mode not in POLICY['mode_order']: raise ContractError('unsupported call-cost mode')
    observer=None if mode=='native_only' else probe.ObservationBuffer(loop_contract,clock=clock)
    if observer is not None: observer.installed=True  # Model only, not connection installation coverage.
    native_gate=threading.Lock(); native_socket=NativeSocket()
    assembler=SimpleNamespace(closed=False,paused=False,frames=queue.SimpleQueue(),mutex=threading.Lock())
    return SimpleNamespace(mode=mode,observer=observer,native_gate=native_gate,native_socket=native_socket,
        gate=probe.GateProxy(native_gate,observer) if mode=='observer_wrapped' else native_gate,
        socket=probe.SocketProxy(native_socket,observer) if mode=='observer_wrapped' else native_socket,
        assembler=assembler,native_callbacks=0,pause_calls=0,resume_calls=0)


def workload(state):
    o=state.observer
    def pause(): state.pause_calls+=1; return state.native_gate.acquire()
    def resume(): state.resume_calls+=1; return state.native_gate.release()
    pause_call=probe.flow_callback(pause,'pause',state.assembler,o) if state.mode=='observer_wrapped' else pause
    resume_call=probe.flow_callback(resume,'resume',state.assembler,o) if state.mode=='observer_wrapped' else resume
    for index in range(POLICY['reads']):
        if state.mode=='observer_direct':
            token=o.gate_begin(); result=state.gate.acquire(); o.gate_end(token,'acquired' if result else 'not_acquired')
        else: state.gate.acquire()
        state.gate.release()
        if state.mode=='observer_direct':
            token=o.read_begin(); data=state.socket.recv(65536); o.read_end(token,data=data)
        else: state.socket.recv(65536)
        for _ in range(POLICY['frames_per_read']):
            token=o.dispatch_begin(True) if o is not None else None
            state.native_callbacks+=1
            if o is not None: o.dispatch_end(token)
        if (index+1)%POLICY['flow_every_reads']==0:
            with state.assembler.mutex:
                for _ in range(17): state.assembler.frames.put(None)
                state.assembler.paused=True
                token=o.flow_begin('pause',state.assembler) if state.mode=='observer_direct' else None
                pause_call()
                if state.mode=='observer_direct': o.flow_end(token)
                for _ in range(13): state.assembler.frames.get()
                state.assembler.paused=False
                token=o.flow_begin('resume',state.assembler) if state.mode=='observer_direct' else None
                resume_call()
                if state.mode=='observer_direct': o.flow_end(token)
                for _ in range(4): state.assembler.frames.get()


def check(state,loop_contract):
    expected=POLICY['reads']//POLICY['flow_every_reads']
    counts={'native_recv_calls':state.native_socket.calls,'native_frame_callbacks':state.native_callbacks,
            'native_pause_calls':state.pause_calls,'native_resume_calls':state.resume_calls}
    if counts!={'native_recv_calls':POLICY['reads'],'native_frame_callbacks':POLICY['reads']*POLICY['frames_per_read'],
                'native_pause_calls':expected,'native_resume_calls':expected} or state.native_gate.locked():
        raise ContractError('native-model operation population or release differs')
    if state.observer is not None:
        state.observer.loop_finished(); band=state.observer.snapshot(); scan=lane.scan_sideband(band,loop_contract)
        if not scan['complete'] or scan['frame_callbacks']!=counts['native_frame_callbacks']:
            raise ContractError('synthetic observer incomplete or callback counts differ')
        counts.update(read_summaries=len(band['reads']),flow_edges=len(band['flows']),sideband_sha256=band['sideband_sha256'])
    return counts


def run(loop_contract):
    contract.validate_contract(loop_contract)
    results=[]
    for mode in POLICY['mode_order']:
        clock=StepClock(); state=prepare(mode,loop_contract,clock); workload(state)
        mechanics=check(state,loop_contract); mechanics['synthetic_clock_calls']=clock.calls
        cpu=[]
        for _ in range(POLICY['cpu_repetitions']):
            state=prepare(mode,loop_contract); before=time.process_time(); workload(state)
            cpu.append(time.process_time()-before); check(state,loop_contract)
        state=prepare(mode,loop_contract); profiler=cProfile.Profile(); profiler.enable(); workload(state); profiler.disable()
        stats=pstats.Stats(profiler); functions=[]
        for (filename,line,name),(primitive,total,self_time,cumulative,_) in stats.stats.items():
            functions.append({'file':Path(filename).name,'line':line,'function':name,
                'primitive_calls':primitive,'total_calls':total,'self_seconds':self_time,'cumulative_seconds':cumulative})
        check(state,loop_contract)
        if tracemalloc.is_tracing(): raise ContractError('do not contaminate an existing allocation trace')
        state=prepare(mode,loop_contract)
        tracemalloc.start()
        try:
            workload(state); current,peak=tracemalloc.get_traced_memory()
            allocations=[{'file':Path(s.traceback[0].filename).name,'line':s.traceback[0].lineno,
                'bytes':s.size,'blocks':s.count} for s in tracemalloc.take_snapshot().statistics('lineno')[:10]]
        finally: tracemalloc.stop()
        check(state,loop_contract)
        results.append({'mode':mode,'mechanics':mechanics,'unprofiled_cpu_seconds':cpu,
            'median_unprofiled_cpu_seconds':statistics.median(cpu),
            'profile_top_cumulative':sorted(functions,key=lambda r:r['cumulative_seconds'],reverse=True)[:20],
            'traced_retained_bytes':current,'traced_peak_bytes':peak,'allocation_sites':allocations})
    repo=Path(__file__).resolve().parents[2]
    out={'schema_version':'qcrl.receive_loop_call_cost.v1','policy':POLICY,
        'loop_contract_sha256':loop_contract['contract_sha256'],'runtime_receipt':contract.runtime_receipt(),
        'sources':{n:file_hash(repo/n) for n in ('infra/stream/receive_loop_cost.py',
            'infra/stream/receive_loop_probe.py','infra/stream/receive_loop_lane.py','execution_truth/receive_path.py',
            'tests/test_receive_loop_cost.py')},'results':results,'cohort_replayed':False,
        'transport_semantics_proven':False,'full_recorder_overhead_measured':False,
        'public_rollout_authorized':False,'orders_authorized':False}
    out['profile_sha256']=payload_hash(out)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loop-contract',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    if not args.execute: parser.error('synthetic microprofile requires explicit --execute')
    if args.output.exists(): parser.error('do not overwrite profiling evidence')
    obj=run(json.loads(args.loop_contract.read_text()))
    with args.output.open('x') as handle: json.dump(obj,handle,sort_keys=True,indent=2); handle.write('\n')
    print(json.dumps({'profile_sha256':obj['profile_sha256'],'full_recorder_overhead_measured':False}))


if __name__=='__main__': main()
