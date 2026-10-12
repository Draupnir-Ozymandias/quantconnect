import copy
import threading
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream.recorder_application_budget import declare, POLICY, corpus
from infra.stream.recorder_application_worker import schedule, message, transmit, context, publish
from infra.stream.recorder_application_resources import cpus, counters, quota, observe, LinuxReader, text
from infra.stream.recorder_application_evaluator import (
    finite, percentile, timing_gate, stimulus_gate, resource_gate, outcome, audit_cohort)


OWNER = dict(pid=1, process_start_id='10', cgroup='/unit', boot_id='fixture-boot')
ANCESTRY = [dict(path='unit', cpu_max='75000 100000', cpuset_effective='0-3',
                 memory_max='536870912'),
            dict(path='.', cpu_max=None, cpuset_effective='0-3', memory_max=None)]


def sample(at, cpu, rss=1000):
    return dict(before=at, after=at+.0001, owner=copy.deepcopy(OWNER),
                ancestry=copy.deepcopy(ANCESTRY), effective_quota=.75,
                cpu=dict(usage_usec=cpu), memory_events=dict(oom=0, oom_kill=0, max=0),
                actors=[dict(OWNER, rss_bytes=rss)], rss_bytes=rss)


def resources(duration=120):
    return dict(overflow=False, rows=[dict(slot=i, target=1000+i, error=None,
        sample=sample(1000+i, i*1000+100),
        cpu_before=sample(1000+i-.001, max(0, i*1000)) if i % 60 == 0 else None)
        for i in range(duration+1)])


class WorkerTests(unittest.TestCase):
    def test_workload_order_population_and_duplicate_bytes(self):
        for kind, duration in [('steady', 120), ('mixed', 70)]:
            rows = schedule(kind)
            self.assertEqual(len(rows), 60000)
            self.assertLess(rows[-1]['offset'], duration)
            self.assertTrue(all(a['offset'] < b['offset'] for a, b in zip(rows, rows[1:])))
        self.assertEqual(message(0), corpus()['initial'][0])
        self.assertEqual(message(2), message(10))
        self.assertEqual(message(6), message(9))
        for value in (-1, 60000, True):
            with self.assertRaises(ContractError):
                message(value)

    def test_transmit_preserves_failed_prefix_no_retry(self):
        class Clock:
            value = 0
            def now(self): return self.value
            def pause(self, seconds): self.value += seconds
        class Socket:
            calls = 0
            def send(self, value):
                self.calls += 1
                if self.calls == 4:
                    raise OSError('injected')
        clock, socket = Clock(), Socket()
        result = transmit(socket, 'steady', 1, clock=clock.now, pause=clock.pause)
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['rows']), 3)
        self.assertEqual(socket.calls, 4)
        self.assertIn('OSError', result['error'])

    def test_explicit_execution_guard_before_io(self):
        with self.assertRaises(ContractError):
            context('/does-not-exist', {}, False)


