from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_wake_launch as launch
from infra.stream import recorder_wake_worker as worker
from infra.stream.recorder_application_worker import control, publish
from infra.stream.recorder_wake_probe import PLAN, collect
from tests.test_recorder_counter_schedule import Clock


class WakeLauncherTests(unittest.TestCase):
    def test_explicit_execution_platform_and_scope(self):
        with self.assertRaises(ContractError): launch.launch('/tmp/unsafe')
        with self.assertRaises(ContractError): worker.run('/tmp/unsafe')
        with patch.object(launch.platform, 'system', return_value='Darwin'):
            with self.assertRaises(ContractError): launch.preflight('/tmp/unsafe')
        with patch.object(launch.platform, 'system', return_value='Linux'), \
             patch.object(launch.os, 'geteuid', return_value=0):
            with self.assertRaises(ContractError): launch.preflight('/tmp/unsafe')

    def test_probe_network_denied_tests_only_loopback_and_fixed_limits(self):
        for tests in (True, False):
            args = launch.unit_command(Path('/private/source'), Path('/private/evidence'),
                                       'qcrl-wake-test', ['-m', 'example'], tests=tests)
            for value in ('CPUQuota=75%', 'MemoryMax=512M', 'TasksMax=32', 'RuntimeMaxSec=240',
                          'NoNewPrivileges=yes', 'ProtectSystem=strict', 'ProtectHome=yes',
                          'IPAddressDeny=any', 'ReadWritePaths=/private/evidence',
                          'ReadOnlyPaths=/private/source'):
                self.assertIn('--property='+value, args)
            self.assertEqual('--property=IPAddressAllow=127.0.0.1/32' in args, tests)
            self.assertIn('--property=RestrictAddressFamilies='+('AF_UNIX AF_INET' if tests else 'AF_UNIX'), args)

    def test_existing_stage_evidence_refused_before_commands(self):
        for marker in ('evidence', 'launch-claim.json', 'origin-inventory.json'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                (root/'source').mkdir()
                with (root/marker).open('x') as handle: handle.write('retained')
                with patch.object(launch.platform, 'system', return_value='Linux'), \
                     patch.object(launch.os, 'geteuid', return_value=0), \
                     patch.object(launch.re, 'fullmatch', return_value=True), \
                     patch.object(launch, 'ROOT', root/'source'), \
                     patch.object(launch.app.common, 'command') as command:
                    with self.assertRaisesRegex(ContractError, 'never replay'):
                        launch.preflight(root)
                    command.assert_not_called()

    def test_freeze_requires_exact_commit_and_includes_wake_sources(self):
        with self.assertRaises(ContractError): launch.freeze('main')
        with patch.object(launch, 'runtime', return_value={'fixture': True}):
            frozen = launch.freeze('a'*40)
        self.assertEqual(frozen['plan_sha256'], payload_hash(PLAN))
        self.assertIn('infra/stream/recorder_wake_worker.py', frozen['sources'])
        self.assertIn('tests/test_recorder_wake_launch.py', frozen['sources'])
        self.assertIn('docs/WAKE_PROBE_LINUX_LAUNCHER.md', frozen['sources'])

    def test_bounded_exclusive_publication_and_missing_context(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'result.json'
            worker.bounded_publish(path, dict(small=True))
            self.assertTrue(control(path)['small'])
            with self.assertRaises(FileExistsError): worker.bounded_publish(path, {})
            large = Path(directory)/'large.json'
            with self.assertRaises(ContractError):
                worker.bounded_publish(large, dict(large='x'*worker.CAP))
            self.assertFalse(large.exists())
            self.assertEqual(worker.read_context(Path(directory)/'missing')['status'], 'unknown')
            capped = Path(directory)/'context'
            with capped.open('x') as handle: handle.write('x'*8193)
            self.assertEqual(worker.read_context(capped)['error'], 'ContractError')

    def fixture(self, root, fault=None):
        root.mkdir()
        (root/'source').mkdir()
        publish(root/'execution-freeze.json', dict(fixture=True))
        before = dict(collectors={}, public_head='a', environment_sha256='b')
        c = dict(root=root, source=root/'source', tag='qcrl-wake-fixture',
                 before=before, sources={}, runtime={}, source_commit='a'*40,
                 execution_sha256='b'*64, boot_id='boot')
        commands, captures = [], []
        def command(args, **kwargs):
            commands.append(args)
            if args[0] == 'install': (root/'evidence').mkdir()
            if args[0] == 'systemd-run':
                if fault == 'start': raise OSError('start failed')
            return ''
        def wait_finished(name):
            if name.endswith('-probe'):
                clock = Clock()
                probe = collect(clock=clock.now, pause=clock.pause, execute=True)
                release = control(root/'evidence/release.json')
                publish(root/'evidence/wake-result.json', dict(error=None,
                    execution_sha256=c['execution_sha256'], ready_sha256='d'*64,
                    release_sha256=release['artifact_sha256'], identity={'pid':123}, probe=probe))
        def capture(name, prefix):
            captures.append(name)
            if fault == 'capture': raise OSError('cannot capture')
            with Path(str(prefix)+'-unit.properties').open('x') as handle: handle.write('fixture')
            return dict(SubState='exited', Result='failed' if fault == 'unit' else 'success',
                        ExecMainStatus='1' if fault == 'unit' else '0')
        def binding(*args):
            if fault == 'binding': raise ContractError('missing binding')
            return {'artifact_sha256':'c'*64}
        with patch.object(launch, 'preflight', return_value=c), \
             patch.object(launch.app.common, 'command', side_effect=command), \
             patch.object(launch.app, 'wait_finished', side_effect=wait_finished), \
             patch.object(launch.app, 'wait_file', return_value={'artifact_sha256':'d'*64, 'identity':{'pid':123}}), \
             patch.object(launch.app, 'bind_active', side_effect=binding), \
             patch.object(launch.app.common, 'capture', side_effect=capture), \
             patch.object(launch.app.common, 'public_state', return_value={} if fault == 'drift' else before), \
             patch.object(launch, 'sources', return_value={}), \
             patch.object(launch, 'runtime', return_value={}):
            if fault:
                with self.assertRaises(ContractError): launch.launch(root, execute=True)
            else:
                launch.launch(root, execute=True)
        return commands, captures, control(root/'evidence/launch-result.json')

    def test_serial_tests_probe_binding_release_and_scoped_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'fresh'
            commands, captures, result = self.fixture(root)
            units = [a for a in commands if a[0] == 'systemd-run']
            self.assertEqual(len(units), 2)
            self.assertIn('--unit=qcrl-wake-fixture-tests', units[0])
            self.assertIn('--unit=qcrl-wake-fixture-probe', units[1])
            self.assertTrue(result['complete'])
            self.assertFalse(result['native_origin_verified'])
            self.assertFalse(result['acceptance_demonstrated'])
            self.assertEqual(len(captures), 2)
            self.assertEqual(control(root/'evidence/release.json')['binding_sha256'], 'c'*64)
            self.assertTrue((root/'origin-inventory.json').is_file())

    def test_failures_retained_no_replay_or_public_restoration(self):
        for fault in ('start', 'unit', 'capture', 'binding', 'drift'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'fresh'
                commands, captures, result = self.fixture(root, fault)
                self.assertFalse(result['complete'])
                self.assertTrue((root/'origin-inventory.json').is_file())
                starts = [a for a in commands if a[0] == 'systemd-run']
                self.assertEqual(len(starts), 2 if fault in ('binding', 'drift') else 1)
                self.assertTrue(all(a[2].startswith('qcrl-wake-fixture-')
                                    for a in commands if a[:2] == ['systemctl', 'stop']))
                self.assertFalse(any(a[:2] in (['systemctl', 'restart'], ['systemctl', 'reset-failed'])
                                     for a in commands))

    def test_worker_context_outside_probe_signal_restore_and_failure_retention(self):
        for failure in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                stage = Path(directory).resolve()
                source, evidence = stage/'source', stage/'evidence'
                source.mkdir()
                evidence.mkdir()
                with (evidence/'release.json').open('x') as handle: handle.write('{}')
                frozen = dict(sources={}, runtime={}, plan_sha256=payload_hash(PLAN),
                              artifact_sha256='b'*64)
                def controls(path):
                    if Path(path).name == 'execution-freeze.json': return frozen
                    return dict(ready_sha256=control(evidence/'ready.json')['artifact_sha256'],
                                execution_sha256='b'*64, artifact_sha256='c'*64)
                events = []
                def snapshot(reader):
                    events.append('context')
                    return {'fixture': True}
                def probe(**kwargs):
                    events.append('probe')
                    if failure: raise OSError('injected probe failure')
                    clock = Clock()
                    return collect(clock=clock.now, pause=clock.pause, execute=True)
                with patch.object(worker, '__file__', str(source/'infra/stream/recorder_wake_worker.py')), \
                     patch.object(worker.platform, 'system', return_value='Linux'), \
                     patch.object(worker.os, 'geteuid', return_value=123), \
                     patch.object(worker.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=123)), \
                     patch.object(worker.re, 'fullmatch', return_value=True), \
                     patch.object(launch, 'sources', return_value={}), \
                     patch.object(launch, 'runtime', return_value={}), \
                     patch.object(worker, 'control', side_effect=controls), \
                     patch.object(worker, 'LinuxReader', return_value=SimpleNamespace(expected={'pid':123})), \
                     patch.object(worker, 'context', side_effect=snapshot), \
                     patch.object(worker, 'collect', side_effect=probe), \
                     patch.object(worker.signal, 'signal', return_value='previous') as handler:
                    if failure:
                        with self.assertRaises(ContractError): worker.run(evidence, execute=True)
                    else:
                        worker.run(evidence, execute=True)
                self.assertEqual(events, ['context', 'probe', 'context'])
                self.assertEqual(handler.call_count, 2)
                result = control(evidence/'wake-result.json')
                self.assertEqual(result['error'] is not None, failure)
                self.assertEqual(result['probe'] is None, failure)
                self.assertFalse(result['native_origin_verified'])


if __name__ == '__main__': unittest.main()
