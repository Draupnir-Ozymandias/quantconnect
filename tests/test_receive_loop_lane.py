from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import time
import unittest

from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import stream_plan
from execution_truth.receive_adapter import ObservedSocket
from infra.stream import marker_cap_pair as cap, receive_loop_lane as lane
from infra.stream.receive_loop_contract import declare, runtime_receipt
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE, local_server


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class ReceiveLoopLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract=declare('a'*64,runtime_receipt())

    def fixture(self, root, fail=False):
        from websockets.exceptions import ConnectionClosed
        c=corpus()
        with cap.scope('cap128'):
            spec=stream_plan(c['bundle'],max_seconds=15,max_frames=5,segmented=True,profiling=True,
                resilient=True,receive_path=True,freshness_telemetry=True,receive_policy='v3',source_plan_sha256='b'*64)
        base=_time(spec['event_start_at_utc']); origin=time.monotonic()
        def clock(): return base+timedelta(seconds=time.monotonic()-origin)
        raw=c['book_template']; cut=len(raw)//2
        messages=[raw,raw,[raw[:cut],raw[cut:]],c['price_templates'][0],'PONG']
        def handler(conn):
            self.assertEqual(json.loads(conn.recv(timeout=3))['type'],'market')
            for message in messages: conn.send(message)
            try: conn.recv(timeout=3)
            except ConnectionClosed: pass
        def fail_clock(): raise RuntimeError('observer only')
        with local_server(handler) as uri:
            summary,envelope=lane.collect_fixture(c['bundle'],spec,root/'stream',uri,self.contract,
                clock=clock,_observer_clock=fail_clock if fail else time.monotonic)
        self.assertEqual(summary['status'],'frame_limit')
        return envelope

    def test_inherited_delivery_and_queue_paths_are_not_rewritten(self):
        self.assertIs(lane.DiagnosticSocket.recv,ObservedSocket.recv)
        self.assertIs(lane.DiagnosticSocket.queue_snapshot,ObservedSocket.queue_snapshot)
        self.assertIs(lane.DiagnosticSocket.close,ObservedSocket.close)

    def test_real_recorder_binds_duplicates_fragments_and_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); envelope=self.fixture(root)
            result=lane.verify_fixture(root/'stream',envelope,self.contract)
            self.assertTrue(result['attribution_available'])
            self.assertEqual(result['linked_markers'],5)
            self.assertEqual(result['unknown_markers'],0)
            self.assertTrue(result['raw_archive_integrity_verified'])

    def test_observer_failure_preserves_raw_archive_but_blocks_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); envelope=self.fixture(root,fail=True)
            result=lane.verify_fixture(root/'stream',envelope,self.contract)
            self.assertTrue(result['raw_archive_integrity_verified'])
            self.assertEqual(result['deliveries'],5)
            self.assertEqual(result['markers_with_incomplete_sideband'],5)
            self.assertFalse(result['attribution_available'])

    def test_rehashed_frame_gap_wrong_archive_and_fake_completeness_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); envelope=self.fixture(root)
            bad=deepcopy(envelope); band=bad['connections'][0]['sideband']
            frame=next(r for r in band['reads'] if r['frame_callbacks'])
            frame['frame_first']+=1
            band.pop('sideband_sha256'); band['sideband_sha256']=payload_hash(band)
            bad.pop('envelope_sha256'); bad['envelope_sha256']=payload_hash(bad)
            with self.assertRaises(ContractError): lane.verify_fixture(root/'stream',bad,self.contract)
            bad=deepcopy(envelope); bad['stream_final_record_sha256']='c'*64
            bad.pop('envelope_sha256'); bad['envelope_sha256']=payload_hash(bad)
            with self.assertRaises(ContractError): lane.verify_fixture(root/'stream',bad,self.contract)
            band=deepcopy(envelope['connections'][0]['sideband']); band['complete_observation']=False
            band.pop('sideband_sha256'); band['sideband_sha256']=payload_hash(band)
            with self.assertRaises(ContractError): lane.scan_sideband(band,self.contract)

    def test_rehashed_dispatch_clock_outside_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); envelope=self.fixture(root); band=envelope['connections'][0]['sideband']
            row=next(r for r in band['reads'] if r['frame_callbacks'])
            row['dispatch_first_begin']=row['dispatch_last_end']
            band.pop('sideband_sha256'); band['sideband_sha256']=payload_hash(band)
            envelope.pop('envelope_sha256'); envelope['envelope_sha256']=payload_hash(envelope)
            with self.assertRaises(ContractError): lane.verify_fixture(root/'stream',envelope,self.contract)

    def test_unknown_fields_and_population_budget_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); envelope=self.fixture(root); band=deepcopy(envelope['connections'][0]['sideband'])
            band['reads'][0]['raw_payload']='not permitted'
            band.pop('sideband_sha256'); band['sideband_sha256']=payload_hash(band)
            with self.assertRaises(ContractError): lane.scan_sideband(band,self.contract)
            bad=deepcopy(envelope); bad['connections']*=4
            bad.pop('envelope_sha256'); bad['envelope_sha256']=payload_hash(bad)
            with self.assertRaises(ContractError): lane.verify_fixture(root/'stream',bad,self.contract)

    def test_boolean_ordinals_and_false_native_flow_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); envelope=self.fixture(root)
            band=deepcopy(envelope['connections'][0]['sideband'])
            band['reads'][0]['iteration']=True
            band.pop('sideband_sha256'); band['sideband_sha256']=payload_hash(band)
            with self.assertRaises(ContractError): lane.scan_sideband(band,self.contract)
            band=deepcopy(envelope['connections'][0]['sideband'])
            now=band['reads'][0]['gate_begin']
            band['flows']=[{'operation':1,'kind':'resume','thread':1,'begin':now,'end':now,
                'outcome':'returned','assembler_closed':False,'assembler_paused':False,'queue_depth':4}]
            band.pop('sideband_sha256'); band['sideband_sha256']=payload_hash(band)
            with self.assertRaises(ContractError): lane.scan_sideband(band,self.contract)

    def test_parent_extension_rejects_non_client_class(self):
        from infra.stream import receive_loop_probe as probe
        observer=probe.ObservationBuffer(self.contract)
        with self.assertRaises(ContractError): probe._connection_class(observer,_parent=object)
        from websockets.sync.client import ClientConnection
        class ChangedLoop(ClientConnection):
            def recv_events(self): pass
        with self.assertRaises(ContractError): probe._connection_class(observer,_parent=ChangedLoop)


if __name__ == '__main__': unittest.main()
