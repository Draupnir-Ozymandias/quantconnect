"""Independent six-case recorder integrity, unit binding and inclusive-cost audit."""
from datetime import timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re

from execution_truth.acquisition import utc_text
from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import stream_plan
from infra.stream import recorder_persistence_worker as worker
from infra.stream.recorder_absolute_observer import audit_resources
from infra.stream.recorder_persistence_cohort import PLAN, spec, validate_freeze, require, PYTHON
from infra.stream.recorder_persistence_cohort import declaration, verify_cohort_properties
from infra.stream.recorder_application_audit import verify_binding
from infra.stream.recorder_application_evaluator import finite, timing_gate, outcome, stimulus_gate, large_control
from infra.stream.recorder_application_budget import POLICY
from infra.stream.recorder_case_archive import archive_frames as case_archive_frames
from infra.stream.recorder_completion import verify_completion
from infra.stream.recorder_wait_production import verified_properties
from infra.stream.recorder_wait_compatibility_worker import load


def verify_case(case, frozen, *, protocol=None):
    plan = PLAN if protocol is None else protocol.PLAN
    from tests.test_taker_replay import raw_bundle, revise
    verify_artifact_hash(case,'artifact_sha256','smoke case')
    require(case['cohort_only'] is True and case['cohort_plan_sha256']==payload_hash(plan)
        and case['freeze_sha256']==frozen['freeze_sha256'] and case['case'] in plan['case_order']
        and case['fixture_is_synthetic'] is True and case['boot_id']==frozen['runtime']['boot_id'],
        'cohort case/source/boot binding differs')
    from infra.stream.recorder_application_budget import declare
    require(case['plan_sha256']==declare()['plan_sha256'],'cohort original recorder identity differs')
    clock=case['epoch_clock'];require(0<=finite(clock['before'])<=finite(clock['after'])
        and case['epoch']==clock['after']+20,'cohort epoch recipe differs')
    epoch_utc=_time(clock['utc'])+timedelta(seconds=case['epoch']-clock['before'])
    require(case['epoch_utc']==utc_text(epoch_utc),'cohort UTC/monotonic recipe differs')
    raw=raw_bundle()
    revise(raw,'gamma_market',startDate=utc_text(epoch_utc-timedelta(seconds=60)),
        eventStartTime=utc_text(epoch_utc-timedelta(seconds=10)),endDate=utc_text(epoch_utc+timedelta(seconds=290)))
    require(case['raw_bundle']==raw and case['spec']==stream_plan(raw,segmented=True,max_frames=60000,max_seconds=180),
        'cohort synthetic fixture/frame-limit recipe differs')
    require(case['implementation_sources']==worker.implementation_sources(),'smoke implementation input drift')
    return case


