"""Prospective localhost recorder declaration only; no launcher or evaluator."""
from copy import deepcopy
import argparse
import json
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_CONDITION = '0x' + '11' * 32
POLICY = {
    'schema_version': 'qcrl.recorder_application_budget_policy.v1',
    'scope': 'actual_segmented_recorder_loopback_websocket_synthetic_not_venue',
    'source_baseline': 'e4b28b7d26fb2203984957f8b142b00ffbc00dae',
    'case_order': ['steady-0', 'mixed-0', 'mixed-1', 'steady-1', 'steady-2', 'mixed-2'],
    'workloads': {
        'steady': [{'seconds': 120, 'rate': 500}],
        'mixed': [{'seconds': 10, 'rate': 500}, {'seconds': 10, 'rate': 3000},
                  {'seconds': 50, 'rate': 500}],
    },
    'occurrences_per_case': 60000,
    'total_occurrences': 360000,
    'wire': 'real_websockets_sync_client_and_server_ipv4_127.0.0.1_only_no_tls',
    'connection': 'one_per_case_no_injected_recv_no_public_connector',
    'subscription': 'verify_exact_frozen_two_token_subscription_before_epoch',
    'epoch': 'producer_recorder_observer_ready_barrier_then_future_shared_native_monotonic',
    'schedule': 'each_phase_start_plus_index_over_rate_no_drop_or_rate_retuning',
    'late_send': 'send_in_original_order_retain_every_deadline_and_send_bracket',
    'send_bracket_max_seconds': .05,
    'send_start_lateness_max_seconds': .05,
    'send_start_phase_attainment_min': .99,
    'frame_limit': 60000,
    'capture_max_seconds': 180,
    'synthetic_terms': 'five_minute_fixture_start_epoch_minus_10s_end_start_plus_300s',
    'synthetic_condition_id': SYNTHETIC_CONDITION,
    'frame_selection': 'initial_book_10001_initial_book_10002_then_cycle_by_occurrence_minus_2',
    'frame_mutation': 'none_no_sequence_injection_no_timestamp_retiming',
    'phase_assignment': 'producer_occurrence_schedule_not_receive_time',
    'timing_groups': 'each_case_and_each_separate_phase_no_pooling_or_outlier_exclusion',
    'recorder': {'segmented': True, 'profiling': False, 'receive_path': False,
                 'resilient': False, 'freshness_telemetry': False,
                 'fsync_every_records': 64, 'fsync_interval_seconds': 1,
                 'completion_capacity': 65536, 'barrier_capacity': 65536,
                 'sideband_encoded_bytes_max': 33554432},
    'unit': {'cpu_quota_percent': 75, 'memory_max_bytes': 536870912,
             'tasks_max': 32, 'runtime_max_seconds': 240},
    'producer_unit': {'cpu_quota_percent': 75, 'memory_max_bytes': 536870912,
                      'tasks_max': 32, 'runtime_max_seconds': 240},
    'actors': 'recorder_supervisor_and_resource_observer_one_dedicated_cgroup_no_double_count',
    'producer_resources': 'separate_cgroup_excluded_from_recorder_budget_reported_separately',
    'cpu_windows': 'epoch_anchored_complete_nonoverlapping_60s_windows_only',
    'cpu_bound': 'enclosing_cgroup_usage_delta_upper_divided_by_60s_times_effective_quota',
    'counter_boundary_bracket_max_seconds': .005,
    'rss': 'sum_current_VmRSS_all_unique_live_cgroup_processes_at_epoch_plus_integer_seconds',
    'rss_sample_bracket_max_seconds': .005,
    'rss_sample_lateness_max_seconds': .05,
    'rss_peak_claim': False,
    'resources_include': 'subscription_capture_close_all_active_observer_work',
    'resources_outside_gate': 'startup_and_post_collection_sideband_publication_audit_report_separately',
    'runtime_witnesses': ['boot_id', 'pid_starttime', 'live_cgroup_membership',
                          'cpu_max', 'cpuset_effective', 'memory_max', 'unit_properties',
                          'dependency_versions', 'clock_domain', 'instance_credit_policy',
                          'cpu_stat', 'memory_events', 'current_rss', 'host_concurrency'],
    'completion': 'all_sent_supported_text_occurrences_equal_archived_ordered_raw_bytes',
    'terminal': 'frame_limit_with_footer_manifest_complete_sideband_no_gap_or_reconnect',
    'failure': 'preserve_prefix_and_all_evidence_no_same_case_retry_replay_or_substitution',
    'outcomes': 'archive_integrity_workload_validity_application_budget_separate',
    'precedence': 'known_failures_retained_missing_evidence_unknown_never_pass',
    'stopping': 'one_finite_six_case_cohort_then_review_no_automatic_optimization',
    'public_state': 'unchanged_source_environment_services_limits_no_restart_or_capture',
}


