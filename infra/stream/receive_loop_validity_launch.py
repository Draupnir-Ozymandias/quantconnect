"""Explicit finite Linux launcher; no audit acceptance or public collector changes."""
import argparse
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import time

from execution_truth.contracts import ContractError
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_compact_launch as common
from infra.stream import receive_loop_validity_lifecycle as life
from infra.stream import receive_loop_validity_cost as plan

FILES = ('infra/stream/receive_loop_validity_launch.py',
         'tests/test_receive_loop_validity_launch.py',
         'infra/stream/receive_loop_compact_launch.py',
         'infra/stream/receive_loop_validity_metrics.py',
         'tests/test_receive_loop_validity_metrics.py',
         'infra/stream/receive_loop_validity_audit.py',
         'tests/test_receive_loop_validity_audit.py',
         'infra/stream/receive_loop_compact_audit.py')


def sources():
    root=Path(__file__).resolve().parents[2]
    return dict(life.sources(), **{p:file_hash(root/p) for p in FILES})


def bind_active(unit,ready,path,boot):
    begin=time.monotonic();_,p=common.properties(unit);end=time.monotonic()
    own=ready['identity']
    if (p.get('Id')!=unit+'.service' or p.get('SubState')!='running'
            or p.get('ActiveState')!='active' or p.get('MainPID')!=str(own['pid'])
            or p.get('ExecMainPID')!=str(own['pid']) or p.get('ControlGroup')!=own['cgroup']
            or own['boot_id']!=boot):
        raise ContractError('live unit PID/boot/dedicated cgroup unavailable or differs')
    return life.save(path,dict(schema_version='qcrl.validity_active_unit_binding.v1',
                              unit=unit+'.service',boot_id=boot,begin=begin,end=end,
                              properties={k:p[k] for k in ('Id','MainPID','ExecMainPID','ControlGroup','SubState','ActiveState')}))


