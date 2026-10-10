from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_validity_worker import WorkloadCore, verify_core


class CoreTests(unittest.TestCase):
    def core(self, lane, n=3):
        clock = Mock(side_effect=[i/1000 for i in range(300)])
        core = WorkloadCore(lane, n, execute=True, monotonic=clock, sleep=Mock(),
                            cpu=Mock(side_effect=[i/100000 for i in range(100)]))
        return core, clock

    def result(self, lane):
        core, clock = self.core(lane)
        for i in range(3): core.step(.1+i/10)
        return core.finish(), clock

    def test_identical_input_and_independent_occurrences_all_lanes(self):
        reports = [self.result(lane)[0] for lane in ('control', 'pacing', 'full')]
        self.assertEqual(reports[0]['raws'], reports[1]['raws'])
        self.assertEqual(reports[1]['raws'], reports[2]['raws'])
        for report in reports:
            self.assertEqual(verify_core(report)['verified_occurrences'], 3)
            self.assertFalse(report['protocol_workload'])
            self.assertFalse(report['resource_audited'])

    def test_exact_wall_cpu_and_sleep_call_counts(self):
        for lane, calls in (('control', 4), ('pacing', 7), ('full', 11)):
            core, clock = self.core(lane)
            for i in range(3): core.step(.1+i/10)
            self.assertEqual(clock.call_count, 1+3*calls)
            self.assertEqual(core.cpu.call_count, 6 if lane == 'full' else 0)
            self.assertEqual(core.sleep.call_count, 3)

    def test_execution_barrier_and_bounds(self):
        with self.assertRaises(ContractError): WorkloadCore('control')
        for lane, n in (('bad', 1), ('control', 0), ('full', 30001), ('control', True)):
            with self.assertRaises(ContractError): WorkloadCore(lane, n, execute=True)

    def test_overflow_before_extra_native_operation(self):
        core, clock = self.core('pacing', 1)
        core.step(.1)
        calls = clock.call_count
        with self.assertRaises(ContractError): core.step(.2)
        self.assertEqual(clock.call_count, calls)
        r = core.finish()
        self.assertEqual(len(r['raws']), 1)
        self.assertFalse(r['complete'])
        with self.assertRaises(ContractError): verify_core(r)
        with self.assertRaises(ContractError): core.finish()

    def test_native_prepare_failure_retains_prefix_and_exact_exception(self):
        core, _ = self.core('control')
        core.step(.1)
        error = OSError('prepare fault')
        with patch('infra.stream.receive_loop_validity_worker.prepare', side_effect=error):
            with self.assertRaises(OSError) as caught: core.step(.2)
        self.assertIs(caught.exception, error)
        r = core.finish()
        self.assertEqual(len(r['raws']), 1)
        self.assertFalse(r['complete'])

    def test_cpu_fault_after_send_preserves_delivered_raw(self):
        core, _ = self.core('full')
        core.cpu.side_effect = [.1, RuntimeError('CPU fault')]
        with self.assertRaises(RuntimeError): core.step(.1)
        r = core.finish()
        self.assertEqual(len(r['raws']), 1)
        self.assertEqual(r['completed_steps'], 0)
        self.assertFalse(r['complete'])

    def test_rehashed_occurrence_and_acceptance_tampering_refused(self):
        report, _ = self.result('full')
        for change in ('duplicate', 'claim', 'cpu', 'boundary'):
            r = deepcopy(report)
            if change == 'duplicate': r['raws'][1] = r['raws'][0]
            elif change == 'claim': r['resource_audited'] = True
            elif change == 'cpu': r['cpu_pairs'].pop()
            else: r['rows'][1]['previous_send_end'] -= .001
            r.pop('report_sha256'); r['report_sha256'] = payload_hash(r)
            with self.subTest(change=change), self.assertRaises(ContractError): verify_core(r)

    def test_partial_workload_not_complete(self):
        core, _ = self.core('pacing')
        core.step(.1)
        r = core.finish()
        self.assertFalse(r['complete'])
        with self.assertRaises(ContractError): verify_core(r)


if __name__ == '__main__': unittest.main()
