from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream import receive_loop_validity_launch as launch
from infra.stream import receive_loop_validity_cost as plan


class LaunchTests(unittest.TestCase):
    def test_execution_platform_and_stage_barriers(self):
        with self.assertRaises(ContractError):launch.launch('/tmp/not-a-stage')
        with patch.object(launch.platform,'system',return_value='Darwin'):
            with self.assertRaises(ContractError):launch.preflight('/tmp/not-a-stage')
        with patch.object(launch.platform,'system',return_value='Linux'),patch.object(launch.os,'geteuid',return_value=0):
            with self.assertRaises(ContractError):launch.preflight('/tmp/not-a-stage')

    def run_mock(self,root,fail=False,drift=False):
        root.mkdir();(root/'source').mkdir();(root/'preregistration.json').write_text('{}')
        before={'collectors':{},'environment_sha256':'a','public_head':'b'}
        c=dict(root=root,source=root/'source',tag='qcrl-validity-fixture',before=before,
               source_commit='a'*40,boot_id='boot',plan_sha256='b'*64,sources={},preregistration_file_sha256='c'*64)
        commands=[];captures=[]
        def command(args,**kwargs):
            commands.append(args)
            if args[0]=='install':(root/'evidence').mkdir()
            return ''
        def capture(unit,prefix):
            prefix.parent.mkdir(parents=True,exist_ok=True)
            Path(str(prefix)+'-unit.properties').write_text('fixture')
            captures.append(unit)
            return {'SubState':'exited','Result':'failed' if fail else 'success','ExecMainStatus':'1' if fail else '0'}
        def bind(unit,ready,path,boot):
            path.parent.mkdir(parents=True,exist_ok=True)
            return launch.life.save(path,dict(fixture=True,unit=unit))
        with patch.object(launch,'preflight',return_value=c),patch.object(launch.common,'command',side_effect=command), \
             patch.object(launch.common,'wait_finished'),patch.object(launch.common,'capture',side_effect=capture), \
             patch.object(launch.life,'wait',return_value={}),patch.object(launch,'bind_active',side_effect=bind), \
             patch.object(launch.common,'public_state',return_value={} if drift else before):
            if fail or drift:
                with self.assertRaises(ContractError):launch.launch(root,execute=True)
            else:launch.launch(root,execute=True)
        return commands,captures

    def test_exact_nine_case_order_quotas_and_no_external_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'fresh';commands,captures=self.run_mock(root)
            units=[a for a in commands if a[0]=='systemd-run']
            self.assertEqual(len(units),19)
            roles=[next(x for x in a if x.startswith('--property=CPUQuota=')) for a in units]
            self.assertEqual(roles,['--property=CPUQuota=75%']+['--property=CPUQuota=100%','--property=CPUQuota=25%']*9)
            self.assertEqual(len(captures),19)
            stops=[a[2] for a in commands if a[:2]==['systemctl','stop']]
            self.assertTrue(all(s.startswith('qcrl-validity-fixture-') for s in stops))
            result=launch.life.read(root/'evidence/launch-result.json')
            self.assertTrue(result['measurement_complete'])
            self.assertFalse(result['probe_cost_accepted'])
            self.assertEqual(result['completed'],[dict(round=i,lane=l) for i,ls in enumerate(plan.POLICY['order']) for l in ls])

    def test_test_gate_failure_preserved_zero_cases_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'fresh';commands,_=self.run_mock(root,fail=True)
            self.assertEqual(sum(a[0]=='systemd-run' for a in commands),1)
            self.assertEqual(launch.life.read(root/'evidence/launch-result.json')['completed'],[])
            self.assertTrue((root/'origin-inventory.json').exists())

    def test_public_drift_fails_without_restoration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'fresh';commands,_=self.run_mock(root,drift=True)
            self.assertFalse(launch.life.read(root/'evidence/launch-result.json')['measurement_complete'])
            self.assertFalse(any(a[:2]==['systemctl','restart'] for a in commands))

    def test_active_binding_requires_running_pid_and_actual_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready={'identity':dict(pid=10,boot_id='b',cgroup='/system.slice/private.service')}
            props=dict(Id='private.service',SubState='running',ActiveState='active',MainPID='10',
                       ExecMainPID='10',ControlGroup=ready['identity']['cgroup'])
            with patch.object(launch.common,'properties',return_value=('',props)):
                b=launch.bind_active('private',ready,Path(tmp)/'binding.json','b')
                self.assertEqual(b['properties']['ControlGroup'],ready['identity']['cgroup'])
            bad=dict(props);bad.pop('ControlGroup')
            with patch.object(launch.common,'properties',return_value=('',bad)):
                with self.assertRaises(ContractError):launch.bind_active('private',ready,Path(tmp)/'missing.json','b')
