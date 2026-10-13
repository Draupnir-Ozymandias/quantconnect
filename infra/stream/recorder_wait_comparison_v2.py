"""Prospective runtime-retry disclosure and injected finite collection only."""
from copy import deepcopy

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_wait_comparison as original
from infra.stream.recorder_absolute_wait import NS, MAX_WAIT_NS, timestamp

PREDECESSOR_HASH = 'a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee'
PLAN = deepcopy(original.PLAN)
PLAN.update(
    schema_version='qcrl.wait_comparison_plan.v2',
    experiment_id='absolute-select-finite-v2',
    predecessor_plan_sha256=PREDECESSOR_HASH,
    attempts_per_target=1,
    attempt_boundary='one_application_wait_call_not_one_kernel_syscall',
    application_retries=0,
    select_runtime_retry_policy='recomputed_timeout_after_signal_unless_handler_raises',
    select_internal_retry_count=None,
    absolute_runtime_retry_policy='returned_eintr_retained_no_resubmission',
    interrupt_handling='exposed_exception_or_errno_unknown_no_application_retry_stop',
    max_summary_bytes=262144,
)


def declaration():
    result = deepcopy(PLAN)
    result['plan_sha256'] = payload_hash(result)
    return result


def error_text(exc):
    return (type(exc).__name__+':'+str(exc))[:PLAN['max_error_characters']]


class SelectWait:
    """One injected Python select call; runtime internal retry count is unknown."""
    def __init__(self, *, clock_ns, select_call):
        self.clock_ns, self.select_call = clock_ns, select_call
        self.last = None

    def wait(self, target_ns, *, execute=False):
        if execute is not True:
            raise ContractError('explicit injected select wait required')
        timestamp(target_ns)
        before = timestamp(self.clock_ns())
        row = dict(schema_version='qcrl.select_wait.v2', target_ns=target_ns,
                   before_ns=before, after_ns=None,
                   requested_remaining_ns=target_ns-before,
                   requested_seconds_ratio=None, conversion_error_ns_ratio=None,
                   attempted=False, return_code=None, lateness_ns=None,
                   status='unknown', error=None, retries=0,
                   internal_retry_count=None,
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
            remaining = target_ns-before
            seconds = remaining/NS
            numerator, denominator = seconds.as_integer_ratio()
            row['requested_seconds_ratio'] = [numerator, denominator]
            row['conversion_error_ns_ratio'] = [numerator*NS-remaining*denominator, denominator]
            row['attempted'] = True
            try:
                returned = self.select_call([], [], [], seconds)
                if type(returned) is not tuple or len(returned) != 3 or any(
                        type(part) is not list or part for part in returned):
                    raise ContractError('empty select result triple required')
                row['return_code'] = 0
            except Exception as exc:
                row['error'] = error_text(exc)
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
                row['error'] = row['error'] or error_text(exc)
        self.last = max(before, self.last or 0)
        row['wait_sha256'] = payload_hash(row)
        return row


def _receipt(run_index):
    if type(run_index) is not int or run_index not in (0, 1):
        raise ContractError('declared run index required')
    return dict(schema_version='qcrl.wait_comparison_run.v2', run_index=run_index,
                plan_sha256=payload_hash(PLAN), epoch_ns=None, baseline=[], rows=[],
                fatal_error=None, cancelled=False, native_origin_verified=False,
                acceptance_demonstrated=False, orders_authorized=False)


def _seal(result):
    result['run_sha256'] = payload_hash(result)
    return result


def cancelled_run(run_index):
    result = _receipt(run_index)
    result.update(cancelled=True, fatal_error='prior_run_fatal_cancelled')
    return _seal(result)


def collect_run(*, run_index, clock_ns, select_wait, absolute_wait, execute=False):
    """Injected dependencies only; faults retain a finite partial receipt."""
    if execute is not True:
        raise ContractError('explicit injected finite collection required')
    result = _receipt(run_index)
    last = None
    try:
        for _ in range(PLAN['baseline_pairs_per_run']):
            before, after = timestamp(clock_ns()), timestamp(clock_ns())
            if (last is not None and before < last) or after < before:
                raise ContractError('baseline clock regressed')
            result['baseline'].append(dict(before_ns=before, after_ns=after))
            last = after
        epoch = timestamp(clock_ns())
        if epoch < last:
            raise ContractError('epoch clock regressed')
        scheduled = original.targets(epoch, run_index)
        result['epoch_ns'] = epoch
        last = epoch
    except Exception as exc:
        result['fatal_error'] = error_text(exc)
        return _seal(result)
    for ordinal, target in enumerate(scheduled):
        row = dict(target, ordinal=ordinal, checkpoint_ns=None, observation=None, error=None)
        result['rows'].append(row)
        if result['fatal_error'] is not None:
            row['error'] = 'prior_wait_fault_no_attempt'
            continue
        try:
            checkpoint = timestamp(clock_ns())
            row['checkpoint_ns'] = checkpoint
            if checkpoint < last:
                raise ContractError('comparison clock regressed before attempt')
            last = checkpoint
            adapter = select_wait if target['arm'] == 'select' else absolute_wait
            observed = adapter.wait(target['target_ns'], execute=True)
            row['observation'] = observed
            before = timestamp(observed['before_ns'])
            if before < last:
                raise ContractError('comparison clock regressed across arms')
            last = before
            if observed['after_ns'] is not None:
                after = timestamp(observed['after_ns'])
                if after >= before:
                    last = after
            if observed['error'] is not None and observed['error'] != 'target_already_missed_no_catch_up':
                result['fatal_error'] = observed['error']
        except Exception as exc:
            row['error'] = error_text(exc)
            result['fatal_error'] = row['error']
    return _seal(result)


def collect_pair(*, run_factory, publish, execute=False):
    """Inject collection/publication; publication failure prevents the next run.

    The factory supplies fresh clock/adapters per run. Validation precedes each
    publication, and run one is cancelled rather than measured after fatal run zero.
    No filesystem path, real clock or native callable is supplied by this module.
    """
    if execute is not True:
        raise ContractError('explicit injected pair collection required')
    from infra.stream.recorder_wait_comparison_audit import validate_run
    runs = []
    for index in (0, 1):
        if index == 1 and runs[0]['fatal_error'] is not None:
            result = cancelled_run(index)
        else:
            dependencies = run_factory(index)
            result = collect_run(run_index=index, execute=True, **dependencies)
        validate_run(result)
        publish(index, deepcopy(result))
        runs.append(result)
    return runs
