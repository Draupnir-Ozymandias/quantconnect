from copy import deepcopy
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import receive_loop_contract as loop, receive_loop_overhead as overhead
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE


@unittest.skipUnless(AVAILABLE, 'pinned optional WebSocket library required')
class ReceiveLoopOverheadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'corpus.json'
        data = corpus(); self.path.write_text(json.dumps(data))
        self.contract = loop.declare(overhead.ANALYSIS_SHA256, loop.runtime_receipt())
        self.corpus_patch = patch.object(overhead, 'CORPUS_SHA256', data['corpus_sha256'])
        self.corpus_patch.start(); self.addCleanup(self.corpus_patch.stop)

    def test_roundtrip_fixed_population_and_no_execution_authority(self):
        obj = overhead.declare(self.path, self.contract)
        overhead.validate(obj, self.path)
        policy = obj['policy']
        self.assertEqual(policy['cases'], 6)
        self.assertEqual(sum(p['seconds']*p['rate'] for p in policy['phases'])*policy['cycles'], 30000)
        self.assertEqual(policy['pair_order'][1], ['instrumented', 'baseline'])
        for key in ('benchmark_performed', 'execution_authorized_by_declaration',
                    'public_rollout_authorized', 'orders_authorized'):
            self.assertIs(obj[key], False)

    def test_rehashed_policy_changes_and_extra_fields_rejected(self):
        for mutate in (lambda o: o['policy']['acceptance'].update(each_pair_cpu_ratio_max=2),
                       lambda o: o['policy'].update(marker_cap=256),
                       lambda o: o.update(execution_authorized_by_declaration=True),
                       lambda o: o.update(extra='payload')):
            obj = overhead.declare(self.path, self.contract); mutate(obj)
            obj.pop('plan_sha256'); obj['plan_sha256'] = payload_hash(obj)
            with self.assertRaises(ContractError): overhead.validate(obj, self.path)

    def test_source_inventory_complete_and_rehashed_mutation_rejected(self):
        obj = overhead.declare(self.path, self.contract)
        self.assertIn('execution_truth/market_stream.py', obj['sources'])
        self.assertIn('infra/stream/receive_loop_lane.py', obj['sources'])
        self.assertIn('docs/RECEIVE_LOOP_OVERHEAD.md', obj['sources'])
        for key in ('execution_truth/market_stream.py', 'infra/stream/receive_loop_probe.py'):
            altered = deepcopy(obj); altered['sources'][key] = 'b'*64
            altered.pop('plan_sha256'); altered['plan_sha256'] = payload_hash(altered)
            with self.assertRaises(ContractError): overhead.validate(altered, self.path)
        with patch.object(overhead, 'sources', return_value={}):
            with self.assertRaises(ContractError): overhead.validate(obj, self.path)

    def test_wrong_corpus_or_analysis_binding_rejected(self):
        with patch.object(overhead, 'CORPUS_SHA256', 'f'*64):
            with self.assertRaises(ContractError): overhead.declare(self.path, self.contract)
        wrong = loop.declare('a'*64, loop.runtime_receipt())
        with self.assertRaises(ContractError): overhead.declare(self.path, wrong)

    def test_native_contract_tamper_rejected(self):
        wrong = deepcopy(self.contract); wrong['policy']['max_read_summaries'] *= 2
        wrong.pop('contract_sha256'); wrong['contract_sha256'] = payload_hash(wrong)
        with self.assertRaises(ContractError): overhead.declare(self.path, wrong)

    def test_deep_copy_protects_policy_and_contract(self):
        obj = overhead.declare(self.path, self.contract)
        obj['policy']['pair_order'][0].reverse()
        obj['loop_contract']['runtime_receipt']['methods'].clear()
        self.assertEqual(overhead.POLICY['pair_order'][0], ['baseline', 'instrumented'])
        self.assertEqual(len(self.contract['runtime_receipt']['methods']), 13)

    def test_cli_exclusive_output_no_execution(self):
        contract_path = Path(self.tmp.name)/'contract.json'
        contract_path.write_text(json.dumps(self.contract))
        output = Path(self.tmp.name)/'declaration.json'
        args = ['declaration', '--corpus', str(self.path), '--loop-contract',
                str(contract_path), '--output', str(output)]
        with patch.object(sys, 'argv', args):
            overhead.main()
            before = output.read_bytes()
            with self.assertRaises(FileExistsError): overhead.main()
        self.assertEqual(before, output.read_bytes())
        overhead.validate(json.loads(before), self.path)


if __name__ == '__main__': unittest.main()
