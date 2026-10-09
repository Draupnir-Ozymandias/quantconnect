"""Read-only, independently anchored origin/unit audit; never launches workers."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_launch as launch, receive_loop_trial as trial
from infra.stream import receive_loop_overhead as plan


def digest(value, width=64):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{'+str(width)+'}',value):
        raise ContractError('invalid externally anchored digest')
    return value


def read_json(path):
    if path.is_symlink() or not path.is_file(): raise ContractError('regular evidence file required')
    return json.loads(path.read_text())


def verify_origin(root, expected_inventory_file_sha256):
    """Anchor to bytes learned independently from the originating host, not the local JSON."""
    root=Path(root); inventory_path=root/'origin-inventory.json'; evidence=root/'evidence'
    digest(expected_inventory_file_sha256)
    if root.is_symlink() or evidence.is_symlink() or inventory_path.is_symlink():
        raise ContractError('origin root/inventory cannot be a symlink')
    if file_hash(inventory_path)!=expected_inventory_file_sha256:
        raise ContractError('inventory bytes differ from independent origin anchor')
    inventory=read_json(inventory_path)
    verify_artifact_hash(inventory,'inventory_sha256','origin inventory')
    if set(inventory)!={'schema_version','files','inventory_sha256'} or inventory['schema_version']!='qcrl.receive_loop_launch_origin_inventory.v1':
        raise ContractError('unexpected origin inventory schema')
    files=inventory['files']
    if not isinstance(files,dict) or not 1<=len(files)<=10000: raise ContractError('origin file population invalid')
    for name,value in files.items():
        path=PurePosixPath(name)
        if (not isinstance(name,str) or path.is_absolute() or str(path)!=name
                or any(p in ('.','..') for p in path.parts) or not path.parts):
            raise ContractError('unsafe or aliased inventory path')
        digest(value)
    actual={}
    for path in evidence.rglob('*'):
        if path.is_symlink(): raise ContractError('symlink in origin evidence')
        if path.is_file(): actual[str(path.relative_to(evidence))]=file_hash(path)
    if actual!=files: raise ContractError('exact originating file population/bytes differ')
    for name in ('launch-manifest.json','launch-claim.json'):
        path=root/name
        if path.is_symlink() or file_hash(path)!=files.get(name):
            raise ContractError('outer launcher metadata differs from anchored evidence copy')
    return inventory


def parse_properties(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1024**2:
        raise ContractError('bounded regular unit properties required')
    values={}
    for line in path.read_text().splitlines():
        key,sep,value=line.partition('=')
        if not sep or not key or key in values: raise ContractError('malformed/duplicate unit properties')
        values[key]=value
    return values


def duration_us(value):
    match=re.fullmatch(r'([0-9]+)(us|ms|s|min)',value or '')
    if not match: raise ContractError('unsupported or unbounded systemd duration')
    return int(match[1])*{'us':1,'ms':1000,'s':1000000,'min':60000000}[match[2]]


def integer(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9]+',value): raise ContractError('invalid systemd integer')
    return int(value)


def verify_unit(path, role, *, expected_name=None, source=None, evidence=None, identity=None, boot_id=None):
    if role not in ('tests','producer','consumer'): raise ContractError('unsupported unit role')
    p=parse_properties(path)
    quota=1000000 if role=='producer' else 750000
    fixed={'User':'qcrl','Group':'qcrl','MemoryMax':'536870912','TasksMax':'32',
           'NoNewPrivileges':'yes','PrivateTmp':'yes','ProtectSystem':'strict','ProtectHome':'yes',
           'RemainAfterExit':'yes','SubState':'exited','ActiveState':'active','Result':'success',
           'ExecMainCode':'1','ExecMainStatus':'0'}
    if any(p.get(k)!=v for k,v in fixed.items()): raise ContractError('unit limit/security/exit properties differ')
    if duration_us(p.get('CPUQuotaPerSecUSec'))!=quota or duration_us(p.get('RuntimeMaxUSec'))!=120000000:
        raise ContractError('unit CPU/runtime limits differ')
    working=p.get('WorkingDirectory','')
    if not re.fullmatch(r'/var/lib/qcrl-stream/receive-loop-overhead-[A-Za-z0-9]+/source',working):
        raise ContractError('unit not in dedicated private source directory')
    stage=PurePosixPath(working).parent; inferred_evidence=str(stage/'evidence')
    if p.get('ReadWritePaths')!=inferred_evidence or (source is not None and working!=source) or (evidence is not None and inferred_evidence!=evidence):
        raise ContractError('unit writable/work directories differ')
    name=p.get('Id','')
    if expected_name is not None and name!=expected_name: raise ContractError('unit identity differs')
    start=integer(p.get('ExecMainStartTimestampMonotonic')); end=integer(p.get('ExecMainExitTimestampMonotonic'))
    pid=integer(p.get('ExecMainPID'))
    if not 0<start<end or end-start>120000000 or pid<=0: raise ContractError('unit timestamps/runtime/pid invalid')
    if identity is not None:
        if (identity.get('pid')!=pid or type(identity.get('pid')) is not int
                or identity.get('boot_id')!=boot_id or not isinstance(identity.get('cgroup'),str)):
            raise ContractError('worker identity does not bind to unit/boot')
        groups=[]
        for line in identity['cgroup'].splitlines():
            parts=line.split(':',2)
            if len(parts)!=3 or not parts[2].startswith('/'): raise ContractError('malformed worker cgroup')
            groups.append(parts[2])
        if not groups or not all(g.endswith('/'+name) for g in groups):
            raise ContractError('worker cgroup does not belong to recorded unit')
    peak=p.get('MemoryPeak')
    peak_bytes=None if peak in (None,'[not set]','infinity') else integer(peak)
    return {'unit':name,'pid':pid,'start_us':start,'exit_us':end,'source':working,
            'evidence':inferred_evidence,'memory_peak_bytes':peak_bytes,
            'memory_peak_scope':'whole_unit_including_post_measurement'}


def validate_window(unit,measurement):
    begin=trial.finite(measurement['begin_monotonic'])*1000000
    end=trial.finite(measurement['end_monotonic'])*1000000
    persisted=trial.finite(measurement['post_window_finished_monotonic'])*1000000
    if not unit['start_us']-1<=begin<=end<=persisted<=unit['exit_us']+1:
        raise ContractError('measurement/persistence outside actual worker lifetime')


def audit(root, *, expected_inventory_file_sha256, expected_source_commit):
    root=Path(root); evidence=root/'evidence'; repo=Path(__file__).resolve().parents[2]
    digest(expected_source_commit,40)
    inventory=verify_origin(root,expected_inventory_file_sha256)
    manifest=read_json(evidence/'launch-manifest.json')
    verify_artifact_hash(manifest,'launch_manifest_sha256','launcher manifest')
    fields={'before','source_commit','boot_id','sources','schema_version','preregistration_sha256',
            'pair_order','public_rollout_authorized','orders_authorized','launch_manifest_sha256'}
    if (set(manifest)!=fields or manifest['schema_version']!='qcrl.receive_loop_launch_manifest.v1'
            or manifest['source_commit']!=expected_source_commit
            or manifest['sources']!={name:file_hash(repo/name) for name in launch.FILES}
            or manifest['pair_order']!=plan.POLICY['pair_order']
            or manifest['public_rollout_authorized'] is not False or manifest['orders_authorized'] is not False
            or not isinstance(manifest['boot_id'],str)
            or not re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',manifest['boot_id'])):
        raise ContractError('launcher source/boot/policy binding differs')
    before=read_json(evidence/'public-before.json'); after=read_json(evidence/'public-after.json')
    if (before!=after or before!=manifest['before'] or set(before)!={'environment_sha256','public_head','collectors'}
            or before['collectors']!={n:('active' if n.endswith('.timer') else 'inactive') for n in launch.SERVICES}):
        raise ContractError('public state/configuration not preserved')
    digest(before['environment_sha256']); digest(before['public_head'],40)
    result=read_json(evidence/'launch-result.json')
    order=[{'pair':p,'lane':s} for p,lanes in enumerate(plan.POLICY['pair_order']) for s in lanes]
    result_fields={'schema_version','completed','error','preservation_errors','measurement_complete',
                   'resource_and_origin_audit_performed','overhead_acceptance_established',
                   'public_rollout_authorized','orders_authorized'}
    if (set(result)!=result_fields or result['schema_version']!='qcrl.receive_loop_launch_result.v1'
            or result['completed']!=order or result['measurement_complete'] is not True
            or not isinstance(result['completed'],list)
            or any(not isinstance(v,dict) or set(v)!={'pair','lane'} or type(v['pair']) is not int for v in result['completed'])
            or result['error'] is not None or result['preservation_errors']!=[]
            or any(result[k] is not False for k in ('resource_and_origin_audit_performed',
                'overhead_acceptance_established','public_rollout_authorized','orders_authorized'))):
        raise ContractError('finite cohort incomplete/failed or contains prior acceptance claims')
    trial_root=evidence/'trial'
    declaration=trial.burst.read(trial_root/'preregistration.json','plan_sha256')
    plan.validate(declaration,trial_root/'corpus.json')
    if declaration['plan_sha256']!=manifest['preregistration_sha256']: raise ContractError('preregistration binding differs')
    claim=read_json(evidence/'launch-claim.json')
    if (set(claim)!={'schema_version','pid','started_monotonic','boot_id','replay_authorized'}
            or claim['schema_version']!='qcrl.receive_loop_launch_claim.v1'
            or claim['boot_id']!=manifest['boot_id'] or type(claim['pid']) is not int or claim['pid']<=0
            or claim['replay_authorized'] is not False): raise ContractError('launch claim differs')
    test=verify_unit(evidence/'tests-unit.properties','tests')
    source=test['source']; original_stage=PurePosixPath(source).parent
    tag='qcrl-loop-'+original_stage.name[len('receive-loop-overhead-'):]
    if test['unit']!=tag+'-tests.service': raise ContractError('test unit prefix differs')
    if trial.finite(claim['started_monotonic'])*1000000>test['start_us']+1: raise ContractError('tests precede launcher claim')
    previous_exit=test['exit_us']; units=[test]; cases=[]
    for item in order:
        pair,selected=item['pair'],item['lane']; case=trial_root/str(pair)/selected
        ready=trial.burst.read(case/'ready.json','ready_sha256')
        delivery=trial.burst.read(case/'deliveries.json','delivery_sha256')
        producer=verify_unit(case/'producer-unit.properties','producer',source=source,evidence=test['evidence'],
            expected_name=tag+'-'+str(pair)+'-'+selected+'-producer.service',
            identity=ready['producer_identity'],boot_id=manifest['boot_id'])
        consumer=verify_unit(case/'consumer-unit.properties','consumer',source=source,evidence=test['evidence'],
            expected_name=tag+'-'+str(pair)+'-'+selected+'-consumer.service',
            identity=delivery['consumer_identity'],boot_id=manifest['boot_id'])
        if previous_exit>producer['start_us'] or producer['start_us']>consumer['start_us']:
            raise ContractError('actual worker ordering/overlap differs from fixed cohort')
        previous_exit=max(producer['exit_us'],consumer['exit_us'])
        verified=trial.verify_case(trial_root,pair,selected,require_isolation=True)
        validate_window(consumer,verified['measurement'])
        units.extend([producer,consumer]); cases.append(verified)
    if len({u['pid'] for u in units})!=13: raise ContractError('worker/test PIDs reused within finite cohort')
    if not trial.measured_order(cases): raise ContractError('consumer interval order/boot differs')
    metrics=trial.evaluate_metrics(cases)
    # Recheck the external byte anchor after expensive audits; writes or drift fail closed.
    verify_origin(root,expected_inventory_file_sha256)
    report={'schema_version':'qcrl.receive_loop_independent_audit.v1',
        'origin_inventory_file_sha256':expected_inventory_file_sha256,
        'origin_inventory_sha256':inventory['inventory_sha256'],'verified_files':len(inventory['files']),
        'launch_manifest_sha256':manifest['launch_manifest_sha256'],'source_commit':expected_source_commit,
        'units':units,'performance':metrics,'resource_and_origin_gate':'verified',
        'advancement':'diagnostic_interval_analysis_only' if metrics['metric_gate']=='pass' else metrics['metric_gate'],
        'case_bindings':[{'pair':c['pair'],'lane':c['lane'],'measurement_sha256':c['measurement_sha256'],
                          'case_report_sha256':c['case_report_sha256']} for c in cases],
        'auditor_sources':{name:file_hash(repo/name) for name in (
            'infra/stream/receive_loop_audit.py','tests/test_receive_loop_audit.py','docs/RECEIVE_LOOP_AUDIT.md')},
        'public_rollout_authorized':False,'orders_authorized':False}
    report['audit_sha256']=payload_hash(report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--expected-inventory-file-sha256',required=True)
    parser.add_argument('--expected-source-commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve(); output=args.output.resolve()
    if root==output or root in output.parents: parser.error('audit output must be outside immutable originating tree')
    result=audit(root,expected_inventory_file_sha256=args.expected_inventory_file_sha256,
                 expected_source_commit=args.expected_source_commit)
    with args.output.open('x') as handle: json.dump(result,handle,sort_keys=True,indent=2); handle.write('\n')
    print(json.dumps({'audit_sha256':result['audit_sha256'],'advancement':result['advancement']}))


if __name__=='__main__': main()
