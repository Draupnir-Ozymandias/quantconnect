"""Offline structural/arithmetic audit and bounded exclusive publication."""
from fractions import Fraction
from pathlib import Path

from execution_truth.contracts import ContractError, canonical_json, payload_hash, verify_artifact_hash
from infra.stream import recorder_wait_comparison as original
from infra.stream.recorder_wait_comparison_v2 import PLAN
from infra.stream.recorder_absolute_wait import NS, MAX_WAIT_NS, timestamp


def require(condition, message):
    if not condition:
        raise ContractError(message)


def _error(value):
    require(value is None or (type(value) is str and 0 < len(value) <= 160), 'bounded error required')


def _no_authority(value):
    for key in ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'):
        require(value.get(key) is False, 'offline authority must remain false')


def validate_run(result):
    require(type(result) is dict, 'run object required')
    require(len(canonical_json(result).encode('utf-8')) <= PLAN['max_result_bytes_per_run'], 'run exceeds byte cap')
    verify_artifact_hash(result, 'run_sha256', 'comparison run')
    require(result.get('schema_version') == 'qcrl.wait_comparison_run.v2', 'run schema mismatch')
    require(result.get('plan_sha256') == payload_hash(PLAN), 'plan mismatch')
    index = result.get('run_index')
    require(type(index) is int and index in (0, 1), 'run index mismatch')
    _no_authority(result)
    _error(result.get('fatal_error'))
    require(type(result.get('cancelled')) is bool, 'cancelled flag required')
    baseline, rows = result.get('baseline'), result.get('rows')
    require(type(baseline) is list and len(baseline) <= 16 and type(rows) is list, 'bounded population required')
    last = None
    for pair in baseline:
        before, after = timestamp(pair['before_ns']), timestamp(pair['after_ns'])
        require((last is None or before >= last) and after >= before, 'baseline regressed')
        last = after
    if result['epoch_ns'] is None:
        require(not rows and result['fatal_error'] is not None, 'uninstantiated run requires failure')
        if result['cancelled']:
            require(index == 1 and not baseline and result['fatal_error'] == 'prior_run_fatal_cancelled', 'invalid cancellation')
        return result
    require(not result['cancelled'] and len(baseline) == 16, 'initialized run baseline mismatch')
    epoch = timestamp(result['epoch_ns'])
    require(epoch >= last, 'epoch regressed')
    last = epoch
    expected = original.targets(epoch, index)
    require(len(rows) == 12, 'all declared rows required')
    fatal = None
    for ordinal, (row, target) in enumerate(zip(rows, expected)):
        require(row.get('ordinal') == ordinal and type(row.get('ordinal')) is int, 'ordinal mismatch')
        for key, value in target.items():
            require(type(row.get(key)) is type(value) and row[key] == value, 'target population mismatch')
        _error(row.get('error'))
        observation = row.get('observation')
        checkpoint = row.get('checkpoint_ns')
        if fatal is not None:
            require(checkpoint is None and observation is None and row['error'] == 'prior_wait_fault_no_attempt', 'attempt after fatal fault')
            continue
        if checkpoint is not None:
            checkpoint = timestamp(checkpoint)
            if checkpoint < last:
                require(observation is None and row['error'] == 'ContractError:comparison clock regressed before attempt', 'checkpoint regression not refused')
                fatal = row['error']
                continue
            last = checkpoint
        if observation is None:
            require(row['error'] is not None, 'missing observation must retain error')
            fatal = row['error']
            continue
        require(checkpoint is not None, 'observation requires checkpoint')
        require(type(observation) is dict, 'observation object required')
        verify_artifact_hash(observation, 'wait_sha256', 'wait')
        _no_authority(observation)
        _error(observation.get('error'))
        require(type(observation.get('retries')) is int and observation['retries'] == 0, 'application retries forbidden')
        require(type(observation.get('attempted')) is bool, 'attempted flag required')
        require(type(observation.get('target_ns')) is int and observation['target_ns'] == target['target_ns'], 'wait target mismatch')
        before = timestamp(observation['before_ns'])
        remaining = target['target_ns']-before
        require(type(observation['requested_remaining_ns']) is int and observation['requested_remaining_ns'] == remaining, 'remaining mismatch')
        schema = 'qcrl.select_wait.v2' if target['arm'] == 'select' else 'qcrl.absolute_monotonic_wait.v1'
        require(observation.get('schema_version') == schema, 'arm schema mismatch')
        if target['arm'] == 'select':
            require(observation.get('internal_retry_count', 'missing') is None, 'select internal retries must remain unknown')
            if observation['attempted']:
                ratio = list((remaining/NS).as_integer_ratio())
                require(observation['requested_seconds_ratio'] == ratio, 'select request conversion mismatch')
                require(observation['conversion_error_ns_ratio'] == [ratio[0]*NS-remaining*ratio[1], ratio[1]], 'conversion error mismatch')
            else:
                require(observation['requested_seconds_ratio'] is None and observation['conversion_error_ns_ratio'] is None, 'unattempted request representation')
        code = observation.get('return_code')
        require(code is None or (type(code) is int and 0 <= code <= 4095), 'invalid return code')
        if target['arm'] == 'select':
            require(code in (None, 0), 'select return code mismatch')
        after = observation.get('after_ns')
        if after is not None:
            after = timestamp(after)
        lateness = observation.get('lateness_ns')
        if after is not None and after >= before and observation['attempted']:
            require(type(lateness) is int and lateness == after-target['target_ns'], 'lateness mismatch')
        else:
            require(lateness is None, 'invalid lateness enclosure')
        status, error = observation.get('status'), observation.get('error')
        require(status in ('unknown', 'observed'), 'invalid status')
        if observation['attempted']:
            require(0 < remaining <= MAX_WAIT_NS, 'attempt outside wait cap')
            if status == 'observed':
                require(error is None and code == 0 and after is not None and after >= target['target_ns'], 'invalid observed wait')
            else:
                require(error is not None, 'unknown wait requires error')
        else:
            require(status == 'unknown' and error is not None and after is None and code is None, 'invalid refused wait')
            if error == 'target_already_missed_no_catch_up':
                require(remaining <= 0, 'missed target arithmetic mismatch')
            elif error == 'remaining_wait_exceeds_fixed_cap':
                require(remaining > MAX_WAIT_NS, 'wait cap arithmetic mismatch')
            else:
                require(error == 'clock_regressed_between_waits', 'invalid refusal reason')
        if before < last:
            require(row['error'] == 'ContractError:comparison clock regressed across arms', 'cross-arm clock regression not retained')
            fatal = row['error']
        else:
            require(row['error'] is None, 'unexpected collector error')
            last = max(before, after if after is not None and after >= before else before)
            if error is not None and error != 'target_already_missed_no_catch_up':
                fatal = error
    require(result['fatal_error'] == fatal, 'fatal summary mismatch')
    return result


