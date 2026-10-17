"""Offline actual recorder paths and public study count boundaries; no public socket."""
from copy import deepcopy
from datetime import timedelta
from fractions import Fraction
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import stream_plan
from infra.stream.recorder_completion import CompletionWitnesses, verify_completion
from infra.stream import recorder_public_counts as counts
from infra.stream import recorder_public_capture as capture
from infra.stream import recorder_public_study as study
from infra.stream import recorder_public_operator as operator
from infra.stream.recorder_persistence_worker import publish
from tests import test_market_stream as fixtures
from tests.test_taker_replay import raw_bundle, revise


def public_fixture():
    raw=raw_bundle()
    from execution_truth.rolling_stream import SOURCE, DESCRIPTION
    start=int(counts.utc(counts.PLAN['event_start']).timestamp())
    revise(raw,'gamma_market',startDate='2026-10-16T16:00:00Z',
        eventStartTime=counts.PLAN['event_start'],endDate=counts.PLAN['event_end'],
        slug='btc-updown-5m-'+str(start),question='Bitcoin Up or Down - October 17',
        description=DESCRIPTION,resolutionSource=SOURCE)
    return raw


def frame(i, a, b):
    return dict(sequence=i, returned=dict(before=a, after=b))


class CountsTests(unittest.TestCase):
    def test_plan_and_detached_copy(self):
        self.assertEqual(payload_hash(counts.ORIGINAL_PLAN),
            '90fe9a6a7fc6fd0ba78b1a1d6218188cfd7399dd06cbd5bae02de870e2f56d32')
        self.assertEqual(payload_hash(counts.SUCCESSOR_V2_PLAN),
            '220e1b592365b33dd5e0e4c46ab53103735f4add634694aba4cb745a7fa0adff')
        self.assertEqual(payload_hash(counts.PLAN), '6cdc0386787c0a6bd68ac0061e59c6f50b657dfac19f2ec27bd056f336488533')
        self.assertEqual(counts.PLAN['case'], 'btc5m-20261017T183000Z-local-counts-03')
        changed={'schema_version','parent_plan_sha256','case','event_start','event_end',
                 'discovery','freeze_cutoff','arm','nominal_epoch'}
        self.assertEqual({k:v for k,v in counts.PLAN.items() if k not in changed},
                         {k:v for k,v in counts.SUCCESSOR_V2_PLAN.items() if k not in changed})
        self.assertEqual(counts.PLAN['connection_attempts'], 1)
        self.assertEqual(counts.PLAN['reconnects'], 0)
        self.assertEqual(counts.PLAN['original_application_verdict'], 'fail')
        value = counts.plan()
        value['unit']['MemoryMax'] = '1G'
        self.assertEqual(counts.plan()['unit']['MemoryMax'], '512M')

    def test_exact_anchor_ceiling_and_no_past_adoption(self):
        value = counts.epoch_ns(1., '2026-10-17T18:30:40.000001Z', 1.0000000001)
        exact = (Fraction(1.0000000001)+Fraction(19999999,1000000))*1000000000
        self.assertGreaterEqual(value, exact)
        self.assertLess(value-exact, 1)
        for a, u, b in [(2, counts.PLAN['arm'], 1),
                         (1, counts.PLAN['nominal_epoch'], 1),
                         (float('nan'), counts.PLAN['arm'], 1),
                         (True, counts.PLAN['arm'], 1)]:
            with self.assertRaises(ContractError): counts.epoch_ns(a,u,b)

    def test_closed_edges_long_intervals_tail_and_no_badge(self):
        value = counts.bins([frame(0,10.25,10.5), frame(1,10.75,11),
            frame(2,11,11.125), frame(3,12,15.1), frame(4,70,70)],10000000000,
            coverage_complete=True)
        self.assertEqual((value['rows'][0]['lower'],value['rows'][0]['upper_archived']),(1,2))
        self.assertEqual((value['rows'][1]['lower'],value['rows'][1]['upper_archived']),(1,2))
        self.assertEqual(value['ambiguous'][1]['possible_primary_bins'],[2,3,4,5])
        self.assertEqual(value['outside_primary']['4'],dict(first_bin=60,last_bin=60))
        self.assertNotIn('verdict', value)
        self.assertFalse(value['venue_completeness_proven'])
        self.assertEqual(value['original_application_verdict'],'fail')

    def test_unplaced_and_censored_cannot_manufacture_zero_coverage(self):
        for bad in (float('nan'), float('inf'), True, -1):
            value=counts.bins([frame(0,bad,12)],10000000000,censored_from=11)
            self.assertEqual(value['unplaced'],[0])
            self.assertEqual(value['rows'][0]['upper_archived'],1)
            self.assertEqual(value['rows'][0]['coverage'],'unverified')
            self.assertEqual(value['rows'][1]['coverage'],'censored')
            self.assertTrue(all(r['feed_activity_upper'] is None for r in value['rows']))
        with self.assertRaises(ContractError):counts.bins([frame(1,10,10)],10000000000)
        self.assertEqual(counts.bins([],10000000000)['rows'][0]['coverage'],'unverified')

    def test_direct_interval_membership_agrees_without_width_filter(self):
        frames=[frame(i,float(Fraction(40*i,13)),float(Fraction(40*i,13)+Fraction(7,2)))
                for i in range(25)]
        value=counts.bins(frames,1000000000)
        for row in value['rows']:
            lo,hi=Fraction(1+row['slot']),Fraction(2+row['slot'])
            self.assertEqual(row['lower'],sum(lo<=Fraction(f['returned']['before'])
                <=Fraction(f['returned']['after'])<hi for f in frames))
            self.assertEqual(row['upper_linked'],sum(Fraction(f['returned']['after'])>=lo
                and Fraction(f['returned']['before'])<hi for f in frames))


