"""Prospective notification and pre-close persistence; actual collector paths."""
from copy import deepcopy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from execution_truth.contracts import payload_hash,ContractError
from infra.stream import recorder_public_capture as capture
from infra.stream import recorder_public_study as study
from infra.stream import recorder_public_counts as counts
from infra.stream.recorder_completion import verify_completion
from infra.stream.recorder_persistence_worker import publish
from tests import test_recorder_public_study as fixtures
public_fixture=fixtures.public_fixture


def notice():
    # Structural reproduction of v4's offending event, with synthetic IDs only.
    return dict(event_type='new_market',market='0x'+'a'*64,condition_id='0x'+'a'*64,
                assets_ids=['20001','20002'],clob_token_ids=['20001','20002'],outcomes=['Over','Under'])


def setup(root):
    clock,spec,witness,conn,invoke=fixtures.PublicRuntimeTests().setup_case(root/'archive',public_fixture())
    case=publish(root/'case.json',dict(case=counts.PLAN['case'],study_plan_sha256=payload_hash(counts.PLAN),
        discovered_at_utc=counts.PLAN['discovery'],raw_bundle=public_fixture(),spec=spec))
    def checkpoint(result):
        return study.publish_acquisition_checkpoint(root,case,result,witness,dict(pid=os.getpid()),'test.boot')
    return clock,spec,witness,conn,invoke,checkpoint,case


