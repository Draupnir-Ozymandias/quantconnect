"""Single-case routing, prospective freezes, retained faults and raw auxiliary pairs."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_rss_thread_cpu_validation as validation
from infra.stream import recorder_persistence_cohort as base
from infra.stream import recorder_persistence_cohort_audit as audit
from infra.stream import recorder_persistence_worker as worker
from infra.stream.recorder_application_resources import RSS_THREAD_CPU_POLICY
from tests import test_recorder_rss_thread_cpu as cpu_tests

STAGE='/var/lib/qcrl-stream/recorder-persistence-OfflineRssCpu'


class ValidationTests(unittest.TestCase):
    def test_identity_and_exact_three_unit_routing(self):
        self.assertEqual(payload_hash(validation.PLAN),'455cf599c150eb08cab9840103a3a114900dc0524289c82d700c67b215379e96')
        self.assertEqual(validation.PLAN['case_order'],['mixed-0'])
        self.assertEqual(len(base.PLAN['case_order']),6)
        ops=object.__new__(validation.Production);ops.root=Path(STAGE);ops.evidence=ops.root/'evidence';ops.specs={};ops.case_name=None
        with patch.object(base,'command',return_value='') as command:
            ops.start(base.spec(STAGE,'tests'));ops.case_name='mixed-0'
            for role in ('producer','consumer'):ops.start(base.spec(STAGE,role,'mixed-0'))
            self.assertEqual(len(command.call_args_list),3)
            for call in command.call_args_list[1:]:self.assertIn(validation.MODULE,call.args[0])
            ops.case_name='steady-0'
            with self.assertRaises(ContractError):ops.start(base.spec(STAGE,'consumer','steady-0'))
        self.assertEqual(base.spec(STAGE,'tests')['properties']['MemoryMax'],'1G')
        self.assertEqual(base.spec(STAGE,'consumer','mixed-0')['properties']['MemoryMax'],'512M')
        with self.assertRaises(ContractError):validation.worker_main('/unused','consumer','mixed-0')

    def run_fake(self, fault=None):
        with TemporaryDirectory() as d:
            class Ops:
                root=Path(STAGE);case_name=None;frozen=dict(linux_tests=1200,freeze_sha256='a'*64)
                def __init__(self):self.evidence=Path(d);self.events=[]
                def preflight(self):return {'public':'unchanged'}
                def claim(self):self.events.append(('claim',None))
                def start(self,v):self.events.append(('start',v['unit']))
                def finish(self,unit,**kw):
                    if unit.endswith('-tests'):
                        (self.evidence/(unit+'-journal.txt')).write_text('Ran '+('1199' if fault=='readiness' else '1200')+' tests in 1s\nOK (skipped=1)\n')
                def capture(self,unit,**kw):
                    self.events.append(('capture',unit))
                    role='tests' if unit.endswith('-tests') else unit.rsplit('-',1)[-1]
                    return dict(unit=unit,result='success',exec_status=0,substate='exited',observed_properties=base.spec(STAGE,role,None if role=='tests' else self.case_name)['properties'])
                def stop(self,unit):self.events.append(('stop',unit))
                def recheck(self,*args):return {'unchanged':True}
                def public_state(self):return {'public':'unchanged'}
                def prepare(self,name):
                    self.case_name=name;path=self.evidence/name;path.mkdir()
                    self.case=worker.publish(path/'case.json',dict(case=name,epoch=100));self.events.append(('prepare',name))
                def ready(self,name,deadline):
                    role='producer' if name=='server-ready.json' else 'consumer'
                    return dict(case_sha256=self.case['artifact_sha256'],at=1,identity={'boot_id':'boot','cgroup':'/'+role})
                def bind(self,role,*args):return {'artifact_sha256':role+'-binding'}
                def publish_report(self,report):self.report=report
            ops=Ops()
            def lifecycle(*args):
                if fault=='completion':raise ContractError('retained completion fault')
            with patch.object(base.time,'monotonic',return_value=2),patch.object(base,'verify_case_lifecycle',side_effect=lifecycle):
                result=base.execute_cohort(ops,execute=True,protocol=validation)
            return result,ops.events

    def test_one_pair_after_readiness_and_no_replay_on_fatal_conditions(self):
        for fault in (None,'readiness','completion'):
            report,events=self.run_fake(fault)
            self.assertEqual(report['cohort_plan_sha256'],payload_hash(validation.PLAN))
            starts=[v for k,v in events if k=='start']
            self.assertEqual(len(starts),1 if fault=='readiness' else 3)
            self.assertEqual(report['completed'],['mixed-0'] if fault is None else [])
            self.assertEqual(report['complete'],fault is None)
            for unit in starts:
                self.assertEqual(events.count(('stop',unit)),1);self.assertEqual(events.count(('capture',unit)),1)

    def freeze_fixture(self):
        sources=validation.declaration()['sources']
        sources=dict(sources,**{'stable.py':'b'*64})
        baseline_sources=dict(sources);baseline_sources['infra/stream/recorder_application_resources.py']='c'*64
        host=dict(instance_id='instance',region='us-east-2',instance_type='t4g.small',credit_mode='standard',
                  boot_id='boot',observed_utc='fresh',public={'collectors':{'timer':'active'}})
        runtime=dict(wait={},websockets={},boot_id='boot',host=host,
            thread_clock=dict(implementation='clock_gettime(CLOCK_THREAD_CPUTIME_ID)',resolution=1e-9,monotonic=True,adjustable=False,callable=True))
        baseline=dict(source_commit=validation.BASE_COMMIT,sources=baseline_sources,runtime=runtime)
        baseline['freeze_sha256']=payload_hash(baseline)
        lineage=dict(baseline_freeze=baseline,baseline_audit_sha256=validation.BASE_AUDIT,
            baseline_outcome_sha256=validation.BASE_OUTCOME,baseline_failed_verdict_preserved=True,
            reviewed_source_delta=validation.source_delta(baseline_sources,sources))
        return sources,runtime,lineage

    def test_freeze_exact_delta_clock_and_failed_baseline_anchors(self):
        sources,runtime,lineage=self.freeze_fixture()
        with patch.object(validation,'BASE_FREEZE',lineage['baseline_freeze']['freeze_sha256']), \
             patch.object(validation,'validate_runtime'),patch.object(validation,'verify_host'):
            frozen=validation.freeze('1'*40,sources,runtime,1200,lineage)
            self.assertEqual(validation.validate_freeze(frozen,lineage),frozen)
            for mutation in ('extra_code','clock','credit','baseline','readiness','authority'):
                s,r,l=deepcopy(sources),deepcopy(runtime),deepcopy(lineage)
                if mutation=='extra_code':
                    s['stable.py']='d'*64;l['reviewed_source_delta']=validation.source_delta(l['baseline_freeze']['sources'],s)
                if mutation=='clock':r['thread_clock']['monotonic']=False
                if mutation=='credit':r['host']['credit_mode']='unlimited'
                if mutation=='baseline':l['baseline_failed_verdict_preserved']=False
                with self.subTest(mutation=mutation),self.assertRaises(ContractError):
                    if mutation=='authority':
                        bad=deepcopy(frozen);bad.pop('freeze_sha256');bad['orders_authorized']=True;bad['freeze_sha256']=payload_hash(bad)
                        validation.validate_freeze(bad,lineage)
                    else:validation.freeze('1'*40,s,r,True if mutation=='readiness' else 1200,l)

    def auxiliary_fixture(self, root, *, wide=True, cpu_fault=False):
        reader=cpu_tests.RssThreadCpuTests().reader(root)
        if cpu_fault:
            def fault():raise OSError('injected')
            reader.thread_cpu_ns=fault
        values=iter([10.,10.001]+[n for i in range(71) for n in (10.+i,10.+i+(.006 if wide and i==10 else .001))])
        reader.clock=lambda:next(values)
        case=worker.publish(root/'case.json',dict(epoch=10.,case='mixed-0'))
        initial=reader.read(rss=True);rows=[dict(slot=i,sample=reader.read(rss=True),cpu_before=None) for i in range(71)]
        policy=payload_hash(RSS_THREAD_CPU_POLICY)
        worker.publish(root/'observer-ready.json',dict(case_sha256=case['artifact_sha256'],identity=reader.expected,
            rss_thread_cpu_policy_sha256=policy,initial=initial))
        worker.publish(root/'consumer.json',dict(case_sha256=case['artifact_sha256'],identity=reader.expected,
            rss_thread_cpu_policy_sha256=policy,resources=dict(rows=rows),closed=80.))

    def test_auxiliary_raw_pairs_and_inconclusive_result_not_application_acceptance(self):
        for wide,fault,usefulness in [(True,False,'paired_measurement_available'),(False,False,'inconclusive_no_wide_valid_pair'),
                                      (True,True,'inconclusive_no_wide_valid_pair')]:
            with self.subTest(wide=wide,fault=fault),TemporaryDirectory() as d:
                root=Path(d);self.auxiliary_fixture(root,wide=wide,cpu_fault=fault)
                report=validation.auxiliary(root,{})
                self.assertEqual(report['usefulness'],usefulness)
                self.assertEqual(report['complete'],not fault)
                self.assertEqual(len(report['rows']),72)
                self.assertFalse(report['thresholds_compensated'])
                self.assertIsNone(report['incremental_overhead'])
                if wide:self.assertAlmostEqual(report['rows'][11]['wall_seconds'],.006)

    def test_auxiliary_rehashed_copy_wrong_policy_and_missing_sample(self):
        for mutation in ('copy','policy','missing'):
            with self.subTest(mutation=mutation),TemporaryDirectory() as d:
                root=Path(d);self.auxiliary_fixture(root)
                value=worker.control(root/'consumer.json');value.pop('artifact_sha256')
                if mutation=='copy':value['resources']['rows'][1]['sample']['rss_thread_cpu']=value['resources']['rows'][0]['sample']['rss_thread_cpu']
                if mutation=='policy':value['rss_thread_cpu_policy_sha256']='wrong'
                if mutation=='missing':value['resources']['rows'][1]['sample']=None
                (root/'consumer.json').unlink();worker.publish(root/'consumer.json',value)
                if mutation=='missing':self.assertFalse(validation.auxiliary(root,{})['complete'])
                else:
                    with self.assertRaises(ContractError):validation.auxiliary(root,{})

    def test_auxiliary_never_promotes_failed_application_verdict(self):
        with TemporaryDirectory() as d:
            root=Path(d);(root/'evidence').mkdir();(root/'evidence/execution-freeze.json').write_text('{}')
            with patch.object(audit,'audit',return_value=dict(complete=True,verdict='fail',application_budget_pass=False)), \
                 patch.object(validation,'auxiliary',return_value=dict(complete=True,usefulness='paired_measurement_available')):
                report=validation.audit(root)
            self.assertEqual(report['verdict'],'fail');self.assertFalse(report['application_budget_pass'])

    def test_new_case_declaration_cannot_be_audited_as_old_cohort(self):
        from tests.test_market_stream import Clock
        clock=Clock()
        with TemporaryDirectory() as d:
            with patch.object(base.time,'monotonic',clock.mono),patch.object(base,'utc_now',clock.utc),patch.object(base,'boot',return_value='fixture'):
                case=base.prepare(Path(d)/'mixed-0','a'*64,'mixed-0',execute=True,protocol=validation)
            frozen=dict(freeze_sha256='a'*64,runtime=dict(boot_id='fixture'))
            self.assertEqual(audit.verify_case(case,frozen,protocol=validation),case)
            binding=worker.control(Path(d)/'mixed-0/absolute-wait-plan.json')
            self.assertEqual(binding['declaration'],validation.declaration())
            with self.assertRaises(ContractError):audit.verify_case(case,frozen)
            changed=deepcopy(case);changed.pop('artifact_sha256');changed['spec']['max_frames']=59999
            changed['artifact_sha256']=payload_hash(changed)
            with self.assertRaises(ContractError):audit.verify_case(changed,frozen,protocol=validation)

    def test_independent_inventory_audit_expects_one_case_and_new_worker_module(self):
        from tests import test_recorder_persistence_cohort as fixtures
        with TemporaryDirectory() as d:
            root=Path(d);fixture=fixtures.OriginAuditTests()
            frozen=fixture.fixture(root)
            path=root/'evidence/launch-result.json';launch=json.loads(path.read_text());launch.pop('launch_sha256')
            launch.update(completed=['mixed-0'],cohort_plan_sha256=payload_hash(validation.PLAN))
            launch['launch_sha256']=payload_hash(launch);path.write_text(json.dumps(launch));anchors=fixture.seal(root)
            def checked(e,name,frozen,stage,test_end,previous,**kwargs):
                self.assertEqual(name,'mixed-0');self.assertIs(kwargs['protocol'],validation)
                return dict(case=name,failures=['utc'],unknowns=[]),previous+100,{}
            with patch.object(validation,'validate_freeze',return_value=frozen),patch.object(audit,'audit_case_native',side_effect=checked) as call:
                report=audit.audit(root,protocol=validation,**anchors)
            call.assert_called_once();self.assertEqual(report['verdict'],'fail')
