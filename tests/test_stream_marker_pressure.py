from copy import deepcopy
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from execution_truth.stream_marker_pressure import PressureScan, POLICY
from tests.test_receive_recovery import tracker, fill
from tests.test_receive_path import stamp


class MarkerPressureTests(unittest.TestCase):
    def test_exact_overflow_unknown_fence_and_recovery(self):
        t = tracker(); scan = PressureScan(t.contract)
        fill(t, 100)
        for i in range(100):
            r = t.deliver(1, 'same', stamp(200+i), library_queue_depth=99-i,
                          library_backpressure_active=True)
            scan.consume(r, 'same')
        t.observe_frame(1, 1, True, b'same', stamp(301))
        scan.consume(t.deliver(1, 'same', stamp(302)), 'same')
        result = scan.summary(); e = result['episodes'][0]
        self.assertEqual(result['counts']['known'], 65)
        self.assertEqual(result['counts']['unknown'], 36)
        self.assertEqual(e['retained_prefix_deliveries'], 64)
        self.assertEqual(e['unknown_deliveries'], 36)
        self.assertEqual(e['unknown_library_depth_above_marker_limit'], 0)
        self.assertEqual(e['fence']['delivered_messages'], 100)
        self.assertEqual(e['first_known_after_fence'], 101)
        self.assertEqual(result['maxima']['observed_message_increment'], 100)
        self.assertEqual(result['closed_episodes'], 1)

    def test_partial_tail_remains_open(self):
        t = tracker(); fill(t, 100); scan = PressureScan(t.contract)
        for i in range(70): scan.consume(t.deliver(1, 'same', stamp(200+i)), 'same')
        s = scan.summary()
        self.assertEqual(s['open_episodes'], 1)
        self.assertEqual(s['episodes'][0]['unknown_library_depth_missing'], 6)

    def test_tampering_and_missing_occurrence_rejected(self):
        t = tracker(); fill(t, 2)
        records = [t.deliver(1, 'same', stamp(100+i)) for i in range(2)]
        with self.assertRaises(ContractError): PressureScan(t.contract).consume(records[1], 'same')
        bad = deepcopy(records[0]); bad['library_queue_depth'] = 999
        with self.assertRaises(ContractError): PressureScan(t.contract).consume(bad, 'same')
        with self.assertRaises(ContractError): PressureScan(t.contract).consume(records[0], 'other')

    def test_multiple_episodes_and_fragment_visibility(self):
        t = tracker(); scan = PressureScan(t.contract)
        for cycle in range(2):
            fill(t, 65, start=cycle*1000+1)
            for i in range(65): scan.consume(t.deliver(1, 'same', stamp(cycle*1000+200+i)), 'same')
        t.observe_frame(1, 1, False, b'sa', stamp(2001))
        t.observe_frame(1, 0, True, b'me', stamp(2002))
        scan.consume(t.deliver(1, 'same', stamp(2003)), 'same')
        self.assertEqual(scan.summary()['closed_episodes'], 2)
        self.assertEqual(scan.summary()['episodes'][0]['first_known_after_fence'], 66)
        self.assertEqual(scan.summary()['counts']['known_fragmented'], 1)

    def test_limits_fail_closed(self):
        t = tracker(); fill(t, 65); scan = PressureScan(t.contract)
        r = t.deliver(1, 'same', stamp(100))
        with patch.dict(POLICY, max_episodes=0):
            with self.assertRaises(ContractError): scan.consume(r, 'same')
        with patch.dict(POLICY, max_deliveries=0):
            with self.assertRaises(ContractError): PressureScan(t.contract).consume(r, 'same')


if __name__ == '__main__': unittest.main()