def components(case_root, frozen, *, protocol=None):
    declared = declaration() if protocol is None else protocol.declaration()
    root=Path(case_root);case=verify_case(worker.control(root/'case.json'),frozen,protocol=protocol)
    binding=worker.control(root/'absolute-wait-plan.json');require(binding['declaration'] == declared, 'successor declaration differs')
    require(binding['case_sha256']==case['artifact_sha256'] and binding['declaration']==frozen['observer'],
            'cohort observer declaration binding differs')
    producer=large_control(root/'producer.json');consumer=worker.control(root/'consumer.json')
    require(all(x['case_sha256']==case['artifact_sha256'] for x in (producer,consumer)),'cohort result case binding differs')
    frames,footer,gaps=case_archive_frames(root/'archive',case['spec']['max_frames'])
    require(frames==[worker.message(i) for i in range(60000)],'ordered cohort archive population differs')
    completion=load(root/'completion.json',cap=32*1024**2)
    from infra.stream.recorder_completion import _sources
    expected_sources={n:frozen['sources'][n] for n in _sources()}
    verified=verify_completion(completion,root/'archive',expected_domain=consumer['domain'],expected_sources=expected_sources)
    require(consumer['domain']=='localhost.'+case['boot_id'] and completion['spec_sha256']==payload_hash(case['spec'])
        and completion['runtime']['pid']==consumer['identity']['pid'] and verified['frames']==60000,
        'cohort completion actor/spec/population differs')
    require(footer==consumer['summary'],'cohort archive/consumer footer differs')
    for frame,sent in zip(completion['frames'],producer['result']['rows']):
        require(frame['returned']['before']>=sent['begin'],'application return predates original send')
    timing=timing_gate(verified['latencies'],completion['frames'],[row['phase'] for row in worker_schedule(case)],frozen['observer']['budgets'])
    sends=stimulus_gate(producer['result'],case['case'].split('-')[0],case['epoch'])
    if producer['result'].get('internal_retry_count','absent') is not None:
        sends['unknowns'].append('producer_retry_disclosure_missing');sends['verdict']=outcome(sends['failures'],sends['unknowns'])
    closure_failures=[]
    try:
        worker.verify_closure(producer['result'],producer['terminal_receive'],producer['controls'],
            producer['control_errors'],worker.verify_recorder_completion(root,case),case)
    except ContractError:
        # Retain all available timing/resource results alongside a known close fault.
        closure_failures.append('producer_closure_or_recorder_completion')
    resources=audit_resources(consumer['resources'],case['epoch'],sum(p['seconds'] for p in POLICY['workloads'][case['case'].split('-')[0]]),consumer['closed'],
                              frozen['observer']['budgets'],consumer['identity'])
    failures=timing['failures']+sends['failures']+resources['failures']+closure_failures
    if gaps or consumer['error'] or consumer['observer_thread_alive'] is not False or (
        consumer['summary']['status']!='frame_limit' or consumer['summary']['frames']!=60000
        or consumer['summary']['connections']!=1 or consumer['summary']['book_snapshot_assets_by_connection']!={'1':['10001','10002']}):
        failures.append('capture_lifecycle_or_observer_failure')
    if producer['control_errors'] or any(row['text']!='PING' for row in producer['controls']):
        failures.append('unexpected_client_control_or_drain_error')
    unknowns=timing['unknowns']+sends['unknowns']+resources['unknowns']
    samples=consumer['resources']['rows'];first=next((r['cpu_before'] for r in samples if r['cpu_before'] is not None),None)
    last=next((r['sample'] for r in reversed(samples) if r['sample'] is not None),None)
    initial=worker.control(root/'observer-ready.json')['initial']
    cost_samples=[initial]+[s for r in samples for s in (r['cpu_before'],r['sample']) if s is not None]
    disclosures=[]
    for counter in ('nr_throttled','throttled_usec'):
        values=[s.get('cpu',{}).get(counter) for s in cost_samples]
        if any(type(v) is not int or v<0 for v in values) or values!=sorted(values):
            unknowns.append('inclusive_counter:'+counter)
        else:disclosures.append(dict(counter=counter,initial=values[0],last=values[-1],delta=values[-1]-values[0]))
    cost=dict(scope='inclusive_recorder_unit_not_incremental_observer_overhead',
        incremental_observer_overhead=None,wait_receipts=sum(len(r['waits']) for r in samples),
        missed_slots=[dict(slot=r['slot'],rss_error=r['error'],cpu_before_error=r['cpu_before_error'])
                      for r in samples if r['error'] or r['cpu_before_error']],
        startup_usage_usec=None if first is None else first['cpu']['usage_usec']-initial['cpu']['usage_usec'],
        observed_unit_usage_usec=None if first is None or last is None else last['cpu']['usage_usec']-first['cpu']['usage_usec'],
        complete_windows=resources['windows'],throttling_counters=disclosures,
        memory_events=[dict(before=s['before'],after=s['after'],events=s['memory_events']) for s in cost_samples],
        producer_resources=dict(initial=producer['initial_resource'],final=producer['final_resource']),
        reader_bracket_max_seconds=max([s['after']-s['before'] for r in samples
            for s in (r['cpu_before'],r['sample']) if s is not None],default=None),
        maximum_rss_bytes=max([r['sample']['rss_bytes'] for r in samples if r['sample'] is not None],default=None))
    return dict(schema_version='qcrl.recorder_persistence_cohort_components.v1',archive_integrity='pass',
        frames=60000,stimulus=sends,timing=timing,resources=resources,inclusive_cost=cost,
        failures=failures,unknowns=unknowns,verdict=outcome(failures,unknowns),
        compatibility_verified=False,budget_acceptance=False,orders_authorized=False)


