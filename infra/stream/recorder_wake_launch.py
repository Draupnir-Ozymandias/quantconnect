"""Finite isolated Linux wake launcher. Never starts or restores public units."""
import argparse
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import sys
import time

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream import recorder_application_launch as app
from infra.stream.recorder_application_worker import control, publish
from infra.stream.recorder_wake_probe import PLAN

ROOT = Path(__file__).resolve().parents[2]
STAGE = r'/var/lib/qcrl-stream/recorder-wake-[A-Za-z0-9]+'


def sources():
    values = app.sources()
    for name in ('docs/WAKE_PROBE_PREREGISTRATION.md', 'docs/COUNTER_WAKE_DIAGNOSTICS.md',
                 'docs/WAKE_PROBE_LINUX_LAUNCHER.md'):
        values[name] = file_hash(ROOT/name)
    return values


def runtime():
    return app.runtime()


def freeze(commit):
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ContractError('exact committed wake source required')
    return dict(schema_version='qcrl.recorder_wake_execution_freeze.v1',
                plan_sha256=payload_hash(PLAN), source_commit=commit,
                sources=sources(), runtime=runtime(), orders_authorized=False,
                acceptance_demonstrated=False)


def unit_command(source, evidence, name, args, *, tests=False):
    values = app.unit_command(source, evidence, name, args)
    if not tests:
        values = [value for value in values
                  if not value.startswith('--property=IPAddressAllow=')]
        values = ['--property=RestrictAddressFamilies=AF_UNIX'
                  if value.startswith('--property=RestrictAddressFamilies=') else value
                  for value in values]
    return values


