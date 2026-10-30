"""Offline lifecycle/adapter faults; no native unit creation or cleanup."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_exited_unit as inspection


def binding():
    return dict(properties=dict(Id='qcrl-fixture.service', InvocationID='a'*32,
                WorkingDirectory='/private/source', ExecStart='exact frozen argv',
                ExecMainStartTimestampMonotonic='123'),
                boot_id='fixture-boot', cgroup='/system.slice/qcrl-fixture.service',
                processes=[dict(pid=11, start_id='101'), dict(pid=12, start_id='102')])


def properties():
    return dict(binding()['properties'], ActiveState='active', SubState='exited',
                MainPID='0', ControlGroup=binding()['cgroup'], TasksCurrent='[not set]')


def reader():
    return Mock(boot=Mock(return_value='fixture-boot'),
                unit=Mock(side_effect=lambda unit: properties()),
                process=Mock(return_value=None),
                group=Mock(side_effect=lambda group: dict(state='exists', identity=[1, 20], members=[])))


class LifecycleTests(unittest.TestCase):
    @staticmethod
    def exec_display(*, exited=False, argv='/opt/python -m worker', path='/opt/python', ignore='no'):
        return ('{ path='+path+' ; argv[]='+argv+' ; ignore_errors='+ignore+
                ' ; start_time=[Fri 2026-10-30 16:00:55 UTC] ; stop_time=['+
                ('Fri 2026-10-30 16:01:28 UTC' if exited else 'n/a')+
                '] ; pid=3208026 ; code='+('killed' if exited else '(null)')+
                ' ; status='+('15/TERM' if exited else '0/0')+' }')

    def test_command_identity_contract_is_pinned(self):
        self.assertEqual(payload_hash(inspection.COMMAND_IDENTITY),
                         '821675a9cb9f7897203e57d04da00213d5d39fb00274998dce8a837b7943d7ca')

    def test_lifecycle_execstart_change_retains_failed_exit_and_raw_displays(self):
        b=binding();b['properties']['ExecStart']=self.exec_display()
        p=properties();p['ExecStart']=self.exec_display(exited=True)
        p.update(ExecMainStatus='15',ExecMainCode='2')
        r=reader();r.unit.side_effect=lambda _:deepcopy(p)
        value=inspection.inspect_exited_unit(b,r)
        self.assertTrue(value['exited_binding_observed'],value)
        self.assertEqual(value['observations'][0]['properties']['ExecStart'],p['ExecStart'])
        self.assertEqual(value['observations'][0]['properties']['ExecMainStatus'],'15')
        self.assertIsNone(value['tasks_current'])
        self.assertFalse(value['stop_authorized'])
        for key,change in [('path','/foreign'),('argv','/opt/python -m other'),('ignore','yes')]:
            r=reader();q=deepcopy(p);q['ExecStart']=self.exec_display(exited=True,**{key:change})
            r.unit.side_effect=lambda _,q=q:deepcopy(q)
            self.assertFalse(inspection.inspect_exited_unit(b,r)['exited_binding_observed'])

    def test_execstart_malformed_multiple_and_unknown_fields_fail_closed(self):
        original=self.exec_display()
        for text in (original+' '+original,original.replace('argv[]','unknown'),
                     original.replace(' ; pid=3208026',' ; extra=yes ; pid=3208026'),
                     original[:-1],original.replace('/opt/python -m worker','/opt/python ; other'),
                     '{ malformed }'):
            b=binding();b['properties']['ExecStart']=text;r=reader()
            with self.subTest(text=text),self.assertRaises(ContractError):
                inspection.inspect_exited_unit(b,r)
            r.boot.assert_not_called()

    def test_lifecycle_change_between_exit_rounds_is_still_a_race(self):
        b=binding();b['properties']['ExecStart']=self.exec_display()
        a=properties();a['ExecStart']=self.exec_display(exited=True)
        z=deepcopy(a);z['ExecStart']=z['ExecStart'].replace('15/TERM','9/KILL')
        r=reader();r.unit.side_effect=[a,z]
        self.assertIn('inspection changed between rounds',
                      inspection.inspect_exited_unit(b,r)['errors'][0])

    def test_prospective_policy_identity_is_pinned(self):
        self.assertEqual(payload_hash(inspection.POLICY),
                         '24898288fd05207fbfda23597c20a8ba04c56ab4f626a30b262ead55b50c4a6b')

    def inspect(self, r=None):
        value = inspection.inspect_exited_unit(binding(), r or reader())
        original = {k: v for k, v in value.items() if k != 'artifact_sha256'}
        self.assertEqual(value['artifact_sha256'], payload_hash(original))
        self.assertFalse(value['stop_authorized'])
        self.assertIsNone(value['resource_qualification'])
        return value

    def test_missing_counter_is_unknown_with_independent_exit_evidence(self):
        for raw in ('[not set]', '', None):
            with self.subTest(raw=raw):
                r = reader(); r.unit.side_effect = None
                p = properties(); p['TasksCurrent'] = raw
                r.unit.return_value = p
                value = self.inspect(r)
                self.assertTrue(value['exited_binding_observed'])
                self.assertIsNone(value['tasks_current'])
                self.assertEqual(value['errors'], [])
                self.assertEqual(value['observations'][0]['tasks_current_raw'], raw)

    def test_zero_and_removed_group(self):
        r = reader(); p = properties(); p['TasksCurrent'] = '0'
        r.unit.side_effect = lambda _: deepcopy(p)
        r.group.side_effect = lambda _: dict(state='removed', members=[])
        value = self.inspect(r)
        self.assertTrue(value['exited_binding_observed'])
        self.assertEqual(value['tasks_current'], 0)

    def test_active_foreign_or_restarted_unit_is_rejected(self):
        mutations = [('ActiveState', 'activating'), ('SubState', 'running'), ('MainPID', '11'),
                     ('Id', 'foreign.service'), ('InvocationID', 'b'*32),
                     ('WorkingDirectory', '/foreign'), ('ExecStart', 'exact frozen argv extra'),
                     ('ExecMainStartTimestampMonotonic', '124'), ('ControlGroup', '/foreign')]
        for key, val in mutations:
            with self.subTest(key=key):
                r = reader(); p = properties(); p[key] = val
                r.unit.side_effect = lambda _, p=p: deepcopy(p)
                self.assertFalse(self.inspect(r)['exited_binding_observed'])

    def test_all_declared_exited_states(self):
        for active, sub in [('active', 'exited'), ('inactive', 'dead'), ('failed', 'failed')]:
            r = reader(); p = properties(); p.update(ActiveState=active, SubState=sub)
            r.unit.side_effect = lambda _: deepcopy(p)
            self.assertTrue(self.inspect(r)['exited_binding_observed'])

    def test_failed_exit_is_retained_not_converted_to_success(self):
        r = reader(); p = properties()
        p.update(ActiveState='failed', SubState='failed', Result='signal', ExecMainStatus='15')
        r.unit.side_effect = lambda _: deepcopy(p)
        value = self.inspect(r)
        self.assertTrue(value['exited_binding_observed'])
        self.assertEqual(value['observations'][0]['properties']['Result'], 'signal')
        self.assertEqual(value['observations'][0]['properties']['ExecMainStatus'], '15')
        self.assertIsNone(value['resource_qualification'])

    def test_bad_or_populated_counter_rejected_even_with_no_members(self):
        for raw in ('1', '-1', '00', '0.0', 'unknown', True, 0, '9'*21):
            with self.subTest(raw=raw):
                r = reader(); p = properties(); p['TasksCurrent'] = raw
                r.unit.side_effect = lambda _: deepcopy(p)
                self.assertFalse(self.inspect(r)['exited_binding_observed'])

    def test_bound_process_exists_even_if_counter_zero(self):
        for start in ('101', '102'):
            r = reader(); r.process.side_effect = lambda pid: start if pid == (11 if start == '101' else 12) else None
            self.assertFalse(self.inspect(r)['exited_binding_observed'])

    def test_reused_pid_is_explicit_and_not_original_process(self):
        r = reader(); r.process.return_value = '999'
        value = self.inspect(r)
        self.assertTrue(value['exited_binding_observed'])
        self.assertEqual(value['observations'][0]['processes'][0]['current_start_id'], '999')

    def test_populated_group_rejected_despite_missing_counter(self):
        r = reader(); r.group.side_effect = lambda _: dict(state='exists', identity=[1, 20], members=['999'])
        self.assertFalse(self.inspect(r)['exited_binding_observed'])

    def test_detects_observable_races(self):
        for which in ('invocation', 'pid', 'group', 'boot', 'last_boot', 'counter'):
            with self.subTest(which=which):
                r = reader()
                if which in ('invocation', 'counter'):
                    a, b = properties(), properties()
                    b['InvocationID' if which == 'invocation' else 'TasksCurrent'] = 'b'*32 if which == 'invocation' else '0'
                    r.unit.side_effect = [a, b]
                elif which == 'pid': r.process.side_effect = [None, None, '999', None]
                elif which == 'group':
                    r.group.side_effect = [dict(state='exists', identity=[1, 20], members=[]),
                                           dict(state='exists', identity=[1, 21], members=[])]
                elif which == 'boot': r.boot.side_effect = ['fixture-boot', 'other']
                else: r.boot.side_effect = ['fixture-boot', 'fixture-boot', 'other']
                value = self.inspect(r)
                self.assertFalse(value['exited_binding_observed'])
                self.assertTrue(value['errors'])

    def test_read_failure_keeps_partial_observations_and_bounded_error(self):
        for where in ('unit', 'process', 'group', 'boot'):
            r = reader(); getattr(r, where).side_effect = PermissionError('secret-free fault'*30)
            value = self.inspect(r)
            self.assertFalse(value['exited_binding_observed'])
            self.assertLessEqual(len(value['errors'][0]), 160)
            if where in ('process', 'group'): self.assertEqual(len(value['observations']), 1)

    def test_invalid_bindings_rejected_before_reads(self):
        for key, val in [('processes', []), ('processes', [dict(pid=True, start_id='1')]*2),
                         ('cgroup', '/system.slice/../foreign'), ('boot_id', '')]:
            expected = binding(); expected[key] = val; r = reader()
            with self.assertRaises(ContractError): inspection.inspect_exited_unit(expected, r)
            r.boot.assert_not_called()


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.proc = self.root/'proc'; self.proc.mkdir()
        self.group = self.root/'cgroup'; (self.group/'system.slice').mkdir(parents=True)
        self.path = self.group/'system.slice/qcrl-fixture.service'; self.path.mkdir()
        (self.path/'cgroup.procs').write_text('')
        self.run = Mock(return_value='\n'.join(k+'='+v for k, v in properties().items()))
        with patch.object(inspection.platform, 'system', return_value='Linux'):
            self.reader = inspection.LinuxReader(execute=True, proc=self.proc, cgroup=self.group, run=self.run)

    def test_adapter_properties_bounded_read_only_command(self):
        self.assertEqual(self.reader.unit('qcrl-fixture.service'), properties())
        args, kwargs = self.run.call_args
        self.assertEqual(args[0][:3], ['systemctl', 'show', 'qcrl-fixture.service'])
        self.assertEqual(kwargs, dict(execute=True, timeout=5, cap=32768))
        for raw in ('Id=x\nId=y', 'badline', 'Unexpected=x'):
            self.run.return_value = raw
            with self.assertRaises(ContractError): self.reader.unit('qcrl-fixture.service')

    def test_actual_bounded_file_reads_and_process_parser(self):
        folder = self.proc/'11'; folder.mkdir()
        path = folder/'stat'; path.write_text('11 (a ) tricky) '+' '.join(['S']+['0']*18+['101']))
        self.assertEqual(self.reader.process(11), '101')
        path.write_text('malformed')
        with self.assertRaises(ContractError): self.reader.process(11)
        path.write_text('x'*4097)
        with self.assertRaises(ContractError): self.reader.process(11)
        path.unlink(); self.assertIsNone(self.reader.process(11))
        path.symlink_to(self.path/'cgroup.procs')
        with self.assertRaises(OSError): self.reader.process(11)

    def test_group_empty_populated_removed_and_unavailable(self):
        self.assertEqual(self.reader.group(binding()['cgroup'])['members'], [])
        (self.path/'cgroup.procs').write_text('11\n12\n')
        self.assertEqual(self.reader.group(binding()['cgroup'])['members'], ['11', '12'])
        (self.path/'cgroup.procs').unlink()
        with self.assertRaises(FileNotFoundError): self.reader.group(binding()['cgroup'])
        self.path.rmdir()
        self.assertEqual(self.reader.group(binding()['cgroup']), dict(state='removed', members=[]))
        (self.group/'system.slice').rmdir()
        with self.assertRaises(ContractError): self.reader.group(binding()['cgroup'])

    def test_group_symlink_and_midread_replacement(self):
        original = self.reader.text
        def replace(path):
            value = original(path)
            self.path.rename(self.path.with_name('old'))
            self.path.mkdir()
            return value
        with patch.object(self.reader, 'text', side_effect=replace):
            with self.assertRaisesRegex(ContractError, 'replaced'): self.reader.group(binding()['cgroup'])
        self.path.rmdir(); self.path.symlink_to(self.root/'missing')
        with self.assertRaisesRegex(ContractError, 'symlink'): self.reader.group(binding()['cgroup'])

    def test_boot_and_explicit_execution_requirement(self):
        p = self.proc/'sys/kernel/random'; p.mkdir(parents=True)
        (p/'boot_id').write_text('fixture-boot\n')
        self.assertEqual(self.reader.boot(), 'fixture-boot')
        with self.assertRaises(ContractError): inspection.LinuxReader()

    def test_inspection_uses_real_adapter_over_offline_files(self):
        p = self.proc/'sys/kernel/random'; p.mkdir(parents=True)
        (p/'boot_id').write_text('fixture-boot\n')
        value = inspection.inspect_exited_unit(binding(), self.reader)
        self.assertTrue(value['exited_binding_observed'])
        self.assertEqual(value['errors'], [])
        self.assertEqual(self.run.call_count, 2)
        # Zero task count cannot mask a bound process that still exists.
        folder = self.proc/'11'; folder.mkdir()
        (folder/'stat').write_text('11 (worker) '+' '.join(['S']+['0']*18+['101']))
        self.assertFalse(inspection.inspect_exited_unit(binding(), self.reader)['exited_binding_observed'])

    def test_short_reads_are_drained_with_original_cap(self):
        p = self.root/'file'; p.write_text('unused')
        with patch.object(inspection.os, 'read', side_effect=[b'12', b'3\n', b'']):
            self.assertEqual(self.reader.text(p), '123\n')


if __name__ == '__main__':
    unittest.main()
