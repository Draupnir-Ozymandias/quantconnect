"""Offline declaration and integer target expansion; no native execution API."""
from copy import deepcopy

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_absolute_wait import MAX_NS, timestamp

PLAN = dict(
    schema_version='qcrl.wait_comparison_plan.v1',
    experiment_id='absolute-select-finite-v1',
    interval_ns=[50_000_000, 100_000_000, 500_000_000,
                 1_000_000_000, 5_000_000_000, 60_000_000_000],
    run_blocks=[['select', 'absolute'], ['absolute', 'select']],
    baseline_pairs_per_run=16, attempts_per_target=1,
    max_rows_per_run=12, max_result_bytes_per_run=262144,
    max_error_characters=160,
    unit_limits=dict(cpu_percent=75, memory_bytes=536870912,
                     tasks=32, runtime_seconds=240),
    unknown_handling='retain_all_rows_no_imputation',
    fault_handling='stop_remaining_attempts_in_run_and_cancel_second_run',
    missed_handling='unknown_no_wait_no_catch_up',
    interrupt_handling='unknown_no_retry_stop',
    early_return_handling='unknown_no_retry_stop',
    stopping_rule='two_declared_runs_once_no_replay',
    reference='explicit_select_timeout_not_time_sleep',
    native_execution_authorized=False, resource_changes_authorized=False,
    acceptance_demonstrated=False, orders_authorized=False,
)


def declaration():
    result = deepcopy(PLAN)
    result['plan_sha256'] = payload_hash(result)
    return result


def targets(epoch_ns, run_index):
    """Expand the locked cumulative grid without clock reads or waits."""
    timestamp(epoch_ns)
    if type(run_index) is not int or run_index not in (0, 1):
        raise ContractError('declared run index required')
    duration = 2 * sum(PLAN['interval_ns'])
    if epoch_ns > MAX_NS-duration:
        raise ContractError('target grid exceeds bounded monotonic range')
    elapsed, rows = 0, []
    for block, arm in enumerate(PLAN['run_blocks'][run_index]):
        for interval in PLAN['interval_ns']:
            elapsed += interval
            rows.append(dict(run_index=run_index, block=block, arm=arm,
                             interval_ns=interval, target_ns=epoch_ns+elapsed))
    return rows
