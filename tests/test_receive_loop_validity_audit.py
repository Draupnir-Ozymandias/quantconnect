from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_validity_audit as audit
from infra.stream import receive_loop_validity_lifecycle as life


class AuditTests(unittest.TestCase):
    def fixture(self,root):
        e=root/'evidence';e.mkdir()
        for name in ('launch-claim.json','launch-manifest.json'):
            life.save(root/name,{'fixture':True})
            (e/name).write_bytes((root/name).read_bytes())
        inventory=dict(schema_version='qcrl.validity_launch_inventory.v1',
                       files={p.name:file_hash(p) for p in e.iterdir()})
        life.save(root/'origin-inventory.json',inventory)
        return file_hash(root/'origin-inventory.json')

    def test_external_anchor_exact_population_and_outer_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);anchor=self.fixture(root)
            self.assertEqual(len(audit.origin(root,anchor)['files']),2)
            with self.assertRaises(ContractError):audit.origin(root,'0'*64)
            (root/'evidence/extra').write_text('extra')
            with self.assertRaises(ContractError):audit.origin(root,anchor)

    def test_outer_copy_and_symlink_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);anchor=self.fixture(root)
            (root/'launch-claim.json').write_text('{}')
            with self.assertRaises(ContractError):audit.origin(root,anchor)
            (root/'evidence/link').symlink_to(root/'origin-inventory.json')
            with self.assertRaises(ContractError):audit.origin(root,anchor)

    def properties(self):
        source='/var/lib/qcrl-stream/receive-loop-validity-X/source'
        name='qcrl-validity-X-0-control-worker.service'
        p=dict(User='qcrl',Group='qcrl',MemoryMax='536870912',TasksMax='32',
               NoNewPrivileges='yes',PrivateTmp='yes',ProtectSystem='strict',ProtectHome='yes',
               RemainAfterExit='yes',SubState='exited',ActiveState='active',Result='success',
               ExecMainCode='1',ExecMainStatus='0',Id=name,WorkingDirectory=source,
               ReadWritePaths='/var/lib/qcrl-stream/receive-loop-validity-X/evidence',
               CPUQuotaPerSecUSec='1s',RuntimeMaxUSec='2min',ExecMainStartTimestampMonotonic='1000000',
               ExecMainExitTimestampMonotonic='31000000',ExecMainPID='10',CPUUsageNSec='1000000000',
               ControlGroup='/system.slice/'+name,
               ExecStart='argv[]='+audit.launch.common.PYTHON+' -m infra.stream.receive_loop_validity_lifecycle --root '+
               '/var/lib/qcrl-stream/receive-loop-validity-X/evidence/trial --round 0 --lane control --execute worker ;')
        return p,source,name

    def test_unit_identity_limits_and_command(self):
        p,source,name=self.properties()
        own=dict(pid=10,boot_id='b',cgroup=p['ControlGroup'])
        with patch.object(audit.primitive,'parse_properties',return_value=p):
            out=audit.unit('fixture','worker',name=name,source=source,identity=own,boot='b')
            self.assertEqual(out['pid'],10)
        for field,value in (('CPUQuotaPerSecUSec','750ms'),('ExecMainStatus','1'),
                            ('ControlGroup','/shared'),('ExecStart','other command'),('MemoryMax','1073741824')):
            changed=dict(p);changed[field]=value
            with patch.object(audit.primitive,'parse_properties',return_value=changed):
                with self.assertRaises(ContractError):audit.unit('fixture','worker',name=name,source=source,identity=own,boot='b')

    def test_window_and_whole_unit_cpu_bound(self):
        u=dict(begin_us=1000000,end_us=31000000,cpu_usage_ns=1000000000)
        audit.window(u,dict(begin=1,end=30,cpu_seconds=.5))
        for d in (dict(begin=0,end=30,cpu_seconds=.5),dict(begin=1,end=32,cpu_seconds=.5),
                  dict(begin=1,end=30,cpu_seconds=2)):
            with self.assertRaises(ContractError):audit.window(u,d)

    def test_retired_group_requires_real_live_receipt_not_inference(self):
        p,source,name=self.properties();group=p.pop('ControlGroup')
        own=dict(pid=10,boot_id='b',cgroup=group)
        binding=dict(schema_version='qcrl.validity_active_unit_binding.v1',unit=name,boot_id='b',begin=1.1,end=1.2,
                     properties=dict(Id=name,MainPID='10',ExecMainPID='10',ActiveState='active',
                                     SubState='running',ControlGroup=group))
        with patch.object(audit.primitive,'parse_properties',return_value=p):
            with self.assertRaises(ContractError):audit.unit('fixture','worker',name=name,source=source,identity=own,boot='b')
            self.assertEqual(audit.unit('fixture','worker',name=name,source=source,identity=own,boot='b',active=binding)['pid'],10)
            binding['properties']['MainPID']='11'
            with self.assertRaises(ContractError):audit.unit('fixture','worker',name=name,source=source,identity=own,boot='b',active=binding)