def verify_unit(raw, value, source, expected_pid=None, case_name=None,
                worker_module='infra.stream.recorder_persistence_cohort'):
    verify_cohort_properties(raw,value)
    require(raw['Id']==value['unit']+'.service' and raw['SubState']=='exited' and raw['ActiveState']=='active'
        and raw['Result']=='success' and raw['ExecMainStatus']=='0' and raw['ExecMainCode']=='1',
        'smoke native completion differs')
    role=value['worker_role']
    args=['-m','unittest','discover','-s','tests','-q'] if role=='tests' else [
        '-m',worker_module,'--root',str(Path(source).parent/'evidence'/case_name),
        '--worker',role,'--case',case_name,'--execute']
    match=re.search(r'argv\[\]=(.*?) ;',raw['ExecStart'])
    require(match is not None and match.group(1)==' '.join([PYTHON,*args]),'smoke actual command differs')
    start,end,pid=(int(raw[k]) for k in ('ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic','ExecMainPID'))
    require(0<start<end<=start+240_000_000 and pid>0 and (expected_pid is None or pid==expected_pid),
            'smoke native lifetime/PID differs')
    return dict(unit=value['unit']+'.service',pid=pid,start=start/1e6,end=end/1e6)


def worker_schedule(case):
    from infra.stream.recorder_application_worker import schedule
    return schedule(case['case'].split('-')[0])


def audit_case_native(e,case_name,frozen,stage,test_end,previous_end, *, protocol=None):
    root=e/case_name;case=worker.control(root/'case.json')
    require(case['case']==case_name,'case directory/name differs')
    units={};exit_accounting={}
    for role in ('producer','consumer'):
        value=spec(stage,role,case_name)
        raw=dict(line.split('=',1) for line in (e/(value['unit']+'-properties.txt')).read_text().splitlines() if '=' in line)
        units[role]=verify_unit(raw,value,stage+'/source',case_name=case_name,
            **({} if protocol is None else dict(worker_module=protocol.MODULE)))
        exit_accounting[role]=dict(cpu_usage_ns=int(raw['CPUUsageNSec']) if raw.get('CPUUsageNSec','').isdigit() else None,
            cgroup_memory_peak_bytes=int(raw['MemoryPeak']) if raw.get('MemoryPeak','').isdigit() else None,
            scope='whole_unit_including_startup_and_publication',continuous_rss_peak=None,process_high_water_rss=None)
        require((e/(value['unit']+'-journal.txt')).is_file(),'cohort journal missing')
        binding=worker.control(root/(role+'-active.json'));verified_properties(binding['properties'],value)
        verify_binding(binding,units[role],binding['identity'],case['boot_id'],case['epoch'])
        ready=worker.control(root/('server-ready.json' if role=='producer' else 'worker-ready.json'))
        actor=large_control(root/'producer.json') if role=='producer' else worker.control(root/'consumer.json')
        require(ready['identity']==binding['identity']==actor['identity'] and ready['case_sha256']==case['artifact_sha256']
            and units[role]['start']<=ready['at']<=binding['begin']<binding['end']<case['epoch']-.1,
            'cohort readiness/identity chronology differs')
        require(units[role]['start']>=max(test_end,previous_end),'cohort cases overlap')
    producer=large_control(root/'producer.json');consumer=worker.control(root/'consumer.json')
    observer=worker.control(root/'observer-ready.json');closed=worker.control(root/'capture-closed.json')
    require(units['producer']['pid']!=units['consumer']['pid'] and producer['identity']['cgroup']!=consumer['identity']['cgroup'],
        'cohort actors not isolated')
    require(observer['identity']==consumer['identity'] and observer['case_sha256']==case['artifact_sha256']
        and observer['at']<case['epoch']-.1 and units['consumer']['start']<=observer['initial']['before']
        <=observer['initial']['after']<=observer['at'],'cohort observer readiness differs')
    require(closed['case_sha256']==case['artifact_sha256'] and closed['at']==consumer['closed']
        and units['consumer']['start']<=consumer['closed']<=units['consumer']['end'],'cohort closure differs')
    release=worker.control(root/'bindings-ready.json')
    for role in ('producer','consumer'):
        binding=worker.control(root/(role+'-active.json'))
        require(release['case_sha256']==case['artifact_sha256'] and release[role+'_binding']==binding['artifact_sha256']
            and max(binding['end'],observer['at'])<=release['at']<case['epoch']-.1,'cohort release differs')
    for row in producer['result']['rows']:
        require(units['producer']['start']<=row['begin']<=row['end']<=units['producer']['end'],'send outside unit')
    for row in producer['terminal_receive']:
        require(units['producer']['start']<=row['at']<=units['producer']['end'],'close outside producer unit')
    completion=load(root/'completion.json',cap=32*1024**2)
    for row in completion['frames']:
        require(units['consumer']['start']<=row['returned']['before']<=row['append_completed']<=units['consumer']['end'],
            'completion outside unit')
    for row in completion['barriers']:
        require(units['consumer']['start']<=row['begin']<=row['end']<=units['consumer']['end'],'sync outside unit')
    for role,samples in [('producer',[producer['initial_resource'],producer['final_resource']]),('consumer',[observer['initial']])]:
        actor=producer['identity'] if role=='producer' else consumer['identity']
        for sample in samples:
            require(sample['owner']==actor and units[role]['start']<=sample['before']<=sample['after']<=units[role]['end'],
                'startup/final resource actor/lifetime differs')
    for row in consumer['resources']['rows']:
        for sample in (row['sample'],row['cpu_before']):
            if sample is not None:require(units['consumer']['start']<=sample['before']<=sample['after']<=units['consumer']['end'],
                'resource read outside unit')
        for wait in row['waits'].values():
            require(units['consumer']['start']*1e9<=wait['before_ns']<=units['consumer']['end']*1e9
                and (wait['after_ns'] is None or wait['before_ns']<=wait['after_ns']<=units['consumer']['end']*1e9),
                'wait outside unit')
    report=components(root,frozen,**({} if protocol is None else dict(protocol=protocol)));report.update(case=case_name,unit_bindings_verified=True)
    report['inclusive_cost']['whole_unit_exit_accounting']=exit_accounting
    return report,max(u['end'] for u in units.values()),units


