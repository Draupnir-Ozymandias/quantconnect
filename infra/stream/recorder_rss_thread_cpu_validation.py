"""One prospective mixed-case RSS CPU validation, reusing recorder lifecycle/gates."""
import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import pwd
import re
import sys
import time

from execution_truth.contracts import payload_hash, verify_artifact_hash, ContractError
from execution_truth.stream_segments import file_hash, exclusive_json
from infra.stream import recorder_persistence_cohort as base
from infra.stream import recorder_persistence_cohort_audit as base_audit
from infra.stream import recorder_persistence_worker as worker
from infra.stream.recorder_absolute_observer import observe_absolute
from infra.stream.recorder_application_resources import RSS_THREAD_CPU_POLICY, verify_rss_thread_cpu
from infra.stream.recorder_application_audit import verify_host
from infra.stream.recorder_wait_execution import validate_runtime, selected

MODULE = 'infra.stream.recorder_rss_thread_cpu_validation'
ROOT, PYTHON, STAGE, require = base.ROOT, base.PYTHON, base.STAGE, base.require
PLAN = dict(schema_version='qcrl.recorder_rss_cpu_validation_plan.v1',
    parent_cohort_plan_sha256=payload_hash(base.PLAN), case_order=['mixed-0'],
    occurrences_per_case=60000, total_occurrences=60000, readiness_units=1,
    producer_units=1, consumer_units=1, measurement_runs=1,
    rss_thread_cpu_policy_sha256=payload_hash(RSS_THREAD_CPU_POLICY),
    capture_seconds=180, epoch_lead_seconds=20, readiness_margin_seconds=.1,
    resource_limits='unchanged_512MiB_75percent_32tasks_240s',
    readiness_envelope_sha256=payload_hash(base.READINESS_ENVELOPE),
    budgets='unchanged_wall_and_resource_gates_no_subtraction',
    stop='one_readiness_then_one_pair_no_retry_replay_replacement_or_cohort',
    no_wide_bracket='inconclusive_no_automatic_repeat', credit_balance_minimum=None,
    native_execution_authorized=False, acceptance_demonstrated=False, orders_authorized=False)
BASE_COMMIT = '4926d62faab552af8a3c8e3fe964dc16052e4773'
BASE_FREEZE = '6428a09a34633987a353c32beeca340be535b33c1e11aa897f291d37a4da434b'
BASE_AUDIT = 'c9296f31e5c89efb3071f883cdf15ff54f3ae1bbace64e70c01f2f1488f67618'
BASE_OUTCOME = '51609e2ecca1b155d0ea3a631b3961ee46b207489be49504dc0840782ce71b64'
REVIEWED_CODE = {'infra/stream/recorder_application_resources.py',
    'infra/stream/recorder_persistence_worker.py','infra/stream/recorder_persistence_cohort.py',
    'infra/stream/recorder_persistence_cohort_audit.py', MODULE.replace('.','/')+'.py',
    'tests/test_recorder_rss_thread_cpu.py','tests/test_recorder_rss_thread_cpu_validation.py'}


def declaration():
    value = base.declaration(); value.pop('declaration_sha256')
    value.update(schema_version='qcrl.recorder_rss_cpu_validation_declaration.v1',
        plan=deepcopy(PLAN), plan_sha256=payload_hash(PLAN),
        rss_thread_cpu_policy=deepcopy(RSS_THREAD_CPU_POLICY))
    for name in (MODULE.replace('.','/')+'.py','tests/test_recorder_rss_thread_cpu.py',
                 'tests/test_recorder_rss_thread_cpu_validation.py','docs/RECORDER_RSS_THREAD_CPU_V1.md'):
        value['sources'][name] = file_hash(ROOT/name)
    value['declaration_sha256'] = payload_hash(value)
    return value


def runtime(root):
    value = base.runtime(root)
    info = time.get_clock_info('thread_time')
    value['thread_clock'] = dict(implementation=info.implementation, resolution=info.resolution,
        monotonic=info.monotonic, adjustable=info.adjustable, callable=callable(time.thread_time_ns))
    return value


