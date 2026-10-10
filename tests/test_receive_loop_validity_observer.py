from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from execution_truth.contracts import ContractError, verify_artifact_hash
from infra.stream.receive_loop_validity import CounterSample
from infra.stream.receive_loop_validity_probe import CounterRead
from infra.stream.receive_loop_validity_observer import ObserverCore


TARGET = dict(boot_id='b', pid=10, process_start_id='s', cgroup='/worker')


class ObserverTests(unittest.TestCase):
    def core(self, lane, reader=None, capacity=2):
        return ObserverCore(lane, TARGET, execute=True, capacity=capacity,
                            monotonic=Mock(side_effect=[0, .01, .02, .03]),
                            sleep=Mock(), reader=reader)

    def test_controls_never_construct_or_read_counter_reader(self):
        with patch('infra.stream.receive_loop_validity_observer.CounterReader') as factory:
            for lane in ('control', 'pacing'):
                core = self.core(lane)
                core.tick(.005)
                r = core.finish()
                self.assertTrue(r['complete'])
                self.assertIsNone(r['rows'][0]['counter'])
                verify_artifact_hash(r, 'report_sha256', 'observer component')
            factory.assert_not_called()

    def test_full_reads_once_and_binds_target(self):
        sample = CounterSample('b', 10, 's', '/worker', .01, .011, (('usage_usec', 1),))
        result = CounterRead(sample, None)
        reader = Mock()
        reader.read.return_value = result
        reader.finish.return_value = dict(reads=(result,), complete=True)
        core = self.core('full', reader)
        core.tick(.005)
        reader.read.assert_called_once_with()
        r = core.finish()
        self.assertTrue(r['complete'])
        self.assertFalse(r['dedicated_cgroup_verified'])

    def test_identity_change_and_missing_data_retain_attempt(self):
        for result in (CounterRead(None, 'PermissionError'),
                       CounterRead(CounterSample('b', 11, 's', '/worker', .01, .011, ()), None)):
            reader = Mock(read=Mock(return_value=result))
            reader.finish.return_value = dict(reads=(result,), complete=result.sample is not None)
            core = self.core('full', reader)
            with self.assertRaises(ContractError): core.tick(.005)
            r = core.finish()
            self.assertEqual(len(r['rows']), 1)
            self.assertFalse(r['complete'])

    def test_capacity_no_extra_native_call_and_no_replay(self):
        core = self.core('control', capacity=1)
        core.tick(.005)
        calls = core.clock.call_count
        with self.assertRaises(ContractError): core.tick(.02)
        self.assertEqual(core.clock.call_count, calls)
        self.assertFalse(core.finish()['complete'])
        with self.assertRaises(ContractError): core.finish()

    def test_past_or_duplicate_tick_refused_not_catchup_burst(self):
        for deadline in (.005, .009):
            core = self.core('control')
            core.tick(.005)  # wake is .01
            with self.assertRaises(ContractError): core.tick(deadline)
            self.assertEqual(core.sleep.call_count, 1)
            self.assertFalse(core.finish()['complete'])

    def test_execution_and_identity_barriers(self):
        with self.assertRaises(ContractError): ObserverCore('control', TARGET)
        with self.assertRaises(ContractError): ObserverCore('full', {}, execute=True)
        with self.assertRaises(ContractError): ObserverCore('full', TARGET, execute=True, capacity=513)


if __name__ == '__main__': unittest.main()
