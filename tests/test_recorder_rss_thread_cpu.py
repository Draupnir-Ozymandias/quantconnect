"""Offline RSS auxiliary timing faults, authoritative gates and worker publication."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_application_resources as resources
from infra.stream import recorder_persistence_worker as worker
from infra.stream.recorder_absolute_observer import observe_absolute
from infra.stream.recorder_application_budget import declare
from infra.stream.recorder_application_evaluator import resource_gate
from tests import test_recorder_application_components as fixtures
from tests.test_recorder_absolute_observer import Clock


POLICY_HASH = '6eb2509c03a390c53d3fdc31124177403638d700e1e4922ee8ce015e7cf81ee5'


class RssThreadCpuTests(unittest.TestCase):
    def reader(self, directory, cpu=lambda: 100, wall=None, enabled=True):
        fixture = fixtures.ResourceTests().fixture(Path(directory).resolve())
        return resources.LinuxReader(execute=True, proc=fixture.proc, mount=fixture.mount,
            pid=fixture.pid, monotonic=fixture.clock if wall is None else wall,
            rss_thread_cpu=enabled, thread_cpu_ns=cpu)

    def verify(self, sample):
        return resources.verify_rss_thread_cpu(sample, expected_thread_id=threading.get_ident())

    def test_pinned_identity_and_no_implicit_opt_in(self):
        self.assertEqual(payload_hash(resources.RSS_THREAD_CPU_POLICY), POLICY_HASH)
        with TemporaryDirectory() as d:
            reader = fixtures.ResourceTests().fixture(Path(d).resolve())
            with patch.object(reader, 'thread_cpu_ns', side_effect=AssertionError('unexpected')):
                self.assertNotIn('rss_thread_cpu', reader.read(rss=True))
            reader.rss_thread_cpu = True
            with patch.object(reader, 'thread_cpu_ns', side_effect=AssertionError('CPU pre-read instrumented')):
                self.assertNotIn('rss_thread_cpu', reader.read(rss=False))
        for option in (1, None, 'yes'):
            with self.assertRaises(ContractError):
                resources.LinuxReader(execute=True, rss_thread_cpu=option)
        with self.assertRaises(ContractError):
            resources.LinuxReader(execute=True, thread_cpu_ns=None)

    def test_actual_reader_call_placement_and_inclusive_wall_width(self):
        calls = []
        def wall():
            calls.append('wall')
            return 10 if len(calls) == 1 else 10.006
        stamps = iter([100, 2_000_100])
        def cpu():
            calls.append('cpu')
            return next(stamps)
        with TemporaryDirectory() as d:
            reader = self.reader(d, cpu, wall)
            check = reader.check_paths
            def paths():
                calls.append('paths')
                return check()
            with patch.object(reader, 'check_paths', side_effect=paths):
                sample = reader.read(rss=True)
        self.assertEqual(calls, ['wall', 'cpu', 'paths', 'paths', 'cpu', 'wall'])
        self.assertEqual((sample['before'], sample['after']), (10, 10.006))
        self.assertAlmostEqual(sample['after']-sample['before'], .006)
        self.assertEqual(self.verify(sample)['delta_ns'], 2_000_000)
        # Auxiliary CPU is not subtracted: a 6-ms read remains inadmissible.
        value = fixtures.resources()
        value['rows'][10]['sample']['after'] = value['rows'][10]['sample']['before']+.006
        value['rows'][10]['sample']['rss_thread_cpu'] = sample['rss_thread_cpu']
        result = resource_gate(value, 1000, 120, 1120, declare()['budgets'], fixtures.OWNER)
        self.assertEqual(result['verdict'], 'unknown')
        self.assertIn('resource_sample:10', result['unknowns'])

    def test_auxiliary_unknown_does_not_change_resource_acceptance(self):
        with TemporaryDirectory() as d:
            def unavailable(): raise OSError('unavailable')
            witness = self.reader(d, unavailable).read(rss=True)['rss_thread_cpu']
        value = fixtures.resources()
        sample = value['rows'][10]['sample']
        witness['sample_sha256'] = payload_hash(sample)
        witness.pop('witness_sha256'); witness['witness_sha256'] = payload_hash(witness)
        sample['rss_thread_cpu'] = witness
        self.assertEqual(self.verify(sample)['status'], 'unknown')
        self.assertEqual(resource_gate(value, 1000, 120, 1120, declare()['budgets'], fixtures.OWNER)['verdict'], 'pass')

    def test_cpu_clock_faults_and_invalid_readings_preserve_wall_and_rss(self):
        for bad in (OSError('x'*300), RuntimeError('unavailable'), True, -1, 1.5,
                    float('nan'), float('inf'), None, '100'):
            for endpoint in (0, 1):
                with self.subTest(bad=bad, endpoint=endpoint), TemporaryDirectory() as d:
                    values = [100, 200]; values[endpoint] = bad
                    def cpu():
                        value = values.pop(0)
                        if isinstance(value, Exception):
                            raise value
                        return value
                    wall = iter([10., 10.001])
                    sample = self.reader(d, cpu, lambda: next(wall)).read(rss=True)
                    witness = self.verify(sample)
                    self.assertEqual(values, [])  # two endpoints, no retry
                    self.assertEqual(witness['status'], 'unknown')
                    self.assertIsNone(witness['delta_ns'])
                    self.assertLessEqual(len(witness['error']), 160)
                    self.assertEqual(sample['rss_bytes'], 102400)
                    self.assertEqual((sample['before'], sample['after']), (10., 10.001))
                    json.dumps(sample, allow_nan=False)

    def test_regression_zero_delta_and_interrupt(self):
        for values, status in [([200, 100], 'unknown'), ([0, 0], 'observed')]:
            with TemporaryDirectory() as d:
                cpu = iter(values)
                sample = self.reader(d, lambda: next(cpu)).read(rss=True)
                self.assertEqual(self.verify(sample)['status'], status)
        with TemporaryDirectory() as d:
            reader = self.reader(d)
            with patch.object(reader, 'thread_cpu_ns', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                reader.read(rss=True)

    def test_wall_or_resource_fault_not_hidden_by_auxiliary_clock(self):
        for values in ([float('nan'), 11], [11, 10]):
            with TemporaryDirectory() as d:
                wall = iter(values)
                with self.assertRaises(ContractError):
                    self.reader(d, wall=lambda: next(wall)).read(rss=True)
        with TemporaryDirectory() as d:
            reader = self.reader(d)
            with patch.object(reader, 'clock', side_effect=OSError('wall unavailable')), self.assertRaises(OSError):
                reader.read(rss=True)
            with patch.object(reader, 'members', side_effect=OSError('process disappeared')), self.assertRaises(OSError):
                reader.read(rss=True)

    def test_sample_policy_thread_delta_and_publication_tampering_rejected(self):
        with TemporaryDirectory() as d:
            sample = self.reader(d).read(rss=True)
            published = worker.publish(Path(d)/'consumer.json', dict(case_sha256='case', sample=sample))
            loaded = worker.control(Path(d)/'consumer.json')
            self.assertEqual(published, loaded)
            self.verify(loaded['sample'])
            for kind in ('wall', 'rss', 'owner', 'policy', 'thread', 'delta', 'schema', 'missing', 'cpu_bool', 'error', 'hash'):
                value = deepcopy(sample); w = value['rss_thread_cpu']
                if kind == 'wall': value['before'] += .01
                if kind == 'rss': value['rss_bytes'] += 1024
                if kind == 'owner': value['owner']['pid'] += 1
                if kind == 'policy': w['policy_sha256'] = 'wrong'
                if kind == 'thread': w['thread_id'] += 1
                if kind == 'delta': w['delta_ns'] += 1
                if kind == 'schema': w['schema_version'] = 'future'
                if kind == 'missing': del value['rss_thread_cpu']
                if kind == 'cpu_bool': w['before_ns'] = True
                if kind == 'error': w['error'] = 'fault'; w['status'] = 'unknown'; w['delta_ns'] = None
                if kind == 'hash': w['witness_sha256'] = 'wrong'
                elif kind != 'missing':
                    w.pop('witness_sha256'); w['witness_sha256'] = payload_hash(w)
                with self.subTest(kind=kind), self.assertRaises(ContractError): self.verify(value)
            with self.assertRaises(ContractError):
                resources.verify_rss_thread_cpu(sample, expected_thread_id=True)
            data = deepcopy(loaded); data['sample']['after'] += .1
            (Path(d)/'consumer.json').write_text(json.dumps(data))
            with self.assertRaises(ContractError): worker.control(Path(d)/'consumer.json')

    def test_actual_consumer_monitor_and_absolute_observer_publish_linked_witnesses(self):
        self.consumer_publication(cpu_fault=False)

    def test_cpu_fault_survives_actual_consumer_publication(self):
        self.consumer_publication(cpu_fault=True)

    def consumer_publication(self, *, cpu_fault):
        with TemporaryDirectory() as d:
            root = Path(d); clock = Clock(); done = threading.Event()
            def cpu():
                if cpu_fault: raise OSError('CPU clock unavailable')
                return 100
            reader = self.reader(d, cpu, wall=lambda: clock.now()/1e9)
            case = dict(artifact_sha256='offline-case', boot_id='fixture-boot', epoch=30., spec={}, raw_bundle={})
            worker.publish(root/'server-ready.json', dict(case_sha256='offline-case',
                uri='ws://127.0.0.1:12345', identity=dict(boot_id='fixture-boot', cgroup='/producer')))
            def observer(reader, epoch, stop):
                result = observe_absolute(reader, epoch, stop, execute=True,
                    wait=clock.wait(), clock_ns=clock.now, capacity=2)
                done.set()
                return result
            def collect(*args, **kwargs):
                if not done.wait(3): raise AssertionError('monitor did not publish')
                return dict(status='fixture')
            with patch.object(worker, 'context', return_value=case), \
                 patch.object(worker, 'LinuxReader', return_value=reader) as factory, \
                 patch.object(worker, 'CompletionWitnesses', return_value=SimpleNamespace(snapshot=lambda p:{})), \
                 patch.object(worker, 'collect_with_completion', side_effect=collect):
                worker.consume(root, {}, execute=True, rss_thread_cpu=True, resource_observer=observer)
            factory.assert_called_once_with(execute=True, rss_thread_cpu=True)
            ready = worker.control(root/'observer-ready.json'); consumer = worker.control(root/'consumer.json')
            self.assertEqual(ready['case_sha256'], consumer['case_sha256'])
            self.assertEqual(ready['rss_thread_cpu_policy_sha256'], POLICY_HASH)
            self.assertEqual(consumer['rss_thread_cpu_policy_sha256'], POLICY_HASH)
            tid = ready['initial']['rss_thread_cpu']['thread_id']
            self.assertNotEqual(tid, threading.get_ident())
            samples = [ready['initial']] + [row['sample'] for row in consumer['resources']['rows']]
            self.assertEqual(len(samples), 3)
            for sample in samples:
                self.assertEqual(resources.verify_rss_thread_cpu(sample, expected_thread_id=tid)['status'],
                                 'unknown' if cpu_fault else 'observed')
            self.assertNotIn('rss_thread_cpu', consumer['resources']['rows'][0]['cpu_before'])
            self.assertIsNone(consumer['error']); self.assertFalse(consumer['observer_thread_alive'])