def corpus():
    """Synthetic shapes only; deliberately includes repeated and malformed text."""
    def book(token):
        return json.dumps(dict(event_type='book', market=SYNTHETIC_CONDITION,
                               asset_id=token, timestamp='0',
                               bids=[{'price': '0.49', 'size': '100'}] * 20,
                               asks=[{'price': '0.51', 'size': '100'}] * 20),
                          sort_keys=True, separators=(',', ':'))
    books = [book('10001'), book('10002')]
    change = dict(event_type='price_change', market=SYNTHETIC_CONDITION, timestamp='0',
                  price_changes=[dict(asset_id=t, price='0.50', size='10', side='BUY',
                                      best_bid='0.49', best_ask='0.51')
                                 for t in ('10001', '10002')])
    cycle = books + [json.dumps(change, sort_keys=True, separators=(',', ':')),
                     json.dumps([change, change], sort_keys=True, separators=(',', ':')),
                     'PONG', '{malformed', '{"event_type":"synthetic_unknown"}', 'PONG']
    return dict(schema_version='qcrl.recorder_localhost_corpus.v1',
                synthetic=True, initial=books, cycle=cycle,
                representative_of_live_distribution=False)


def sources():
    names = ['infra/stream/recorder_application_budget.py',
             'infra/stream/recorder_completion.py', 'infra/stream/recorder_completion_lane.py',
             'tests/test_recorder_application_budget.py',
             'docs/RECORDER_APPLICATION_BUDGET_PREREGISTRATION.md',
             'execution_truth/specs/minimum_useful_research_recorder_draft.json']
    # Full execution-truth inventory protects transitive collector dependencies.
    names += [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'execution_truth').glob('*.py'))]
    return {name: file_hash(ROOT / name) for name in names}


def declare():
    draft = json.loads((ROOT / 'execution_truth/specs/minimum_useful_research_recorder_draft.json').read_text())
    obj = dict(schema_version='qcrl.recorder_application_budget_declaration.v1',
               policy=deepcopy(POLICY), budgets=deepcopy(draft['budgets']),
               sources=sources(), corpus=corpus(), corpus_sha256=payload_hash(corpus()),
               workers_implemented=False, launcher_implemented=False,
               acceptance_evaluator_implemented=False, execution_authorized=False,
               benchmark_performed=False, acceptance_demonstrated=False,
               deployment_authorized=False, public_rollout_authorized=False,
               orders_authorized=False, prior_probe_rejections_superseded=False)
    obj['plan_sha256'] = payload_hash(obj)
    return obj


def validate(obj):
    verify_artifact_hash(obj, 'plan_sha256', 'recorder application declaration')
    if obj != declare():
        raise ContractError('recorder application source/input/policy drift')
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    from execution_truth.stream_segments import exclusive_json
    obj = declare()
    exclusive_json(args.output, obj)
    print(json.dumps({'plan_sha256': obj['plan_sha256'], 'execution_authorized': False}))


if __name__ == '__main__':
    main()
