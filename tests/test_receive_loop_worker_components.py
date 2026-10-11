import unittest
from unittest.mock import patch
from execution_truth.contracts import ContractError, verify_artifact_hash
from infra.stream import receive_loop_worker_components as components


class WorkerComponentTests(unittest.TestCase):
    def test_barriers(self):
        for kwargs in ({},{'execute':True,'operations':True},
                       {'execute':True,'operations':0},{'execute':True,'operations':5001}):
            with self.assertRaises(ContractError):components.run(**kwargs)

    def test_population_rotation_and_verification(self):
        report=components.run(execute=True,operations=2)
        verify_artifact_hash(report,'diagnostic_sha256','worker diagnostic')
        self.assertTrue(report['complete']);self.assertIsNone(report['error'])
        self.assertEqual(len(report['rows']),42)
        for round_index in range(3):
            rows=[r for r in report['rows'] if r['round']==round_index]
            self.assertEqual([r['lane'] for r in rows],
                             list(components.LANES[round_index:]+components.LANES[:round_index]))
        for row in report['rows']:
            self.assertEqual(row['completed_operations'],2)
            self.assertGreaterEqual(row['cpu_seconds'],0)
            if row['lane'].startswith('core_'):
                self.assertEqual(row['verified_steps'],2)
                self.assertEqual(len(row['verified_core_sha256']),64)
        for flag in ('cost_gate_evaluated','probe_cost_accepted','cohort_executed',
                     'public_rollout_authorized','orders_authorized'):
            self.assertIs(report[flag],False)

    def test_fault_retains_partial_no_retry(self):
        with patch.object(components,'prepare',side_effect=OSError('fault')) as prepare:
            report=components.run(execute=True,operations=2)
        self.assertFalse(report['complete']);self.assertEqual(prepare.call_count,1)
        self.assertEqual(report['rows'][-1]['lane'],'prepare_json')
        self.assertEqual(report['error']['completed_operations'],0)
        self.assertFalse(report['error']['replayed'])

    def test_verification_outside_operation_window(self):
        with patch.object(components.PackedCore,'finish',side_effect=ContractError('verify fault')):
            report=components.run(execute=True,operations=2)
        self.assertFalse(report['complete'])
        self.assertEqual(report['error']['phase'],'post_window_verification')
        self.assertEqual(report['error']['completed_operations'],2)
        self.assertIsNone(report['rows'][-1]['verified_steps'])
