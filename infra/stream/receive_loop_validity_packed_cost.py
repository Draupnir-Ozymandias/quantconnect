"""Separate packed-cost declaration; no execution authorization or benchmarking."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_validity_cost as baseline
from infra.stream.receive_loop_validity_packed import METHOD

POLICY = deepcopy(baseline.POLICY)
POLICY.update(schema_version='qcrl.validity_packed_cost_policy.v1',
              scope='packed_synthetic_producer_and_unchanged_counter_observer_not_recorder_or_exchange',
              adapter=deepcopy(METHOD),
              validation_timing='finite_order_identity_cpu_bounds_inline_partition_materialization_after_close',
              sideband_size_basis='canonical_core_without_raws_plus_observer_compact_json_not_wrapper_duplicate',
              frozen_baseline_acceptance=deepcopy(baseline.POLICY['acceptance']))

FILES = (
    'infra/stream/receive_loop_validity_packed.py',
    'tests/test_receive_loop_validity_packed.py',
    'infra/stream/receive_loop_validity_packed_cost.py',
    'tests/test_receive_loop_validity_packed_cost.py',
    'infra/stream/receive_loop_validity_packed_trial.py',
    'tests/test_receive_loop_validity_packed_trial.py',
    'infra/stream/receive_loop_validity_packed_launch.py',
    'tests/test_receive_loop_validity_packed_launch.py',
    'infra/stream/receive_loop_validity_packed_audit.py',
    'tests/test_receive_loop_validity_packed_audit.py',
    'infra/stream/receive_loop_validity_observer.py',
    'infra/stream/receive_loop_validity_resources.py',
    'infra/stream/receive_loop_validity_metrics.py',
    'infra/stream/receive_loop_compact_launch.py',
    'infra/stream/receive_loop_compact_audit.py',
    'docs/RECEIVE_LOOP_VALIDITY_PACKED_COST.md',
)


def sources():
    root=Path(__file__).resolve().parents[2]
    return dict(baseline.sources(), **{p:file_hash(root/p) for p in FILES})


def declare():
    obj=dict(schema_version='qcrl.validity_packed_cost_declaration.v1',
             policy=deepcopy(POLICY), sources=sources(),
             prior_plan_sha256='590e270d3766437712cdfbff588278287f1126bb442f0e8959c350e5f7b04235',
             prior_audit_sha256='17d5d12509fb4a535ed90fd2d6da273fdb9833a3cb11ea6e30d4641cddbd236b',
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
