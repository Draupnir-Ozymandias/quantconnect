import unittest
from unittest.mock import patch
from execution_truth.contracts import ContractError
from infra.stream import receive_loop_probe_components as components


class ComponentTests(unittest.TestCase):
    def test_barriers(self):
        for kwargs in ({},{'execute':True,'operations':True},
                       {'execute':True,'operations':0},{'execute':True,'operations':1001}):
            with self.assertRaises(ContractError):components.run(**kwargs)

    def test_population_rotations_and_no_acceptance(self):
        r=components.run(execute=True,operations=3)
        self.assertEqual(len(r['rows']),21)
        for i in range(3):
            self.assertEqual([x['lane'] for x in r['rows'] if x['round']==i],
                             list(components.LANES[i:]+components.LANES[:i]))
        self.assertTrue(r['fixture_io']);self.assertFalse(r['native_linux_io_measured'])
        self.assertFalse(r['probe_cost_accepted']);self.assertFalse(r['cohort_executed'])
        self.assertTrue(all(x['operations']==3 and x['cpu_seconds']>=0 for x in r['rows']))

    def test_fault_is_not_retried(self):
        error=OSError('fixture fault')
        with patch.object(components,'parse_cpu_stat',side_effect=error) as f:
            with self.assertRaises(OSError) as caught:components.run(execute=True,operations=3)
        self.assertIs(caught.exception,error);self.assertEqual(f.call_count,1)