def preflight(root):
    root = Path(root)
    if platform.system() != 'Linux' or os.geteuid() != 0 or not re.fullmatch(STAGE, str(root)):
        raise ContractError('root Linux dedicated wake stage required')
    source = root/'source'
    if root.resolve(strict=True) != root or source.resolve(strict=True) != source or ROOT != source:
        raise ContractError('canonical private source checkout required')
    for name in ('evidence', 'launch-claim.json', 'origin-inventory.json'):
        if (root/name).exists() or (root/name).is_symlink():
            raise ContractError('never replay or adopt wake evidence')
    if (os.path.abspath(sys.executable) != app.common.PYTHON
            or not Path(app.common.PYTHON).is_file()
            or shutil.disk_usage(root).free <= 4*1024**3
            or source.stat().st_uid != pwd.getpwnam('qcrl').pw_uid):
        raise ContractError('fixed interpreter, private owner and disk reserve required')
    git = ['sudo', '-u', 'qcrl', 'git', '-C', str(source)]
    if app.common.command(git+['status', '--porcelain']).strip():
        raise ContractError('clean source required')
    app.common.command(git+['ls-files', '--error-unmatch', *sources()])
    commit = app.common.command(git+['rev-parse', 'HEAD']).strip()
    path = root/'execution-freeze.json'
    if path.is_symlink() or not path.is_file():
        raise ContractError('regular staged execution freeze required')
    app.common.command(['sudo', '-u', 'qcrl', 'test', '-r', str(path)])
    frozen = control(path)
    if {k:v for k,v in frozen.items() if k != 'artifact_sha256'} != freeze(commit):
        raise ContractError('source/runtime execution freeze differs')
    tag = 'qcrl-wake-'+root.name[len('recorder-wake-'):]
    if app.common.command(['systemctl', 'list-units', '--all', '--full', '--no-legend', tag+'-*']).strip():
        raise ContractError('private unit prefix already exists')
    before = app.common.public_state()
    if before['collectors'] != {n:'active' if n.endswith('.timer') else 'inactive'
                                for n in app.common.SERVICES}:
        raise ContractError('public collector prerequisites differ')
    return dict(root=root, source=source, tag=tag, before=before, sources=sources(),
                runtime=runtime(), source_commit=commit, execution_sha256=frozen['artifact_sha256'],
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def launch(root, *, execute=False):
    if execute is not True:
        raise ContractError('explicit finite wake launch required')
    c = preflight(root)
    root, source = c['root'], c['source']
    evidence = root/'evidence'
    claim = publish(root/'launch-claim.json', dict(pid=os.getpid(), boot_id=c['boot_id'],
                    began=time.monotonic(), replay_authorized=False))
    app.common.command(['install', '-d', '-o', 'qcrl', '-g', 'qcrl', '-m', '750', str(evidence)])
    publish(evidence/'launch-manifest.json', dict(
        **{k:v for k,v in c.items() if k not in ('root', 'source')},
        plan_sha256=payload_hash(PLAN), claim_sha256=claim['artifact_sha256'],
        acceptance_demonstrated=False, orders_authorized=False))
    with (root/'execution-freeze.json').open('rb') as src, (evidence/'execution-freeze.json').open('xb') as dst:
        shutil.copyfileobj(src, dst)
    started, captured, stopped = [], set(), set()
    error, preservation, after, complete = None, [], None, False
    try:
        for role in ('tests', 'probe'):
            name = c['tag']+'-'+role
            args = (['-m', 'unittest', 'discover', '-s', 'tests', '-q'] if role == 'tests'
                    else ['-m', 'infra.stream.recorder_wake_worker', '--root', str(evidence), '--execute'])
            started.append((name, role))
            app.common.command(unit_command(source, evidence, name, args, tests=role == 'tests'))
            if role == 'probe':
                ready = app.wait_file(evidence/'ready.json', time.monotonic()+12)
                bound = app.bind_active(name, ready, evidence/'probe-active.json', c['boot_id'])
                publish(evidence/'release.json', dict(ready_sha256=ready['artifact_sha256'],
                    execution_sha256=c['execution_sha256'], binding_sha256=bound['artifact_sha256']))
            app.wait_finished(name)
            values = app.common.capture(name, evidence/role)
            captured.add(name)
            if (values.get('SubState') != 'exited' or values.get('Result') != 'success'
                    or values.get('ExecMainStatus') != '0'):
                raise ContractError('private '+role+' unit failed; no retry')
            app.common.command(['systemctl', 'stop', name+'.service'])
            stopped.add(name)
        result = control(evidence/'wake-result.json')
        probe = result['probe']
        verify_artifact_hash(probe, 'probe_sha256', 'wake probe')
        release = control(evidence/'release.json')
        if (result['error'] is not None or result['execution_sha256'] != c['execution_sha256']
                or result['ready_sha256'] != ready['artifact_sha256']
                or result['release_sha256'] != release['artifact_sha256']
                or result['identity'] != ready['identity']
                or probe['plan_sha256'] != payload_hash(PLAN) or probe['plan'] != PLAN
                or len(probe['baseline']) != 16 or len(probe['rows']) != 12
                or any(row['status'] != 'observed' for row in probe['rows'])
                or probe['native_origin_verified'] is not False
                or probe['acceptance_demonstrated'] is not False
                or probe['orders_authorized'] is not False):
            raise ContractError('worker result binding differs')
        complete = True
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:256])
    finally:
        for name, role in reversed(started):
            if name in stopped:
                continue
            try:
                if name not in captured:
                    app.common.capture(name, evidence/role)
            except Exception as exc:
                preservation.append(dict(unit=name, capture_error=type(exc).__name__))
            try:
                app.common.command(['systemctl', 'stop', name+'.service'])
            except Exception as exc:
                preservation.append(dict(unit=name, stop_error=type(exc).__name__))
        try:
            after = app.common.public_state()
            if after != c['before'] or sources() != c['sources'] or runtime() != c['runtime']:
                error = error or dict(type='ContractError', message='public/source/runtime drift; no restoration')
        except Exception as exc:
            preservation.append(dict(state_error=type(exc).__name__))
        publish(evidence/'launch-result.json', dict(complete=complete and error is None and not preservation,
            error=error, preservation_errors=preservation, after=after,
            native_origin_verified=False, acceptance_demonstrated=False, orders_authorized=False))
        inventory = app.common.origin_inventory(evidence)
        inventory['inventory_sha256'] = payload_hash(inventory)
        app.common.save_json(root/'origin-inventory.json', inventory)
    if error or preservation:
        raise ContractError('wake launch failed; evidence retained, no replay')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    launch(args.root, execute=args.execute)


if __name__ == '__main__': main()
