"""Offline transport/audit fixtures; never native timing evidence."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_absolute_smoke as smoke
from infra.stream import recorder_absolute_smoke_audit as audit
from infra.stream import recorder_application_worker as worker
from infra.stream.recorder_absolute_observer import observe_absolute
from infra.stream.recorder_absolute_wait import NS
from infra.stream.recorder_completion_lane import collect_with_completion
from infra.stream.recorder_completion import CompletionWitnesses
from infra.stream.recorder_wait_compatibility_worker import publish
from tests.test_market_stream import Clock as AppClock
from tests.test_recorder_absolute_observer import Clock, Reader
from tests import test_recorder_wait_execution as wait_tests
from tests.test_recorder_application_components import sample

BOOT='11111111-2222-3333-4444-555555555555'
STAGE='/var/lib/qcrl-stream/recorder-absolute-OfflineFixture'


def frozen():
    sources={str(p.relative_to(smoke.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
             for base in ('infra/stream','execution_truth','tests') for p in (smoke.ROOT/base).glob('*.py')}
    sources.update(smoke.declaration()['sources'])
    sources['docs/RECORDER_ABSOLUTE_SMOKE_PREPARATION.md']=hashlib.sha256(
        (smoke.ROOT/'docs/RECORDER_ABSOLUTE_SMOKE_PREPARATION.md').read_bytes()).hexdigest()
    installed=dict(wait=wait_tests.WaitExecutionTests().runtime(),boot_id=BOOT,
        websockets=dict(version='15.0.1',root='/fixture',files={'websockets/sync/client.py':'a'*64,'websockets/sync/server.py':'b'*64}))
    installed['host']=dict(instance_id='i-039c11d5ea49cf413',region='us-east-2',instance_type='t4g.small',
        credit_mode='standard',boot_id=BOOT,method='read_only_ec2_console',credit_balance=None,
        observed_utc='2026-10-15T12:00:00+00:00',console_text_sha256='c'*64,
        public=dict(collectors={'public.timer':'active','public.service':'inactive'},env_sha256='a'*64))
    return smoke.freeze('a'*40,sources,installed,1200)


def identity(role,pid):
    return dict(pid=pid,process_start_id='1',boot_id=BOOT,
        cgroup='/system.slice/'+smoke.spec(STAGE,role)['unit']+'.service')


def resource(at,owner):
    value=sample(at,int(at*1000));value['owner']=deepcopy(owner)
    value['actors']=[dict(owner,rss_bytes=1000)]
    value['cpu'].update(nr_throttled=0,throttled_usec=0)
    return value


def properties(role,pid,start,end):
    value=smoke.spec(STAGE,role)
    p=dict(value['properties'],Id=value['unit']+'.service',CPUQuotaPerSecUSec='750ms',
        RuntimeMaxUSec='4min',MemoryMax='536870912',ActiveState='active',SubState='exited',
        Result='success',ExecMainStatus='0',ExecMainCode='1',ExecMainPID=str(pid),MainPID=str(pid),
        ControlGroup=identity(role,pid)['cgroup'],ExecMainStartTimestampMonotonic=str(int(start*1e6)),
        ExecMainExitTimestampMonotonic=str(int(end*1e6)))
    args=['-m','unittest','discover','-s','tests','-q'] if role=='tests' else [
        '-m','infra.stream.recorder_absolute_smoke','--root',STAGE+'/evidence/case','--worker',role,'--execute']
    p['ExecStart']='{ path='+smoke.PYTHON+' ; argv[]='+' '.join([smoke.PYTHON,*args])+' ; }'
    return p


def reseal(root,freeze):
    e=root/'evidence';files={}
    for p in sorted(e.rglob('*')):
        if p.is_file():
            b=p.read_bytes();files[str(p.relative_to(e))]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    v=dict(schema_version='qcrl.recorder_absolute_smoke_inventory.v1',files=files,
        freeze_sha256=freeze['freeze_sha256'],native_origin_verified=False)
    v['inventory_sha256']=payload_hash(v)
    path=root/'origin-inventory.json';path.unlink(missing_ok=True);publish(path,v)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_control(path,mutate):
    v=worker.control(path);v.pop('artifact_sha256');mutate(v);path.unlink();worker.publish(path,v)


def fixture(root):
    f=frozen();e=root/'evidence';e.mkdir();clock=AppClock()
    with patch.object(smoke.time,'monotonic',clock.mono),patch.object(smoke,'utc_now',clock.utc),patch.object(smoke,'boot',return_value=BOOT):
        case=smoke.prepare(e/'case',f['freeze_sha256'],execute=True)
    c=e/'case';owner=identity('consumer',os.getpid());sender=identity('producer',os.getpid()+1)
    class Socket:
        def __init__(self):self.i=0
        def recv(self,timeout):
            clock.seconds=case['epoch']+self.i+.001
            value=worker.message(self.i);self.i+=1;return value
        def send(self,value):pass
        def close(self):pass
    clock.seconds=6
    witness=CompletionWitnesses(case['spec'],'localhost.'+BOOT,clock=clock.utc,monotonic=clock.mono,execute=True)
    summary=collect_with_completion(case['raw_bundle'],case['spec'],c/'archive',completion_observer=witness,
        connector=lambda:Socket(),clock=clock.utc,monotonic=clock.mono,pause=clock.pause)
    completion=witness.snapshot(c/'archive');publish(c/'completion.json',completion)
    closed=clock.seconds
    worker.publish(c/'capture-closed.json',dict(case_sha256=case['artifact_sha256'],at=closed))
    nsclock=Clock(6*NS)
    class BoundReader(Reader):
        def read(self,*,rss):
            value=super().read(rss=rss);value['owner']=deepcopy(owner)
            value['actors']=[dict(owner,rss_bytes=value['rss_bytes'])]
            value['cpu'].update(nr_throttled=0,throttled_usec=0);return value
    resources=observe_absolute(BoundReader(nsclock),case['epoch'],
        SimpleNamespace(is_set=lambda:nsclock.value>=(case['epoch']+68)*NS),
        execute=True,wait=nsclock.wait(),clock_ns=nsclock.now)
    sendclock=AppClock();sent=[]
    result=smoke.transmit(SimpleNamespace(send=sent.append),'steady',case['epoch'],clock=sendclock.mono,pause=sendclock.pause)
    worker.publish(c/'producer.json',dict(case_sha256=case['artifact_sha256'],identity=sender,
        result=result,controls=[],control_errors=[],initial_resource=resource(3.1,sender),final_resource=resource(89,sender)))
    worker.publish(c/'consumer.json',dict(case_sha256=case['artifact_sha256'],identity=owner,
        domain='localhost.'+BOOT,summary=summary,resources=resources,closed=closed,error=None,observer_thread_alive=False))
    for role,actor,at in [('producer',sender,5),('consumer',owner,6)]:
        worker.publish(c/('server-ready.json' if role=='producer' else 'worker-ready.json'),
            dict(case_sha256=case['artifact_sha256'],identity=actor,at=at))
        raw=properties(role,actor['pid'],3 if role=='producer' else 4,90 if role=='producer' else 91);raw['SubState']='running'
        worker.publish(c/(role+'-active.json'),dict(unit=raw['Id'],begin=at+.1,end=at+.3,
            identity=actor,properties=raw,sample=resource(at+.2,actor)))
    worker.publish(c/'observer-ready.json',dict(case_sha256=case['artifact_sha256'],identity=owner,at=6,
        initial=resource(5,owner)))
    worker.publish(c/'bindings-ready.json',dict(case_sha256=case['artifact_sha256'],at=7,
        producer_binding=worker.control(c/'producer-active.json')['artifact_sha256'],
        consumer_binding=worker.control(c/'consumer-active.json')['artifact_sha256']))
    public=dict(collectors={'public.timer':'active','public.service':'inactive'},env_sha256='a'*64)
    launch=dict(schema_version='qcrl.recorder_absolute_smoke_launch.v1',stage=STAGE,
        freeze_sha256=f['freeze_sha256'],smoke_plan_sha256=payload_hash(smoke.PLAN),public_before=public,public_after=public,
        complete=True,error=None,preservation_errors=[],native_origin_verified=False,compatibility_verified=False,
        budget_cohort_authorized=False,orders_authorized=False)
    launch['launch_sha256']=payload_hash(launch);publish(e/'launch-result.json',launch);publish(e/'execution-freeze.json',f);publish(e/'host-context.json',f['runtime']['host'])
    for role,pid,start,end in [('tests',os.getpid()+2,1,2),('producer',sender['pid'],3,90),('consumer',owner['pid'],4,91)]:
        name=smoke.spec(STAGE,role)['unit'];p=properties(role,pid,start,end)
        (e/(name+'-properties.txt')).write_text('\n'.join(k+'='+v for k,v in p.items()))
        (e/(name+'-journal.txt')).write_text('Ran 1200 tests in 1.0s\nOK (skipped=1)\n' if role=='tests' else 'fixture\n')
    return f,reseal(root,f)


class SmokeTests(unittest.TestCase):
    def test_literal_plan_identity(self):
        self.assertEqual(payload_hash(smoke.PLAN),'e3b86ea5be1482c7352552459ab14df365789f12b74e37c746adcdb1b529321d')
        self.assertEqual(smoke.PLAN['occurrences'],68)
        self.assertFalse(smoke.PLAN['earlier_results_superseded'])

    def test_guard_before_any_operation(self):
        with self.assertRaises(ContractError):smoke.execute_smoke(None)
        with self.assertRaises(ContractError):smoke.prepare('/absent','a'*64)
        with self.assertRaises(ContractError):smoke.worker_main('/absent','consumer')
        for stage,role in [(STAGE,'cohort'),('/tmp/other','tests'),(STAGE+'/../x','consumer')]:
            with self.assertRaises(ContractError):smoke.spec(stage,role)

    def test_transmit_exact_original_population_and_failed_prefix(self):
        clock=AppClock();rows=[]
        result=smoke.transmit(SimpleNamespace(send=rows.append),'steady',20,clock=clock.mono,pause=clock.pause)
        self.assertEqual(rows,[worker.message(i) for i in range(68)])
        self.assertEqual(audit.stimulus(result,20)['verdict'],'pass')
        calls=[]
        def send(raw):
            calls.append(raw)
            if len(calls)==4:raise KeyboardInterrupt('x'*300)
        clock=AppClock();result=smoke.transmit(SimpleNamespace(send=send),'steady',20,clock=clock.mono,pause=clock.pause)
        self.assertEqual(len(calls),4);self.assertEqual(len(result['rows']),3)
        self.assertLessEqual(len(result['error']),160);self.assertFalse(result['complete'])

    def test_prepare_exclusive_recipe_and_freeze_tamper(self):
        f=frozen();smoke.validate_freeze(f)
        for key in ('native_execution_authorized','compatibility_verified'):
            bad=deepcopy(f);bad[key]=True;bad.pop('freeze_sha256');bad['freeze_sha256']=payload_hash(bad)
            with self.assertRaises(ContractError):smoke.validate_freeze(bad)
        with TemporaryDirectory() as d:
            p=Path(d)/'case';clock=AppClock()
            with patch.object(smoke.time,'monotonic',clock.mono),patch.object(smoke,'utc_now',clock.utc),patch.object(smoke,'boot',return_value=BOOT):
                case=smoke.prepare(p,f['freeze_sha256'],execute=True);audit.verify_case(case,f)
                with self.assertRaises(FileExistsError):smoke.prepare(p,f['freeze_sha256'],execute=True)
            case['epoch']+=1;case.pop('artifact_sha256');case['artifact_sha256']=payload_hash(case)
            with self.assertRaises(ContractError):audit.verify_case(case,f)

    def test_package_inventory_refuses_escape(self):
        dist=SimpleNamespace(version='15.0.1',locate_file=lambda _:Path('/tmp'),files=['../secret'])
        with patch.object(smoke.importlib.metadata,'distribution',return_value=dist),self.assertRaises(ContractError):smoke.dependencies()
        dist.version='16'
        with patch.object(smoke.importlib.metadata,'distribution',return_value=dist),self.assertRaises(ContractError):smoke.dependencies()

    def test_full_synthetic_archive_and_native_binding_fixture(self):
        with TemporaryDirectory() as d:
            root=Path(d);f,anchor=fixture(root)
            report=audit.audit(root,expected_inventory_file_sha256=anchor,expected_freeze_sha256=f['freeze_sha256'])
            self.assertEqual(report['verdict'],'pass',report)
            self.assertEqual(report['frames'],68);self.assertFalse(report['native_origin_verified'])
            self.assertFalse(report['budget_acceptance'])
            self.assertIsNone(report['inclusive_cost']['incremental_observer_overhead'])
            with self.assertRaises(ContractError):audit.audit(root,expected_inventory_file_sha256='0'*64,expected_freeze_sha256=f['freeze_sha256'])

    def test_rehashed_changes_do_not_create_valid_smoke(self):
        for change in ('epoch','frame_limit','source','pid','release','grid','archive','limits','missing_file','wait_retry'):
            with self.subTest(change=change),TemporaryDirectory() as d:
                root=Path(d);f,_=fixture(root);c=root/'evidence/case'
                if change in ('epoch','frame_limit','source'):
                    def mutate(v):
                        if change=='epoch':v['epoch']+=1
                        elif change=='frame_limit':v['spec']['max_frames']=67
                        else:v['implementation_sources']['unexpected']='0'*64
                    replace_control(c/'case.json',mutate)
                elif change=='pid':replace_control(c/'consumer.json',lambda v:v['identity'].update(pid=99))
                elif change=='release':replace_control(c/'bindings-ready.json',lambda v:v.update(at=21))
                elif change=='grid':replace_control(c/'consumer.json',lambda v:v['resources']['rows'][1].update(target_ns=0))
                elif change=='wait_retry':
                    def mutate(v):
                        w=v['resources']['rows'][1]['waits']['rss'];w['retries']=1;w.pop('wait_sha256');w['wait_sha256']=payload_hash(w)
                    replace_control(c/'consumer.json',mutate)
                elif change=='archive':(next((c/'archive').glob('segment-*.gz'))).write_bytes(b'bad')
                elif change=='limits':
                    p=root/'evidence'/(smoke.spec(STAGE,'consumer')['unit']+'-properties.txt')
                    p.write_text(p.read_text().replace('MemoryMax=536870912','MemoryMax=999'))
                else:(c/'completion.json').unlink()
                anchor=reseal(root,f)
                with self.assertRaises((ContractError,FileNotFoundError,OSError,KeyError)):
                    audit.audit(root,expected_inventory_file_sha256=anchor,expected_freeze_sha256=f['freeze_sha256'])


    def test_missing_slot_preserves_known_budget_failure_and_unknown(self):
        with TemporaryDirectory() as d:
            root=Path(d);f,_=fixture(root);path=root/'evidence/case/consumer.json'
            def mutate(v):
                row=v['resources']['rows'][1]
                row['sample']['rss_bytes']=500000000;row['sample']['actors'][0]['rss_bytes']=500000000
                row=v['resources']['rows'][2];row['sample']=None;row['error']='read fault'
            replace_control(path,mutate);anchor=reseal(root,f)
            report=audit.audit(root,expected_inventory_file_sha256=anchor,expected_freeze_sha256=f['freeze_sha256'])
            self.assertEqual(report['verdict'],'fail');self.assertTrue(report['unknowns'])
            self.assertFalse(report['compatibility_verified'])
            self.assertEqual(report['inclusive_cost']['missed_slots'][0]['slot'],2)

    def test_inventory_extra_file_and_symlink_are_not_adopted(self):
        for kind in ('extra','symlink'):
            with self.subTest(kind=kind),TemporaryDirectory() as d:
                root=Path(d);f,anchor=fixture(root);p=root/'evidence/unexpected'
                if kind=='extra':p.write_text('extra')
                else:p.symlink_to(root/'evidence/execution-freeze.json')
                with self.assertRaises(ContractError):
                    audit.audit(root,expected_inventory_file_sha256=anchor,expected_freeze_sha256=f['freeze_sha256'])

    def test_incomplete_launch_keeps_unknown_without_promoting_prefix(self):
        with TemporaryDirectory() as d:
            root=Path(d);f,_=fixture(root);p=root/'evidence/launch-result.json';v=json.loads(p.read_text())
            v.pop('launch_sha256');v.update(complete=False,error='failed gate');v['launch_sha256']=payload_hash(v)
            p.unlink();publish(p,v);anchor=reseal(root,f)
            report=audit.audit(root,expected_inventory_file_sha256=anchor,expected_freeze_sha256=f['freeze_sha256'])
            self.assertFalse(report['complete']);self.assertFalse(report['compatibility_verified']);self.assertTrue(report['unknowns'])

    def test_fixed_production_commands_and_no_cohort_route(self):
        ops=object.__new__(smoke.SmokeProduction);ops.root=Path(STAGE);ops.specs={}
        with patch.object(smoke,'command',return_value='') as command:
            for role in ('tests','producer','consumer'):ops.start(smoke.spec(STAGE,role))
            self.assertEqual(command.call_count,3)
            for call in command.call_args_list:
                argv=call.args[0];self.assertEqual(argv[0],'systemd-run')
                self.assertIn('--property=MemoryMax=512M',argv)
                self.assertIn('--property=CPUQuota=75%',argv)
            value=smoke.spec(STAGE,'consumer');value['properties']['CPUQuota']='90%'
            with self.assertRaises(ContractError):ops.start(value)
            self.assertEqual(command.call_count,3)


class LifecycleTests(unittest.TestCase):
    def ops(self,root,fault=None):
        class Ops:
            frozen={'freeze_sha256':'a'*64,'linux_tests':1200}
            evidence=root/'evidence'
            def __init__(self):self.root=Path(STAGE);self.events=[];self.evidence.mkdir()
            def event(self,name):
                self.events.append(name)
                if name==fault:raise OSError('injected '+name)
            def preflight(self):self.event('preflight');return {'public':'same'}
            def claim(self):self.event('claim')
            def public_state(self):return {'public':'same'}
            def recheck(self,*args):self.event('recheck');return {'same':True}
            def start(self,v):self.event('start:'+v['worker_role'])
            def finish(self,unit,**kwargs):self.event('finish:'+unit.rsplit('-',1)[1])
            def capture(self,unit,**kwargs):
                role=unit.rsplit('-',1)[1];self.event('capture:'+role)
                (self.evidence/(unit+'-journal.txt')).write_text('Ran 1200 tests in 1.0s\nOK (skipped=1)\n')
                return dict(unit=unit,result='success',exec_status=0,substate='exited',observed_properties=smoke.spec(STAGE,role)['properties'])
            def stop(self,unit):self.event('stop:'+unit.rsplit('-',1)[1])
            def prepare(self):
                self.event('prepare');(self.evidence/'case').mkdir()
                worker.publish(self.evidence/'case/case.json',{'epoch':100})
            def ready(self,name,deadline):
                self.event('ready:'+name)
                actor=identity('producer',10) if name=='server-ready.json' else identity('consumer',20)
                return dict(case_sha256=worker.control(self.evidence/'case/case.json')['artifact_sha256'],at=1,identity=actor)
            def bind(self,role,ready,deadline):self.event('bind:'+role);return {'artifact_sha256':role+'-hash'}
            def publish_report(self,v):self.report=deepcopy(v);self.event('publish')
        return Ops()

    def test_success_one_regression_one_producer_one_recorder(self):
        with TemporaryDirectory() as d,patch.object(smoke.time,'monotonic',return_value=2):
            ops=self.ops(Path(d));report=smoke.execute_smoke(ops,execute=True)
            self.assertTrue(report['complete'],report)
            self.assertEqual([x for x in ops.events if x.startswith('start:')],['start:tests','start:producer','start:consumer'])
            for role in ('tests','producer','consumer'):self.assertEqual(ops.events.count('capture:'+role),1)
            self.assertFalse(report['budget_cohort_authorized'])

    def test_faults_stop_progress_capture_once_and_cleanup_only_submitted_units(self):
        for fault in ('start:tests','finish:tests','capture:tests','recheck','prepare','start:producer',
                      'ready:server-ready.json','bind:producer','start:consumer','ready:observer-ready.json',
                      'bind:consumer','finish:consumer','capture:consumer','stop:consumer'):
            with self.subTest(fault=fault),TemporaryDirectory() as d,patch.object(smoke.time,'monotonic',return_value=2):
                ops=self.ops(Path(d),fault);report=smoke.execute_smoke(ops,execute=True)
                self.assertFalse(report['complete']);self.assertIsNotNone(report['error'])
                for role in ('tests','producer','consumer'):
                    started='start:'+role in ops.events
                    self.assertEqual('stop:'+role in ops.events,started)
                    self.assertLessEqual(ops.events.count('capture:'+role),1)
                    self.assertLessEqual(ops.events.count('start:'+role),1)
                if fault in ('start:tests','finish:tests','capture:tests','recheck','prepare'):
                    self.assertNotIn('start:producer',ops.events)

    def test_failed_preflight_never_claims_or_starts(self):
        with TemporaryDirectory() as d:
            ops=self.ops(Path(d),'preflight')
            with self.assertRaises(OSError):smoke.execute_smoke(ops,execute=True)
            self.assertEqual(ops.events,['preflight'])
