from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity_probe import (
    CounterReader, PacingProbe, cpu_stamp, parse_cpu_stat, process_start, unified_cgroup)


class ProbeTests(unittest.TestCase):
    def probe(self, **kwargs):
        return PacingProbe(2, monotonic=Mock(side_effect=[i/10 for i in range(30)]),
                           sleep=Mock(), **kwargs)

    def test_native_calls_once_and_exact_return_and_clock_order(self):
        p = self.probe()
        raw, result = object(), object()
        prepare, send = Mock(return_value=raw), Mock(return_value=result)
        self.assertIs(p.step(1, prepare, send), result)
        prepare.assert_called_once_with(.5)
        send.assert_called_once_with(raw)
        p.sleep.assert_called_once_with(.8)
        report = p.finish()
        self.assertTrue(report['complete'])
        self.assertEqual(report['samples'][0].send_end, .7)
        self.assertFalse(report['probe_cost_verified'])

    def test_native_exception_identity_and_no_retry(self):
        for stage in ('sleep', 'prepare', 'send'):
            p = self.probe()
            failure = OSError('injected native fault')
            prepare, send = Mock(return_value='raw'), Mock(return_value='ok')
            {'sleep': p.sleep, 'prepare': prepare, 'send': send}[stage].side_effect = failure
            with self.subTest(stage=stage), self.assertRaises(OSError) as caught:
                p.step(1, prepare, send)
            self.assertIs(caught.exception, failure)
            with self.assertRaises(ContractError): p.step(1, prepare, send)
            self.assertFalse(p.finish()['complete'])
            self.assertEqual(send.call_count, 1 if stage == 'send' else 0)

    def test_clock_fault_after_send_preserves_calls_but_blocks_success(self):
        clock = Mock(side_effect=[0, .1, .2, .3, .4, .5, .6, RuntimeError('clock')])
        p = PacingProbe(1, monotonic=clock, sleep=Mock())
        prepare, send = Mock(return_value='raw'), Mock(return_value='native')
        with self.assertRaises(RuntimeError): p.step(1, prepare, send)
        self.assertEqual(send.call_count, 1)
        self.assertFalse(p.finish()['complete'])

    def test_clock_fault_at_every_boundary_never_retries_native(self):
        for boundary in range(1, 8):
            stamps = [i/10 for i in range(8)]
            stamps[boundary] = RuntimeError('injected clock fault')
            p = PacingProbe(1, monotonic=Mock(side_effect=stamps), sleep=Mock())
            prepare, send = Mock(return_value='raw'), Mock()
            with self.subTest(boundary=boundary), self.assertRaises(RuntimeError):
                p.step(1, prepare, send)
            self.assertLessEqual(p.sleep.call_count, 1)
            self.assertLessEqual(prepare.call_count, 1)
            self.assertLessEqual(send.call_count, 1)
            self.assertFalse(p.finish()['complete'])

    def test_invalid_clock_fails_before_sleep_or_prepare(self):
        for stamp in (float('nan'), -.1):
            p = PacingProbe(1, monotonic=Mock(side_effect=[0, stamp]), sleep=Mock())
            prepare = Mock()
            with self.assertRaises(ContractError): p.step(1, prepare, Mock())
            p.sleep.assert_not_called()
            prepare.assert_not_called()
            self.assertFalse(p.finish()['complete'])

    def test_bound_before_extra_operations_and_finish_single_use(self):
        p = PacingProbe(1, monotonic=Mock(side_effect=[i/10 for i in range(30)]), sleep=Mock())
        prepare, send = Mock(return_value='raw'), Mock(return_value='ok')
        p.step(1, prepare, send)
        with self.assertRaises(ContractError): p.step(2, prepare, send)
        self.assertEqual(send.call_count, 1)
        self.assertFalse(p.finish()['complete'])
        with self.assertRaises(ContractError): p.finish()

    def test_two_contiguous_steps(self):
        p = self.probe()
        p.step(1, lambda t:'x', lambda raw:None)
        p.step(2, lambda t:'x', lambda raw:None)
        r = p.finish()
        self.assertTrue(r['complete'])
        self.assertEqual(r['samples'][1].previous_send_end, r['samples'][0].send_end)

    def test_cross_thread_refused_before_native_call(self):
        p = self.probe()
        send = Mock()
        with patch('infra.stream.receive_loop_validity_probe.threading.get_ident', return_value=-1):
            with self.assertRaises(ContractError): p.step(1, Mock(), send)
        send.assert_not_called()
        self.assertFalse(p.finish()['complete'])

    def test_cpu_sampling_acquisition_order(self):
        calls = []
        def wall(): calls.append('wall'); return len(calls)
        def cpu(): calls.append('cpu'); return .1
        def identity(): calls.append('identity'); return 1
        stamp = cpu_stamp(wall=wall, cpu=cpu, identity=identity)
        self.assertEqual(calls, ['identity', 'wall', 'cpu', 'wall'])
        self.assertLess(stamp.wall_before, stamp.wall_after)

    def test_stat_parsers_and_unknown_fields(self):
        self.assertEqual(parse_cpu_stat('usage_usec 10\nfuture 99\n'), (('usage_usec', 10),))
        for text in ('usage_usec -1', 'usage_usec 1\nusage_usec 2', 'nr_periods nan', 'bad'):
            with self.assertRaises(ContractError): parse_cpu_stat(text)
        text = '10 (name with ) spaces) '+' '.join(['S']+['0']*18+['123'])
        self.assertEqual(process_start(text, 10), '123')
        with self.assertRaises(ContractError): process_start(text, 11)
        self.assertEqual(unified_cgroup('0::/private\n'), '/private')
        for text in ('0::/../escape', '0::/x\n0::/y', '1:cpu:/x', '0::relative'):
            with self.assertRaises(ContractError): unified_cgroup(text)

    def fixture(self, root):
        proc, mount = root/'proc', root/'cgroup'
        (proc/'sys/kernel/random').mkdir(parents=True)
        (proc/'10').mkdir()
        (mount/'private').mkdir(parents=True)
        (proc/'sys/kernel/random/boot_id').write_text('fixture-boot')
        (proc/'10/stat').write_text('10 (fixture) '+' '.join(['S']+['0']*18+['123']))
        (proc/'10/cgroup').write_text('0::/private\n')
        (mount/'private/cpu.stat').write_text('usage_usec 12\nnr_throttled 0\n')
        return CounterReader(10, 2, proc_root=proc, cgroup_root=mount,
                             monotonic=Mock(side_effect=range(20)))

    def test_bounded_reader_native_fixture_partial_fields_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self.fixture(Path(tmp))
            result = reader.read()
            self.assertIsNone(result.error)
            self.assertEqual(dict(result.sample.counters), {'usage_usec': 12, 'nr_throttled': 0})
            self.assertEqual(result.sample.process_start_id, '123')
            reader.read()
            with self.assertRaises(ContractError): reader.read()
            self.assertFalse(reader.finish()['complete'])
            with self.assertRaises(ContractError): reader.read()
            with self.assertRaises(ContractError): reader.finish()

    def test_missing_process_permission_and_identity_change_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            reader = self.fixture(Path(tmp))
            with patch.object(reader, '_identity', side_effect=PermissionError):
                self.assertEqual(reader.read().error, 'PermissionError')
            with patch.object(reader, '_identity', side_effect=[('b', '1', '/private'), ('b', '2', '/private')]):
                self.assertIsNone(reader.read().sample)
            self.assertFalse(reader.finish()['complete'])

    def test_symlink_and_oversized_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reader = self.fixture(root)
            path = root/'cgroup/private/cpu.stat'
            path.write_text('x'*4097)
            self.assertIsNone(reader.read().sample)
            path.unlink()
            path.symlink_to(root/'proc/10/stat')
            self.assertIsNone(reader.read().sample)
            self.assertFalse(reader.finish()['complete'])

    def test_empty_reader_not_complete_and_bad_capacity_refused(self):
        self.assertFalse(CounterReader(10).finish()['complete'])
        for pid, cap in ((True, 1), (0, 1), (1, 0), (1, 1025)):
            with self.assertRaises(ContractError): CounterReader(pid, cap)


if __name__ == '__main__': unittest.main()
