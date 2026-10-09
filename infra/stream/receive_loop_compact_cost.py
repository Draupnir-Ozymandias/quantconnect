"""Finite reference/compact call-model comparison; no socket or recorder acceptance."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import tracemalloc

from execution_truth.contracts import ContractError,payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_cost as cost,receive_loop_compact as compact
from infra.stream.receive_loop_contract import validate_contract,runtime_receipt

ORDER=[['reference','compact'],['compact','reference'],['reference','compact']]


def prepare(kind,contract,clock=time.monotonic):
    if kind not in ('reference','compact'): raise ContractError('unsupported model variant')
    state=cost.prepare('observer_direct',contract,clock)
    if kind=='compact': state.observer=compact.CompactBuffer(contract,clock=clock)
    state.observer.installed=True
    return state


def check(state,kind,contract):
    if kind=='reference': return cost.check(state,contract)
    p=cost.POLICY; expected=p['reads']//p['flow_every_reads']
    if (state.native_socket.calls!=p['reads'] or state.native_callbacks!=p['reads']*p['frames_per_read']
            or state.pause_calls!=expected or state.resume_calls!=expected or state.native_gate.locked()):
        raise ContractError('compact native-model counts differ')
    state.observer.loop_finished(); band=state.observer.snapshot(); scan=compact.scan_model(band,contract)
    if not scan['complete'] or scan['frame_callbacks']!=state.native_callbacks:
        raise ContractError('compact model incomplete')
    return {'native_recv_calls':state.native_socket.calls,'native_frame_callbacks':state.native_callbacks,
            'native_pause_calls':state.pause_calls,'native_resume_calls':state.resume_calls,
            'read_summaries':len(band['reads']),'flow_edges':len(band['flows']),
            'sideband_sha256':band['sideband_sha256']}


def run(contract):
    validate_contract(contract); cases=[]; mechanics={}; allocations={}
    for kind in ('reference','compact'):
        clock=cost.StepClock(); state=prepare(kind,contract,clock); cost.workload(state)
        mechanics[kind]=dict(check(state,kind,contract),synthetic_clock_calls=clock.calls)
    for pair,variants in enumerate(ORDER):
        for kind in variants:
            state=prepare(kind,contract); before=time.process_time(); cost.workload(state)
            elapsed=time.process_time()-before; check(state,kind,contract)
            cases.append({'pair':pair,'variant':kind,'workload_cpu_seconds':elapsed})
    for kind in ('reference','compact'):
        if tracemalloc.is_tracing(): raise ContractError('do not overwrite active allocation tracing')
        state=prepare(kind,contract); tracemalloc.start()
        try:
            cost.workload(state); current,peak=tracemalloc.get_traced_memory()
        finally: tracemalloc.stop()
        check(state,kind,contract)
        allocations[kind]={'traced_retained_bytes':current,'traced_peak_bytes':peak,
                            'scope':'workload_only_excludes_snapshot_materialization'}
    repo=Path(__file__).resolve().parents[2]
    out={'schema_version':'qcrl.compact_buffer_call_model_comparison.v1',
        'model_policy':deepcopy(cost.POLICY),'case_order':deepcopy(ORDER),
        'loop_contract_sha256':contract['contract_sha256'],'runtime_receipt':runtime_receipt(),
        'mechanics':mechanics,'cpu_cases':cases,'allocations':allocations,
        'sources':{n:file_hash(repo/n) for n in ('infra/stream/receive_loop_compact.py',
            'infra/stream/receive_loop_compact_cost.py','infra/stream/receive_loop_cost.py',
            'infra/stream/receive_loop_probe.py','infra/stream/receive_loop_lane.py',
            'tests/test_receive_loop_compact.py','tests/test_receive_loop_compact_cost.py')},
        'model_only':True,'transport_semantics_proven':False,'full_recorder_overhead_measured':False,
        'cohort_replayed':False,'public_rollout_authorized':False,'orders_authorized':False}
    out['comparison_sha256']=payload_hash(out)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loop-contract',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    if not args.execute: parser.error('model comparison requires explicit --execute')
    if args.output.exists(): parser.error('do not overwrite model evidence')
    obj=run(json.loads(args.loop_contract.read_text()))
    with args.output.open('x') as handle: json.dump(obj,handle,sort_keys=True,indent=2); handle.write('\n')
    print(json.dumps({'comparison_sha256':obj['comparison_sha256'],'full_recorder_overhead_measured':False}))


if __name__=='__main__': main()