def audit(root,*,expected_inventory_file_sha256,expected_freeze_sha256,expected_host_context_file_sha256, protocol=None):
    plan = PLAN if protocol is None else protocol.PLAN
    validate = validate_freeze if protocol is None else protocol.validate_freeze
    options = {} if protocol is None else dict(protocol=protocol)
    root=Path(root);e=root/'evidence';inventory_bytes=(root/'origin-inventory.json').read_bytes()
    require(hashlib.sha256(inventory_bytes).hexdigest()==expected_inventory_file_sha256,'external origin anchor differs')
    inventory=json.loads(inventory_bytes);verify_artifact_hash(inventory,'inventory_sha256','cohort inventory')
    require(inventory['schema_version']=='qcrl.recorder_persistence_cohort_inventory.v1'
        and inventory['native_origin_verified'] is False,'cohort inventory authority differs')
    actual={};total=0
    for p in sorted(e.rglob('*')):
        require(not p.is_symlink(),'retained symlink')
        if p.is_dir():continue
        require(p.is_file() and len(actual)<1024 and p.stat().st_size<=256*1024**2,'cohort inventory cap')
        b=p.read_bytes();total+=len(b);require(total<=4*1024**3,'cohort inventory total cap')
        actual[str(p.relative_to(e))]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    require(actual==inventory['files'],'cohort retained population/bytes differ')
    lineage=load(e/'compatibility-lineage.json');frozen=validate(load(e/'execution-freeze.json'),lineage)
    require(frozen['freeze_sha256']==inventory['freeze_sha256']==expected_freeze_sha256,'external cohort freeze differs')
    require(hashlib.sha256((e/'host-context.json').read_bytes()).hexdigest()==expected_host_context_file_sha256,
        'external host context anchor differs')
    require(load(e/'host-context.json')==frozen['runtime']['host'],'cohort host context differs')
    launch=load(e/'launch-result.json');verify_artifact_hash(launch,'launch_sha256','cohort launch')
    require(launch['freeze_sha256']==expected_freeze_sha256 and launch['cohort_plan_sha256']==payload_hash(plan),
        'launch freeze/plan differs')
    require(all(launch[k] is False for k in ('native_origin_verified','compatibility_verified','budget_cohort_authorized','orders_authorized')),
        'producer authority flags changed')
    if not launch['complete']:
        reports=[];failures=['incomplete_native_launch'];unknowns=['independent_unit_binding_incomplete']
        for name in plan['case_order']:
            case_root=e/name
            for file in ('producer.json','consumer.json'):
                if not (case_root/file).exists():continue
                try:
                    prefix=large_control(case_root/file)
                    if prefix.get('error') or prefix.get('control_errors') or (file=='producer.json' and
                            (prefix['result'].get('error') or prefix['result'].get('complete') is not True)):
                        failures.append(name+':'+file+':retained_runtime_fault')
                except (ContractError,KeyError,TypeError,ValueError,OSError):failures.append(name+':invalid_retained_prefix')
            try:
                report=components(case_root,frozen,**options);report['case']=name;reports.append(report)
                failures.extend(name+':'+v for v in report['failures']);unknowns.extend(name+':'+v for v in report['unknowns'])
            except (ContractError,KeyError,TypeError,ValueError,OSError) as exc:
                unknowns.append(name+':component_unavailable:'+type(exc).__name__)
        return dict(complete=False,verdict='fail',failure=launch['error'],preservation_errors=launch['preservation_errors'],
            reports=reports,failures=failures,unknowns=unknowns,application_budget_pass=False,
            native_origin_verified=False,orders_authorized=False)
    require(launch['error'] is None and not launch['preservation_errors'] and launch['completed']==plan['case_order']
        and launch['public_before']==launch['public_after']==frozen['runtime']['host']['public'],'cohort incomplete/drift')
    stage=launch['stage'];tests=spec(stage,'tests')
    raw=dict(line.split('=',1) for line in (e/(tests['unit']+'-properties.txt')).read_text().splitlines() if '=' in line)
    test_unit=verify_unit(raw,tests,stage+'/source')
    journal=(e/(tests['unit']+'-journal.txt')).read_text()
    require(re.findall(r'Ran (\d+) tests in [\d.]+s',journal)[-1:]==[str(frozen['linux_tests'])]
        and re.findall(r'OK \(skipped=(\d+)\)',journal)[-1:]==['1'],'cohort readiness count/skip differs')
    for name in ('host-processes-before.txt','host-processes-after.txt'):
        require(0<(e/name).stat().st_size<=65536,'host concurrency disclosure missing')
    reports=[];units={'tests':test_unit};previous=test_unit['end'];binding_failures=[];binding_unknowns=[]
    for name in plan['case_order']:
        try:
            report,previous,pair=audit_case_native(e,name,frozen,stage,test_unit['end'],previous,**options)
            reports.append(report);units[name]=pair
        except (ContractError,KeyError,TypeError,ValueError,OSError) as exc:
            binding_failures.append(name+':invalid_native_or_component_evidence:'+type(exc).__name__)
            binding_unknowns.append(name+':case_budget_or_binding_unavailable')
    failures=[r['case']+':'+reason for r in reports for reason in r['failures']]
    unknowns=[r['case']+':'+reason for r in reports for reason in r['unknowns']]
    failures+=binding_failures;unknowns+=binding_unknowns
    require(hashlib.sha256((root/'origin-inventory.json').read_bytes()).hexdigest()==expected_inventory_file_sha256,'origin anchor changed during audit')
    for name,entry in actual.items():
        require(hashlib.sha256((e/name).read_bytes()).hexdigest()==entry['sha256'],'evidence changed during audit')
    require({str(p.relative_to(e)) for p in e.rglob('*') if p.is_file()}==set(actual),'evidence population changed during audit')
    verdict=outcome(failures,unknowns)
    return dict(schema_version='qcrl.recorder_persistence_cohort_independent_audit.v1',complete=True,
        reports=reports,units=units,failures=failures,unknowns=unknowns,verdict=verdict,application_budget_pass=verdict=='pass',
        native_origin_verified=False,requires_observed_origin_attestation=True,incremental_observer_overhead=None,
        rss_continuous_peak_proven=False,orders_authorized=False,public_rollout_authorized=False)


def main():
    import argparse
    from execution_truth.stream_segments import exclusive_json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--inventory-sha256',required=True)
    p.add_argument('--freeze-sha256',required=True);p.add_argument('--host-context-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(a.root.resolve() not in a.output.resolve().parents,'audit output must be outside sealed retained tree')
    report=audit(a.root,expected_inventory_file_sha256=a.inventory_sha256,
        expected_freeze_sha256=a.freeze_sha256,expected_host_context_file_sha256=a.host_context_sha256)
    exclusive_json(a.output,report);print(json.dumps(dict(verdict=report['verdict'],complete=report['complete'])))


if __name__=='__main__':main()
