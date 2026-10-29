"""BTC20 actual runtime paths with local virtual transport/clocks only."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError,payload_hash
from execution_truth.market_stream import stream_plan
from infra.stream import recorder_public_counts as counts,recorder_public_capture as capture
from infra.stream import recorder_public_study as study,recorder_public_operator as operator
from infra.stream import recorder_phase_quotas as quota
from infra.stream import recorder_exited_unit as exited
from infra.stream.recorder_persistence_worker import publish
from infra.stream.recorder_completion import verify_completion
from tests.test_public_recovery import Harness,closed
from tests.test_recorder_public_study import DummyInterrupt
from tests.test_taker_replay import revise

PLAN=counts.SUCCESSOR_V7_PLAN


def run(h, **kwargs):
    return h.run(study_plan=PLAN,**kwargs)


class AllocationTests(unittest.TestCase):
    def test_literal_policies_old_plans_and_new_dimensions(self):
        self.assertEqual(payload_hash(quota.POLICY),'a19febf2bbf1824f11d3bdb4c464e085b62f89ce8831375ffc922f374e8df033')
        self.assertEqual(payload_hash(exited.PUBLIC_POLICY),PLAN['exited_unit_policy_sha256'])
        self.assertEqual(payload_hash(counts.PLAN),'8f36b9350255135ad18445fe602677d3fb6600844f2a546a6c9ecff2414568c9')
        self.assertEqual(payload_hash(counts.SUCCESSOR_V6_PLAN),'6b4d7c4943523e025b645b0f0677e0b7d43e3c11ee1c82624176750ab0e2752c')
        self.assertEqual(counts.version_plan('v7'),PLAN)
        self.assertEqual(payload_hash(PLAN),'eaaf6bfa25d0b00fd7985506dfb877680342397a0d47b1f31dfcdb68a3d09049')
        self.assertEqual((PLAN['seconds'],PLAN['tail_seconds'],PLAN['frame_cap']),(20,2,60000))
        self.assertEqual(sum(quota.POLICY['frames'].values()),60000)
        self.assertEqual(sum(quota.POLICY['bytes'].values())+3*quota.POLICY['record_cap_bytes']+quota.POLICY['terminal_bytes'],212*1024**2)

    def test_exact_phase_edges_and_one_charge_for_straddling_interval(self):
        a=quota.Allocations(20_000_000_000)
        for at,phase in ((19.999,'prewindow'),(20.,'primary'),(39.999,'primary'),(40.,'tail')):
            self.assertEqual(a.phase(at),phase)
        # The after endpoint does not change allocation of a spanning return.
        before,after=19.999,20.001;a.receive(a.phase(before))
        self.assertEqual(a.frames,dict(prewindow=1,primary=0,tail=0))
        f=dict(sequence=0,returned=dict(before=before,after=after))
        v=counts.bins([f],20_000_000_000,study_plan=PLAN)
        self.assertEqual(v['rows'][0]['lower'],0);self.assertEqual(v['rows'][0]['upper_archived'],1)
        self.assertEqual(len(v['rows']),20)
        self.assertFalse(v['venue_completeness_proven'])

    def test_frame_and_byte_exact_boundaries_and_terminal_hard_limit(self):
        for phase,limit in quota.POLICY['frames'].items():
            a=quota.Allocations(0);a.frames[phase]=limit-2
            a.receive(phase);self.assertIsNone(a.stop)
            a.receive(phase);self.assertEqual(a.stop,phase+'_frame_limit')
        for phase,limit in quota.POLICY['bytes'].items():
            a=quota.Allocations(0);a.written(phase,limit-1);self.assertIsNone(a.stop)
            a.written(phase,1);self.assertEqual(a.stop,phase+'_byte_limit')
        a=quota.Allocations(0);a.terminal=quota.POLICY['terminal_bytes']-1
        a.admit('terminal',1);a.written('terminal',1)
        with self.assertRaises(quota.QuotaStop):a.admit('terminal',1)
        with self.assertRaises(quota.QuotaStop):a.admit('primary',4*1024**2+1)

    def test_short_collector_and_recomputed_allocations(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a');h.clock.seconds=15
            r=run(h);v=self.describe(h)
            self.assertEqual(h.clock.seconds,42)
            self.assertEqual(r['summary']['status'],'scheduled_stop')
            self.assertEqual(len(v['rows']),20)
            self.assertTrue(v['normal_acquisition_end_proven'])
            self.assertLess(v['eligible_population'],v['population'])
            q=quota.verify_archive_allocations(r,h.completion,h.root)
            self.assertEqual(q['received_occurrences'],q['archived_occurrences'])
            self.assertGreater(q['phase_frames']['prewindow'],0)
            self.assertGreater(q['phase_frames']['tail'],0)
            self.assertFalse(v['venue_completeness_proven']);self.assertFalse(v['coverage_complete'])

    @staticmethod
    def describe(h):
        from infra.stream.recorder_public_recovery import describe_archive
        return describe_archive(h.result,h.completion,h.root,expected_domain='test.recovery',study_plan=PLAN)

    def test_reconnect_and_bootstrap_do_not_reset_or_bypass_allocation(self):
        def first(c,t,h):
            if c.n<=2:h.clock.pause(.01);return h.event(h.spec['asset_ids'][c.n-1])
            raise closed()
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=first),{}]);h.clock.seconds=15
            r=run(h);v=self.describe(h);q=quota.verify_archive_allocations(r,h.completion,h.root)
            self.assertEqual(h.calls,2);self.assertIn('ConnectionClosedError',r['error'])
            self.assertEqual(q['received_occurrences'],len(h.completion['frames']))
            self.assertGreaterEqual(q['phase_frames']['prewindow'],4)
            self.assertFalse(q['counters_reset']);self.assertLess(v['eligible_population'],v['population'])
            self.assertIsNone(v['full_minute_feed_population'])

    def test_returned_oversize_text_retained_then_fatal_without_reconnect(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=lambda *a:'x'*262145)]);h.clock.seconds=15
            r=run(h);q=r['phase_allocations']
            self.assertEqual(h.calls,1);self.assertIn('oversize',r['error'])
            self.assertEqual((q['received_occurrences'],q['archived_occurrences']),(1,1))
            self.assertIsNone(q['unarchived_occurrence'])
            quota.verify_archive_allocations(r,h.completion,h.root)

    def test_binary_unarchived_receipt_is_explicit_and_completion_unresolved(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=lambda *a:b'bad')]);h.clock.seconds=15
            r=run(h);q=r['phase_allocations']
            self.assertEqual((q['received_occurrences'],q['archived_occurrences']),(1,0))
            self.assertEqual(q['unarchived_occurrence']['phase'],'prewindow')
            self.assertIn('binary',q['unarchived_occurrence']['reason'])
            self.assertIsNotNone(h.completion['unlinked_return'])
            with self.assertRaises(ContractError):verify_completion(h.completion,h.root,expected_domain='test.recovery')

    def test_append_storage_failure_discloses_triggering_occurrence(self):
        original=capture.AllocatedLog.append
        def fail(log,kind,payload):
            if kind=='frame':raise OSError('injected disk full')
            return original(log,kind,payload)
        with TemporaryDirectory() as d,patch.object(capture.AllocatedLog,'append',fail):
            h=Harness(Path(d)/'a');h.clock.seconds=15;r=run(h)
            q=r['phase_allocations'];self.assertEqual(q['received_occurrences'],1)
            self.assertEqual(q['archived_occurrences'],0)
            self.assertIn('disk full',q['unarchived_occurrence']['reason'])
            self.assertIsNotNone(q['unarchived_occurrence']['raw_sha256'])

    def test_byte_trigger_is_archived_then_censors_without_next_receive(self):
        # Seed a real writer's already-charged bytes, not a reduced production policy.
        original=capture.AllocatedLog.append
        def near(log,kind,payload):
            if kind=='frame' and log.allocations.received==1:
                log.allocations.bytes['prewindow']=quota.POLICY['bytes']['prewindow']-1
            return original(log,kind,payload)
        with TemporaryDirectory() as d,patch.object(capture.AllocatedLog,'append',near):
            h=Harness(Path(d)/'a');h.clock.seconds=15;r=run(h)
            q=r['phase_allocations'];self.assertEqual(q['archived_occurrences'],1)
            self.assertEqual(q['received_occurrences'],1)
            self.assertEqual(r['summary']['status'],'phase_limit')
            self.assertEqual(q['stop_reason'],'prewindow_byte_limit')
            self.assertFalse(r['connection_epochs'][0]['normal'])

    def test_real_encoded_byte_budget_retains_crossing_text(self):
        def incoming(c,t,h):
            if c.n<=2:return h.event(h.spec['asset_ids'][c.n-1])
            return 'x'*262144
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=incoming)]);h.clock.seconds=15;r=run(h)
            q=quota.verify_archive_allocations(r,h.completion,h.root)
            self.assertEqual(q['stop_reason'],'prewindow_byte_limit')
            self.assertEqual(q['received_occurrences'],q['archived_occurrences'])
            self.assertGreaterEqual(q['phase_encoded_bytes']['prewindow'],32*1024**2)
            self.assertLess(q['phase_encoded_bytes']['prewindow'],36*1024**2)
            self.assertEqual(q['phase_frames']['primary'],0)

    def test_oversize_encoding_above_record_ceiling_disclosed_not_dropped_silently(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=lambda *a:'\x00'*800000)]);h.clock.seconds=15;r=run(h)
            q=r['phase_allocations'];self.assertEqual((q['received_occurrences'],q['archived_occurrences']),(1,0))
            self.assertEqual(q['unarchived_occurrence']['utf8_bytes'],800000)
            self.assertIn('record exceeds',q['unarchived_occurrence']['reason'])

    def test_tail_frame_ceiling_is_independent_and_trigger_archived(self):
        def incoming(c,t,h):
            if c.n<=2:return h.event(h.spec['asset_ids'][c.n-1])
            h.clock.seconds=40;return 'tail'
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a',[dict(recv=incoming)]);h.clock.seconds=15;r=run(h)
            q=quota.verify_archive_allocations(r,h.completion,h.root)
            self.assertEqual(q['phase_frames'],dict(prewindow=2,primary=0,tail=2000))
            self.assertEqual(q['archived_occurrences'],2002)
            self.assertEqual(q['stop_reason'],'tail_frame_limit')

    def test_actual_return_bracket_spanning_m0_charges_prewindow_once(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a');h.clock.seconds=15
            def first(c,t,h):
                if c.n==1:h.clock.seconds=19.999;return h.event(h.spec['asset_ids'][0])
                h.clock.pause(t)
                return h.event(h.spec['asset_ids'][1])
            h.scripts=[dict(recv=first)]
            utc=h.clock.utc
            def crossing():
                value=utc()
                if h.clock.seconds==19.999:h.clock.pause(.002)
                return value
            h.witness.clock=crossing
            r=run(h,clock=crossing)
            self.assertEqual(r['phase_allocations']['phase_frames']['prewindow'],1)
            self.assertLess(h.completion['frames'][0]['returned']['before'],20)
            self.assertGreater(h.completion['frames'][0]['returned']['after'],20)

    def test_single_worker_inspector_policy_is_explicit_not_v1_exemption(self):
        from tests.test_recorder_exited_unit import binding,reader
        b=binding();b['processes']=b['processes'][:1]
        with self.assertRaises(ContractError):exited.inspect_exited_unit(b,reader())
        value=exited.inspect_exited_unit(b,reader(),policy=exited.PUBLIC_POLICY)
        self.assertTrue(value['exited_binding_observed']);self.assertFalse(value['stop_authorized'])
        self.assertEqual(value['policy_sha256'],PLAN['exited_unit_policy_sha256'])

    def test_true_storage_guard_uses_selected_ceilings(self):
        with TemporaryDirectory() as d,patch.object(capture.shutil,'disk_usage',return_value=SimpleNamespace(free=2*1024**3)):
            guard=capture.StorageGuard(Path(d),study_plan=PLAN);guard.check()
            with patch.object(capture.shutil,'disk_usage',return_value=SimpleNamespace(free=1024**3)):
                with self.assertRaisesRegex(ContractError,'disk reserve'):guard.check()

    def test_control_byte_exhaustion_stops_before_another_receive(self):
        original=capture.AllocatedLog.append
        def charge(log,kind,payload):
            if kind=='ping_sent':log.allocations.bytes['primary']=quota.POLICY['bytes']['primary']-1
            return original(log,kind,payload)
        with TemporaryDirectory() as d,patch.object(capture.AllocatedLog,'append',charge):
            h=Harness(Path(d)/'a');h.clock.seconds=15;r=run(h)
            self.assertEqual(r['phase_allocations']['stop_reason'],'primary_byte_limit')
            self.assertEqual(r['phase_allocations']['received_occurrences'],h.connections[0].n)
            self.assertEqual(h.clock.seconds,25)

    def test_timing_failure_discloses_unallocated_occurrence(self):
        with TemporaryDirectory() as d:
            h=Harness(Path(d)/'a');h.clock.seconds=15
            h.witness.application_return=lambda *a:h.witness.disable('injected invalid clock')
            r=run(h);q=r['phase_allocations']
            self.assertEqual(q['received_occurrences'],1);self.assertEqual(q['unallocated_occurrences'],1)
            self.assertIsNone(q['unarchived_occurrence']['phase'])
            self.assertIsNone(q['unarchived_occurrence']['returned'])

    def test_full_prewindow_and_primary_caps_in_bounded_separate_processes(self):
        for phase in ('prewindow','primary'):
            code='from tests.test_public_btc20 import stress; stress('+repr(phase)+')'
            child=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=100)
            self.assertEqual(child.returncode,0,child.stderr[-2000:])

    def test_archive_replay_rejects_cross_phase_continuation_after_exhaustion(self):
        # Simulate a faulty collector that suppresses the stop until publication.
        # Every row/hash/receipt is genuine and totals stay within each cap, so
        # the independent verifier must detect ordering, not just final sums.
        written=quota.Allocations.written
        snapshot=quota.Allocations.snapshot
        for mode in ('frame','control'):
            with self.subTest(mode=mode),TemporaryDirectory() as d:
                def incoming(c,t,h):
                    if c.n<=2:return h.event(h.spec['asset_ids'][c.n-1])
                    if c.n<=8000:return 'prewindow'
                    if mode=='frame' and c.n==8001:
                        h.clock.seconds=20
                        return 'forbidden primary continuation'
                    raise RuntimeError('bounded adversarial fixture end')
                h=Harness(Path(d)/'archive',[dict(recv=incoming)])
                h.clock.seconds=15
                def suppress_stop(meter,phase,size):
                    written(meter,phase,size)
                    if meter.stop:
                        meter.saved_stop=meter.stop
                        meter.stop=None
                        if mode=='control':h.clock.seconds=25
                def publish_stop(meter):
                    meter.stop=getattr(meter,'saved_stop',None)
                    return snapshot(meter)
                with patch.object(quota.Allocations,'written',suppress_stop),patch.object(quota.Allocations,'snapshot',publish_stop):
                    result=run(h)
                self.assertEqual(result['phase_allocations']['phase_frames']['prewindow'],8000)
                verify_completion(h.completion,h.root,expected_domain='test.recovery')
                with self.assertRaisesRegex(ContractError,'acquisition record follows phase quota exhaustion'):
                    quota.verify_archive_allocations(result,h.completion,h.root)


class WorkerIntegrationTests(unittest.TestCase):
    def exercise(self,root,mode='normal'):
        from execution_truth.rolling_stream import SOURCE,DESCRIPTION
        h=Harness(root/'archive');h.clock.base=counts.utc(PLAN['arm'])
        revise(h.raw,'gamma_market',startDate='2026-10-16T16:00:00Z',eventStartTime=PLAN['event_start'],
            endDate=PLAN['event_end'],slug='btc-updown-5m-'+str(int(counts.utc(PLAN['event_start']).timestamp())),
            description=DESCRIPTION,resolutionSource=SOURCE)
        h.spec=stream_plan(h.raw,segmented=True,max_seconds=90,max_frames=60000,resilient=True)
        approval=publish(root.parent/'operator-approval.json',dict(case=PLAN['case'],one_case_only=True))
        frozen=dict(study_plan=PLAN,study_plan_sha256=payload_hash(PLAN),sources={},boot_id='test.boot',
            operator_approval_sha256=approval['artifact_sha256'],
            resource_publication_policy_sha256=payload_hash(study.RESOURCE_PUBLICATION_POLICY))
        frozen['freeze_sha256']=payload_hash(frozen)
        case=publish(root/'case.json',dict(case=PLAN['case'],study_plan_sha256=payload_hash(PLAN),
            discovered_at_utc=PLAN['discovery'],raw_bundle=h.raw,spec=h.spec,freeze_sha256=frozen['freeze_sha256']))
        publish(root.parent/'case-lock.json',dict(case_sha256=case['artifact_sha256'],
            freeze_sha256=frozen['freeze_sha256'],locked_at_utc=PLAN['discovery']))
        identity=dict(pid=os.getpid(),boot_id='test.boot',process_start_id='123',cgroup='/fixture')
        publish(root/'release.json',dict(case_sha256=case['artifact_sha256'],identity=identity,epoch_ns=5_000_000_000,at=0))
        wall=lambda:counts.utc(PLAN['arm'])+timedelta(seconds=h.clock.seconds)
        if mode=='binary':h.scripts=[dict(recv=lambda *a:b'bad')]
        with ExitStack() as stack:
            stack.enter_context(patch.object(study.platform,'system',return_value='Linux'))
            stack.enter_context(patch.object(sys,'executable',study.PYTHON))
            stack.enter_context(patch.object(study,'utc_now',wall))
            stack.enter_context(patch.object(study.time,'monotonic',h.clock.mono))
            stack.enter_context(patch.object(study,'LinuxReader',return_value=SimpleNamespace(expected=identity,read=lambda **k:{})))
            stack.enter_context(patch.object(study,'StorageGuard',return_value=SimpleNamespace(check=lambda:None)))
            stack.enter_context(patch.object(study,'observe_absolute',return_value={}))
            stack.enter_context(patch.object(operator,'pinned_tls',return_value=object()))
            def collecting(*args,**kwargs):
                self.assertEqual(kwargs['study_plan'],PLAN)
                return capture.collect(*args,**kwargs,clock=wall,monotonic=h.clock.mono,
                    connect_factory=h.connect,pause=h.clock.pause,uniform=lambda a,b:a,
                    interrupt_factory=DummyInterrupt,connect_guard_factory=DummyInterrupt)
            stack.enter_context(patch.object(study,'collect',side_effect=collecting))
            study.consume(root.resolve(),frozen,execute=True)
        return h

    def test_actual_consume_checkpoint_resource_report_and_short_cpu_unavailable(self):
        for mode in ('normal','checkpoint','missing','bad_quota','binary'):
            with self.subTest(mode=mode),TemporaryDirectory() as d:
                root=Path(d)/'evidence';root.mkdir();h=self.exercise(root,mode)
                if mode in ('checkpoint','missing'):(root/'consumer.json').unlink()
                if mode=='missing':(root/'acquisition-checkpoint.json').unlink()
                if mode=='bad_quota':
                    c=json.loads((root/'consumer.json').read_text());c['result']['phase_allocations']['phase_frames']['primary']+=1
                    c.pop('artifact_sha256');(root/'consumer.json').unlink();publish(root/'consumer.json',c)
                v=study.report(root,study_plan=PLAN)
                self.assertEqual(len(v['rows']),20)
                self.assertIsNone(v['original_60_second_cpu_window'])
                self.assertEqual(v['original_60_second_cpu_window_status'],'unavailable_short_primary_no_prorating')
                self.assertFalse(v['venue_completeness_proven'])
                self.assertTrue(all(x['feed_activity_upper'] is None for x in v['rows']))
                if mode=='missing':self.assertIsNone(v['population']);continue
                if mode=='binary':
                    self.assertEqual(v['received_occurrence_disclosure']['received_occurrences'],1)
                    self.assertIsNotNone(v['received_occurrence_disclosure']['unarchived_occurrence']);continue
                if mode=='bad_quota':
                    self.assertIn('allocation_linkage_error',v)
                    self.assertIsNone(v['eligible_population']);continue
                self.assertIn('verified_phase_allocations',v)
                self.assertNotIn('allocation_linkage_error',v)
                self.assertTrue(v['archive_linkage']['completion_linkage_verified'])
                self.assertLess(v['eligible_population'],v['population'])
                self.assertIsNone(v['preclose_resource_component']['resource_qualification'])

    def test_unit_command_uses_v7_and_new_namespace(self):
        ops=object.__new__(operator.Production);ops.plan=PLAN;ops.stage,ops.unit=operator.layout(PLAN)
        ops.root=Path(ops.stage);ops.evidence=ops.root/'evidence';ops.submission_attempted=False
        calls=[]
        with patch.object(operator,'utc_now',return_value=counts.utc(PLAN['arm'])),patch.object(operator,'command',side_effect=lambda args,**k:calls.append(args) or ''):
            ops.start()
        self.assertEqual(calls[-1][calls[-1].index('--study-version')+1],'v7')
        self.assertIn('20261030T160000Z',ops.unit)

    def test_cleanup_owner_refuses_active_or_foreign_binding_and_retains_unknown_counter(self):
        for mode in ('exited','active','foreign'):
            with self.subTest(mode=mode),TemporaryDirectory() as d:
                ops=object.__new__(operator.Production);ops.plan=PLAN;ops.stage,ops.unit=operator.layout(PLAN)
                ops.root=Path(d);ops.evidence=ops.root/'evidence';ops.evidence.mkdir()
                ops.frozen=dict(freeze_sha256='fixture.freeze')
                case=publish(ops.evidence/'case.json',dict(case=PLAN['case']))
                p=dict(Id=ops.unit+'.service',InvocationID='a'*32,WorkingDirectory=str(operator.ROOT),
                    ExecStart='complete frozen argv',ExecMainStartTimestampMonotonic='123')
                binding=dict(properties=p,boot_id='fixture-boot',cgroup='/system.slice/'+ops.unit+'.service',
                    processes=[dict(pid=11,start_id='101')])
                if mode=='foreign':p['WorkingDirectory']='/foreign'
                publish(ops.root/'unit-invocation.json',dict(binding=binding,case_sha256=case['artifact_sha256'],freeze_sha256='fixture.freeze'))
                props=dict(p,ActiveState='active',SubState='running' if mode=='active' else 'exited',
                    MainPID='11' if mode=='active' else '0',ControlGroup=binding['cgroup'],TasksCurrent='[not set]')
                from unittest.mock import Mock
                reader=Mock(boot=Mock(return_value='fixture-boot'),unit=Mock(return_value=props),
                    process=Mock(return_value=None),group=Mock(return_value=dict(state='removed',members=[])))
                calls=[]
                with patch.object(exited,'LinuxReader',return_value=reader),patch.object(operator,'verify_freeze'),patch.object(operator,'public_state',return_value={}),patch.object(operator,'command',side_effect=lambda args,**k:calls.append(args) or ''):
                    ops.stop_and_seal()
                post=operator.control(ops.root/'post-run-checks.json')
                self.assertEqual(post['exact_exited_unit_stopped'],mode=='exited')
                self.assertEqual(calls,[['systemctl','stop',ops.unit+'.service']] if mode=='exited' else [])
                if mode=='exited':
                    receipt=operator.control(ops.root/'exited-unit-inspection.json')
                    self.assertIsNone(receipt['tasks_current']);self.assertFalse(receipt['stop_authorized'])

    def test_v7_freeze_refuses_implicit_legacy_publication(self):
        with self.assertRaisesRegex(ContractError,'explicit preclose'):
            operator.make_freeze(Path('.'),{},{},{},'approval',study_plan=PLAN)


def stress(phase):
    def incoming(c,t,h):
        if phase=='primary' and c.n==3:h.clock.seconds=20
        if c.n<=2:return h.event(h.spec['asset_ids'][c.n-1])
        return 'x'
    with TemporaryDirectory() as d:
        h=Harness(Path(d)/'a',[dict(recv=incoming)]);h.clock.seconds=15;r=run(h)
        expected=8000 if phase=='prewindow' else 50002
        assert r['summary']['frames']==expected,r
        assert r['summary']['status']=='phase_limit'
        assert r['phase_allocations']['stop_reason']==phase+'_frame_limit'
        assert r['phase_allocations']['received_occurrences']==expected
        quota.verify_archive_allocations(r,h.completion,h.root)


if __name__=='__main__':unittest.main()
