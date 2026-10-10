from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream import receive_loop_compact_launch as launch


class ReceiveLoopLaunchTests(unittest.TestCase):
    def test_wrong_source_owner_rejected_before_declaration_or_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'receive-loop-compact-Test'; source=root/'source'; source.mkdir(parents=True)
            for name in ('preregistration.json','input-corpus.json'): (root/name).write_text('{}')
            with patch.object(launch.platform,'system',return_value='Linux'),patch.object(launch.os,'geteuid',return_value=0),\
                    patch.object(launch.re,'fullmatch',return_value=True),patch.object(launch,'PYTHON',sys.executable),\
                    patch.object(launch,'__file__',str(source/'infra'/'stream'/'receive_loop_compact_launch.py')),\
                    patch.object(launch.shutil,'disk_usage',return_value=launch.shutil._ntuple_diskusage(100,0,10*1024**3)),\
                    patch.object(launch,'command',return_value=''),\
                    patch.object(launch.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=source.stat().st_uid+1)),\
                    patch.object(launch.plan,'validate') as validate:
                with self.assertRaisesRegex(ContractError,'owned by qcrl'): launch.preflight(root)
                validate.assert_not_called()

    def test_no_execute_does_not_even_preflight(self):
        with patch.object(launch,'preflight') as check:
            with self.assertRaises(ContractError): launch.launch('/arbitrary')
            check.assert_not_called()

    def test_preflight_platform_and_broad_path_rejected(self):
        with patch.object(launch.platform,'system',return_value='Darwin'):
            with self.assertRaises(ContractError): launch.preflight('/tmp/example')
        with patch.object(launch.platform,'system',return_value='Linux'),patch.object(launch.os,'geteuid',return_value=0):
            for root in ('/','/var/lib/qcrl-stream','/var/lib/qcrl-stream/receive-loop-compact-abc/child',
                         '/var/lib/qcrl-stream/receive-loop-compact-../other'):
                with self.assertRaises(ContractError): launch.preflight(root)

    def test_fixed_unit_limits_and_workdir(self):
        args=launch.unit_command(Path('/stage/source'),Path('/stage/evidence'),'qcrl-compact-X',75,['-m','unit'])
        for value in ('--property=CPUQuota=75%','--property=MemoryMax=512M','--property=TasksMax=32',
                      '--property=RuntimeMaxSec=120','--property=User=qcrl','--property=NoNewPrivileges=yes',
                      '--property=ProtectSystem=strict','--property=ProtectHome=yes',
                      '--working-directory=/stage/source','--property=ReadWritePaths=/stage/evidence'):
            self.assertIn(value,args)
        self.assertIn('--property=CPUQuota=100%',launch.unit_command(Path('/s'),Path('/e'),'qcrl-compact-X',100,[]))

    def test_existing_private_unit_prefix_rejected_before_any_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'receive-loop-compact-Test'; source=root/'source'; source.mkdir(parents=True)
            for name in ('preregistration.json','input-corpus.json'): (root/name).write_text('{}')
            def command(args,**kwargs): return 'existing unit\n' if args[:2]==['systemctl','list-units'] else ''
            with patch.object(launch.platform,'system',return_value='Linux'),patch.object(launch.os,'geteuid',return_value=0),\
                    patch.object(launch.re,'fullmatch',return_value=True),patch.object(launch,'PYTHON',sys.executable),\
                    patch.object(launch,'__file__',str(source/'infra'/'stream'/'receive_loop_compact_launch.py')),\
                    patch.object(launch.shutil,'disk_usage',return_value=launch.shutil._ntuple_diskusage(100,0,10*1024**3)),\
                    patch.object(launch,'command',side_effect=command),patch.object(launch,'public_state') as public:
                with self.assertRaisesRegex(ContractError,'prefix already exists'): launch.preflight(root)
                public.assert_not_called()

    def run_fixture(self,root,*,fail=False,drift=False,capture_failure=False):
        source=root/'source'; source.mkdir()
        state={'environment_sha256':'a'*64,'public_head':'b'*40,
               'collectors':{name:('active' if name.endswith('.timer') else 'inactive') for name in launch.SERVICES}}
        ctx={'root':root,'source':source,'declaration':{'plan_sha256':'c'*64},'before':state,
             'source_commit':'d'*40,'boot_id':'testboot','sources':{'fixture':'e'*64}}
        commands=[]; units=[]
        def command(args,**kwargs):
            commands.append(args)
            if args[0]=='install': Path(args[-1]).mkdir()
            if args[0]=='sudo': (root/'evidence'/'trial').mkdir()
            if args[0]=='systemd-run':
                unit=next(a[7:] for a in args if a.startswith('--unit=')); units.append(unit)
                if args[-1] in ('produce','consume'):
                    pair=args[args.index('--pair')+1]; selected=args[args.index('--lane')+1]
                    (root/'evidence'/'trial'/pair/selected).mkdir(parents=True,exist_ok=True)
                if fail and unit.endswith('consumer'): raise subprocess.CalledProcessError(1,args)
            return 'fixture journal\n' if args[0]=='journalctl' else ''
        def properties(unit):
            if capture_failure and unit.endswith('consumer'): raise ContractError('unavailable properties')
            values={'SubState':'exited','Result':'success','ExecMainStatus':'0'}
            return '\n'.join(k+'='+v for k,v in values.items())+'\n',values
        after=dict(state,public_head='f'*40) if drift else state
        with patch.object(launch,'preflight',return_value=ctx),patch.object(launch,'command',side_effect=command),\
                patch.object(launch,'properties',side_effect=properties),patch.object(launch,'ready'),\
                patch.object(launch,'wait_finished'),patch.object(launch,'public_state',return_value=after):
            if fail or drift or capture_failure:
                with self.assertRaises(ContractError): launch.launch(root,execute=True)
            else: launch.launch(root,execute=True)
        return commands,units

    def test_six_cases_alternate_and_only_own_units_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'receive-loop-compact-Test'; root.mkdir()
            commands,units=self.run_fixture(root)
            producers=[u for u in units if u.endswith('-producer')]
            self.assertEqual(producers,['qcrl-compact-Test-'+s+'-producer' for s in (
                '0-baseline','0-instrumented','1-instrumented','1-baseline','2-baseline','2-instrumented')])
            stops=[a[-1] for a in commands if a[:2]==['systemctl','stop']]
            self.assertEqual(len(stops),13)
            self.assertTrue(all(s.startswith('qcrl-compact-Test-') for s in stops))
            # Every unit stop precedes the following systemd-run, except the concurrent producer/consumer pair.
            for pair in range(3):
                for selected in ('baseline','instrumented'):
                    producer='qcrl-compact-Test-'+str(pair)+'-'+selected+'-producer'
                    consumer=producer.replace('-producer','-consumer')
                    consumer_start=next(i for i,a in enumerate(commands) if '--unit='+consumer in a)
                    stop=commands.index(['systemctl','stop',producer+'.service'])
                    self.assertGreater(stop,consumer_start)
            result=json.loads((root/'evidence'/'launch-result.json').read_text())
            self.assertTrue(result['measurement_complete']); self.assertFalse(result['overhead_acceptance_established'])
            inventory=json.loads((root/'origin-inventory.json').read_text())
            self.assertIn('launch-manifest.json',inventory['files'])
            self.assertIn('launch-result.json',inventory['files'])

    def test_failure_preserves_evidence_stops_private_units_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'receive-loop-compact-Test'; root.mkdir()
            commands,units=self.run_fixture(root,fail=True)
            self.assertEqual(len(units),3)
            result=json.loads((root/'evidence'/'launch-result.json').read_text())
            self.assertFalse(result['measurement_complete']); self.assertEqual(result['completed'],[])
            self.assertTrue((root/'evidence'/'trial'/'0'/'baseline'/'producer-unit.properties').exists())
            self.assertTrue((root/'launch-claim.json').exists())
            self.assertTrue(all(a[-1].startswith('qcrl-compact-Test-') for a in commands if a[:2]==['systemctl','stop']))

    def test_public_drift_and_capture_failure_are_not_success(self):
        for kwargs in ({'drift':True},{'capture_failure':True}):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)/'receive-loop-compact-Test'; root.mkdir()
                commands,_=self.run_fixture(root,**kwargs)
                result=json.loads((root/'evidence'/'launch-result.json').read_text())
                self.assertFalse(result['measurement_complete'])
                self.assertFalse(any(a[:2]==['systemctl','start'] for a in commands))

    def test_origin_inventory_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'file').write_text('original'); (root/'link').symlink_to(root/'file')
            with self.assertRaises(ContractError): launch.origin_inventory(root)


if __name__=='__main__': unittest.main()