class GateTests(unittest.TestCase):
    def test_nearest_rank_and_nonfinite(self):
        self.assertEqual(percentile(list(range(100))), 98)
        for value in (True, float('nan'), float('inf'), -1):
            with self.assertRaises(ContractError): finite(value)
        with self.assertRaises(ContractError): percentile([])

    def test_phase_failure_not_pooled_away(self):
        latencies = [dict(append_upper_seconds=.001, durable_upper_seconds=.1) for _ in range(100)]
        latencies[-1]['append_upper_seconds'] = .2
        witnesses = [dict(returned=dict(before=1, after=1.0001)) for _ in latencies]
        result = timing_gate(latencies, witnesses, [0]*99+[1], declare()['budgets'])
        self.assertEqual(result['verdict'], 'fail')
        self.assertIn('1:append_p99', result['failures'])
        self.assertEqual(result['groups']['case']['append_p99'], .001)

    def test_missing_and_invalid_timing_never_pass(self):
        budgets = declare()['budgets']
        self.assertEqual(timing_gate([], [], [0], budgets)['verdict'], 'unknown')
        result = timing_gate([dict(append_upper_seconds=float('nan'), durable_upper_seconds=1)],
                             [dict(returned=dict(before=2, after=1))], [0], budgets)
        self.assertEqual(result['verdict'], 'unknown')
        result = timing_gate([dict(append_upper_seconds=2, durable_upper_seconds=3),
                              dict(append_upper_seconds=float('nan'), durable_upper_seconds=1)],
                             [dict(returned=dict(before=1, after=1.0001))]*2, [0, 0], budgets)
        self.assertEqual(result['verdict'], 'fail')
        self.assertTrue(result['unknowns'])

    def test_resource_windows_conservative_and_current_rss(self):
        result = resource_gate(resources(), 1000, 120, 1120, declare()['budgets'], OWNER)
        self.assertEqual(result['verdict'], 'pass', result)
        self.assertEqual(len(result['windows']), 2)
        self.assertFalse(result['rss_continuous_peak_proven'])

    def test_resource_missing_race_reset_and_nan_fail_closed(self):
        for mutation in ('missing', 'race', 'reset', 'nan', 'bracket', 'quota'):
            value = resources()
            if mutation == 'missing': value['rows'].pop(10)
            if mutation == 'race': value['rows'][10]['error'] = 'process disappeared'
            if mutation == 'reset': value['rows'][10]['sample']['cpu']['usage_usec'] = 0
            if mutation == 'nan': value['rows'][60]['sample']['before'] = float('nan')
            if mutation == 'bracket': value['rows'][60]['cpu_before']['after'] = 1060.1
            if mutation == 'quota': value['rows'][10]['sample']['effective_quota'] = 1
            result = resource_gate(value, 1000, 120, 1120, declare()['budgets'], OWNER)
            self.assertEqual(result['verdict'], 'unknown', (mutation, result))

    def test_known_failures_retained_alongside_unknown(self):
        value = resources()
        value['rows'][5]['sample']['actors'][0]['rss_bytes'] = 500000000
        value['rows'][5]['sample']['rss_bytes'] = 500000000
        value['rows'][7]['error'] = 'missing'
        value['rows'][60]['sample']['cpu']['usage_usec'] = 40000000
        result = resource_gate(value, 1000, 120, 1120, declare()['budgets'], OWNER)
        self.assertEqual(result['verdict'], 'fail')
        self.assertIn('current_rss:5', result['failures'])
        self.assertIn('cpu_window:0', result['failures'])
        self.assertTrue(result['unknowns'])

    def test_stimulus_missing_phase_and_chronology(self):
        result = stimulus_gate(dict(rows=[], complete=False, error='failed'), 'mixed', 1000)
        self.assertEqual(result['verdict'], 'fail')
        self.assertIn('phase_attainment:1', result['failures'])
        self.assertEqual(outcome(['known'], ['missing']), 'fail')

    def test_failed_prefix_not_erased_by_missing_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'steady-0').mkdir()
            publish(root/'steady-0/consumer.json', dict(error='injected fsync failure'))
            result = audit_cohort(root, declare())
            self.assertEqual(result['verdict'], 'fail')
            self.assertIn('steady-0:consumer_failure_prefix', result['failures'])
            self.assertTrue(result['unknowns'])
            self.assertFalse(result['acceptance_demonstrated'])


