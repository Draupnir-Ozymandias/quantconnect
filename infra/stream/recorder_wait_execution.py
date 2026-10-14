"""Offline freeze and prospective compatibility envelope; no native driver."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path, PurePosixPath
import re

from execution_truth.contracts import ContractError, canonical_json, payload_hash, verify_artifact_hash
from infra.stream.recorder_wait_comparison_v2 import PLAN as COMPARISON

COMPATIBILITY = dict(
    schema_version='qcrl.wait_compatibility_plan.v1',
    experiment_id='absolute-select-compatibility-v1',
    comparison_plan_sha256=payload_hash(COMPARISON),
    arm_order=['select', 'absolute'], interval_ns=50_000_000,
    application_calls_per_arm=1, application_retries=0,
    select_internal_retry_count=None, max_result_bytes=262144,
    max_error_characters=160, unit_limits=deepcopy(COMPARISON['unit_limits']),
    stopping_rule='one_finite_compatibility_unit_no_retry_no_replay',
    faults='retain_unknown_stop_remaining_arms',
    signal_injection_authorized=False, native_execution_authorized=False,
    performance_acceptance=False, orders_authorized=False,
)
HASH = re.compile(r'[0-9a-f]{64}')
SELECT_POLICY = COMPARISON['select_runtime_retry_policy']
DOCUMENTS = {
    'docs/ABSOLUTE_MONOTONIC_WAIT_PROTOTYPE.md',
    'docs/ABSOLUTE_SELECT_COMPARISON_PREREGISTRATION.md',
    'docs/ABSOLUTE_SELECT_COMPARISON_V2.md',
    'docs/WAIT_EXECUTION_PREPARATION.md',
}


def require(value, message):
    if not value:
        raise ContractError(message)


def declaration():
    result = deepcopy(COMPATIBILITY)
    result['plan_sha256'] = payload_hash(result)
    return result


def selected(name):
    if type(name) is not str:
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or any(part in ('.', '..') for part in path.parts):
        return False
    if name in ('poly.py', 'poly2.py') or any(part.startswith('.') for part in path.parts):
        return False
    allowed_suffixes = {'.py', '.json', '.md', '.sh', '.ipynb'}
    if path.suffix not in allowed_suffixes:
        return False
    return (len(path.parts) == 1 or path.parts[0] in
            ('infra', 'execution_truth', 'tests', 'ops', 'campaigns', 'syntheses', 'discovery', 'docs'))


def source_inventory(root, tracked_paths):
    """Hash selected regular tracked inputs only; never read evidence or secrets."""
    root = Path(root)
    require(root.is_absolute() and root.resolve(strict=True) == root, 'canonical source root required')
    require(type(tracked_paths) is list and all(type(name) is str for name in tracked_paths), 'tracked path list required')
    require(len(tracked_paths) == len(set(tracked_paths)), 'duplicate tracked paths')
    names = sorted(name for name in tracked_paths if selected(name))
    required = DOCUMENTS | {
        'infra/stream/recorder_absolute_wait.py',
        'infra/stream/recorder_wait_comparison.py',
        'infra/stream/recorder_wait_comparison_v2.py',
        'infra/stream/recorder_wait_comparison_audit.py',
        'infra/stream/recorder_wait_execution.py',
        'infra/stream/recorder_wait_lifecycle.py',
        'infra/stream/recorder_wait_compatibility_worker.py',
        'infra/stream/recorder_wait_production.py',
        'tests/test_recorder_wait_production.py',
        'execution_truth/contracts.py',
        'tests/test_recorder_wait_execution.py',
    }
    require(required <= set(names), 'tracked execution inventory incomplete')
    result = {}
    for name in names:
        path = root/name
        require(path.resolve(strict=True) == path and path.is_file(), 'regular nonsymlink source required')
        require(path.stat().st_size <= 4*1024*1024, 'source file exceeds 4 MiB cap')
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            total = 0
            while True:
                block = handle.read(65536)
                if not block:
                    break
                total += len(block)
                require(total <= 4*1024*1024, 'source grew beyond cap')
                digest.update(block)
        result[name] = digest.hexdigest()
    return result


def validate_runtime(runtime):
    """Validate declared envelope fields; this is not installed-runtime proof."""
    require(type(runtime) is dict, 'runtime inventory required')
    expected = dict(system='Linux', libc='glibc', python='3.9.25',
                    gil_enabled=True, long_bits=64, pointer_bits=64,
                    timespec_size=16, tv_sec_offset=0, tv_nsec_offset=8,
                    clock_monotonic_id=1, timer_abstime=1,
                    monotonic_implementation='clock_gettime(CLOCK_MONOTONIC)',
                    clock_nanosleep_symbol='clock_nanosleep',
                    argtypes=['c_int', 'c_int', 'POINTER(Timespec)', 'c_void_p'],
                    restype='c_int', select_retry_policy=SELECT_POLICY,
                    signal_context_policy='observe_existing_handlers_no_changes')
    for key, value in expected.items():
        require(type(runtime.get(key)) is type(value) and runtime[key] == value, 'runtime field differs: '+key)
    require(runtime.get('machine') in ('aarch64', 'x86_64'), 'unsupported machine')
    require(runtime.get('select_binary_kind') in ('builtin', 'extension'), 'reviewed select binary kind required')
    for key in ('kernel', 'libc_version', 'monotonic_resolution', 'signal_handlers'):
        require(type(runtime.get(key)) is str and 0 < len(runtime[key]) <= 2048, 'bounded runtime context required: '+key)
    for key in ('python_binary_sha256', 'libc_binary_sha256', 'select_binary_sha256',
                'select_review_source_sha256', 'select_review_receipt_sha256'):
        require(type(runtime.get(key)) is str and HASH.fullmatch(runtime[key]), 'runtime hash required: '+key)
    try:
        resolution = Decimal(runtime['monotonic_resolution'])
        require(resolution.is_finite() and resolution > 0, 'finite positive clock resolution required')
    except InvalidOperation as exc:
        raise ContractError('numeric clock resolution required') from exc
    require(len(canonical_json(runtime).encode('utf-8')) <= 16384, 'runtime inventory exceeds cap')
    return runtime


def freeze(*, source_commit, sources, runtime):
    require(type(source_commit) is str and re.fullmatch('[0-9a-f]{40}', source_commit), 'exact source commit required')
    require(type(sources) is dict and bool(sources), 'source inventory required')
    for name, digest in sources.items():
        require(selected(name) and type(digest) is str and HASH.fullmatch(digest), 'invalid source inventory entry')
    # Inventory completeness is enforced by source_inventory and rechecked here.
    required = DOCUMENTS | {'infra/stream/recorder_wait_execution.py',
                           'infra/stream/recorder_wait_lifecycle.py',
                           'infra/stream/recorder_wait_comparison_v2.py',
                           'infra/stream/recorder_wait_comparison_audit.py',
                           'infra/stream/recorder_absolute_wait.py',
                           'infra/stream/recorder_wait_comparison.py',
                           'infra/stream/recorder_wait_compatibility_worker.py',
                           'infra/stream/recorder_wait_production.py',
                           'tests/test_recorder_wait_production.py',
                           'execution_truth/contracts.py', 'tests/test_recorder_wait_execution.py'}
    require(required <= set(sources), 'freeze inventory incomplete')
    validate_runtime(runtime)
    result = dict(schema_version='qcrl.wait_execution_freeze.v1',
                  source_commit=source_commit, sources=deepcopy(sources), runtime=deepcopy(runtime),
                  comparison_plan_sha256=payload_hash(COMPARISON),
                  compatibility_plan_sha256=payload_hash(COMPATIBILITY),
                  execution_authorized=False, native_origin_verified=False,
                  compatibility_verified=False, acceptance_demonstrated=False, orders_authorized=False)
    require(len(canonical_json(result).encode('utf-8')) <= 262144, 'freeze exceeds cap')
    result['freeze_sha256'] = payload_hash(result)
    return result


def validate_freeze(value):
    require(type(value) is dict, 'freeze object required')
    verify_artifact_hash(value, 'freeze_sha256', 'execution freeze')
    expected = freeze(source_commit=value.get('source_commit'), sources=value.get('sources'), runtime=value.get('runtime'))
    require(value == expected, 'freeze fields differ')
    return value