class ManualTimer:
    def __init__(self,delay,callback):
        self.delay,self.callback=delay,callback
    def start(self):pass
    def cancel(self):pass
    def join(self,timeout=None):pass


class DummyInterrupt(capture.DeadlineInterrupt):
    def __init__(self,*args,**kwargs):
        if len(args)==1:args=(None,args[0])
        super().__init__(*args,**kwargs,timer_factory=ManualTimer)


class PublicRuntimeTests(unittest.TestCase):
    def setup_case(self, root, raw=None):
        clock=fixtures.Clock()
        raw=raw_bundle() if raw is None else raw
        spec=stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000)
        witness=CompletionWitnesses(spec,'test.boot',clock=clock.utc,monotonic=clock.mono,execute=True)
        guard=SimpleNamespace(check=lambda:None)
        class Connection:
            socket=None
            state=capture.State.OPEN
            outgoing=[]
            next_reply=False
            calls=0
            def send(self,value):
                self.outgoing.append(value)
                self.next_reply=True
            def recv(self,timeout):
                self.calls+=1
                clock.pause(timeout)
                if self.next_reply:
                    self.next_reply=False
                    return 'PONG'
                raise TimeoutError('idle')
            def close(self):pass
        conn=Connection()
        def invoke(**options):
            args=dict(epoch_ns=20000000000,observer=witness,execute=True,clock=clock.utc,
                monotonic=clock.mono,connect_factory=lambda *a,**k:conn,guard=guard,
                interrupt_factory=DummyInterrupt,connect_guard_factory=DummyInterrupt)
            args.update(options)
            return capture.collect(raw,spec,root,**args)
        return clock,spec,witness,conn,invoke

    def test_actual_writer_and_witness_publication_with_deadline_and_heartbeats(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'archive'
            clock,spec,witness,conn,invoke=self.setup_case(root)
            result=invoke()
            report=witness.snapshot(root)
            verified=verify_completion(report,root,expected_domain='test.boot')
            self.assertEqual(result['summary']['status'],'scheduled_stop')
            self.assertIsNone(result['error'])
            self.assertEqual(result['summary']['connections'],1)
            self.assertEqual(clock.seconds,85)
            self.assertEqual(verified['frames'],result['summary']['frames'])
            self.assertTrue(capture.normal_completion_proven(result))
            self.assertEqual(result['normal_completion']['owner'],'acquisition_thread')
            self.assertEqual(json.loads(conn.outgoing[0]),spec['subscription'])
            self.assertTrue(all(t=='PING' for t in conn.outgoing[1:]))

    def test_explicit_guard_and_late_readiness_before_connect(self):
        with TemporaryDirectory() as d:
            _,_,_,_,invoke=self.setup_case(Path(d)/'a')
            with self.assertRaises(ContractError):invoke(execute=False)
        with TemporaryDirectory() as d:
            clock,_,_,_,invoke=self.setup_case(Path(d)/'a')
            def late(*a,**k):
                clock.pause(20)
                return SimpleNamespace(socket=None,send=lambda v:None,close=lambda:None)
            result=invoke(connect_factory=late)
            self.assertEqual(result['summary']['connections'],1)
            self.assertIn('readiness missed',result['error'])

    def test_normal_remote_close_is_fault_even_across_deadline_race(self):
        from websockets.exceptions import ConnectionClosedOK
        from websockets.frames import Close
        with TemporaryDirectory() as d:
            clock,_,_,conn,invoke=self.setup_case(Path(d)/'a')
            alarms=[]
            def alarm(*a,**k):
                value=DummyInterrupt(*a,**k);alarms.append(value);return value
            def fail(timeout):
                alarms[-1].fired.set()
                raise ConnectionClosedOK(Close(1000,''),Close(1000,''),True)
            conn.recv=fail
            result=invoke(interrupt_factory=alarm)
            self.assertIn('ConnectionClosedOK',result['error'])
            self.assertEqual(result['summary']['status'],'interrupted')
            self.assertEqual(len(result['terminal_receive']),1)
            self.assertTrue(result['deadline_interrupts'][-1]['fired'])

    def test_wrong_binding_preserved_before_stop_and_unknown_text_accepted(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'a'
            _,_,witness,conn,invoke=self.setup_case(root)
            values=iter(['{malformed','{"event_type":"unknown"}','{"asset_id":"foreign"}'])
            conn.recv=lambda timeout:next(values)
            result=invoke()
            self.assertEqual(result['summary']['frames'],3)
            self.assertIn('foreign',result['error'])
            verified=verify_completion(witness.snapshot(root),root,expected_domain='test.boot')
            self.assertEqual(verified['frames'],3)

    def test_already_closed_at_stop_is_not_completed_coverage(self):
        with TemporaryDirectory() as d:
            _,_,_,conn,invoke=self.setup_case(Path(d)/'a')
            conn.state=capture.State.CLOSED
            result=invoke()
            self.assertEqual(result['summary']['status'],'interrupted')
            self.assertIn('closure timing unknown',result['error'])

    def test_clock_failure_keeps_returned_raw_once_then_stops(self):
        from infra.stream.recorder_case_archive import archive_frames
        with TemporaryDirectory() as d:
            root=Path(d)/'a';clock,_,witness,conn,invoke=self.setup_case(root)
            original=clock.utc;state=dict(fail=False,calls=0)
            def wall():
                if state['fail']:
                    state['fail']=False
                    return None
                return original()
            clock.utc=wall;witness.clock=wall
            def receive(timeout):
                state['calls']+=1;state['fail']=True
                return 'raw-at-clock-failure'
            conn.recv=receive
            result=invoke()
            self.assertEqual(state['calls'],1)
            self.assertEqual(result['summary']['frames'],1)
            self.assertIn('clock fault',result['error'])
            self.assertEqual(archive_frames(root,1)[0],['raw-at-clock-failure'])
            self.assertFalse(witness.snapshot(root)['complete'])

    def test_subscription_and_close_failures_retained_no_second_attempt(self):
        for at in ('connect','send','close'):
            with self.subTest(at=at),TemporaryDirectory() as d:
                _,_,_,conn,invoke=self.setup_case(Path(d)/'a')
                calls=[]
                def connect(*a,**k):
                    calls.append(1)
                    if at=='connect':raise OSError('connect fault')
                    return conn
                def fault(*a):raise OSError(at+' fault')
                if at=='send':conn.send=fault
                if at=='close':conn.close=fault
                result=invoke(connect_factory=connect)
                self.assertEqual(len(calls),1)
                self.assertIn(at+' fault',result['error'])

    def test_blocked_send_interrupted_by_actual_watchdog_without_network(self):
        left,right=socket.socketpair()
        try:
            left.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096)
            alarm=capture.DeadlineInterrupt(left,time.monotonic()+.05)
            try:
                with self.assertRaises(OSError):left.sendall(b'x'*(1024**2))
            finally:alarm.cancel()
            self.assertTrue(alarm.fired.is_set())
        finally:left.close();right.close()

    def test_blocked_connection_worker_terminates_once_with_retained_prefix(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'prefix'
            program=('import time,os;from pathlib import Path;'
                'from infra.stream.recorder_public_capture import ConnectDeadline;'
                'p=Path('+repr(str(path))+');'
                'f=p.open("xb");f.write(b"retained-prefix");f.flush();os.fsync(f.fileno());'
                'g=ConnectDeadline(time.monotonic()+.05);time.sleep(5)')
            result=subprocess.run([sys.executable,'-c',program],capture_output=True,timeout=3)
            self.assertEqual(result.returncode,-15)
            self.assertEqual(path.read_bytes(),b'retained-prefix')

    def test_storage_reserve_spool_and_symlink_guards(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(capture.shutil,'disk_usage',return_value=SimpleNamespace(free=3*1024**3)):
                guard=capture.StorageGuard(root);guard.check()
                (root/'link').symlink_to(root/'absent')
                with self.assertRaisesRegex(ContractError,'symlink'):guard.check()
            with patch.object(capture.shutil,'disk_usage',return_value=SimpleNamespace(free=1024**3)):
                with self.assertRaisesRegex(ContractError,'two GiB'):capture.StorageGuard(root)

    def test_fixed_market_and_discovery_window_faults(self):
        raw=public_fixture()
        case=dict(case=counts.PLAN['case'],study_plan_sha256=payload_hash(counts.PLAN),
            discovered_at_utc=counts.PLAN['discovery'],raw_bundle=raw,
            spec=stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000))
        def seal(value):return dict(value,artifact_sha256=payload_hash(value))
        self.assertEqual(study.validate_case(seal(case))['case'],counts.PLAN['case'])
        for mutation in ('time','window','tokens','slug','case','storage'):
            value=deepcopy(case)
            if mutation=='time':value['discovered_at_utc']='2026-10-17T15:55:31Z'
            if mutation=='window':revise(value['raw_bundle'],'gamma_market',eventStartTime='2026-10-17T16:00:01Z')
            if mutation=='tokens':value['spec']['asset_ids']=['foreign','10002']
            if mutation=='slug':revise(value['raw_bundle'],'gamma_market',slug='btc-updown-5m-other')
            if mutation=='case':value['case']='replacement'
            if mutation=='storage':value['spec']['storage']['max_compressed_bytes']*=2
            with self.subTest(mutation=mutation),self.assertRaises(ContractError):study.validate_case(seal(value))

    def test_independent_report_broken_receipts_and_missing_archive_never_badge(self):
        for mutation in ('none','receipt','archive','early','consumer','stop_receipt'):
            with self.subTest(mutation=mutation),TemporaryDirectory() as d:
                root=Path(d);raw=public_fixture()
                clock,spec,witness,conn,invoke=self.setup_case(root/'archive',raw)
                result=invoke()
                case=publish(root/'case.json',dict(case=counts.PLAN['case'],
                    study_plan_sha256=payload_hash(counts.PLAN),discovered_at_utc=counts.PLAN['discovery'],
                    raw_bundle=raw,spec=spec))
                completion=witness.snapshot(root/'archive')
                (root/'completion.json').write_text(json.dumps(completion))
                if mutation=='receipt':(root/'completion.json').unlink()
                if mutation=='archive':(root/'archive/segment-000000.gz').unlink()
                if mutation=='early':
                    # Closing time alone cannot repair an acquisition ending early.
                    result['acquisition_ended']=70
                    result['closed']=90
                if mutation=='stop_receipt':result['normal_completion']=None
                publish(root/'consumer.json',dict(case_sha256=case['artifact_sha256'],
                    result=result,epoch_ns=20000000000,domain='test.boot',
                    identity=dict(pid=os.getpid()),error=None,observer_thread_alive=False))
                if mutation=='consumer':(root/'consumer.json').unlink()
                value=study.report(root)
                self.assertEqual(len(value['rows']),60)
                self.assertNotIn('verdict',value)
                if mutation=='none':self.assertTrue(all(r['coverage']=='recorded' for r in value['rows']))
                if mutation=='receipt':self.assertEqual(len(value['unplaced']),result['summary']['frames'])
                if mutation=='archive':self.assertIsNone(value['population'])
                if mutation=='consumer':
                    self.assertIsNone(value['population'])
                    self.assertIsNone(value['epoch_ns'])
                    self.assertTrue(all(r['lower'] is None for r in value['rows']))
                if mutation=='early':self.assertTrue(any(r['coverage']!='recorded' for r in value['rows']))
                if mutation=='stop_receipt':self.assertTrue(all(r['coverage']!='recorded' for r in value['rows']))


class OperatorTests(unittest.TestCase):
    def test_fixed_metadata_opportunity_and_no_repeat(self):
        class Acquirer:
            def __init__(self,**kw):pass
            def resolve_market_slug(self,slug,kind):
                self.assertion=(slug,kind)
                return dict(resolved_market_id='123456')
            def acquire_market_bundle(self,value):return public_fixture()
        with TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(ContractError):operator.discover(root,{},execute=False)
            with self.assertRaises(ContractError):operator.discover(root,{},execute=True,
                clock=lambda:counts.utc(counts.PLAN['discovery'])+timedelta(seconds=31))
            self.assertFalse(list(root.iterdir()))
            with patch.object(operator,'pinned_tls',return_value=None):
                case=operator.discover(root,dict(freeze_sha256='0'*64),execute=True,
                    clock=lambda:counts.utc(counts.PLAN['discovery']),acquirer_factory=Acquirer)
            self.assertEqual(case['case'],counts.PLAN['case'])
            with self.assertRaises(FileExistsError):operator.discover(root,dict(freeze_sha256='0'*64),execute=True,
                clock=lambda:counts.utc(counts.PLAN['discovery']),acquirer_factory=Acquirer)

    def test_controller_stops_only_its_attempt_no_retry_after_fault(self):
        for fault in ('none','preflight','discover','lock','start_before','start_after','release','await_exit'):
            with self.subTest(fault=fault):
                calls=[]
                class Ops:
                    submission_attempted=False
                    def event(self,name):
                        calls.append(name)
                        if name==fault:raise OSError(name)
                    def preflight(self):self.event('preflight')
                    def wait_until(self,key):self.event('wait_'+key)
                    def discover(self):self.event('discover');return {}
                    def lock(self,case):self.event('lock')
                    def start(self):
                        self.event('start_before');self.submission_attempted=True;self.event('start_after')
                    def release(self,case):self.event('release')
                    def await_exit(self):self.event('await_exit')
                    def failure(self,error,started):calls.append(('failure',started))
                    def stop_and_seal(self):calls.append('stop')
                operator.run_controller(Ops())
                self.assertLessEqual(calls.count('discover'),1)
                self.assertLessEqual(calls.count('start_after'),1)
                self.assertEqual('stop' in calls,fault in ('none','start_after','release','await_exit'))
                if fault=='discover':self.assertNotIn('wait_arm',calls)

    def test_unit_limits_and_metadata_credentials_isolation(self):
        expected=operator.properties()
        raw=dict(expected,MemoryMax='536870912',CPUQuotaPerSecUSec='750ms',RuntimeMaxUSec='4min',IPAddressAllow='')
        self.assertEqual(operator.verify_properties(raw),expected)
        for key,value in [('MemoryMax','1073741824'),('User','root'),('IPAddressDeny','any'),
                          ('InaccessiblePaths',''),('ReadWritePaths','/')]:
            bad=dict(raw);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ContractError):operator.verify_properties(bad)

    def test_metadata_transport_refuses_account_redirect_proxy_and_extra_requests(self):
        with TemporaryDirectory() as d:
            transport=operator.MetadataTransport(Path(d))
            for url in ('http://gamma-api.polymarket.com/markets/123',
                        'https://clob.polymarket.com/orders',
                        'https://user:pass@clob.polymarket.com/book',
                        'https://example.com/book'):
                with self.assertRaises(ContractError):transport.get_json(url)
            self.assertEqual(transport.requests,0)
            with self.assertRaises(ContractError):operator.NoRedirect().redirect_request(None,None,None,None,None,None)
            transport.requests=5
            with self.assertRaises(ContractError):transport.get_json('https://gamma-api.polymarket.com/markets/123')

    def test_metadata_retains_partial_body_on_byte_cap_failure(self):
        from io import BytesIO
        class Response(BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        with TemporaryDirectory() as d:
            root=Path(d);transport=operator.MetadataTransport(root)
            transport.opener=SimpleNamespace(open=lambda *a,**k:Response(b'x'*(2*1024**2+1)))
            with self.assertRaisesRegex(ContractError,'response cap'):
                transport.get_json('https://gamma-api.polymarket.com/markets/123')
            self.assertEqual((root/'response-1.partial').stat().st_size,2*1024**2+1)
            self.assertTrue((root/'request-1.json').exists())
            self.assertFalse((root/'response-1.body').exists())


if __name__=='__main__':unittest.main()


class TLSBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.der=ssl.create_default_context().get_ca_certs(binary_form=True)[0]
        cls.bundle=('# Å non-ASCII fixture comment\n'+ssl.DER_cert_to_PEM_cert(cls.der)).encode('utf-8')

    def fixture(self,root,data=None):
        import hashlib
        path=Path(root)/'ca.pem';data=self.bundle if data is None else data;path.write_bytes(data)
        profile=dict(ca_file=str(path),ca_sha256=hashlib.sha256(data).hexdigest())
        return path,profile,dict(tls=profile)

    def test_non_ascii_bundle_real_loader_and_snapshot_cleanup(self):
        with TemporaryDirectory() as d:
            path,profile,frozen=self.fixture(d)
            loader=ssl.create_default_context;seen=[]
            def load(**kw):
                self.assertEqual(set(kw),{'cafile'})
                fd=int(kw['cafile'].split('/')[-1]);seen.append(fd)
                self.assertEqual(os.fstat(fd).st_mode & 0o777,0o600)
                self.assertNotEqual(kw['cafile'],str(path))
                return loader(**kw)
            with patch.object(operator,'tls_profile',return_value=profile),patch.object(ssl,'create_default_context',side_effect=load):
                context=operator.pinned_tls(frozen)
            self.assertEqual(context.get_ca_certs(binary_form=True),[self.der])
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
            self.assertEqual(len(seen),1)
            with self.assertRaises(OSError):os.fstat(seen[0])

    def test_malformed_empty_and_oversized_bundles_fail(self):
        for data,expected in ((b'',ssl.SSLError),(b'not a certificate\n',ssl.SSLError),
                               (b'x'*(4*1024**2+1),ContractError)):
            with self.subTest(size=len(data)),TemporaryDirectory() as d:
                _,profile,frozen=self.fixture(d,data)
                with patch.object(operator,'tls_profile',return_value=profile),self.assertRaises(expected):
                    operator.pinned_tls(frozen)

    def test_profile_and_byte_drift_refused(self):
        with TemporaryDirectory() as d:
            path,profile,frozen=self.fixture(d)
            with patch.object(operator,'tls_profile',return_value=dict(profile,changed=True)),self.assertRaises(ContractError):
                operator.pinned_tls(frozen)
            path.write_bytes(self.bundle+b'# changed\n')
            with patch.object(operator,'tls_profile',return_value=profile),self.assertRaises(ContractError):
                operator.pinned_tls(frozen)

    def test_path_replacement_after_hash_cannot_change_loaded_snapshot(self):
        with TemporaryDirectory() as d:
            path,profile,frozen=self.fixture(d);loader=ssl.create_default_context
            def replace(**kw):
                path.write_bytes(b'not a certificate anymore')
                return loader(**kw)
            with patch.object(operator,'tls_profile',return_value=profile),patch.object(ssl,'create_default_context',side_effect=replace):
                context=operator.pinned_tls(frozen)
            self.assertEqual(context.get_ca_certs(binary_form=True),[self.der])

    def test_actual_readiness_constructs_context_and_refuses_malformed_ca(self):
        from contextlib import ExitStack
        for data,expected_error in ((self.bundle,None),(b'malformed PEM',ssl.SSLError)):
            with self.subTest(malformed=expected_error is not None),TemporaryDirectory() as d,ExitStack() as stack:
                _,profile,_=self.fixture(d,data)
                approval=dict(artifact_sha256='a'*64,case=counts.PLAN['case'],one_case_only=True)
                value=dict(study_plan=counts.PLAN,study_plan_sha256=payload_hash(counts.PLAN),
                    unit_properties=operator.properties(),sources={},source_commit='f'*40,runtime={},tls=profile,
                    public_state={},operator_approval_sha256=approval['artifact_sha256'])
                frozen=dict(value,freeze_sha256=payload_hash(value))
                stack.enter_context(patch.object(operator,'inspect_source',return_value=({},'f'*40)))
                stack.enter_context(patch('infra.stream.recorder_rss_thread_cpu_validation.runtime',return_value={}))
                stack.enter_context(patch.object(operator,'tls_profile',return_value=profile))
                stack.enter_context(patch.object(operator,'public_state',return_value={}))
                stack.enter_context(patch.object(operator,'control',return_value=approval))
                network=stack.enter_context(patch.object(operator,'build_opener',side_effect=AssertionError('no network')))
                if expected_error:
                    with self.assertRaises(expected_error):operator.verify_freeze(Path(d),frozen)
                else:operator.verify_freeze(Path(d),frozen)
                self.assertEqual(network.call_count,0)
