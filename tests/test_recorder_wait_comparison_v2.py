from copy import deepcopy
import errno
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.recorder_absolute_wait import AbsoluteWait, NS
from infra.stream import recorder_wait_comparison as original
from infra.stream import recorder_wait_comparison_v2 as comparison
from infra.stream import recorder_wait_comparison_audit as audit


class WaitComparisonV2Tests(unittest.TestCase):
    def fixture(self, index=0, *, select_offset=0, absolute_offset=0,
                select_error=None, absolute_code=0, select_result=([], [], [])):
        clock = SimpleNamespace(value=10*NS)
        calls = []
        def select_call(read, write, error, seconds):
            calls.append(('select', read, write, error, seconds))
            if select_error:
                raise select_error
            # Fixture rounding is not native scheduling evidence.
            clock.value += round(seconds*NS)+select_offset
            return select_result
        def syscall(clock_id, flags, sec, ns):
            calls.append(('absolute', clock_id, flags, sec, ns))
            clock.value = sec*NS+ns+absolute_offset
            return absolute_code
        select = comparison.SelectWait(clock_ns=lambda: clock.value, select_call=select_call)
        absolute = AbsoluteWait(clock_ns=lambda: clock.value, syscall=syscall)
        result = comparison.collect_run(run_index=index, clock_ns=lambda: clock.value,
                                        select_wait=select, absolute_wait=absolute, execute=True)
        return result, calls, clock

    def rehash(self, result):
        result.pop('run_sha256', None)
        for row in result['rows']:
            if row['observation']:
                row['observation'].pop('wait_sha256', None)
                row['observation']['wait_sha256'] = payload_hash(row['observation'])
        result['run_sha256'] = payload_hash(result)
        return result

    def test_successor_hash_literal_and_unchanged_predecessor(self):
        self.assertEqual(comparison.declaration()['plan_sha256'],
                         'c501255908329a12c93cab58d6e7ffc0f44711175141749db8953c95c6a2982d')
        self.assertEqual(original.declaration()['plan_sha256'], comparison.PREDECESSOR_HASH)
        self.assertEqual(comparison.PLAN['interval_ns'], original.PLAN['interval_ns'])
        self.assertEqual(comparison.PLAN['run_blocks'], original.PLAN['run_blocks'])
        value = comparison.declaration()
        verify_artifact_hash(value, 'plan_sha256', 'v2 declaration')
        value['interval_ns'][0] = 1
        self.assertEqual(comparison.PLAN['interval_ns'][0], 50_000_000)

    def test_complete_population_exact_targets_requests_and_unknown_retries(self):
        for index in (0, 1):
            run, calls, _ = self.fixture(index)
            audit.validate_run(run)
            self.assertEqual(len(calls), 12)
            self.assertEqual(run['rows'][-1]['target_ns'], 143_300_000_000)
            self.assertEqual(len(run['baseline']), 16)
            self.assertIsNone(run['fatal_error'])
            for row in run['rows']:
                obs = row['observation']
                self.assertEqual(obs['status'], 'observed')
                self.assertEqual(obs['retries'], 0)
                if row['arm'] == 'select':
                    self.assertIsNone(obs['internal_retry_count'])
                    self.assertEqual(obs['requested_seconds_ratio'], list((row['interval_ns']/NS).as_integer_ratio()))
            self.assertTrue(all(not run[key] for key in ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized')))

    def test_finite_analysis_exact_pairs_and_descriptive_stats(self):
        runs = [self.fixture(index, select_offset=2, absolute_offset=1)[0] for index in (0, 1)]
        summary = audit.evaluate(runs)
        verify_artifact_hash(summary, 'summary_sha256', 'summary')
        self.assertTrue(summary['comparison_complete'])
        self.assertEqual(len(summary['pairs']), 12)
        self.assertTrue(all(pair['absolute_minus_select_ns'] == -1 for pair in summary['pairs']))
        for stats in summary['interval_statistics']:
            self.assertEqual(stats['median_difference_ns_ratio'], [-1, 1])
            self.assertEqual(stats['arms']['select']['median_ns_ratio'], [2, 1])
        self.assertEqual(summary['arm_counts']['absolute'], dict(observed=12, unknown=0))
        self.assertFalse(summary['acceptance_demonstrated'])

    def test_eintr_and_early_return_stop_without_second_run(self):
        for kwargs in (dict(select_error=InterruptedError('signal')),
                       dict(absolute_code=errno.EINTR), dict(select_offset=-1),
                       dict(absolute_offset=-1), dict(select_result=([1], [], []))):
            with self.subTest(kwargs=kwargs):
                run, calls, _ = self.fixture(**kwargs)
                audit.validate_run(run)
                self.assertIsNotNone(run['fatal_error'])
                cancelled = comparison.cancelled_run(1)
                summary = audit.evaluate([run, cancelled])
                self.assertFalse(summary['comparison_complete'])
                self.assertTrue(all(row['observation'] is None for row in run['rows'][len(calls):]))
                self.assertTrue(all(stats['median_difference_ns_ratio'] is None for stats in summary['interval_statistics']))

    def test_missed_target_unknown_without_call_then_original_grid_continues(self):
        run, calls, _ = self.fixture(absolute_offset=60_000_000)
        audit.validate_run(run)
        self.assertIsNone(run['fatal_error'])
        # Run 0 has absolute in the final block; use run 1 for cross-block miss.
        run, calls, _ = self.fixture(1, absolute_offset=60_000_000)
        audit.validate_run(run)
        self.assertEqual(run['rows'][6]['observation']['error'], 'target_already_missed_no_catch_up')
        self.assertFalse(run['rows'][6]['observation']['attempted'])
        self.assertEqual(len(calls), 11)
        self.assertIsNone(run['fatal_error'])

    def test_guards_before_injected_clock_or_request(self):
        calls = []
        with self.assertRaises(ContractError):
            comparison.collect_run(run_index=0, clock_ns=lambda: calls.append('clock'),
                                   select_wait=None, absolute_wait=None)
        with self.assertRaises(ContractError):
            comparison.SelectWait(clock_ns=lambda: calls.append('clock'), select_call=None).wait(100)
        self.assertEqual(calls, [])

    def test_baseline_fault_partial_receipt_and_second_run_cancellation(self):
        values = iter((100, 101, 102, -1))
        run = comparison.collect_run(run_index=0, clock_ns=lambda: next(values),
                                     select_wait=None, absolute_wait=None, execute=True)
        audit.validate_run(run)
        self.assertIsNone(run['epoch_ns'])
        self.assertEqual(len(run['baseline']), 1)
        summary = audit.evaluate([run, comparison.cancelled_run(1)])
        self.assertEqual(summary['arm_counts']['select']['unknown'], 12)
        self.assertTrue(all(pair['lateness_ns'] == {'select': None, 'absolute': None} for pair in summary['pairs']))

    def test_clock_regression_refused_before_any_wait(self):
        values = iter([100]*33+[99])
        run = comparison.collect_run(run_index=0, clock_ns=lambda: next(values),
                                     select_wait=None, absolute_wait=None, execute=True)
        audit.validate_run(run)
        self.assertEqual(run['rows'][0]['error'], 'ContractError:comparison clock regressed before attempt')
        self.assertTrue(all(row['observation'] is None for row in run['rows']))

    def test_long_exception_and_select_return_clock_fault_bounded(self):
        run, _, _ = self.fixture(select_error=OSError('x'*500))
        self.assertEqual(len(run['fatal_error']), 160)
        audit.validate_run(run)
        values = iter((1, -1))
        wait = comparison.SelectWait(clock_ns=lambda: next(values), select_call=lambda *args: ([], [], []))
        row = wait.wait(200, execute=True)
        self.assertEqual(row['status'], 'unknown')
        self.assertIsNone(row['after_ns'])
        self.assertIsNone(row['lateness_ns'])

    def test_rehashed_tampering_is_not_accepted_as_valid_arithmetic(self):
        good = self.fixture()[0]
        mutations = [lambda r: r['rows'][0].update(target_ns=1),
                     lambda r: r['rows'][0]['observation'].update(lateness_ns=7),
                     lambda r: r['rows'][0]['observation'].update(internal_retry_count=0),
                     lambda r: r['rows'][0]['observation'].update(requested_seconds_ratio=[1, 1]),
                     lambda r: r.update(orders_authorized=True),
                     lambda r: r['rows'][0]['observation'].update(retries=1),
                     lambda r: r.update(fatal_error='invented'),
                     lambda r: r['rows'].pop(),
                     lambda r: r['rows'][0]['observation'].update(error='x'*161),
                     lambda r: r.update(plan_sha256=original.declaration()['plan_sha256'])]
        for mutation in mutations:
            bad = deepcopy(good)
            mutation(bad)
            with self.assertRaises(ContractError): audit.validate_run(self.rehash(bad))

    def test_evaluator_rejects_reordered_runs_and_unauthorized_resume(self):
        good = [self.fixture(index)[0] for index in (0, 1)]
        with self.assertRaises(ContractError): audit.evaluate(list(reversed(good)))
        fatal = self.fixture(select_error=OSError('failure'))[0]
        with self.assertRaises(ContractError): audit.evaluate([fatal, good[1]])
        with self.assertRaises(ContractError): audit.evaluate([good[0], comparison.cancelled_run(1)])

    def test_select_refusals_and_internal_retries_remain_unknown(self):
        values = SimpleNamespace(now=100)
        calls = []
        adapter = comparison.SelectWait(clock_ns=lambda: values.now, select_call=lambda *args: calls.append(args))
        for target in (100, 99, 100+60*NS+1):
            row = adapter.wait(target, execute=True)
            self.assertFalse(row['attempted'])
            self.assertIsNone(row['internal_retry_count'])
            self.assertEqual(row['retries'], 0)
        values.now = 50
        row = adapter.wait(200, execute=True)
        self.assertEqual(row['error'], 'clock_regressed_between_waits')
        self.assertEqual(calls, [])

    def test_pair_lifecycle_publishes_before_next_factory_and_cancels_fatal(self):
        for fatal in (False, True):
            events = []
            def factory(index):
                events.append(('factory', index))
                clock = SimpleNamespace(value=NS)
                def select_call(*args):
                    if fatal:
                        raise InterruptedError('signal')
                    clock.value += round(args[-1]*NS)
                    return ([], [], [])
                def syscall(clock_id, flags, sec, ns):
                    clock.value = sec*NS+ns
                    return 0
                return dict(clock_ns=lambda: clock.value,
                            select_wait=comparison.SelectWait(clock_ns=lambda: clock.value, select_call=select_call),
                            absolute_wait=AbsoluteWait(clock_ns=lambda: clock.value, syscall=syscall))
            runs = comparison.collect_pair(run_factory=factory,
                                           publish=lambda index, result: events.append(('publish', index)), execute=True)
            audit.evaluate(runs)
            expected = [('factory', 0), ('publish', 0)]
            if not fatal:
                expected.append(('factory', 1))
            expected.append(('publish', 1))
            self.assertEqual(events, expected)
            events.clear()
            def fail_publish(index, result):
                events.append(('publish', index))
                raise OSError('injected publication failure')
            with self.assertRaises(OSError):
                comparison.collect_pair(run_factory=factory, publish=fail_publish, execute=True)
            self.assertEqual(events, [('factory', 0), ('publish', 0)])

    def test_pair_guard_prevents_factory_or_publication(self):
        calls = []
        with self.assertRaises(ContractError):
            comparison.collect_pair(run_factory=lambda index: calls.append(index),
                                    publish=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_byte_cap_precedes_publication_and_summary_is_exclusive(self):
        runs = [self.fixture(index)[0] for index in (0, 1)]
        oversized = deepcopy(runs[0])
        oversized['unexpected'] = 'x'*comparison.PLAN['max_result_bytes_per_run']
        with TemporaryDirectory() as directory:
            absent = Path(directory)/'oversized.json'
            with self.assertRaises(ContractError): audit.publish_run(absent, self.rehash(oversized))
            self.assertFalse(absent.exists())
            path = Path(directory)/'summary.json'
            receipt = audit.publish_summary(path, runs)
            self.assertEqual(receipt['file_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(json.loads(path.read_text()), audit.evaluate(runs))
            with self.assertRaises(FileExistsError): audit.publish_summary(path, runs)

    def test_exclusive_publication_hash_and_invalid_no_file(self):
        run = self.fixture()[0]
        with TemporaryDirectory() as directory:
            path = Path(directory)/'result.json'
            receipt = audit.publish_run(path, run)
            self.assertEqual(json.loads(path.read_text()), run)
            self.assertEqual(receipt['file_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): audit.publish_run(path, run)
            self.assertEqual(path.read_bytes(), before)
            invalid = deepcopy(run)
            invalid['orders_authorized'] = True
            absent = Path(directory)/'invalid.json'
            with self.assertRaises(ContractError): audit.publish_run(absent, self.rehash(invalid))
            self.assertFalse(absent.exists())


if __name__ == '__main__': unittest.main()
