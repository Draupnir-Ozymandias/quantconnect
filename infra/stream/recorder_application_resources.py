"""Bounded current Linux cgroup/RSS observations, never self-attested acceptance."""
import math
import os
import re
import stat
import threading
from pathlib import Path, PurePosixPath
import time

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.receive_loop_validity_probe import process_start, unified_cgroup


RSS_THREAD_CPU_POLICY = dict(schema_version='qcrl.rss_thread_cpu_policy.v1',
    clock='time.thread_time_ns', scope='rss_reads_only_opt_in',
    placement='wall_before_cpu_before_resource_work_cpu_after_wall_after',
    cpu_clock_calls_per_read=2, retries=0, cpu_scope='inside_wall_bracket',
    wall_bracket_authoritative=True, subtract_cpu_from_wall=False,
    auxiliary_failure='retain_wall_sample_cpu_unknown',
    linkage='sample_sha256_and_observer_thread_id',
    incremental_overhead_proven=False, native_validation_complete=False)


def cpu_stamp(clock):
    """An auxiliary clock fault must not discard the authoritative RSS read."""
    try:
        value = clock()
        if type(value) is not int or value < 0:
            raise ContractError('nonnegative integer thread CPU nanoseconds required')
        return value, None
    except Exception as exc:
        return None, (type(exc).__name__ + ':' + str(exc))[:160]


