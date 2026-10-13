"""Injected offline rehearsal of a private finite compatibility launch lifecycle.

No systemd/subprocess/native implementation or worker entrypoint is supplied.
"""
from copy import deepcopy
import re

from execution_truth.contracts import ContractError, canonical_json, payload_hash, verify_artifact_hash
from infra.stream.recorder_absolute_wait import timestamp
from infra.stream.recorder_wait_execution import COMPATIBILITY, validate_freeze

STAGE = r'/var/lib/qcrl-stream/recorder-wait-[A-Za-z0-9]+'
BASE_PROPERTIES = dict(User='qcrl', Group='qcrl', CPUQuota='75%', MemoryMax='512M',
                       TasksMax='32', RuntimeMaxSec='240', RemainAfterExit='yes',
                       NoNewPrivileges='yes', PrivateTmp='yes', ProtectSystem='strict',
                       ProtectHome='yes', IPAddressDeny='any')


def require(condition, message):
    if not condition:
        raise ContractError(message)


def unit_spec(stage, role):
    require(type(stage) is str and re.fullmatch(STAGE, stage), 'fresh private wait stage required')
    require(role in ('tests', 'compatibility'), 'declared role required')
    suffix = stage.rsplit('recorder-wait-', 1)[1]
    properties = dict(BASE_PROPERTIES, ReadWritePaths=stage+'/evidence',
                      ReadOnlyPaths=stage+'/source',
                      InaccessiblePaths='-/etc/qcrl-stream.env -/etc/qcrl-collector.env',
                      RestrictAddressFamilies='AF_UNIX AF_INET' if role == 'tests' else 'AF_UNIX')
    if role == 'tests':
        properties['IPAddressAllow'] = '127.0.0.1/32'
    return dict(unit='qcrl-wait-'+suffix+'-'+role, role=role, properties=properties,
                interpreter='/opt/qcrl-stream/venv/bin/python',
                working_directory=stage+'/source', worker_entrypoint=None,
                native_execution_authorized=False)


def validate_compatibility(result, frozen, ready, release):
    validate_freeze(frozen)
    require(type(result) is dict and len(canonical_json(result).encode('utf-8')) <= COMPATIBILITY['max_result_bytes'], 'compatibility result exceeds cap')
    verify_artifact_hash(result, 'result_sha256', 'compatibility')
    require(result.get('schema_version') == 'qcrl.wait_compatibility_result.v1', 'compatibility schema differs')
    require(result.get('plan_sha256') == payload_hash(COMPATIBILITY), 'compatibility plan differs')
    require(result.get('freeze_sha256') == frozen['freeze_sha256'], 'compatibility freeze differs')
    require(result.get('ready_sha256') == ready['ready_sha256'] and result.get('release_sha256') == release['release_sha256'], 'readiness/release differs')
    require(result.get('identity') == ready['identity'], 'compatibility identity differs')
    for key in ('native_origin_verified', 'compatibility_verified', 'acceptance_demonstrated', 'orders_authorized'):
        require(result.get(key) is False, 'compatibility authority must remain false')
    rows = result.get('waits')
    require(type(rows) is list and len(rows) == 2, 'both declared compatibility waits required')
    epoch = timestamp(result.get('epoch_ns'))
    last = epoch
    for ordinal, (arm, row) in enumerate(zip(COMPATIBILITY['arm_order'], rows)):
        require(row.get('arm') == arm, 'compatibility order differs')
        observation = row['observation']
        verify_artifact_hash(observation, 'wait_sha256', 'compatibility wait')
        target = epoch+(ordinal+1)*COMPATIBILITY['interval_ns']
        require(type(observation.get('target_ns')) is int and observation['target_ns'] == target, 'compatibility target differs')
        before, after = timestamp(observation['before_ns']), timestamp(observation['after_ns'])
        require(last <= before < target <= after, 'compatibility clock bracket invalid')
        require(type(observation.get('requested_remaining_ns')) is int and observation['requested_remaining_ns'] == target-before, 'compatibility remaining mismatch')
        require(type(observation.get('lateness_ns')) is int and observation['lateness_ns'] == after-target, 'compatibility lateness mismatch')
        require(observation.get('status') == 'observed' and observation.get('error') is None
                and observation.get('attempted') is True and type(observation.get('return_code')) is int
                and observation['return_code'] == 0 and type(observation.get('retries')) is int
                and observation['retries'] == 0, 'compatibility wait unsuccessful')
        expected_schema = 'qcrl.select_wait.v2' if arm == 'select' else 'qcrl.absolute_monotonic_wait.v1'
        require(observation.get('schema_version') == expected_schema, 'compatibility arm schema differs')
        for key in ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'):
            require(observation.get(key) is False, 'wait authority must remain false')
        if arm == 'select':
            require(observation.get('internal_retry_count', 'missing') is None, 'select internal retry count must remain unknown')
            ratio = list(((target-before)/1_000_000_000).as_integer_ratio())
            require(observation.get('requested_seconds_ratio') == ratio, 'select compatibility conversion differs')
            require(observation.get('conversion_error_ns_ratio') == [ratio[0]*1_000_000_000-(target-before)*ratio[1], ratio[1]], 'select compatibility rounding differs')
        last = after
    require(len(canonical_json(result).encode('utf-8')) <= COMPATIBILITY['max_result_bytes'], 'compatibility result exceeds cap')
    return result


