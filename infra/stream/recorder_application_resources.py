"""Bounded current Linux cgroup/RSS observations, never self-attested acceptance."""
import math
import os
import stat
from pathlib import Path
import time

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity_probe import process_start, unified_cgroup


def text(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ContractError('regular resource pseudo-file required')
        data = os.read(fd, 16385)
    finally:
        os.close(fd)
    if len(data) > 16384:
        raise ContractError('resource read cap exceeded')
    return data.decode('ascii')


def counters(value):
    result = {}
    for line in value.splitlines():
        key, number = line.split()
        if key in result or not number.isdecimal():
            raise ContractError('invalid resource counter')
        result[key] = int(number)
    return result


def cpus(value):
    result = set()
    for piece in value.strip().split(','):
        pair = piece.split('-')
        if not 1 <= len(pair) <= 2 or any(not n.isdecimal() for n in pair):
            raise ContractError('invalid CPU set')
        lo, hi = int(pair[0]), int(pair[-1])
        if not 0 <= lo <= hi < 65536:
            raise ContractError('CPU set outside cap')
        result.update(range(lo, hi + 1))
    if not result:
        raise ContractError('empty CPU set')
    return result


def quota(ancestors):
    limits = []
    intersection = None
    for row in ancestors:
        if row['cpu_max'] is None:
            if row['path'] != '.':
                raise ContractError('invalid CPU quota')
        else:
            pieces = row['cpu_max'].split()
            if len(pieces) != 2 or not pieces[1].isdecimal() or int(pieces[1]) <= 0:
                raise ContractError('invalid CPU quota')
            if pieces[0] != 'max':
                if not pieces[0].isdecimal() or int(pieces[0]) <= 0:
                    raise ContractError('invalid CPU quota')
                limits.append(int(pieces[0]) / int(pieces[1]))
        selected = cpus(row['cpuset_effective'])
        intersection = selected if intersection is None else intersection & selected
    if not ancestors or not intersection:
        raise ContractError('missing effective CPU ancestry')
    return min(limits + [len(intersection)])


class LinuxReader:
    def __init__(self, *, execute=False, proc='/proc', mount='/sys/fs/cgroup',
                 pid=None, monotonic=time.monotonic):
        if execute is not True:
            raise ContractError('explicit resource observation required')
        self.proc, self.mount = Path(proc), Path(mount)
        if not self.proc.is_absolute() or self.proc.resolve() != self.proc:
            raise ContractError('canonical proc root required')
        self.pid = os.getpid() if pid is None else pid
        self.clock = monotonic
        self.expected = self.identity(self.pid)
        group = self.expected['cgroup']
        self.group = self.mount / group.lstrip('/')
        if self.group.resolve() != self.group or self.mount.resolve() != self.mount:
            raise ContractError('canonical cgroup mount required')
        self.ancestors = []
        path = self.group
        while True:
            self.ancestors.append(path)
            if path == self.mount:
                break
            if self.mount not in path.parents or len(self.ancestors) >= 32:
                raise ContractError('bounded cgroup ancestry required')
            path = path.parent
        self.anchors = {str(p): (p.stat().st_dev, p.stat().st_ino) for p in self.ancestors}

    def check_paths(self):
        for path, expected in self.anchors.items():
            value = os.stat(path, follow_symlinks=False)
            if not stat.S_ISDIR(value.st_mode) or (value.st_dev, value.st_ino) != expected:
                raise ContractError('cgroup directory identity changed')

    def identity(self, pid):
        return dict(pid=pid, process_start_id=process_start(text(self.proc / str(pid) / 'stat'), pid),
                    cgroup=unified_cgroup(text(self.proc / str(pid) / 'cgroup')),
                    boot_id=text(self.proc / 'sys/kernel/random/boot_id').strip())

    def members(self):
        rows = text(self.group / 'cgroup.procs').split()
        if not rows or len(rows) > 32 or any(not p.isdecimal() or int(p) <= 0 for p in rows):
            raise ContractError('bounded live actor population required')
        values = [int(p) for p in rows]
        if len(set(values)) != len(values) or self.pid not in values:
            raise ContractError('duplicate/missing unit actor')
        if any(p.is_dir() for p in self.group.iterdir()):
            raise ContractError('descendant cgroups unsupported; do not omit actors')
        return sorted(values)

    def read(self, *, rss=False):
        begin = self.clock()
        self.check_paths()
        if self.identity(self.pid) != self.expected:
            raise ContractError('resource owner identity changed')
        def limit(path, name):
            if path == self.mount and not (path / name).exists():
                return None  # Root absence is retained, not a fabricated quota.
            return text(path / name).strip()
        ancestry = [dict(path=str(p.relative_to(self.mount)), cpu_max=limit(p, 'cpu.max'),
                         cpuset_effective=text(p / 'cpuset.cpus.effective').strip(),
                         memory_max=limit(p, 'memory.max')) for p in self.ancestors]
        first = self.members()
        actors = []
        for pid in first:
            identity = self.identity(pid)
            if identity['cgroup'] != self.expected['cgroup']:
                raise ContractError('actor left dedicated cgroup')
            row = dict(identity)
            if rss:
                fields = [line.split() for line in text(self.proc / str(pid) / 'status').splitlines()
                          if line.startswith('VmRSS:')]
                if len(fields) != 1 or len(fields[0]) != 3 or fields[0][2] != 'kB':
                    raise ContractError('current VmRSS missing')
                row['rss_bytes'] = int(fields[0][1]) * 1024
                if row['rss_bytes'] < 0:
                    raise ContractError('negative current RSS')
            if self.identity(pid) != identity:
                raise ContractError('actor identity raced')
            actors.append(row)
        cpu = counters(text(self.group / 'cpu.stat'))
        events = counters(text(self.group / 'memory.events'))
        current = int(text(self.group / 'memory.current').strip())
        if self.members() != first or self.identity(self.pid) != self.expected:
            raise ContractError('actor membership raced')
        self.check_paths()
        end = self.clock()
        if not math.isfinite(begin) or not math.isfinite(end) or not 0 <= begin <= end:
            raise ContractError('invalid resource clock')
        return dict(before=begin, after=end, owner=self.expected, ancestry=ancestry,
                    effective_quota=quota(ancestry), cpu=cpu, memory_events=events,
                    memory_current=current, actors=actors,
                    rss_bytes=sum(r['rss_bytes'] for r in actors) if rss else None)


def observe(reader, epoch, stop, *, clock=time.monotonic, pause=time.sleep, capacity=184):
    """One sample per scheduled second; late slots stay explicit, no catch-up repair."""
    rows = []
    for slot in range(capacity):
        target = epoch + slot
        row = dict(slot=slot, target=target, cpu_before=None, sample=None, error=None)
        try:
            if slot % 60 == 0:
                pause(max(0, target - .002 - clock()))
                row['cpu_before'] = reader.read()
            pause(max(0, target - clock()))
            row['sample'] = reader.read(rss=True)
        except Exception as exc:
            row['error'] = type(exc).__name__ + ':' + str(exc)[:160]
        rows.append(row)
        if stop.is_set():
            return dict(rows=rows, overflow=False)
    return dict(rows=rows, overflow=True)
