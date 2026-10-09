from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import receive_loop_compact_overhead as candidate, receive_loop_overhead as reference
from infra.stream import receive_loop_contract as loop
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE


@unittest.skipUnless(AVAILABLE, 'pinned optional WebSocket library required')
class CompactOverheadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'corpus.json'
        data = corpus(); self.path.write_text(json.dumps(data))
        self.contract = loop.declare(reference.ANALYSIS_SHA256, loop.runtime_receipt())
        selected = patch.object(candidate, 'CORPUS_SHA256', data['corpus_sha256'])
        selected.start(); self.addCleanup(selected.stop)

    def obj(self): return candidate.declare(self.path, self.contract)

    def test_exact_policy_parity_except_candidate_identity(self):
        obj = self.obj(); candidate.validate(obj, self.path)
        policy = deepcopy(obj['policy'])
        policy['schema_version'] = reference.POLICY['schema_version']
        policy['instrumented'] = reference.POLICY['instrumented']
        self.assertEqual(policy, reference.POLICY)
        self.assertEqual(obj['prior_reference_verdict'], 'reject')
        self.assertEqual(obj['policy']['messages_per_case'], 30000)
        self.assertEqual(obj['policy']['cases'], 6)
        for key in ('benchmark_performed', 'execution_authorized_by_declaration',
                    'candidate_workers_implemented', 'candidate_launcher_implemented',
                    'overhead_acceptance_established', 'public_rollout_authorized', 'orders_authorized'):
            self.assertIs(obj[key], False)

    def test_freeze_inventory_and_changed_live_source_fail_closed(self):
        obj = self.obj()
        self.assertEqual(payload_hash(obj['candidate_recorder_sources']), candidate.RECORDER_SOURCE_SHA256)
        self.assertEqual(len(obj['candidate_recorder_sources']), 47)
        for name in ('infra/stream/receive_loop_compact_lane.py', 'infra/stream/receive_loop_compact_transport.py',
                     'infra/stream/receive_loop_compact.py', 'execution_truth/receive_recovery.py'):
            self.assertIn(name, obj['sources'])
        with patch.object(candidate, 'integration_sources', return_value={}):
            with self.assertRaises(ContractError): self.obj()

    def test_rehashed_policy_identity_authority_and_source_changes_rejected(self):
        mutations = [lambda o: o['policy']['acceptance'].update(each_pair_cpu_ratio_max=1.2),
            lambda o: o['policy'].update(consumer_cpu_quota_percent=100),
            lambda o: o['policy']['pair_order'][0].reverse(),
            lambda o: o.update(candidate_recorder_commit='f' * 40),
            lambda o: o.update(prior_reference_verdict='pass'),
            lambda o: o.update(candidate_workers_implemented=True),
            lambda o: o.update(candidate_launcher_implemented=True),
            lambda o: o.update(execution_authorized_by_declaration=True),
            lambda o: o.update(overhead_acceptance_established=True),
            lambda o: o.update(extra='no'),
            lambda o: o['sources'].update({'infra/stream/receive_loop_compact_overhead.py': 'f' * 64})]
        for change in mutations:
            obj = self.obj(); change(obj); obj.pop('plan_sha256'); obj['plan_sha256'] = payload_hash(obj)
            with self.assertRaises(ContractError): candidate.validate(obj, self.path)

    def test_wrong_corpus_analysis_and_native_contract_rejected(self):
        with patch.object(candidate, 'CORPUS_SHA256', 'f' * 64):
            with self.assertRaises(ContractError): self.obj()
        with self.assertRaises(ContractError):
            candidate.declare(self.path, loop.declare('a' * 64, loop.runtime_receipt()))
        wrong = deepcopy(self.contract); wrong['policy']['max_read_summaries'] *= 2
        wrong.pop('contract_sha256'); wrong['contract_sha256'] = payload_hash(wrong)
        with self.assertRaises(ContractError): candidate.declare(self.path, wrong)

    def test_deep_copy_and_old_validator_do_not_adopt_candidate(self):
        obj = self.obj(); obj['policy']['pair_order'][0].reverse(); obj['loop_contract']['runtime_receipt']['methods'].clear()
        self.assertEqual(candidate.POLICY['pair_order'][0], ['baseline', 'instrumented'])
        self.assertEqual(len(self.contract['runtime_receipt']['methods']), 13)
        with self.assertRaises(ContractError): reference.validate(self.obj(), self.path)

    def test_cli_exclusive_offline_output_and_no_claims(self):
        contract = Path(self.tmp.name) / 'contract.json'; contract.write_text(json.dumps(self.contract))
        output = Path(self.tmp.name) / 'preregistration.json'
        args = ['declaration', '--corpus', str(self.path), '--loop-contract', str(contract), '--output', str(output)]
        with patch.object(sys, 'argv', args):
            candidate.main(); before = output.read_bytes()
            with self.assertRaises(FileExistsError): candidate.main()
        self.assertEqual(before, output.read_bytes())
        candidate.validate(json.loads(before), self.path)
