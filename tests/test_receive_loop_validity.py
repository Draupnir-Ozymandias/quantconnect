from dataclasses import FrozenInstanceError, replace
import unittest

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity import (
    ProducerSample, SampleBuffer, CpuStamp, cpu_interval, CounterSample, counter_interval)


class ValidityTests(unittest.TestCase):
    def sample(self):
        return ProducerSample(0, 0, .1, .2, .3, 1.1, 1.2, 1.4, 1.5, 1, .8)

    def counter(self, **kwargs):
        base = CounterSample('boot', 10, 'start-10', '/private', 0, .01,
                             (('usage_usec', 100), ('nr_periods', 2),
                              ('nr_throttled', 0), ('throttled_usec', 0)))
        return replace(base, **kwargs)

    def test_exact_partition_and_absolute_sleep_request(self):
        result = self.sample().partition()
        self.assertAlmostEqual(sum(result['parts'].values()), 1.5)
        self.assertAlmostEqual(result['sleep_excess_seconds'], 0)
        self.assertAlmostEqual(result['begin_deadline_lateness_seconds'], .2)
        self.assertFalse(result['scheduler_causality_proven'])

    def test_known_oversleep_localized_without_cause_claim(self):
        r = replace(self.sample(), sleep_end=1.15).partition()
        self.assertAlmostEqual(r['sleep_excess_seconds'], .05)
        self.assertAlmostEqual(r['parts']['wake_to_begin'], .05)

    def test_slow_prepare_send_bookkeeping_localized(self):
        r = replace(self.sample(), pacing_begin=.15, send_start=1.45, send_end=1.8).partition()
        self.assertAlmostEqual(r['parts']['bookkeeping'], .15)
        self.assertAlmostEqual(r['parts']['preparation'], .25)
        self.assertAlmostEqual(r['parts']['send'], .35)

    def test_late_pacing_zero_request(self):
        r = replace(self.sample(), deadline=.1, requested_sleep=0).partition()
        self.assertAlmostEqual(r['sleep_excess_seconds'], .8)

    def test_negative_sleep_excess_is_not_clamped(self):
        self.assertLess(replace(self.sample(), sleep_end=1).partition()['sleep_excess_seconds'], 0)

    def test_invalid_sequence_order_request_and_nonfinite_refused(self):
        for changes in ({'sequence': True}, {'sequence': -1}, {'sleep_begin': .1},
                        {'requested_sleep': .9}, {'requested_sleep': -1},
                        {'deadline': float('nan')}, {'begin': float('inf')}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(self.sample(), **changes).partition()

    def test_immutable_sample(self):
        with self.assertRaises(FrozenInstanceError):
            self.sample().begin = 99

    def test_buffer_overflow_retains_prefix_no_success(self):
        b = SampleBuffer(1)
        self.assertTrue(b.append(self.sample()))
        self.assertFalse(b.append(replace(self.sample(), sequence=1)))
        self.assertFalse(b.append(replace(self.sample(), sequence=2)))
        r = b.finish()
        self.assertEqual(len(r['samples']), 1)
        self.assertTrue(r['overflow'])
        self.assertFalse(r['complete'])
        self.assertFalse(r['probe_cost_verified'])
        self.assertFalse(r['execution_authorized'])
        with self.assertRaises(ContractError): b.append(self.sample())
        with self.assertRaises(ContractError): b.finish()

    def test_buffer_complete_and_bounds(self):
        b = SampleBuffer(1)
        b.append(self.sample())
        self.assertTrue(b.finish()['complete'])
        for cap in (0, -1, True, 100001):
            with self.assertRaises(ContractError): SampleBuffer(cap)
        with self.assertRaises(ContractError): SampleBuffer(1).append({})

    def test_buffer_invalid_record_latches_failure_even_if_caught(self):
        b = SampleBuffer(2)
        b.append(self.sample())
        with self.assertRaises(ContractError):
            b.append(replace(self.sample(), sequence=2))
        self.assertFalse(b.append(self.sample()))
        r = b.finish()
        self.assertFalse(r['complete'])
        self.assertEqual(len(r['samples']), 1)
        self.assertIsNotNone(r['failure'])

    def test_buffer_disconnected_boundary_refused_and_empty_not_complete(self):
        b = SampleBuffer(2)
        b.append(self.sample())
        with self.assertRaises(ContractError):
            b.append(replace(self.sample(), sequence=1))
        self.assertFalse(b.finish()['complete'])
        self.assertFalse(SampleBuffer(1).finish()['complete'])

    def test_buffer_valid_continuous_intervals(self):
        b = SampleBuffer(2)
        b.append(self.sample())
        s = self.sample()
        second = replace(s, sequence=1, previous_send_end=1.5, pacing_begin=1.6,
                         request_at=1.7, sleep_begin=1.8, sleep_end=2.6, begin=2.7,
                         send_start=2.9, send_end=3, deadline=2.5)
        self.assertTrue(b.append(second))
        self.assertTrue(b.finish()['complete'])

    def test_cpu_acquisition_brackets_not_point_estimate(self):
        r = cpu_interval(CpuStamp(0, .1, .01, 1), CpuStamp(.1, .12, .11, 1))
        self.assertAlmostEqual(r['cpu_seconds'], .02)
        self.assertAlmostEqual(r['elapsed_lower_seconds'], .09)
        self.assertAlmostEqual(r['elapsed_upper_seconds'], .11)
        self.assertFalse(r['scheduler_causality_proven'])

    def test_thread_change_and_cpu_reset_unknown(self):
        a = CpuStamp(0, 1, .01, 1)
        for b, reason in ((CpuStamp(2, 2, 2.01, 2), 'thread_changed'),
                         (CpuStamp(2, .5, 2.01, 1), 'cpu_counter_reset')):
            r = cpu_interval(a, b)
            self.assertEqual(r['reason'], reason)
            self.assertIsNone(r['cpu_seconds'])

    def test_invalid_cpu_brackets_and_impossible_cpu_refused(self):
        a = CpuStamp(0, 0, .01, 1)
        for b in (CpuStamp(.1, 1, .11, 1), CpuStamp(.1, 0, .09, 1),
                  CpuStamp(.005, 0, .1, 1), CpuStamp(.1, -1, .11, 1)):
            with self.assertRaises(ContractError): cpu_interval(a, b)

    def test_counter_zero_is_observed_not_missing(self):
        a = self.counter()
        r = counter_interval(a, replace(a, read_begin=1, read_end=1.01))
        self.assertEqual(r['status'], 'observed')
        self.assertEqual(set(r['deltas'].values()), {0})
        self.assertFalse(r['event_specific_throttling_proven'])

    def test_counter_partial_does_not_invent_zero(self):
        r = counter_interval(self.counter(counters=(('usage_usec', 100),)),
                             self.counter(read_begin=1, read_end=1.01,
                                          counters=(('usage_usec', 200),)))
        self.assertEqual(r['status'], 'partial')
        self.assertEqual(r['deltas']['usage_usec'], 100)
        self.assertIsNone(r['deltas']['nr_throttled'])

    def test_counter_read_failure_retains_unknown(self):
        r = counter_interval(self.counter(), self.counter(read_begin=1, read_end=1.01,
                             error='permission_denied', counters=()))
        self.assertEqual(r['reason'], 'read_failed')
        self.assertTrue(all(v is None for v in r['deltas'].values()))

    def test_pid_reuse_boot_cgroup_and_start_identity_changes(self):
        for change in ({'pid': 11}, {'boot_id': 'other'}, {'cgroup': '/other'},
                       {'process_start_id': 'reused-pid'}):
            r = counter_interval(self.counter(), self.counter(read_begin=1, read_end=1.01, **change))
            self.assertEqual(r['reason'], 'identity_changed')

    def test_reset_does_not_rescue_other_fields(self):
        r = counter_interval(self.counter(), self.counter(read_begin=1, read_end=1.01,
                             counters=(('usage_usec', 99), ('nr_periods', 3))))
        self.assertEqual(r['reason'], 'counter_reset')
        self.assertTrue(all(v is None for v in r['deltas'].values()))

    def test_invalid_counter_shapes_negatives_duplicates_and_overlap(self):
        for changes in ({'counters': (('usage_usec', -1),)}, {'pid': True},
                        {'counters': (('other', 1),)}, {'counters': (('usage_usec', True),)},
                        {'counters': (('usage_usec', 1), ('usage_usec', 2))},
                        {'error': 'failed'}, {'read_begin': .5, 'read_end': .4}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.counter(**changes).validate()
        with self.assertRaises(ContractError):
            counter_interval(self.counter(), self.counter())


if __name__ == '__main__':
    unittest.main()
