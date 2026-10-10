"""Offline, source-bound diagnostic probe-cost declaration. No worker execution."""
import argparse
from copy import deepcopy
from pathlib import Path
import json

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash

POLICY = {
    'schema_version': 'qcrl.validity_probe_cost_policy.v1',
    'scope': 'synthetic_producer_and_counter_observer_not_recorder_or_exchange',
    'lanes': ['control', 'pacing', 'full'],
    'order': [['control', 'pacing', 'full'], ['pacing', 'full', 'control'],
              ['full', 'control', 'pacing']],
    'cases': 9, 'cycles': 6,
    'phases': [{'seconds': 4, 'rate': 500}, {'seconds': 1, 'rate': 3000}],
    'deliveries_per_case': 30000,
    'pacing': 'absolute_deadlines_no_drops_no_catchup_rate_retuning',
    'operations': 'same_prepare_and_in_memory_send_sink_all_lanes_no_sockets',
    'input': 'versioned_deterministic_synthetic_generator_frozen_before_execution',
    'control': 'four_monotonic_calls_per_step_deadline_check_begin_send_start_send_end',
    'pacing': 'PacingProbe_seven_monotonic_calls_per_step_plus_initial_stamp',
    'full': 'pacing_plus_two_cpu_stamps_per_step_and_counter_observer',
    'cpu_stamp_order': 'thread_identity_wall_before_thread_cpu_wall_after',
    'full_added_per_step': {'wall_calls': 4, 'thread_cpu_calls': 2, 'thread_identity_calls': 2},
    'producer_capacity': 30000,
    'cpu_pair_capacity': 30000,
    'observer_interval_seconds': .1,
    'observer_capacity': 512,
    'observer_in_control_and_pacing': 'same_absolute_wake_schedule_without_proc_reads',
    'observer_in_full': 'CounterReader_samples_dedicated_worker_cgroup_no_auto_discovery',
    'observer_missed_deadlines': 'record_lateness_never_catchup_burst_or_adapt_interval',
    'workers': {'cpu_quota_percent': 100, 'memory_max_bytes': 536870912,
                'tasks_max': 32, 'runtime_max_seconds': 120},
    'observers': {'cpu_quota_percent': 25, 'memory_max_bytes': 536870912,
                  'tasks_max': 32, 'runtime_max_seconds': 120},
    'isolation': 'separate_worker_observer_processes_and_cgroups_shared_host_no_affinity',
    'cpu_window': 'worker_collection_close_plus_observer_entire_worker_window_no_subtraction',
    'outside_window': ['row_snapshot_serialization', 'archive_verification', 'analysis'],
    'raw_occurrences': 'ordered_generator_and_sink_identity_for_all_30000_not_just_digest_set',
    'counter_read_byte_limit': 4096,
    'sideband_encoded_bytes_max_per_case': 33554432,
    'acceptance': {
        'all_cases_complete': True, 'all_rows_and_occurrences_required': True,
        'all_cpu_pairs_valid': True, 'max_inline_clock_bracket_seconds': .001,
        'counter_read_bracket_max_seconds': .005,
        'required_counters': ['usage_usec', 'nr_periods', 'nr_throttled', 'throttled_usec'],
        'counter_identity_stable_and_no_reset': True,
        'producer_phase_attainment_min': .99,
        'producer_deadline_lateness_max_seconds': .05,
        'observer_lateness_max_seconds': .05,
        'combined_cpu_ratio_max_each_lane_vs_round_control': 1.05,
        'combined_sampled_rss_ratio_max_each_lane_vs_round_control': 1.10,
        'p99_begin_lateness_added_seconds_max': .001,
        'worst_begin_lateness_added_seconds_max': .005,
        'tail_estimator': 'nearest_rank_separate_each_phase_and_round_no_pooling',
        'zero_cpu_or_rss_control_denominator': 'inconclusive',
        'missing_platform_counters_or_unit_identity': 'inconclusive',
        'known_loss_reset_overflow_resource_or_threshold_failure': 'reject',
        'inconclusive_precedence': 'retain_all_rejections_and_unknowns_never_pass',
    },
    'failure': 'preserve_once_no_retry_replay_retune_or_same_cohort_confirmation',
    'pass_advancement': 'separately_preregister_validity_workload_not_recorder_acceptance',
    'public_state': 'must_remain_unchanged_no_stop_restart_or_resource_changes',
}


def sources():
    root = Path(__file__).resolve().parents[2]
    names = ('infra/stream/receive_loop_validity.py',
             'infra/stream/receive_loop_validity_probe.py',
             'infra/stream/receive_loop_validity_smoke.py',
             'infra/stream/receive_loop_validity_cost.py',
             'tests/test_receive_loop_validity.py',
             'tests/test_receive_loop_validity_probe.py',
             'tests/test_receive_loop_validity_smoke.py',
             'tests/test_receive_loop_validity_cost.py',
             'docs/RECEIVE_LOOP_VALIDITY_COST.md',
             'execution_truth/contracts.py', 'execution_truth/stream_segments.py')
    return {name: file_hash(root/name) for name in names}


def declare():
    obj = dict(schema_version='qcrl.validity_probe_cost_declaration.v1',
               policy=deepcopy(POLICY), sources=sources(),
               prior_compact_plan_sha256='c909b91e94413bc2f5a0bcc34f14b328bd4ed76d5258cde6168d05e4db224e8e',
               prior_compact_verdict='inconclusive',
               prior_audit_sha256='f9cb0e6c9b2f488606a05850a26c3206ffafeb1348773f884ca5647c25c550f9',
               workers_implemented=False, launcher_implemented=False,
               benchmark_performed=False, execution_authorized=False,
               probe_cost_accepted=False, public_rollout_authorized=False, orders_authorized=False)
    obj['plan_sha256'] = payload_hash(obj)
    return obj


def validate(obj):
    if not isinstance(obj, dict):
        raise ContractError('probe-cost declaration object required')
    verify_artifact_hash(obj, 'plan_sha256', 'validity probe-cost declaration')
    if obj != declare():
        raise ContractError('probe-cost source/policy/scope changed')
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    from execution_truth.rolling_stream import persist
    obj = declare()
    persist(args.output, obj)
    print(json.dumps({'plan_sha256': obj['plan_sha256'], 'execution_authorized': False}))


if __name__ == '__main__': main()
