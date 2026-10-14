from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_absolute_wait import AbsoluteWait, NS
from infra.stream import recorder_wait_comparison_native as transport
from infra.stream import recorder_wait_execution as execution
from infra.stream.recorder_wait_comparison_audit import validate_run
from infra.stream.recorder_wait_compatibility_worker import publish, load
from tests import test_recorder_wait_execution as envelope_fixtures
from tests import test_recorder_wait_comparison_v2 as comparison_fixtures


class ComparisonNativeTests(unittest.TestCase):
    stage = '/var/lib/qcrl-stream/recorder-wait-fixture'

    def frozen(self):
        old = envelope_fixtures.WaitExecutionTests().freeze()
        sources = dict(old['sources'])
        sources.update({'infra/stream/recorder_wait_comparison_native.py': 'c'*64,
                        'tests/test_recorder_wait_comparison_native.py': 'd'*64})
        return old, execution.freeze(source_commit='c'*40, sources=sources, runtime=old['runtime'])

    def fixture(self, fault=None, fatal=False, missed=False):
        _, frozen = self.frozen()
        events, specs, ready, releases = [], {}, {}, {}
        results = [comparison_fixtures.WaitComparisonV2Tests().fixture(
                   i, absolute_code=4 if fatal and i == 0 else 0,
                   select_offset=200_000_000 if missed else 0)[0] for i in (0, 1)]
        checks = dict(fresh_stage=True, clean_source=True, source_freeze_matches=True,
                      runtime_freeze_matches=True, canonical_qcrl_owner=True, fixed_interpreter=True,
                      disk_reserve_over_4_gib=True, public_prerequisites_match=True, private_units_absent=True)
        state = dict(collectors={name:'active' if name.endswith('.timer') else 'inactive' for name in transport.SERVICES},
                     environment_sha256='a'*64, public_head='b'*40)
        final = {}

        def hit(name, unit=None):
            events.append((name, unit))
            if fault == name:
                raise OSError(name+' fault')

        def preflight(stage, value):
            hit('preflight')
            return checks

        def claim(stage, digest):
            hit('claim')

        def start(spec):
            specs[spec['unit']] = spec
            hit('start', spec['unit'])

        def readiness(unit, **bounds):
            hit('ready', unit)
            self.assertEqual(bounds, dict(timeout_seconds=12, max_bytes=262144))
            r = dict(unit=unit, run_index=specs[unit]['run_index'], plan_sha256=payload_hash(transport.PLAN),
                     freeze_sha256=frozen['freeze_sha256'],
                     identity=dict(pid=100, boot_id='fixture', process_start_id='fixture',
                                   cgroup='/system.slice/'+unit+'.service'))
            if fault == 'ready_index':
                r['run_index'] = 1-r['run_index']
            r['ready_sha256'] = payload_hash(r)
            ready[unit] = r
            return r

        def bind(unit, r):
            hit('bind', unit)
            return dict(unit=unit, identity=r['identity'], active=fault != 'inactive',
                        observed_properties=specs[unit]['properties'])

        def release(unit, value):
            hit('release', unit)
            releases[unit] = value

        def capture(unit, **bounds):
            hit('capture', unit)
            self.assertEqual(bounds, dict(max_journal_bytes=65536))
            return dict(unit=unit, result='failed' if fault == 'test_failure' else 'success',
                        exec_status=0, substate='exited', observed_properties=specs[unit]['properties'])

        def finish(unit, **bounds):
            hit('finish', unit)
            self.assertEqual(bounds, dict(timeout_seconds=240))

        def result(index):
            hit('result', index)
            unit = transport.comparison_spec(self.stage, index)['unit']
            r = results[index]
            e = dict(schema_version='qcrl.wait_comparison_native_envelope.v1', run_index=index,
                     run_sha256=r['run_sha256'], identity=ready[unit]['identity'],
                     ready_sha256=ready[unit]['ready_sha256'], release_sha256=releases[unit]['release_sha256'],
                     freeze_sha256=frozen['freeze_sha256'], native_origin_verified=False,
                     acceptance_demonstrated=False, orders_authorized=False)
            if fault == 'envelope':
                e['run_sha256'] = 'f'*64
            e['envelope_sha256'] = payload_hash(e)
            return r, e

        def recheck(stage, value):
            hit('recheck')
            return dict(clean_source=True, source_freeze_matches=True, runtime_freeze_matches=fault != 'drift')

        def save(value):
            hit('publish')
            final.update(value)

        ops = SimpleNamespace(preflight=preflight, claim=claim, public_state=lambda: deepcopy(state),
                              start=start, activate=lambda index: hit('activate', index), ready=readiness,
                              bind=bind, release=release, finish=finish, capture=capture,
                              comparison_result=result, stop=lambda unit: hit('stop', unit),
                              select_evidence=lambda spec: None, recheck=recheck,
                              cancel=lambda value: hit('cancel', value['run_index']), publish_comparison=save)
        return frozen, ops, events, final

    def test_success_fixed_order_limits_and_fresh_release_per_run(self):
        frozen, ops, events, report = self.fixture()
        result = transport.execute_pair(self.stage, frozen, ops, execute=True)
        self.assertTrue(result['complete'])
        self.assertEqual(result['unknown_cells'], [])
        self.assertTrue(result['summary']['comparison_complete'])
        self.assertEqual([item for name, item in events if name == 'start'],
                         ['qcrl-wait-fixture-tests', 'qcrl-wait-fixture-comparison-0', 'qcrl-wait-fixture-comparison-1'])
        self.assertLess(events.index(('result', 0)), events.index(('activate', 1)))
        self.assertFalse(result['native_origin_verified'])
        for index in (0, 1):
            spec = transport.comparison_spec(self.stage, index)
            self.assertEqual(spec['properties']['CPUQuota'], '75%')
            self.assertEqual(spec['properties']['RuntimeMaxSec'], '240')
            self.assertEqual(spec['properties']['MemoryMax'], '512M')
            self.assertEqual(spec['properties']['TasksMax'], '32')
            self.assertEqual(spec['properties']['RestrictAddressFamilies'], 'AF_UNIX')
            self.assertEqual(spec['properties']['ReadWritePaths'], self.stage+'/evidence/run-'+str(index))
            self.assertNotIn('IPAddressAllow', spec['properties'])

    def test_run_zero_interrupt_cancels_second_without_start(self):
        frozen, ops, events, _ = self.fixture(fatal=True)
        result = transport.execute_pair(self.stage, frozen, ops, execute=True)
        self.assertTrue(result['complete'])
        self.assertEqual(result['stop_reason'], 'run_zero_fatal_second_cancelled')
        self.assertNotIn(('activate', 1), events)
        self.assertIn(('cancel', 1), events)
        self.assertEqual(sum(c['run_index'] == 1 for c in result['unknown_cells']), 12)
        self.assertFalse(result['summary']['comparison_complete'])

    def test_missed_cells_retained_without_replay_or_cancellation(self):
        frozen, ops, events, _ = self.fixture(missed=True)
        result = transport.execute_pair(self.stage, frozen, ops, execute=True)
        self.assertTrue(result['complete'])
        self.assertTrue(result['unknown_cells'])
        self.assertTrue(all(c['reason'] == 'target_already_missed_no_catch_up' for c in result['unknown_cells']))
        self.assertIn(('activate', 1), events)
        self.assertFalse(any(name == 'cancel' for name, _ in events))

    def test_native_gates_fail_before_next_unit_and_never_repeat_capture(self):
        for fault in ('start', 'finish', 'capture', 'test_failure', 'activate', 'ready', 'ready_index',
                      'bind', 'inactive', 'release', 'result', 'envelope', 'drift', 'recheck'):
            with self.subTest(fault=fault):
                frozen, ops, events, _ = self.fixture(fault)
                result = transport.execute_pair(self.stage, frozen, ops, execute=True)
                self.assertFalse(result['complete'])
                self.assertNotIn(('activate', 1), events)
                self.assertEqual(len(result['unknown_cells']), 24)
                captures = [item for name, item in events if name == 'capture']
                self.assertEqual(len(captures), len(set(captures)))
                self.assertTrue(all('qcrl-wait-fixture' in item for name, item in events if name == 'stop'))

    def test_cleanup_failure_retained_and_public_drift_not_restored(self):
        frozen, ops, events, _ = self.fixture('stop')
        result = transport.execute_pair(self.stage, frozen, ops, execute=True)
        self.assertFalse(result['complete'])
        self.assertTrue(result['preservation_errors'])
        self.assertNotIn(('activate', 1), events)
        frozen, ops, events, _ = self.fixture()
        calls = iter((dict(public='unchanged'), dict(public='drift'), dict(public='drift')))
        ops.public_state = lambda: next(calls)
        result = transport.execute_pair(self.stage, frozen, ops, execute=True)
        self.assertFalse(result['complete'])
        self.assertEqual(result['public_after'], dict(public='drift'))
        self.assertNotIn(('activate', 0), events)

    def test_claim_preflight_and_final_publication_failure_propagate(self):
        for fault in ('claim', 'preflight', 'publish'):
            frozen, ops, events, _ = self.fixture(fault)
            with self.assertRaises(OSError):
                transport.execute_pair(self.stage, frozen, ops, execute=True)
            if fault != 'publish':
                self.assertFalse(any(name == 'start' for name, _ in events))

    def test_second_run_fault_does_not_erase_validated_first_run(self):
        frozen, ops, events, _ = self.fixture()
        original = ops.comparison_result
        ops.comparison_result = lambda index: original(index) if index == 0 else (_ for _ in ()).throw(OSError('partial'))
        result = transport.execute_pair(self.stage, frozen, ops, execute=True)
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['unknown_cells']), 12)
        self.assertTrue(all(c['run_index'] == 1 for c in result['unknown_cells']))
        self.assertIsNone(result['summary'])

    def test_prerequisite_rejects_rehashed_runtime_code_and_audit_changes(self):
        old, frozen = self.frozen()
        audit = dict(freeze_sha256=old['freeze_sha256'], native_origin_verified=True,
                     compatibility_verified=True, private_units_inactive=True,
                     public_unchanged=True, source_runtime_matches=True)
        audit['audit_sha256'] = payload_hash(audit)
        with patch.multiple(transport, COMPATIBILITY_AUDIT=audit['audit_sha256'], COMPATIBILITY_FREEZE=old['freeze_sha256']):
            self.assertTrue(transport.prerequisite(audit, old, frozen))
            for changed in ('runtime', 'code', 'audit', 'missing'):
                bad, a = deepcopy(frozen), deepcopy(audit)
                if changed == 'runtime': bad['runtime']['kernel'] = 'changed'
                if changed == 'code': bad['sources']['infra/stream/recorder_absolute_wait.py'] = 'd'*64
                if changed == 'missing': del bad['sources']['infra/stream/recorder_wait_comparison_native.py']
                if changed == 'audit': a['public_unchanged'] = False; a.pop('audit_sha256'); a['audit_sha256'] = payload_hash(a)
                bad.pop('freeze_sha256'); bad['freeze_sha256'] = payload_hash(bad)
                with self.assertRaises(ContractError): transport.prerequisite(a, old, bad)

    def test_failed_setup_retains_all_uninstantiated_cells(self):
        result = transport.failed_run(0, RuntimeError('x'*200))
        self.assertIsNone(result['epoch_ns'])
        self.assertEqual(result['rows'], [])
        self.assertEqual(len(result['fatal_error']), 160)
        validate_run(result)

    def test_production_start_is_fixed_and_preserves_bounds(self):
        ops = object.__new__(transport.ComparisonProduction)
        ops.root, ops.specs = Path(self.stage), {}
        spec = transport.comparison_spec(self.stage, 0)
        with patch.object(transport, 'command') as call:
            ops.start(spec)
            args = call.call_args.args[0]
            self.assertIn('infra.stream.recorder_wait_comparison_native', args)
            self.assertEqual(args[-3:], ['--run-index', '0', '--execute'])
            bad = deepcopy(spec); bad['properties']['CPUQuota'] = '100%'
            with self.assertRaises(ContractError): ops.start(bad)
            self.assertEqual(call.call_count, 1)

    def test_nested_inventory_seals_partial_files_and_never_overwrites(self):
        with TemporaryDirectory() as directory:
            root = Path(directory); evidence = root/'evidence'; (evidence/'run-0').mkdir(parents=True)
            (evidence/'run-0'/'partial.json').write_bytes(b'{')
            ops = object.__new__(transport.ComparisonProduction); ops.root = root
            ops.frozen = self.frozen()[1]
            ops.publish_comparison(dict(summary=None))
            self.assertIn('run-0/partial.json', load(root/'origin-inventory.json')['files'])
            with self.assertRaises(FileExistsError): ops.publish_comparison(dict(summary=None))

    def test_regression_population_gate_rejects_extra_skips_and_missing_tests(self):
        self.assertEqual(transport.regression_population('fixture: Ran 1093 tests in 100.0s\nfixture: OK (skipped=1)\n')['skipped'], 1)
        for text in ('Ran 1092 tests in 1.0s\nOK (skipped=1)\n', 'Ran 1093 tests in 1.0s\nOK (skipped=2)\n',
                     'Ran 1093 tests in 1.0s\nFAILED\n', 'Ran 1093 tests in 1.0s\nOK\n'):
            with self.assertRaises(ContractError): transport.regression_population(text)

    def test_worker_retains_interrupt_and_publication_failure_without_native_calls(self):
        for failure in (None, 'interrupt', 'publication', 'escaped', 'prior'):
            with self.subTest(failure=failure), TemporaryDirectory() as directory:
                stage = Path(directory).resolve()/'recorder-wait-fixture';stage.mkdir();(stage/'source').mkdir();runroot=stage/'evidence/run-0';runroot.mkdir(parents=True)
                if failure=='prior':(stage/'evidence/run-1').mkdir()
                frozen = self.frozen()[1]
                for name,value in [('execution-freeze.json',frozen),('compatibility-audit.json',{}),
                                   ('compatibility-freeze.json',{}),('runtime-review.json',{})]:publish(stage/name,value)
                identity=dict(pid=100,boot_id='fixture',process_start_id='1',cgroup='/system.slice/'+transport.comparison_spec(self.stage,0)['unit']+'.service')
                # Native stage names are irrelevant to the injected filesystem/platform guard fixture.
                tag=stage.name[len('recorder-wait-'):]
                identity['cgroup']='/system.slice/qcrl-wait-'+tag+'-comparison-0.service'
                reader=SimpleNamespace(expected=identity)
                clock=SimpleNamespace(value=10*NS)
                calls=[]
                def selected(*args):
                    calls.append('select')
                    if failure=='interrupt' and len(calls)==2:raise KeyboardInterrupt('fixture')
                    clock.value+=round(args[-1]*NS);return ([],[],[])
                def syscall(clock_id,flags,seconds,nanos):
                    calls.append('absolute');clock.value=seconds*NS+nanos;return 0
                absolute=AbsoluteWait(clock_ns=lambda:clock.value,syscall=syscall)
                events=[]
                real_publish=publish
                def publisher(path,value):
                    events.append(path.name)
                    if path.name=='run.json' and failure=='publication':raise OSError('disk fault')
                    real_publish(path,value)
                    if path.name=='ready.json':
                        props=transport.comparison_spec(str(stage),0)['properties']
                        binding=dict(unit=value['unit'],identity=identity,active=True,observed_properties=props)
                        release=transport.bind_ready(value,transport.comparison_spec(str(stage),0),frozen,binding)
                        real_publish(runroot/'release.json',release)
                import re
                real_collect = transport.collect_run
                def collector(**kwargs):
                    if failure=='escaped':raise KeyboardInterrupt('outside wrapped call')
                    return real_collect(**kwargs)
                with patch.multiple(transport, ROOT=stage/'source',STAGE=re.escape(str(stage))), \
                     patch('infra.stream.recorder_wait_lifecycle.STAGE',re.escape(str(stage))), \
                     patch.object(transport.platform,'system',return_value='Linux'), \
                     patch.object(transport.os,'geteuid',return_value=123), \
                     patch.object(transport.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=123)), \
                     patch.object(transport,'prerequisite',return_value=True), \
                     patch.object(transport,'inspect_source',return_value=(frozen['sources'],frozen['source_commit'])), \
                     patch.object(transport,'observe_runtime',return_value=frozen['runtime']), \
                     patch.object(transport.sys,'executable',transport.PYTHON), \
                     patch('infra.stream.recorder_application_resources.LinuxReader',return_value=reader), \
                     patch('infra.stream.recorder_wake_worker.context',return_value={'fixture':True}), \
                     patch.object(transport,'native',return_value=absolute) as binder, \
                     patch.object(transport.time,'monotonic_ns',side_effect=lambda:clock.value), \
                     patch.object(transport.select,'select',side_effect=selected), \
                     patch.object(transport,'collect_run',side_effect=collector), \
                     patch.object(transport,'publish',side_effect=publisher),patch('builtins.print') as printed:
                    if failure=='prior':
                        with self.assertRaises(ContractError):transport.worker(stage,1,execute=True)
                        binder.assert_not_called()
                        self.assertEqual(events,[])
                        continue
                    elif failure=='escaped':
                        with self.assertRaises(KeyboardInterrupt):transport.worker(stage,0,execute=True)
                        self.assertFalse((runroot/'run.json').exists())
                        printed.assert_not_called()
                    elif failure=='publication':
                        with self.assertRaises(OSError):transport.worker(stage,0,execute=True)
                        self.assertFalse((runroot/'run.json').exists())
                        self.assertTrue(printed.call_args.args[0].startswith('QCRL_COMPARISON_RUN='))
                    else:
                        transport.worker(stage,0,execute=True)
                        result=validate_run(load(runroot/'run.json'))
                        self.assertEqual(len(result['rows']),12)
                        if failure=='interrupt':
                            self.assertIn('KeyboardInterrupt',result['fatal_error'])
                            self.assertEqual(result['rows'][0]['observation']['status'],'observed')
                            self.assertEqual(len(calls),2)
                            self.assertTrue(all(row['observation'] is None for row in result['rows'][2:]))
                        else:self.assertIsNone(result['fatal_error'])
                    binder.assert_called_once_with(execute=True)
                    self.assertEqual(events[0],'ready.json')

    def test_guard_refuses_execution_before_native_bind_or_units(self):
        with patch.object(transport, 'native') as binder, patch.object(transport, 'command') as helper:
            with self.assertRaises(ContractError): transport.worker(Path(self.stage), 0)
            with self.assertRaises(ContractError): transport.launch(Path(self.stage))
            binder.assert_not_called(); helper.assert_not_called()
        for index in (False, 2, -1, None):
            with self.assertRaises(ContractError): transport.comparison_spec(self.stage, index)

    def test_retained_audit_rejects_rehashed_identity_properties_and_unknown_loss(self):
        old, frozen = self.frozen()
        audit = dict(freeze_sha256=old['freeze_sha256'], native_origin_verified=True,
                     compatibility_verified=True, private_units_inactive=True,
                     public_unchanged=True, source_runtime_matches=True)
        audit['audit_sha256'] = payload_hash(audit)
        frozen2, ops, events, _ = self.fixture()
        report = transport.execute_pair(self.stage, frozen2, ops, execute=True)
        with TemporaryDirectory() as directory:
            root = Path(directory); evidence = root/'evidence'; evidence.mkdir()
            for name, value in [('execution-freeze.json', frozen), ('compatibility-freeze.json', old),
                                ('compatibility-audit.json', audit)]:
                publish(evidence/name, value)
            tests = transport.unit_spec(self.stage, 'tests')
            test_props = dict(tests['properties'], CPUQuotaPerSecUSec='750ms', RuntimeMaxUSec='4min',
                              MemoryMax='536870912', Id=tests['unit']+'.service', Result='success',
                              ExecMainStatus='0', SubState='exited', ExecMainExitTimestampMonotonic='8000000')
            (evidence/(tests['unit']+'-properties.txt')).write_text('\n'.join(k+'='+v for k,v in test_props.items()))
            (evidence/(tests['unit']+'-journal.txt')).write_text('fixture: Ran 1093 tests in 1.0s\nfixture: OK (skipped=1)\n')
            runs = []
            for index in (0, 1):
                spec = transport.comparison_spec(self.stage, index)
                result = comparison_fixtures.WaitComparisonV2Tests().fixture(index)[0]
                if index == 1:
                    offset = 200_000_000_000
                    result['epoch_ns'] += offset
                    for pair in result['baseline']:
                        for key in ('before_ns', 'after_ns'): pair[key] += offset
                    for row in result['rows']:
                        row['target_ns'] += offset; row['checkpoint_ns'] += offset
                        for key in ('target_ns', 'before_ns', 'after_ns'): row['observation'][key] += offset
                    comparison_fixtures.WaitComparisonV2Tests().rehash(result)
                runs.append(result)
                identity = dict(pid=100+index, boot_id='fixture', process_start_id=str(index+1),
                                cgroup='/system.slice/'+spec['unit']+'.service')
                resource = dict(owner=identity, effective_quota=.75,
                                ancestry=[dict(cpu_max='75000 100000', memory_max='536870912')])
                context = dict(resource=resource, files={'fixture-file': dict(status='unknown', error='fixture')})
                ready = dict(unit=spec['unit'], run_index=index, identity=identity,
                             plan_sha256=payload_hash(transport.PLAN), freeze_sha256=frozen['freeze_sha256'],
                             context_before=context)
                ready['ready_sha256'] = payload_hash(ready)
                binding = dict(unit=spec['unit'], identity=identity, active=True, observed_properties=spec['properties'])
                release = transport.bind_ready(ready, spec, frozen, binding)
                raw = dict(spec['properties'], CPUQuotaPerSecUSec='750ms', RuntimeMaxUSec='4min',
                           MemoryMax='536870912', Id=spec['unit']+'.service', ActiveState='active',
                           SubState='running', MainPID=str(identity['pid']), ExecMainPID=str(identity['pid']),
                           ControlGroup=identity['cgroup'])
                active = dict(binding=binding, binding_sha256=payload_hash(binding), raw_properties=raw, sample=resource)
                envelope = dict(schema_version='qcrl.wait_comparison_native_envelope.v1', run_index=index,
                                run_sha256=result['run_sha256'], ready_sha256=ready['ready_sha256'],
                                release_sha256=release['release_sha256'], freeze_sha256=frozen['freeze_sha256'],
                                identity=identity, context_after=context, native_origin_verified=False,
                                acceptance_demonstrated=False, orders_authorized=False)
                envelope['envelope_sha256'] = payload_hash(envelope)
                runroot = evidence/('run-'+str(index)); runroot.mkdir()
                for name, value in [('run.json', result), ('ready.json', ready), ('release.json', release),
                                    ('active-binding.json', active), ('run-envelope.json', envelope)]:
                    publish(runroot/name, value)
                props = dict(raw, Result='success', SubState='exited', ExecMainStatus='0',
                             ExecMainStartTimestampMonotonic=str((9+200*index)*1_000_000),
                             ExecMainExitTimestampMonotonic=str((144+200*index)*1_000_000))
                (runroot/(spec['unit']+'-properties.txt')).write_text('\n'.join(k+'='+v for k,v in props.items()))
                (runroot/(spec['unit']+'-journal.txt')).write_text('fixture retained journal\n')
            report['summary'] = transport.evaluate(runs)
            report.pop('launch_sha256');report['launch_sha256'] = payload_hash(report)
            publish(evidence/'comparison-launch.json', report);publish(evidence/'summary.json', report['summary'])

            def seal():
                import hashlib
                value = dict(schema_version='qcrl.wait_comparison_origin_inventory.v1',
                             freeze_sha256=frozen['freeze_sha256'], native_origin_verified=False,
                             files={str(p.relative_to(evidence)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                    for p in evidence.rglob('*') if p.is_file()})
                value['inventory_sha256'] = payload_hash(value)
                (root/'origin-inventory.json').write_text(json.dumps(value))
            seal()
            with patch.multiple(transport, COMPATIBILITY_AUDIT=audit['audit_sha256'], COMPATIBILITY_FREEZE=old['freeze_sha256']):
                result = transport.audit_retained(root)
                self.assertTrue(result['structure_verified'])
                self.assertFalse(result['native_origin_verified'])
                self.assertEqual(len(result['unknown_context']), 4)
                path = evidence/'run-1'/'active-binding.json'
                prior = path.read_bytes();changed=load(path);changed['raw_properties']['MemoryMax']='1';path.write_text(json.dumps(changed));seal()
                with self.assertRaises(ContractError):transport.audit_retained(root)
                path.write_bytes(prior);seal()
                path = evidence/'comparison-launch.json';changed=load(path)
                changed['unknown_cells']=[dict(run_index=0,arm='select',interval_ns=50_000_000,reason='invented')]
                changed.pop('launch_sha256');changed['launch_sha256']=payload_hash(changed);path.write_text(json.dumps(changed));seal()
                with self.assertRaises(ContractError):transport.audit_retained(root)


if __name__ == '__main__':
    unittest.main()
