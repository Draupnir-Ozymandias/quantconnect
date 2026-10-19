"""Offline stop ownership, real socket faults and retained publication linkage."""
import json
import os
import platform
from pathlib import Path
import signal
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_public_capture as capture
from tests import test_recorder_public_study as fixtures
from tests.test_recorder_public_study import DummyInterrupt, ManualTimer


VALIDATION_PLAN=dict(schema_version='qcrl.public_stop_ownership.validation.v1',
    case='StopOwn01',initial_texts=60,heartbeat_replies=8,expected_texts=68,
    epoch_lead_seconds=20,normal_tail_seconds=65,acquisition_hard_seconds=90,
    close_hard_seconds=5,frame_cap=60000,invocations=1,retries=0,
    unit=dict(CPUQuota='75%',MemoryMax='512M',TasksMax='32',RuntimeMaxSec='240'),
    network='numeric_loopback_only_no_TLS_or_public_feed',
    peer='hold_open_until_client_close',observer='existing_completion_witnesses_only',
    budget_acceptance_claim=False,native_execution_authorized=False)


class StopOwnershipTests(unittest.TestCase):
    def case(self, root):
        return fixtures.PublicRuntimeTests().setup_case(root)

    def test_policy_and_normal_runtime_disarms_before_close(self):
        self.assertEqual(payload_hash(capture.STOP_POLICY), 'dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3')
        self.assertEqual(payload_hash(VALIDATION_PLAN),'9702f4e923b99873dd4d4a7d641e9be634dbadd3d81f6991dc1b70230c35d808')
        with TemporaryDirectory() as d:
            clock,_,_,conn,invoke=self.case(Path(d)/'archive')
            alarms=[];process_guards=[];closed=[]
            def alarm(*a,**k):
                value=DummyInterrupt(*a,**k);alarms.append(value);return value
            def process_guard(*a,**k):
                value=DummyInterrupt(*a,**k);process_guards.append(value);return value
            def close():
                closed.append(alarms[-1].receipt())
                # A queued callback cannot touch the socket after normal claim.
                alarms[-1].interrupt()
            conn.close=close
            result=invoke(interrupt_factory=alarm,connect_guard_factory=process_guard)
            self.assertTrue(capture.normal_completion_proven(result))
            self.assertEqual(closed[0]['owner'],'acquisition_thread')
            self.assertFalse(alarms[-1].fired.is_set())
            self.assertEqual(alarms[-1].normal_deadline,85)
            self.assertEqual(alarms[-1].deadline,85.25)
            self.assertEqual([g.deadline for g in process_guards],[90,10,90])
            self.assertTrue(all(g.owner=='cancelled' for g in process_guards))
            for change in ({'owner':'emergency'},{'fired':True},{'error':'socket fault'},
                           {'completed_at':84},{'emergency_deadline':86}):
                changed=json.loads(json.dumps(result))
                changed['normal_completion'].update(change)
                changed['deadline_interrupts'][-1]=changed['normal_completion']
                self.assertFalse(capture.normal_completion_proven(changed))
            changed=json.loads(json.dumps(result));changed['deadline_interrupts']=[]
            self.assertFalse(capture.normal_completion_proven(changed))
            changed=json.loads(json.dumps(result));changed['deadline_interrupts']*=2
            self.assertFalse(capture.normal_completion_proven(changed))
            changed=json.loads(json.dumps(result));changed['attempted']=False
            self.assertFalse(capture.normal_completion_proven(changed))

    def test_real_websocket_normal_timeout_owns_close(self):
        """Fast offline functional case, or one explicitly frozen Linux validation.

        Native mode uses real clocks and retains files on failure. It is never
        enabled by ordinary test discovery and has no unit launcher or retry.
        """
        from websockets.sync.server import serve
        from websockets.sync.client import connect
        from websockets.exceptions import ConnectionClosedOK
        from infra.stream.recorder_application_worker import message
        from infra.stream.recorder_completion import CompletionWitnesses,verify_completion
        from infra.stream.recorder_case_archive import archive_frames
        from infra.stream.recorder_persistence_worker import publish
        native=os.environ.get('QCRL_STOP_OWNERSHIP_NATIVE')=='1'
        retained=Path('/var/lib/qcrl-stream/public-stop-validation-StopOwn01')
        if native:
            from execution_truth.contracts import verify_artifact_hash
            from infra.stream.recorder_wait_production import inspect_source
            from infra.stream.recorder_rss_thread_cpu_validation import runtime
            from infra.stream.recorder_application_resources import LinuxReader
            from infra.stream.recorder_public_operator import load
            self.assertEqual(platform.system(),'Linux')
            import pwd
            self.assertEqual(os.geteuid(),pwd.getpwnam('qcrl').pw_uid)
            self.assertEqual(os.path.abspath(sys.executable),'/opt/qcrl-stream/venv/bin/python')
            frozen=load(retained/'execution-freeze.json')
            verify_artifact_hash(frozen,'freeze_sha256','one-case validation freeze')
            self.assertEqual(frozen['freeze_sha256'],os.environ.get('QCRL_STOP_FREEZE_SHA256'))
            self.assertEqual(frozen['case'],'StopOwn01')
            self.assertEqual(frozen['stop_policy_sha256'],payload_hash(capture.STOP_POLICY))
            self.assertEqual(frozen['validation_plan_sha256'],payload_hash(VALIDATION_PLAN))
            from infra.stream.recorder_persistence_worker import control
            approval=control(retained/'execution-confirmation.json')
            self.assertIs(approval['direct_user_approval'],True)
            self.assertIs(approval['one_case_only'],True)
            self.assertEqual(approval['freeze_sha256'],frozen['freeze_sha256'])
            source=Path(capture.__file__).resolve().parents[2]
            self.assertEqual(source,retained/'source')
            sources,commit=inspect_source(source)
            self.assertEqual((sources,commit),(frozen['sources'],frozen['source_commit']))
            self.assertEqual(runtime(retained),frozen['runtime'])
            identity=LinuxReader(execute=True).expected
            self.assertEqual(identity['cgroup'],'/system.slice/qcrl-public-stop-StopOwn01.service')
            self.assertEqual(identity['boot_id'],frozen['runtime']['boot_id'])
            initial=LinuxReader(execute=True).read(rss=False)
            self.assertEqual(initial['effective_quota'],.75)
            self.assertEqual(initial['ancestry'][0]['memory_max'],'536870912')
        with TemporaryDirectory() as temporary:
            root=retained/'evidence' if native else Path(temporary)
            if native:
                self.assertEqual(root.resolve(strict=True),root)
                self.assertEqual(list(root.iterdir()),[])
                publish(root/'validation-claim.json',dict(case='StopOwn01',
                    freeze_sha256=frozen['freeze_sha256'],pid=os.getpid()))
            fake_clock,spec,_,_,_=self.case(root/'unused')
            wall=capture.utc_now if native else fake_clock.utc
            mono=time.monotonic if native else fake_clock.mono
            epoch_ns=time.monotonic_ns()+VALIDATION_PLAN['epoch_lead_seconds']*10**9 if native else 20_000_000_000
            witness=CompletionWitnesses(spec,'StopOwn01' if native else 'test.boot',
                clock=wall,monotonic=mono,execute=True)
            ledger=[];errors=[];subscription=[]
            def handler(peer):
                try:
                    subscription.append(json.loads(peer.recv(timeout=10)))
                    for i in range(VALIDATION_PLAN['initial_texts']):
                        value=message(i);peer.send(value);ledger.append(value)
                    while True:
                        self.assertEqual(peer.recv(timeout=95 if native else 2),'PING')
                        peer.send('PONG');ledger.append('PONG')
                except ConnectionClosedOK:pass  # Collector must separately prove normal ownership.
                except BaseException as exc:errors.append(capture.short_error(exc))
            try:
                with serve(handler,'127.0.0.1',0,compression=None,ping_interval=None,
                           max_size=262144,max_queue=16,close_timeout=1) as server:
                    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                    uri='ws://127.0.0.1:'+str(server.socket.getsockname()[1])
                    def connecting(endpoint,**options):
                        real=connect(uri,**options)
                        if native:return real
                        class AcceleratedConnection:
                            socket=real.socket
                            @property
                            def state(self):return real.state
                            def send(self,value):real.send(value)
                            def close(self):real.close()
                            def recv(self,timeout):
                                try:return real.recv(timeout=min(timeout,.002))
                                except TimeoutError:
                                    fake_clock.pause(timeout);raise
                        return AcceleratedConnection()
                    from tests.test_taker_replay import raw_bundle
                    result=capture.collect(raw_bundle(),spec,root/'archive',epoch_ns=epoch_ns,
                        observer=witness,execute=True,clock=wall,monotonic=mono,
                        connect_factory=connecting,
                        interrupt_factory=capture.DeadlineInterrupt if native else DummyInterrupt,
                        connect_guard_factory=capture.ConnectDeadline if native else DummyInterrupt)
                    server.shutdown();thread.join(timeout=2)
                completion=witness.snapshot(root/'archive')
                publish(root/'result.json',result);publish(root/'server.json',dict(sent=ledger,errors=errors,subscription=subscription))
                (root/'completion.json').write_text(json.dumps(completion))
                verified=verify_completion(completion,root/'archive',expected_domain=witness.domain)
                self.assertTrue(completion['complete']);self.assertIsNone(completion['failure'])
                self.assertTrue(capture.normal_completion_proven(result))
                self.assertEqual(result['summary']['status'],'scheduled_stop')
                self.assertIsNone(result['error']);self.assertEqual(result['close_errors'],[])
                self.assertFalse(any(x['fired'] for x in result['deadline_interrupts']))
                self.assertEqual(subscription,[spec['subscription']]);self.assertEqual(errors,[])
                self.assertEqual(archive_frames(root/'archive',len(ledger))[0],ledger)
                self.assertEqual(verified['frames'],len(ledger))
                if native:
                    self.assertEqual(len(ledger),VALIDATION_PLAN['expected_texts'])
                    self.assertEqual(ledger,[message(i) for i in range(60)]+['PONG']*8)
            finally:
                if native:publish(root/'server-final.json',dict(sent=ledger,errors=errors,subscription=subscription))

    def test_normal_and_emergency_deadline_boundary_is_not_a_success_exemption(self):
        left,right=socket.socketpair()
        try:
            now=[1.]
            guard=capture.DeadlineInterrupt(left,1.25,clock=lambda:now[0],
                normal_deadline=1,phase='acquisition',timer_factory=ManualTimer)
            conn=SimpleNamespace(state=capture.State.OPEN)
            with self.assertRaises(ContractError):guard.claim_normal(conn,.999)
            now[0]=1.25
            # Even a delayed callback cannot make a stale, pre-cutoff clock pass.
            with self.assertRaises(ContractError):guard.claim_normal(conn,1)
            guard.interrupt()
            with self.assertRaises(ContractError):guard.claim_normal(conn,1.25)
            guard.cancel()
            self.assertEqual(guard.receipt()['owner'],'emergency')
            self.assertTrue(guard.fired.is_set())
        finally:left.close();right.close()

    def test_cancel_then_queued_callback_never_shuts_down_socket(self):
        left,right=socket.socketpair()
        try:
            guard=capture.DeadlineInterrupt(left,1,timer_factory=ManualTimer)
            guard.cancel();guard.interrupt()
            left.sendall(b'still-open');self.assertEqual(right.recv(10),b'still-open')
            self.assertEqual(guard.receipt()['owner'],'cancelled')
            self.assertFalse(guard.fired.is_set())
        finally:left.close();right.close()

    def test_cancellation_racing_running_callback_retains_emergency(self):
        left,right=socket.socketpair();entered=threading.Event();release=threading.Event()
        original=socket.socket.shutdown
        def shutdown(sock,how):
            entered.set()
            if not release.wait(2):raise RuntimeError('test release missing')
            original(sock,how)
        try:
            guard=capture.DeadlineInterrupt(left,1,timer_factory=ManualTimer)
            with patch.object(socket.socket,'shutdown',shutdown):
                firing=threading.Thread(target=guard.interrupt);firing.start()
                self.assertTrue(entered.wait(2))
                cancelling=threading.Thread(target=guard.cancel);cancelling.start()
                release.set();firing.join(2);cancelling.join(2)
                self.assertFalse(firing.is_alive() or cancelling.is_alive())
            self.assertTrue(guard.fired.is_set())
            self.assertEqual(guard.receipt()['owner'],'emergency')
            self.assertEqual(right.recv(1),b'')
        finally:release.set();left.close();right.close()

    def test_normal_claim_racing_queued_callback_owns_close(self):
        left,right=socket.socketpair();entered=threading.Event();release=threading.Event()
        errors=[]
        class Connection:
            @property
            def state(self):
                entered.set()
                if not release.wait(2):raise RuntimeError('test release missing')
                return capture.State.OPEN
        try:
            guard=capture.DeadlineInterrupt(left,1.25,clock=lambda:1,
                normal_deadline=1,phase='acquisition',timer_factory=ManualTimer)
            def complete():
                try:guard.claim_normal(Connection(),1)
                except BaseException as exc:errors.append(exc)
            normal=threading.Thread(target=complete);normal.start()
            self.assertTrue(entered.wait(2))
            emergency=threading.Thread(target=guard.interrupt);emergency.start()
            release.set();normal.join(2);emergency.join(2);guard.cancel()
            self.assertFalse(normal.is_alive() or emergency.is_alive());self.assertFalse(errors)
            self.assertEqual(guard.receipt()['owner'],'acquisition_thread')
            self.assertFalse(guard.fired.is_set())
            left.sendall(b'x');self.assertEqual(right.recv(1),b'x')
        finally:release.set();left.close();right.close()

    def test_process_guard_cancellation_and_callback_order(self):
        with patch.object(capture.threading,'Timer',ManualTimer),patch.object(capture.os,'kill') as kill:
            first=capture.ConnectDeadline(1,clock=lambda:0)
            first.cancel();first.interrupt();kill.assert_not_called()
            second=capture.ConnectDeadline(1,clock=lambda:0)
            second.interrupt();second.cancel();second.interrupt()
            kill.assert_called_once_with(capture.os.getpid(),signal.SIGTERM)

    def test_real_blocked_receive_subscription_and_ping_send_remain_faults(self):
        for operation in ('receive','subscription','ping'):
            with self.subTest(operation=operation),TemporaryDirectory() as d:
                left,right=socket.socketpair()
                try:
                    left.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
                    _,_,_,conn,invoke=self.case(Path(d)/'archive');conn.socket=left
                    send=conn.send
                    def sending(value):
                        if operation=='subscription' or operation=='ping' and value=='PING':
                            left.sendall(b'x'*(1024**2))
                        else:send(value)
                    conn.send=sending
                    if operation=='receive':
                        def receive(timeout):
                            if left.recv(1)==b'':raise OSError('emergency unblocked receive')
                            raise AssertionError('unexpected peer data')
                        conn.recv=receive
                    alarms=[]
                    def alarm(raw_socket,deadline,**options):
                        # Shorten only this offline fault wait, not production policy.
                        value=capture.DeadlineInterrupt(raw_socket,time.monotonic()+.05,
                            clock=time.monotonic,phase=options['phase'])
                        alarms.append(value);return value
                    result=invoke(interrupt_factory=alarm)
                    self.assertEqual(result['summary']['status'],'interrupted')
                    self.assertIsNotNone(result['error'])
                    self.assertFalse(capture.normal_completion_proven(result))
                    self.assertTrue(any(g.fired.is_set() for g in alarms))
                    self.assertEqual(result['summary']['connections'],1)
                    self.assertTrue((Path(d)/'archive/manifest.json').exists())
                finally:left.close();right.close()

    def test_peer_close_remains_fault_before_or_at_deadline_even_if_timer_fired(self):
        from websockets.exceptions import ConnectionClosedOK
        from websockets.frames import Close
        for at in (1,85):
            for fired in (False,True):
                with self.subTest(at=at,fired=fired),TemporaryDirectory() as d:
                    clock,_,_,conn,invoke=self.case(Path(d)/'archive');alarms=[]
                    def alarm(*args,**kw):
                        value=DummyInterrupt(*args,**kw);alarms.append(value);return value
                    def receive(timeout):
                        clock.seconds=at
                        if fired:alarms[-1].fired.set()
                        raise ConnectionClosedOK(Close(1000,''),Close(1000,''),True)
                    conn.recv=receive
                    result=invoke(interrupt_factory=alarm)
                    self.assertIn('ConnectionClosedOK',result['error'])
                    self.assertFalse(capture.normal_completion_proven(result))

    def test_subscription_interrupt_is_not_erased_when_send_returns_normally(self):
        with TemporaryDirectory() as d:
            _,_,_,conn,invoke=self.case(Path(d)/'archive');alarms=[]
            def alarm(*args,**kw):
                value=DummyInterrupt(*args,**kw);alarms.append(value);return value
            def send(value):alarms[-1].fired.set()
            conn.send=send
            result=invoke(interrupt_factory=alarm)
            self.assertIn('emergency interruption during subscription',result['error'])
            self.assertEqual(result['summary']['status'],'interrupted')
            self.assertEqual(result['summary']['frames'],0)
            self.assertEqual(len(result['deadline_interrupts']),1)
            self.assertFalse(capture.normal_completion_proven(result))

    def test_invalid_or_regressed_claim_clock_keeps_capture_unqualified(self):
        for reading in (None,float('nan'),84):
            with self.subTest(reading=reading),TemporaryDirectory() as d:
                _,_,_,_,invoke=self.case(Path(d)/'archive')
                def alarm(*args,**kw):
                    value=DummyInterrupt(*args,**kw)
                    if kw.get('phase')=='acquisition':value.clock=lambda:reading
                    return value
                result=invoke(interrupt_factory=alarm)
                self.assertEqual(result['summary']['status'],'interrupted')
                self.assertIsNotNone(result['error'])
                self.assertIsNone(result['normal_completion'])
                self.assertFalse(capture.normal_completion_proven(result))

    def test_actual_collect_blocked_close_has_default_five_second_process_bound(self):
        with TemporaryDirectory() as d:
            program=('import time;from pathlib import Path;'
                'from tests.test_recorder_public_study import PublicRuntimeTests;'
                'from infra.stream.recorder_public_capture import ConnectDeadline;'
                'clock,spec,witness,conn,invoke=PublicRuntimeTests().setup_case(Path('+repr(d)+')/"archive");'
                'conn.close=lambda:time.sleep(30);invoke(connect_guard_factory=ConnectDeadline)')
            result=subprocess.run([sys.executable,'-c',program],capture_output=True,timeout=8)
            self.assertEqual(result.returncode,-signal.SIGTERM)
            self.assertTrue(any(p.stat().st_size for p in (Path(d)/'archive').glob('segment-*.gz*')))
            self.assertTrue((Path(d)/'archive/manifest.json').exists())


if __name__=='__main__':unittest.main()
