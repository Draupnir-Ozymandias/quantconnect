"""One declared two-wait compatibility worker; explicit private Linux gate only."""
import argparse
import json
import os
from pathlib import Path
import platform
import pwd
import select
import sys
import time

from execution_truth.contracts import ContractError, canonical_json, payload_hash, verify_artifact_hash
from infra.stream.recorder_absolute_wait import native, timestamp
from infra.stream.recorder_wait_comparison_v2 import SelectWait, error_text
from infra.stream.recorder_wait_execution import COMPATIBILITY, validate_freeze
from infra.stream.recorder_wait_lifecycle import STAGE

CAP = 262144


def load(path, *, cap=CAP):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ContractError('regular nonsymlink control required')
    with path.open('rb') as handle:
        data = handle.read(cap+1)
    if len(data) > cap:
        raise ContractError('control read exceeds cap')
    value = json.loads(data)
    if type(value) is not dict:
        raise ContractError('control object required')
    return value


def publish(path, value):
    """Exclusive bounded publication; failed writes are retained without replay."""
    data = (canonical_json(value)+'\n').encode('utf-8')
    if len(data) > CAP:
        raise ContractError('publication exceeds cap')
    path = Path(path)
    with path.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return value


def collect(*, clock_ns, select_wait, absolute_wait, execute=False):
    if execute is not True:
        raise ContractError('explicit injected compatibility collection required')
    result = dict(epoch_ns=None, waits=[], fatal_error=None)
    try:
        epoch = timestamp(clock_ns())
        timestamp(epoch+2*COMPATIBILITY['interval_ns'])
        result['epoch_ns'] = epoch
    except (Exception, KeyboardInterrupt) as exc:
        result['fatal_error'] = error_text(exc)
    last = result['epoch_ns']
    for ordinal, arm in enumerate(COMPATIBILITY['arm_order']):
        row = dict(arm=arm, observation=None, error=None)
        result['waits'].append(row)
        if result['fatal_error'] is not None:
            row['error'] = 'prior_compatibility_fault_no_attempt'
            continue
        try:
            checkpoint = timestamp(clock_ns())
            if checkpoint < last:
                raise ContractError('compatibility clock regressed before wait')
            adapter = select_wait if arm == 'select' else absolute_wait
            observed = adapter.wait(epoch+(ordinal+1)*COMPATIBILITY['interval_ns'], execute=True)
            row['observation'] = observed
            if observed['before_ns'] < checkpoint:
                raise ContractError('compatibility request clock regressed')
            last = max(observed['before_ns'], observed['after_ns'] or 0)
            if observed['status'] != 'observed':
                result['fatal_error'] = observed['error'] or 'unknown_compatibility_wait'
        except (Exception, KeyboardInterrupt) as exc:
            row['error'] = error_text(exc)
            result['fatal_error'] = row['error']
    return result


def result_object(measured, frozen, ready, release):
    value = dict(measured, schema_version='qcrl.wait_compatibility_result.v1',
                 plan_sha256=payload_hash(COMPATIBILITY), freeze_sha256=frozen['freeze_sha256'],
                 ready_sha256=ready['ready_sha256'], release_sha256=release['release_sha256'],
                 identity=ready['identity'], native_origin_verified=False,
                 compatibility_verified=False, acceptance_demonstrated=False, orders_authorized=False)
    value['result_sha256'] = payload_hash(value)
    return value


def run(root, *, execute=False):
    if execute is not True:
        raise ContractError('explicit native compatibility authorization required')
    import re
    root = Path(root)
    source = Path(__file__).resolve().parents[2]
    if (platform.system() != 'Linux' or os.geteuid() != pwd.getpwnam('qcrl').pw_uid
            or not re.fullmatch(STAGE+'/evidence', str(root))
            or root.resolve(strict=True) != root or source != root.parent/'source'
            or os.path.abspath(sys.executable) != '/opt/qcrl-stream/venv/bin/python'):
        raise ContractError('canonical qcrl Linux worker/interpreter required')
    from infra.stream.recorder_wait_production import inspect_source, observe_runtime
    from infra.stream.recorder_application_resources import LinuxReader
    frozen = validate_freeze(load(root/'execution-freeze.json'))
    sources, commit = inspect_source(source)
    runtime = observe_runtime(load(root/'runtime-review.json'), review_source=root/'select-review-source.c', execute=True)
    if sources != frozen['sources'] or commit != frozen['source_commit'] or runtime != frozen['runtime']:
        raise ContractError('worker source/runtime differs from freeze')
    reader = LinuxReader(execute=True)
    reader.read(rss=True)
    unit = 'qcrl-wait-'+root.parent.name[len('recorder-wait-'):]+'-compatibility'
    ready = dict(unit=unit, identity=reader.expected, freeze_sha256=frozen['freeze_sha256'])
    ready['ready_sha256'] = payload_hash(ready)
    publish(root/'ready.json', ready)
    deadline = time.monotonic()+15
    while not (root/'release.json').exists() and time.monotonic() < deadline:
        time.sleep(.01)
    if time.monotonic() >= deadline:
        raise ContractError('release deadline missed; no late adoption')
    release = load(root/'release.json')
    verify_artifact_hash(release, 'release_sha256', 'release')
    if release['ready_sha256'] != ready['ready_sha256'] or release['freeze_sha256'] != frozen['freeze_sha256']:
        raise ContractError('release binding differs')
    # No signal handlers installed. Native binder runs only after independent release.
    try:
        absolute = native(execute=True)
        relative = SelectWait(clock_ns=time.monotonic_ns, select_call=select.select)
        measured = collect(clock_ns=time.monotonic_ns, select_wait=relative, absolute_wait=absolute, execute=True)
    except (Exception, KeyboardInterrupt) as exc:
        measured = dict(epoch_ns=None, fatal_error=error_text(exc),
                        waits=[dict(arm=arm, observation=None, error='adapter_setup_fault_no_attempt')
                               for arm in COMPATIBILITY['arm_order']])
    result = result_object(measured, frozen, ready, release)
    publish(root/'compatibility-result.json', result)
    if measured['fatal_error'] is not None:
        raise ContractError('compatibility incomplete; evidence retained, no replay')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    run(args.root, execute=args.execute)


if __name__ == '__main__': main()
