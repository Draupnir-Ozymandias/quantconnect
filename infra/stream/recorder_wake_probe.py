"""Bounded clock-only prototype with injected I/O; no launcher or deployment."""
from copy import deepcopy

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_counter_prototype import finite

PLAN = dict(schema_version='qcrl.recorder_wake_plan.v1',
            interval_seconds=[.05, .1, .5, 1, 5, 60], cycles=2,
            baseline_pairs=16, wake_lateness_reference_seconds=.05,
            attempts_per_target=1, catch_up_authorized=False,
            resource_changes_authorized=False, orders_authorized=False)


def collect(*, clock, pause, execute=False):
    if execute is not True:
        raise ContractError('explicit finite clock probe required')
    baseline = []
    last = finite(clock())
    for _ in range(PLAN['baseline_pairs']):
        before, after = finite(clock()), finite(clock())
        if not last <= before <= after:
            raise ContractError('baseline clock regressed')
        baseline.append(dict(before=before, after=after))
        last = after
    epoch = finite(clock())
    if epoch < last:
        raise ContractError('epoch clock regressed')
    elapsed, rows, stopped = 0, [], False
    last = epoch
    for cycle in range(PLAN['cycles']):
        for interval in PLAN['interval_seconds']:
            elapsed += interval
            target = epoch+elapsed
            row = dict(cycle=cycle, interval_seconds=interval, target=target,
                       pre_request=None, requested_seconds=None, returned=None,
                       attempted=False, status='unknown', error=None,
                       wake_lateness_seconds=None, return_minus_request_seconds=None,
                       observed_request_excess_seconds=None)
            rows.append(row)
            if stopped:
                row['error'] = 'prior_clock_or_sleep_fault'
                continue
            try:
                before = finite(clock())
                row['pre_request'] = before
                if before < last:
                    raise ContractError('request clock regressed')
                last = before
                if before >= target:
                    row['error'] = 'target_already_missed_no_catch_up'
                    continue
                requested = target-before
                row['requested_seconds'] = requested
                row['attempted'] = True
                pause(requested)
                returned = finite(clock())
                row['returned'] = returned
                if returned < before:
                    raise ContractError('return clock regressed')
                last = returned
                row.update(wake_lateness_seconds=returned-target,
                           return_minus_request_seconds=returned-before,
                           observed_request_excess_seconds=returned-before-requested)
                if returned < target:
                    row['error'] = 'early_return_no_retry'
                else:
                    row['status'] = 'observed'
            except Exception as exc:
                row['error'] = type(exc).__name__+':'+str(exc)[:160]
                stopped = True
    result = dict(schema_version='qcrl.recorder_wake_probe.v1',
                  plan=deepcopy(PLAN), plan_sha256=payload_hash(PLAN),
                  epoch=epoch, baseline=baseline, rows=rows,
                  native_origin_verified=False, acceptance_demonstrated=False,
                  kernel_sleep_overshoot_isolated=False, orders_authorized=False)
    result['probe_sha256'] = payload_hash(result)
    return result
