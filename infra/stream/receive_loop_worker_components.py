"""Finite unpaced local worker diagnostic; never a workload acceptance test."""
import argparse
import json
from pathlib import Path
import platform
import threading
import time

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream.receive_loop_validity_packed import PackedCore
from infra.stream.receive_loop_validity_worker import prepare
from infra.stream.receive_loop_validity_lifecycle import save

LANES = ('empty', 'wall4_native', 'wall4_validated', 'wall7_validated',
         'native_cpu_pair', 'packed_cpu_pair', 'prepare_json', 'sleep_zero',
         'core_control_no_sleep', 'core_pacing_no_sleep', 'core_full_no_sleep',
         'core_control_yield', 'core_pacing_yield', 'core_full_yield')


def run(*, execute=False, operations=500):
    if execute is not True or type(operations) is not int or not 1 <= operations <= 5000:
        raise ContractError('explicit bounded offline worker diagnostic required')
    rows=[]; error=None
    for round_index in range(3):
        for lane in LANES[round_index:]+LANES[:round_index]:
            core=None
            if lane.startswith('core_'):
                core_lane=lane.split('_')[1]
                core=PackedCore(core_lane,operations,execute=True,
                                sleep=(lambda _:None) if lane.endswith('no_sleep') else time.sleep)
                operation=lambda i:core.step(0.0)
            elif lane=='packed_cpu_pair':
                core=PackedCore('full',operations,execute=True)
                def operation(i):
                    core._cpu('first',i);core._cpu('last',i)
            elif lane=='native_cpu_pair':
                def operation(i):
                    for _ in range(2):
                        threading.get_ident();time.monotonic();time.thread_time();time.monotonic()
            elif lane.startswith('wall'):
                calls=7 if lane=='wall7_validated' else 4
                def operation(i):
                    for _ in range(calls):
                        value=time.monotonic()
                        if lane.endswith('validated'):PackedCore._value(value)
            else:
                operation={'empty':lambda i:None, 'prepare_json':lambda i:prepare(i,0),
                           'sleep_zero':lambda i:time.sleep(0)}[lane]
            completed=0; verified_steps=None; core_hash=None
            wall_begin=time.monotonic();cpu_begin=time.process_time()
            try:
                for i in range(operations):
                    operation(i);completed+=1
            except Exception as exc:
                error={'type':type(exc).__name__,'round':round_index,'lane':lane,
                       'completed_operations':completed,'replayed':False}
            cpu_elapsed=time.process_time()-cpu_begin;wall_elapsed=time.monotonic()-wall_begin
            # Full semantic verification/materialization is outside measured batches.
            if error is None and lane.startswith('core_'):
                try:
                    report=core.finish()
                    verified_steps=report['core']['completed_steps']
                    core_hash=report['prototype_sha256']
                except Exception as exc:
                    error={'type':type(exc).__name__,'round':round_index,'lane':lane,
                           'completed_operations':completed,'replayed':False,
                           'phase':'post_window_verification'}
            rows.append(dict(round=round_index,lane=lane,operations=operations,
                             completed_operations=completed,cpu_seconds=cpu_elapsed,
                             wall_seconds=wall_elapsed,verified_steps=verified_steps,
                             verified_core_sha256=core_hash))
            if error is not None:break
        if error is not None:break
    repo=Path(__file__).resolve().parents[2]
    names=('infra/stream/receive_loop_worker_components.py',
           'tests/test_receive_loop_worker_components.py',
           'infra/stream/receive_loop_validity_packed.py',
           'infra/stream/receive_loop_validity_worker.py',
           'infra/stream/receive_loop_validity.py',
           'docs/MEASUREMENT_OVERHEAD_REVIEW.md')
    obj=dict(schema_version='qcrl.local_worker_components.v1',rows=rows,error=error,
             complete=error is None,platform=platform.platform(),python=platform.python_version(),
             sources={name:file_hash(repo/name) for name in names},
             scope='unpaced_batches_zero_deadlines_no_sockets_not_native_cohort_or_causal_profile',
             sleep_modes='no_op_or_native_sleep_zero_not_fixed_rate_pacing',
             verification_timing='after_each_measured_batch',
             cost_gate_evaluated=False,probe_cost_accepted=False,cohort_executed=False,
             public_rollout_authorized=False,orders_authorized=False)
    obj['diagnostic_sha256']=payload_hash(obj)
    return obj


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();report=run(execute=args.execute);save(args.output,report)
    print(json.dumps({'complete':report['complete'],'rows':len(report['rows']),
                      'diagnostic_sha256':report['diagnostic_sha256']}))
    if not report['complete']:raise ContractError('diagnostic failed; partial evidence retained, no retry')


if __name__=='__main__':main()
