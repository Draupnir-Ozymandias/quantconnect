from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_audit as audit, receive_loop_launch as launch
from tests.test_receive_loop_trial import synthetic_cases


def properties():
    return {'User':'qcrl','Group':'qcrl','MemoryMax':'536870912','TasksMax':'32',
        'NoNewPrivileges':'yes','PrivateTmp':'yes','ProtectSystem':'strict','ProtectHome':'yes',
        'RemainAfterExit':'yes','SubState':'exited','ActiveState':'active','Result':'success',
        'ExecMainCode':'1','ExecMainStatus':'0','CPUQuotaPerSecUSec':'750ms','RuntimeMaxUSec':'2min',
        'WorkingDirectory':'/var/lib/qcrl-stream/receive-loop-overhead-Test/source',
        'ReadWritePaths':'/var/lib/qcrl-stream/receive-loop-overhead-Test/evidence',
        'Id':'qcrl-loop-Test-0-baseline-consumer.service','ExecMainPID':'123',
        'ExecMainStartTimestampMonotonic':'1000000','ExecMainExitTimestampMonotonic':'4000000'}


class ReceiveLoopAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.path=self.root/'unit.properties'

    def write_properties(self,obj):
        self.path.write_text('\n'.join(k+'='+v for k,v in obj.items())+'\n')

    def test_actual_format_limits_exit_pid_cgroup_and_unknown_peak(self):
        p=properties(); self.write_properties(p)
        identity={'pid':123,'boot_id':'boot','cgroup':'0::/system.slice/'+p['Id']+'\n'}
        result=audit.verify_unit(self.path,'consumer',identity=identity,boot_id='boot')
        self.assertEqual(result['exit_us'],4000000); self.assertIsNone(result['memory_peak_bytes'])
        self.assertEqual(audit.duration_us('2min'),120000000)
        for change in ({'pid':124},{'boot_id':'wrong'},{'cgroup':'0::/system.slice/other.service\n'}):
            bad=dict(identity,**change)
            with self.assertRaises(ContractError): audit.verify_unit(self.path,'consumer',identity=bad,boot_id='boot')

    def test_changed_limits_security_and_failed_unit_rejected(self):
        for key,value in (('MemoryMax','1073741824'),('CPUQuotaPerSecUSec','1s'),
                          ('RuntimeMaxUSec','3min'),('TasksMax','64'),('NoNewPrivileges','no'),
                          ('Result','timeout'),('ExecMainStatus','1'),('ExecMainCode','2'),
                          ('ReadWritePaths','/'),('WorkingDirectory','/opt/qcrl-stream'),
                          ('ExecMainExitTimestampMonotonic','0')):
            p=properties(); p[key]=value; self.write_properties(p)
            with self.assertRaises(ContractError): audit.verify_unit(self.path,'consumer')

    def test_duplicate_missing_unbounded_and_nonfinite_properties_rejected(self):
        p=properties(); self.write_properties(p)
        with self.path.open('a') as handle: handle.write('TasksMax=32\n')
        with self.assertRaises(ContractError): audit.parse_properties(self.path)
        for value in ('infinity','[not set]','nan','-1s','2.0min'):
            with self.assertRaises(ContractError): audit.duration_us(value)
        del p['MemoryMax']; self.write_properties(p)
        with self.assertRaises(ContractError): audit.verify_unit(self.path,'consumer')

    def test_producer_quota_and_bounded_window(self):
        p=properties(); p['CPUQuotaPerSecUSec']='1s'; self.write_properties(p)
        result=audit.verify_unit(self.path,'producer')
        measurement={'begin_monotonic':1.1,'end_monotonic':3,'post_window_finished_monotonic':3.5}
        audit.validate_window(result,measurement)
        for key,value in (('begin_monotonic',.5),('post_window_finished_monotonic',4.5),('end_monotonic',float('nan'))):
            bad=dict(measurement,**{key:value})
            with self.assertRaises(ContractError): audit.validate_window(result,bad)

    def origin(self):
        evidence=self.root/'evidence'; evidence.mkdir()
        for name in ('launch-manifest.json','launch-claim.json'):
            (self.root/name).write_text('{}'); (evidence/name).write_text('{}')
        (evidence/'raw.txt').write_text('untouched bytes')
        obj=launch.origin_inventory(evidence); obj['inventory_sha256']=payload_hash(obj)
        path=self.root/'origin-inventory.json'; path.write_text(json.dumps(obj))
        return file_hash(path),obj

    def test_external_anchor_and_exact_population_not_just_inner_digest(self):
        anchor,_=self.origin(); audit.verify_origin(self.root,anchor)
        with self.assertRaises(ContractError): audit.verify_origin(self.root,'a'*64)
        raw=self.root/'evidence'/'raw.txt'; raw.write_text('modified bytes')
        with self.assertRaises(ContractError): audit.verify_origin(self.root,anchor)
        raw.write_text('untouched bytes'); (self.root/'evidence'/'extra.txt').write_text('extra')
        with self.assertRaises(ContractError): audit.verify_origin(self.root,anchor)

    def test_deleted_file_and_outer_metadata_rejected(self):
        anchor,_=self.origin(); (self.root/'launch-manifest.json').write_text('{"changed":true}')
        with self.assertRaises(ContractError): audit.verify_origin(self.root,anchor)
        (self.root/'launch-manifest.json').write_text('{}'); (self.root/'evidence'/'raw.txt').unlink()
        with self.assertRaises(ContractError): audit.verify_origin(self.root,anchor)

    def test_traversal_alias_and_symlink_rejected_even_with_new_anchor(self):
        anchor,obj=self.origin()
        for name in ('../escape','/absolute','./raw.txt','folder//file'):
            bad=deepcopy(obj); bad['files'][name]='a'*64; bad.pop('inventory_sha256'); bad['inventory_sha256']=payload_hash(bad)
            path=self.root/'origin-inventory.json'; path.write_text(json.dumps(bad))
            with self.assertRaises(ContractError): audit.verify_origin(self.root,file_hash(path))
        (self.root/'origin-inventory.json').write_text(json.dumps(obj))
        (self.root/'evidence'/'link').symlink_to(self.root/'evidence'/'raw.txt')
        with self.assertRaises(ContractError): audit.verify_origin(self.root,file_hash(self.root/'origin-inventory.json'))

    def audit_fixture(self):
        evidence=self.root/'evidence'; evidence.mkdir()
        trial_root=evidence/'trial'; trial_root.mkdir()
        state={'environment_sha256':'a'*64,'public_head':'b'*40,
               'collectors':{n:('active' if n.endswith('.timer') else 'inactive') for n in launch.SERVICES}}
        boot='12345678-1234-1234-1234-123456789abc'; commit='f'*40
        declaration={'fixture_only':True}; declaration['plan_sha256']=payload_hash(declaration)
        (trial_root/'preregistration.json').write_text(json.dumps(declaration))
        repo=Path(audit.__file__).resolve().parents[2]
        manifest={'before':state,'source_commit':commit,'boot_id':boot,
            'sources':{n:file_hash(repo/n) for n in launch.FILES},
            'schema_version':'qcrl.receive_loop_launch_manifest.v1',
            'preregistration_sha256':declaration['plan_sha256'],'pair_order':audit.plan.POLICY['pair_order'],
            'public_rollout_authorized':False,'orders_authorized':False}
        manifest['launch_manifest_sha256']=payload_hash(manifest)
        claim={'schema_version':'qcrl.receive_loop_launch_claim.v1','pid':100,'started_monotonic':.5,
               'boot_id':boot,'replay_authorized':False}
        for name,obj in (('launch-manifest.json',manifest),('launch-claim.json',claim)):
            (evidence/name).write_text(json.dumps(obj)); (self.root/name).write_text(json.dumps(obj))
        for name in ('public-before.json','public-after.json'): (evidence/name).write_text(json.dumps(state))
        order=[{'pair':p,'lane':s} for p,lanes in enumerate(audit.plan.POLICY['pair_order']) for s in lanes]
        result={'schema_version':'qcrl.receive_loop_launch_result.v1','completed':order,'error':None,
            'preservation_errors':[],'measurement_complete':True,'resource_and_origin_audit_performed':False,
            'overhead_acceptance_established':False,'public_rollout_authorized':False,'orders_authorized':False}
        (evidence/'launch-result.json').write_text(json.dumps(result))
        def write(path,obj): path.write_text('\n'.join(k+'='+v for k,v in obj.items())+'\n')
        p=properties(); p['Id']='qcrl-loop-Test-tests.service'; write(evidence/'tests-unit.properties',p)
        cases=synthetic_cases(); by={(c['pair'],c['lane']):c for c in cases}
        for i,item in enumerate(order):
            pair,selected=item['pair'],item['lane']; case=trial_root/str(pair)/selected; case.mkdir(parents=True)
            identities={}
            for role,offset in (('producer',0),('consumer',1)):
                p=properties(); p['Id']='qcrl-loop-Test-'+str(pair)+'-'+selected+'-'+role+'.service'
                p['ExecMainPID']=str(200+i*2+offset); p['CPUQuotaPerSecUSec']='1s' if role=='producer' else '750ms'
                p['ExecMainStartTimestampMonotonic']=str((5+i*10+offset)*1000000)
                p['ExecMainExitTimestampMonotonic']=str((8+i*10+offset)*1000000)
                write(case/(role+'-unit.properties'),p)
                identities[role]={'pid':int(p['ExecMainPID']),'boot_id':boot,'cgroup':'0::/system.slice/'+p['Id']+'\n'}
            for name,key,role,field in (('ready.json','producer_identity','producer','ready_sha256'),
                                       ('deliveries.json','consumer_identity','consumer','delivery_sha256')):
                obj={key:identities[role]}; obj[field]=payload_hash(obj); (case/name).write_text(json.dumps(obj))
            c=by[(pair,selected)]; c['measurement']={'begin_monotonic':6.1+i*10,'end_monotonic':7+i*10,
                'post_window_finished_monotonic':7.5+i*10,'consumer_identity':identities['consumer']}
            c['metrics']['consumer_timed_cpu_seconds']=1
            c['case_report_sha256']='c'*64; c['measurement_sha256']='d'*64
        return commit,by

    def reanchor(self):
        inventory=launch.origin_inventory(self.root/'evidence'); inventory['inventory_sha256']=payload_hash(inventory)
        path=self.root/'origin-inventory.json'; path.write_text(json.dumps(inventory)); return file_hash(path)

    def test_metadata_pipeline_combines_gate_only_after_independent_checks(self):
        commit,by=self.audit_fixture(); anchor=self.reanchor()
        # Mock only the already separately-tested full archive/corpus layer.
        with patch.object(audit.plan,'validate'),patch.object(audit.trial,'verify_case',side_effect=lambda root,p,s,**kw:by[(p,s)]):
            result=audit.audit(self.root,expected_inventory_file_sha256=anchor,expected_source_commit=commit)
            self.assertEqual(result['resource_and_origin_gate'],'verified')
            self.assertEqual(result['advancement'],'diagnostic_interval_analysis_only')
            self.assertEqual(len(result['units']),13); self.assertFalse(result['public_rollout_authorized'])
            by[(0,'instrumented')]['metrics']['consumer_timed_cpu_seconds']=2
            self.assertEqual(audit.audit(self.root,expected_inventory_file_sha256=anchor,
                expected_source_commit=commit)['advancement'],'reject')

    def test_reanchored_wrong_actual_order_still_rejected(self):
        commit,by=self.audit_fixture()
        path=self.root/'evidence'/'trial'/'1'/'instrumented'/'producer-unit.properties'
        value=path.read_text().replace('ExecMainStartTimestampMonotonic=25000000',
                                      'ExecMainStartTimestampMonotonic=17000000')
        path.write_text(value); anchor=self.reanchor()
        with patch.object(audit.plan,'validate'),patch.object(audit.trial,'verify_case',side_effect=lambda root,p,s,**kw:by[(p,s)]):
            with self.assertRaisesRegex(ContractError,'worker ordering'):
                audit.audit(self.root,expected_inventory_file_sha256=anchor,expected_source_commit=commit)


if __name__=='__main__': unittest.main()
