"""Isolated finite workload core; not a cohort launcher or unit/resource audit."""
from dataclasses import asdict
import json
import threading
import time

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_validity import cpu_interval, number, ordered
from infra.stream.receive_loop_validity_probe import PacingProbe, cpu_stamp

GENERATOR = {'schema_version': 'qcrl.validity_synthetic_input.v1',
             'body': 'x'*512, 'encoding': 'json_sorted_compact',
             'sequence': 'contiguous_zero_based', 'time_dependent': False}


def prepare(sequence, begin):
    # Same deterministic operation in every lane; begin deliberately isn't encoded.
    if type(sequence) is not int or sequence < 0:
        raise ContractError('input occurrence sequence required')
    return json.dumps({'schema_version': GENERATOR['schema_version'],
                       'sequence': sequence, 'body': GENERATOR['body']},
                      sort_keys=True, separators=(',', ':'))


class WorkloadCore:
    """Explicit finite synthetic callbacks; default capacity is the declared 30k."""
    def __init__(self, lane, capacity=30000, *, execute=False,
                 monotonic=time.monotonic, sleep=time.sleep,
                 cpu=time.thread_time, identity=threading.get_ident):
        if execute is not True:
            raise ContractError('synthetic workload requires explicit execution')
        if lane not in ('control', 'pacing', 'full') or type(capacity) is not int or not 1 <= capacity <= 30000:
            raise ContractError('bounded declared lane/capacity required')
        self.lane, self.capacity = lane, capacity
        self.clock, self.sleep, self.cpu, self.identity = monotonic, sleep, cpu, identity
        self.owner = identity()
        self.raws, self.rows, self.cpus = [None]*capacity, [None]*capacity, [None]*capacity
        self.count = self.delivered = 0
        self.closed = self.overflow = False
        self.failure = None
        self.probe = None if lane == 'control' else PacingProbe(capacity, monotonic=monotonic, sleep=sleep)
        self.previous = number(monotonic()) if lane == 'control' else self.probe.previous

    def step(self, deadline):
        if self.closed or self.failure or self.overflow:
            raise ContractError('workload finished/failed; no replay')
        if self.count == self.capacity:
            self.overflow = True
            raise ContractError('workload bound exceeded before operations')
        index = self.count
        def build(begin):
            return prepare(index, begin)
        def sink(raw):
            self.raws[index] = raw
            self.delivered += 1
        try:
            if self.identity() != self.owner:
                raise ContractError('workload thread changed')
            number(deadline)
            first_cpu = cpu_stamp(wall=self.clock, cpu=self.cpu, identity=self.identity) if self.lane == 'full' else None
            if self.lane == 'control':
                decision = number(self.clock())
                self.sleep(max(0, deadline-decision))
                begin = number(self.clock())
                raw = build(begin)
                send_start = number(self.clock())
                sink(raw)
                end = number(self.clock())
                ordered(self.previous, decision, begin, send_start, end)
                self.rows[index] = dict(sequence=index, deadline=deadline, begin=begin,
                                        send_start=send_start, send_end=end)
                self.previous = end
            else:
                self.probe.step(deadline, build, sink)
            if first_cpu is not None:
                last_cpu = cpu_stamp(wall=self.clock, cpu=self.cpu, identity=self.identity)
                self.cpus[index] = (first_cpu, last_cpu)
                interval = cpu_interval(first_cpu, last_cpu)
                if (interval['status'] != 'observed' or
                        first_cpu.thread_id != self.owner or last_cpu.thread_id != self.owner):
                    raise ContractError('same-thread CPU pair unavailable')
            self.count += 1
        except Exception as exc:
            self.failure = type(exc).__name__
            raise

    def finish(self):
        if self.closed:
            raise ContractError('workload finish is single use')
        self.closed = True
        probe = self.probe.finish() if self.probe else None
        rows = ([asdict(s) for s in probe['samples']] if probe else self.rows[:self.count])
        report = dict(schema_version='qcrl.validity_workload_core.v1', lane=self.lane,
            capacity=self.capacity, thread_id=self.owner,
            completed_steps=self.count, delivered_occurrences=self.delivered,
            rows=rows, raws=self.raws[:self.delivered],
            cpu_pairs=[[asdict(a), asdict(b)] for a, b in self.cpus[:self.count]] if self.lane == 'full' else [],
            generator_sha256=payload_hash(GENERATOR), failure=self.failure, overflow=self.overflow,
            complete=self.count == self.capacity and self.failure is None and not self.overflow,
            protocol_workload=self.capacity == 30000, resource_audited=False,
            probe_cost_accepted=False, cohort_executed=False)
        report['report_sha256'] = payload_hash(report)
        return report


