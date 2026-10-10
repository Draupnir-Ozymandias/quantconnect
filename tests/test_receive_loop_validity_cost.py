from copy import deepcopy
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import receive_loop_validity_cost as cost


class CostDeclarationTests(unittest.TestCase):
    def test_deterministic_source_bound_and_no_execution(self):
        obj = cost.declare()
        self.assertEqual(obj, cost.declare())
        self.assertIs(cost.validate(obj), obj)
        for field in ('workers_implemented', 'launcher_implemented', 'benchmark_performed',
                      'execution_authorized', 'probe_cost_accepted', 'public_rollout_authorized', 'orders_authorized'):
            self.assertIs(obj[field], False)
        self.assertEqual(len(obj['sources']), 11)

    def test_nine_cases_fixed_schedule_and_resource_limits(self):
        p = cost.declare()['policy']
        self.assertEqual(sum(s['seconds']*s['rate'] for s in p['phases'])*p['cycles'], 30000)
        self.assertEqual(sum(len(r) for r in p['order']), 9)
        for row in p['order']: self.assertEqual(set(row), {'control', 'pacing', 'full'})
        self.assertEqual(p['workers']['cpu_quota_percent'], 100)
        self.assertEqual(p['observers']['cpu_quota_percent'], 25)
        self.assertEqual(p['observer_capacity'], 512)

    def test_policy_and_authority_tampering_even_when_rehashed(self):
        for change in ('quota', 'authority', 'scope'):
            obj = deepcopy(cost.declare())
            if change == 'quota': obj['policy']['workers']['cpu_quota_percent'] = 200
            elif change == 'authority': obj['execution_authorized'] = True
            else: obj['policy']['scope'] = 'public_recorder'
            obj.pop('plan_sha256'); obj['plan_sha256'] = payload_hash(obj)
            with self.subTest(change=change), self.assertRaises(ContractError): cost.validate(obj)

    def test_source_drift_and_bad_hash_refused(self):
        obj = cost.declare()
        with patch.object(cost, 'sources', return_value={}):
            with self.assertRaises(ContractError): cost.validate(obj)
        obj['plan_sha256'] = '0'*64
        with self.assertRaises(ContractError): cost.validate(obj)

    def test_policy_is_not_shared_mutable_declaration_state(self):
        obj = cost.declare(); obj['policy']['order'][0].clear()
        self.assertEqual(len(cost.declare()['policy']['order'][0]), 3)


if __name__ == '__main__': unittest.main()