def evaluate(runs):
    require(type(runs) is list and len(runs) == 2, 'both declared run receipts required')
    for index, run in enumerate(runs):
        validate_run(run)
        require(run['run_index'] == index, 'run ordering mismatch')
    if runs[0]['fatal_error'] is not None:
        require(runs[1]['cancelled'], 'second run must be cancelled after fatal run zero')
    else:
        require(not runs[1]['cancelled'], 'unexpected cancellation')
    pairs = []
    for interval in PLAN['interval_ns']:
        differences = []
        for run in runs:
            cells = {row['arm']: row for row in run['rows'] if row['interval_ns'] == interval}
            observed = {}
            for arm in ('select', 'absolute'):
                cell = cells.get(arm)
                obs = cell['observation'] if cell else None
                observed[arm] = obs['lateness_ns'] if obs and obs['status'] == 'observed' and cell['error'] is None else None
            difference = None if any(value is None for value in observed.values()) else observed['absolute']-observed['select']
            differences.append(difference)
            pairs.append(dict(run_index=run['run_index'], interval_ns=interval,
                              lateness_ns=observed, absolute_minus_select_ns=difference))
    stats = []
    for interval in PLAN['interval_ns']:
        values = [pair['absolute_minus_select_ns'] for pair in pairs if pair['interval_ns'] == interval]
        exact = None if None in values else Fraction(sum(values), 2)
        arm_stats = {}
        for arm in ('select', 'absolute'):
            samples = sorted(pair['lateness_ns'][arm] for pair in pairs
                             if pair['interval_ns'] == interval and pair['lateness_ns'][arm] is not None)
            mid = None if not samples else Fraction(sum(samples), len(samples))
            arm_stats[arm] = dict(observed=len(samples), unknown=2-len(samples),
                                 minimum_ns=samples[0] if samples else None,
                                 maximum_ns=samples[-1] if samples else None,
                                 median_ns_ratio=None if mid is None else [mid.numerator, mid.denominator])
        stats.append(dict(interval_ns=interval, arms=arm_stats,
                          median_difference_ns_ratio=None if exact is None else [exact.numerator, exact.denominator]))
    arms = {}
    for arm in ('select', 'absolute'):
        values = [pair['lateness_ns'][arm] for pair in pairs if pair['lateness_ns'][arm] is not None]
        arms[arm] = dict(observed=len(values), unknown=12-len(values))
    result = dict(schema_version='qcrl.wait_comparison_summary.v2', plan_sha256=payload_hash(PLAN),
                  run_sha256=[run['run_sha256'] for run in runs], pairs=pairs,
                  interval_statistics=stats, arm_counts=arms,
                  comparison_complete=all(pair['absolute_minus_select_ns'] is not None for pair in pairs),
                  native_origin_verified=False, acceptance_demonstrated=False, orders_authorized=False)
    result['summary_sha256'] = payload_hash(result)
    require(len(canonical_json(result).encode('utf-8')) <= PLAN['max_summary_bytes'], 'summary exceeds byte cap')
    return result


def publish_run(path, result):
    """Validate before exclusive creation; failed writes are retained, never replaced."""
    validate_run(result)
    data = canonical_json(result).encode('utf-8')
    with Path(path).open('xb') as output:
        output.write(data)
    import hashlib
    return dict(bytes=len(data), file_sha256=hashlib.sha256(data).hexdigest(),
                native_origin_verified=False)


def publish_summary(path, runs):
    result = evaluate(runs)
    data = canonical_json(result).encode('utf-8')
    with Path(path).open('xb') as output:
        output.write(data)
    import hashlib
    return dict(bytes=len(data), file_sha256=hashlib.sha256(data).hexdigest(),
                summary_sha256=result['summary_sha256'], native_origin_verified=False)
