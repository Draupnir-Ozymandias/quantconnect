"""Absolute waiting in the isolated recorder observer; no launch or receive edits."""
import time

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream.recorder_absolute_wait import native, target_nanoseconds, timestamp, NS
from infra.stream.recorder_absolute_budget import PLAN, declaration, validate
from infra.stream import recorder_application_worker as worker


def error(exc):
    return (type(exc).__name__+':'+str(exc))[:160]


def observe_absolute(reader, epoch, stop, *, execute=False, wait=None, clock_ns=None,
                     capacity=184):
    if execute is not True or type(capacity) is not int or not 1 <= capacity <= PLAN['max_slots']:
        raise ContractError('explicit bounded absolute recorder observer required')
    epoch_ns = target_nanoseconds(epoch)
    if epoch_ns < PLAN['cpu_lead_ns']:
        raise ContractError('epoch must admit original pre-boundary target')
    timestamp(epoch_ns+(capacity-1)*NS)
    clock_ns = time.monotonic_ns if clock_ns is None else clock_ns
    result = dict(schema_version='qcrl.recorder_absolute_resources.v1',
                  plan_sha256=payload_hash(PLAN), epoch_ns=epoch_ns, capacity=capacity, rows=[],
                  overflow=False, error=None, native_origin_verified=False,
                  acceptance_demonstrated=False, orders_authorized=False)
    try:
        wait = native(execute=True) if wait is None else wait
    except (Exception, KeyboardInterrupt) as exc:
        result['error'] = error(exc)
        return result
    fatal = None
    last_clock = None
    last_read_after = None

    def sample(target, row, key, boundary=None):
        nonlocal fatal, last_clock, last_read_after
        try:
            observation = wait.wait(target, execute=True)
            validate_wait(observation, target)
            row['waits'][key] = observation
            if ((last_clock is not None and observation['before_ns'] < last_clock)
                    or (last_read_after is not None and observation['before_ns']/NS < last_read_after)):
                fatal = 'observer_clock_regressed'
                return None, fatal
            if observation['status'] != 'observed':
                reason = observation['error']
                if reason != 'target_already_missed_no_catch_up':
                    fatal = reason
                return None, reason
            if observation['after_ns']-target > PLAN['wake_lateness_max_ns']:
                return None, 'late_wake_no_read_no_catch_up'
            now = timestamp(clock_ns())
            if now < observation['after_ns'] or (last_clock is not None and now < last_clock):
                fatal = 'observer_clock_regressed'
                return None, fatal
            last_clock = now
            if now-target > PLAN['wake_lateness_max_ns']:
                return None, 'read_deadline_missed_no_catch_up'
            if boundary is not None and now >= boundary:
                return None, 'pre_read_boundary_missed'
            try:
                value = reader.read(rss=(key == 'rss'))
            except Exception as exc:
                return None, error(exc)
            # Reader brackets are represented seconds, not exact integer timestamps.
            last_read_after = value['after']
            return value, None
        except (Exception, KeyboardInterrupt) as exc:
            # A wait/clock fault must stop; a reader fault retains its slot only.
            fatal = error(exc)
            return None, fatal

    for slot in range(capacity):
        target = epoch_ns+slot*NS
        row = dict(slot=slot, target=epoch+slot, target_ns=target, waits={},
                   cpu_before=None, cpu_before_error=None, sample=None, error=None)
        result['rows'].append(row)
        if slot % PLAN['cpu_period_slots'] == 0:
            row['cpu_before'], row['cpu_before_error'] = sample(
                target-PLAN['cpu_lead_ns'], row, 'cpu_before', boundary=target)
        if fatal is None:
            row['sample'], row['error'] = sample(target, row, 'rss')
        else:
            row['error'] = fatal
        if fatal is not None:
            result['error'] = fatal
            return result
        if stop.is_set():
            return result
    result['overflow'] = True
    return result