def source_delta(before, after):
    return {n:dict(before=before.get(n),after=after.get(n)) for n in sorted(set(before)|set(after))
            if before.get(n) != after.get(n)}


def freeze(commit, sources, installed, linux_tests, lineage):
    baseline=lineage['baseline_freeze'];verify_artifact_hash(baseline,'freeze_sha256','baseline freeze')
    require(baseline['freeze_sha256']==BASE_FREEZE and baseline['source_commit']==BASE_COMMIT
        and lineage['baseline_audit_sha256']==BASE_AUDIT and lineage['baseline_outcome_sha256']==BASE_OUTCOME
        and lineage['baseline_failed_verdict_preserved'] is True,'failed baseline anchors differ')
    delta=source_delta(baseline['sources'],sources)
    require(delta==lineage['reviewed_source_delta'] and delta
        and all(n.endswith('.md') or n in REVIEWED_CODE for n in delta)
        and all(entry['after'] is not None for entry in delta.values()),'unreviewed source delta/removal')
    validate_runtime(installed['wait']);verify_host(installed['host'])
    for key in ('wait','websockets','boot_id'):
        require(installed[key]==baseline['runtime'][key],'installed baseline runtime changed: '+key)
    for key in ('instance_id','region','instance_type','credit_mode','public'):
        require(installed['host'][key]==baseline['runtime']['host'][key],'host/public configuration changed: '+key)
    clock=installed['thread_clock']
    require(clock['monotonic'] is True and clock['adjustable'] is False and clock['callable'] is True
        and type(clock['resolution']) in (int,float) and math.isfinite(clock['resolution']) and clock['resolution']>0
        and clock['implementation']=='clock_gettime(CLOCK_THREAD_CPUTIME_ID)', 'native thread CPU clock differs')
    require(installed['boot_id']==installed['host']['boot_id'] and installed['host']['observed_utc'], 'fresh host/boot required')
    require(re.fullmatch('[0-9a-f]{40}',commit) and type(linux_tests) is int and linux_tests>=1186,
        'exact candidate/readiness population required')
    require(all(sources.get(n)==h for n,h in declaration()['sources'].items())
        and all(selected(n) and re.fullmatch('[0-9a-f]{64}',h) for n,h in sources.items()),'full source inventory required')
    value=dict(schema_version='qcrl.recorder_rss_cpu_validation_freeze.v1',source_commit=commit,
        sources=deepcopy(sources),runtime=deepcopy(installed),observer=declaration(),
        cohort_plan_sha256=payload_hash(PLAN),linux_tests=linux_tests,linux_skips=1,
        lineage_sha256=payload_hash(lineage),native_execution_authorized=False,
        acceptance_demonstrated=False,orders_authorized=False)
    value['freeze_sha256']=payload_hash(value)
    return value


def validate_freeze(value, lineage=None):
    verify_artifact_hash(value,'freeze_sha256','RSS CPU validation freeze')
    require(value['schema_version']=='qcrl.recorder_rss_cpu_validation_freeze.v1'
        and value['observer']==declaration() and value['cohort_plan_sha256']==payload_hash(PLAN)
        and all(value[k] is False for k in ('native_execution_authorized','acceptance_demonstrated','orders_authorized')),
        'RSS CPU validation declaration/authority differs')
    require(all(value['sources'].get(n)==h for n,h in value['observer']['sources'].items()), 'declaration source absent')
    if lineage is not None:
        require(value==freeze(value['source_commit'],value['sources'],value['runtime'],value['linux_tests'],lineage),
            'RSS CPU full freeze/lineage differs')
    return value


