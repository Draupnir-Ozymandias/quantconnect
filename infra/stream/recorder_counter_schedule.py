"""Finite prototype schedule; one attempt per endpoint, no cohort integration."""
from copy import deepcopy
import time

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_counter_prototype import finite, validate_endpoint, window

POLICY = dict(schema_version='qcrl.recorder_counter_schedule_policy.v1',
              duration_seconds=60, pre_boundary_lead_seconds=.050,
              wake_lateness_max_seconds=.050, counter_bracket_max_seconds=.005,
              attempts_per_endpoint=1, catch_up_authorized=False,
              endpoint_order=['before', 'after'])


def scheduled_window(probe, boundary, ready_at, *, execute=False,
                     clock=time.monotonic, pause=time.sleep):
    if execute is not True:
        raise ContractError('explicit finite counter schedule required')
    finite(boundary)
    finite(ready_at)
    began = finite(clock())
    first = boundary - POLICY['pre_boundary_lead_seconds']
    if first < 0 or ready_at > began:
        raise ContractError('invalid counter readiness/epoch')
    rows, last = [], began
    for role, target in [('before', first), ('after', boundary+60)]:
        row = dict(role=role, target=target, wake=None, attempted=False,
                   endpoint=None, error=None, status='unknown')
        rows.append(row)
        if ready_at > first:
            row['error'] = 'readiness_deadline_missed'
            continue
        now = finite(clock())
        if now < last:
            row['error'] = 'schedule_clock_regressed'
            continue
        # Already missed slots are not caught up or shifted to a new epoch.
        if now-target > POLICY['wake_lateness_max_seconds']:
            row['wake'] = now
            row['error'] = 'endpoint_deadline_missed'
            continue
        try:
            if now < target:
                pause(target-now)
            row['wake'] = finite(clock())
            if row['wake'] < target:
                row['error'] = 'early_wake_no_read'
                continue
            if row['wake']-target > POLICY['wake_lateness_max_seconds']:
                row['error'] = 'late_wake_no_catch_up'
                continue
            row['attempted'] = True
            row['endpoint'] = probe.sample()
            validate_endpoint(row['endpoint'])
            value = row['endpoint']
            if value['total_begin'] < row['wake']:
                raise ContractError('endpoint predates scheduled attempt')
            if value['after']-value['before'] > POLICY['counter_bracket_max_seconds']:
                row['error'] = 'counter_bracket_too_wide'
            elif role == 'before' and value['after'] > boundary:
                row['error'] = 'pre_counter_did_not_finish_before_boundary'
            elif role == 'after' and value['before'] < boundary+60:
                row['error'] = 'post_counter_started_before_boundary'
            else:
                row['status'] = 'observed'
        except Exception as exc:
            row['error'] = type(exc).__name__+':'+str(exc)[:160]
        last = max(last, now, row['wake'] or 0,
                   row['endpoint']['total_end'] if row['endpoint'] is not None else 0)
    diagnostic, error = None, None
    if all(row['status'] == 'observed' for row in rows):
        try:
            diagnostic = window(rows[0]['endpoint'],rows[1]['endpoint'],boundary)
        except Exception as exc:
            error = type(exc).__name__+':'+str(exc)[:160]
    else:
        error = 'required_endpoint_unknown'
    result = dict(schema_version='qcrl.recorder_counter_schedule_prototype.v1',
                  policy=deepcopy(POLICY), boundary=boundary, ready_at=ready_at, began=began,
                  rows=rows, diagnostic=diagnostic, error=error,
                  enclosure_verified=diagnostic is not None,
                  acceptance_demonstrated=False, orders_authorized=False)
    result['schedule_sha256'] = payload_hash(result)
    return result
