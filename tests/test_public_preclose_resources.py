"""Prospective component publication through the actual worker/recorder paths.

Local fixtures replace Linux resources and public transport; no native acceptance.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_public_study as study, recorder_public_operator as operator
from infra.stream import recorder_public_capture as capture
from infra.stream.recorder_absolute_budget import PLAN as RESOURCE_PLAN
from infra.stream.recorder_persistence_worker import publish, control
from tests.test_public_recovery import Harness
from tests.test_public_v6_integration import PLAN, make_case
from tests.test_recorder_public_study import DummyInterrupt


@contextmanager
def worker(root, *, opted=True, observer=None, on_close=None, guards=None, publish_component=None):
    """Actual consume/collect/archive/report, with deterministic external boundaries."""
    with ExitStack() as stack:
        root=Path(root);root.mkdir()
        h=Harness(root/'archive');h.clock.base=study.utc(PLAN['arm'])
        approval=publish(root.parent/'operator-approval.json',dict(case=PLAN['case'],one_case_only=True))
        frozen=dict(study_plan=PLAN,study_plan_sha256=payload_hash(PLAN),sources={},
            operator_approval_sha256=approval['artifact_sha256'],boot_id='test.boot')
        if opted:frozen['resource_publication_policy_sha256']=payload_hash(study.RESOURCE_PUBLICATION_POLICY)
        frozen['freeze_sha256']=payload_hash(frozen)
        case=make_case(root,freeze_sha256=frozen['freeze_sha256'])
        h.raw=case['raw_bundle'];h.spec=case['spec']
        identity=dict(pid=os.getpid(),boot_id='test.boot',start_ticks=123)
        publish(root.parent/'case-lock.json',dict(case_sha256=case['artifact_sha256'],
            freeze_sha256=frozen['freeze_sha256'],locked_at_utc=PLAN['discovery']))
        publish(root/'release.json',dict(case_sha256=case['artifact_sha256'],identity=identity,epoch_ns=20_000_000_000,at=0))
        wall=lambda:study.utc(PLAN['arm'])+timedelta(seconds=h.clock.seconds)
        stack.enter_context(patch.object(study.platform,'system',return_value='Linux'))
        stack.enter_context(patch.object(sys,'executable',study.PYTHON))
        stack.enter_context(patch.object(study,'utc_now',wall))
        stack.enter_context(patch.object(study.time,'monotonic',h.clock.mono))
        stack.enter_context(patch.object(study,'LinuxReader',return_value=SimpleNamespace(expected=identity,read=lambda **k:{})))
        stack.enter_context(patch.object(study,'StorageGuard',return_value=SimpleNamespace(check=lambda:None)))
        stack.enter_context(patch.object(operator,'pinned_tls',return_value=object()))
        def default_observer(reader,epoch,stop,**kwargs):
            # Empty, explicitly unqualified prefix, not fabricated resource samples.
            return dict(schema_version='qcrl.recorder_absolute_resources.v1',
                plan_sha256=payload_hash(RESOURCE_PLAN),epoch_ns=20_000_000_000,
                capacity=184,rows=[],overflow=False,error='test_empty_prefix')
        stack.enter_context(patch.object(study,'observe_absolute',side_effect=observer or default_observer))
        if publish_component is not None:
            stack.enter_context(patch.object(study,'publish_preclose_resources',side_effect=publish_component))
        def connect(*args,**kwargs):
            conn=h.connect(*args,**kwargs)
            if on_close is not None:conn.close=lambda:on_close(root,conn)
            return conn
        def collecting(*args,**kwargs):
            return capture.collect(*args,**kwargs,clock=wall,monotonic=h.clock.mono,connect_factory=connect,
                pause=h.clock.pause,uniform=lambda a,b:a,interrupt_factory=DummyInterrupt,
                connect_guard_factory=guards or DummyInterrupt)
        stack.enter_context(patch.object(study,'collect',side_effect=collecting))
        yield SimpleNamespace(root=root,h=h,frozen=frozen,case=case,identity=identity,
                              run=lambda:study.consume(root.resolve(),frozen,execute=True))


def run_retained_blocked_close(root, *, executable=None):
    """Exactly one synthetic worker child; caller owns root, lifetime and retention.

    Reuses the production-path regression without TemporaryDirectory cleanup.
    Not a public-study entry point or a substitute for independent native audit.
    """
    root=Path(root)
    if not root.is_dir() or root.is_symlink() or root.resolve()!=root:
        raise ContractError('existing canonical retained root required')
    if any(root.iterdir()):raise ContractError('fresh retained case root required')
    program='''import time
from pathlib import Path
from tests.test_public_preclose_resources import worker
from infra.stream.recorder_public_capture import ConnectDeadline
with worker(Path(ROOT)/'evidence',guards=ConnectDeadline,on_close=lambda *a:time.sleep(30)) as w:
    w.run()
'''.replace('ROOT',repr(str(root)))
    executable=sys.executable if executable is None else executable
    result=subprocess.run([executable,'-c',program],capture_output=True,timeout=10)
    # Frozen child emits no normal output. Bound what is retained on a fault;
    # its pipe allocations remain inside the declared native unit memory limit.
    cap=262144
    (root/'child.stdout').write_bytes(result.stdout[:cap])
    (root/'child.stderr').write_bytes(result.stderr[:cap])
    outputs_within_cap=len(result.stdout)<=cap and len(result.stderr)<=cap
    if not outputs_within_cap:raise ContractError('blocked-close child output cap reached')
    return result


class PrecloseResourceTests(unittest.TestCase):
    def test_literal_policy_identity_and_freeze_opt_in(self):
        self.assertEqual(payload_hash(study.RESOURCE_PUBLICATION_POLICY),
            '97182fefdef0ebd4e5007a8aed416fc13e189abb52c6218f3de252fddb4daa73')
        with patch.object(operator,'inspect_source',return_value=({},'source')):
            old=operator.make_freeze('.',dict(boot_id='boot'),{}, {},'approval',study_plan=PLAN)
            new=operator.make_freeze('.',dict(boot_id='boot'),{}, {},'approval',study_plan=PLAN,preclose_resources=True)
        self.assertNotIn('resource_publication_policy_sha256',old)
        self.assertFalse(study.resource_publication_enabled(old))
        self.assertTrue(study.resource_publication_enabled(new))
        self.assertNotEqual(old['freeze_sha256'],new['freeze_sha256'])
        self.assertEqual(old['study_plan'],new['study_plan'])
        self.assertEqual(old['unit_properties'],new['unit_properties'])
        for invalid in (None,True,'0'*64):
            with self.subTest(invalid=invalid),self.assertRaises(ContractError):
                study.resource_publication_enabled(dict(resource_publication_policy_sha256=invalid))

    def test_production_worker_publishes_linked_component_before_close(self):
        with TemporaryDirectory() as d:
            order=[]
            def close(root,conn):
                self.assertFalse((root/'consumer.json').exists())
                self.assertTrue((root/'completion.json').is_file())
                component=control(root/'preclose-resources.json')
                self.assertFalse(component['observer_thread_alive'])
                self.assertEqual(component['resources']['error'],'test_empty_prefix')
                self.assertFalse(component['close_verified'])
                order.append('close')
            with worker(Path(d)/'evidence',on_close=close) as w:
                w.run()
                consumer=control(w.root/'consumer.json')
                component=study.verify_preclose_resources(w.root,w.case,consumer)
                self.assertEqual(consumer['preclose_resources_sha256'],component['artifact_sha256'])
                self.assertTrue(consumer['result']['close_completed'])
                report=study.report(w.root,study_plan=PLAN)
                self.assertEqual(report['preclose_resource_component'],component)
                self.assertIsNone(component['resource_qualification'])
                self.assertFalse(report['original_application_budget_pass'])
                self.assertEqual(order,['close'])

    def test_legacy_freeze_never_moves_publication_or_observer_stop(self):
        with TemporaryDirectory() as d:
            def close(root,conn):
                self.assertFalse((root/'preclose-resources.json').exists())
            with worker(Path(d)/'evidence',opted=False,on_close=close) as w:
                w.run()
                self.assertNotIn('resource_publication_policy_sha256',control(w.root/'acquisition-checkpoint.json'))
                self.assertNotIn('preclose_resources_sha256',control(w.root/'consumer.json'))
                self.assertNotIn('preclose_resource_component',study.report(w.root,study_plan=PLAN))

    def test_stop_delivers_observer_result_without_changing_its_rows(self):
        with TemporaryDirectory() as d:
            returned={'rows':[dict(slot=7,error='original reading failed')], 'error':'original clock fault'}
            def observe(reader,epoch,stop,**kwargs):
                self.assertTrue(stop.wait(4))
                return deepcopy(returned)
            with worker(Path(d)/'evidence',observer=observe) as w:
                w.run()
                component=study.verify_preclose_resources(w.root,w.case,control(w.root/'consumer.json'))
                self.assertEqual(component['resources'],returned)
                self.assertFalse(component['observer_thread_alive'])
                self.assertIsNone(component['resource_qualification'])

    def test_live_observer_publishes_unavailable_without_copy_or_second_join(self):
        release=threading.Event();done=threading.Event()
        class Poison(dict):
            def __deepcopy__(self,memo):raise AssertionError('live state copied')
        def observe(reader,epoch,stop,**kwargs):
            try:release.wait(8);return Poison(rows=['late result'])
            finally:done.set()
        with TemporaryDirectory() as d:
            try:
                def close(root,conn):
                    component=control(root/'preclose-resources.json')
                    self.assertTrue(component['observer_thread_alive'])
                    self.assertIsNone(component['resources'])
                    release.set()
                with worker(Path(d)/'evidence',observer=observe,on_close=close) as w:
                    w.run()
                    component=control(w.root/'preclose-resources.json')
                    self.assertTrue(component['observer_thread_alive'])
                    self.assertIsNone(component['resources'])
            finally:release.set();self.assertTrue(done.wait(2))

    def test_observer_exception_is_retained_without_resource_qualification(self):
        with TemporaryDirectory() as d:
            def observe(*args,**kwargs):raise OSError('clock/read fault')
            with worker(Path(d)/'evidence',observer=observe) as w:
                w.run()
                component=control(w.root/'preclose-resources.json')
                self.assertIn('clock/read fault',component['resources']['error'])
                self.assertIsNone(component['resource_qualification'])

    def test_actual_observer_clock_and_read_faults_survive_component_publication(self):
        from infra.stream.recorder_absolute_observer import observe_absolute, audit_resources
        from infra.stream.recorder_application_budget import declare
        from tests.test_recorder_absolute_observer import Clock, Reader
        from tests.test_recorder_application_components import OWNER
        for mode in ('clock_exception','invalid_clock','read_exception','invalid_reading'):
            with self.subTest(mode=mode),TemporaryDirectory() as d:
                generated=[]
                def observe(reader,epoch,stop,**kwargs):
                    clock=Clock();source=Reader(clock,fail_at=1 if mode=='read_exception' else None)
                    now=clock.now
                    if mode=='clock_exception':
                        def now():raise OSError('clock unavailable')
                    elif mode=='invalid_clock':now=lambda:1.5
                    if mode=='invalid_reading':
                        read=source.read
                        def invalid(**kw):
                            value=read(**kw);value['before']=value['after']+1;return value
                        source.read=invalid
                    value=observe_absolute(source,epoch,stop,execute=True,wait=clock.wait(),clock_ns=now,capacity=2)
                    generated.append(deepcopy(value))
                    return value
                with worker(Path(d)/'evidence',observer=observe) as w:
                    w.run()
                    component=study.verify_preclose_resources(w.root,w.case,control(w.root/'consumer.json'))
                    self.assertEqual(component['resources'],generated[0])
                    self.assertIsNone(component['resource_qualification'])
                    if mode in ('clock_exception','invalid_clock'):
                        self.assertIsNotNone(component['resources']['error'])
                    try:
                        qualification=audit_resources(component['resources'],20.,60,85.,declare()['budgets'],OWNER)
                    except (ContractError,KeyError,TypeError,ValueError):
                        pass  # Invalid readings fail the original validation.
                    else:self.assertNotEqual(qualification['verdict'],'pass')

    def test_payload_cap_nonfinite_and_live_state_refusal_before_publication(self):
        with TemporaryDirectory() as d,worker(Path(d)/'evidence') as w:
            w.run();component_path=w.root/'preclose-resources.json';component_path.unlink()
            checkpoint=control(w.root/'acquisition-checkpoint.json')
            cases=[(dict(value='x'*study.RESOURCE_PUBLICATION_POLICY['max_bytes']),False),
                   (dict(value=float('nan')),False),(dict(rows=[]),True)]
            for resources,alive in cases:
                with self.subTest(alive=alive),self.assertRaises((ContractError,ValueError)):
                    study.publish_preclose_resources(w.root,checkpoint,resources,alive)
                self.assertFalse(component_path.exists())
                self.assertFalse(component_path.with_suffix('.json.pending').exists())

    def test_component_publication_failure_is_not_retried_or_normalized(self):
        with TemporaryDirectory() as d:
            calls=[]
            def fail(*args):calls.append(1);raise OSError('publication fault')
            with worker(Path(d)/'evidence',publish_component=fail) as w:
                w.run()
                consumer=control(w.root/'consumer.json')
                self.assertIn('publication fault',consumer['result']['error'])
                self.assertIsNone(consumer['preclose_resources_sha256'])
                self.assertEqual(calls,[1])
                self.assertIn('error',study.report(w.root,study_plan=PLAN)['preclose_resource_component'])

    def test_actual_link_and_directory_sync_faults_remain_failed_publications(self):
        for phase in ('link','directory_sync'):
            with self.subTest(phase=phase),TemporaryDirectory() as d:
                original=study.publish_preclose_resources
                def failing(*args):
                    real_link=os.link;real_sync=os.fsync;calls=[]
                    def link(*a,**kw):
                        if phase=='link':raise OSError('component link failed')
                        return real_link(*a,**kw)
                    def sync(fd):
                        calls.append(fd)
                        if phase=='directory_sync' and len(calls)==3:
                            raise OSError('component directory sync failed')
                        return real_sync(fd)
                    with patch.object(os,'link',side_effect=link),patch.object(os,'fsync',side_effect=sync):
                        return original(*args)
                with worker(Path(d)/'evidence',publish_component=failing) as w:
                    w.run();consumer=control(w.root/'consumer.json')
                    self.assertIn('component',consumer['result']['error'])
                    self.assertIsNone(consumer['preclose_resources_sha256'])
                    self.assertTrue((w.root/'preclose-resources.json.pending').exists())
                    # Link may have become visible; it is not silently promoted
                    # to a durably successful publication after fsync failure.
                    self.assertEqual((w.root/'preclose-resources.json').exists(),phase=='directory_sync')
                    self.assertIn('error',study.report(w.root,study_plan=PLAN)['preclose_resource_component'])
                    (w.root/'consumer.json').unlink()
                    # A visible final link with pending state cannot masquerade
                    # as a complete publication when the final consumer is gone.
                    self.assertIn('error',study.report(w.root,study_plan=PLAN)['preclose_resource_component'])

    def test_invalid_freeze_extension_fails_before_reader_or_capture(self):
        with TemporaryDirectory() as d,worker(Path(d)/'evidence') as w:
            w.frozen['resource_publication_policy_sha256']='0'*64
            with patch.object(study,'LinuxReader') as reader,patch.object(study,'collect') as collect:
                with self.assertRaisesRegex(ContractError,'publication policy'):
                    w.run()
                reader.assert_not_called();collect.assert_not_called()
            with patch.object(operator,'inspect_source') as source:
                bad=deepcopy(w.frozen)
                bad['freeze_sha256']=payload_hash({k:v for k,v in bad.items() if k!='freeze_sha256'})
                with self.assertRaisesRegex(ContractError,'publication policy'):
                    operator.verify_freeze(Path(d),bad)
                source.assert_not_called()

    def test_guard_races_preserve_fault_and_published_component(self):
        for phase in ('publication','close'):
            with self.subTest(phase=phase),TemporaryDirectory() as d,patch.object(capture.os,'kill') as kill:
                guards=[]
                def factory(*args,**kwargs):
                    value=capture.ConnectDeadline(*args,**kwargs);guards.append(value);return value
                original=study.publish_preclose_resources
                def publication(*args):
                    value=original(*args)
                    if phase=='publication':guards[0].interrupt()
                    return value
                def close(root,conn):
                    if phase=='close':guards[-1].interrupt()
                with worker(Path(d)/'evidence',guards=factory,on_close=close,publish_component=publication) as w:
                    w.run()
                    kill.assert_called_once_with(os.getpid(),signal.SIGTERM)
                    consumer=control(w.root/'consumer.json')
                    self.assertIn('process guard fired',consumer['result']['error'])
                    if phase=='close':self.assertFalse(consumer['result']['close_completed'])
                    self.assertIsNone(study.verify_preclose_resources(w.root,w.case,consumer)['resource_qualification'])

    def test_linkage_mutations_and_corruption_are_rejected_without_erasing_counts(self):
        mutations=('case_sha256','identity','epoch_ns','domain','policy_sha256','checkpoint_sha256',
                   'completion_sha256','resource_plan_sha256','close_verified','resource_qualification',
                   'resource_epoch','resource_plan','live_with_rows','hash','symlink','missing')
        with TemporaryDirectory() as d,worker(Path(d)/'evidence') as w:
            w.run();path=w.root/'preclose-resources.json';original=path.read_bytes()
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    value=json.loads(original)
                    if mutation=='missing':path.unlink()
                    elif mutation=='symlink':path.unlink();path.symlink_to(w.root/'consumer.json')
                    else:
                        if mutation=='identity':value['identity']['start_ticks']+=1
                        elif mutation=='epoch_ns':value[mutation]+=1
                        elif mutation=='close_verified':value[mutation]=True
                        elif mutation=='resource_qualification':value[mutation]='passed'
                        elif mutation=='live_with_rows':value['observer_thread_alive']=True
                        elif mutation=='resource_epoch':value['resources']['epoch_ns']+=1
                        elif mutation=='resource_plan':value['resources']['plan_sha256']='0'*64
                        else:value[mutation]='bad'
                        value['artifact_sha256']=payload_hash({k:v for k,v in value.items() if k!='artifact_sha256'})
                        if mutation=='hash':value['artifact_sha256']='0'*64
                        path.write_text(json.dumps(value))
                    report=study.report(w.root,study_plan=PLAN)
                    self.assertIn('error',report['preclose_resource_component'])
                    self.assertIsNotNone(report['population'])
                    if path.exists() or path.is_symlink():path.unlink()
                    path.write_bytes(original)

    def test_retained_case_rejects_reuse_symlink_and_missing_root_before_spawn(self):
        with TemporaryDirectory() as d,patch.object(subprocess,'run') as spawn:
            root=Path(d).resolve()
            (root/'existing').write_text('do not overwrite')
            for path in (root,root/'missing'):
                with self.subTest(path=path),self.assertRaises(ContractError):
                    run_retained_blocked_close(path)
            alias=root/'alias';alias.symlink_to(root,target_is_directory=True)
            with self.assertRaises(ContractError):run_retained_blocked_close(alias)
            spawn.assert_not_called()

    def test_real_process_guard_kill_during_close_keeps_component_and_no_final_consumer(self):
        with TemporaryDirectory() as d:
            result=run_retained_blocked_close(Path(d).resolve())
            self.assertEqual(result.returncode,-signal.SIGTERM,result.stderr)
            root=Path(d)/'evidence'
            self.assertTrue((root/'preclose-resources.json').is_file())
            self.assertFalse((root/'consumer.json').exists())
            report=study.report(root,study_plan=PLAN)
            self.assertIn('resources',report['preclose_resource_component'])
            self.assertFalse(report['close_verified'])
            self.assertFalse(report['coverage_complete'])
            self.assertIsNotNone(report['population'])


if __name__=='__main__':unittest.main()
