from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_validity_packed import PackedCore, verify_prototype
from infra.stream.receive_loop_validity_worker import WorkloadCore, verify_core


class PackedTests(unittest.TestCase):
    def make(self, lane='full', n=3, cls=PackedCore):
        return cls(lane, n, execute=True,
                   monotonic=Mock(side_effect=[i/1000 for i in range(200)]),
                   sleep=Mock(), cpu=Mock(side_effect=[i/100000 for i in range(100)]))

    def test_same_clock_trace_same_canonical_evidence_all_lanes(self):
        for lane in ('control', 'pacing', 'full'):
            old, new = self.make(lane, cls=WorkloadCore), self.make(lane)
            for i in range(3):
                old.step(.1+i/10); new.step(.1+i/10)
            original, packed = old.finish(), new.finish()
            self.assertEqual(original, packed['core'])
            self.assertEqual(verify_core(packed['core'])['verified_occurrences'], 3)
            self.assertEqual(verify_prototype(packed)['verified_occurrences'], 3)
            self.assertFalse(packed['cost_verified'])
            self.assertFalse(packed['execution_authorized'])

    def test_call_counts_and_sleep_requests(self):
        for lane, walls in (('control', 4), ('pacing', 7), ('full', 11)):
            core = self.make(lane)
            for i in range(3): core.step(.1+i/10)
            self.assertEqual(core.clock.call_count, 1+3*walls)
            self.assertEqual(core.cpu.call_count, 6 if lane == 'full' else 0)
            self.assertEqual(core.sleep.call_count, 3)

    def test_packed_storage_has_fixed_population_and_no_row_objects(self):
        core = self.make()
        for i in range(3): core.step(.1+i/10)
        self.assertEqual(len(core.columns), 14)
        self.assertTrue(all(len(v)==3 and v.typecode=='d' for v in core.columns.values()))
        self.assertFalse(hasattr(core, 'rows'))
        self.assertFalse(hasattr(core, 'cpus'))

    def test_bounds_and_execution_barrier(self):
        with self.assertRaises(ContractError): PackedCore('full')
        for lane, n in (('bad', 1), ('full', 0), ('full', 30001), ('full', True)):
            with self.assertRaises(ContractError): self.make(lane, n)

    def test_overflow_before_more_native_calls_and_no_replay(self):
        core = self.make(n=1); core.step(.1); calls = core.clock.call_count
        with self.assertRaises(ContractError): core.step(.2)
        self.assertEqual(core.clock.call_count, calls)
        self.assertFalse(core.finish()['core']['complete'])
        with self.assertRaises(ContractError): core.finish()

    def test_prepare_fault_preserves_prefix_and_exception(self):
        core = self.make();core.step(.1);error = OSError('prepare')
        with patch('infra.stream.receive_loop_validity_packed.prepare', side_effect=error):
            with self.assertRaises(OSError) as caught: core.step(.2)
        self.assertIs(caught.exception, error)
        self.assertEqual(core.finish()['core']['delivered_occurrences'], 1)
        with self.assertRaises(ContractError): core.step(.3)

    def test_post_send_cpu_fault_retains_delivery_not_completed_row(self):
        core = self.make();core.cpu.side_effect = [.1, RuntimeError('cpu')]
        with self.assertRaises(RuntimeError): core.step(.1)
        r = core.finish()['core']
        self.assertEqual((r['delivered_occurrences'], r['completed_steps']), (1, 0))
        self.assertEqual(len(r['raws']), 1)
        with self.assertRaises(ContractError): verify_core(r)

    def test_sleep_fault_does_not_send(self):
        core = self.make();error=OSError('sleep');core.sleep.side_effect=error
        with self.assertRaises(OSError) as caught: core.step(.1)
        self.assertIs(caught.exception,error)
        self.assertEqual(core.delivered,0)

    def test_clock_regression_and_nonfinite_deadline_fail_closed(self):
        for bad in (float('nan'), float('inf'), True):
            core=self.make()
            with self.assertRaises(ContractError):core.step(bad)
            self.assertEqual(core.delivered,0)
        core=self.make();core.clock.side_effect=[-1]
        with self.assertRaises(ContractError):core.step(.1)
        self.assertFalse(core.finish()['core']['complete'])

    def test_thread_change_and_cpu_reset(self):
        core=self.make();core.identity=Mock(return_value=core.owner+1)
        with self.assertRaises(ContractError):core.step(.1)
        self.assertEqual(core.delivered,0)
        core=self.make();core.cpu.side_effect=[.2,.1]
        with self.assertRaises(ContractError):core.step(.1)
        self.assertEqual(core.delivered,1)
        self.assertFalse(core.finish()['core']['complete'])

    def test_rehashed_tampering_still_rejected(self):
        core=self.make(n=1);core.step(.1);r=deepcopy(core.finish()['core'])
        r['cpu_pairs'][0][1]['thread_cpu']=-1
        r.pop('report_sha256');r['report_sha256']=payload_hash(r)
        with self.assertRaises(ContractError):verify_core(r)

    def test_partial_is_not_protocol_evidence(self):
        core=self.make();core.step(.1);r=core.finish()
        self.assertFalse(r['core']['complete'])
        with self.assertRaises(ContractError):verify_core(r['core'])

    def test_wrapper_rehashed_authority_claim_rejected(self):
        core=self.make(n=1);core.step(.1);r=core.finish()
        r['cost_verified']=True;r.pop('prototype_sha256')
        r['prototype_sha256']=payload_hash(r)
        with self.assertRaises(ContractError):verify_prototype(r)


if __name__ == '__main__': unittest.main()
