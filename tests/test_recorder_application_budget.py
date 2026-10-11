import copy
import unittest

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.recorder_application_budget import POLICY, corpus, declare, validate
from execution_truth.market_stream import classify_frame
from infra.stream.recorder_completion import POLICY as COMPLETION_POLICY


class DeclarationTests(unittest.TestCase):
    def test_source_bound_roundtrip(self):
        obj = declare()
        self.assertEqual(validate(obj), obj)
        self.assertEqual(obj['corpus_sha256'], payload_hash(corpus()))
        self.assertFalse(obj['execution_authorized'])
        self.assertFalse(obj['acceptance_evaluator_implemented'])

    def test_exact_population_and_complete_cpu_windows(self):
        self.assertEqual(len(POLICY['case_order']), 6)
        for phases in POLICY['workloads'].values():
            count = sum(p['seconds'] * p['rate'] for p in phases)
            self.assertEqual(count, 60000)
            self.assertLessEqual(count, COMPLETION_POLICY['max_frames'])
            self.assertGreaterEqual(sum(p['seconds'] for p in phases), 60)
        self.assertEqual(POLICY['total_occurrences'], 6 * 60000)

    def test_rehashed_mutations_refused(self):
        for key, value in [('execution_authorized', True), ('budgets', {}),
                           ('corpus_sha256', '0' * 64), ('sources', {})]:
            obj = copy.deepcopy(declare())
            obj[key] = value
            obj.pop('plan_sha256')
            obj['plan_sha256'] = payload_hash(obj)
            with self.assertRaises(ContractError):
                validate(obj)

    def test_detached_declaration_and_duplicate_corpus(self):
        obj = declare()
        obj['policy']['unit']['cpu_quota_percent'] = 100
        self.assertEqual(declare()['policy']['unit']['cpu_quota_percent'], 75)
        self.assertEqual(corpus()['cycle'].count('PONG'), 2)
        self.assertEqual(len(corpus()['initial']), 2)
        spec = {'condition_id': POLICY['synthetic_condition_id'], 'asset_ids': ['10001', '10002']}
        for frame in corpus()['initial']:
            self.assertEqual(classify_frame(frame, spec)[0]['scope'], 'selected_market')


if __name__ == '__main__':
    unittest.main()
