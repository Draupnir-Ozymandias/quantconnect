from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream import recorder_application_launch as launch
from infra.stream.recorder_application_budget import POLICY
from infra.stream.recorder_application_worker import control, publish


class LauncherTests(unittest.TestCase):
    def test_explicit_platform_and_scope_guards(self):
        with self.assertRaises(ContractError): launch.launch('/tmp/not-a-stage')
        with patch.object(launch.platform, 'system', return_value='Darwin'):
            with self.assertRaises(ContractError): launch.preflight('/tmp/not-a-stage')
        with patch.object(launch.platform, 'system', return_value='Linux'), patch.object(launch.os, 'geteuid', return_value=0):
            with self.assertRaises(ContractError): launch.preflight('/tmp/not-a-stage')

    def test_unit_isolation_and_fixed_limits(self):
        args = launch.unit_command(Path('/private/source'), Path('/private/evidence'), 'private-test', ['-m', 'tests'])
        for required in ('CPUQuota=75%', 'RuntimeMaxSec=240', 'MemoryMax=512M', 'TasksMax=32',
                         'IPAddressDeny=any', 'IPAddressAllow=127.0.0.1/32',
                         'ReadOnlyPaths=/private/source', 'ReadWritePaths=/private/evidence'):
            self.assertIn('--property='+required, args)
        self.assertFalse(any('PrivateNetwork=' in a for a in args))

    def mock_launch(self, root, *, fail=False, drift=False, bind_fail=False, capture_fail=False):
        root.mkdir()
        (root/'source').mkdir()
        for name in ('preregistration.json', 'execution-freeze.json', 'host-context.json', 'native-smoke-audit.json'):
            (root/name).write_text('{}')
        before = dict(collectors={}, environment_sha256='a', public_head='b')
        c = dict(root=root, source=root/'source', tag='qcrl-application-fixture', before=before,
                 source_commit='a'*40, boot_id='boot', plan_sha256='b'*64,
                 execution_sha256='c'*64, host_context_sha256='d'*64, sources={}, runtime={})
        commands, captures = [], []
        def command(args, **kwargs):
            commands.append(args)
            if args[0] == 'install': (root/'evidence').mkdir()
            if args[0] == 'sudo' and 'prepare' in args:
                case = Path(args[args.index('--root')+1])
                case.mkdir()
                publish(case/'case.json', dict(epoch=time.monotonic()+20))
            return ''
        def capture(name, prefix):
            captures.append(name)
            if capture_fail: raise OSError('cannot preserve properties')
            Path(str(prefix)+'-unit.properties').write_text('fixture')
            return dict(SubState='exited', Result='failed' if fail else 'success', ExecMainStatus='1' if fail else '0')
        def binding(name, ready, path, boot):
            if bind_fail: raise ContractError('missing live PID')
            return publish(path, dict(unit=name, fixture=True))
        with patch.object(launch, 'preflight', return_value=c), \
             patch.object(launch.common, 'command', side_effect=command), \
             patch.object(launch, 'wait_finished'), patch.object(launch.common, 'capture', side_effect=capture), \
             patch.object(launch, 'wait_file', return_value={}), patch.object(launch, 'bind_active', side_effect=binding), \
             patch.object(launch, 'sources', return_value={}), patch.object(launch, 'runtime', return_value={}), \
             patch.object(launch.common, 'public_state', return_value={} if drift else before):
            if fail or drift or bind_fail or capture_fail:
                with self.assertRaises(ContractError): launch.launch(root, execute=True)
            else:
                launch.launch(root, execute=True)
        return commands, captures, control(root/'evidence/launch-result.json')

    def test_serial_six_cases_exact_units_and_scoped_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            commands, captures, result = self.mock_launch(Path(directory)/'fresh')
            units = [a for a in commands if a[0] == 'systemd-run']
            self.assertEqual(len(units), 13)
            self.assertEqual(len(captures), 13)
            self.assertEqual(result['completed'], POLICY['case_order'])
            self.assertTrue(result['measurement_complete'])
            self.assertFalse(result['acceptance_demonstrated'])
            stops = [a[2] for a in commands if a[:2] == ['systemctl', 'stop']]
            self.assertEqual(len(stops), 13)
            self.assertTrue(all(s.startswith('qcrl-application-fixture-') for s in stops))
            self.assertFalse(any(a[:2] == ['systemctl', 'restart'] for a in commands))

    def test_failures_preserved_no_retry_no_public_restoration(self):
        for failure in ('fail', 'bind_fail', 'capture_fail', 'drift'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'fresh'
                commands, captures, result = self.mock_launch(root, **{failure:True})
                self.assertFalse(result['measurement_complete'])
                self.assertTrue((root/'origin-inventory.json').is_file())
                if failure in ('fail', 'capture_fail'):
                    self.assertEqual(sum(a[0] == 'systemd-run' for a in commands), 1)
                if failure == 'bind_fail':
                    self.assertEqual(sum(a[0] == 'systemd-run' for a in commands), 2)
                self.assertFalse(any(a[:2] == ['systemctl', 'restart'] for a in commands))


if __name__ == '__main__': unittest.main()
