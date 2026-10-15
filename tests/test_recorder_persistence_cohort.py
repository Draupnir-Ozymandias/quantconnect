"""Case-sized completion, actual offline recorder paths and finite cohort faults."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError,payload_hash
from infra.stream.recorder_case_archive import archive_frames
from infra.stream import recorder_persistence_worker as worker
from infra.stream import recorder_persistence_cohort as cohort
from infra.stream import recorder_persistence_cohort_audit as audit
from infra.stream.recorder_persistence_lane import collect_with_completion
from infra.stream.recorder_completion import CompletionWitnesses
from infra.stream.recorder_application_budget import corpus,declare
from infra.stream.recorder_application_worker import schedule
from infra.stream.recorder_application_evaluator import large_control
from tests.test_market_stream import Clock
from tests.test_recorder_absolute_observer import Clock as ResourceClock,Reader
from tests.test_recorder_absolute_smoke import resource,BOOT
from infra.stream.recorder_absolute_observer import observe_absolute

STAGE='/var/lib/qcrl-stream/recorder-persistence-OfflineCohort'


def capture(root,count=60000,kind='steady'):
    clock=Clock()
    with patch.object(cohort.time,'monotonic',clock.mono),patch.object(cohort,'utc_now',clock.utc),patch.object(cohort,'boot',return_value=BOOT):
        case=cohort.prepare(root,'a'*64,kind+'-0',execute=True)
    if count!=60000:
        # Only boundary fixtures shorten the original case; no production override.
        value=case.copy();value.pop('artifact_sha256');value['spec']['max_frames']=count
        (root/'case.json').unlink();case=worker.publish(root/'case.json',value)
    population=corpus();scheduled=schedule(kind)
    class Socket:
        i=0
        def recv(self,timeout):
            clock.seconds=case['epoch']+scheduled[self.i]['offset']+.0005
            i=self.i;self.i+=1
            return population['initial'][i] if i<2 else population['cycle'][(i-2)%8]
        def send(self,value):pass
        def close(self):pass
    clock.seconds=6
    witness=CompletionWitnesses(case['spec'],'localhost.'+BOOT,clock=clock.utc,monotonic=clock.mono,execute=True)
    summary=collect_with_completion(case['raw_bundle'],case['spec'],root/'archive',completion_observer=witness,
        connector=Socket,clock=clock.utc,monotonic=clock.mono,pause=clock.pause)
    worker.exclusive_json(root/'completion.json',witness.snapshot(root/'archive'))
    owner=dict(pid=os.getpid(),process_start_id='1',boot_id=BOOT,cgroup='/consumer')
    worker.publish(root/'capture-closed.json',dict(case_sha256=case['artifact_sha256'],at=clock.seconds))
    worker.publish(root/'consumer.json',dict(case_sha256=case['artifact_sha256'],identity=owner,
        domain='localhost.'+BOOT,summary=summary,resources={},closed=clock.seconds,error=None,observer_thread_alive=False))
    return case,clock


class ArchiveBoundaryTests(unittest.TestCase):
    def make(self,path,count):
        path.mkdir();(path/'segment-000001.json').write_text(json.dumps({'file':'segment-000001.gz'}))
        with gzip.open(path/'segment-000001.gz','wt') as out:
            for i in range(count):out.write(json.dumps(dict(kind='frame',payload={'raw_text':str(i)}))+'\n')
            out.write(json.dumps(dict(kind='session_end',payload={'frames':count}))+'\n')

    def test_declared_count_boundaries_missing_and_extra(self):
        with tempfile.TemporaryDirectory() as d:
            for count in (1,2,67,68,69,70,59999,60000):
                with self.subTest(count=count):
                    root=Path(d)/str(count);self.make(root,count)
                    frames,footer,gaps=archive_frames(root,count)
                    self.assertEqual((len(frames),footer['frames'],gaps),(count,count,0))
                    if count>1:
                        with self.assertRaises(ContractError):archive_frames(root,count-1)
                    if count<60000:
                        with self.assertRaises(ContractError):archive_frames(root,count+1)
            for count in (0,-1,True,60001,65536,1.5,None):
                with self.assertRaises(ContractError):archive_frames(Path(d)/'68',count)

    def test_traversal_symlink_duplicate_footer_and_row_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'case';self.make(root,1);desc=root/'segment-000001.json'
            original=desc.read_bytes();desc.write_text(json.dumps({'file':'../escape.gz'}))
            with self.assertRaises(ContractError):archive_frames(root,1)
            desc.write_bytes(original);p=root/'segment-000001.gz';p.rename(root/'other.gz');p.symlink_to(root/'other.gz')
            with self.assertRaises(ContractError):archive_frames(root,1)
            p.unlink()
            (root/'other.gz').rename(p)
            with gzip.open(p,'at') as out:out.write(json.dumps(dict(kind='session_end',payload={}))+'\n')
            with self.assertRaises(ContractError):archive_frames(root,1)
            with gzip.open(p,'wt') as out:out.write('x'*(4*1024**2+1))
            with self.assertRaises(ContractError):archive_frames(root,1)

    def test_actual_completion_accepts_69_and_rejects_count_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            case,_=capture(Path(d)/'case',69)
            worker.verify_recorder_completion(Path(d)/'case',case)
            for count in (68,70):
                bad=deepcopy(case);bad['spec']['max_frames']=count
                with self.assertRaises(ContractError):worker.verify_recorder_completion(Path(d)/'case',bad)


class FullPopulationTests(unittest.TestCase):
    def test_actual_60000_completion_producer_large_reader_and_absolute_audit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'steady-0';case,clock=capture(root)
            verified=worker.verify_recorder_completion(root,case)
            self.assertEqual(verified['completion']['frames'][-1]['sequence'],59999)
            tx=Clock();sent=0
            class Sink:
                def send(self,raw):pass
            result=cohort.transmit(Sink(),'steady',case['epoch'],clock=tx.mono,pause=tx.pause)
            sender=dict(pid=os.getpid()+1,process_start_id='1',boot_id=BOOT,cgroup='/producer')
            worker.publish(root/'producer.json',dict(case_sha256=case['artifact_sha256'],identity=sender,
                result=result,controls=[],control_errors=[],terminal_receive=[dict(at=clock.seconds,normal=True,
                type='ConnectionClosedOK',received_code=1000,sent_code=1000)],
                initial_resource=resource(3,sender),final_resource=resource(clock.seconds+1,sender)))
            self.assertGreater((root/'producer.json').stat().st_size,2*1024**2)
            producer=large_control(root/'producer.json')
            worker.verify_closure(result,producer['terminal_receive'],[],[],verified,case)
            owner=verified['consumer']['identity'];ns=ResourceClock(6*10**9)
            class BoundReader(Reader):
                def read(self,*,rss):
                    v=super().read(rss=rss);v['owner']=owner;v['actors']=[dict(owner,rss_bytes=v['rss_bytes'])]
                    v['cpu'].update(nr_throttled=0,throttled_usec=0);return v
            resources=observe_absolute(BoundReader(ns),case['epoch'],SimpleNamespace(is_set=lambda:ns.value>=(case['epoch']+120)*10**9),
                execute=True,wait=ns.wait(),clock_ns=ns.now)
            value=verified['consumer'];value.pop('artifact_sha256');value['resources']=resources
            (root/'consumer.json').unlink();worker.publish(root/'consumer.json',value)
            worker.publish(root/'observer-ready.json',dict(initial=resource(5,owner),case_sha256=case['artifact_sha256'],identity=owner,at=6))
            for role,actor,at,start,end in [('producer',sender,5,3,150),('consumer',owner,6,4,149)]:
                value=cohort.spec(STAGE,role,'steady-0')
                props=dict(value['properties'],Id=value['unit']+'.service',CPUQuotaPerSecUSec='750ms',RuntimeMaxUSec='4min',
                    MemoryMax='536870912',ActiveState='active',SubState='exited',Result='success',ExecMainStatus='0',ExecMainCode='1',
                    ExecMainPID=str(actor['pid']),MainPID=str(actor['pid']),ControlGroup=actor['cgroup'],
                    ExecMainStartTimestampMonotonic=str(start*1000000),ExecMainExitTimestampMonotonic=str(end*1000000))
                args=[cohort.PYTHON,'-m','infra.stream.recorder_persistence_cohort','--root',STAGE+'/evidence/steady-0',
                    '--worker',role,'--case','steady-0','--execute']
                props['ExecStart']='{ argv[]='+' '.join(args)+' ; }'
                (root.parent/(value['unit']+'-properties.txt')).write_text('\n'.join(k+'='+v for k,v in props.items()))
                (root.parent/(value['unit']+'-journal.txt')).write_text('retained journal')
                props=props.copy();props['SubState']='running'
                binding=worker.publish(root/(role+'-active.json'),dict(unit=props['Id'],identity=actor,properties=props,
                    sample=resource(at+.2,actor),begin=at+.1,end=at+.3))
                worker.publish(root/('server-ready.json' if role=='producer' else 'worker-ready.json'),
                    dict(case_sha256=case['artifact_sha256'],identity=actor,at=at))
            worker.publish(root/'bindings-ready.json',dict(case_sha256=case['artifact_sha256'],at=7,
                producer_binding=worker.control(root/'producer-active.json')['artifact_sha256'],
                consumer_binding=worker.control(root/'consumer-active.json')['artifact_sha256']))
            frozen=dict(freeze_sha256='a'*64,runtime={'boot_id':BOOT},sources=dict(cohort.declaration()['sources'],**__import__('infra.stream.recorder_completion',fromlist=['_sources'])._sources()),observer=cohort.declaration())
            report,end,units=audit.audit_case_native(root.parent,'steady-0',frozen,STAGE,2,2)
            self.assertEqual(report['frames'],60000)
            self.assertEqual(report['verdict'],'pass',report['failures']+report['unknowns'])
            self.assertEqual(len(report['resources']['windows']),2)

    def test_full_mixed_schedule_and_error_bound(self):
        class Sink:
            def send(self,raw):pass
        clock=Clock();result=cohort.transmit(Sink(),'mixed',20,clock=clock.mono,pause=clock.pause)
        from infra.stream.recorder_application_evaluator import stimulus_gate
        self.assertEqual(stimulus_gate(result,'mixed',20)['verdict'],'pass')
        class Fault:
            def send(self,raw):raise ValueError('x'*300)
        result=cohort.transmit(Fault(),'steady',20,clock=clock.mono,pause=clock.pause)
        self.assertEqual(len(result['error']),160);self.assertFalse(result['complete'])


class RoutingTests(unittest.TestCase):
    def test_exact_thirteen_units_commands_and_no_unapproved_execution(self):
        self.assertEqual(cohort.PLAN['case_order'],declare()['policy']['case_order'])
        ops=object.__new__(cohort.CohortProduction);ops.root=Path(STAGE);ops.evidence=ops.root/'evidence';ops.specs={};ops.case_name=None
        with patch.object(cohort,'command',return_value='') as call:
            ops.start(cohort.spec(STAGE,'tests'))
            for case in cohort.PLAN['case_order']:
                ops.case_name=case
                for role in ('producer','consumer'):ops.start(cohort.spec(STAGE,role,case))
        self.assertEqual(len(call.call_args_list),13)
        for call in call.call_args_list[1:]:
            self.assertIn('infra.stream.recorder_persistence_cohort',call.args[0]);self.assertIn('--case',call.args[0])
        with self.assertRaises(ContractError):cohort.execute_cohort(None)
        with self.assertRaises(ContractError):cohort.spec(STAGE,'consumer','extra-0')
        with self.assertRaises(ContractError):cohort.prepare(Path('/unused'),'a'*64,'steady-0')


class LifecycleTests(unittest.TestCase):
    def run_fake(self,fault=None):
        with tempfile.TemporaryDirectory() as d:
            class Ops:
                root=Path(STAGE);case_name=None;frozen={'linux_tests':1200,'freeze_sha256':'a'*64};events=[]
                def __init__(self):self.evidence=Path(d);self.events=[]
                def preflight(self):
                    if fault=='preflight':raise ContractError('preflight')
                    return {'public':'unchanged'}
                def claim(self):self.events.append(('claim',None))
                def start(self,v):self.events.append(('start',v['unit']))
                def finish(self,unit,**kw):
                    self.events.append(('finish',unit))
                    if unit.endswith('-tests'):
                        (self.evidence/(unit+'-journal.txt')).write_text('Ran '+('1199' if fault=='tests' else '1200')+' tests in 1s\nOK (skipped=1)\n')
                def capture(self,unit,**kw):
                    self.events.append(('capture',unit))
                    if fault=='capture' and '-consumer' in unit:raise ContractError('capture fault')
                    role='tests' if unit.endswith('-tests') else unit.rsplit('-',1)[-1]
                    value=cohort.spec(STAGE,role,None if role=='tests' else self.case_name)
                    return dict(unit=unit,result='success',exec_status=0,substate='exited',observed_properties=value['properties'])
                def stop(self,unit):self.events.append(('stop',unit))
                def recheck(self,*args):return {'unchanged':True}
                def public_state(self):return {'public':'unchanged'}
                def prepare(self,name):
                    self.case_name=name;path=self.evidence/name;path.mkdir()
                    self.case=worker.publish(path/'case.json',dict(case=name,epoch=100))
                    self.events.append(('prepare',name))
                def ready(self,name,deadline):
                    role='producer' if name=='server-ready.json' else 'consumer'
                    return dict(case_sha256=self.case['artifact_sha256'],at=1,identity={'boot_id':BOOT,'cgroup':'/'+role})
                def bind(self,role,ready,deadline):return {'artifact_sha256':role+'-binding'}
                def publish_report(self,report):self.report=report
            ops=Ops()
            def lifecycle(root,case):
                if fault=='lifecycle' and case['case']=='mixed-0':raise ContractError('completion failed')
            with patch.object(cohort.time,'monotonic',return_value=2),patch.object(cohort,'verify_case_lifecycle',side_effect=lifecycle):
                if fault=='preflight':
                    with self.assertRaises(ContractError):cohort.execute_cohort(ops,execute=True)
                    return ops.events,None
                result=cohort.execute_cohort(ops,execute=True)
            return ops.events,result

    def test_exact_serial_six_case_lifecycle(self):
        events,result=self.run_fake()
        self.assertTrue(result['complete']);self.assertEqual(result['completed'],cohort.PLAN['case_order'])
        starts=[u for k,u in events if k=='start'];self.assertEqual(len(starts),13)
        for unit in starts:
            self.assertEqual(events.count(('capture',unit)),1);self.assertEqual(events.count(('stop',unit)),1)
        for i,name in enumerate(cohort.PLAN['case_order']):
            if i:
                prior=cohort.PLAN['case_order'][i-1]
                self.assertLess(events.index(('stop',cohort.spec(STAGE,'producer',prior)['unit'])),events.index(('prepare',name)))

    def test_preflight_readiness_capture_and_completion_faults_stop_without_replay(self):
        events,_=self.run_fake('preflight');self.assertEqual(events,[])
        for fault in ('tests','capture','lifecycle'):
            with self.subTest(fault=fault):
                events,result=self.run_fake(fault);self.assertFalse(result['complete']);self.assertIsNotNone(result['error'])
                started=[u for k,u in events if k=='start']
                self.assertEqual(len(started),1 if fault=='tests' else 3 if fault=='capture' else 5)
                for unit in started:
                    self.assertEqual(events.count(('capture',unit)),1);self.assertEqual(events.count(('stop',unit)),1)
                self.assertLess(len(result['completed']),6)

    def test_cohort_protocol_identity_is_pinned(self):
        self.assertEqual(payload_hash(cohort.PLAN),'eca23ef82ac9ca72a816a9580483a35657df364ea081f7772f8e5c0477b1fa6b')
        self.assertFalse(cohort.PLAN['incremental_observer_overhead_gate'])
        self.assertFalse(cohort.PLAN['continuous_rss_peak_gate']);self.assertIsNone(cohort.PLAN['credit_balance_minimum'])


class LineageTests(unittest.TestCase):
    def fixture(self):
        before='from infra.stream.recorder_absolute_smoke_audit import archive_frames\nframes = archive_frames(root/\'archive\')\n'
        after=before.replace('from infra.stream.recorder_absolute_smoke_audit import archive_frames','from infra.stream.recorder_case_archive import archive_frames').replace("archive_frames(root/'archive')","archive_frames(root/'archive', case['spec']['max_frames'])")
        name='infra/stream/recorder_persistence_worker.py';core='infra/stream/recorder_persistence_lane.py'
        sources={name:hashlib.sha256(after.encode()).hexdigest(),core:'b'*64}
        host=dict(instance_id='instance',region='region',instance_type='type',credit_mode='standard')
        runtime=dict(wait={},websockets={},boot_id=BOOT,host=host)
        old=dict(sources={name:hashlib.sha256(before.encode()).hexdigest(),core:'b'*64},runtime=runtime)
        old['freeze_sha256']=payload_hash(old)
        origin={'freeze_sha256':old['freeze_sha256']};origin['attestation_sha256']=payload_hash(origin)
        text=json.dumps(dict(verdict='pass',complete=True,compatibility_verified=True,native_origin_verified=False,failures=[],unknowns=[]))
        value=dict(freeze=old,origin_attestation=origin,audit_text=text,worker_original=before)
        constants=dict(COMPATIBILITY_FREEZE=old['freeze_sha256'],COMPATIBILITY_ORIGIN=origin['attestation_sha256'],
            COMPATIBILITY_AUDIT=hashlib.sha256(text.encode()).hexdigest())
        return value,sources,runtime,constants

    def test_tested_core_exact_delta_runtime_and_origin_fail_closed(self):
        value,sources,runtime,constants=self.fixture()
        with patch.multiple(cohort,**constants):
            cohort.validate_lineage(value,sources,runtime)
            for mode in ('core','worker','runtime','audit','origin','host'):
                v,s,r=deepcopy(value),sources.copy(),deepcopy(runtime)
                if mode=='core':s['infra/stream/recorder_persistence_lane.py']='a'*64
                if mode=='worker':s['infra/stream/recorder_persistence_worker.py']='a'*64
                if mode=='runtime':r['boot_id']='different'
                if mode=='audit':v['audit_text']+='\n'
                if mode=='origin':v['origin_attestation']['freeze_sha256']='a'*64
                if mode=='host':r['host']['credit_mode']='unlimited'
                with self.subTest(mode=mode),self.assertRaises(ContractError):cohort.validate_lineage(v,s,r)


class OriginAuditTests(unittest.TestCase):
    def fixture(self,root,complete=True):
        e=root/'evidence';e.mkdir();host={'public':{'collectors':{'public.timer':'active'}}}
        (e/'host-context.json').write_text(json.dumps(host))
        (e/'compatibility-lineage.json').write_text('{}');(e/'execution-freeze.json').write_text('{}')
        f={'freeze_sha256':'a'*64,'runtime':{'host':host},'linux_tests':1200}
        launch=dict(freeze_sha256='a'*64,cohort_plan_sha256=payload_hash(cohort.PLAN),stage=STAGE,
            complete=complete,completed=cohort.PLAN['case_order'] if complete else [],error=None if complete else 'runtime fault',
            preservation_errors=[],public_before=host['public'],public_after=host['public'],
            native_origin_verified=False,compatibility_verified=False,budget_cohort_authorized=False,orders_authorized=False)
        launch['launch_sha256']=payload_hash(launch);(e/'launch-result.json').write_text(json.dumps(launch))
        value=cohort.spec(STAGE,'tests');raw=dict(value['properties'],Id=value['unit']+'.service',CPUQuotaPerSecUSec='750ms',
            RuntimeMaxUSec='4min',MemoryMax='1073741824',ActiveState='active',SubState='exited',Result='success',
            ExecMainStatus='0',ExecMainCode='1',ExecMainPID='10',ExecMainStartTimestampMonotonic='1000000',ExecMainExitTimestampMonotonic='2000000')
        raw['ExecStart']='{ argv[]='+cohort.PYTHON+' -m unittest discover -s tests -q ; }'
        (e/(value['unit']+'-properties.txt')).write_text('\n'.join(k+'='+v for k,v in raw.items()))
        (e/(value['unit']+'-journal.txt')).write_text('Ran 1200 tests in 1s\nOK (skipped=1)\n')
        for n in ('before','after'):(e/('host-processes-'+n+'.txt')).write_text('retained actors')
        return f

    def seal(self,root):
        e=root/'evidence';v=dict(schema_version='qcrl.recorder_persistence_cohort_inventory.v1',freeze_sha256='a'*64,
            native_origin_verified=False,files={str(p.relative_to(e)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in e.rglob('*') if p.is_file()})
        v['inventory_sha256']=payload_hash(v);(root/'origin-inventory.json').write_text(json.dumps(v))
        return dict(expected_inventory_file_sha256=hashlib.sha256((root/'origin-inventory.json').read_bytes()).hexdigest(),
            expected_freeze_sha256='a'*64,expected_host_context_file_sha256=hashlib.sha256((e/'host-context.json').read_bytes()).hexdigest())

    def test_six_case_audit_preserves_known_failures_and_unknowns(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);f=self.fixture(root);anchors=self.seal(root);calls=[]
            def case(e,name,frozen,stage,test_end,previous):
                calls.append((name,previous));return dict(case=name,failures=['timing'] if name=='mixed-1' else [],
                    unknowns=['missed_resource_slot'] if name=='steady-2' else []),previous+150,{}
            with patch.object(audit,'validate_freeze',return_value=f),patch.object(audit,'audit_case_native',side_effect=case):
                report=audit.audit(root,**anchors)
            self.assertEqual([v[0] for v in calls],cohort.PLAN['case_order'])
            self.assertEqual(report['verdict'],'fail');self.assertIn('mixed-1:timing',report['failures'])
            self.assertIn('steady-2:missed_resource_slot',report['unknowns']);self.assertFalse(report['application_budget_pass'])

    def test_external_anchor_extra_file_and_rehashed_wrong_case_order_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);f=self.fixture(root);anchors=self.seal(root)
            with patch.object(audit,'validate_freeze',return_value=f):
                bad=anchors.copy();bad['expected_host_context_file_sha256']='b'*64
                with self.assertRaises(ContractError):audit.audit(root,**bad)
                (root/'evidence/extra').write_text('unsealed')
                with self.assertRaises(ContractError):audit.audit(root,**anchors)
                p=root/'evidence/launch-result.json';v=json.loads(p.read_text());v.pop('launch_sha256');v['completed']=list(reversed(v['completed']));v['launch_sha256']=payload_hash(v);p.write_text(json.dumps(v))
                anchors=self.seal(root)
                with self.assertRaises(ContractError):audit.audit(root,**anchors)

    def test_incomplete_launch_retains_runtime_fault_and_missing_case_unknowns(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);f=self.fixture(root,False);case=root/'evidence/steady-0';case.mkdir()
            worker.publish(case/'consumer.json',dict(error='fsync fault',observer_thread_alive=False))
            anchors=self.seal(root)
            with patch.object(audit,'validate_freeze',return_value=f),patch.object(audit,'components',side_effect=FileNotFoundError):
                report=audit.audit(root,**anchors)
            self.assertFalse(report['complete']);self.assertEqual(report['verdict'],'fail')
            self.assertIn('steady-0:consumer.json:retained_runtime_fault',report['failures'])
            self.assertEqual(len([v for v in report['unknowns'] if ':component_unavailable:' in v]),6)
