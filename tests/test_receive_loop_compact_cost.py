import unittest
from unittest.mock import patch

from infra.stream import receive_loop_compact_cost as compare,receive_loop_cost as cost
from infra.stream.receive_loop_contract import declare,runtime_receipt
from tests.test_receive_adapter import AVAILABLE


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class CompactModelComparisonTests(unittest.TestCase):
    def test_tiny_alternating_model_same_clock_and_native_counts_not_acceptance(self):
        contract=declare('a'*64,runtime_receipt())
        with patch.object(cost,'POLICY',dict(cost.POLICY,reads=16)):
            out=compare.run(contract)
        self.assertEqual([(r['pair'],r['variant']) for r in out['cpu_cases']],
                         [(0,'reference'),(0,'compact'),(1,'compact'),(1,'reference'),(2,'reference'),(2,'compact')])
        for key in ('native_recv_calls','native_frame_callbacks','native_pause_calls','native_resume_calls',
                    'synthetic_clock_calls','read_summaries','flow_edges'):
            self.assertEqual(out['mechanics']['reference'][key],out['mechanics']['compact'][key])
        self.assertFalse(out['transport_semantics_proven']); self.assertFalse(out['full_recorder_overhead_measured'])
        self.assertFalse(out['cohort_replayed']); self.assertFalse(out['public_rollout_authorized'])
        self.assertTrue(out['model_only'])


if __name__=='__main__': unittest.main()
