"""Finite private Linux launcher; execution freeze required, no public mutations."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import sys
import time

from execution_truth.contracts import ContractError
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_compact_launch as common
from infra.stream.recorder_application_budget import POLICY, validate
from infra.stream.recorder_application_resources import LinuxReader
from infra.stream.recorder_application_worker import control, load, publish

ROOT = Path(__file__).resolve().parents[2]
STAGE = r'/var/lib/qcrl-stream/recorder-application-[A-Za-z0-9]+'


def sources():
    paths = list((ROOT/'infra/stream').glob('*.py')) + list((ROOT/'execution_truth').glob('*.py'))
    paths += list((ROOT/'tests/fixtures/polymarket').glob('*.json'))
    paths += list((ROOT/'tests').glob('test_recorder*.py'))
    paths += [ROOT/'tests/test_taker_replay.py', ROOT/'tests/test_execution_truth_acquisition.py',
              ROOT/'execution_truth/specs/minimum_useful_research_recorder_draft.json',
              ROOT/'docs/RECORDER_APPLICATION_BUDGET_PREREGISTRATION.md',
              ROOT/'docs/RECORDER_APPLICATION_LINUX_LAUNCHER.md']
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(set(paths))}


def runtime():
    return dict(python=platform.python_version(), machine=platform.machine(),
                system=platform.system(), websockets=importlib.metadata.version('websockets'))


def freeze(declaration, source_commit):
    validate(declaration)
    if not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ContractError('exact committed source identity required')
    return dict(schema_version='qcrl.recorder_application_execution_freeze.v1',
                plan_sha256=declaration['plan_sha256'], source_commit=source_commit,
                sources=sources(), runtime=runtime(), execution_authorized=False,
                native_smoke_verified=False, orders_authorized=False)


def unit_command(source, evidence, name, args):
    return ['systemd-run', '--unit='+name, '--working-directory='+str(source),
            '--property=User=qcrl', '--property=Group=qcrl', '--property=CPUQuota=75%',
            '--property=MemoryMax=512M', '--property=TasksMax=32', '--property=RuntimeMaxSec=240',
            '--property=RemainAfterExit=yes', '--property=NoNewPrivileges=yes',
            '--property=PrivateTmp=yes', '--property=ProtectSystem=strict', '--property=ProtectHome=yes',
            '--property=ReadWritePaths='+str(evidence), '--property=ReadOnlyPaths='+str(source),
            '--property=InaccessiblePaths=-/etc/qcrl-stream.env -/etc/qcrl-collector.env',
            '--property=IPAddressDeny=any', '--property=IPAddressAllow=127.0.0.1/32',
            '--property=RestrictAddressFamilies=AF_UNIX AF_INET', common.PYTHON, *args]


def preflight(root):
    root = Path(root)
    if platform.system() != 'Linux' or os.geteuid() != 0 or not re.fullmatch(STAGE, str(root)):
        raise ContractError('root Linux launch in a dedicated application stage required')
    source = root/'source'
    if root.resolve(strict=True) != root or source.resolve(strict=True) != source or source != ROOT:
        raise ContractError('canonical private stage/source required')
    for name in ('evidence', 'launch-claim.json', 'launch-manifest.json', 'origin-inventory.json'):
        if (root/name).exists() or (root/name).is_symlink():
            raise ContractError('never replay/adopt an existing launch')
    if os.path.abspath(sys.executable) != common.PYTHON or not Path(common.PYTHON).is_file() or shutil.disk_usage(root).free <= 4*1024**3:
        raise ContractError('fixed interpreter and four GiB free required')
    if source.stat().st_uid != pwd.getpwnam('qcrl').pw_uid:
        raise ContractError('qcrl-owned private checkout required')
    git = ['sudo', '-u', 'qcrl', 'git', '-C', str(source)]
    if common.command(git+['status', '--porcelain']).strip():
        raise ContractError('clean Git-readable checkout required')
    common.command(git+['ls-files', '--error-unmatch', *sources()])
    commit = common.command(git+['rev-parse', 'HEAD']).strip()
    for name in ('preregistration.json', 'execution-freeze.json', 'host-context.json', 'native-smoke-audit.json'):
        if (root/name).is_symlink() or not (root/name).is_file():
            raise ContractError('regular staged declaration/environment required')
        common.command(['sudo', '-u', 'qcrl', 'test', '-r', str(root/name)])
    declaration = load(root/'preregistration.json')
    execution = control(root/'execution-freeze.json')
    expected = freeze(declaration, commit)
    if {k:v for k,v in execution.items() if k != 'artifact_sha256'} != expected:
        raise ContractError('execution source/runtime freeze differs')
    host = control(root/'host-context.json')
    from infra.stream.recorder_application_audit import verify_host
    verify_host(host)
    if host['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        raise ContractError('operator-anchored host context boot differs')
    smoke = control(root/'native-smoke-audit.json')
    if (smoke.get('schema_version') != 'qcrl.recorder_application_native_compatibility.v1'
            or smoke.get('source_commit') != commit or smoke.get('sources') != sources()
            or smoke.get('runtime') != runtime() or smoke.get('plan_sha256') != declaration['plan_sha256']
            or smoke.get('compatibility_verified') is not True or smoke.get('orders_authorized') is not False):
        raise ContractError('source-bound independently verified native smoke required before cohort')
    tag = 'qcrl-application-' + root.name[len('recorder-application-'):]
    if common.command(['systemctl', 'list-units', '--all', '--full', '--no-legend', tag+'-*']).strip():
        raise ContractError('private unit prefix exists; do not adopt it')
    before = common.public_state()
    if before['collectors'] != {n: 'active' if n.endswith('.timer') else 'inactive' for n in common.SERVICES}:
        raise ContractError('public collector prerequisites differ')
    return dict(root=root, source=source, tag=tag, before=before, source_commit=commit,
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                plan_sha256=declaration['plan_sha256'], execution_sha256=execution['artifact_sha256'],
                host_context_sha256=host['artifact_sha256'], sources=sources(), runtime=runtime())


def wait_file(path, deadline):
    while time.monotonic() < deadline:
        if Path(path).exists():
            return control(path)
        time.sleep(.01)
    raise ContractError('readiness deadline missed; no adoption/retry')


def bind_active(unit, ready, path, boot):
    begin = time.monotonic()
    _, properties = common.properties(unit)
    identity = ready['identity']
    reader = LinuxReader(execute=True, pid=identity['pid'])
    sample = reader.read(rss=True)
    end = time.monotonic()
    if (reader.expected != identity or identity['boot_id'] != boot
            or properties.get('Id') != unit+'.service' or properties.get('MainPID') != str(identity['pid'])
            or properties.get('ExecMainPID') != str(identity['pid'])
            or properties.get('ControlGroup') != identity['cgroup']
            or properties.get('SubState') != 'running' or properties.get('ActiveState') != 'active'):
        raise ContractError('independent live unit/proc/cgroup binding differs')
    return publish(path, dict(unit=unit+'.service', begin=begin, end=end,
                             identity=identity, properties=properties, sample=sample))


def wait_finished(unit):
    deadline = time.monotonic()+250
    while time.monotonic() < deadline:
        _, properties = common.properties(unit)
        if properties.get('SubState') in ('exited', 'failed', 'dead'):
            return
        time.sleep(.25)
    raise ContractError('private unit exceeded finite wait')


def launch(root, *, execute=False):
    if execute is not True:
        raise ContractError('explicit finite --execute required')
    c = preflight(root)
    root, source = c['root'], c['source']
    evidence = root/'evidence'
    publish(root/'launch-claim.json', dict(pid=os.getpid(), boot_id=c['boot_id'],
            began=time.monotonic(), replay_authorized=False))
    common.command(['install', '-d', '-o', 'qcrl', '-g', 'qcrl', '-m', '750', str(evidence)])
    manifest = publish(root/'launch-manifest.json', dict(schema_version='qcrl.recorder_application_launch.v1',
        **{k:v for k,v in c.items() if k not in ('root', 'source')},
        source=str(source), evidence=str(evidence), case_order=POLICY['case_order'],
        acceptance_demonstrated=False, public_rollout_authorized=False, orders_authorized=False))
    for name in ('launch-claim.json', 'launch-manifest.json', 'preregistration.json',
                 'execution-freeze.json', 'host-context.json', 'native-smoke-audit.json'):
        with (root/name).open('rb') as src, (evidence/name).open('xb') as dst:
            shutil.copyfileobj(src, dst)
    started, captured, stopped, completed = [], set(), set(), []
    error, preservation = None, []
    def processes(name):
        with (evidence/name).open('x') as handle:
            handle.write(common.command(['ps', '-eo', 'pid,ppid,comm,pcpu']))
    def start(name, prefix, args):
        started.append((name, prefix))
        common.command(unit_command(source, evidence, name, args))
    def finish(name, prefix):
        wait_finished(name)
        values = common.capture(name, prefix)
        captured.add(name)
        if values.get('SubState') != 'exited' or values.get('Result') != 'success' or values.get('ExecMainStatus') != '0':
            raise ContractError('private unit failed: '+name)
        common.command(['systemctl', 'stop', name+'.service'])
        stopped.add(name)
    try:
        processes('host-processes-before.txt')
        tests = c['tag']+'-tests'
        start(tests, evidence/'tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-q'])
        finish(tests, evidence/'tests')
        for name in POLICY['case_order']:
            case = evidence/name
            args = ['-m', 'infra.stream.recorder_application_worker', '--root', str(case),
                    '--declaration', str(evidence/'preregistration.json'), '--execute']
            common.command(['sudo', '-u', 'qcrl', common.PYTHON, *args, 'prepare', '--case', name], cwd=str(source))
            case_info = control(case/'case.json')
            deadline = case_info['epoch']-.1
            producer, consumer = c['tag']+'-'+name+'-producer', c['tag']+'-'+name+'-consumer'
            start(producer, case/'producer', [*args, 'produce'])
            server = wait_file(case/'server-ready.json', deadline)
            pb = bind_active(producer, server, case/'producer-active.json', c['boot_id'])
            start(consumer, case/'consumer', [*args, 'consume'])
            worker = wait_file(case/'worker-ready.json', deadline)
            wait_file(case/'observer-ready.json', deadline)
            cb = bind_active(consumer, worker, case/'consumer-active.json', c['boot_id'])
            if time.monotonic() >= deadline:
                raise ContractError('live bindings missed epoch; no late adoption')
            publish(case/'bindings-ready.json', dict(case_sha256=case_info['artifact_sha256'],
                    at=time.monotonic(), producer_binding=pb['artifact_sha256'], consumer_binding=cb['artifact_sha256']))
            finish(consumer, case/'consumer')
            finish(producer, case/'producer')
            completed.append(name)
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:256])
    finally:
        for name, prefix in reversed(started):
            if name in stopped:
                continue
            try:
                if name not in captured:
                    common.capture(name, prefix)
            except Exception as exc:
                preservation.append(dict(unit=name, capture_error=type(exc).__name__))
            try:
                common.command(['systemctl', 'stop', name+'.service'])
            except Exception as exc:
                preservation.append(dict(unit=name, stop_error=type(exc).__name__))
        try:
            processes('host-processes-after.txt')
            after = common.public_state()
            if after != c['before']:
                error = error or dict(type='ContractError', message='public state changed; no automatic restoration')
            if sources() != c['sources'] or runtime() != c['runtime']:
                error = error or dict(type='ContractError', message='execution source/runtime changed; no automatic restoration')
        except Exception as exc:
            after = None
            preservation.append(dict(state_error=type(exc).__name__))
        publish(evidence/'launch-result.json', dict(completed=completed, error=error,
                preservation_errors=preservation, after=after,
                measurement_complete=completed == POLICY['case_order'] and error is None and not preservation,
                acceptance_demonstrated=False, orders_authorized=False))
        inventory = common.origin_inventory(evidence)
        # Reuse the existing exact-population verifier's generic byte-inventory format.
        from execution_truth.contracts import payload_hash
        inventory['inventory_sha256'] = payload_hash(inventory)
        common.save_json(root/'origin-inventory.json', inventory)
    if error or preservation:
        raise ContractError('finite launch failed; evidence preserved, no retry')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(launch(args.root, execute=args.execute)))


if __name__ == '__main__':
    main()