class ResourceTests(unittest.TestCase):
    def fixture(self, root):
        proc, mount = root/'proc', root/'cgroup'
        (proc/'sys/kernel/random').mkdir(parents=True)
        (proc/'10').mkdir()
        (mount/'unit').mkdir(parents=True)
        (proc/'sys/kernel/random/boot_id').write_text('fixture-boot')
        (proc/'10/stat').write_text('10 (fixture) '+' '.join(['S']+['0']*18+['123']))
        (proc/'10/cgroup').write_text('0::/unit\n')
        (proc/'10/status').write_text('VmRSS:\t100 kB\n')
        for name, value in {'cpu.max':'75000 100000', 'memory.max':'536870912',
                            'cgroup.controllers':'cpuset cpu memory', 'cgroup.subtree_control':'',
                            'cpuset.cpus.effective':'0-3', 'cgroup.procs':'10',
                            'cpu.stat':'usage_usec 100\nnr_periods 1\nnr_throttled 0\nthrottled_usec 0',
                            'memory.events':'oom 0\noom_kill 0\nmax 0', 'memory.current':'1000'}.items():
            (mount/'unit'/name).write_text(value)
        (mount/'cpuset.cpus.effective').write_text('0-3')
        (mount/'cgroup.controllers').write_text('cpuset cpu memory io')
        (mount/'cgroup.subtree_control').write_text('cpuset cpu memory')
        return LinuxReader(execute=True, proc=proc, mount=mount, pid=10)

    def ohio_fixture(self, root):
        self.fixture(root)
        mount = root/'cgroup'
        (mount/'system.slice').mkdir()
        (mount/'unit').rename(mount/'system.slice/unit')
        (root/'proc/10/cgroup').write_text('0::/system.slice/unit\n')
        (mount/'system.slice/unit/cpuset.cpus.effective').unlink()
        (mount/'system.slice/unit/cgroup.controllers').write_text('cpu memory')
        (mount/'cgroup.subtree_control').write_text('cpu memory')
        for name, value in {'cgroup.controllers':'cpu memory', 'cgroup.subtree_control':'cpu memory',
                            'cpu.max':'max 100000', 'memory.max':'max'}.items():
            (mount/'system.slice'/name).write_text(value)
        (mount/'cpuset.cpus.effective').write_text('0-1')
        return LinuxReader(execute=True, proc=root/'proc', mount=mount, pid=10)

    def test_ohio_disabled_cpuset_retained_null_with_ancestor_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            reader = self.ohio_fixture(root)
            result = reader.read(rss=True)
            rows = result['ancestry']
            self.assertEqual([r['path'] for r in rows], ['system.slice/unit','system.slice','.'])
            self.assertEqual([r['cpuset_effective'] for r in rows], [None,None,'0-1'])
            self.assertEqual(result['effective_quota'], .75)
            self.assertEqual(quota(rows), .75)
            (root/'cgroup/system.slice/cpu.max').write_text('25000 100000')
            self.assertEqual(reader.read()['effective_quota'], .25)
            (root/'cgroup/system.slice/unit/cpu.max').write_text('max 100000')
            (root/'cgroup/system.slice/cpu.max').write_text('max 100000')
            self.assertEqual(reader.read()['effective_quota'], 2)

    def test_absent_enabled_root_or_unproven_cpuset_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            reader = self.fixture(root)
            (root/'cgroup/unit/cpuset.cpus.effective').unlink()
            with self.assertRaisesRegex(ContractError,'file/controller state differs'): reader.read()
        for mutation in ('enabled','root','unproven','empty','contradictory','parent','partial'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                reader = self.ohio_fixture(root)
                if mutation == 'enabled':
                    (root/'cgroup/system.slice/cgroup.subtree_control').write_text('cpuset cpu memory')
                if mutation == 'root': (root/'cgroup/cpuset.cpus.effective').unlink()
                if mutation == 'unproven': (root/'cgroup/system.slice/cgroup.subtree_control').unlink()
                if mutation == 'empty': (root/'cgroup/cpuset.cpus.effective').write_text('')
                if mutation == 'contradictory':
                    (root/'cgroup/system.slice/unit/cpuset.cpus.effective').write_text('0-1')
                if mutation == 'parent':
                    (root/'cgroup/system.slice/unit/cgroup.controllers').write_text('cpu memory cpuset')
                if mutation == 'partial': (root/'cgroup/system.slice/cgroup.controllers').write_text('cpu')
                with self.assertRaises((ContractError,FileNotFoundError)): reader.read()

    def test_controller_quota_metadata_tampering_refused_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            rows = self.ohio_fixture(root).read()['ancestry']
            for mutation in ('stripped','partial','skip','duplicate','invalid','enable','present','cpu','root','type','repeat_root'):
                value = copy.deepcopy(rows)
                if mutation == 'stripped':
                    for row in value:
                        del row['controllers']; del row['subtree_control']
                if mutation == 'partial': del value[0]['controllers']
                if mutation == 'skip': value.pop(1)
                if mutation == 'duplicate': value[-1]['controllers'] += ' cpu'
                if mutation == 'invalid': value[-1]['controllers'] += ' +cpuset'
                if mutation == 'enable': value[1]['subtree_control'] += ' cpuset'
                if mutation == 'present': value[0]['cpuset_effective'] = '0-1'
                if mutation == 'cpu': value[0]['cpu_max'] = None
                if mutation == 'root': value[-1]['path'] = 'other'
                if mutation == 'type': value[-1]['cpuset_effective'] = 2
                if mutation == 'repeat_root': value.insert(-1,copy.deepcopy(value[-1]))
                with self.subTest(mutation=mutation), self.assertRaises(ContractError): quota(value)

    def test_controller_leaf_symlink_and_permission_failure_not_absence(self):
        for mutation in ('cpuset_link','controller_link','permission'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                reader = self.ohio_fixture(root)
                if mutation == 'cpuset_link':
                    (root/'cgroup/system.slice/unit/cpuset.cpus.effective').symlink_to(root/'missing')
                if mutation == 'controller_link':
                    leaf = root/'cgroup/system.slice/unit/cgroup.controllers'
                    leaf.unlink(); leaf.symlink_to(root/'cgroup/cgroup.controllers')
                if mutation == 'permission':
                    def denied(path):
                        if path.name == 'cpuset.cpus.effective': raise PermissionError('injected')
                        return text(path)
                    with patch('infra.stream.recorder_application_resources.text',side_effect=denied):
                        with self.assertRaises(PermissionError): reader.read()
                else:
                    with self.assertRaises(OSError): reader.read()

    def test_controller_change_inside_sample_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            reader = self.fixture(root)
            calls = 0
            def changing(path):
                nonlocal calls
                result = text(path)
                if path == root/'cgroup/cgroup.subtree_control':
                    calls += 1
                    if calls == 2: result += ' io'
                return result
            with patch('infra.stream.recorder_application_resources.text',side_effect=changing):
                with self.assertRaisesRegex(ContractError,'ancestry raced'): reader.read()

    def test_enabled_nested_cpuset_uses_observed_restrictions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            reader = self.ohio_fixture(root)
            mount = root/'cgroup'
            (mount/'cgroup.subtree_control').write_text('cpuset cpu memory')
            (mount/'system.slice/cgroup.controllers').write_text('cpuset cpu memory')
            (mount/'system.slice/cgroup.subtree_control').write_text('cpuset cpu memory')
            (mount/'system.slice/cpuset.cpus.effective').write_text('1')
            (mount/'system.slice/unit/cgroup.controllers').write_text('cpuset cpu memory')
            (mount/'system.slice/unit/cpuset.cpus.effective').write_text('1')
            (mount/'system.slice/unit/cpu.max').write_text('max 100000')
            self.assertEqual(reader.read()['effective_quota'], 1)
            # An enabled ancestor may stop distributing cpuset to its children.
            (mount/'system.slice/cgroup.subtree_control').write_text('cpu memory')
            (mount/'system.slice/unit/cgroup.controllers').write_text('cpu memory')
            (mount/'system.slice/unit/cpuset.cpus.effective').unlink()
            inherited = reader.read()
            self.assertIsNone(inherited['ancestry'][0]['cpuset_effective'])
            self.assertEqual(inherited['effective_quota'],1)
            (mount/'system.slice/cgroup.subtree_control').write_text('cpuset cpu memory')
            (mount/'system.slice/unit/cgroup.controllers').write_text('cpuset cpu memory')
            (mount/'system.slice/unit/cpuset.cpus.effective').write_text('0')
            with self.assertRaises(ContractError): reader.read()

    def test_ohio_resource_gate_recomputes_proof_and_retains_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            ancestry = self.ohio_fixture(root).read()['ancestry']
            value = resources()
            for row in value['rows']:
                for witness in (row['sample'],row['cpu_before']):
                    if witness is not None: witness['ancestry'] = copy.deepcopy(ancestry)
            result = resource_gate(value,1000,120,1120,declare()['budgets'],OWNER)
            self.assertEqual(result['verdict'],'pass',result)
            del value['rows'][10]['sample']['ancestry'][0]['controllers']
            result = resource_gate(value,1000,120,1120,declare()['budgets'],OWNER)
            self.assertEqual(result['verdict'],'unknown',result)

    def test_actual_read_fixture_current_rss_identity_and_root_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            reader = self.fixture(root)
            first = reader.read(rss=True)
            self.assertEqual(first['rss_bytes'], 102400)
            self.assertEqual(first['effective_quota'], .75)
            self.assertIsNone(first['ancestry'][-1]['cpu_max'])
            (root/'proc/10/stat').write_text('10 (fixture) '+' '.join(['S']+['0']*18+['124']))
            with self.assertRaises(ContractError): reader.read(rss=True)

    def test_missing_rss_duplicate_members_and_descendant_refused(self):
        for mutation in ('rss', 'duplicates', 'descendant'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                reader = self.fixture(root)
                if mutation == 'rss': (root/'proc/10/status').write_text('Name: fixture')
                if mutation == 'duplicates': (root/'cgroup/unit/cgroup.procs').write_text('10 10')
                if mutation == 'descendant': (root/'cgroup/unit/child').mkdir()
                with self.assertRaises(ContractError): reader.read(rss=True)

    def test_fifo_and_symlink_resource_files_refused_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'fifo'
            os.mkfifo(path)
            with self.assertRaises(ContractError): text(path)
            link = root/'link'
            link.symlink_to(path)
            with self.assertRaises(OSError): text(link)

    def test_parse_caps_and_ancestor_minimum(self):
        self.assertEqual(cpus('0-2,4'), {0, 1, 2, 4})
        self.assertEqual(quota(ANCESTRY), .75)
        rows = copy.deepcopy(ANCESTRY)
        rows[-1]['cpu_max'] = '25000 100000'
        self.assertEqual(quota(rows), .25)
        for value in ('2-1', '0-65536', '', 'x'):
            with self.assertRaises(ContractError): cpus(value)
        with self.assertRaises(ContractError): counters('x 1\nx 2')
        rows[0]['cpu_max'] = None
        with self.assertRaises(ContractError): quota(rows)

    def test_sampler_failure_retains_slot_and_late_evidence(self):
        class Clock:
            value = 999
            def now(self): return self.value
            def pause(self, seconds): self.value += seconds
        clock = Clock()
        class Reader:
            def read(self, **kwargs):
                raise OSError('raced')
        stop = threading.Event()
        stop.set()
        result = observe(Reader(), 1000, stop, clock=clock.now, pause=clock.pause)
        self.assertEqual(len(result['rows']), 1)
        self.assertIn('OSError', result['rows'][0]['error'])
        self.assertFalse(result['overflow'])


if __name__ == '__main__':
    unittest.main()
