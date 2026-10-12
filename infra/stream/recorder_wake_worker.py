"""One private Linux clock diagnostic; no public workload or network."""
import argparse
import json
import os
from pathlib import Path
import platform
import pwd
import re
import signal
import time

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_application_resources import LinuxReader
from infra.stream.recorder_application_worker import control, publish
from infra.stream.recorder_wake_probe import collect, PLAN

CAP = 256 * 1024


def bounded_publish(path, value):
    wrapped = dict(value, artifact_sha256=payload_hash(value))
    if len((json.dumps(wrapped, sort_keys=True)+'\n').encode('utf-8')) > CAP:
        raise ContractError('wake artifact exceeds 256 KiB')
    return publish(path, value)


def read_context(path):
    try:
        with Path(path).open('rb') as handle:
            data = handle.read(8193)
        if len(data) > 8192:
            raise ContractError('context exceeds bounded read')
        return dict(status='observed', text=data.decode('ascii'))
    except Exception as exc:
        return dict(status='unknown', error=type(exc).__name__)


def context(reader):
    before = time.monotonic()
    resource = reader.read(rss=True)
    files = {path: read_context(path) for path in (
        '/proc/self/timerslack_ns',
        '/sys/devices/system/clocksource/clocksource0/current_clocksource',
        '/proc/pressure/cpu', '/proc/pressure/memory', '/proc/pressure/io')}
    info = time.get_clock_info('monotonic')
    return dict(before=before, after=time.monotonic(), resource=resource,
                files=files, clock=dict(implementation=info.implementation,
                resolution=info.resolution, monotonic=info.monotonic,
                adjustable=info.adjustable))


def run(root, *, execute=False):
    if execute is not True:
        raise ContractError('explicit private wake execution required')
    root = Path(root)
    source = Path(__file__).resolve().parents[2]
    if (platform.system() != 'Linux' or os.geteuid() != pwd.getpwnam('qcrl').pw_uid
            or not re.fullmatch(r'/var/lib/qcrl-stream/recorder-wake-[A-Za-z0-9]+/evidence', str(root))
            or root.resolve(strict=True) != root or source != root.parent/'source'):
        raise ContractError('canonical qcrl private Linux worker required')
    from infra.stream.recorder_wake_launch import sources, runtime
    frozen = control(root/'execution-freeze.json')
    if (frozen['sources'] != sources() or frozen['runtime'] != runtime()
            or frozen['plan_sha256'] != payload_hash(PLAN)):
        raise ContractError('worker source/runtime/plan differs')
    reader = LinuxReader(execute=True)
    before = context(reader)
    ready = bounded_publish(root/'ready.json', dict(identity=reader.expected,
        before=before, execution_sha256=frozen['artifact_sha256']))
    deadline = time.monotonic()+15
    while not (root/'release.json').exists() and time.monotonic() < deadline:
        time.sleep(.01)
    release = control(root/'release.json')
    if (time.monotonic() >= deadline or release['ready_sha256'] != ready['artifact_sha256']
            or release['execution_sha256'] != frozen['artifact_sha256']):
        raise ContractError('independent release missing or mismatched')
    def terminate(signum, frame):
        raise ContractError('finite worker termination signal')
    previous = signal.signal(signal.SIGTERM, terminate)
    probe, error, after = None, None, None
    try:
        probe = collect(clock=time.monotonic, pause=time.sleep, execute=True)
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:160])
    finally:
        signal.signal(signal.SIGTERM, previous)
        try:
            after = context(reader)
        except Exception as exc:
            error = error or dict(type=type(exc).__name__, message=str(exc)[:160])
        bounded_publish(root/'wake-result.json', dict(probe=probe, error=error,
            before=before, after=after, identity=reader.expected,
            ready_sha256=ready['artifact_sha256'], release_sha256=release['artifact_sha256'],
            execution_sha256=frozen['artifact_sha256'],
            native_origin_verified=False, acceptance_demonstrated=False, orders_authorized=False))
    if error or probe is None or any(row['status'] != 'observed' for row in probe['rows']):
        raise ContractError('finite wake diagnostic contains unknowns; no replay')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    run(args.root, execute=args.execute)


if __name__ == '__main__': main()
