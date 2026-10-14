from copy import deepcopy
import io
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_wait_compatibility_worker as worker
from infra.stream import recorder_wait_production as production
from infra.stream import recorder_wait_lifecycle as lifecycle
from infra.stream.recorder_absolute_wait import AbsoluteWait
from infra.stream.recorder_wait_comparison_v2 import SelectWait
from tests import test_recorder_wait_execution as fixtures


class WaitWorkerTests(unittest.TestCase):
    def fixture(self, fault=None):
        clock = SimpleNamespace(value=100)
        calls = []
        def relative(*args):
            calls.append('select')
            if fault == 'eintr': raise InterruptedError('signal')
            if fault == 'interrupt': raise KeyboardInterrupt('operator')
            clock.value += round(args[-1]*1_000_000_000)+(60_000_000 if fault == 'late' else -1 if fault == 'early' else 0)
            return ([], [], [])
        def absolute(clock_id, flags, sec, ns):
            calls.append('absolute')
            clock.value = sec*1_000_000_000+ns
            return 4 if fault == 'absolute_eintr' else 0
        result = worker.collect(clock_ns=lambda: clock.value,
                                select_wait=SelectWait(clock_ns=lambda: clock.value, select_call=relative),
                                absolute_wait=AbsoluteWait(clock_ns=lambda: clock.value, syscall=absolute), execute=True)
        return result, calls

    def test_exact_two_waits_and_source_bound_result(self):
        measured, calls = self.fixture()
        self.assertEqual(calls, ['select', 'absolute'])
        self.assertEqual([row['observation']['target_ns'] for row in measured['waits']], [50_000_100, 100_000_100])
        frozen = fixtures.WaitExecutionTests().freeze()
        ready = dict(identity={'pid': 1}, ready_sha256='a'*64)
        release = dict(release_sha256='b'*64)
        value = worker.result_object(measured, frozen, ready, release)
        lifecycle.validate_compatibility(value, frozen, ready, release)
        for mutation in (lambda v: v.update(fatal_error='fault'), lambda v: v['waits'][0].update(error='collector fault')):
            changed = deepcopy(value)
            mutation(changed)
            changed.pop('result_sha256')
            changed['result_sha256'] = payload_hash(changed)
            with self.assertRaises(ContractError): lifecycle.validate_compatibility(changed, frozen, ready, release)

    def test_unknown_faults_retained_no_retry_or_second_attempt(self):
        for fault in ('eintr', 'interrupt', 'early', 'late', 'absolute_eintr'):
            measured, calls = self.fixture(fault)
            self.assertIsNotNone(measured['fatal_error'])
            self.assertEqual(len(measured['waits']), 2)
            self.assertLessEqual(len(calls), 2)
            if fault in ('eintr', 'interrupt', 'early'):
                self.assertEqual(calls, ['select'])
                self.assertIsNone(measured['waits'][1]['observation'])
            if fault == 'late':
                self.assertEqual(calls, ['select'])
                self.assertEqual(measured['waits'][1]['observation']['error'], 'target_already_missed_no_catch_up')

    def test_epoch_and_checkpoint_failure_retains_both_arm_slots(self):
        for values in ((-1,), (100, 99)):
            clock = iter(values)
            result = worker.collect(clock_ns=lambda: next(clock), select_wait=None, absolute_wait=None, execute=True)
            self.assertIsNotNone(result['fatal_error'])
            self.assertEqual(len(result['waits']), 2)
            self.assertTrue(all(row['observation'] is None for row in result['waits']))

    def test_guards_precede_io_or_native_binding(self):
        with patch.object(worker, 'native') as native, patch.object(worker, 'load') as load:
            with self.assertRaises(ContractError): worker.run('/tmp/unsafe')
            load.assert_not_called()
            native.assert_not_called()
        with patch.object(worker.platform, 'system', return_value='Darwin'), patch.object(worker, 'load') as load:
            with self.assertRaises(ContractError): worker.run('/tmp/unsafe', execute=True)
            load.assert_not_called()
        with self.assertRaises(ContractError): worker.collect(clock_ns=None, select_wait=None, absolute_wait=None)

    def test_worker_full_flow_release_setup_fault_drift_and_timeout(self):
        for fault in (None, 'setup', 'drift', 'release_timeout'):
            with self.subTest(fault=fault), TemporaryDirectory() as directory:
                stage = Path(directory).resolve()/'recorder-wait-fixture'
                root = stage/'evidence'
                root.mkdir(parents=True)
                (stage/'source').mkdir()
                frozen = fixtures.WaitExecutionTests().freeze()
                worker.publish(root/'execution-freeze.json', frozen)
                worker.publish(root/'runtime-review.json', {})
                clock = SimpleNamespace(value=100)
                def syscall(clock_id, flags, sec, ns):
                    clock.value = sec*1_000_000_000+ns
                    return 0
                absolute = AbsoluteWait(clock_ns=lambda: clock.value, syscall=syscall)
                def select_call(*args):
                    clock.value += round(args[-1]*1_000_000_000)
                    return ([], [], [])
                real_publish = worker.publish
                def publish(path, value):
                    result = real_publish(path, value)
                    if Path(path).name == 'ready.json' and fault != 'release_timeout':
                        release = dict(ready_sha256=value['ready_sha256'], freeze_sha256=frozen['freeze_sha256'], binding_sha256='a'*64)
                        release['release_sha256'] = payload_hash(release)
                        real_publish(root/'release.json', release)
                    return result
                reader = SimpleNamespace(expected=dict(pid=123, cgroup='/system.slice/qcrl-wait-fixture-compatibility.service', boot_id='boot'), read=lambda **kwargs: {})
                with patch.object(worker, '__file__', str(stage/'source/infra/stream/recorder_wait_compatibility_worker.py')), \
                     patch.object(worker, 'STAGE', str(stage)), \
                     patch.object(worker.platform, 'system', return_value='Linux'), \
                     patch.object(worker.os, 'geteuid', return_value=123), \
                     patch.object(worker.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=123)), \
                     patch.object(worker.sys, 'executable', '/opt/qcrl-stream/venv/bin/python'), \
                     patch.object(production, 'inspect_source', return_value=(frozen['sources'], frozen['source_commit'])), \
                     patch.object(production, 'observe_runtime', return_value={} if fault == 'drift' else frozen['runtime']), \
                     patch('infra.stream.recorder_application_resources.LinuxReader', return_value=reader), \
                     patch.object(worker, 'publish', side_effect=publish), \
                     patch.object(worker, 'native', side_effect=OSError('missing symbol') if fault == 'setup' else None, return_value=absolute) as binder, \
                     patch.object(worker.select, 'select', side_effect=select_call), \
                     patch.object(worker.time, 'monotonic_ns', side_effect=lambda: clock.value), \
                     patch.object(worker.time, 'monotonic', side_effect=iter((0, 16, 17)) if fault == 'release_timeout' else lambda: 0):
                    if fault:
                        with self.assertRaises(ContractError): worker.run(root, execute=True)
                    else:
                        worker.run(root, execute=True)
                    if fault in ('drift', 'release_timeout'):
                        binder.assert_not_called()
                        self.assertFalse((root/'compatibility-result.json').exists())
                    else:
                        result = worker.load(root/'compatibility-result.json')
                        self.assertEqual(len(result['waits']), 2)
                        self.assertEqual(result['fatal_error'] is None, fault is None)
                        if fault == 'setup':
                            self.assertTrue(all(row['observation'] is None for row in result['waits']))

    def test_bounded_durable_exclusive_controls_symlinks_and_partial_write(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'control.json'
            worker.publish(path, dict(small=True))
            self.assertEqual(worker.load(path), {'small': True})
            with self.assertRaises(FileExistsError): worker.publish(path, {})
            huge = root/'huge.json'
            with self.assertRaises(ContractError): worker.publish(huge, {'large': 'x'*worker.CAP})
            self.assertFalse(huge.exists())
            link = root/'link.json'
            link.symlink_to(path)
            with self.assertRaises(ContractError): worker.load(link)
            with self.assertRaises(ContractError): worker.load(path, cap=1)
            failed = root/'failed.json'
            with patch.object(worker.os, 'fsync', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError): worker.publish(failed, {'retained': True})
            self.assertTrue(failed.exists())
            with self.assertRaises(FileExistsError): worker.publish(failed, {})


class WaitProductionTests(unittest.TestCase):
    def raw_properties(self, role='compatibility'):
        spec = lifecycle.unit_spec('/var/lib/qcrl-stream/recorder-wait-fixture', role)
        raw = deepcopy(spec['properties'])
        raw.pop('CPUQuota')
        raw.pop('RuntimeMaxSec')
        raw.update(MemoryMax='536870912', CPUQuotaPerSecUSec='750ms', RuntimeMaxUSec='4min',
                   IPAddressDeny='0.0.0.0/0 ::/0')
        return spec, raw

    def test_actual_property_normalization_and_refusal(self):
        for role in ('tests', 'compatibility'):
            spec, raw = self.raw_properties(role)
            self.assertEqual(production.verified_properties(raw, spec), spec['properties'])
            for key, value in (('MemoryMax', '999999999'), ('CPUQuotaPerSecUSec', '1s'), ('RuntimeMaxUSec', '5min'),
                               ('ProtectHome', 'no'), ('ReadWritePaths', '/public'), ('IPAddressDeny', ''),
                               ('IPAddressAllow', '10.0.0.0/8'), ('RestrictAddressFamilies', 'AF_UNIX AF_INET6')):
                changed = dict(raw, **{key: value})
                with self.assertRaises(ContractError): production.verified_properties(changed, spec)
        for value in ('infinity', '', '-1s'):
            with self.assertRaises(ContractError): production.seconds(value)

    def test_bounded_helpers_success_nonzero_cap_timeout_and_no_shell(self):
        # Local helper fixtures only: no systemd/native wait or remote access.
        self.assertEqual(production.command([sys.executable, '-c', 'print("fixture")'], execute=True).strip(), 'fixture')
        with self.assertRaises(production.CommandError) as error:
            production.command([sys.executable, '-c', 'print("retained"); raise SystemExit(2)'], execute=True)
        self.assertIn(b'retained', error.exception.output)
        with self.assertRaises(production.CommandError) as error:
            production.command([sys.executable, '-c', 'print("x"*10000)'], cap=128, execute=True)
        self.assertEqual(len(error.exception.output), 128)
        with self.assertRaises(production.CommandError):
            production.command([sys.executable, '-c', 'import time; time.sleep(2)'], timeout=.05, execute=True)
        with self.assertRaises(production.CommandError) as error:
            production.command([sys.executable, '-c', 'import os; os.write(1, bytes([255]))'], execute=True)
        self.assertEqual(error.exception.output, bytes([255]))
        with patch.object(production.subprocess, 'Popen') as popen:
            with self.assertRaises(ContractError): production.command(['true'])
            with self.assertRaises(ContractError): production.command(['true'], cap=True, execute=True)
            popen.assert_not_called()

    def test_runtime_guards_and_review_fail_closed_before_library_load(self):
        with patch.object(production.ctypes, 'CDLL') as library:
            with self.assertRaises(ContractError): production.observe_runtime({}, review_source=None)
            library.assert_not_called()
        with patch.object(production.platform, 'system', return_value='Linux'), patch.object(production.ctypes, 'CDLL') as library:
            review = dict(schema_version='qcrl.installed_select_review.v1', installed_binary_verified=False)
            review['review_sha256'] = payload_hash(review)
            with self.assertRaises(ContractError): production.observe_runtime(review, review_source=None, execute=True)
            library.assert_not_called()

    def test_runtime_observation_uses_reviewed_installed_bytes_without_waits(self):
        from infra.stream.recorder_wait_execution import SELECT_POLICY
        review = dict(schema_version='qcrl.installed_select_review.v1', installed_binary_verified=True,
                      distribution_source_verified=True, retry_policy=SELECT_POLICY,
                      binary_kind='extension' if getattr(production.select, '__file__', None) else 'builtin',
                      select_binary_sha256='a'*64, source_sha256='a'*64)
        review['review_sha256'] = payload_hash(review)
        symbol = SimpleNamespace()
        with patch.object(production.platform, 'system', return_value='Linux'), \
             patch.object(production.platform, 'python_version', return_value='3.9.25'), \
             patch.object(production.platform, 'machine', return_value='aarch64'), \
             patch.object(production.platform, 'libc_ver', return_value=('glibc', '2.34')), \
             patch.object(production.platform, 'release', return_value='fixture-kernel'), \
             patch.object(Path, 'open', return_value=io.BytesIO(b'0-1 r-xp 0 0 0 /usr/lib64/libc.so.6\n')), \
             patch.object(production, 'digest', return_value='a'*64), \
             patch.object(production.ctypes, 'CDLL', return_value=SimpleNamespace(clock_nanosleep=symbol)) as library, \
             patch.object(production.time, 'CLOCK_MONOTONIC', 1), \
             patch.object(production.time, 'get_clock_info', return_value=SimpleNamespace(implementation='clock_gettime(CLOCK_MONOTONIC)', resolution=1e-9)), \
             patch.object(production.signal, 'getsignal', return_value=0), \
             patch.object(production, 'sysconfig_value', return_value=None):
            runtime = production.observe_runtime(review, review_source='fixture-source', execute=True)
            self.assertEqual(runtime['select_review_receipt_sha256'], review['review_sha256'])
            self.assertEqual(runtime['select_binary_sha256'], 'a'*64)
            self.assertEqual(runtime['tv_nsec_offset'], 8)
            library.assert_called_once_with(None)
            self.assertEqual(len(symbol.argtypes), 4)

    def test_start_maps_only_declared_roles_to_fixed_private_commands(self):
        ops = object.__new__(production.Production)
        ops.root = Path('/var/lib/qcrl-stream/recorder-wait-fixture')
        ops.evidence, ops.specs = ops.root/'evidence', {}
        commands = []
        with patch.object(production, 'command', side_effect=lambda args, **kwargs: commands.append(args)):
            for role in ('tests', 'compatibility'):
                ops.start(lifecycle.unit_spec(str(ops.root), role))
            changed = lifecycle.unit_spec(str(ops.root), 'compatibility')
            changed['unit'] = 'public-collector'
            with self.assertRaises(ContractError): ops.start(changed)
        self.assertEqual(len(commands), 2)
        self.assertIn('infra.stream.recorder_wait_compatibility_worker', commands[1])
        self.assertNotIn('infra.stream.recorder_wait_comparison_v2', commands[1])
        self.assertIn('--property=RestrictAddressFamilies=AF_UNIX', commands[1])
        self.assertFalse(any('IPAddressAllow' in arg for arg in commands[1]))

    def test_native_launch_guard_before_any_files_or_commands(self):
        with patch.object(production, 'load') as load, patch.object(production, 'command') as command:
            with self.assertRaises(ContractError): production.launch('/tmp/unsafe')
            with patch.object(production.platform, 'system', return_value='Darwin'):
                with self.assertRaises(ContractError): production.launch('/tmp/unsafe', execute=True)
            load.assert_not_called()
            command.assert_not_called()

    def ops(self, root):
        ops = object.__new__(production.Production)
        ops.root, ops.evidence, ops.frozen = root, root/'evidence', fixtures.WaitExecutionTests().freeze()
        ops.evidence.mkdir()
        spec, raw = self.raw_properties()
        ops.specs = {spec['unit']: spec}
        return ops, spec, raw

    def test_scoped_capture_retains_truncated_journal_before_stop(self):
        with TemporaryDirectory() as directory:
            ops, spec, raw = self.ops(Path(directory))
            raw.update(Result='success', ExecMainStatus='0', SubState='exited')
            with patch.object(ops, 'properties', return_value=('fixture-properties', raw)), \
                 patch.object(production, 'command', side_effect=production.CommandError('output cap exceeded', b'partial')):
                with self.assertRaises(ContractError): ops.capture(spec['unit'], max_journal_bytes=65536)
            self.assertEqual((ops.evidence/(spec['unit']+'-journal.txt')).read_bytes(), b'partial')
            self.assertTrue((ops.evidence/(spec['unit']+'-capture-error.json')).exists())
            with patch.object(production, 'command') as command:
                with self.assertRaises(ContractError): ops.stop('public-collector')
                command.assert_not_called()

    def test_claim_copy_cap_retains_partial_source_and_never_reclaims(self):
        with TemporaryDirectory() as directory:
            ops = object.__new__(production.Production)
            ops.root = Path(directory).resolve()
            ops.evidence, ops.frozen = ops.root/'evidence', fixtures.WaitExecutionTests().freeze()
            worker.publish(ops.root/'runtime-review.json', {})
            source = ops.root/'select-review-source.c'
            source.write_text('small-before-copy')
            real_open = Path.open
            def open_file(path, *args, **kwargs):
                if path == source and args and args[0] == 'rb':
                    return io.BytesIO(b'x'*(4*1024*1024+1))
                return real_open(path, *args, **kwargs)
            def install(args, **kwargs):
                ops.evidence.mkdir()
                return ''
            with patch.object(production, 'command', side_effect=install), patch.object(Path, 'open', open_file):
                with self.assertRaisesRegex(ContractError, 'copy cap'):
                    ops.claim(str(ops.root), ops.frozen['freeze_sha256'])
            self.assertTrue((ops.root/'launch-claim.json').exists())
            self.assertEqual((ops.evidence/'select-review-source.c').stat().st_size, 4*1024*1024)
            with self.assertRaises(FileExistsError): ops.claim(str(ops.root), ops.frozen['freeze_sha256'])

    def test_origin_inventory_seals_retained_files_and_rejects_symlink(self):
        with TemporaryDirectory() as directory:
            ops, spec, raw = self.ops(Path(directory))
            (ops.evidence/'partial-journal.txt').write_text('partial')
            ops.publish({'complete': False}, max_bytes=262144)
            inventory = worker.load(ops.root/'origin-inventory.json')
            self.assertIn('partial-journal.txt', inventory['files'])
            self.assertFalse(inventory['native_origin_verified'])
            with self.assertRaises(FileExistsError): ops.publish({'complete': True}, max_bytes=262144)


if __name__ == '__main__': unittest.main()