def verify_core(report):
    """Independent occurrence/order check; never turns a component into a cohort."""
    from execution_truth.contracts import verify_artifact_hash
    from infra.stream.receive_loop_validity import ProducerSample, CpuStamp
    fields = {'schema_version', 'lane', 'capacity', 'thread_id', 'completed_steps',
              'delivered_occurrences', 'rows', 'raws', 'cpu_pairs', 'generator_sha256',
              'failure', 'overflow', 'complete', 'protocol_workload', 'resource_audited',
              'probe_cost_accepted', 'cohort_executed', 'report_sha256'}
    if (not isinstance(report, dict) or set(report) != fields or
            report['schema_version'] != 'qcrl.validity_workload_core.v1' or
            type(report['thread_id']) is not int or report['thread_id'] <= 0):
        raise ContractError('workload report shape/identity differs')
    verify_artifact_hash(report, 'report_sha256', 'validity workload core')
    lane = report.get('lane')
    if lane not in ('control', 'pacing', 'full') or report['generator_sha256'] != payload_hash(GENERATOR):
        raise ContractError('workload input/lane binding differs')
    n = report['completed_steps']
    if (type(n) is not int or type(report['capacity']) is not int or
            not 0 <= n <= report['capacity'] <= 30000 or report['capacity'] < 1 or
            report['complete'] is not True or n != report['capacity'] or
            report['failure'] is not None or report['overflow'] is not False or
            report['delivered_occurrences'] != n or len(report['rows']) != n or
            len(report['raws']) != n or
            report['protocol_workload'] != (n == 30000) or
            any(report[k] is not False for k in ('resource_audited', 'probe_cost_accepted', 'cohort_executed'))):
        raise ContractError('incomplete/failed workload or unsupported acceptance claim')
    previous = None
    for i, (row, raw) in enumerate(zip(report['rows'], report['raws'])):
        if raw != prepare(i, 0) or type(row['sequence']) is not int or row['sequence'] != i:
            raise ContractError('ordered raw occurrence differs')
        if lane == 'control':
            if set(row) != {'sequence', 'deadline', 'begin', 'send_start', 'send_end'}:
                raise ContractError('control row fields differ')
            number(row['deadline'])
            ordered(row['begin'], row['send_start'], row['send_end'])
            if previous is not None and row['begin'] < previous:
                raise ContractError('control operation order regressed')
        else:
            sample = ProducerSample(**row)
            sample.partition()
            if previous is not None and sample.previous_send_end != previous:
                raise ContractError('probe adjacent boundary differs')
        previous = row['send_end']
    pairs = report['cpu_pairs']
    if len(pairs) != (n if lane == 'full' else 0):
        raise ContractError('CPU pair population differs')
    for row, pair in zip(report['rows'], pairs):
        first, last = (CpuStamp(**s) for s in pair)
        if (cpu_interval(first, last)['status'] != 'observed' or
                first.thread_id != report['thread_id'] or last.thread_id != report['thread_id']):
            raise ContractError('CPU pair unavailable')
        if first.wall_after > row['pacing_begin'] or last.wall_before < row['send_end']:
            raise ContractError('CPU pair does not enclose step')
    return dict(verified_occurrences=n, protocol_workload=n == 30000,
                resource_audited=False, probe_cost_accepted=False)
