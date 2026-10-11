"""Read-only independent origin/live-unit audit for the finite localhost cohort."""
import argparse
import json
from pathlib import Path
import re

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_compact_audit as origin
from infra.stream import recorder_application_launch as launch
from infra.stream.recorder_application_budget import POLICY, validate
from infra.stream.recorder_application_worker import control, load
from infra.stream.recorder_application_evaluator import audit_cohort, large_control, finite, outcome


def verify_host(host):
    """Raw operator-retained AWS responses; caller must separately anchor these bytes."""
    instance = host['instance_id']
    iid = host['instance_identity_document']
    if not re.fullmatch('i-[0-9a-f]{17}', instance) or not re.fullmatch('[a-z]{2}-[a-z]+-[0-9]', host['region']):
        raise ContractError('invalid declared AWS host context')
    matches = [i for r in host['describe_instances']['Reservations'] for i in r['Instances']
               if i['InstanceId'] == instance]
    credit = [r for r in host['describe_credit_specifications']['InstanceCreditSpecifications']
              if r['InstanceId'] == instance]
    if (len(matches) != 1 or len(credit) != 1 or matches[0]['InstanceType'] != host['instance_type']
            or credit[0]['CpuCredits'] != host['credit_mode'] or host['credit_mode'] not in ('standard', 'unlimited')
            or not matches[0]['Placement']['AvailabilityZone'].startswith(host['region'])):
        raise ContractError('host/credit response binding differs')
    if iid['instanceId'] != instance or iid['region'] != host['region'] or iid['instanceType'] != host['instance_type']:
        raise ContractError('retained instance identity document differs')
    if not re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', host['boot_id']):
        raise ContractError('host-context native boot unavailable')


def verify_unit(properties, name, role, source, evidence, case=None, identity=None):
    if role not in ('tests', 'producer', 'consumer'):
        raise ContractError('unknown private unit role')
    fixed = dict(Id=name+'.service', User='qcrl', Group='qcrl', MemoryMax='536870912', TasksMax='32',
                 NoNewPrivileges='yes', PrivateTmp='yes', ProtectSystem='strict', ProtectHome='yes',
                 RemainAfterExit='yes', SubState='exited', ActiveState='active', Result='success',
                 ExecMainCode='1', ExecMainStatus='0', WorkingDirectory=source, ReadWritePaths=evidence,
                 ReadOnlyPaths=source)
    if any(properties.get(k) != v for k,v in fixed.items()):
        raise ContractError('private unit identity/limit/security/exit differs')
    if (origin.duration_us(properties.get('CPUQuotaPerSecUSec')) != 750000
            or origin.duration_us(properties.get('RuntimeMaxUSec')) != 240000000):
        raise ContractError('CPU/runtime limit differs')
    if set(properties.get('RestrictAddressFamilies', '').split()) != {'AF_UNIX', 'AF_INET'}:
        raise ContractError('address-family restriction differs')
    if set(properties.get('IPAddressDeny', '').split()) != {'0.0.0.0/0', '::/0'} or properties.get('IPAddressAllow') != '127.0.0.1/32':
        raise ContractError('numeric-loopback IP restrictions differ')
    masked = {v.lstrip('-') for v in properties.get('InaccessiblePaths', '').split()}
    if masked != {'/etc/qcrl-stream.env', '/etc/qcrl-collector.env'}:
        raise ContractError('public environment masking differs')
    args = ['-m', 'unittest', 'discover', '-s', 'tests', '-q'] if role == 'tests' else [
        '-m', 'infra.stream.recorder_application_worker', '--root', evidence+'/'+case,
        '--declaration', evidence+'/preregistration.json', '--execute', 'produce' if role == 'producer' else 'consume']
    command = ' '.join([launch.common.PYTHON, *args])
    match = re.search(r'argv\[\]=(.*?) ;', properties.get('ExecStart', ''))
    if match is None or match.group(1) != command:
        raise ContractError('actual executed command differs')
    start = origin.integer(properties.get('ExecMainStartTimestampMonotonic'))
    end = origin.integer(properties.get('ExecMainExitTimestampMonotonic'))
    pid = origin.integer(properties.get('ExecMainPID'))
    if not 0 < start < end <= start+240000000 or pid <= 0:
        raise ContractError('native unit lifetime invalid')
    if identity is not None and identity['pid'] != pid:
        raise ContractError('actual unit PID differs')
    return dict(unit=name+'.service', pid=pid, start=start/1e6, end=end/1e6)


