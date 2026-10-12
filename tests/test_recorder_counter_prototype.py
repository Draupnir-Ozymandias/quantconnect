import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_counter_prototype import endpoint, window, validate_endpoint, NativeCounterProbe, CAP
from tests import test_recorder_application_components as fixtures


def make(at, usage=100, read_cost=.0001, guard_cost=.003, raw=None):
    class Clock:
        value = at
        def now(self): return self.value
    clock = Clock()
    calls = []
    def guard():
        before = clock.value
        clock.value += guard_cost
        sample = fixtures.sample(before, usage-1 if not calls else usage+1)
        sample['after'] = clock.value
        calls.append('guard')
        return sample
    def read():
        calls.append('read')
        clock.value += read_cost
        return raw if raw is not None else ('usage_usec '+str(usage)+'\nnr_throttled 0\n').encode()
    return endpoint(read,guard,clock.now),calls


def rehash(value):
    value.pop('endpoint_sha256')
    value['endpoint_sha256'] = payload_hash(value)
    return value


class CounterPrototypeTests(unittest.TestCase):
    def test_narrow_bracket_retains_separate_total_guard_cost(self):
        value,calls = make(1)
        self.assertEqual(calls,['guard','read','guard'])
        self.assertAlmostEqual(value['after']-value['before'],.0001)
        self.assertGreater(value['total_end']-value['total_begin'],.006)
        self.assertFalse(value['acceptance_demonstrated'])
        self.assertFalse(value['native_origin_binding_verified'])
        self.assertFalse(value['orders_authorized'])

    def test_fixed_window_conservative_delta_no_interpolation(self):
        start,_ = make(.99,100)
        end,_ = make(61.001,45000100)
        result = window(start,end,1)
        self.assertEqual(result['cpu_fraction_upper'],1)
        self.assertFalse(result['acceptance_demonstrated'])
        self.assertEqual(result['duration'],60)

    def test_late_preboundary_and_early_postboundary_refused(self):
        valid_start,_ = make(.99)
        valid_end,_ = make(61.001)
        late,_ = make(1)
        early,_ = make(60.99)
        for start,end in ((late,valid_end),(valid_start,early)):
            with self.assertRaisesRegex(ContractError,'do not enclose'): window(start,end,1)
        for kwargs in ({'duration':59},{'duration':60.0},{'bracket_max':.01}):
            with self.assertRaises(ContractError): window(valid_start,valid_end,1,**kwargs)

    def test_slow_read_reset_and_changed_quota_never_accepted(self):
        start,_ = make(.98,100)
        end,_ = make(61.001,200,read_cost=.006)
        with self.assertRaisesRegex(ContractError,'exceeds'): window(start,end,1)
        reset,_ = make(61.001,50)
        with self.assertRaisesRegex(ContractError,'reset'): window(start,reset,1)
        end,_ = make(61.001,200)
        for guard in ('guard_before','guard_after'):
            end[guard]['ancestry'][0]['cpu_max'] = '50000 100000'
            end[guard]['effective_quota'] = .5
        rehash(end)
        with self.assertRaisesRegex(ContractError,'guards differ'): window(start,end,1)

    def test_endpoint_tampering_and_guard_races_refused(self):
        valid,_ = make(1)
        for mutation in ('hash','clock','nan','pid','quota','members','owner','reset','authority','raw'):
            value = copy.deepcopy(valid)
            if mutation == 'hash': value['cpu']['usage_usec'] = 0
            if mutation == 'clock': value['after'] = value['before']-1
            if mutation == 'nan': value['before'] = float('nan')
            if mutation == 'pid': value['guard_after']['owner']['process_start_id'] = 'reused'
            if mutation == 'quota': value['guard_after']['ancestry'][0]['cpu_max'] = '50000 100000'
            if mutation == 'members': value['guard_after']['actors'] *= 2
            if mutation == 'owner': value['guard_after']['owner']['pid'] = True
            if mutation == 'reset': value['guard_after']['cpu']['usage_usec'] = 1
            if mutation == 'authority': value['native_origin_binding_verified'] = True
            if mutation == 'raw': value['raw_ascii'] = 'usage_usec 2'
            if mutation != 'hash': rehash(value)
            with self.subTest(mutation=mutation), self.assertRaises(ContractError): validate_endpoint(value)

    def test_raw_caps_missing_usage_malformed_and_read_failure(self):
        for raw in (b'',b'x'*(CAP+1),b'nr_periods 1',b'usage_usec 1\nusage_usec 2',b'usage_usec -1', 'usage_usec 1'):
            with self.subTest(raw=str(raw)[:30]), self.assertRaises((ContractError,ValueError)): make(1,raw=raw)
        with self.assertRaises(OSError):
            endpoint(lambda:(_ for _ in ()).throw(OSError('injected')),lambda:fixtures.sample(0,1),lambda:0)

    def test_native_fd_repeated_offset_zero_reads_and_scoped_close(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            reader = fixtures.ResourceTests().fixture(root)
            with self.assertRaises(ContractError): NativeCounterProbe(reader)
            with NativeCounterProbe(reader,execute=True) as probe:
                fd = probe.fd
                self.assertEqual(probe.sample()['cpu']['usage_usec'],100)
                (reader.group/'cpu.stat').write_text('usage_usec 200')
                self.assertEqual(probe.sample()['cpu']['usage_usec'],200)
            self.assertIsNone(probe.fd)
            probe.close()
            with self.assertRaises(OSError): os.fstat(fd)
            with self.assertRaises(ContractError): probe.sample()

    def test_native_leaf_replacement_or_unlinked_descriptor_refused(self):
        for mutation in ('replace','unlink','symlink'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                reader = fixtures.ResourceTests().fixture(root)
                with NativeCounterProbe(reader,execute=True) as probe:
                    leaf = reader.group/'cpu.stat'
                    leaf.rename(root/'retained-counter')
                    if mutation == 'replace': leaf.write_text('usage_usec 100')
                    if mutation == 'symlink': leaf.symlink_to(root/'retained-counter')
                    with self.assertRaises((ContractError,OSError)): probe.sample()

    def test_guard_failure_preserved_without_read_or_retry(self):
        read = unittest.mock.Mock(return_value=b'usage_usec 1')
        with self.assertRaisesRegex(OSError,'guard failure'):
            endpoint(read,lambda:(_ for _ in ()).throw(OSError('guard failure')),lambda:1)
        read.assert_not_called()

    def test_post_guard_failure_never_publishes_a_success(self):
        calls = []
        def guard():
            calls.append('guard')
            if len(calls) == 3: raise OSError('post guard disappeared')
            return fixtures.sample(1,1)
        def read():
            calls.append('read')
            return b'usage_usec 1'
        with self.assertRaisesRegex(OSError,'post guard disappeared'):
            endpoint(read,guard,lambda:1)
        self.assertEqual(calls,['guard','read','guard'])

    def test_native_controller_change_across_counter_read_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            reader = fixtures.ResourceTests().fixture(root)
            original = os.pread
            with NativeCounterProbe(reader,execute=True) as probe:
                def change(fd,size,offset):
                    raw = original(fd,size,offset)
                    (reader.group/'cpu.max').write_text('50000 100000')
                    return raw
                with patch('infra.stream.recorder_counter_prototype.os.pread',side_effect=change):
                    with self.assertRaisesRegex(ContractError,'controller state changed'): probe.sample()

    def test_regular_counter_leaf_required_without_fifo_block(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            reader = fixtures.ResourceTests().fixture(root)
            leaf = reader.group/'cpu.stat'
            leaf.unlink()
            os.mkfifo(leaf)
            with self.assertRaises(ContractError): NativeCounterProbe(reader,execute=True)


if __name__ == '__main__':
    unittest.main()
