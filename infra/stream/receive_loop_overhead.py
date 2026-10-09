"""Offline preregistration only; no socket, worker, benchmark or deployment launcher."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream.reader_comparison import load_corpus
from infra.stream import receive_loop_contract as loop

CORPUS_SHA256 = 'a343b91c289731a9262354bb629b4ef22379b67a806568e3d4f2caf08d1fa849'
ANALYSIS_SHA256 = 'c846322545a4c4007b815a066ae4067109af63f4bc01b797fc5c5278337c9dc0'
POLICY = {
    'schema_version': 'qcrl.receive_loop_overhead_policy.v1',
    'network': 'numeric_localhost_only', 'lanes': ['baseline', 'instrumented'],
    'pair_order': [['baseline', 'instrumented'], ['instrumented', 'baseline'],
                   ['baseline', 'instrumented']],
    'cases': 6, 'cycles': 6, 'phases': [{'seconds': 4, 'rate': 500}, {'seconds': 1, 'rate': 3000}],
    'messages_per_case': 30000, 'scheduled_seconds_per_case': 30,
    'pacing': 'absolute_deadlines_no_drops',
    'heartbeat': 'replace_last_message_of_each_cycle_with_synthetic_text_PONG',
    'encoder': 'single_pass', 'receive_policy': 'scoped_v3_cap128',
    'marker_cap': 128, 'library_high_water_frames': 16, 'library_low_water_frames': 4,
    'socket_recv_bufsize': 65536, 'max_size_bytes': 262144,
    'compression': None, 'protocol_ping_interval': None, 'proxy': None,
    'producer_cpu_quota_percent': 100, 'consumer_cpu_quota_percent': 75,
    'memory_max_bytes_per_process_group': 536870912, 'tasks_max': 32,
    'runtime_max_seconds_per_unit': 120,
    'isolation': 'separate_process_and_cgroup_shared_host_no_core_affinity',
    'baseline': 'ObservedSocket_no_receive_loop_probe',
    'instrumented': 'DiagnosticSocket_same_inherited_recv_queue_send_close',
    'measurement': 'before_connect_through_collector_return_close_and_receiver_join',
    'outside_measurement': ['sideband_snapshot', 'sideband_serialization', 'archive_verification',
                            'delivery_serialization', 'analysis'],
    'durability': 'unchanged_single_pass_segment_gzip_flush_fsync_final_seal',
    'max_read_summaries': 32768, 'max_flow_edges': 32768,
    'max_encoded_sideband_bytes': 33554432,
    'acceptance': {
        'complete_cases_required': 6, 'raw_delivery_fraction': 1.0,
        'baseline_and_instrumented_timing_eligible_fraction': 1.0,
        'instrumented_linked_dispatch_fraction': 1.0,
        'observation_loss_allowed': 0, 'resource_failures_allowed': 0,
        'marker_overflows_allowed': 0, 'open_recovery_episodes_allowed': 0,
        'each_pair_cpu_ratio_max': 1.05,
        'each_pair_low_rate_p99_ratio_max': 1.05,
        'each_pair_burst_p99_ratio_max': 1.05,
        'each_pair_worst_delivery_upper_bound_ratio_max': 1.05,
        'each_pair_sampled_rss_max_ratio_max': 1.10,
        'producer_phase_attainment_fraction_min': 0.99,
        'producer_max_deadline_lateness_seconds': 0.05,
        'missing_required_metric': 'inconclusive_not_pass',
        'zero_baseline_denominator': 'inconclusive_not_pass',
        'aggregation': 'all_three_pairs_pass_no_pooled_percentiles_or_median_override',
    },
    'failure_action': 'preserve_all_evidence_no_retry_retune_or_confirmation_in_this_cohort',
    'gate_authorizes': 'diagnostic_interval_analysis_only_not_causality_or_public_rollout',
    'execution_implemented': False, 'benchmark_performed': False,
    'public_rollout_authorized': False, 'orders_authorized': False,
}


def sources():
    repo = Path(__file__).resolve().parents[2]
    names = ['infra/stream/receive_loop_overhead.py', 'infra/stream/receive_loop_contract.py',
             'infra/stream/receive_loop_probe.py', 'infra/stream/receive_loop_lane.py',
             'infra/stream/reader_comparison.py', 'infra/stream/burst_reader_comparison.py',
             'infra/stream/marker_cap_pair.py', 'infra/stream/encoding_pair.py',
             'infra/stream/single_pass_encoder.py', 'docs/RECEIVE_LOOP_OVERHEAD.md',
             'tests/test_receive_loop_overhead.py']
    names += sorted(str(p.relative_to(repo)) for p in (repo/'execution_truth').glob('*.py'))
    return {name: file_hash(repo/name) for name in names}


def declare(corpus_path, contract):
    loop.validate_contract(contract)
    corpus = load_corpus(corpus_path)
    if corpus['corpus_sha256'] != CORPUS_SHA256:
        raise ContractError('overhead declaration requires the frozen original corpus')
    if contract['source_analysis_sha256'] != ANALYSIS_SHA256:
        raise ContractError('overhead declaration requires the verified decomposition binding')
    obj = {'schema_version': 'qcrl.receive_loop_overhead_declaration.v1',
           'policy': deepcopy(POLICY), 'corpus_sha256': CORPUS_SHA256,
           'loop_contract': deepcopy(contract), 'sources': sources(),
           'benchmark_performed': False, 'execution_authorized_by_declaration': False,
           'orders_authorized': False, 'public_rollout_authorized': False}
    obj['plan_sha256'] = payload_hash(obj)
    return obj


def validate(obj, corpus_path):
    verify_artifact_hash(obj, 'plan_sha256', 'receive-loop overhead declaration')
    if obj != declare(corpus_path, obj.get('loop_contract')):
        raise ContractError('overhead declaration differs from fixed policy or source bytes')
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--loop-contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    obj = declare(args.corpus, json.loads(args.loop_contract.read_text()))
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(obj, handle, sort_keys=True, indent=2); handle.write('\n')
    print(json.dumps({'plan_sha256': obj['plan_sha256'], 'benchmark_performed': False}))


if __name__ == '__main__': main()