def preflight(root):
    root=Path(root)
    if platform.system()!='Linux' or os.geteuid()!=0:
        raise ContractError('explicit private Linux root launch required')
    if not re.fullmatch(r'/var/lib/qcrl-stream/receive-loop-validity-[A-Za-z0-9]+',str(root)):
        raise ContractError('dedicated canonical validity stage required')
    if root.resolve(strict=True)!=root or root.is_symlink(): raise ContractError('stage symlink refused')
    source=root/'source'
    if source!=Path(__file__).resolve().parents[2] or source.resolve()!=source:
        raise ContractError('run from private stage/source')
    for name in ('evidence','launch-claim.json','launch-manifest.json','origin-inventory.json'):
        if (root/name).exists() or (root/name).is_symlink(): raise ContractError('never replay/adopt prior evidence')
    if not Path(common.PYTHON).is_file() or shutil.disk_usage(root).free<=4*1024**3:
        raise ContractError('fixed interpreter and four GiB free required')
    if source.stat().st_uid!=pwd.getpwnam('qcrl').pw_uid:
        raise ContractError('qcrl-owned checkout required')
    git=['sudo','-u','qcrl','git','-C',str(source)]
    if common.command(git+['status','--porcelain']).strip(): raise ContractError('clean qcrl Git-readable source required')
    common.command(git+['ls-files','--error-unmatch',*sources(),*plan.sources()])
    input_path=root/'preregistration.json'
    if input_path.is_symlink() or not input_path.is_file(): raise ContractError('regular preregistration required')
    common.command(['sudo','-u','qcrl','test','-r',str(input_path)])
    declaration=json.loads(input_path.read_text()); plan.validate(declaration)
    tag='qcrl-validity-'+root.name[len('receive-loop-validity-'):]
    if common.command(['systemctl','list-units','--all','--full','--no-legend',tag+'-*']).strip():
        raise ContractError('private unit prefix exists; never adopt it')
    before=common.public_state()
    if before['collectors']!={n:('active' if n.endswith('.timer') else 'inactive') for n in common.SERVICES}:
        raise ContractError('public service prerequisite differs')
    return dict(root=root,source=source,tag=tag,before=before,
                source_commit=common.command(git+['rev-parse','HEAD']).strip(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                plan_sha256=declaration['plan_sha256'],sources=sources(),
                preregistration_file_sha256=file_hash(input_path))


def launch(root, *, execute=False):
    if execute is not True: raise ContractError('finite launcher requires explicit --execute')
    c=preflight(root); root=c['root']; evidence=root/'evidence'
    claim=life.save(root/'launch-claim.json',dict(pid=os.getpid(),replay_authorized=False,
                                               boot_id=c['boot_id']))
    common.command(['install','-d','-o','qcrl','-g','qcrl','-m','750',str(evidence)])
    manifest=life.save(root/'launch-manifest.json',dict(
        schema_version='qcrl.validity_launch_manifest.v1',
        **{k:v for k,v in c.items() if k not in ('root','source')},
        case_order=plan.POLICY['order'],public_rollout_authorized=False,orders_authorized=False))
    shutil.copyfile(root/'launch-claim.json',evidence/'launch-claim.json')
    shutil.copyfile(root/'launch-manifest.json',evidence/'launch-manifest.json')
    shutil.copyfile(root/'preregistration.json',evidence/'preregistration.json')
    started=[]; captured=set(); stopped=set(); completed=[]; error=None; preservation=[]
    def finish(unit,prefix):
        common.wait_finished(unit)
        p=common.capture(unit,prefix); captured.add(unit)
        if p.get('SubState')!='exited' or p.get('Result')!='success' or p.get('ExecMainStatus')!='0':
            raise ContractError('private test/worker/observer unit failed: '+unit)
        common.command(['systemctl','stop',unit+'.service']); stopped.add(unit)
    try:
        tests=c['tag']+'-tests'; started.append((tests,evidence/'tests'))
        common.command(common.unit_command(c['source'],evidence,tests,75,
                                           ['-m','unittest','discover','-s','tests','-q']))
        finish(tests,evidence/'tests')
        common.command(['sudo','-u','qcrl',common.PYTHON,'-m','infra.stream.receive_loop_validity_lifecycle',
                        'stage','--root',str(evidence/'trial')],cwd=str(c['source']))
        for round_index, lanes in enumerate(plan.POLICY['order']):
            for lane in lanes:
                case=evidence/'trial'/str(round_index)/lane
                args=['-m','infra.stream.receive_loop_validity_lifecycle','--root',str(evidence/'trial'),
                      '--round',str(round_index),'--lane',lane,'--execute']
                worker=c['tag']+'-'+str(round_index)+'-'+lane+'-worker'
                observer=c['tag']+'-'+str(round_index)+'-'+lane+'-observer'
                started.append((worker,case/'worker'))
                common.command(common.unit_command(c['source'],evidence,worker,100,[*args,'worker']))
                ready=life.wait(case/'worker-ready.json')
                wb=bind_active(worker,ready,case/'worker-active.json',c['boot_id'])
                started.append((observer,case/'observer'))
                common.command(common.unit_command(c['source'],evidence,observer,25,[*args,'observer']))
                oready=life.wait(case/'observer-ready.json')
                ob=bind_active(observer,oready,case/'observer-active.json',c['boot_id'])
                life.save(case/'bindings-ready.json',dict(worker_binding_sha256=wb['artifact_sha256'],
                          observer_binding_sha256=ob['artifact_sha256']))
                finish(observer,case/'observer'); finish(worker,case/'worker')
                completed.append({'round':round_index,'lane':lane})
    except Exception as exc:
        error={'type':type(exc).__name__,'message':str(exc)[:256]}
    finally:
        # Never touch another prefix or public units. Preserve before private cleanup.
        for unit,prefix in reversed(started):
            if unit in stopped: continue
            try:
                if unit not in captured:
                    prefix.parent.mkdir(parents=True,exist_ok=True)
                    common.capture(unit,prefix); captured.add(unit)
            except Exception as exc: preservation.append({'unit':unit,'capture_error':type(exc).__name__})
            try: common.command(['systemctl','stop',unit+'.service'])
            except Exception as exc: preservation.append({'unit':unit,'stop_error':type(exc).__name__})
        try:
            after=common.public_state()
            if after!=c['before'] and error is None:
                error={'type':'ContractError','message':'public state changed; do not restore automatically'}
        except Exception as exc:
            after=None;preservation.append({'state_error':type(exc).__name__})
        life.save(evidence/'launch-result.json',dict(completed=completed,error=error,
                  preservation_errors=preservation,after=after,
                  measurement_complete=len(completed)==9 and error is None and not preservation,
                  origin_and_resource_audited=False,probe_cost_accepted=False))
        inventory=common.origin_inventory(evidence)
        inventory['schema_version']='qcrl.validity_launch_inventory.v1'
        life.save(root/'origin-inventory.json',inventory)
    if error or preservation: raise ContractError('finite launch failed; evidence retained, no retry')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();print(json.dumps(launch(args.root,execute=args.execute)))


if __name__=='__main__':main()
