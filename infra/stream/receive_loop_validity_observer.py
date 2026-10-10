"""Bounded observer component, explicitly driven; no scheduling thread or launcher."""
from dataclasses import asdict
import time

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_validity import number, ordered
from infra.stream.receive_loop_validity_probe import CounterReader


class ObserverCore:
    def __init__(self, lane, target, *, execute=False, capacity=512,
                 monotonic=time.monotonic, sleep=time.sleep, reader=None):
        if execute is not True:
            raise ContractError('observer component requires explicit execution')
        if lane not in ('control', 'pacing', 'full') or type(capacity) is not int or not 1 <= capacity <= 512:
            raise ContractError('observer lane/bound differs')
        if (not isinstance(target, dict) or set(target) != {'boot_id', 'pid', 'process_start_id', 'cgroup'}
                or type(target['pid']) is not int or target['pid'] <= 0
                or any(not isinstance(target[k], str) or not target[k]
                       for k in ('boot_id', 'process_start_id', 'cgroup'))):
            raise ContractError('explicit bound worker identity required')
        self.lane, self.target = lane, dict(target)
        self.clock, self.sleep = monotonic, sleep
        # Control/pacing do not even construct a counter reader.
        self.reader = (reader if reader is not None else CounterReader(target['pid'], capacity)) if lane == 'full' else None
        self.rows, self.count = [None]*capacity, 0
        self.closed = self.overflow = False
        self.failure = None
        self.last_deadline = self.last_wake = None

    def tick(self, deadline):
        if self.closed or self.failure or self.overflow:
            raise ContractError('observer finished/failed; no replay')
        if self.count == len(self.rows):
            self.overflow = True
            raise ContractError('observer bound exceeded before reads')
        try:
            deadline = number(deadline)
            # An external absolute scheduler must skip elapsed ticks, not burst-read.
            if (self.last_deadline is not None and deadline <= self.last_deadline) or (
                    self.last_wake is not None and deadline < self.last_wake):
                raise ContractError('observer replay/catch-up tick refused')
            decision = number(self.clock())
            requested = max(0, deadline-decision)
            self.sleep(requested)
            wake = number(self.clock())
            ordered(decision, wake)
            row = dict(sequence=self.count, deadline=deadline, decision=decision,
                       requested_sleep=requested, wake=wake,
                       deadline_lateness_seconds=wake-deadline,
                       counter=None)
            # Save attempted tick before the native read, retaining failure context.
            self.rows[self.count] = row
            self.count += 1
            self.last_deadline, self.last_wake = deadline, wake
            if self.reader is not None:
                result = self.reader.read()
                row['counter'] = result  # Materialization is deferred until finish.
                if result.sample is None:
                    raise ContractError('counter attempt unavailable: '+str(result.error))
                sample = result.sample
                if any(getattr(sample, k) != v for k, v in self.target.items()):
                    raise ContractError('counter does not bind to declared worker')
        except Exception as exc:
            self.failure = type(exc).__name__
            raise

    def finish(self):
        if self.closed:
            raise ContractError('observer finish is single use')
        self.closed = True
        report = dict(schema_version='qcrl.validity_observer_core.v1', lane=self.lane,
                      target=self.target,
                      rows=[dict(row, counter=asdict(row['counter']) if row['counter'] is not None else None)
                            for row in self.rows[:self.count]],
                      reader=self.reader.finish() if self.reader is not None else None,
                      failure=self.failure, overflow=self.overflow,
                      complete=bool(self.count) and self.failure is None and not self.overflow,
                      dedicated_cgroup_verified=False, resource_audited=False,
                      probe_cost_accepted=False, cohort_executed=False)
        # Reader report contains dataclasses: materialize only after observation ends.
        if report['reader'] is not None:
            report['reader']['reads'] = [asdict(r) for r in report['reader']['reads']]
            report['complete'] = report['complete'] and report['reader']['complete']
        report['report_sha256'] = payload_hash(report)
        return report
