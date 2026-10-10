"""Separate packed-worker/pinned-observer declaration; no execution authorization."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_validity_cost as baseline
from infra.stream.receive_loop_validity_packed import METHOD
from infra.stream.receive_loop_pinned_observer import METHOD as OBSERVER_METHOD

POLICY = deepcopy(baseline.POLICY)
POLICY.update(schema_version='qcrl.pinned_combined_cost_policy.v1',
              scope='packed_synthetic_producer_and_pinned_observer_not_recorder_or_exchange',
              adapter=deepcopy(METHOD), observer_adapter=deepcopy(OBSERVER_METHOD),
              cpu_window='worker_collection_plus_observer_entire_window_including_first_pin_and_cleanup',
              validation_timing='finite_order_identity_cpu_bounds_inline_partition_materialization_after_close',
              sideband_size_basis='canonical_core_without_raws_plus_observer_compact_json_not_wrapper_duplicate',
              frozen_baseline_acceptance=deepcopy(baseline.POLICY['acceptance']))

FILES = (
    'infra/stream/receive_loop_validity_packed.py',
    'tests/test_receive_loop_validity_packed.py',
    'infra/stream/receive_loop_pinned_cost.py',
    'tests/test_receive_loop_pinned_cost.py',
    'infra/stream/receive_loop_pinned_trial.py',
    'tests/test_receive_loop_pinned_trial.py',
    'infra/stream/receive_loop_pinned_launch.py',
    'tests/test_receive_loop_pinned_launch.py',
    'infra/stream/receive_loop_pinned_audit.py',
    'tests/test_receive_loop_pinned_audit.py',
    'infra/stream/receive_loop_validity_observer.py',
    'infra/stream/receive_loop_validity_resources.py',
    'infra/stream/receive_loop_validity_metrics.py',
    'infra/stream/receive_loop_compact_launch.py',
    'infra/stream/receive_loop_compact_audit.py',
    'docs/PINNED_COMBINED_COST.md',
    'infra/stream/receive_loop_pinned_observer.py',
    'tests/test_receive_loop_pinned_observer.py',
    'infra/stream/receive_loop_pinned_counter.py',
    'tests/test_receive_loop_pinned_counter.py',
)


def sources():
    root=Path(__file__).resolve().parents[2]
    return dict(baseline.sources(), **{p:file_hash(root/p) for p in FILES})


def declare():
    obj=dict(schema_version='qcrl.pinned_combined_cost_declaration.v1',
             policy=deepcopy(POLICY), sources=sources(),
             prior_plan_sha256='dfd19d6179100ff5de298f8a2b79bb4eea68a6217a66190712fb27260c8b121a',
             prior_audit_sha256='dff05667c263e859566d1d334c48446ebda6f8a866411a5c2ee12f884dfc06e5',
             prior_verdict='reject', workers_implemented=True, launcher_implemented=True,
             auditor_implemented=True, benchmark_performed=False, execution_authorized=False,
             probe_cost_accepted=False, public_rollout_authorized=False, orders_authorized=False)
    obj['plan_sha256']=payload_hash(obj)
    return obj


def validate(obj):
    if not isinstance(obj,dict):raise ContractError('packed declaration object required')
    verify_artifact_hash(obj,'plan_sha256','packed cost declaration')
    if obj!=declare():raise ContractError('packed source/policy/authority differs')
    return obj


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    from execution_truth.rolling_stream import persist
    obj=declare();persist(args.output,obj)
    print(json.dumps({'plan_sha256':obj['plan_sha256'],'execution_authorized':False}))


if __name__=='__main__':main()

