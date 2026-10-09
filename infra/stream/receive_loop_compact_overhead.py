"""Offline compact-recorder overhead preregistration; no workers or launcher."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_contract as loop, receive_loop_overhead as reference
from infra.stream.receive_loop_compact_lane import integration_sources
from infra.stream.reader_comparison import load_corpus

RECORDER_COMMIT = '0d29b3dbb8ff4777c0fa52f16adb1775d9624311'
RECORDER_SOURCE_SHA256 = '0c52e1220ee41cac13aa9dd967fb37472af4187848fab75c805bab529850b1a2'
PRIOR_REFERENCE_PLAN_SHA256 = '39f4bfccec57910fec0adad1be3fdec16dd8a67d5f7d7f1abe04c7cd224739bb'
CORPUS_SHA256 = reference.CORPUS_SHA256
POLICY = deepcopy(reference.POLICY)
POLICY.update(schema_version='qcrl.receive_loop_compact_overhead_policy.v1',
              instrumented='CompactDiagnosticSocket_same_inherited_recv_queue_send_close')


def sources():
    repo = Path(__file__).resolve().parents[2]
    names = ('infra/stream/receive_loop_compact_overhead.py',
             'tests/test_receive_loop_compact_overhead.py',
             'docs/RECEIVE_LOOP_COMPACT_OVERHEAD.md')
    return dict(reference.sources(), **integration_sources(),
                **{name: file_hash(repo / name) for name in names})


def declare(corpus_path, contract):
    loop.validate_contract(contract)
    if load_corpus(corpus_path)['corpus_sha256'] != CORPUS_SHA256:
        raise ContractError('compact overhead requires the frozen original corpus')
    if contract['source_analysis_sha256'] != reference.ANALYSIS_SHA256:
        raise ContractError('compact overhead requires the original decomposition binding')
    frozen = integration_sources()
    if payload_hash(frozen) != RECORDER_SOURCE_SHA256:
        raise ContractError('compact recorder differs from committed source freeze')
    obj = {'schema_version': 'qcrl.receive_loop_compact_overhead_declaration.v1',
           'candidate_recorder_commit': RECORDER_COMMIT,
           'candidate_recorder_sources': frozen, 'candidate_recorder_source_sha256': RECORDER_SOURCE_SHA256,
           'prior_reference_plan_sha256': PRIOR_REFERENCE_PLAN_SHA256,
           'prior_reference_verdict': 'reject', 'policy': deepcopy(POLICY),
           'corpus_sha256': CORPUS_SHA256, 'loop_contract': deepcopy(contract), 'sources': sources(),
           'benchmark_performed': False, 'execution_authorized_by_declaration': False,
           'candidate_workers_implemented': False, 'candidate_launcher_implemented': False,
           'overhead_acceptance_established': False, 'public_rollout_authorized': False,
           'orders_authorized': False}
    obj['plan_sha256'] = payload_hash(obj)
    return obj


def validate(obj, corpus_path):
    verify_artifact_hash(obj, 'plan_sha256', 'compact overhead declaration')
    if obj != declare(corpus_path, obj.get('loop_contract')):
        raise ContractError('compact overhead differs from frozen source/policy/scope')
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', required=True, type=Path)
    parser.add_argument('--loop-contract', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    obj = declare(args.corpus, json.loads(args.loop_contract.read_text()))
    from execution_truth.rolling_stream import persist
    persist(args.output, obj)  # Exclusive and durable; existing declarations are never overwritten.
    print(json.dumps({'plan_sha256': obj['plan_sha256'], 'benchmark_performed': False,
                      'execution_authorized_by_declaration': False}))


if __name__ == '__main__': main()
