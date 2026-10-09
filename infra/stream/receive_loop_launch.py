"""Explicit finite Linux launcher; no public collector changes or offline archive audit."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_overhead as plan, receive_loop_trial as trial

PYTHON = '/opt/qcrl-stream/venv/bin/python'
PUBLIC = '/opt/qcrl-stream'
ENVIRONMENT = '/etc/qcrl-stream.env'
SERVICES = ('qcrl-collector.timer', 'qcrl-stream-pilot.service', 'qcrl-stream-observer.service')
FILES = ('infra/stream/receive_loop_launch.py', 'tests/test_receive_loop_launch.py',
         'docs/RECEIVE_LOOP_LINUX_LAUNCHER.md')


def command(args, *, cwd=None):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30,cwd=cwd).stdout


def status(name):
    # is-active uses a nonzero exit for inactive; retain that exact state.
    result = subprocess.run(['systemctl','is-active',name],capture_output=True,text=True,timeout=30)
    value = result.stdout.strip()
    if value not in ('active','inactive'): raise ContractError('collector state unavailable or transitional: '+name)
    return value


def public_state():
    return {'environment_sha256':file_hash(Path(ENVIRONMENT)),
            'public_head':command(['git','-c','safe.directory='+PUBLIC,'-C',PUBLIC,'rev-parse','HEAD']).strip(),
            'collectors':{name:status(name) for name in SERVICES}}


def preflight(root):
    root=Path(root)
    if platform.system()!='Linux' or os.geteuid()!=0:
        raise ContractError('launcher requires Linux root and explicit private staging')
    if not re.fullmatch(r'/var/lib/qcrl-stream/receive-loop-overhead-[A-Za-z0-9]+',str(root)):
        raise ContractError('launcher root must be a dedicated finite receive-loop-overhead directory')
    if root.resolve(strict=True)!=root or root.is_symlink(): raise ContractError('canonical nonsymlink stage required')
    repo=Path(__file__).resolve().parents[2]
    source=root/'source'
    if source.resolve(strict=True)!=source or repo!=source: raise ContractError('run from dedicated stage/source checkout')
    for name in ('evidence','launch-claim.json','launch-manifest.json','origin-inventory.json'):
        if (root/name).exists() or (root/name).is_symlink(): raise ContractError('do not replay or overwrite launcher evidence')
    for name in ('preregistration.json','input-corpus.json'):
        if (root/name).is_symlink() or not (root/name).is_file(): raise ContractError('staged input must be a regular file')
    if not Path(PYTHON).is_file(): raise ContractError('fixed interpreter missing')
    if shutil.disk_usage(root).free<=4*1024**3: raise ContractError('at least four GiB free required')
    git=['git','-c','safe.directory='+str(source),'-C',str(source)]
    if command(git+['status','--porcelain']).strip(): raise ContractError('measurement checkout must be clean')
    command(git+['ls-files','--error-unmatch',*FILES])
    for path in (source,root/'preregistration.json',root/'input-corpus.json'):
        command(['sudo','-u','qcrl','test','-r',str(path)])
    tag='qcrl-loop-'+root.name[len('receive-loop-overhead-'):]
    if command(['systemctl','list-units','--all','--full','--no-legend',tag+'-*']).strip():
        raise ContractError('private unit prefix already exists; never adopt or stop existing units')
    declaration=json.loads((root/'preregistration.json').read_text())
    plan.validate(declaration,root/'input-corpus.json')
    before=public_state()
    if before['collectors']!={'qcrl-collector.timer':'active','qcrl-stream-pilot.service':'inactive',
                              'qcrl-stream-observer.service':'inactive'}:
        raise ContractError('daily timer must remain active and public stream workers inactive')
    return {'root':root,'source':source,'declaration':declaration,'before':before,
            'source_commit':command(git+['rev-parse','HEAD']).strip(),
            'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'sources':{name:file_hash(source/name) for name in FILES}}


def properties(unit):
    text=command(['systemctl','show',unit+'.service'])
    values={}
    for line in text.splitlines():
        key,sep,value=line.partition('=')
        if sep:
            if key in values: raise ContractError('duplicate unit property')
            values[key]=value
    return text,values


def capture(unit,prefix):
    text,values=properties(unit)
    # All outputs are exclusive. Capture before stopping the private unit.
    with Path(str(prefix)+'-unit.properties').open('x') as handle: handle.write(text)
    with Path(str(prefix)+'-journal.txt').open('x') as handle:
        handle.write(command(['journalctl','-u',unit+'.service','--no-pager']))
    return values


def wait_finished(unit):
    deadline=time.monotonic()+130
    while time.monotonic()<deadline:
        _,values=properties(unit)
        if values.get('SubState') in ('exited','failed','dead'): return
        time.sleep(.5)
    raise ContractError('private unit wait exceeded fixed bound')


def ready(path):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        try:
            obj=json.loads(path.read_text()); trial.burst.localhost_uri(obj['uri']); return
        except (FileNotFoundError,json.JSONDecodeError): time.sleep(.05)
    raise ContractError('private producer did not become ready')


def unit_command(source,evidence,unit,quota,args):
    return ['systemd-run','--unit='+unit,'--working-directory='+str(source),
        '--property=User=qcrl','--property=Group=qcrl','--property=CPUQuota='+str(quota)+'%',
        '--property=MemoryMax=512M','--property=TasksMax=32','--property=RuntimeMaxSec=120',
        '--property=RemainAfterExit=yes','--property=NoNewPrivileges=yes',
        '--property=PrivateTmp=yes','--property=ProtectSystem=strict','--property=ProtectHome=yes',
        '--property=ReadWritePaths='+str(evidence),PYTHON,*args]


def save_json(path,obj):
    with Path(path).open('x') as handle: json.dump(obj,handle,sort_keys=True,indent=2); handle.write('\n')


def origin_inventory(root):
    files={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise ContractError('origin evidence must not contain symlinks')
        if path.is_file(): files[str(path.relative_to(root))]=file_hash(path)
    return {'schema_version':'qcrl.receive_loop_launch_origin_inventory.v1','files':files}


def launch(root, *, execute=False):
    if execute is not True: raise ContractError('launcher requires explicit --execute')
    ctx=preflight(root); root=ctx['root']; evidence=root/'evidence'
    claim={'schema_version':'qcrl.receive_loop_launch_claim.v1','pid':os.getpid(),
           'started_monotonic':time.monotonic(),'boot_id':ctx['boot_id'],'replay_authorized':False}
    save_json(root/'launch-claim.json',claim)
    command(['install','-d','-o','qcrl','-g','qcrl','-m','750',str(evidence)])
    manifest={k:v for k,v in ctx.items() if k not in ('root','source','declaration')}
    manifest.update(schema_version='qcrl.receive_loop_launch_manifest.v1',
        preregistration_sha256=ctx['declaration']['plan_sha256'],
        pair_order=plan.POLICY['pair_order'],public_rollout_authorized=False,orders_authorized=False)
    manifest['launch_manifest_sha256']=payload_hash(manifest)
    save_json(root/'launch-manifest.json',manifest)
    save_json(evidence/'launch-manifest.json',manifest)
    save_json(evidence/'launch-claim.json',claim)
    save_json(evidence/'public-before.json',ctx['before'])
    tag='qcrl-loop-'+root.name[len('receive-loop-overhead-'):]
    launched=[]; captured=set(); stopped=set(); completed=[]; error=None; preservation_errors=[]
    def finish(unit,prefix):
        wait_finished(unit)
        values=capture(unit,prefix); captured.add(unit)
        if (values.get('SubState')!='exited' or values.get('Result')!='success'
                or values.get('ExecMainStatus')!='0'):
            raise ContractError('private measurement/test unit failed: '+unit)
        command(['systemctl','stop',unit+'.service']); stopped.add(unit)
    try:
        test_unit=tag+'-tests'; launched.append((test_unit,evidence/'tests'))
        command(unit_command(ctx['source'],evidence,test_unit,75,['-m','unittest','discover','-s','tests','-q']))
        finish(test_unit,evidence/'tests')
        command(['sudo','-u','qcrl',PYTHON,'-m','infra.stream.receive_loop_trial','stage',
            '--root',str(evidence/'trial'),'--declaration',str(root/'preregistration.json'),
            '--corpus',str(root/'input-corpus.json')],cwd=str(ctx['source']))
        for pair,lanes in enumerate(plan.POLICY['pair_order']):
            for selected in lanes:
                case=evidence/'trial'/str(pair)/selected
                worker_args=['-m','infra.stream.receive_loop_trial','--root',str(evidence/'trial'),
                             '--pair',str(pair),'--lane',selected,'--execute']
                producer=tag+'-'+str(pair)+'-'+selected+'-producer'
                consumer=tag+'-'+str(pair)+'-'+selected+'-consumer'
                launched.append((producer,case/'producer'))
                command(unit_command(ctx['source'],evidence,producer,100,[*worker_args,'produce']))
                ready(case/'ready.json')
                launched.append((consumer,case/'consumer'))
                command(unit_command(ctx['source'],evidence,consumer,75,[*worker_args,'consume']))
                finish(consumer,case/'consumer'); finish(producer,case/'producer')
                completed.append({'pair':pair,'lane':selected})
    except Exception as exc:
        error={'error_type':type(exc).__name__,'message':str(exc)[:512]}
    finally:
        # Stop only our named transient units; never restore/change public services.
        for unit,prefix in reversed(launched):
            if unit in stopped: continue
            try:
                if unit not in captured:
                    prefix.parent.mkdir(parents=True,exist_ok=True)
                    capture(unit,prefix); captured.add(unit)
            except Exception as exc: preservation_errors.append({'unit':unit,'capture_error':type(exc).__name__})
            try: command(['systemctl','stop',unit+'.service'])
            except Exception as exc: preservation_errors.append({'unit':unit,'cleanup_error':type(exc).__name__})
        try:
            after=public_state(); save_json(evidence/'public-after.json',after)
            if after!=ctx['before'] and error is None:
                error={'error_type':'ContractError','message':'public collector state/configuration changed; do not restore automatically'}
        except Exception as exc: preservation_errors.append({'public_state_error':type(exc).__name__})
        save_json(evidence/'launch-result.json',{'schema_version':'qcrl.receive_loop_launch_result.v1',
            'completed':completed,'error':error,'preservation_errors':preservation_errors,
            'measurement_complete':len(completed)==6 and error is None and not preservation_errors,
            'resource_and_origin_audit_performed':False,'overhead_acceptance_established':False,
            'public_rollout_authorized':False,'orders_authorized':False})
        inventory=origin_inventory(evidence); inventory['inventory_sha256']=payload_hash(inventory)
        save_json(root/'origin-inventory.json',inventory)
    if error or preservation_errors: raise ContractError('finite launcher failed; evidence preserved, no retry')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True); parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(); result=launch(args.root,execute=args.execute)
    print(json.dumps({'launch_manifest_sha256':result['launch_manifest_sha256'],
                      'overhead_acceptance_established':False}))


if __name__=='__main__': main()
