from copy import deepcopy
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.receive_path import declare, validate_delivery, ReceivePathTracker
from execution_truth.receive_recovery import ReceiveRecoveryTracker, validate_recovery_connection
from tests.test_receive_path import DOMAIN, stamp
from tests.test_receive_adapter import AVAILABLE, local_server


def tracker():
    t=ReceiveRecoveryTracker(declare('a'*64,DOMAIN,stream_spec_sha256='b'*64,policy_version='v3'))
    t.begin_connection(1)
    return t


def fill(t, count=65, *, start=1, value=b'same'):
    for i in range(count):
        t.observe_frame(t.connection,1,True,value,stamp(start+i))


def deliver(t, message='same', at=100):
    r=t.deliver(t.connection,message,stamp(at))
    validate_delivery(r,t.contract,message)
    return r


class ReceiveRecoveryTests(unittest.TestCase):
    def test_explicit_tracker_and_no_collector_enablement(self):
        from execution_truth.market_stream import stream_plan
        from tests.test_taker_replay import raw_bundle
        with self.assertRaises(ContractError):
            ReceivePathTracker(declare('a'*64,DOMAIN,stream_spec_sha256='b'*64,policy_version='v3'))
        with self.assertRaises(ContractError):
            ReceiveRecoveryTracker(declare('a'*64,DOMAIN,stream_spec_sha256='b'*64))
        with self.assertRaises(ContractError):
            stream_plan(raw_bundle(),segmented=True,profiling=True,receive_path=True,
                        receive_policy='v3',source_plan_sha256='a'*64)

    def test_prefix_unknown_fence_then_duplicate_occurrence_recovery(self):
        t=tracker(); fill(t)
        self.assertEqual(len(t.pending),64)
        for i in range(64):
            r=deliver(t,at=100+i)
            self.assertEqual(r['receive_marker']['message_sequence'],i+1)
            self.assertEqual(r['alignment']['state'],'draining')
        r=deliver(t,at=164)
        self.assertIsNone(r['receive_marker'])
        self.assertEqual(r['unavailable_reason'],'pending_marker_budget')
        self.assertEqual(r['alignment']['generation'],1)
        self.assertEqual(r['alignment']['state'],'aligned')
        self.assertEqual(r['alignment']['recovery_fence']['delivered_messages'],65)
        t.observe_frame(1,1,True,b'same',stamp(165))
        r=deliver(t,at=166)
        self.assertEqual(r['receive_marker']['message_sequence'],66)
        self.assertEqual(r['last_observation_to_delivery']['upper_seconds'],1)

    def test_repeated_overflow_generations_bound_all_metadata(self):
        t=tracker(); records=[]
        for cycle in range(3):
            fill(t,100,start=cycle*1000+1)
            self.assertEqual(len(t.pending),64)
            for i in range(100):
                r=deliver(t,at=cycle*1000+200+i)
                records.append(r)
                self.assertEqual(r['telemetry_available'],i<64)
            self.assertEqual(r['alignment']['generation'],cycle+1)
            self.assertIsNone(t.fragment)
        self.assertEqual(t.message_sequence,t.delivered_messages)
        result=validate_recovery_connection(records,t.contract,['same']*300)
        self.assertEqual(result['recovery_generations'],3)
        self.assertEqual(result['known'],192)

    def test_trajectory_rejects_omitted_duplicate_and_forged_fence_records(self):
        t=tracker(); fill(t)
        records=[deliver(t,at=100+i) for i in range(65)]
        with self.assertRaises(ContractError): validate_recovery_connection(records[1:],t.contract,['same']*64)
        with self.assertRaises(ContractError): validate_recovery_connection(records+[records[-1]],t.contract,['same']*66)
        with self.assertRaises(ContractError): validate_recovery_connection(records,t.contract,['same']*64)
        forged=deepcopy(records)
        # A locally valid clock in a rehashed fence is still wrong for THIS
        # trajectory if it differs from the fence-closing delivery's stamp.
        forged[-1]['alignment']['recovery_fence']['observation']=stamp(163.5)
        forged[-1].pop('telemetry_sha256'); forged[-1]['telemetry_sha256']=payload_hash(forged[-1])
        validate_delivery(forged[-1],t.contract,'same')
        with self.assertRaises(ContractError): validate_recovery_connection(forged,t.contract,['same']*65)

    def test_partial_fragment_blocks_empty_counter_fence(self):
        t=tracker(); fill(t)
        t.observe_frame(1,1,False,b'\xe2',stamp(66))
        for i in range(65): r=deliver(t,at=100+i)
        self.assertEqual(r['alignment']['observed_messages'],r['alignment']['delivered_messages'])
        self.assertEqual(r['alignment']['state'],'draining')
        self.assertIsNone(r['alignment']['recovery_fence'])
        t.observe_frame(1,9,True,b'ping',stamp(165))
        t.observe_frame(1,0,True,b'\x82\xac',stamp(166))
        r=deliver(t,'€',at=167)
        self.assertFalse(r['telemetry_available'])
        self.assertEqual(r['alignment']['generation'],1)
        t.observe_frame(1,1,False,b'\xe2',stamp(168))
        t.observe_frame(1,9,True,b'ping',stamp(169))
        t.observe_frame(1,0,True,b'\x82\xac',stamp(170))
        r=deliver(t,'€',at=171)
        self.assertEqual(r['receive_marker']['fragment_count'],2)
        self.assertEqual(r['receive_marker']['last_frame_sequence']-r['receive_marker']['first_frame_sequence'],2)

    def test_future_complete_callbacks_prevent_premature_recovery(self):
        t=tracker(); fill(t)
        for i in range(64): deliver(t,at=100+i)
        fill(t,3,start=164)
        r=deliver(t,at=170)
        self.assertEqual(r['alignment']['state'],'draining')
        self.assertEqual(r['alignment']['observed_messages'],68)
        for at in (171,172,173): r=deliver(t,at=at)
        self.assertEqual(r['alignment']['generation'],1)
        self.assertFalse(r['telemetry_available'])

    def test_control_frames_do_not_consume_message_occurrences(self):
        t=tracker(); fill(t)
        t.observe_frame(1,10,True,b'',stamp(66))
        for i in range(65): r=deliver(t,at=100+i)
        self.assertEqual(r['alignment']['observed_messages'],65)
        self.assertEqual(r['alignment']['observed_frames'],66)
        self.assertEqual(r['alignment']['generation'],1)

    def test_callback_after_delivery_stamp_blocks_recovery(self):
        t=tracker(); fill(t)
        for i in range(64): deliver(t,at=100+i)
        # Models a control callback between external clock sampling and entry
        # into deliver's metadata lock. Counter equality alone is insufficient.
        t.observe_frame(1,9,True,b'ping',stamp(200))
        r=deliver(t,at=164)
        self.assertEqual(r['alignment']['state'],'draining')
        self.assertIsNone(r['alignment']['recovery_fence'])
        t.observe_frame(1,1,True,b'same',stamp(201))
        r=deliver(t,at=202)
        self.assertEqual(r['alignment']['generation'],1)

    def test_rehashed_malformed_common_fields_fail_with_contract_error(self):
        t=tracker(); t.observe_frame(1,1,True,b'same',stamp(1))
        r=deliver(t,at=2)
        for value in ({'receive_marker':{}},{'pending_marker_depth':'64'},
                      {'application_delivery':{}},{'receive_marker':'not a marker'}):
            forged={**deepcopy(r),**value}; forged.pop('telemetry_sha256')
            forged['telemetry_sha256']=payload_hash(forged)
            with self.assertRaises(ContractError): validate_delivery(forged,t.contract,'same')

    def test_digest_mismatch_is_terminal_not_hash_search_or_recovery(self):
        t=tracker(); fill(t)
        r=deliver(t,'different',at=100)
        self.assertEqual(r['alignment']['state'],'terminal')
        self.assertEqual(r['unavailable_reason'],'fifo_message_mismatch')
        for i in range(64): deliver(t,at=101+i)
        self.assertEqual(t.generation,0)
        self.assertFalse(t.observe_frame(1,1,True,b'same',stamp(200)))

    def test_reconnect_resets_counters_and_rejects_retired_callbacks(self):
        t=tracker(); fill(t)
        for i in range(64): deliver(t,at=100+i)
        reset=t.begin_connection(2)
        self.assertEqual(reset['discarded_unknown_backlog'],1)
        with self.assertRaises(ContractError): t.observe_frame(1,1,True,b'same',stamp(200))
        t.observe_frame(2,1,True,b'new',stamp(201))
        r=deliver(t,'new',at=202)
        self.assertEqual(r['receive_marker']['message_sequence'],1)
        self.assertEqual(r['alignment']['generation'],0)

    def test_skipped_frame_protocol_byte_and_fragment_errors_are_terminal(self):
        for frames in (((0,True,b'x'),),((1,False,b'x'),(1,True,b'x')),
                       ((9,False,b'x'),),((1,True,b'x'*262145),)):
            t=tracker(); fill(t)
            for i,(opcode,final,data) in enumerate(frames):
                t.observe_frame(1,opcode,final,data,stamp(66+i))
            self.assertNotEqual(t.disabled_reason,'pending_marker_budget')
            self.assertIsNotNone(t.disabled_reason)
            for i in range(65): r=deliver(t,at=100+i)
            self.assertEqual(r['alignment']['state'],'terminal')

    def test_invalid_clock_and_counter_budget_never_rearm(self):
        t=tracker(); fill(t)
        t.observe_frame(1,1,True,b'x',stamp(1))
        self.assertEqual(t.disabled_reason,'receiver_monotonic_regression')
        t=tracker(); fill(t)
        bad=stamp(66); bad['monotonic_after']=65
        with self.assertRaises(ContractError): t.observe_frame(1,1,True,b'x',bad)
        self.assertEqual(t.disabled_reason,'invalid_receiver_clock')
        t=tracker(); t.policy['max_observed_messages']=1
        fill(t,2)
        self.assertEqual(t.disabled_reason,'occurrence_counter_budget')

    def test_rehashed_forged_fence_and_marker_are_rejected(self):
        t=tracker(); fill(t)
        for i in range(65): r=deliver(t,at=100+i)
        mutations=[lambda a:a['alignment']['recovery_fence'].update(incomplete_fragment=True),
                   lambda a:a['alignment']['recovery_fence'].update(delivered_messages=64),
                   lambda a:a['alignment'].update(generation=0),
                   lambda a:a['alignment'].update(overflow=None),
                   lambda a:a['alignment'].update(observed_messages=66)]
        for mutate in mutations:
            forged=deepcopy(r); mutate(forged); forged.pop('telemetry_sha256')
            forged['telemetry_sha256']=payload_hash(forged)
            with self.assertRaises(ContractError): validate_delivery(forged,t.contract,'same')
        t.observe_frame(1,1,True,b'same',stamp(165))
        r=deliver(t,at=166)
        r['receive_marker']['message_sequence']=65; r.pop('telemetry_sha256')
        r['telemetry_sha256']=payload_hash(r)
        with self.assertRaises(ContractError): validate_delivery(r,t.contract,'same')

    def test_recovered_marker_cannot_reuse_fence_frame_identity(self):
        t=tracker(); fill(t)
        for i in range(65): deliver(t,at=100+i)
        t.observe_frame(1,1,True,b'same',stamp(165))
        r=deliver(t,at=166)
        fence_frame=r['alignment']['recovery_fence']['observed_frames']
        r['receive_marker']['first_frame_sequence']=fence_frame
        r['receive_marker']['last_frame_sequence']=fence_frame
        r.pop('telemetry_sha256'); r['telemetry_sha256']=payload_hash(r)
        with self.assertRaises(ContractError): validate_delivery(r,t.contract,'same')

    def test_delivery_ahead_and_adapter_failure_are_terminal(self):
        t=tracker(); r=deliver(t,at=1)
        self.assertEqual(r['unavailable_reason'],'delivery_occurrence_ahead_of_observation')
        t=tracker(); fill(t)
        t._disable('receiver_observation_error')
        for i in range(65): r=deliver(t,at=100+i)
        self.assertEqual(r['alignment']['state'],'terminal')
        self.assertEqual(r['alignment']['generation'],0)

    @unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
    def test_real_adapter_overflow_duplicate_batch_then_fragment_recovery(self):
        import time
        from websockets.frames import Frame, OP_TEXT
        from execution_truth.receive_adapter import ObservedSocket
        def handler(conn):
            self.assertEqual(conn.recv(timeout=3),'go')
            # Valid concatenated text frames in one send create a callback batch
            # exceeding 64 without changing the client's queue/flow control.
            conn.socket.sendall(b''.join(Frame(OP_TEXT,b'x').serialize(mask=False) for _ in range(500)))
            self.assertEqual(conn.recv(timeout=5),'next')
            conn.send(['€','-after'],text=True)
            self.assertEqual(conn.recv(timeout=3),'done')
        t=ReceiveRecoveryTracker(declare('a'*64,'loopback:recovery',stream_spec_sha256='b'*64,policy_version='v3'))
        with local_server(handler) as uri:
            client=ObservedSocket(uri,t,1)
            try:
                client.send('go')
                deadline=time.monotonic()+3
                while time.monotonic()<deadline:
                    with t.lock: exhausted=t.disabled_reason=='pending_marker_budget'
                    if exhausted: break
                    time.sleep(.005)
                self.assertTrue(exhausted)
                unknown=0; records=[]; raws=[]
                for _ in range(500):
                    raw,record=client.recv(3)
                    self.assertEqual(raw,'x')
                    validate_delivery(record,t.contract,raw)
                    records.append(record); raws.append(raw)
                    unknown+=not record['telemetry_available']
                self.assertGreater(unknown,0)
                self.assertGreaterEqual(t.generation,1)
                self.assertIsNone(t.disabled_reason)
                self.assertEqual(t.message_sequence,t.delivered_messages)
                client.send('next')
                raw,record=client.recv(3)
                self.assertEqual(raw,'€-after')
                validate_delivery(record,t.contract,raw)
                records.append(record); raws.append(raw)
                result=validate_recovery_connection(records,t.contract,raws)
                self.assertEqual(result['deliveries'],501)
                self.assertEqual(record['receive_marker']['message_sequence'],501)
                self.assertGreaterEqual(record['receive_marker']['fragment_count'],2)
                client.send('done')
            finally:
                client.close()
