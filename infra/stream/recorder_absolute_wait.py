"""Isolated absolute-monotonic wait prototype; never used by current launchers."""
import ctypes
import math
import platform
import time

from execution_truth.contracts import ContractError, payload_hash

NS = 1_000_000_000
MAX_NS = (1 << 63)-1
MAX_WAIT_NS = 60*NS
CLOCK_MONOTONIC = 1
TIMER_ABSTIME = 1


def timestamp(value):
    if type(value) is not int or not 0 <= value <= MAX_NS:
        raise ContractError('bounded integer monotonic nanoseconds required')
    return value


def target_nanoseconds(seconds):
    """Ceil the exact represented float, never an intermediate rounded product."""
    if (type(seconds) not in (int, float) or seconds < 0
            or (type(seconds) is float and not math.isfinite(seconds))):
        raise ContractError('finite nonnegative target seconds required')
    numerator, denominator = seconds.as_integer_ratio() if type(seconds) is float else (seconds, 1)
    return timestamp((numerator*NS+denominator-1)//denominator)


def timespec_parts(target_ns):
    return divmod(timestamp(target_ns), NS)


class Timespec(ctypes.Structure):
    _fields_ = [('tv_sec', ctypes.c_long), ('tv_nsec', ctypes.c_long)]


class AbsoluteWait:
    def __init__(self, *, clock_ns, syscall):
        self.clock_ns, self.syscall = clock_ns, syscall
        self.last = None

    def wait(self, target_ns, *, execute=False):
        if execute is not True:
            raise ContractError('explicit single absolute wait required')
        timestamp(target_ns)
        before = timestamp(self.clock_ns())
        row = dict(schema_version='qcrl.absolute_monotonic_wait.v1',
                   target_ns=target_ns, before_ns=before, after_ns=None,
                   requested_remaining_ns=target_ns-before,
                   attempted=False, return_code=None, lateness_ns=None,
                   status='unknown', error=None, retries=0,
                   native_origin_verified=False, acceptance_demonstrated=False,
                   orders_authorized=False)
        if self.last is not None and before < self.last:
            row['error'] = 'clock_regressed_between_waits'
        elif target_ns <= before:
            row['error'] = 'target_already_missed_no_catch_up'
        elif target_ns-before > MAX_WAIT_NS:
            row['error'] = 'remaining_wait_exceeds_fixed_cap'
        else:
            self.last = before
            sec, nsec = timespec_parts(target_ns)
            row['attempted'] = True
            try:
                code = self.syscall(CLOCK_MONOTONIC, TIMER_ABSTIME, sec, nsec)
                if type(code) is not int or not 0 <= code <= 4095:
                    raise ContractError('invalid clock_nanosleep return code')
                row['return_code'] = code
                if code:
                    row['error'] = 'clock_nanosleep_error_'+str(code)+'_no_retry'
            except Exception as exc:
                row['error'] = type(exc).__name__+':'+str(exc)[:160]
            try:
                after = timestamp(self.clock_ns())
                row['after_ns'] = after
                if after < before:
                    raise ContractError('clock regressed across wait')
                self.last = after
                row['lateness_ns'] = after-target_ns
                if row['error'] is None:
                    if after < target_ns:
                        row['error'] = 'early_return_no_retry'
                    else:
                        row['status'] = 'observed'
            except Exception as exc:
                row['error'] = row['error'] or type(exc).__name__+':'+str(exc)[:160]
        self.last = max(before, self.last or 0)
        row['wait_sha256'] = payload_hash(row)
        return row


def native(*, execute=False):
    """Bind glibc only on the declared Linux LP64 ABI; no sleep until wait()."""
    if execute is not True:
        raise ContractError('explicit native binding required')
    if (platform.system() != 'Linux' or platform.machine() not in ('aarch64', 'x86_64')
            or platform.libc_ver()[0] != 'glibc' or ctypes.sizeof(ctypes.c_long) != 8
            or ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(Timespec) != 16
            or getattr(time, 'CLOCK_MONOTONIC', None) != CLOCK_MONOTONIC
            or time.get_clock_info('monotonic').implementation != 'clock_gettime(CLOCK_MONOTONIC)'):
        raise ContractError('verified Linux glibc LP64 monotonic ABI required')
    library = ctypes.CDLL(None)
    function = library.clock_nanosleep
    function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(Timespec), ctypes.c_void_p]
    function.restype = ctypes.c_int
    def syscall(clock_id, flags, sec, nsec):
        value = Timespec(sec, nsec)
        return function(clock_id, flags, ctypes.byref(value), None)
    return AbsoluteWait(clock_ns=time.monotonic_ns, syscall=syscall)
