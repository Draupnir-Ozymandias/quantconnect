"""Explicit v6 operator/consumer/report wiring, using local fixtures only."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError,payload_hash
from execution_truth.market_stream import stream_plan
from infra.stream import recorder_public_counts as counts,recorder_public_study as study
from infra.stream import recorder_public_capture as capture,recorder_public_operator as operator
from infra.stream.recorder_persistence_worker import publish
from tests.test_public_recovery import Harness,closed
from tests.test_taker_replay import raw_bundle,revise
from tests.test_recorder_public_study import DummyInterrupt

PLAN=counts.SUCCESSOR_V6_PLAN


def public_raw():
    from execution_truth.rolling_stream import SOURCE,DESCRIPTION
    raw=raw_bundle();start=int(counts.utc(PLAN['event_start']).timestamp())
    revise(raw,'gamma_market',startDate='2026-10-16T16:00:00Z',eventStartTime=PLAN['event_start'],
        endDate=PLAN['event_end'],slug='btc-updown-5m-'+str(start),description=DESCRIPTION,resolutionSource=SOURCE)
    return raw


def make_case(root,**extra):
    raw=public_raw()
    return publish(root/'case.json',dict(case=PLAN['case'],study_plan_sha256=payload_hash(PLAN),
        discovered_at_utc=PLAN['discovery'],raw_bundle=raw,
        spec=stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000,resilient=True),**extra))


class V6Tests(unittest.TestCase):
    def test_literal_plan_identities_explicit_selection_and_limits(self):
        self.assertEqual(payload_hash(counts.PLAN),'8f36b9350255135ad18445fe602677d3fb6600844f2a546a6c9ecff2414568c9')
        self.assertEqual(payload_hash(PLAN),'6b4d7c4943523e025b645b0f0677e0b7d43e3c11ee1c82624176750ab0e2752c')
        self.assertEqual(counts.version_plan('v5'),counts.PLAN)
        self.assertEqual(counts.version_plan('v6'),PLAN)
        for key in ('unit','seconds','tail_seconds','acquisition_seconds','frame_cap','completion_cap_bytes','spool_cap_bytes'):
            self.assertEqual(PLAN[key],counts.PLAN[key])
        self.assertEqual((PLAN['connection_attempts'],PLAN['reconnects']),(3,2))
        bad=deepcopy(PLAN);bad['reconnects']=3
        with self.assertRaises(ContractError):counts.supported_plan(bad)
        with self.assertRaises(ContractError):counts.version_plan('v8')
        self.assertEqual(counts.epoch_ns(1.,'2026-10-21T16:00:40Z',1.,study_plan=PLAN),21_000_000_000)
        self.assertEqual(operator.layout(PLAN),('/var/lib/qcrl-stream/public-feed-20261021T160000Z','qcrl-public-counts-20261021T160000Z'))
        props=operator.properties(PLAN)
        self.assertTrue(props['ReadWritePaths'].endswith('20261021T160000Z/evidence'))

    def test_discovery_produces_only_selected_recovery_case_and_refuses_v5_adoption(self):
        class Acquirer:
            def __init__(self,**kw):assert kw['transport'].plan==PLAN
            def resolve_market_slug(self,slug,kind):return dict(resolved_market_id='123456')
            def acquire_market_bundle(self,value):return public_raw()
        with TemporaryDirectory() as d,patch.object(operator,'pinned_tls',return_value=None):
            root=Path(d)
            case=operator.discover(root,dict(freeze_sha256='0'*64),execute=True,
                clock=lambda:counts.utc(PLAN['discovery']),acquirer_factory=Acquirer,study_plan=PLAN)
            study.validate_case(case,study_plan=PLAN)
            self.assertIn('resilience',case['spec'])
            with self.assertRaises(ContractError):study.validate_case(case)
            with self.assertRaises(FileExistsError):operator.discover(root,{},execute=True,
                clock=lambda:counts.utc(PLAN['discovery']),study_plan=PLAN)

    def test_consume_and_final_or_checkpoint_report_use_actual_recovery_path(self):
        for mode in ('normal','reconnect','foreign','missing_final','missing_completion','corrupt_epochs','corrupt_final','missing_archive'):
            with self.subTest(mode=mode),TemporaryDirectory() as d,ExitStack() as stack:
                root=Path(d)/'evidence';root.mkdir();h=Harness(root/'archive')
                approval=publish(Path(d)/'operator-approval.json',dict(case=PLAN['case'],one_case_only=True))
                frozen=dict(study_plan=PLAN,study_plan_sha256=payload_hash(PLAN),sources={},
                    operator_approval_sha256=approval['artifact_sha256'],boot_id='test.boot')
                frozen['freeze_sha256']=payload_hash(frozen)
                case=make_case(root,freeze_sha256=frozen['freeze_sha256'])
                identity=dict(pid=os.getpid(),boot_id='test.boot')
                publish(Path(d)/'case-lock.json',dict(case_sha256=case['artifact_sha256'],
                    freeze_sha256=frozen['freeze_sha256'],locked_at_utc=PLAN['discovery']))
                publish(root/'release.json',dict(case_sha256=case['artifact_sha256'],identity=identity,epoch_ns=20_000_000_000,at=0))
                wall=lambda:counts.utc(PLAN['arm'])+timedelta(seconds=h.clock.seconds)
                h.raw=case['raw_bundle'];h.spec=case['spec'];h.clock.base=counts.utc(PLAN['arm'])
                if mode=='foreign':h.scripts=[dict(recv=lambda c,t,h:h.event(asset_id='foreign'))]
                if mode=='reconnect':
                    h.scripts=[dict(recv=lambda *args:(_ for _ in ()).throw(closed())),{}]
                stack.enter_context(patch.object(study.platform,'system',return_value='Linux'))
                stack.enter_context(patch.object(sys,'executable',study.PYTHON))
                stack.enter_context(patch.object(study,'utc_now',wall))
                stack.enter_context(patch.object(study.time,'monotonic',h.clock.mono))
                stack.enter_context(patch.object(study,'LinuxReader',return_value=SimpleNamespace(expected=identity,read=lambda **k:{})))
                stack.enter_context(patch.object(study,'StorageGuard',return_value=SimpleNamespace(check=lambda:None)))
                stack.enter_context(patch.object(study,'observe_absolute',return_value={}))
                stack.enter_context(patch.object(operator,'pinned_tls',return_value=object()))
                def collecting(*args,**kwargs):
                    self.assertEqual(payload_hash(kwargs['recovery_policy']),PLAN['recovery_policy_sha256'])
                    return capture.collect(*args,**kwargs,clock=wall,monotonic=h.clock.mono,connect_factory=h.connect,
                        pause=h.clock.pause,uniform=lambda a,b:a,interrupt_factory=DummyInterrupt,connect_guard_factory=DummyInterrupt)
                stack.enter_context(patch.object(study,'collect',side_effect=collecting))
                study.consume(root.resolve(),frozen,execute=True)
                consumer=json.loads((root/'consumer.json').read_text())
                self.assertIsNone(consumer['error']);self.assertIn('connection_epochs',consumer['result'])
                if mode=='missing_final':(root/'consumer.json').unlink()
                if mode=='missing_completion':(root/'completion.json').unlink()
                if mode=='corrupt_final':(root/'consumer.json').write_text('{bad')
                if mode=='missing_archive':(root/'archive/segment-000000.gz').unlink()
                if mode=='corrupt_epochs':
                    consumer['result']['connection_epochs'][0]['eligible_after']=0
                    consumer['artifact_sha256']=payload_hash({k:v for k,v in consumer.items() if k!='artifact_sha256'})
                    (root/'consumer.json').write_text(json.dumps(consumer))
                value=study.report(root,study_plan=PLAN)
                self.assertEqual(len(value['rows']),60);self.assertNotIn('verdict',value)
                self.assertTrue(all('eligible_lower' in x and 'eligible_upper_archived' in x for x in value['rows']))
                self.assertTrue(all(x['feed_activity_upper'] is None for x in value['rows']))
                if mode in ('corrupt_final','missing_archive'):
                    self.assertIsNone(value['population']);self.assertTrue(all(x['lower'] is None for x in value['rows']));continue
                if mode=='missing_completion':
                    self.assertIn('error',value['archive_linkage']);continue
                self.assertEqual(value['study_plan_sha256'],payload_hash(PLAN))
                if mode=='corrupt_epochs':
                    self.assertIn('error',value['recovery_linkage'])
                    self.assertTrue(all(x['eligible_lower'] is None for x in value['rows']));continue
                self.assertNotIn('recovery_linkage',value)
                self.assertTrue(value['archive_linkage']['completion_linkage_verified'])
                self.assertEqual(value['final_consumer_present'],mode!='missing_final')
                self.assertEqual(value['close_verified'],mode!='missing_final')
                self.assertFalse(value['coverage_complete'])
                if mode=='foreign':self.assertIn('foreign',consumer['result']['error'])
                if mode=='reconnect':self.assertEqual(h.calls,2)

    def test_unit_command_selects_version_and_never_reuses_v5_namespace(self):
        from infra.stream.recorder_public_operator import Production
        ops=object.__new__(Production);ops.plan=PLAN;ops.stage,ops.unit=operator.layout(PLAN)
        ops.root=Path(ops.stage);ops.evidence=ops.root/'evidence';ops.submission_attempted=False
        calls=[]
        def command(args,**kw):calls.append(args);return ''
        with patch.object(operator,'utc_now',return_value=counts.utc(PLAN['arm'])),patch.object(operator,'command',side_effect=command):ops.start()
        cmd=calls[-1]
        self.assertIn('--unit='+ops.unit,cmd)
        self.assertEqual(cmd[cmd.index('--study-version')+1],'v6')
        self.assertTrue(ops.submission_attempted)
        self.assertNotEqual(ops.unit,operator.UNIT)

    def test_wrong_cli_version_stops_before_consumer(self):
        with TemporaryDirectory() as d:
            root=Path(d)/'evidence';root.mkdir()
            (Path(d)/'execution-freeze.json').write_text(json.dumps(dict(study_plan=PLAN)))
            with patch.object(sys,'argv',['study','consume','--root',str(root),'--execute']),patch.object(study,'consume') as run:
                with self.assertRaisesRegex(ContractError,'CLI study version'):study.main()
                run.assert_not_called()

    def test_controller_rejects_cross_plan_freeze_before_claim(self):
        with TemporaryDirectory() as d:
            root=Path(d).resolve();(root/'source').mkdir()
            frozen=dict(freeze_sha256='0'*64,study_plan=counts.PLAN,study_plan_sha256=payload_hash(counts.PLAN))
            (root/'execution-freeze.json').write_text(json.dumps(frozen))
            with patch.object(operator,'layout',return_value=(str(root),'unused-v6-test')),\
                 patch.object(operator,'ROOT',root/'source'),patch.object(operator.platform,'system',return_value='Linux'),\
                 patch.object(operator.os,'geteuid',return_value=0),patch.object(sys,'executable',operator.PYTHON),\
                 patch.object(operator,'utc_now',return_value=counts.utc(PLAN['discovery'])-timedelta(minutes=5)):
                with self.assertRaisesRegex(ContractError,'freeze/selected plan'):
                    operator.Production(root,'0'*64,execute=True,study_plan=PLAN)
            self.assertFalse((root/'controller-claim.json').exists())

    def test_metadata_cli_rejects_cross_plan_before_any_request(self):
        with TemporaryDirectory() as d:
            root=Path(d).resolve();(root/'source').mkdir()
            frozen=dict(study_plan=counts.PLAN,study_plan_sha256=payload_hash(counts.PLAN))
            frozen['freeze_sha256']=payload_hash(frozen)
            (root/'execution-freeze.json').write_text(json.dumps(frozen))
            args=['operator','metadata','--root',str(root),'--freeze-sha256',frozen['freeze_sha256'],'--study-version','v6','--execute']
            with patch.object(sys,'argv',args),patch.object(operator,'layout',return_value=(str(root),'unused')),                 patch.object(operator,'ROOT',root/'source'),patch.object(operator.platform,'system',return_value='Linux'),\
                 patch.object(sys,'executable',operator.PYTHON),patch.object(operator,'discover') as discover:
                with self.assertRaisesRegex(ContractError,'freeze/selected plan'):operator.main()
                discover.assert_not_called()


    def test_real_metadata_path_gate_uses_v6_slug_and_rejects_expired_v5_slug(self):
        from io import BytesIO
        class Response(BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        with TemporaryDirectory() as d:
            root=Path(d);transport=operator.MetadataTransport(root,study_plan=PLAN)
            old_slug='btc-updown-5m-'+str(int(counts.utc(counts.PLAN['event_start']).timestamp()))
            new_slug='btc-updown-5m-'+str(int(counts.utc(PLAN['event_start']).timestamp()))
            with self.assertRaisesRegex(ContractError,'path differs'):
                transport.get_json('https://gamma-api.polymarket.com/markets/slug/'+old_slug)
            self.assertEqual(transport.requests,0)
            transport.opener=SimpleNamespace(open=lambda *a,**k:Response(b'{}'))
            self.assertEqual(transport.get_json('https://gamma-api.polymarket.com/markets/slug/'+new_slug),{})
            self.assertEqual(transport.requests,1)
            self.assertTrue((root/'request-1.json').exists())
