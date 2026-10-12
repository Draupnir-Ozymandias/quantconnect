"""Isolated endpoint prototype; no worker integration, scheduler or acceptance."""
import hashlib
import math
import os
from pathlib import Path
import stat

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.recorder_application_resources import counters, quota

SCHEMA = 'qcrl.recorder_counter_endpoint_prototype.v1'
CAP = 16384


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError('finite nonnegative counter clock/value required')
    return value


def binding(guard):
    owner = guard['owner']
    actors = guard['actors']
    if (set(owner) != {'pid', 'process_start_id', 'cgroup', 'boot_id'}
            or type(owner['pid']) is not int or owner['pid'] <= 0
            or any(not isinstance(owner[k], str) or not owner[k] for k in ('process_start_id', 'cgroup', 'boot_id'))
            or not owner['cgroup'].startswith('/')):
        raise ContractError('counter owner binding invalid')
    if (not actors or len(actors) > 32 or len({a['pid'] for a in actors}) != len(actors)
            or owner not in [{k:a[k] for k in owner} for a in actors]
            or any(a['cgroup'] != owner['cgroup'] or a['boot_id'] != owner['boot_id'] for a in actors)
            or quota(guard['ancestry']) != guard['effective_quota']):
        raise ContractError('counter guard identity/quota invalid')
    return dict(owner=owner, actors=[{k:a[k] for k in owner} for a in actors],
                ancestry=guard['ancestry'], effective_quota=guard['effective_quota'])


def validate_endpoint(value):
    verify_artifact_hash(value, 'endpoint_sha256', 'prototype counter endpoint')
    if (value['schema_version'] != SCHEMA or value['acceptance_demonstrated'] is not False
            or value['native_origin_binding_verified'] is not False or value['orders_authorized'] is not False):
        raise ContractError('unsupported prototype counter authority/schema')
    pre, post = value['guard_before'], value['guard_after']
    stamps = [value['total_begin'], pre['before'], pre['after'], value['before'],
              value['after'], post['before'], post['after'], value['total_end']]
    if any(finite(t) != t for t in stamps) or stamps != sorted(stamps):
        raise ContractError('counter/guard clocks not enclosed')
    if binding(pre) != binding(post):
        raise ContractError('counter guard identity/controller state changed')
    usage = value['cpu']['usage_usec']
    if type(usage) is not int or usage < 0:
        raise ContractError('native integer CPU usage required')
    if not finite(pre['cpu']['usage_usec']) <= usage <= finite(post['cpu']['usage_usec']):
        raise ContractError('counter reset or inconsistent guard CPU usage')
    if (type(value['raw_bytes']) is not int or not 0 < value['raw_bytes'] <= CAP
            or not isinstance(value['raw_sha256'], str) or len(value['raw_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in value['raw_sha256'])):
        raise ContractError('bounded counter byte witness required')
    raw = value['raw_ascii'].encode('ascii')
    if (len(raw) != value['raw_bytes'] or hashlib.sha256(raw).hexdigest() != value['raw_sha256']
            or counters(value['raw_ascii']) != value['cpu']):
        raise ContractError('raw counter bytes/parsed fields differ')
    return value


def endpoint(read_raw, guard, clock):
    """Only read_raw lies inside the counter bracket; guards remain fully retained."""
    total_begin = clock()
    pre = guard()
    before = clock()
    raw = read_raw()
    after = clock()
    # Parsing/hash work is deliberately outside the critical read interval.
    if not isinstance(raw, bytes) or not 0 < len(raw) <= CAP:
        raise ContractError('counter read missing or exceeds cap')
    cpu = counters(raw.decode('ascii'))
    if 'usage_usec' not in cpu:
        raise ContractError('CPU usage counter missing')
    post = guard()
    value = dict(schema_version=SCHEMA, total_begin=total_begin, total_end=clock(),
                 before=before, after=after, cpu=cpu, raw_bytes=len(raw),
                 raw_ascii=raw.decode('ascii'),
                 raw_sha256=hashlib.sha256(raw).hexdigest(), guard_before=pre, guard_after=post,
                 acceptance_demonstrated=False, native_origin_binding_verified=False,
                 orders_authorized=False)
    value['endpoint_sha256'] = payload_hash(value)
    return validate_endpoint(value)


def window(start, end, boundary, *, duration=60, bracket_max=.005):
    """Offline enclosure diagnostic only; no timestamp repairs or resource verdict."""
    validate_endpoint(start)
    validate_endpoint(end)
    finite(boundary)
    if duration != 60 or type(duration) is not int or bracket_max != .005:
        raise ContractError('fixed complete window/read ceiling required')
    if (binding(start['guard_after']) != binding(end['guard_before'])
            or start['total_end'] > end['total_begin']):
        raise ContractError('window guards differ or endpoints overlap')
    if start['after'] > boundary or end['before'] < boundary + duration:
        raise ContractError('counter reads do not enclose fixed window')
    if any(v['after']-v['before'] > bracket_max for v in (start, end)):
        raise ContractError('counter read bracket exceeds fixed ceiling')
    delta = end['cpu']['usage_usec'] - start['cpu']['usage_usec']
    if delta < 0:
        raise ContractError('window CPU counter reset')
    return dict(schema_version='qcrl.recorder_counter_window_diagnostic.v1',
                boundary=boundary, duration=duration, enclosing_reads_verified=True,
                cpu_fraction_upper=delta / 1e6 / (duration * start['guard_after']['effective_quota']),
                endpoint_hashes=[start['endpoint_sha256'], end['endpoint_sha256']],
                acceptance_demonstrated=False, native_origin_binding_verified=False,
                orders_authorized=False)


class NativeCounterProbe:
    """Explicit-use preopened cpu.stat prototype; fixture-tested, not native-approved."""
    def __init__(self, reader, *, execute=False):
        if execute is not True:
            raise ContractError('explicit prototype counter observation required')
        self.reader = reader
        self.path = Path(reader.group) / 'cpu.stat'
        reader.check_paths()
        self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            value = os.fstat(self.fd)
            if not stat.S_ISREG(value.st_mode):
                raise ContractError('regular counter leaf required')
            self.identity = (value.st_dev, value.st_ino)
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise

    def guard(self):
        if self.fd is None:
            raise ContractError('counter probe closed')
        value = self.reader.read()  # Full native guards remain outside narrow read.
        for info in (os.fstat(self.fd), os.stat(self.path, follow_symlinks=False)):
            if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != self.identity:
                raise ContractError('counter leaf identity changed')
        return value

    def sample(self):
        if self.fd is None:
            raise ContractError('counter probe closed')
        return endpoint(lambda:os.pread(self.fd, CAP+1, 0), self.guard, self.reader.clock)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