def worker_main(root, role, case_name, *, execute=False):
    root=Path(root)
    require(execute is True and platform.system()=='Linux' and os.geteuid()==pwd.getpwnam('qcrl').pw_uid
        and case_name=='mixed-0' and root==ROOT.parent/'evidence'/case_name
        and re.fullmatch(STAGE,str(ROOT.parent)) and os.path.abspath(sys.executable)==PYTHON,
        'canonical explicit Linux single mixed worker required')
    frozen=validate_freeze(base.load(ROOT.parent/'execution-freeze.json'),base.load(ROOT.parent/'compatibility-lineage.json'))
    sources,commit=base.inspect_source(ROOT)
    require(sources==frozen['sources'] and commit==frozen['source_commit'] and runtime(ROOT.parent)==frozen['runtime'],
        'RSS CPU source/runtime drift')
    if role=='prepare':
        return base.prepare(root,frozen['freeze_sha256'],case_name,execute=True,protocol=sys.modules[__name__])
    case=worker.control(root/'case.json');base_audit.verify_case(case,frozen,protocol=sys.modules[__name__])
    binding=worker.control(root/'absolute-wait-plan.json')
    require(binding['case_sha256']==case['artifact_sha256'] and binding['declaration']==declaration(), 'RSS CPU binding differs')
    from infra.stream.recorder_application_budget import declare
    if role=='producer':return worker.produce(root,declare(),execute=True,transmitter=base.transmit)
    require(role=='consumer','unknown RSS CPU worker role')
    return worker.consume(root,declare(),execute=True,rss_thread_cpu=True,
        resource_observer=lambda reader,epoch,stop: observe_absolute(reader,epoch,stop,execute=True))


class Production(base.CohortProduction):
    def __init__(self, root, frozen, *, execute=False):
        self.root=Path(root);self.frozen=validate_freeze(frozen,base.load(self.root/'compatibility-lineage.json'))
        self.evidence=self.root/'evidence';self.specs={};self.case_name=None
        require(execute is True and platform.system()=='Linux' and os.geteuid()==0
            and re.fullmatch(STAGE,str(self.root)) and self.root.resolve(strict=True)==self.root
            and ROOT==self.root/'source' and os.path.abspath(sys.executable)==PYTHON,
            'explicit canonical Linux root RSS CPU stage required')

    def recheck(self, stage, frozen):
        sources,commit=base.inspect_source(self.root/'source')
        return dict(clean_source=True,source_freeze_matches=sources==frozen['sources'] and commit==frozen['source_commit'],
                    runtime_freeze_matches=runtime(self.root)==frozen['runtime'])

    def start(self, value):
        role=value['worker_role'];require(value==base.spec(str(self.root),role,self.case_name)
            and (role=='tests' or self.case_name=='mixed-0'),'single mixed unit only')
        self.specs[value['unit']]=value
        args=['-m','unittest','discover','-s','tests','-q'] if role=='tests' else [
            '-m',MODULE,'--root',str(self.evidence/self.case_name),'--worker',role,'--case',self.case_name,'--execute']
        base.command(['systemd-run','--unit='+value['unit'],'--working-directory='+str(self.root/'source'),
            *['--property='+k+'='+v for k,v in value['properties'].items()],PYTHON,*args],execute=True)

    def prepare(self, case_name):
        require(case_name=='mixed-0','one mixed case only');self.case_name=case_name
        base.command(['sudo','-u','qcrl',PYTHON,'-B','-m',MODULE,'--root',str(self.evidence/case_name),
            '--worker','prepare','--case',case_name,'--execute'],timeout=30,execute=True)


