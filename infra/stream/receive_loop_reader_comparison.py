"""Finite reader lifecycle comparison; not the producer cost acceptance gate."""
from dataclasses import asdict
from pathlib import Path
import time

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream.receive_loop_validity_probe import CounterReader
from infra.stream.receive_loop_pinned_counter import PinnedCounterReader
from infra.stream.receive_loop_validity import counter_interval

POLICY=dict(schema_version='qcrl.reader_lifecycle_comparison_policy.v1',
            order=[['original','pinned'],['pinned','original'],['original','pinned']],
            reads_per_case=100,pacing='none_finite_helper_batch_not_cadence_experiment',
            timing='constructor_first_read_then_99_reads_then_finish_all_in_total',
            identity='explicit_target_checked_on_every_sample_both_readers',
            validation='counter_intervals_after_timing_no_sample_materialization_inside',
            failure='preserve_no_replay',cost_gate_evaluated=False)


def declare():
    root=Path(__file__).resolve().parents[2]
    names=('infra/stream/receive_loop_reader_comparison.py',
           'tests/test_receive_loop_reader_comparison.py',
           'infra/stream/receive_loop_pinned_counter.py',
           'infra/stream/receive_loop_validity_probe.py',
           'infra/stream/receive_loop_validity.py','execution_truth/contracts.py')
    obj=dict(policy=POLICY,sources={p:file_hash(root/p) for p in names},
             execution_authorized=False,probe_cost_accepted=False)
    obj['plan_sha256']=payload_hash(obj);return obj


def run(expected,*,execute=False,proc_root='/proc',cgroup_root='/sys/fs/cgroup'):
    if execute is not True:raise ContractError('explicit finite comparison required')
    rows=[]
    for round_index,lanes in enumerate(POLICY['order']):
        for lane in lanes:
            reader=None;samples=[]
            try:
                cpu_begin=time.process_time();wall_begin=time.monotonic()
                kwargs=dict(proc_root=proc_root,cgroup_root=cgroup_root)
                reader=(CounterReader(expected['pid'],100,**kwargs) if lane=='original' else
                        PinnedCounterReader(expected,100,execute=True,**kwargs))
                for i in range(100):
                    result=reader.read()
                    if result.error or result.sample is None:
                        raise ContractError('reader attempt unavailable: '+str(result.error))
                    if any(getattr(result.sample,k)!=v for k,v in expected.items()):
                        raise ContractError('reader does not bind explicit target')
                    samples.append(result.sample)
                    if i==0:
                        cold_cpu=time.process_time()-cpu_begin;cold_wall=time.monotonic()-wall_begin
                end_reads_cpu=time.process_time();end_reads_wall=time.monotonic()
                done=reader.finish()
                cpu_end=time.process_time();wall_end=time.monotonic()
                if not done['complete']:raise ContractError('reader lifecycle incomplete')
                for a,b in zip(samples,samples[1:]):
                    if counter_interval(a,b)['status']!='observed':
                        raise ContractError('native counter interval unavailable')
                rows.append(dict(round=round_index,lane=lane,reads=100,
                    cold_cpu=cold_cpu,cold_wall=cold_wall,
                    steady_cpu=end_reads_cpu-cpu_begin-cold_cpu,
                    close_cpu=cpu_end-end_reads_cpu,total_cpu=cpu_end-cpu_begin,
                    total_wall=wall_end-wall_begin,samples=[asdict(s) for s in samples]))
            except Exception as exc:
                exc.reader_comparison_partial=dict(completed_rows=rows,round=round_index,lane=lane,
                    observed_samples=[asdict(s) for s in samples],error=type(exc).__name__)
                raise
            finally:
                if isinstance(reader,PinnedCounterReader):reader.close()
    return dict(schema_version='qcrl.reader_lifecycle_comparison.v1',plan=declare(),
                expected=expected,rows=rows,cost_gate_evaluated=False,
                probe_cost_accepted=False,producer_cohort_executed=False)