def validate_wait(value, target):
    verify_artifact_hash(value, 'wait_sha256', 'recorder absolute wait')
    if (value.get('schema_version') != 'qcrl.absolute_monotonic_wait.v1'
            or type(value.get('target_ns')) is not int or value['target_ns'] != target
            or type(value.get('retries')) is not int or value['retries'] != 0
            or any(value.get(k) is not False for k in
                   ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'))):
        raise ContractError('absolute observer wait binding differs')
    before = timestamp(value['before_ns'])
    if type(value['requested_remaining_ns']) is not int or value['requested_remaining_ns'] != target-before:
        raise ContractError('absolute observer remaining duration differs')
    if value['error'] is not None and (type(value['error']) is not str or not 1 <= len(value['error']) <= 160):
        raise ContractError('bounded observer error required')
    if value['attempted'] is True:
        if not 0 < target-before <= PLAN['max_wait_ns']:
            raise ContractError('invalid attempted absolute observer duration')
    elif value['attempted'] is not False or value['after_ns'] is not None or value['return_code'] is not None:
        raise ContractError('unattempted observer wait has a return')
    if value['status'] == 'observed':
        after = timestamp(value['after_ns'])
        if (value['attempted'] is not True or value['error'] is not None
                or type(value['return_code']) is not int or value['return_code'] != 0 or after < target
                or value['lateness_ns'] != after-target):
            raise ContractError('invalid observed absolute observer wait')
    elif value['status'] != 'unknown' or value['error'] is None:
        raise ContractError('unknown observer wait requires its error')
    if value['error'] == 'target_already_missed_no_catch_up' and (target > before or value['attempted']):
        raise ContractError('missed observer target was attempted')
    return value


def audit_resources(resources, epoch, duration, closed, budgets, owner):
    """Validate integration binding before applying unchanged resource gates."""
    from infra.stream.recorder_application_evaluator import resource_gate
    if (resources.get('schema_version') != 'qcrl.recorder_absolute_resources.v1'
            or resources.get('plan_sha256') != payload_hash(PLAN)
            or resources.get('epoch_ns') != target_nanoseconds(epoch)
            or type(resources.get('capacity')) is not int
            or not 1 <= resources['capacity'] <= PLAN['max_slots']
            or any(resources.get(k) is not False for k in
                   ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'))):
        raise ContractError('absolute observer resources binding differs')
    if not isinstance(resources.get('rows'), list) or len(resources['rows']) > resources['capacity']:
        raise ContractError('bounded absolute observer rows required')
    if type(resources.get('overflow')) is not bool or (
            resources.get('error') is not None and
            (type(resources['error']) is not str or not 1 <= len(resources['error']) <= 160)):
        raise ContractError('bounded absolute observer outcome required')
    for slot, row in enumerate(resources['rows']):
        target = resources['epoch_ns']+slot*NS
        if type(row['slot']) is not int or row['slot'] != slot or row['target'] != epoch+slot or row['target_ns'] != target:
            raise ContractError('absolute observer original grid changed')
        expected = {'rss', 'cpu_before'} if slot % PLAN['cpu_period_slots'] == 0 else {'rss'}
        if not set(row['waits']) <= expected or ('rss' not in row['waits'] and not resources['error']):
            raise ContractError('absolute observer endpoint population differs')
        for key, value in row['waits'].items():
            deadline = target-PLAN['cpu_lead_ns'] if key == 'cpu_before' else target
            validate_wait(value, deadline)
            sample = row['cpu_before'] if key == 'cpu_before' else row['sample']
            reason = row['cpu_before_error'] if key == 'cpu_before' else row['error']
            if sample is not None:
                if (reason is not None or value['status'] != 'observed'
                        or value['after_ns']-deadline > PLAN['wake_lateness_max_ns']
                        or target_nanoseconds(sample['before']) < value['after_ns']
                        or target_nanoseconds(sample['before'])-deadline > PLAN['wake_lateness_max_ns']):
                    raise ContractError('resource read without qualified absolute wait')
            elif reason is None:
                raise ContractError('unavailable absolute resource read needs a reason')
        if slot % PLAN['cpu_period_slots'] == 0 and 'cpu_before' not in row['waits'] and not resources['error']:
            raise ContractError('missing pre-boundary absolute endpoint')
        if slot % PLAN['cpu_period_slots'] and (row['cpu_before'] is not None or row['cpu_before_error'] is not None):
            raise ContractError('extra pre-boundary read')
    return resource_gate(resources, epoch, duration, closed, budgets, owner)


def prepare_absolute(path, case, *, execute=False):
    if execute is not True:
        raise ContractError('explicit isolated absolute case preparation required')
    plan = declaration()
    root = worker.prepare(path, worker_parent(), case, execute=True)
    current = worker.control(root/'case.json')
    worker.publish(root/'absolute-wait-plan.json', dict(case_sha256=current['artifact_sha256'],
                   declaration=plan))
    return root


def worker_parent():
    from infra.stream.recorder_application_budget import declare
    return declare()


def consume_absolute(root, *, execute=False, wait=None, clock_ns=None):
    if execute is not True:
        raise ContractError('explicit isolated absolute consume required')
    from pathlib import Path
    root = Path(root)
    binding = worker.control(root/'absolute-wait-plan.json')
    validate(binding['declaration'])
    case = worker.control(root/'case.json')
    if binding['case_sha256'] != case['artifact_sha256']:
        raise ContractError('absolute observer case binding differs')
    return worker.consume(root, worker_parent(), execute=True,
        resource_observer=lambda reader, epoch, stop: observe_absolute(
            reader, epoch, stop, execute=True, wait=wait, clock_ns=clock_ns))