class PublicFaultPublicationTests(unittest.TestCase):
    def test_declared_policy_hashes(self):
        self.assertEqual(payload_hash(capture.NOTICE_POLICY),'6dec039e13620846ed83b0850d0d36a83325cb5afbf87372742359b7cd70bceb')
        self.assertEqual(payload_hash(capture.PUBLICATION_POLICY),'9b07b4ecfa5c2c9a186e8f6a9bcb2e25fc2a890aeac98a65579de83a7d5a0f0e')

    def test_notice_shape_and_foreign_data_are_distinct(self):
        with TemporaryDirectory() as d:
            _,spec,_,_,_,_,_=setup(Path(d))
            self.assertFalse(capture.contamination(json.dumps(notice()),spec))
            for count in (1,2,64,65):
                assets=[str(20000+i) for i in range(count)]
                value=dict(notice(),assets_ids=assets,clob_token_ids=assets,outcomes=[str(i) for i in range(count)])
                self.assertEqual(capture.creation_notice(value,spec),2<=count<=64)
                self.assertEqual(capture.contamination(json.dumps(value),spec),not 2<=count<=64)
            selected=dict(notice(),market=spec['condition_id'],condition_id=spec['condition_id'],
                assets_ids=list(spec['asset_ids']),clob_token_ids=list(spec['asset_ids']))
            self.assertTrue(capture.creation_notice(selected,spec))
            for change in ({'event_type':'book'},{'event_type':'last_trade_price'},
                {'event_type':'market_resolved'},{'event_type':'unknown'},
                {'price_changes':[]},{'bids':[]},{'asset_id':'20001'},
                {'condition_id':'0x'+'b'*64},{'assets_ids':['10001','20001']},
                {'clob_token_ids':['20002','20001']},{'assets_ids':['20001','20001']},
                {'assets_ids':None},{'assets_ids':['２０００１','２０００２']},{'outcomes':['Over']},{'payload':{'event_type':'book'}}):
                with self.subTest(change=change):
                    value=dict(notice(),**change)
                    self.assertTrue(capture.contamination(json.dumps(value),spec))
            self.assertTrue(capture.contamination(json.dumps([notice(),dict(event_type='book',asset_id='foreign')]),spec))
            self.assertFalse(capture.contamination('{malformed',spec))

    def test_notice_retained_once_and_does_not_end_capture_or_make_book_state(self):
        from infra.stream.recorder_case_archive import archive_frames
        with TemporaryDirectory() as d:
            root=Path(d);_,_,witness,conn,invoke,checkpoint,_=setup(root)
            original=conn.recv;first=[True];raw=json.dumps(notice())
            def receive(timeout):
                if first[0]:first[0]=False;return raw
                return original(timeout)
            conn.recv=receive
            result=invoke(before_close=checkpoint)
            self.assertIsNone(result['error']);self.assertTrue(result['close_completed'])
            self.assertTrue(capture.normal_completion_proven(result))
            texts=archive_frames(root/'archive',result['summary']['frames'])[0]
            self.assertEqual(texts.count(raw),1)
            self.assertEqual(result['summary']['book_snapshot_assets_by_connection'],{'1':[]})
            verified=verify_completion(json.loads((root/'completion.json').read_text()),root/'archive',expected_domain='test.boot')
            self.assertEqual(verified['frames'],len(texts))
            self.assertTrue(witness.closed)

    def test_actual_close_sees_sealed_archive_and_checkpoint_even_on_early_fault(self):
        with TemporaryDirectory() as d:
            root=Path(d);_,_,_,conn,invoke,checkpoint,_=setup(root)
            conn.recv=lambda timeout:'{"asset_id":"foreign"}'
            def close():
                self.assertTrue((root/'archive/manifest.json').is_file())
                c=json.loads((root/'acquisition-checkpoint.json').read_text())
                self.assertFalse(c['close_verified']);self.assertFalse(c['result']['close_completed'])
                self.assertIsNone(c['result']['closed']);self.assertIn('foreign',c['result']['error'])
                self.assertEqual(study.report(root)['population'],1)
                self.assertTrue(all(x['coverage']!='recorded' for x in study.report(root)['rows']))
                raise OSError('close fault retained')
            conn.close=close
            result=invoke(before_close=checkpoint)
            self.assertIn('foreign',result['error']);self.assertIn('close fault retained',result['close_errors'][0])
            self.assertFalse(result['close_completed']);self.assertFalse(capture.normal_completion_proven(result))

    def test_checkpoint_never_establishes_full_coverage_even_after_normal_acquisition(self):
        with TemporaryDirectory() as d:
            root=Path(d);_,_,_,_,invoke,checkpoint,case=setup(root)
            result=invoke(before_close=checkpoint)
            value=study.report(root)
            self.assertFalse(value['close_verified']);self.assertFalse(value['final_consumer_present'])
            self.assertTrue(all(x['coverage']!='recorded' for x in value['rows']))
            publish(root/'consumer.json',dict(case_sha256=case['artifact_sha256'],result=result,
                epoch_ns=result['epoch_ns'],domain='test.boot',identity=dict(pid=os.getpid()),
                error=None,observer_thread_alive=False))
            self.assertTrue(all(x['coverage']=='recorded' for x in study.report(root)['rows']))

    def test_publication_failure_is_retained_and_never_retried(self):
        for failed in ('completion','checkpoint'):
            with self.subTest(failed=failed),TemporaryDirectory() as d:
                root=Path(d);_,_,w,_,invoke,checkpoint,_=setup(root)
                target='exclusive_json' if failed=='completion' else 'publish'
                with patch.object(study,target,side_effect=OSError('publication fault')) as called:
                    result=invoke(before_close=checkpoint)
                self.assertEqual(called.call_count,1);self.assertIn('publication fault',result['error'])
                self.assertTrue(w.closed);self.assertFalse((root/'acquisition-checkpoint.json').exists())
                self.assertIsNone(study.report(root)['population'])

    def test_malformed_or_mutated_checkpoint_linkage_is_not_accepted(self):
        for mutation in ('case','epoch','close','policy','hash','completion','final','final_symlink'):
            with self.subTest(mutation=mutation),TemporaryDirectory() as d:
                root=Path(d);_,_,_,_,invoke,checkpoint,_=setup(root);invoke(before_close=checkpoint)
                p=root/'acquisition-checkpoint.json';v=json.loads(p.read_text())
                if mutation=='case':v['case_sha256']='x'*64
                if mutation=='epoch':v['epoch_ns']+=1
                if mutation=='close':v['close_verified']=True
                if mutation=='policy':v['result']['publication_policy_sha256']='x'*64
                if mutation=='completion':(root/'completion.json').unlink()
                if mutation=='final':(root/'consumer.json').write_text('{malformed')
                if mutation=='final_symlink':(root/'consumer.json').symlink_to(root/'absent-final')
                if mutation!='hash':v['artifact_sha256']=payload_hash({k:x for k,x in v.items() if k!='artifact_sha256'})
                else:v['artifact_sha256']='x'*64
                p.write_text(json.dumps(v));report=study.report(root)
                self.assertTrue(all(x['coverage']!='recorded' for x in report['rows']))
                if mutation!='completion':self.assertIsNone(report['population'])

    def test_real_process_close_guard_leaves_early_fault_publication_intact(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            program=('import time;from pathlib import Path;'
                'from tests.test_public_fault_publication import setup;'
                'from infra.stream.recorder_public_capture import ConnectDeadline;'
                'root=Path('+repr(d)+');'
                'clock,spec,w,conn,invoke,checkpoint,case=setup(root);'
                'conn.recv=lambda timeout:\'{"asset_id":"foreign"}\';'
                'conn.close=lambda:time.sleep(30);'
                'invoke(before_close=checkpoint,connect_guard_factory=ConnectDeadline)')
            result=subprocess.run([sys.executable,'-c',program],capture_output=True,timeout=8)
            self.assertEqual(result.returncode,-signal.SIGTERM,result.stderr)
            c=json.loads((root/'acquisition-checkpoint.json').read_text())
            self.assertIn('foreign',c['result']['error']);self.assertIsNone(c['result']['closed'])
            self.assertFalse(c['close_verified']);self.assertFalse((root/'consumer.json').exists())
            self.assertEqual(verify_completion(json.loads((root/'completion.json').read_text()),root/'archive',expected_domain='test.boot')['frames'],1)
            value=study.report(root);self.assertEqual(value['population'],1)
            self.assertTrue(all(x['coverage']!='recorded' for x in value['rows']))

    def test_actual_production_consume_wiring_publishes_once_before_close(self):
        from contextlib import ExitStack
        from types import SimpleNamespace
        from datetime import timedelta
        for early_fault in (False,True):
            with self.subTest(early_fault=early_fault),TemporaryDirectory() as d,ExitStack() as stack:
                root=Path(d)/'evidence';root.mkdir()
                clock,spec,_,conn,_,_,_=setup(root)
                if early_fault:conn.recv=lambda timeout:'{"asset_id":"foreign"}'
                approval=publish(Path(d)/'operator-approval.json',dict(case=counts.PLAN['case'],one_case_only=True))
                frozen=dict(study_plan=counts.PLAN,study_plan_sha256=payload_hash(counts.PLAN),
                    sources={},operator_approval_sha256=approval['artifact_sha256'],boot_id='test.boot')
                frozen['freeze_sha256']=payload_hash(frozen)
                (root/'case.json').unlink()
                case=publish(root/'case.json',dict(case=counts.PLAN['case'],study_plan_sha256=payload_hash(counts.PLAN),
                    discovered_at_utc=counts.PLAN['discovery'],raw_bundle=public_fixture(),spec=spec,freeze_sha256=frozen['freeze_sha256']))
                publish(Path(d)/'case-lock.json',dict(case_sha256=case['artifact_sha256'],freeze_sha256=frozen['freeze_sha256'],locked_at_utc=counts.PLAN['discovery']))
                identity=dict(pid=os.getpid(),boot_id='test.boot')
                publish(root/'release.json',dict(case_sha256=case['artifact_sha256'],identity=identity,epoch_ns=20000000000,at=0))
                wall=lambda:counts.utc(counts.PLAN['arm'])+timedelta(seconds=clock.seconds)
                stack.enter_context(patch.object(study.platform,'system',return_value='Linux'))
                stack.enter_context(patch.object(sys,'executable',study.PYTHON))
                stack.enter_context(patch.object(study,'utc_now',wall))
                stack.enter_context(patch.object(study.time,'monotonic',clock.mono))
                stack.enter_context(patch.object(study,'LinuxReader',return_value=SimpleNamespace(expected=identity,read=lambda **k:{})))
                stack.enter_context(patch.object(study,'StorageGuard',return_value=SimpleNamespace(check=lambda:None)))
                stack.enter_context(patch.object(study,'observe_absolute',return_value={}))
                stack.enter_context(patch('infra.stream.recorder_public_operator.pinned_tls',return_value=object()))
                def collecting(*args,**kwargs):
                    return capture.collect(*args,**kwargs,clock=wall,monotonic=clock.mono,connect_factory=lambda *a,**k:conn,
                        interrupt_factory=fixtures.DummyInterrupt,connect_guard_factory=fixtures.DummyInterrupt)
                stack.enter_context(patch.object(study,'collect',side_effect=collecting))
                def close():
                    self.assertTrue((root/'completion.json').exists())
                    self.assertTrue((root/'acquisition-checkpoint.json').exists())
                    self.assertFalse((root/'consumer.json').exists())
                conn.close=close
                study.consume(root.resolve(),frozen,execute=True)
                consumer=json.loads((root/'consumer.json').read_text())
                self.assertTrue(consumer['result']['close_completed'])
                self.assertFalse((root/'completion-error.json').exists())
                self.assertEqual(study.report(root)['close_verified'],True)
                if early_fault:self.assertIn('foreign',consumer['result']['error'])
                else:self.assertTrue(all(x['coverage']=='recorded' for x in study.report(root)['rows']))

    def test_process_guard_callback_wins_cancellation_and_cannot_become_success(self):
        for phase in ('acquisition','close'):
            with self.subTest(phase=phase),TemporaryDirectory() as d,patch.object(capture.os,'kill') as kill:
                root=Path(d);_,_,_,conn,invoke,checkpoint,_=setup(root);guards=[]
                def guard(*args,**kwargs):
                    value=capture.ConnectDeadline(*args,**kwargs);guards.append(value);return value
                def publishing(value):
                    checkpoint(value)
                    if phase=='acquisition':guards[0].interrupt()
                def close():
                    if phase=='close':guards[-1].interrupt()
                conn.close=close
                result=invoke(before_close=publishing,connect_guard_factory=guard)
                kill.assert_called_once_with(os.getpid(),signal.SIGTERM)
                self.assertIn('process guard fired',result['error'])
                self.assertTrue(guards[0 if phase=='acquisition' else -1].fired.is_set())
                if phase=='close':self.assertFalse(result['close_completed'])
                self.assertFalse(study.report(root)['close_verified'])
