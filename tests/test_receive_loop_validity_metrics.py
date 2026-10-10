from copy import deepcopy
import unittest
from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity_metrics import evaluate


def cases():
    return [dict(round=r,lane=lane,metrics=dict(combined_cpu=1,combined_rss=100,
            tails={f'{cycle}:{rate}':dict(p99=0,worst=0) for cycle in range(6) for rate in ('500','3000')},failures=[],unknown=[]))
            for r in range(3) for lane in ('control','pacing','full')]


class MetricTests(unittest.TestCase):
    def test_passing_self_reports_never_accept_cost(self):
        r=evaluate(cases());self.assertEqual(r['metric_gate'],'pass');self.assertFalse(r['probe_cost_accepted'])

    def test_each_round_failures_not_rescued_by_other_pairs(self):
        for key,value in (('combined_cpu',1.051),('combined_rss',111)):
            c=cases();c[1]['metrics'][key]=value
            self.assertEqual(evaluate(c)['metric_gate'],'reject')

    def test_additive_tails_with_zero_baseline_and_missing_denominators(self):
        c=cases();c[1]['metrics']['tails']['0:500']['p99']=.00101
        self.assertEqual(evaluate(c)['metric_gate'],'reject')
        c[0]['metrics']['combined_cpu']=0
        r=evaluate(c);self.assertEqual(r['metric_gate'],'inconclusive');self.assertTrue(r['failures'])

    def test_fixture_unknown_and_known_failures_both_retained(self):
        c=cases();c[1]['metrics']['unknown']=['test_only_fixture'];c[1]['metrics']['failures']=['observer_skipped_ticks']
        r=evaluate(c);self.assertEqual(r['metric_gate'],'inconclusive');self.assertTrue(r['failures'])

    def test_invalid_population_and_negative_measurement(self):
        with self.assertRaises(ContractError):evaluate(cases()[:-1])
        c=cases();c[1]['metrics']['combined_cpu']=-1
        with self.assertRaises(ContractError):evaluate(c)
