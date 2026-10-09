from datetime import datetime,timezone
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from execution_truth.receive_path import sample_clock,elapsed_bounds,POLICY
from infra.stream import receive_loop_cost as cost, receive_loop_contract as loop
from tests.test_receive_adapter import AVAILABLE


class ClockBracketCostTests(unittest.TestCase):
    def sample(self,before,after):
        return sample_clock(lambda:datetime(2026,10,9,tzinfo=timezone.utc),iter([before,after]).__next__,'cost.fixture')

    def test_receiver_or_delivery_sampling_delay_remains_ineligible(self):
        for first,last in ((self.sample(1,1.002),self.sample(2,2.0001)),
                           (self.sample(1,1.0001),self.sample(2,2.002))):
            value=elapsed_bounds(first,last,'cost.fixture')
            self.assertFalse(value['timing_eligible']); self.assertIn('wide_clock_bracket',value['warnings'])
            self.assertGreaterEqual(value['lower_seconds'],0)
        self.assertEqual(POLICY['max_clock_bracket_seconds'],.001)

    def test_narrow_samples_eligible_overlap_separate_and_bad_clock_rejected(self):
        self.assertTrue(elapsed_bounds(self.sample(1,1.0001),self.sample(2,2.0001),'cost.fixture')['timing_eligible'])
        value=elapsed_bounds(self.sample(1,1.0005),self.sample(1.0002,1.0007),'cost.fixture')
        self.assertFalse(value['timing_eligible']); self.assertIn('overlapping_clock_brackets',value['warnings'])
        with self.assertRaises(ContractError): self.sample(2,1)


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class ObserverCallCostTests(unittest.TestCase):
    def test_same_native_counts_and_exact_clock_population(self):
        contract=loop.declare('a'*64,loop.runtime_receipt())
        policy=dict(cost.POLICY,reads=32)
        with patch.object(cost,'POLICY',policy):
            for mode in policy['mode_order']:
                clock=cost.StepClock(); state=cost.prepare(mode,contract,clock); cost.workload(state)
                counts=cost.check(state,contract)
                self.assertEqual(counts['native_recv_calls'],32)
                self.assertEqual(counts['native_frame_callbacks'],64)
                self.assertEqual(counts['native_pause_calls'],2)
                self.assertEqual(clock.calls,0 if mode=='native_only' else 32*8+2*4)

    def test_tiny_separate_profiling_and_allocation_passes_never_claim_acceptance(self):
        contract=loop.declare('a'*64,loop.runtime_receipt())
        with patch.object(cost,'POLICY',dict(cost.POLICY,reads=16,cpu_repetitions=1)):
            result=cost.run(contract)
        self.assertFalse(result['full_recorder_overhead_measured'])
        self.assertFalse(result['transport_semantics_proven'])
        self.assertFalse(result['cohort_replayed'])
        self.assertEqual(len(result['results']),3)
        self.assertTrue(all(r['profile_top_cumulative'] for r in result['results']))
        self.assertTrue(all(r['traced_peak_bytes']>=r['traced_retained_bytes'] for r in result['results']))

    def test_unknown_mode_and_native_call_size_rejected(self):
        contract=loop.declare('a'*64,loop.runtime_receipt())
        with self.assertRaises(ContractError): cost.prepare('public',contract)
        with self.assertRaises(ContractError): cost.NativeSocket().recv(1024)


if __name__=='__main__': unittest.main()
