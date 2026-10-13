from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream import recorder_wait_execution as envelope
from infra.stream import recorder_wait_lifecycle as lifecycle
from infra.stream.recorder_absolute_wait import AbsoluteWait
from infra.stream.recorder_wait_comparison_v2 import SelectWait


class WaitExecutionTests(unittest.TestCase):
    def runtime(self):
        return dict(system='Linux', libc='glibc', python='3.9.25', machine='aarch64',
                    gil_enabled=True, long_bits=64, pointer_bits=64,
                    timespec_size=16, tv_sec_offset=0, tv_nsec_offset=8,
                    clock_monotonic_id=1, timer_abstime=1,
                    monotonic_implementation='clock_gettime(CLOCK_MONOTONIC)',
                    clock_nanosleep_symbol='clock_nanosleep',
                    argtypes=['c_int', 'c_int', 'POINTER(Timespec)', 'c_void_p'], restype='c_int',
                    select_retry_policy=envelope.SELECT_POLICY,
                    signal_context_policy='observe_existing_handlers_no_changes',
                    kernel='fixture-kernel', libc_version='2.34', monotonic_resolution='1e-9',
                    signal_handlers='fixture-read-only-handler-context',
                    python_binary_sha256='a'*64, libc_binary_sha256='b'*64,
                    select_binary_sha256='c'*64, select_review_source_sha256='d'*64,
                    select_review_receipt_sha256='e'*64)

    def names(self):
        return sorted(envelope.DOCUMENTS | {
            'infra/stream/recorder_absolute_wait.py', 'infra/stream/recorder_wait_comparison.py',
            'infra/stream/recorder_wait_comparison_v2.py', 'infra/stream/recorder_wait_comparison_audit.py',
            'infra/stream/recorder_wait_execution.py', 'infra/stream/recorder_wait_lifecycle.py',
            'execution_truth/contracts.py', 'tests/test_recorder_wait_execution.py'})

    def freeze(self):
        return envelope.freeze(source_commit='a'*40, sources={name: 'b'*64 for name in self.names()}, runtime=self.runtime())

    def test_compatibility_hash_pin_and_no_authority(self):
        value = envelope.declaration()
        self.assertEqual(value['plan_sha256'], 'aec6f48ff1558e544cf68665c062126ce5b44366bf8c7e9e0d18ac82268fd864')
        verify_artifact_hash(value, 'plan_sha256', 'compatibility declaration')
        value['arm_order'].reverse()
        self.assertEqual(envelope.declaration()['arm_order'], ['select', 'absolute'])
        self.assertFalse(value['native_execution_authorized'])
        self.assertEqual(value['interval_ns'], 50_000_000)

    def test_inventory_selection_rejects_evidence_secrets_and_path_escape(self):
        for path in ('.env', '.qcrl/migration-receipt.json', '.git/config',
                     'infra/stream/../../.env', '/infra/stream/example.py',
                     'infra//stream/example.py', 'poly.py', 'poly2.py', 'tests/../secret.py'):
            self.assertFalse(envelope.selected(path))
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            names = self.names()
            for name in names:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
            inventory = envelope.source_inventory(root, names+['.env', '.qcrl/secret'])
            self.assertEqual(set(inventory), set(names))
            for name in names:
                self.assertEqual(inventory[name], hashlib.sha256(name.encode()).hexdigest())
            with self.assertRaises(ContractError): envelope.source_inventory(root, names[:-1])
            with self.assertRaises(ContractError): envelope.source_inventory(root, names+names[:1])

    def test_inventory_symlink_and_size_refusal(self):
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            names = self.names()
            for name in names:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture')
            target = root/names[0]
            target.unlink()
            target.symlink_to(root/names[1])
            with self.assertRaises(ContractError): envelope.source_inventory(root, names)
            target.unlink()
            with target.open('wb') as handle: handle.truncate(4*1024*1024+1)
            with self.assertRaises(ContractError): envelope.source_inventory(root, names)

    def test_freeze_exact_commit_abi_review_and_mutation_isolation(self):
        frozen = self.freeze()
        envelope.validate_freeze(frozen)
        self.assertFalse(frozen['compatibility_verified'])
        for key, bad in (('system', 'Darwin'), ('python', '3.14.6'), ('machine', 'arm64'),
                         ('tv_nsec_offset', 4), ('long_bits', 32), ('gil_enabled', 1),
                         ('select_retry_policy', 'no_retries'), ('select_review_receipt_sha256', None),
                         ('monotonic_resolution', 'nan'), ('monotonic_resolution', '-1'), ('monotonic_resolution', 'unknown')):
            runtime = self.runtime()
            runtime[key] = bad
            with self.assertRaises(ContractError): envelope.validate_runtime(runtime)
        with self.assertRaises(ContractError):
            envelope.freeze(source_commit='main', sources=frozen['sources'], runtime=self.runtime())
        bad = deepcopy(frozen)
        bad['execution_authorized'] = True
        bad.pop('freeze_sha256')
        bad['freeze_sha256'] = payload_hash(bad)
        with self.assertRaises(ContractError): envelope.validate_freeze(bad)
        runtime = self.runtime()
        copied = envelope.freeze(source_commit='a'*40, sources=frozen['sources'], runtime=runtime)
        runtime['argtypes'][0] = 'wrong'
        envelope.validate_freeze(copied)

    def test_unit_spec_fixed_limits_isolation_and_no_entrypoint(self):
        stage = '/var/lib/qcrl-stream/recorder-wait-fixture'
        for role in ('tests', 'compatibility'):
            spec = lifecycle.unit_spec(stage, role)
            self.assertIsNone(spec['worker_entrypoint'])
            self.assertFalse(spec['native_execution_authorized'])
            self.assertEqual(spec['properties']['RuntimeMaxSec'], '240')
            self.assertEqual(spec['properties']['CPUQuota'], '75%')
            self.assertEqual('IPAddressAllow' in spec['properties'], role == 'tests')
            self.assertEqual(spec['properties']['RestrictAddressFamilies'], 'AF_UNIX AF_INET' if role == 'tests' else 'AF_UNIX')
            self.assertEqual(spec['properties']['ReadWritePaths'], stage+'/evidence')
        for stage in ('/tmp/unsafe', '/var/lib/qcrl-stream/recorder-wait-../public'):
            with self.assertRaises(ContractError): lifecycle.unit_spec(stage, 'compatibility')

    def fixture(self, fault=None):
        frozen = self.freeze()
        stage = '/var/lib/qcrl-stream/recorder-wait-fixture'
        events, specs = [], {}
        preflight = dict(fresh_stage=True, clean_source=True, source_freeze_matches=True,
                         runtime_freeze_matches=True, canonical_qcrl_owner=True, fixed_interpreter=True,
                         disk_reserve_over_4_gib=True, public_prerequisites_match=True, private_units_absent=True)
        states = iter(({'public': 'unchanged'}, {'public': 'drift' if fault == 'drift' else 'unchanged'}))
        ready = None
        release = None
        def claim(stage, digest):
            events.append(('claim', stage))
            if fault == 'claim': raise FileExistsError('already claimed')
        def start(spec):
            specs[spec['unit']] = spec
            events.append(('start', spec['unit']))
            if fault == 'start': raise OSError('start failed')
        def readiness(unit, **kwargs):
            nonlocal ready
            events.append(('ready', unit))
            if fault == 'ready_timeout': raise TimeoutError('no readiness')
            ready = dict(unit=unit, freeze_sha256=frozen['freeze_sha256'],
                         identity=dict(pid=123, cgroup='/system.slice/'+unit+'.service', boot_id='fixture-boot'))
            ready['ready_sha256'] = payload_hash(ready)
            return ready
        def bind(unit, ready):
            events.append(('bind', unit))
            result = dict(unit=unit, identity=ready['identity'], active=True, observed_properties=specs[unit]['properties'])
            if fault == 'binding': result['active'] = False
            return result
        def release_call(unit, value):
            nonlocal release
            events.append(('release', unit))
            release = value
        def finish(unit, **kwargs):
            events.append(('finish', unit))
            if fault == 'timeout': raise TimeoutError('unit deadline')
        def capture(unit, **kwargs):
            events.append(('capture', unit))
            if fault == 'capture': raise OSError('cannot retain journal')
            return dict(unit=unit, result='failed' if fault == 'unit_failure' else 'success',
                        exec_status=0, substate='exited', observed_properties=specs.get(unit, {}).get('properties'))
        def result(unit, **kwargs):
            events.append(('result', unit))
            clock = SimpleNamespace(value=100)
            def select_call(*args):
                clock.value += round(args[-1]*1_000_000_000)
                return ([], [], [])
            def syscall(clock_id, flags, sec, ns):
                clock.value = sec*1_000_000_000+ns
                return 0
            select = SelectWait(clock_ns=lambda: clock.value, select_call=select_call)
            absolute = AbsoluteWait(clock_ns=lambda: clock.value, syscall=syscall)
            waits = [dict(arm='select', observation=select.wait(50_000_100, execute=True)),
                     dict(arm='absolute', observation=absolute.wait(100_000_100, execute=True))]
            value = dict(schema_version='qcrl.wait_compatibility_result.v1',
                         plan_sha256=payload_hash(envelope.COMPATIBILITY), freeze_sha256=frozen['freeze_sha256'],
                         ready_sha256=ready['ready_sha256'], release_sha256=release['release_sha256'],
                         identity=ready['identity'], epoch_ns=100, waits=waits,
                         native_origin_verified=False, compatibility_verified=False,
                         acceptance_demonstrated=False, orders_authorized=False)
            if fault == 'tamper': value['waits'][0]['observation']['internal_retry_count'] = 0
            value['result_sha256'] = payload_hash(value)
            return value
        def stop(unit):
            events.append(('stop', unit))
            if fault == 'stop': raise OSError('cannot stop')
        def recheck(*args):
            return dict(clean_source=True, source_freeze_matches=True, runtime_freeze_matches=fault != 'source_drift')
        ops = SimpleNamespace(preflight=lambda *args: preflight, claim=claim,
                              public_state=lambda: next(states), start=start, ready=readiness, bind=bind,
                              release=release_call, finish=finish, capture=capture, result=result, stop=stop,
                              recheck=recheck, publish=lambda value, **kwargs: events.append(('publish', value)))
        if fault == 'claim':
            with self.assertRaises(FileExistsError): lifecycle.rehearse(stage=stage, frozen=frozen, ops=ops, execute=True)
            return events, None
        return events, lifecycle.rehearse(stage=stage, frozen=frozen, ops=ops, execute=True)

    def test_lifecycle_success_claim_tests_readiness_release_capture_stop(self):
        events, result = self.fixture()
        self.assertTrue(result['complete'])
        self.assertFalse(result['compatibility_verified'])
        verify_artifact_hash(result, 'rehearsal_sha256', 'rehearsal')
        kinds = [event[0] for event in events]
        self.assertEqual(kinds, ['claim', 'start', 'finish', 'capture', 'stop',
                                 'start', 'ready', 'bind', 'release', 'finish', 'capture', 'result', 'stop', 'publish'])
        self.assertTrue(all('qcrl-wait-fixture-' in unit for kind, unit in events if kind in ('start', 'capture', 'stop')))

    def test_faults_stop_only_private_units_and_retain_final_receipt(self):
        for fault in ('start', 'ready_timeout', 'binding', 'timeout', 'capture',
                      'unit_failure', 'tamper', 'stop', 'drift', 'source_drift'):
            with self.subTest(fault=fault):
                events, result = self.fixture(fault)
                self.assertFalse(result['complete'])
                self.assertTrue(result['error'] or result['preservation_errors'])
                self.assertEqual(events[-1][0], 'publish')
                self.assertTrue(all('qcrl-wait-fixture-' in unit for kind, unit in events if kind == 'stop'))
                self.assertFalse(any(kind in ('restore', 'restart', 'delete') for kind, value in events))
                if fault in ('start', 'timeout', 'capture', 'unit_failure', 'stop'):
                    self.assertEqual(sum(kind == 'start' for kind, value in events), 1)

    def test_exclusive_claim_failure_and_guard_before_callbacks(self):
        events, _ = self.fixture('claim')
        self.assertEqual(len(events), 1)
        with self.assertRaises(ContractError):
            lifecycle.rehearse(stage='/tmp/unsafe', frozen=self.freeze(), ops=None)
