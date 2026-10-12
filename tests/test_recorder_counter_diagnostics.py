import copy
import unittest

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_counter_diagnostics import describe
from infra.stream.recorder_counter_schedule import scheduled_window, POLICY
from tests.test_recorder_counter_schedule import Clock, Probe


class TimingDiagnosticsTests(unittest.TestCase):
    def schedule(self, shifts=(0, 0), **kwargs):
        clock = Clock()
        probe = Probe(clock, **kwargs)
        sleeps = []
        def pause(seconds):
            sleeps.append(seconds)
            clock.value += seconds+shifts[len(sleeps)-1]
        value = scheduled_window(probe, 1, 0, execute=True,
                                 clock=clock.now, pause=pause)
        return value, probe, sleeps

    def test_native_late_wake_shape_without_native_claim(self):
        value, probe, sleeps = self.schedule((.004991236, .057973565))
        report = describe(value)
        self.assertEqual(probe.calls, 1)
        self.assertEqual(len(sleeps), 2)
        self.assertAlmostEqual(report['rows'][1]['wake_lateness_ms'], 57.973565)
        self.assertAlmostEqual(report['rows'][1]['deadline_excess_ms'], 7.973565)
        self.assertIsNone(report['rows'][1]['counter_read_ms'])
        self.assertEqual(report['wake_cause'], 'unidentified')
        for flag in ('sleep_overshoot_measured', 'native_origin_verified',
                     'acceptance_demonstrated', 'orders_authorized'):
            self.assertFalse(report[flag])

    def test_wake_guard_read_decomposition(self):
        value, probe, _ = self.schedule()
        row = describe(value)['rows'][0]
        self.assertAlmostEqual(row['wake_lateness_ms'], 0)
        self.assertAlmostEqual(row['pre_read_guard_ms'], 3)
        self.assertAlmostEqual(row['counter_read_ms'], .1)
        self.assertAlmostEqual(row['post_read_guard_ms'], 3)
        self.assertAlmostEqual(row['total_guard_envelope_ms'], 6.1)
        self.assertAlmostEqual(row['boundary_margin_ms'], 46.9)
        self.assertEqual(probe.calls, 2)

    def test_valid_wake_does_not_guarantee_boundary(self):
        value, probe, _ = self.schedule((.049, 0))
        row = describe(value)['rows'][0]
        self.assertEqual(probe.calls, 2)
        self.assertLess(row['boundary_margin_ms'], 0)
        self.assertEqual(row['error'], 'pre_counter_did_not_finish_before_boundary')
        self.assertFalse(value['enclosure_verified'])

    def test_final_wake_limit_edges_no_retry_or_retiming(self):
        # Use adjacent margins rather than assuming exact decimal float equality.
        for shift, attempted in ((.049999, True), (.050001, False), (-.001, False)):
            value, probe, sleeps = self.schedule((0, shift))
            self.assertEqual(value['rows'][1]['attempted'], attempted)
            self.assertEqual(probe.calls, 2 if attempted else 1)
            self.assertEqual(len(sleeps), 2)
            self.assertEqual([r['target'] for r in value['rows']], [.95, 61])
            describe(value)

    def test_probe_cost_is_not_wake_lateness(self):
        value, _, _ = self.schedule(slow=True)
        row = describe(value)['rows'][0]
        self.assertEqual(row['wake_lateness_ms'], 0)
        self.assertAlmostEqual(row['counter_read_ms'], 6)
        self.assertEqual(row['error'], 'counter_bracket_too_wide')

    def test_hash_policy_population_and_endpoint_tampering_refused(self):
        original, _, _ = self.schedule()
        for change in ('hash', 'policy', 'rows', 'endpoint', 'authority'):
            value = copy.deepcopy(original)
            if change == 'hash': value['boundary'] = 2
            if change == 'policy': value['policy']['wake_lateness_max_seconds'] = .1
            if change == 'rows': value['rows'].pop()
            if change == 'endpoint': value['rows'][0]['endpoint']['before'] += .1
            if change == 'authority': value['acceptance_demonstrated'] = True
            if change != 'hash':
                value.pop('schedule_sha256')
                value['schedule_sha256'] = payload_hash(value)
            with self.assertRaises(ContractError): describe(value)
        self.assertEqual(POLICY['wake_lateness_max_seconds'], .05)

    def test_description_does_not_mutate_source(self):
        value, _, _ = self.schedule()
        before = copy.deepcopy(value)
        self.assertEqual(describe(value), describe(value))
        self.assertEqual(before, value)

    def test_sleep_exception_retains_unknown_without_retry(self):
        clock = Clock()
        probe = Probe(clock)
        sleeps = []
        def pause(seconds):
            sleeps.append(seconds)
            if len(sleeps) == 1:
                raise OSError('injected sleep failure')
            clock.value += seconds
        value = scheduled_window(probe, 1, 0, execute=True,
                                 clock=clock.now, pause=pause)
        report = describe(value)
        self.assertEqual(len(sleeps), 2)
        self.assertEqual(probe.calls, 1)
        self.assertIsNone(report['rows'][0]['wake_lateness_ms'])
        self.assertIn('OSError', report['rows'][0]['error'])
        self.assertEqual(report['rows'][1]['status'], 'observed')
        self.assertFalse(report['source_enclosure_verified'])


if __name__ == '__main__':
    unittest.main()
