"""Read-only origin/unit/cost audit, requiring independently obtained byte anchors."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_compact_audit as primitive
from infra.stream import receive_loop_validity_launch as launch
from infra.stream import receive_loop_validity_lifecycle as life
from infra.stream import receive_loop_validity_cost as plan
from infra.stream import receive_loop_validity_metrics as metrics


def origin(root,expected_sha):
    root=Path(root);primitive.digest(expected_sha)
    if root.is_symlink() or (root/'evidence').is_symlink():raise ContractError('origin symlink refused')
    path=root/'origin-inventory.json'
    if path.is_symlink():raise ContractError('inventory symlink refused')
    if file_hash(path)!=expected_sha:raise ContractError('origin inventory differs from external byte anchor')
    inventory=life.read(path)
    if inventory['schema_version']!='qcrl.validity_launch_inventory.v1':raise ContractError('inventory schema differs')
    recorded=inventory['files']; actual={}
    if not isinstance(recorded,dict) or not 1<=len(recorded)<=10000:raise ContractError('inventory bound differs')
    for name,digest in recorded.items():
        p=PurePosixPath(name)
        if p.is_absolute() or str(p)!=name or '..' in p.parts:raise ContractError('unsafe inventory path')
        primitive.digest(digest)
    for path in (root/'evidence').rglob('*'):
        if path.is_symlink():raise ContractError('evidence symlink refused')
        if path.is_file():actual[str(path.relative_to(root/'evidence'))]=file_hash(path)
    if actual!=recorded:raise ContractError('origin exact population/bytes differ')
    for name in ('launch-claim.json','launch-manifest.json'):
        if (root/name).is_symlink() or file_hash(root/name)!=recorded[name]:
            raise ContractError('outer metadata differs from originating copy')
    return inventory


def unit(path,role,*,name,source,identity=None,boot=None,active=None):
    if role not in ('tests','worker','observer'):raise ContractError('unknown unit role')
    p=primitive.parse_properties(path)
    fixed={'User':'qcrl','Group':'qcrl','MemoryMax':'536870912','TasksMax':'32',
           'NoNewPrivileges':'yes','PrivateTmp':'yes','ProtectSystem':'strict','ProtectHome':'yes',
           'RemainAfterExit':'yes','SubState':'exited','ActiveState':'active','Result':'success',
           'ExecMainCode':'1','ExecMainStatus':'0','Id':name,'WorkingDirectory':source,
           'ReadWritePaths':str(PurePosixPath(source).parent/'evidence')}
    if any(p.get(k)!=v for k,v in fixed.items()):raise ContractError('unit limits/security/exit/source differ')
    quota={'tests':750000,'worker':1000000,'observer':250000}[role]
    if (primitive.duration_us(p.get('CPUQuotaPerSecUSec'))!=quota
            or primitive.duration_us(p.get('RuntimeMaxUSec'))!=120000000):
        raise ContractError('unit CPU/runtime limits differ')
    if not re.fullmatch(r'/var/lib/qcrl-stream/receive-loop-validity-[A-Za-z0-9]+/source',source):
        raise ContractError('unit not in canonical validity stage')
    begin=primitive.integer(p.get('ExecMainStartTimestampMonotonic'))
    end=primitive.integer(p.get('ExecMainExitTimestampMonotonic'))
    pid=primitive.integer(p.get('ExecMainPID'))
    if not 0<begin<end or end-begin>120000000 or pid<=0:raise ContractError('unit lifetime differs')
    if identity is not None:
        group=p.get('ControlGroup')
        if active is not None:
            a=active['properties']
            if (active['schema_version']!='qcrl.validity_active_unit_binding.v1'
                    or active['unit']!=name or active['boot_id']!=boot
                    or a.get('Id')!=name or a.get('MainPID')!=str(pid)
                    or a.get('ExecMainPID')!=str(pid) or a.get('ActiveState')!='active'
                    or a.get('SubState')!='running' or a.get('ControlGroup')!=identity['cgroup']
                    or not begin-1<=active['begin']*1e6<=active['end']*1e6<=end+1):
                raise ContractError('live unit binding differs')
            group=a['ControlGroup']
            if p.get('ControlGroup') not in (None,'',group):raise ContractError('retired unit group differs from live binding')
        if (identity['pid']!=pid or identity['boot_id']!=boot
                or group!=identity['cgroup']
                or not identity['cgroup'].endswith('/'+name)):
            raise ContractError('dedicated worker PID/boot/cgroup differs')
    if role=='tests':
        expected=launch.common.PYTHON+' -m unittest discover -s tests -q'
    else:
        match=re.fullmatch(r'qcrl-validity-[A-Za-z0-9]+-([0-2])-(control|pacing|full)-'+role+r'\.service',name)
        if not match:raise ContractError('unit role/order name differs')
        expected=(launch.common.PYTHON+' -m infra.stream.receive_loop_validity_lifecycle --root '+
                  str(PurePosixPath(source).parent/'evidence/trial')+' --round '+match[1]+
                  ' --lane '+match[2]+' --execute '+role)
    if expected not in p.get('ExecStart',''):raise ContractError('actual unit command differs')
    return dict(unit=name,pid=pid,begin_us=begin,end_us=end,
                cpu_usage_ns=primitive.integer(p.get('CPUUsageNSec')))


def window(unit_info,done):
    if not unit_info['begin_us']-1<=done['begin']*1e6<=done['end']*1e6<=unit_info['end_us']+1:
        raise ContractError('measurement window outside originating unit')
    if done['cpu_seconds'] is None or done['cpu_seconds']<0:
        raise ContractError('timed CPU unavailable')
    # Bound to whole-unit CPU, allowing 1 ms accounting granularity, not subtracting costs.
    if done['cpu_seconds']*1e9>unit_info['cpu_usage_ns']+1000000:
        raise ContractError('process CPU exceeds whole-unit CPU accounting')


def audit(root,*,expected_inventory_sha,expected_commit):
    root=Path(root);primitive.digest(expected_commit,40)
    inventory=origin(root,expected_inventory_sha);e=root/'evidence'
    m=life.read(e/'launch-manifest.json');result=life.read(e/'launch-result.json')
    if (m['schema_version']!='qcrl.validity_launch_manifest.v1' or m['source_commit']!=expected_commit
            or m['sources']!=launch.sources() or m['case_order']!=plan.POLICY['order']
            or m['orders_authorized'] is not False or m['public_rollout_authorized'] is not False):
        raise ContractError('manifest source/order/authority differs')
    claim=life.read(e/'launch-claim.json')
    if claim['boot_id']!=m['boot_id'] or claim['replay_authorized'] is not False:
        raise ContractError('launch claim boot/replay differs')
    if result['after']!=m['before']:raise ContractError('public state was not preserved')
    if m['before']['collectors']!={n:('active' if n.endswith('.timer') else 'inactive') for n in launch.common.SERVICES}:
        raise ContractError('public service prerequisites differ')
    declaration=json.loads((e/'preregistration.json').read_text());plan.validate(declaration)
    if (file_hash(e/'preregistration.json')!=m['preregistration_file_sha256']
            or declaration['plan_sha256']!=m['plan_sha256']):raise ContractError('input byte/plan binding differs')
    order=[dict(round=r,lane=l) for r,lanes in enumerate(plan.POLICY['order']) for l in lanes]
    if (result['completed']!=order or result['measurement_complete'] is not True
            or result['error'] is not None or result['preservation_errors']
            or result['origin_and_resource_audited'] is not False or result['probe_cost_accepted'] is not False):
        raise ContractError('cohort incomplete/failed or contains premature acceptance')
    trial=e/'trial';impl=life.read(trial/'implementation.json')
    if impl['test_only'] is not False:raise ContractError('test fixtures cannot constitute a real cohort')
    source=str(PurePosixPath('/var/lib/qcrl-stream/receive-loop-validity-'+m['tag'][len('qcrl-validity-'):])/'source')
    tests=unit(e/'tests-unit.properties','tests',name=m['tag']+'-tests.service',source=source)
    previous=tests['end_us'];units=[tests];cases=[]
    for item in order:
        r,l=item['round'],item['lane'];case=trial/str(r)/l
        verified=life.verify_case(trial,r,l)
        worker=life.read(case/'worker-result.json');observer=life.read(case/'observer-result.json')
        done=life.read(case/'worker-done.json');ack=life.read(case/'observer-done.json')
        w=unit(case/'worker-unit.properties','worker',name=f"{m['tag']}-{r}-{l}-worker.service",source=source,
               identity=worker['identity'],boot=m['boot_id'],active=life.read(case/'worker-active.json'))
        o=unit(case/'observer-unit.properties','observer',name=f"{m['tag']}-{r}-{l}-observer.service",source=source,
               identity=observer['identity'],boot=m['boot_id'],active=life.read(case/'observer-active.json'))
        wb,ob=life.read(case/'worker-active.json'),life.read(case/'observer-active.json')
        bindings=life.read(case/'bindings-ready.json')
        if (bindings['worker_binding_sha256']!=wb['artifact_sha256'] or
                bindings['observer_binding_sha256']!=ob['artifact_sha256'] or
                wb['end']>done['begin'] or ob['end']>ack['begin']):
            raise ContractError('active bindings not sealed before measurement windows')
        if previous>w['begin_us'] or w['begin_us']>o['begin_us']:raise ContractError('actual case ordering/overlap differs')
        window(w,done);window(o,ack)
        if worker['persisted_at']*1e6>w['end_us']+1:raise ContractError('worker persistence outside unit')
        previous=max(w['end_us'],o['end_us']);units.extend([w,o])
        cases.append(dict(round=r,lane=l,metrics=metrics.case_metrics(verified,worker,observer,done,ack)))
    if len({u['pid'] for u in units})!=19:raise ContractError('unit PIDs reused')
    evaluated=metrics.evaluate(cases)
    origin(root,expected_inventory_sha)
    report=dict(schema_version='qcrl.validity_independent_cost_audit.v1',
                origin_inventory_file_sha256=expected_inventory_sha,source_commit=expected_commit,
                verified_files=len(inventory['files']),units=units,cases=cases,performance=evaluated,
                origin_and_resources='verified',probe_cost_accepted=evaluated['metric_gate']=='pass',
                advancement='separately_preregister_validity_workload' if evaluated['metric_gate']=='pass' else evaluated['metric_gate'],
                recorder_overhead_accepted=False,public_rollout_authorized=False,orders_authorized=False)
    report['audit_sha256']=payload_hash(report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--expected-inventory-sha',required=True)
    parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();root=args.root.resolve();output=args.output.resolve()
    if output==root or root in output.parents:parser.error('audit output must be outside immutable origin')
    life.save(output,audit(root,expected_inventory_sha=args.expected_inventory_sha,expected_commit=args.expected_commit))


if __name__=='__main__':main()
