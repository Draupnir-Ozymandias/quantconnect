"""Pure post-hoc timing description; no clock, sleep, execution or repair."""
from copy import deepcopy

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.recorder_counter_prototype import finite, validate_endpoint
from infra.stream.recorder_counter_schedule import POLICY


def describe(schedule):
    """Describe hash-checked v1 evidence, not native origin or acceptance."""
    verify_artifact_hash(schedule, 'schedule_sha256', 'counter schedule')
    if (schedule['schema_version'] != 'qcrl.recorder_counter_schedule_prototype.v1'
            or schedule['policy'] != POLICY
            or schedule['acceptance_demonstrated'] is not False
            or schedule['orders_authorized'] is not False):
        raise ContractError('unsupported diagnostic schedule/policy/authority')
    boundary = finite(schedule['boundary'])
    finite(schedule['began'])
    finite(schedule['ready_at'])
    source_rows = schedule['rows']
    if not isinstance(source_rows, list) or len(source_rows) != 2:
        raise ContractError('exactly two fixed endpoint rows required')
    rows = []
    targets = (boundary-POLICY['pre_boundary_lead_seconds'], boundary+60)
    for source, role, target in zip(source_rows, ('before', 'after'), targets):
        if (source['role'] != role or source['target'] != target
                or type(source['attempted']) is not bool
                or source['status'] not in ('observed', 'unknown')):
            raise ContractError('invalid fixed schedule row')
        wake = source['wake']
        if wake is not None:
            finite(wake)
        value = source['endpoint']
        row = dict(role=role, status=source['status'], error=source['error'],
                   attempted=source['attempted'], target=target,
                   wake_lateness_ms=None if wake is None else (wake-target)*1000,
                   deadline_excess_ms=None if wake is None else
                   max(0, wake-target-POLICY['wake_lateness_max_seconds'])*1000,
                   wake_to_guard_begin_ms=None, pre_read_guard_ms=None,
                   counter_read_ms=None, post_read_guard_ms=None,
                   total_guard_envelope_ms=None, boundary_margin_ms=None)
        if value is not None:
            validate_endpoint(value)
            if not source['attempted'] or wake is None or value['total_begin'] < wake:
                raise ContractError('endpoint not bound to attempted wake')
            row.update(wake_to_guard_begin_ms=(value['total_begin']-wake)*1000,
                       pre_read_guard_ms=(value['before']-value['total_begin'])*1000,
                       counter_read_ms=(value['after']-value['before'])*1000,
                       post_read_guard_ms=(value['total_end']-value['after'])*1000,
                       total_guard_envelope_ms=(value['total_end']-value['total_begin'])*1000,
                       boundary_margin_ms=(boundary-value['after'] if role == 'before'
                                           else value['before']-(boundary+60))*1000)
        elif source['status'] == 'observed':
            raise ContractError('observed endpoint missing')
        rows.append(row)
    result = dict(schema_version='qcrl.recorder_counter_timing_diagnostic.v1',
                  source_schedule_sha256=schedule['schedule_sha256'],
                  policy=deepcopy(POLICY), rows=rows,
                  source_enclosure_verified=schedule['enclosure_verified'],
                  wake_cause='unidentified', sleep_overshoot_measured=False,
                  native_origin_verified=False, acceptance_demonstrated=False,
                  orders_authorized=False)
    result['diagnostic_sha256'] = payload_hash(result)
    return result