def verify_rss_thread_cpu(sample, *, expected_thread_id):
    """Verify auxiliary linkage only; never changes wall/resource acceptance."""
    value = sample.get('rss_thread_cpu')
    fields = {'schema_version', 'policy_sha256', 'thread_id', 'sample_sha256',
              'before_ns', 'after_ns', 'delta_ns', 'status', 'error', 'witness_sha256'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ContractError('RSS thread CPU witness required')
    verify_artifact_hash(value, 'witness_sha256', 'RSS thread CPU witness')
    original = {k: v for k, v in sample.items() if k != 'rss_thread_cpu'}
    if (value['schema_version'] != 'qcrl.rss_thread_cpu.v1'
            or value['policy_sha256'] != payload_hash(RSS_THREAD_CPU_POLICY)
            or value['sample_sha256'] != payload_hash(original)
            or sample.get('rss_bytes') is None
            or type(expected_thread_id) is not int or expected_thread_id <= 0
            or type(value['thread_id']) is not int
            or value['thread_id'] != expected_thread_id):
        raise ContractError('RSS thread CPU sample/policy/thread binding differs')
    before, after = value['before_ns'], value['after_ns']
    for stamp in (before, after):
        if stamp is not None and (type(stamp) is not int or stamp < 0):
            raise ContractError('invalid thread CPU reading')
    ordered = before is not None and after is not None and before <= after
    if value['status'] == 'observed':
        if (not ordered or value['error'] is not None
                or type(value['delta_ns']) is not int or value['delta_ns'] != after-before):
            raise ContractError('invalid observed thread CPU delta')
    elif (value['status'] != 'unknown' or ordered or value['delta_ns'] is not None
            or type(value['error']) is not str or not 1 <= len(value['error']) <= 160):
        raise ContractError('invalid unknown thread CPU witness')
    return value


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
    if not isinstance(value, str):
        raise ContractError('observed CPU set required')
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


def controllers(value):
    if not isinstance(value, str):
        raise ContractError('controller declaration required')
    names = value.split()
    if len(names) != len(set(names)) or any(not re.fullmatch('[a-z][a-z0-9_]*', n) for n in names):
        raise ContractError('invalid controller declaration')
    return set(names)


def cpu_sets(ancestors):
    """Absent child files are valid only with complete disabled-controller proof."""
    if not isinstance(ancestors, list) or not 1 <= len(ancestors) <= 32:
        raise ContractError('bounded CPU ancestry required')
    fields = {'controllers', 'subtree_control'}
    witnessed = any(fields & set(row) for row in ancestors)
    if witnessed:
        for i, row in enumerate(ancestors):
            if not fields <= set(row):
                raise ContractError('incomplete controller ancestry')
            available, enabled = controllers(row['controllers']), controllers(row['subtree_control'])
            if not enabled <= available:
                raise ContractError('enabled controller unavailable')
            path = PurePosixPath(row['path'])
            if path.is_absolute() or '..' in path.parts or str(path) != row['path']:
                raise ContractError('noncanonical resource ancestry')
            if i == len(ancestors)-1:
                if row['path'] != '.' or row['cpuset_effective'] is None or 'cpuset' not in available:
                    raise ContractError('observed root CPU set required')
            else:
                parent = ancestors[i+1]
                if row['path'] == '.' or str(path.parent) != parent['path'] or not fields <= set(parent):
                    raise ContractError('incomplete parent controller binding')
                parent_enabled = controllers(parent['subtree_control'])
                if not available <= parent_enabled or ('cpuset' in available) != ('cpuset' in parent_enabled):
                    raise ContractError('controller hierarchy differs')
                if (row['cpuset_effective'] is not None) != ('cpuset' in parent_enabled):
                    raise ContractError('CPU-set file/controller state differs')
    selected = []
    for row in ancestors:
        if row['cpuset_effective'] is None:
            if not witnessed:
                raise ContractError('missing CPU set without controller proof')
            continue
        selected.append(cpus(row['cpuset_effective']))
    if not selected or any(not child <= parent for child, parent in zip(selected, selected[1:])):
        raise ContractError('missing/inconsistent effective CPU ancestry')
    return selected


def quota(ancestors):
    limits = []
    intersection = None
    for row in ancestors:
        if row['cpu_max'] is None:
            if row['path'] != '.':
                raise ContractError('invalid CPU quota')
        else:
            if not isinstance(row['cpu_max'], str):
                raise ContractError('observed CPU quota required')
            pieces = row['cpu_max'].split()
            if len(pieces) != 2 or not pieces[1].isdecimal() or int(pieces[1]) <= 0:
                raise ContractError('invalid CPU quota')
            if pieces[0] != 'max':
                if not pieces[0].isdecimal() or int(pieces[0]) <= 0:
                    raise ContractError('invalid CPU quota')
                limits.append(int(pieces[0]) / int(pieces[1]))
    for selected in cpu_sets(ancestors):
        intersection = selected if intersection is None else intersection & selected
    if not ancestors or not intersection:
        raise ContractError('missing effective CPU ancestry')
    return min(limits + [len(intersection)])


class LinuxReader:
    def __init__(self, *, execute=False, proc='/proc', mount='/sys/fs/cgroup',
                 pid=None, monotonic=time.monotonic, rss_thread_cpu=False,
                 thread_cpu_ns=time.thread_time_ns):
        if execute is not True:
            raise ContractError('explicit resource observation required')
        if type(rss_thread_cpu) is not bool or not callable(thread_cpu_ns):
            raise ContractError('explicit RSS thread CPU option and callable clock required')
        self.rss_thread_cpu, self.thread_cpu_ns = rss_thread_cpu, thread_cpu_ns
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
        instrument = self.rss_thread_cpu and rss
        thread_id = threading.get_ident() if instrument else None
        begin = self.clock()
        if instrument:
            cpu_before, before_error = cpu_stamp(self.thread_cpu_ns)
        self.check_paths()
        if self.identity(self.pid) != self.expected:
            raise ContractError('resource owner identity changed')
        def limit(path, name):
            try:
                return text(path / name).strip()
            except FileNotFoundError:
                if path != self.mount:
                    raise
                return None  # Root absence is retained, not a fabricated quota.
        def ancestry_snapshot():
            rows = []
            for path in self.ancestors:
                try:
                    effective = text(path / 'cpuset.cpus.effective').strip()
                except FileNotFoundError:
                    effective = None  # Validated against actual parent controls below.
                rows.append(dict(path=str(path.relative_to(self.mount)),
                    cpu_max=limit(path, 'cpu.max'), cpuset_effective=effective,
                    memory_max=limit(path, 'memory.max'),
                    controllers=text(path / 'cgroup.controllers').strip(),
                    subtree_control=text(path / 'cgroup.subtree_control').strip()))
            return rows
        ancestry = ancestry_snapshot()
        effective_quota = quota(ancestry)
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
        closing_ancestry = ancestry_snapshot()
        # Compare the complete ordered snapshots, including every quota input.
        # Reuse only within this read; changed snapshots retain validation faults.
        if closing_ancestry != ancestry:
            quota(closing_ancestry)
            raise ContractError('resource controller/limit ancestry raced')
        self.check_paths()
        if instrument:
            cpu_after, after_error = cpu_stamp(self.thread_cpu_ns)
        end = self.clock()
        if not math.isfinite(begin) or not math.isfinite(end) or not 0 <= begin <= end:
            raise ContractError('invalid resource clock')
        result = dict(before=begin, after=end, owner=self.expected, ancestry=ancestry,
                    effective_quota=effective_quota, cpu=cpu, memory_events=events,
                    memory_current=current, actors=actors,
                    rss_bytes=sum(r['rss_bytes'] for r in actors) if rss else None)
        if instrument:
            error = before_error or after_error
            if error is None and cpu_after < cpu_before:
                error = 'ContractError:thread CPU clock regressed'
            value = dict(schema_version='qcrl.rss_thread_cpu.v1',
                policy_sha256=payload_hash(RSS_THREAD_CPU_POLICY), thread_id=thread_id,
                sample_sha256=payload_hash(result), before_ns=cpu_before, after_ns=cpu_after,
                delta_ns=cpu_after-cpu_before if error is None else None,
                status='observed' if error is None else 'unknown', error=error)
            result['rss_thread_cpu'] = dict(value, witness_sha256=payload_hash(value))
        return result


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
