"""Finite local helper-cost diagnostic; not a paced workload or Linux cost gate."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import threading
import time

from execution_truth.contracts import ContractError
from execution_truth.stream_segments import file_hash
from infra.stream.receive_loop_validity_probe import CounterReader, cpu_stamp, parse_cpu_stat
from infra.stream.receive_loop_validity_packed import PackedCore
from infra.stream.receive_loop_validity_lifecycle import save

LANES=('empty','native_cpu_pair','validated_cpu_pair','packed_cpu_pair',
       'counter_parse','fixture_identity','fixture_counter_read')


def run(*, execute=False, operations=100):
    if execute is not True or type(operations) is not int or not 1<=operations<=1000:
        raise ContractError('explicit bounded local diagnostic required')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='qcrl-component-') as tmp:
        root=Path(tmp);proc=root/'proc';mount=root/'cgroup'
        (proc/'sys/kernel/random').mkdir(parents=True);(proc/'123').mkdir()
        (mount/'private').mkdir(parents=True)
        (proc/'sys/kernel/random/boot_id').write_text('fixture-boot\n')
        (proc/'123/stat').write_text('123 (fixture) '+ ' '.join(['0']*19+['42']))
        (proc/'123/cgroup').write_text('0::/private\n')
        stat='usage_usec 100\nnr_periods 10\nnr_throttled 0\nthrottled_usec 0\n'
        (mount/'private/cpu.stat').write_text(stat)
        for round_index in range(3):
            order=LANES[round_index:]+LANES[:round_index]
            for lane in order:
                core=PackedCore('full',1,execute=True)
                reader=CounterReader(123,operations,proc_root=proc,cgroup_root=mount)
                def native():
                    for _ in range(2):
                        threading.get_ident();time.monotonic();time.thread_time();time.monotonic()
                def validated():
                    cpu_stamp();cpu_stamp()
                def packed():
                    core._cpu('first',0);core._cpu('last',0)
                def read_counter():
                    result=reader.read()
                    if result.error:raise ContractError('fixture read failed')
                operation={'empty':lambda:None,'native_cpu_pair':native,
                           'validated_cpu_pair':validated,'packed_cpu_pair':packed,
                           'counter_parse':lambda:parse_cpu_stat(stat),
                           'fixture_identity':reader._identity,
                           'fixture_counter_read':read_counter}[lane]
                wall_begin=time.monotonic();cpu_begin=time.process_time()
                for _ in range(operations):operation()
                cpu_elapsed=time.process_time()-cpu_begin;wall_elapsed=time.monotonic()-wall_begin
                # Materialization outside measurement, no failed round replay.
                if lane=='fixture_counter_read':
                    result=reader.finish()
                    if not result['complete'] or len(result['reads'])!=operations:
                        raise ContractError('fixture population differs')
                rows.append(dict(round=round_index,lane=lane,operations=operations,
                                 cpu_seconds=cpu_elapsed,wall_seconds=wall_elapsed))
    repo=Path(__file__).resolve().parents[2]
    names=('infra/stream/receive_loop_probe_components.py',
           'infra/stream/receive_loop_validity_packed.py',
           'infra/stream/receive_loop_validity_probe.py',
           'tests/test_receive_loop_probe_components.py')
    return dict(schema_version='qcrl.local_probe_components.v1',rows=rows,
                sources={p:file_hash(repo/p) for p in names},
                fixture_io=True,native_linux_io_measured=False,
                scope='local_cached_fixture_and_helper_batches_not_causal_or_workload_acceptance',
                cost_gate_evaluated=False,probe_cost_accepted=False,cohort_executed=False,
                public_rollout_authorized=False,orders_authorized=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    save(a.output,run(execute=a.execute))


if __name__=='__main__':main()