def rehearse(*, stage, frozen, ops, execute=False):
    """Offline callbacks only. Production preflight/driver remains unimplemented.

    ops must expose preflight, claim, public_state, start, ready, bind, release,
    finish, capture, result, stop, recheck, publish. Each external observation needs a
    separately bounded production adapter before this can become a native driver.
    """
    require(execute is True, 'explicit injected rehearsal required')
    validate_freeze(frozen)
    specs = [unit_spec(stage, role) for role in ('tests', 'compatibility')]
    checked = ops.preflight(stage, deepcopy(frozen))
    require(type(checked) is dict and all(value is True for value in checked.values()) and checked == dict(fresh_stage=True, clean_source=True,
                            source_freeze_matches=True, runtime_freeze_matches=True,
                            canonical_qcrl_owner=True, fixed_interpreter=True,
                            disk_reserve_over_4_gib=True, public_prerequisites_match=True,
                            private_units_absent=True), 'offline preflight receipt differs')
    before = ops.public_state()
    # Claim must be exclusive and precede every start. Failure is never retried.
    ops.claim(stage, frozen['freeze_sha256'])
    started, capture_attempted, stopped = [], set(), set()
    result = dict(schema_version='qcrl.wait_lifecycle_rehearsal.v1',
                  freeze_sha256=frozen['freeze_sha256'], complete=False,
                  error=None, preservation_errors=[], public_before=deepcopy(before),
                  public_after=None, compatibility_result_sha256=None,
                  native_origin_verified=False, compatibility_verified=False,
                  acceptance_demonstrated=False, orders_authorized=False)
    try:
        for spec in specs:
            unit = spec['unit']
            started.append(unit)
            ops.start(deepcopy(spec))
            if spec['role'] == 'compatibility':
                ready = ops.ready(unit, timeout_seconds=12, max_bytes=262144)
                require(type(ready) is dict and len(canonical_json(ready).encode('utf-8')) <= 262144, 'readiness exceeds cap')
                verify_artifact_hash(ready, 'ready_sha256', 'readiness')
                identity = ready['identity']
                require(ready.get('freeze_sha256') == frozen['freeze_sha256'] and ready.get('unit') == unit, 'readiness freeze/unit differs')
                require(type(identity.get('pid')) is int and identity['pid'] > 0
                        and identity.get('cgroup') == '/system.slice/'+unit+'.service'
                        and type(identity.get('boot_id')) is str and bool(identity['boot_id']), 'readiness identity invalid')
                binding = ops.bind(unit, deepcopy(ready))
                require(type(binding) is dict and binding.get('active') is True and binding == dict(unit=unit, identity=identity, active=True,
                                        observed_properties=spec['properties']), 'active binding/limits differ')
                release = dict(ready_sha256=ready['ready_sha256'], freeze_sha256=frozen['freeze_sha256'], binding_sha256=payload_hash(binding))
                release['release_sha256'] = payload_hash(release)
                ops.release(unit, deepcopy(release))
            ops.finish(unit, timeout_seconds=240)
            capture_attempted.add(unit)
            captured = ops.capture(unit, max_journal_bytes=65536)
            require(type(captured) is dict and type(captured.get('exec_status')) is int and captured == dict(unit=unit, result='success', exec_status=0,
                                     substate='exited', observed_properties=spec['properties']), 'unit completion/limits differ')
            if spec['role'] == 'compatibility':
                compatibility = ops.result(unit, max_bytes=262144)
                validate_compatibility(compatibility, frozen, ready, release)
                result['compatibility_result_sha256'] = compatibility['result_sha256']
            ops.stop(unit)
            stopped.add(unit)
        result['complete'] = True
    except Exception as exc:
        result['error'] = (type(exc).__name__+':'+str(exc))[:160]
    finally:
        for unit in reversed(started):
            if unit not in capture_attempted:
                capture_attempted.add(unit)
                try:
                    ops.capture(unit, max_journal_bytes=65536)
                except Exception as exc:
                    result['preservation_errors'].append(dict(unit=unit, capture_error=type(exc).__name__[:160]))
            if unit not in stopped:
                try:
                    ops.stop(unit)
                except Exception as exc:
                    result['preservation_errors'].append(dict(unit=unit, stop_error=type(exc).__name__[:160]))
        try:
            result['public_after'] = ops.public_state()
            require(result['public_after'] == before, 'public state drift; no restoration')
            require(ops.recheck(stage, deepcopy(frozen)) == dict(clean_source=True, source_freeze_matches=True, runtime_freeze_matches=True), 'source/runtime envelope drift')
        except Exception as exc:
            result['error'] = result['error'] or (type(exc).__name__+':'+str(exc))[:160]
        result['complete'] = result['complete'] and result['error'] is None and not result['preservation_errors']
        result['rehearsal_sha256'] = payload_hash(result)
        ops.publish(deepcopy(result), max_bytes=262144)
    return result
