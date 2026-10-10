"""Offline packed-buffer prototype; not integrated with any Linux launcher."""
from array import array
from copy import deepcopy
import math
import threading
import time

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.receive_loop_validity_worker import GENERATOR, prepare, verify_core

METHOD = {
    'schema_version': 'qcrl.validity_packed_prototype.v1',
    'storage': 'preallocated_double_columns_raw_reference_list',
    'wall_calls_per_step': {'control': 4, 'pacing': 7, 'full': 11},
    'full_cpu_calls_per_step': 2,
    'coverage': 'same_pacing_boundaries_and_per_step_cpu_pairs',
    'validation': 'finite_order_identity_cpu_bounds_inline_partition_materialization_after_close',
    'cost_verified': False,
    'launcher_integrated': False,
}


class PackedCore:
    def __init__(self, lane, capacity=30000, *, execute=False,
                 monotonic=time.monotonic, sleep=time.sleep,
                 cpu=time.thread_time, identity=threading.get_ident):
        if execute is not True or lane not in ('control', 'pacing', 'full'):
            raise ContractError('explicit offline lane execution required')
        if type(capacity) is not int or not 1 <= capacity <= 30000:
            raise ContractError('bounded capacity required')
        self.owner = identity()
        if type(self.owner) is not int or self.owner <= 0:
            raise ContractError('positive thread identity required')
        self.lane, self.capacity = lane, capacity
        self.clock, self.sleep, self.cpu, self.identity = monotonic, sleep, cpu, identity
        names = ('deadline', 'begin', 'send_start', 'send_end') if lane == 'control' else (
            'deadline', 'pacing_begin', 'request_at', 'sleep_begin', 'sleep_end',
            'begin', 'send_start', 'send_end')
        if lane == 'full':
            names += ('first_before', 'first_cpu', 'first_after',
                      'last_before', 'last_cpu', 'last_after')
        self.columns = {n: array('d', [0.0])*capacity for n in names}
        self.raws = [None]*capacity
        self.count = self.delivered = 0
        self.closed = self.overflow = False
        self.failure = None
        self.initial = self.previous = self._value(monotonic())
        self.last_wall = self.initial

    @staticmethod
    def _value(value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ContractError('finite numeric observation required')
        return value

    def _wall(self):
        value = self._value(self.clock())
        if value < self.last_wall:
            raise ContractError('clock regressed')
        self.last_wall = value
        return value

    def _cpu(self, prefix, index):
        if self.identity() != self.owner:
            raise ContractError('CPU thread changed')
        before = self._wall()
        value = self._value(self.cpu())
        after = self._wall()
        if value < 0:
            raise ContractError('negative CPU counter')
        c = self.columns
        c[prefix+'_before'][index] = before
        c[prefix+'_cpu'][index] = value
        c[prefix+'_after'][index] = after

    def step(self, deadline):
        if self.closed or self.failure or self.overflow:
            raise ContractError('finished/failed; no replay')
        if self.count == self.capacity:
            self.overflow = True
            raise ContractError('capacity exceeded before operations')
        i, c = self.count, self.columns
        try:
            if self.identity() != self.owner:
                raise ContractError('workload thread changed')
            c['deadline'][i] = self._value(deadline)
            if self.lane == 'full': self._cpu('first', i)
            if self.lane == 'control':
                decision = self._wall()
                self.sleep(max(0, deadline-decision))
            else:
                c['pacing_begin'][i] = self._wall()
                decision = c['request_at'][i] = self._wall()
                c['sleep_begin'][i] = self._wall()
                self.sleep(max(0, deadline-decision))
                c['sleep_end'][i] = self._wall()
            begin = c['begin'][i] = self._wall()
            raw = prepare(i, begin)
            c['send_start'][i] = self._wall()
            self.raws[i] = raw
            self.delivered += 1
            end = c['send_end'][i] = self._wall()
            if self.lane == 'full':
                self._cpu('last', i)
                delta = c['last_cpu'][i]-c['first_cpu'][i]
                if delta < 0 or delta > c['last_after'][i]-c['first_before'][i]+1e-9:
                    raise ContractError('CPU reset or enclosure exceeded')
            self.previous = end
            self.count += 1
        except Exception as exc:
            self.failure = type(exc).__name__
            raise

    def finish(self):
        if self.closed: raise ContractError('single-use finish')
        self.closed = True
        rows, pairs = [], []
        previous = self.initial
        for i in range(self.count):
            row = {k: v[i] for k, v in self.columns.items() if not k.startswith(('first_', 'last_'))}
            row['sequence'] = i
            if self.lane != 'control':
                row['previous_send_end'] = previous
                row['requested_sleep'] = max(0, row['deadline']-row['request_at'])
            previous = row['send_end']; rows.append(row)
            if self.lane == 'full':
                pairs.append([dict(wall_before=self.columns[p+'_before'][i],
                                   thread_cpu=self.columns[p+'_cpu'][i],
                                   wall_after=self.columns[p+'_after'][i], thread_id=self.owner)
                              for p in ('first', 'last')])
        core = dict(schema_version='qcrl.validity_workload_core.v1', lane=self.lane,
                    capacity=self.capacity, thread_id=self.owner, completed_steps=self.count,
                    delivered_occurrences=self.delivered, rows=rows, raws=self.raws[:self.delivered],
                    cpu_pairs=pairs, generator_sha256=payload_hash(GENERATOR),
                    failure=self.failure, overflow=self.overflow,
                    complete=self.count == self.capacity and not self.failure and not self.overflow,
                    protocol_workload=self.capacity == 30000, resource_audited=False,
                    probe_cost_accepted=False, cohort_executed=False)
        core['report_sha256'] = payload_hash(core)
        # Original independent semantic verifier remains the post-close authority.
        if core['complete']: verify_core(core)
        result = dict(schema_version=METHOD['schema_version'], method=deepcopy(METHOD), core=core,
                      prototype_only=True, cost_verified=False, execution_authorized=False)
        result['prototype_sha256'] = payload_hash(result)
        return result


def verify_prototype(report):
    fields = {'schema_version', 'method', 'core', 'prototype_only', 'cost_verified',
              'execution_authorized', 'prototype_sha256'}
    if not isinstance(report, dict) or set(report) != fields:
        raise ContractError('prototype report shape differs')
    verify_artifact_hash(report, 'prototype_sha256', 'packed prototype')
    if (report['schema_version'] != METHOD['schema_version'] or report['method'] != METHOD
            or report['prototype_only'] is not True or report['cost_verified'] is not False
            or report['execution_authorized'] is not False):
        raise ContractError('prototype method or authority differs')
    return verify_core(report['core'])
