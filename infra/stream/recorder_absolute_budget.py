"""Prospective isolated-recorder absolute-observer protocol; no native launcher."""
from copy import deepcopy
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream.recorder_application_budget import declare as parent_declaration

PARENT = 'c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade'
PLAN = dict(
    schema_version='qcrl.recorder_absolute_budget_plan.v1',
    parent_declaration_sha256=PARENT,
    comparison_audit_sha256='c2a6b59f07563fbf10f8184fd09494d89f0400e6bc9917bf1337ced04a466f4d',
    scope='isolated_recorder_resource_observer_only_not_receive_or_producer',
    epoch='ceil_exact_represented_shared_epoch_seconds_once_then_integer_offsets',
    rss_period_ns=1_000_000_000, cpu_period_slots=60, cpu_lead_ns=50_000_000,
    max_slots=184, max_wait_ns=60_000_000_000, wake_lateness_max_ns=50_000_000,
    counter_bracket_max_ns=5_000_000, attempts_per_endpoint=1, retries=0,
    missed='past_or_equal_target_unknown_no_wait_no_read_continue_original_grid',
    late='return_over_50ms_unknown_no_read_continue_original_grid',
    wait_fault='stop_observer_retain_prefix_and_unavailable_slots_no_replay',
    read_fault='retain_unknown_slot_continue_original_grid_no_read_retry',
    compatibility=dict(runs=1, occurrences=68, rate_per_second=1,
                       first_offset_ns=0, last_offset_ns=67_000_000_000,
                       capture_max_seconds=180, complete_cpu_windows=[0],
                       population='first_68_unchanged_parent_corpus_occurrences',
                       acceptance_scope='interface_and_evidence_only_not_budget_cohort'),
    budget='unchanged_parent_six_serial_cases_after_separate_compatibility_review',
    cpu_enclosure='50ms_pre_read_then_RSS_read_at_following_60s_boundary_no_subtraction',
    stop='one_compatibility_then_review_no_automatic_budget_launch_no_replacement',
    native_execution_authorized=False, acceptance_demonstrated=False,
    public_rollout_authorized=False, orders_authorized=False,
)


def declaration():
    parent = parent_declaration()
    if parent['plan_sha256'] != PARENT:
        raise ContractError('original recorder declaration changed')
    root = Path(__file__).resolve().parents[2]
    names = ['infra/stream/recorder_absolute_observer.py',
             'infra/stream/recorder_absolute_budget.py',
             'infra/stream/recorder_application_worker.py',
             'infra/stream/recorder_application_resources.py',
             'infra/stream/recorder_application_evaluator.py',
             'infra/stream/recorder_absolute_wait.py',
             'tests/test_recorder_absolute_observer.py',
             'docs/RECORDER_ABSOLUTE_BUDGET_PREREGISTRATION.md']
    value = dict(schema_version='qcrl.recorder_absolute_budget_declaration.v1',
                 plan=deepcopy(PLAN), plan_sha256=payload_hash(PLAN),
                 parent_declaration_sha256=PARENT, budgets=deepcopy(parent['budgets']),
                 case_order=deepcopy(parent['policy']['case_order']),
                 workloads=deepcopy(parent['policy']['workloads']),
                 corpus_sha256=parent['corpus_sha256'],
                 unit=deepcopy(parent['policy']['unit']),
                 producer_unit=deepcopy(parent['policy']['producer_unit']),
                 sources={name: file_hash(root/name) for name in names},
                 native_execution_authorized=False, compatibility_verified=False,
                 budget_cohort_performed=False, acceptance_demonstrated=False,
                 orders_authorized=False)
    value['declaration_sha256'] = payload_hash(value)
    return value


def validate(value):
    verify_artifact_hash(value, 'declaration_sha256', 'absolute recorder declaration')
    if value != declaration():
        raise ContractError('absolute recorder protocol/source drift')
    return value
