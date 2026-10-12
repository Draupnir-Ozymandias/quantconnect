import errno
from fractions import Fraction
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, verify_artifact_hash
from infra.stream import recorder_absolute_wait as wait


class AbsoluteWaitTests(unittest.TestCase):
    def fixture(self, *, code=0, offset=0, at=100, target=200):
        clock = SimpleNamespace(value=at)
        calls = []
        def syscall(clock_id, flags, sec, nsec):
            calls.append((clock_id, flags, sec, nsec))
            clock.value = sec*wait.NS+nsec+offset
            return code
        adapter = wait.AbsoluteWait(clock_ns=lambda: clock.value, syscall=syscall)
        row = adapter.wait(target, execute=True)
        return row, calls, adapter, clock

    def test_exact_absolute_request_and_hash_no_authority(self):
        row, calls, _, _ = self.fixture(target=2*wait.NS+7)
        self.assertEqual(calls, [(1,1,2,7)])
        self.assertEqual(row['status'], 'observed')
        self.assertEqual(row['lateness_ns'], 0)
        self.assertEqual(row['retries'], 0)
        verify_artifact_hash(row, 'wait_sha256', 'wait')
        for key in ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'):
            self.assertFalse(row[key])

    def test_eintr_other_errno_no_retry_no_relative_fallback(self):
        for code in (errno.EINTR, errno.EINVAL, errno.ENOTSUP):
            row, calls, _, _ = self.fixture(code=code)
            self.assertEqual(len(calls), 1)
            self.assertEqual(row['return_code'], code)
            self.assertEqual(row['status'], 'unknown')
            self.assertIn('no_retry', row['error'])

    def test_early_late_and_regressing_returns(self):
        for offset in (-1, 60_000_000, -101):
            row, calls, _, _ = self.fixture(offset=offset)
            self.assertEqual(len(calls), 1)
            self.assertEqual(row['status'], 'observed' if offset > 0 else 'unknown')
            if offset > 0:
                self.assertEqual(row['lateness_ns'], offset)
                self.assertFalse(row['acceptance_demonstrated'])

    def test_missed_and_oversized_target_no_syscall(self):
        for target in (99,100,100+wait.MAX_WAIT_NS+1):
            row, calls, _, _ = self.fixture(target=target)
            self.assertEqual(calls, [])
            self.assertFalse(row['attempted'])
            self.assertEqual(row['status'], 'unknown')

    def test_conversion_ceil_exact_binary_float_no_early_rounding(self):
        for value in (0, .1, 1, math.nextafter(1, math.inf), 764206.3418670511):
            ns = wait.target_nanoseconds(value)
            exact = Fraction(value)*wait.NS
            self.assertGreaterEqual(ns, exact)
            self.assertLess(ns-exact, 1)
            sec,nsec = wait.timespec_parts(ns)
            self.assertEqual(sec*wait.NS+nsec, ns)
            self.assertTrue(0 <= nsec < wait.NS)
        for value in (True, -1, float('nan'), float('inf'), '1', 10**30, 10**1000):
            with self.assertRaises(ContractError): wait.target_nanoseconds(value)
        for value in (True, -1, 1.0, wait.MAX_NS+1):
            with self.assertRaises(ContractError): wait.timespec_parts(value)

    def test_execution_guards_before_clock_or_library_loading(self):
        calls = []
        adapter = wait.AbsoluteWait(clock_ns=lambda: calls.append('clock'), syscall=lambda *a: calls.append('syscall'))
        with self.assertRaises(ContractError): adapter.wait(200)
        with patch.object(wait.ctypes, 'CDLL') as library:
            with self.assertRaises(ContractError): wait.native()
            library.assert_not_called()
        self.assertEqual(calls, [])

    def test_invalid_clock_return_code_and_syscall_exception_preserved(self):
        for code in (True, -1, 4096, '0'):
            row, calls, _, _ = self.fixture(code=code)
            self.assertEqual(len(calls), 1)
            self.assertEqual(row['status'], 'unknown')
            self.assertIsNone(row['return_code'])
        clock = SimpleNamespace(value=100)
        def fail(*args): raise OSError('injected')
        adapter = wait.AbsoluteWait(clock_ns=lambda: clock.value, syscall=fail)
        row = adapter.wait(200, execute=True)
        self.assertIn('OSError', row['error'])
        self.assertEqual(row['after_ns'], 100)
        for bad in (float('nan'), True, -1):
            adapter = wait.AbsoluteWait(clock_ns=lambda: bad, syscall=fail)
            with self.assertRaises(ContractError): adapter.wait(200, execute=True)

    def test_clock_regression_between_calls_refused(self):
        row,calls,adapter,clock = self.fixture()
        clock.value = 50
        second = adapter.wait(300, execute=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(second['error'], 'clock_regressed_between_waits')

    def test_native_abi_guard_and_injected_ffi_argument_layout(self):
        with patch.object(wait.platform, 'system', return_value='Darwin'), \
             patch.object(wait.ctypes, 'CDLL') as library:
            with self.assertRaises(ContractError): wait.native(execute=True)
            library.assert_not_called()
        calls = []
        class Function:
            def __call__(self, clock_id, flags, pointer, remain):
                calls.append((clock_id, flags, pointer._obj.tv_sec, pointer._obj.tv_nsec, remain))
                return 0
        function = Function()
        values = iter((1,wait.NS+7))
        with patch.object(wait.platform, 'system', return_value='Linux'), \
             patch.object(wait.platform, 'machine', return_value='aarch64'), \
             patch.object(wait.platform, 'libc_ver', return_value=('glibc','2.34')), \
             patch.object(wait.time, 'CLOCK_MONOTONIC', 1), \
             patch.object(wait.time, 'get_clock_info', return_value=SimpleNamespace(implementation='clock_gettime(CLOCK_MONOTONIC)')), \
             patch.object(wait.time, 'monotonic_ns', side_effect=lambda: next(values)), \
             patch.object(wait.ctypes, 'CDLL', return_value=SimpleNamespace(clock_nanosleep=function)):
            adapter = wait.native(execute=True)
            row = adapter.wait(wait.NS+7, execute=True)
        self.assertEqual(calls, [(1,1,1,7,None)])
        self.assertEqual(row['status'], 'observed')
        self.assertEqual(len(function.argtypes), 4)


if __name__ == '__main__': unittest.main()