def auxiliary(root, frozen):
    """Report linked raw pairs; auxiliary usefulness never compensates a wall gate."""
    root=Path(root);case=worker.control(root/'case.json');ready=worker.control(root/'observer-ready.json')
    consumer=worker.control(root/'consumer.json');policy=payload_hash(RSS_THREAD_CPU_POLICY)
    require(ready['case_sha256']==consumer['case_sha256']==case['artifact_sha256']
        and ready['rss_thread_cpu_policy_sha256']==consumer['rss_thread_cpu_policy_sha256']==policy
        and ready['identity']==consumer['identity'],'RSS CPU publication policy/case/owner differs')
    thread=ready['initial']['rss_thread_cpu']['thread_id'];rows=[];unknowns=[];wide=[]
    slots=[r['slot'] for r in consumer['resources']['rows']]
    require(all(type(slot) is int and 0<=slot<184 for slot in slots) and len(slots)==len(set(slots)),
        'RSS CPU resource slot population differs')
    required=range(math.ceil(max(70,consumer['closed']-case['epoch']))+1)
    unknowns.extend(str(slot)+':missing_resource_slot' for slot in required if slot not in slots)
    population=[('initial',ready['initial'])]+[(r['slot'],r['sample']) for r in consumer['resources']['rows']]
    for label,sample in population:
        if sample is None:
            unknowns.append(str(label)+':missing_resource_sample');rows.append(dict(slot=label,status='unknown'));continue
        require(sample['owner']==consumer['identity'],'RSS CPU owner differs')
        value=verify_rss_thread_cpu(sample,expected_thread_id=thread)
        width=sample['after']-sample['before']
        anomaly=value['status']=='observed' and value['delta_ns']>width*1e9
        row=dict(slot=label,before=sample['before'],after=sample['after'],wall_seconds=width,
            cpu_ns=value['delta_ns'],status=value['status'],error=value['error'],witness_sha256=value['witness_sha256'])
        row['cpu_exceeds_wall_no_clamping']=anomaly
        rows.append(row)
        if value['status']!='observed':unknowns.append(str(label)+':cpu_unknown')
        if anomaly:unknowns.append(str(label)+':cpu_wall_relationship_requires_review')
        if label!='initial' and width>.005 and value['status']=='observed' and not anomaly:wide.append(label)
    require(all(r['cpu_before'] is None or 'rss_thread_cpu' not in r['cpu_before'] for r in consumer['resources']['rows']),
        'CPU pre-read unexpectedly instrumented')
    return dict(schema_version='qcrl.rss_cpu_validation_auxiliary.v1',policy_sha256=policy,
        complete=not unknowns,unknowns=unknowns,rows=rows,wide_slots_with_cpu=wide,
        question='linked_thread_CPU_and_wall_pair_for_wide_RSS_bracket',
        usefulness='paired_measurement_available' if wide else 'inconclusive_no_wide_valid_pair',
        incremental_overhead=None,exact_off_cpu_duration=None,thresholds_compensated=False)


def audit(root, **anchors):
    report=base_audit.audit(root,protocol=sys.modules[__name__],**anchors)
    frozen=base.load(Path(root)/'evidence/execution-freeze.json')
    try:report['auxiliary']=auxiliary(Path(root)/'evidence/mixed-0',frozen)
    except (ContractError,KeyError,TypeError,ValueError,OSError) as exc:
        report['auxiliary']=dict(complete=False,usefulness='unknown',error=type(exc).__name__+':'+str(exc)[:160])
    report['schema_version']='qcrl.recorder_rss_cpu_validation_audit.v1'
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--worker',choices=('prepare','producer','consumer'));p.add_argument('--case',choices=('mixed-0',))
    p.add_argument('--execute',action='store_true');p.add_argument('--audit',action='store_true')
    p.add_argument('--inventory-sha256');p.add_argument('--freeze-sha256');p.add_argument('--host-context-sha256');p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.audit:
        require(a.output is not None and a.root.resolve() not in a.output.resolve().parents,'audit output outside sealed tree required')
        report=audit(a.root,expected_inventory_file_sha256=a.inventory_sha256,expected_freeze_sha256=a.freeze_sha256,
                     expected_host_context_file_sha256=a.host_context_sha256)
        exclusive_json(a.output,report);print(json.dumps(dict(complete=report['complete'],verdict=report['verdict'])));return
    require(a.execute,'explicit RSS CPU --execute required')
    if a.worker:return worker_main(a.root,a.worker,a.case,execute=True)
    ops=Production(a.root,base.load(a.root/'execution-freeze.json'),execute=True)
    report=base.execute_cohort(ops,execute=True,protocol=sys.modules[__name__])
    require(report['complete'],'single validation incomplete; preserved, no replay')


if __name__=='__main__':main()
