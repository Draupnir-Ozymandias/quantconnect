"""Explicit diagnostic adapters; never imported by deployed collectors."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import threading
import time

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity import (
    COUNTERS, CounterSample, CpuStamp, ProducerSample, SampleBuffer, number)


class PacingProbe:
    """Owns a synthetic producer step, not a drop-in wrapper for frozen workers."""
    def __init__(self, capacity, *, monotonic=time.monotonic, sleep=time.sleep):
        self.buffer = SampleBuffer(capacity)
        self.monotonic, self.sleep = monotonic, sleep
        self.previous = number(monotonic())
        self.last_stamp = self.previous
        self.failure = None
        self.owner = threading.get_ident()

    def _stamp(self):
        value = number(self.monotonic())
        if value < self.last_stamp:
            raise ContractError('probe clock regressed')
        self.last_stamp = value
        return value

    def step(self, deadline, prepare, send):
        if self.buffer.closed or self.failure or self.buffer.overflow:
            raise ContractError('probe closed/failed/overflowed; do not replay')
        if self.buffer.count == len(self.buffer._rows):
            self.buffer.overflow = True
            raise ContractError('probe bound exceeded before native operations')
        if threading.get_ident() != self.owner:
            self.failure = 'thread_changed'
            raise ContractError('pacing probe is single-threaded')
        try:
            number(deadline)
            pacing = self._stamp()
            decision = self._stamp()
            requested = max(0, deadline-decision)
            sleep_begin = self._stamp()
            self.sleep(requested)  # Native operation exactly once, including zero sleep.
            sleep_end = self._stamp()
            begin = self._stamp()
            raw = prepare(begin)
            send_start = self._stamp()
            result = send(raw)
            send_end = self._stamp()
            sample = ProducerSample(self.buffer.count, self.previous, pacing, decision,
                                    sleep_begin, sleep_end, begin, send_start, send_end,
                                    deadline, requested)
            if not self.buffer.append(sample):
                raise ContractError('probe buffer overflow; native result not acceptance')
            self.previous = send_end
            return result
        except Exception as exc:
            self.failure = type(exc).__name__
            raise  # Preserve the exact native exception; no fallback/retry.

    def finish(self):
        report = self.buffer.finish()
        report.update(adapter_failure=self.failure, model_only=False,
                      complete=report['complete'] and self.failure is None)
        return report


def cpu_stamp(*, wall=time.monotonic, cpu=time.thread_time, identity=threading.get_ident):
    # Native sampling order is explicit; no alternate acquisition order hidden here.
    thread = identity()
    before = wall()
    value = cpu()
    after = wall()
    stamp = CpuStamp(before, value, after, thread)
    stamp.validate()
    return stamp


def parse_cpu_stat(text):
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[1].isascii() or not parts[1].isdigit():
            raise ContractError('malformed cpu.stat line')
        name, value = parts
        if name in values:
            raise ContractError('duplicate cpu.stat field')
        values[name] = int(value)
    return tuple((k, values[k]) for k in COUNTERS if k in values)


def process_start(text, pid):
    prefix, sep, suffix = text.rpartition(')')
    if not sep or not prefix.startswith(str(pid)+' ('):
        raise ContractError('proc stat PID/shape differs')
    fields = suffix.split()
    if len(fields) < 20 or not fields[19].isascii() or not fields[19].isdigit():
        raise ContractError('proc stat start identity unavailable')
    return fields[19]


def unified_cgroup(text):
    matches = [line[3:] for line in text.splitlines() if line.startswith('0::')]
    if len(matches) != 1:
        raise ContractError('exactly one cgroup v2 membership required')
    value = matches[0]
    p = PurePosixPath(value)
    if not p.is_absolute() or str(p) != value or '..' in p.parts:
        raise ContractError('noncanonical cgroup path')
    return value


@dataclass(frozen=True)
class CounterRead:
    sample: object
    error: str


class CounterReader:
    """Bounded explicit reads; no observer thread or sampling schedule is created."""
    def __init__(self, pid, capacity=128, *, proc_root='/proc', cgroup_root='/sys/fs/cgroup',
                 monotonic=time.monotonic):
        if type(pid) is not int or pid <= 0 or type(capacity) is not int or not 1 <= capacity <= 1024:
            raise ContractError('bounded counter reader identity/capacity required')
        self.pid, self.proc = pid, Path(proc_root)
        self.mount, self.clock = Path(cgroup_root).resolve(), monotonic
        self.rows, self.count = [None]*capacity, 0
        self.closed = self.overflow = False

    @staticmethod
    def _text(path):
        # Finite bytes per read; no commands or writes. Leaf symlinks are refused.
        if path.is_symlink():
            raise ContractError('counter/proc leaf symlink refused')
        with path.open('rb') as handle:
            data = handle.read(4097)
        if len(data) > 4096:
            raise ContractError('counter/proc input exceeds byte bound')
        return data.decode('ascii')

    def _identity(self):
        boot = self._text(self.proc/'sys/kernel/random/boot_id').strip()
        start = process_start(self._text(self.proc/str(self.pid)/'stat'), self.pid)
        group = unified_cgroup(self._text(self.proc/str(self.pid)/'cgroup'))
        if not boot:
            raise ContractError('boot identity unavailable')
        return boot, start, group

    def read(self):
        if self.closed:
            raise ContractError('finished counter reader cannot be reused')
        if self.count == len(self.rows):
            self.overflow = True
            raise ContractError('counter sample bound exceeded; no further reads')
        try:
            begin = self.clock()
            boot, start, group = self._identity()
            path = self.mount/group.lstrip('/')/'cpu.stat'
            resolved = path.resolve(strict=True)
            if self.mount not in resolved.parents or resolved != path:
                raise ContractError('cgroup counter escapes mount or uses symlink')
            counters = parse_cpu_stat(self._text(path))
            if self._identity() != (boot, start, group):
                raise ContractError('process identity changed during counter read')
            sample = CounterSample(boot, self.pid, start, group, begin, self.clock(), counters)
            sample.validate()
            result = CounterRead(sample, None)
        except Exception as exc:
            # Unknown identity/counters cannot be fabricated as a valid zero sample.
            result = CounterRead(None, type(exc).__name__)
        self.rows[self.count] = result
        self.count += 1
        return result

    def finish(self):
        if self.closed:
            raise ContractError('counter finish is single-use')
        self.closed = True
        rows = tuple(self.rows[:self.count])
        return dict(reads=rows, overflow=self.overflow,
                    complete=bool(rows) and not self.overflow and all(r.error is None for r in rows),
                    probe_cost_verified=False, execution_authorized=False)
