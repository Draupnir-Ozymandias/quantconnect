"""Pure offline validity model. No clocks, files, threads, sockets or execution."""
from dataclasses import dataclass
import math

from execution_truth.contracts import ContractError


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ContractError('finite numeric observation required')
    return value


def ordered(*values):
    for value in values:
        number(value)
    if any(a > b for a, b in zip(values, values[1:])):
        raise ContractError('observation ordering regressed')


@dataclass(frozen=True)
class ProducerSample:
    sequence: int
    previous_send_end: float
    pacing_begin: float
    request_at: float
    sleep_begin: float
    sleep_end: float
    begin: float
    send_start: float
    send_end: float
    deadline: float
    requested_sleep: float

    def partition(self):
        if type(self.sequence) is not int or self.sequence < 0:
            raise ContractError('nonnegative sequence required')
        ordered(self.previous_send_end, self.pacing_begin, self.request_at,
                self.sleep_begin, self.sleep_end, self.begin, self.send_start, self.send_end)
        number(self.deadline)
        number(self.requested_sleep)
        expected = max(0, self.deadline-self.request_at)
        if self.requested_sleep < 0 or not math.isclose(expected, self.requested_sleep,
                                                       rel_tol=0, abs_tol=1e-9):
            raise ContractError('absolute pacing request differs from decision timestamp')
        parts = dict(bookkeeping=self.pacing_begin-self.previous_send_end,
                     pacing_calculation=self.request_at-self.pacing_begin,
                     sleep_entry=self.sleep_begin-self.request_at,
                     sleep_elapsed=self.sleep_end-self.sleep_begin,
                     wake_to_begin=self.begin-self.sleep_end,
                     preparation=self.send_start-self.begin,
                     send=self.send_end-self.send_start)
        total = self.send_end-self.previous_send_end
        if not math.isclose(sum(parts.values()), total, rel_tol=0, abs_tol=1e-9):
            raise ContractError('elapsed partition does not conserve interval')
        return dict(parts=parts, total_seconds=total,
                    sleep_excess_seconds=parts['sleep_elapsed']-self.requested_sleep,
                    begin_deadline_lateness_seconds=self.begin-self.deadline,
                    scheduler_causality_proven=False)


class SampleBuffer:
    """Preallocated references, immutable samples; no native integration/cost claim."""
    def __init__(self, capacity):
        if type(capacity) is not int or not 1 <= capacity <= 100000:
            raise ContractError('bounded sample capacity required')
        self._rows = [None]*capacity
        self.count = 0
        self.overflow = False
        self.closed = False
        self.failure = None

    def append(self, sample):
        if self.closed:
            raise ContractError('finished buffer cannot be reused')
        if self.overflow or self.failure:
            return False
        if self.count == len(self._rows):
            self.overflow = True
            return False
        try:
            if not isinstance(sample, ProducerSample):
                raise ContractError('immutable producer sample required')
            sample.partition()
            if sample.sequence != self.count:
                raise ContractError('contiguous sample sequence required')
            if self.count and sample.previous_send_end != self._rows[self.count-1].send_end:
                raise ContractError('adjacent producer intervals must share exact saved boundary')
        except ContractError as exc:
            self.failure = str(exc)
            raise
        self._rows[self.count] = sample
        self.count += 1
        return True

    def finish(self):
        if self.closed:
            raise ContractError('finish is single use')
        self.closed = True
        return dict(samples=tuple(self._rows[:self.count]), overflow=self.overflow,
                    failure=self.failure,
                    complete=bool(self.count) and not self.overflow and self.failure is None, model_only=True,
                    probe_cost_verified=False, execution_authorized=False)


@dataclass(frozen=True)
class CpuStamp:
    wall_before: float
    thread_cpu: float
    wall_after: float
    thread_id: int

    def validate(self):
        ordered(self.wall_before, self.wall_after)
        if number(self.thread_cpu) < 0 or type(self.thread_id) is not int or self.thread_id <= 0:
            raise ContractError('valid same-thread CPU sample required')


def cpu_interval(first, last):
    first.validate()
    last.validate()
    if first.thread_id != last.thread_id:
        return dict(status='unavailable', reason='thread_changed', cpu_seconds=None)
    ordered(first.wall_after, last.wall_before)
    if last.thread_cpu < first.thread_cpu:
        return dict(status='unavailable', reason='cpu_counter_reset', cpu_seconds=None)
    cpu = last.thread_cpu-first.thread_cpu
    lower = last.wall_before-first.wall_after
    upper = last.wall_after-first.wall_before
    if cpu > upper+1e-9:
        raise ContractError('CPU interval exceeds enclosing elapsed bounds')
    return dict(status='observed', cpu_seconds=cpu, elapsed_lower_seconds=lower,
                elapsed_upper_seconds=upper, scheduler_causality_proven=False)


COUNTERS = ('usage_usec', 'nr_periods', 'nr_throttled', 'throttled_usec')


@dataclass(frozen=True)
class CounterSample:
    boot_id: str
    pid: int
    process_start_id: str
    cgroup: str
    read_begin: float
    read_end: float
    # Tuple (name, integer value). Absent keys remain unavailable, never zero.
    counters: tuple
    error: str = None

    def validate(self):
        ordered(self.read_begin, self.read_end)
        if (type(self.pid) is not int or self.pid <= 0 or
                any(not isinstance(v, str) or not v for v in
                    (self.boot_id, self.process_start_id, self.cgroup))):
            raise ContractError('counter origin identity required')
        if not isinstance(self.counters, tuple):
            raise ContractError('immutable counters required')
        values = {}
        for entry in self.counters:
            if (not isinstance(entry, tuple) or len(entry) != 2 or entry[0] not in COUNTERS
                    or entry[0] in values or type(entry[1]) is not int or entry[1] < 0):
                raise ContractError('invalid/duplicate/negative counter')
            values[entry[0]] = entry[1]
        if self.error is not None and (not isinstance(self.error, str) or not self.error or values):
            raise ContractError('failed read cannot carry successful counter values')
        return values


def counter_interval(first, last):
    a, b = first.validate(), last.validate()
    identity = ('boot_id', 'pid', 'process_start_id', 'cgroup')
    if any(getattr(first, key) != getattr(last, key) for key in identity):
        reason = 'identity_changed'
    elif first.error or last.error:
        reason = 'read_failed'
    elif any(b[k] < a[k] for k in a.keys() & b.keys()):
        reason = 'counter_reset'
    else:
        reason = None
    ordered(first.read_end, last.read_begin)
    deltas = {k: b[k]-a[k] if reason is None and k in a and k in b else None
              for k in COUNTERS}
    return dict(status='unavailable' if reason else 'partial' if None in deltas.values() else 'observed',
                reason=reason, deltas=deltas,
                enclosing_interval=(first.read_begin, last.read_end),
                scheduler_causality_proven=False, event_specific_throttling_proven=False)
