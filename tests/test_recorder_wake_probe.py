import unittest

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.recorder_wake_probe import collect, PLAN
from tests.test_recorder_counter_schedule import Clock


class WakeProbeTests(unittest.TestCase):
    def test_fixed_grid_population_baseline_and_hash(self):
        clock = Clock()
        result = collect(clock=clock.now, pause=clock.pause, execute=True)
        self.assertEqual(len(result['baseline']), 16)
        self.assertEqual(len(result['rows']), 12)
        self.assertAlmostEqual(result['rows'][-1]['target'], 133.3)
        self.assertTrue(all(r['status'] == 'observed' for r in result['rows']))
        self.assertEqual(result['plan_sha256'], payload_hash(PLAN))
        verify_artifact_hash(result, 'probe_sha256', 'probe')
        for key in ('native_origin_verified', 'acceptance_demonstrated',
                    'kernel_sleep_overshoot_isolated', 'orders_authorized'):
            self.assertFalse(result[key])

    def test_overshoot_retained_not_used_as_acceptance_or_new_epoch(self):
        clock = Clock(shift=.057973565)
        result = collect(clock=clock.now, pause=clock.pause, execute=True)
        row = result['rows'][0]
        self.assertAlmostEqual(row['wake_lateness_seconds'], .057973565)
        self.assertAlmostEqual(row['observed_request_excess_seconds'], .057973565)
        self.assertEqual(row['status'], 'observed')
        self.assertAlmostEqual(result['rows'][1]['target'], .15)
        self.assertFalse(result['acceptance_demonstrated'])

    def test_missed_slots_not_replayed(self):
        clock = Clock(shift=10)
        calls = []
        def pause(seconds):
            calls.append(seconds)
            clock.pause(seconds)
        result = collect(clock=clock.now, pause=pause, execute=True)
        self.assertLess(len(calls), 12)
        self.assertEqual(len(calls), sum(r['attempted'] for r in result['rows']))
        self.assertEqual(result['rows'][1]['error'], 'target_already_missed_no_catch_up')
        self.assertAlmostEqual(result['rows'][-1]['target'], 133.3)

    def test_early_return_no_retry(self):
        clock = Clock(shift=-.001)
        result = collect(clock=clock.now, pause=clock.pause, execute=True)
        self.assertTrue(all(r['error'] == 'early_return_no_retry' for r in result['rows']))
        self.assertTrue(all(r['attempted'] for r in result['rows']))

    def test_sleep_fault_stops_remaining_attempts_preserves_population(self):
        clock = Clock()
        def fail(_): raise OSError('injected')
        result = collect(clock=clock.now, pause=fail, execute=True)
        self.assertEqual(sum(r['attempted'] for r in result['rows']), 1)
        self.assertIsNone(result['rows'][0]['returned'])
        self.assertTrue(all(r['error'] == 'prior_clock_or_sleep_fault'
                            for r in result['rows'][1:]))

    def test_return_clock_regression_and_nonfinite_stop(self):
        for bad in (-1, float('nan'), float('inf')):
            clock = Clock()
            def pause(_): clock.value = bad
            result = collect(clock=clock.now, pause=pause, execute=True)
            self.assertEqual(sum(r['attempted'] for r in result['rows']), 1)
            self.assertIn('ContractError', result['rows'][0]['error'])

    def test_no_execution_or_baseline_regression_before_sleep(self):
        calls = []
        with self.assertRaises(ContractError):
            collect(clock=lambda: calls.append('clock'), pause=lambda _: None)
        self.assertEqual(calls, [])
        values = iter((1, .5, .6))
        with self.assertRaises(ContractError):
            collect(clock=lambda: next(values), pause=lambda _: calls.append('sleep'), execute=True)
        self.assertEqual(calls, [])


if __name__ == '__main__': unittest.main()
