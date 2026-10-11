import copy
from pathlib import Path
import tempfile
import unittest

from execution_truth.contracts import ContractError
from infra.stream import recorder_application_audit as audit
from infra.stream.recorder_application_worker import publish
from infra.stream.recorder_application_launch import common
from infra.stream import receive_loop_compact_audit as origin


SOURCE = '/var/lib/qcrl-stream/recorder-application-Fixture/source'
EVIDENCE = str(Path(SOURCE).parent/'evidence')
IDENTITY = dict(pid=10, process_start_id='42', cgroup='/system.slice/private.service', boot_id='boot')


def properties():
    command = common.PYTHON+' -m unittest discover -s tests -q'
    return dict(Id='private.service', User='qcrl', Group='qcrl', MemoryMax='536870912', TasksMax='32',
                NoNewPrivileges='yes', PrivateTmp='yes', ProtectSystem='strict', ProtectHome='yes',
                RemainAfterExit='yes', SubState='exited', ActiveState='active', Result='success',
                ExecMainCode='1', ExecMainStatus='0', WorkingDirectory=SOURCE, ReadWritePaths=EVIDENCE,
                ReadOnlyPaths=SOURCE, CPUQuotaPerSecUSec='750ms', RuntimeMaxUSec='4min',
                RestrictAddressFamilies='AF_INET AF_UNIX', IPAddressDeny='0.0.0.0/0 ::/0',
                IPAddressAllow='127.0.0.1/32', InaccessiblePaths='-/etc/qcrl-stream.env -/etc/qcrl-collector.env',
                ExecStart='{ path='+common.PYTHON+' ; argv[]='+command+' ; ignore_errors=no ; }',
                ExecMainStartTimestampMonotonic='1000000', ExecMainExitTimestampMonotonic='11000000', ExecMainPID='10')


class AuditTests(unittest.TestCase):
    def test_actual_unit_limits_and_command_mutations_refused(self):
        p = properties()
        result = audit.verify_unit(p, 'private', 'tests', SOURCE, EVIDENCE, identity=IDENTITY)
        self.assertEqual(result['pid'], 10)
        for key, value in [('MemoryMax', '1'), ('CPUQuotaPerSecUSec', '1s'), ('ReadWritePaths', '/'),
                           ('ExecMainStatus', '1'), ('IPAddressAllow', '0.0.0.0/0'),
                           ('InaccessiblePaths', ''), ('ExecStart', '{ argv[]=other ; }'),
                           ('ExecMainExitTimestampMonotonic', '999999999')]:
            bad = dict(p, **{key:value})
            with self.assertRaises(ContractError): audit.verify_unit(bad, 'private', 'tests', SOURCE, EVIDENCE)

    def test_live_binding_not_just_self_report(self):
        unit = dict(unit='private.service', pid=10, start=1, end=11)
        p = dict(Id='private.service', MainPID='10', ExecMainPID='10', ControlGroup=IDENTITY['cgroup'],
                 SubState='running', ActiveState='active')
        sample = dict(owner=IDENTITY, before=2.1, after=2.2, actors=[IDENTITY])
        binding = dict(unit='private.service', identity=IDENTITY, properties=p, sample=sample, begin=2, end=2.3)
        audit.verify_binding(binding, unit, IDENTITY, 'boot', 3)
        for mutation in ('pid', 'group', 'epoch', 'actor'):
            bad = copy.deepcopy(binding)
            if mutation == 'pid': bad['properties']['MainPID'] = '20'
            if mutation == 'group': bad['properties']['ControlGroup'] = '/other'
            if mutation == 'epoch': bad['end'] = 4
            if mutation == 'actor': bad['sample']['actors'] = []
            with self.assertRaises(ContractError): audit.verify_binding(bad, unit, IDENTITY, 'boot', 3)

    def test_raw_host_credit_response_matches_not_label_only(self):
        host = dict(instance_id='i-'+'1'*17, region='us-east-2', instance_type='t4g.micro', credit_mode='standard',
                    boot_id='11111111-1111-1111-1111-111111111111',
                    instance_identity_document=dict(instanceId='i-'+'1'*17, region='us-east-2', instanceType='t4g.micro'),
                    describe_instances={'Reservations':[{'Instances':[{'InstanceId':'i-'+'1'*17,
                        'InstanceType':'t4g.micro', 'Placement':{'AvailabilityZone':'us-east-2a'}}]}]},
                    describe_credit_specifications={'InstanceCreditSpecifications':[{'InstanceId':'i-'+'1'*17, 'CpuCredits':'standard'}]})
        audit.verify_host(host)
        host['credit_mode'] = 'unlimited'
        with self.assertRaises(ContractError): audit.verify_host(host)

    def test_external_origin_anchor_exact_population_and_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root/'evidence'
            evidence.mkdir()
            for name in ('launch-manifest.json', 'launch-claim.json'):
                value = publish(root/name, dict(test_only=True))
                (evidence/name).write_bytes((root/name).read_bytes())
            inventory = common.origin_inventory(evidence)
            from execution_truth.contracts import payload_hash
            from execution_truth.stream_segments import file_hash
            inventory['inventory_sha256'] = payload_hash(inventory)
            common.save_json(root/'origin-inventory.json', inventory)
            anchor = file_hash(root/'origin-inventory.json')
            origin.verify_origin(root, anchor)
            (evidence/'extra').write_text('unanchored')
            with self.assertRaises(ContractError): origin.verify_origin(root, anchor)
            with self.assertRaises(ContractError): origin.verify_origin(root, '0'*64)


if __name__ == '__main__': unittest.main()
