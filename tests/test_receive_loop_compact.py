from copy import deepcopy
import inspect
import json
import queue
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError,payload_hash
from infra.stream import receive_loop_compact as compact,receive_loop_probe as reference
from infra.stream import receive_loop_cost as cost,receive_loop_contract as contract
from tests.test_receive_adapter import AVAILABLE
from tests.test_receive_loop_probe import NativeSocket


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class CompactBufferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.contract=contract.declare('a'*64,contract.runtime_receipt())

    def buffer(self,kind=compact.CompactBuffer,clock=None):
        return kind(self.contract,clock=clock or cost.StepClock())

    def snapshot(self,buffer): buffer.loop_finished(); return buffer.snapshot()

    def read(self,buffer):
        row=buffer.gate_begin(); buffer.gate_end(row,'acquired')
        token=buffer.read_begin(); buffer.read_end(token,data=b'x')
        return row

    def test_deterministic_model_exact_fields_clocks_and_independent_scan(self):
        bands=[]; clocks=[]
        with patch.object(cost,'POLICY',dict(cost.POLICY,reads=32)):
            for kind in (reference.ObservationBuffer,compact.CompactBuffer):
                clock=cost.StepClock(); state=cost.prepare('observer_direct',self.contract,clock)
                state.observer=kind(self.contract,clock=clock); state.observer.installed=True
                cost.workload(state); bands.append(self.snapshot(state.observer)); clocks.append(clock.calls)
        for field in ('reads','flows','disabled_reason','complete_observation','receiver_error_type'):
            self.assertEqual(bands[0][field],bands[1][field])
        self.assertEqual(clocks,[264,264])
        scan=compact.scan_model(bands[1],self.contract)
        self.assertTrue(scan['complete']); self.assertEqual(scan['frame_callbacks'],64)
        self.assertTrue(scan['model_only']); self.assertFalse(scan['transport_installation_verified'])

    def test_clock_fault_at_every_update_retains_same_prefix(self):
        for fault_at in range(1,9):
            bands=[]; calls=[]
            for kind in (reference.ObservationBuffer,compact.CompactBuffer):
                n=[0]
                def clock():
                    n[0]+=1
                    if n[0]==fault_at: raise RuntimeError('injected clock fault')
                    return n[0]/1000000
                b=self.buffer(kind,clock); b.installed=True; row=self.read(b)
                token=b.dispatch_begin(True); b.dispatch_end(token)
                assembler=SimpleNamespace(closed=False,paused=True,frames=queue.SimpleQueue())
                token=b.flow_begin('pause',assembler); b.flow_end(token)
                bands.append(self.snapshot(b)); calls.append(n[0])
            for field in ('reads','flows','disabled_reason','complete_observation'):
                self.assertEqual(bands[0][field],bands[1][field],(fault_at,field))
            self.assertEqual(calls[0],calls[1]); self.assertFalse(bands[1]['complete_observation'])

    def test_native_return_eof_error_and_observer_failure_preserved(self):
        for error in (None,TimeoutError('native timeout'),OSError('native socket')):
            b=self.buffer(); row=b.gate_begin(); b.gate_end(row,'acquired')
            native=NativeSocket(b'',error); proxy=reference.SocketProxy(native,b)
            if error:
                with self.assertRaises(type(error)) as caught: proxy.recv(19)
                self.assertIs(caught.exception,error)
            else: self.assertEqual(proxy.recv(19),b'')
            self.assertEqual(len(native.calls),1)
        b=self.buffer(); row=b.gate_begin(); b.gate_end(row,'acquired')
        native=NativeSocket(error=OSError('native'))
        with patch.object(b,'_stamp',side_effect=RuntimeError('observer')):
            with self.assertRaises(OSError) as caught: reference.SocketProxy(native,b).recv(9)
        self.assertIs(caught.exception,native.error); self.assertEqual(len(native.calls),1)
        self.assertEqual(b.disabled_reason,'observer_error')

    def test_native_calls_are_outside_metadata_lock(self):
        b=self.buffer(); self.read(b)
        def recv(*args):
            self.assertTrue(b.lock.acquire(False)); b.lock.release(); return b'x'
        # Next read iteration, not a repeated read of the completed row.
        row=b.gate_begin(); b.gate_end(row,'acquired')
        self.assertEqual(reference.SocketProxy(SimpleNamespace(recv=recv),b).recv(1),b'x')
        def acquire(*args):
            self.assertTrue(b.lock.acquire(False)); b.lock.release(); return True
        self.assertTrue(reference.GateProxy(SimpleNamespace(acquire=acquire),b).acquire())

    def test_flow_under_existing_mutex_keeps_actual_caller_thread(self):
        b=self.buffer(); assembler=SimpleNamespace(closed=True,paused=True,frames=queue.SimpleQueue(),mutex=threading.Lock())
        identities=[]; results=[]
        def run():
            identities.append(threading.get_ident())
            with assembler.mutex:
                def native():
                    self.assertTrue(assembler.mutex.locked())
                    self.assertTrue(b.lock.acquire(False)); b.lock.release(); return 'native'
                results.append(reference.flow_callback(native,'resume',assembler,b)())
        worker=threading.Thread(target=run); worker.start(); worker.join(2)
        self.assertFalse(worker.is_alive()); self.assertEqual(results,['native'])
        band=self.snapshot(b); self.assertEqual(band['flows'][0]['thread'],identities[0])
        self.assertTrue(band['flows'][0]['assembler_closed'])

    def test_budget_exhaustion_snapshot_cap_and_no_closures(self):
        b=self.buffer(); b.limits['max_read_summaries']=0
        native=threading.Lock(); gate=reference.GateProxy(native,b)
        with gate: self.assertTrue(native.locked())
        self.assertFalse(native.locked()); self.assertEqual(b.disabled_reason,'read_summary_budget')
        b=self.buffer(); self.read(b); b.loop_finished(); b.limits['max_encoded_sideband_bytes']=1
        with self.assertRaises(ContractError): b.snapshot()
        self.assertEqual(len(b.reads),1)
        self.assertFalse(hasattr(b.reads[0],'__dict__'))
        for method in ('gate_begin','gate_end','read_begin','read_end','flow_begin','flow_end','dispatch_begin','dispatch_end'):
            self.assertNotIn('def action',inspect.getsource(getattr(compact.CompactBuffer,method)))

    def test_native_connector_rejects_model_before_any_installation(self):
        b=self.buffer()
        self.assertNotIsInstance(b,reference.ObservationBuffer)
        with self.assertRaises(ContractError): reference.connect_loopback('ws://127.0.0.1:9',b)
        self.assertFalse(b.claimed)

    def test_model_schema_source_and_field_tampering_rejected(self):
        b=self.buffer(); b.installed=True; self.read(b); band=self.snapshot(b)
        self.assertTrue(compact.scan_model(band,self.contract)['complete'])
        for mutate in (lambda o:o.update(implementation_sha256='a'*64),
                       lambda o:o.update(model_only=False),lambda o:o.update(raw_payload='no'),
                       lambda o:o['reads'][0].update(iteration=True)):
            bad=deepcopy(band); mutate(bad); bad.pop('sideband_sha256'); bad['sideband_sha256']=payload_hash(bad)
            with self.assertRaises(ContractError): compact.scan_model(bad,self.contract)

    def test_snapshot_is_detached_and_early_or_incomplete_not_success(self):
        b=self.buffer()
        with self.assertRaises(ContractError): b.snapshot()
        b.installed=True; b.gate_begin(); band=self.snapshot(b)
        self.assertFalse(band['complete_observation'])
        band['reads'][0]['iteration']=99
        self.assertEqual(b.reads[0].iteration,1)

    def test_invalid_and_regressing_clocks_match_reference(self):
        for values in ([2,1],[True],[float('nan')],[float('inf')],[-1]):
            bands=[]
            for kind in (reference.ObservationBuffer,compact.CompactBuffer):
                b=self.buffer(kind,iter(values).__next__); row=b.gate_begin(); b.gate_end(row,'acquired')
                bands.append(self.snapshot(b))
            self.assertEqual(bands[0]['reads'],bands[1]['reads'])
            self.assertEqual(bands[0]['disabled_reason'],bands[1]['disabled_reason'])


if __name__=='__main__': unittest.main()