def verify_binding(binding, unit, identity, boot, epoch):
    p, s = binding['properties'], binding['sample']
    if (binding['unit'] != unit['unit'] or binding['identity'] != identity or identity['boot_id'] != boot
            or p.get('Id') != unit['unit'] or p.get('MainPID') != str(unit['pid'])
            or p.get('ExecMainPID') != str(unit['pid']) or p.get('ControlGroup') != identity['cgroup']
            or p.get('SubState') != 'running' or p.get('ActiveState') != 'active'
            or s['owner'] != identity or identity not in [{k:a[k] for k in identity} for a in s['actors']]):
        raise ContractError('independent active unit/proc binding differs')
    times = [binding['begin'], s['before'], s['after'], binding['end']]
    if (any(finite(t) != t for t in times) or times != sorted(times)
            or not unit['start'] <= times[0] <= times[-1] < epoch < unit['end']):
        raise ContractError('active binding outside native lifetime/before epoch')


def audit(root, *, expected_inventory_file_sha256, expected_source_commit,
          expected_host_context_file_sha256):
    """Anchors must come from origin SSH/AWS context, not copied JSON claims."""
    root = Path(root)
    origin.digest(expected_source_commit, 40)
    origin.digest(expected_host_context_file_sha256)
    inventory = origin.verify_origin(root, expected_inventory_file_sha256)
    evidence = root/'evidence'
    manifest = control(evidence/'launch-manifest.json')
    declaration = load(evidence/'preregistration.json')
    validate(declaration)
    frozen = control(evidence/'execution-freeze.json')
    host = control(evidence/'host-context.json')
    smoke = control(evidence/'native-smoke-audit.json')
    verify_host(host)
    if file_hash(evidence/'host-context.json') != expected_host_context_file_sha256:
        raise ContractError('host context differs from separate byte anchor')
    if (manifest['source_commit'] != expected_source_commit or frozen['source_commit'] != expected_source_commit
            or manifest['sources'] != launch.sources() or frozen['sources'] != launch.sources()
            or manifest['runtime'] != frozen['runtime'] or manifest['runtime']['system'] != 'Linux'
            or manifest['plan_sha256'] != declaration['plan_sha256'] or frozen['plan_sha256'] != declaration['plan_sha256']
            or manifest['execution_sha256'] != frozen['artifact_sha256']
            or manifest['host_context_sha256'] != host['artifact_sha256']
            or manifest['case_order'] != POLICY['case_order']
            or any(manifest[k] is not False for k in ('acceptance_demonstrated','orders_authorized','public_rollout_authorized'))
            or frozen['execution_authorized'] is not False or frozen['orders_authorized'] is not False):
        raise ContractError('launch source/runtime/authority freeze differs')
    if (smoke.get('schema_version') != 'qcrl.recorder_application_native_compatibility.v1'
            or smoke.get('source_commit') != expected_source_commit or smoke.get('sources') != launch.sources()
            or smoke.get('runtime') != manifest['runtime'] or smoke.get('plan_sha256') != declaration['plan_sha256']
            or smoke.get('compatibility_verified') is not True or smoke.get('orders_authorized') is not False):
        raise ContractError('native compatibility prerequisite differs')
    for name in ('host-processes-before.txt', 'host-processes-after.txt'):
        path = evidence/name
        if not path.is_file() or not 0 < path.stat().st_size <= 2*1024**2:
            raise ContractError('host concurrency disclosure missing/oversized')
    source, original = manifest['source'], Path(manifest['source']).parent
    if not re.fullmatch(launch.STAGE, str(original)) or source != str(original/'source') or manifest['evidence'] != str(original/'evidence'):
        raise ContractError('dedicated stage binding differs')
    result = control(evidence/'launch-result.json')
    if (result['after'] != manifest['before'] or result['completed'] != POLICY['case_order']
            or result['measurement_complete'] is not True or result['error'] is not None
            or result['preservation_errors'] != [] or result['acceptance_demonstrated'] is not False):
        raise ContractError('finite cohort failed/incomplete or public state changed')
    before = manifest['before']
    if before['collectors'] != {n:'active' if n.endswith('.timer') else 'inactive' for n in launch.common.SERVICES}:
        raise ContractError('public collector prerequisites differ')
    tag, boot = manifest['tag'], manifest['boot_id']
    if tag != 'qcrl-application-'+original.name[len('recorder-application-'):] or host['boot_id'] != boot:
        raise ContractError('private unit prefix/host-context boot differs')
    tests = verify_unit(origin.parse_properties(evidence/'tests-unit.properties'), tag+'-tests', 'tests', source, manifest['evidence'])
    claim = control(evidence/'launch-claim.json')
    if claim['boot_id'] != boot or claim['replay_authorized'] is not False or finite(claim['began']) > tests['start']:
        raise ContractError('claim/test chronology differs')
    units, previous = [tests], tests['end']
    for name in POLICY['case_order']:
        case = control(evidence/name/'case.json')
        producer = large_control(evidence/name/'producer.json')
        consumer = control(evidence/name/'consumer.json')
        for role, actor in [('producer', producer), ('consumer', consumer)]:
            unit = verify_unit(origin.parse_properties(evidence/name/(role+'-unit.properties')),
                       tag+'-'+name+'-'+role, role, source, manifest['evidence'], name, actor['identity'])
            if unit['start'] < previous:
                raise ContractError('case units overlap previous case/test lifecycle')
            binding = control(evidence/name/(role+'-active.json'))
            verify_binding(binding, unit, actor['identity'], boot, case['epoch'])
            units.append(unit)
            ready = control(evidence/name/'bindings-ready.json')
            if (ready['case_sha256'] != case['artifact_sha256'] or ready[role+'_binding'] != binding['artifact_sha256']
                    or not binding['end'] <= finite(ready['at']) < case['epoch']):
                raise ContractError('readiness release does not follow active bindings')
        if producer['identity']['cgroup'] == consumer['identity']['cgroup']:
            raise ContractError('producer and recorder share resource group')
        consumer_unit, producer_unit = units[-1], units[-2]
        for row in producer['result']['rows']:
            if not producer_unit['start'] <= finite(row['begin']) <= finite(row['end']) <= producer_unit['end']:
                raise ContractError('producer timestamps outside native unit')
        completion = large_control_completion(evidence/name/'completion.json')
        for frame in completion['frames']:
            if not consumer_unit['start'] <= finite(frame['returned']['before']) <= finite(frame['append_completed']) <= consumer_unit['end']:
                raise ContractError('completion frame outside native unit')
        for barrier in completion['barriers']:
            if not consumer_unit['start'] <= finite(barrier['begin']) <= finite(barrier['end']) <= consumer_unit['end']:
                raise ContractError('sync barrier outside native unit')
        for row in consumer['resources']['rows']:
            for sample in (row.get('sample'), row.get('cpu_before')):
                if sample and not consumer_unit['start'] <= finite(sample['before']) <= finite(sample['after']) <= consumer_unit['end']:
                    raise ContractError('resource witness outside native unit')
        previous = max(consumer_unit['end'], producer_unit['end'])
    component = audit_cohort(evidence, declaration)
    unknown = 'independent_execution_source_unit_origin_binding_not_implemented'
    unknowns = [reason for reason in component['unknowns'] if not reason.endswith(':'+unknown)]
    verdict = outcome(component['failures'], unknowns)
    # Recheck the exact anchored population after all archive/resource scans.
    origin.verify_origin(root, expected_inventory_file_sha256)
    obj = dict(schema_version='qcrl.recorder_application_independent_audit.v1',
               source_commit=expected_source_commit, origin_file_count=len(inventory['files']),
               source_files_verified=len(manifest['sources']), units=units,
               component_audit_sha256=component['audit_sha256'], failures=component['failures'],
               unknowns=unknowns, verdict=verdict, application_budget_pass=verdict=='pass',
               acceptance_scope='declared_localhost_workload_only_not_public_rollout',
               public_rollout_authorized=False, execution_authorized=False, orders_authorized=False)
    obj['audit_sha256'] = payload_hash(obj)
    return obj


def large_control_completion(path):
    with Path(path).open('rb') as handle:
        data = handle.read(32*1024**2+1)
    if len(data) > 32*1024**2:
        raise ContractError('completion file cap exceeded')
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--inventory-sha256', required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--host-context-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    from execution_truth.stream_segments import exclusive_json
    result = audit(args.root, expected_inventory_file_sha256=args.inventory_sha256,
                   expected_source_commit=args.source_commit,
                   expected_host_context_file_sha256=args.host_context_sha256)
    exclusive_json(args.output, result)
    print(json.dumps(dict(verdict=result['verdict'], audit_sha256=result['audit_sha256'])))


if __name__ == '__main__':
    main()
