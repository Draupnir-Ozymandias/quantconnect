"""Offline recorder-smoke integrity, unit binding and inclusive cost review."""
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
from infra.stream.recorder_persistence_smoke import PLAN, spec, validate_freeze, require, PYTHON
from infra.stream.recorder_persistence_smoke import declaration
from infra.stream.recorder_application_audit import verify_binding
from infra.stream.recorder_application_evaluator import finite, timing_gate, outcome
from infra.stream.recorder_completion import verify_completion
from infra.stream.recorder_wait_production import verified_properties
from infra.stream.recorder_wait_compatibility_worker import load


def verify_case(case, frozen):
    from tests.test_taker_replay import raw_bundle, revise
    verify_artifact_hash(case,'artifact_sha256','smoke case')
    require(case['smoke_only'] is True and case['smoke_plan_sha256']==payload_hash(PLAN)
        and case['freeze_sha256']==frozen['freeze_sha256'] and case['case']=='steady-0'
        and case['fixture_is_synthetic'] is True and case['boot_id']==frozen['runtime']['boot_id'],
        'smoke case/source/boot binding differs')
    from infra.stream.recorder_application_budget import declare
    require(case['plan_sha256']==declare()['plan_sha256'],'smoke original recorder identity differs')
    clock=case['epoch_clock'];require(0<=finite(clock['before'])<=finite(clock['after'])
        and case['epoch']==clock['after']+20,'smoke epoch recipe differs')
    epoch_utc=_time(clock['utc'])+timedelta(seconds=case['epoch']-clock['before'])
    require(case['epoch_utc']==utc_text(epoch_utc),'smoke UTC/monotonic recipe differs')
    raw=raw_bundle()
    revise(raw,'gamma_market',startDate=utc_text(epoch_utc-timedelta(seconds=60)),
        eventStartTime=utc_text(epoch_utc-timedelta(seconds=10)),endDate=utc_text(epoch_utc+timedelta(seconds=290)))
    require(case['raw_bundle']==raw and case['spec']==stream_plan(raw,segmented=True,max_frames=68,max_seconds=180),
        'smoke synthetic fixture/frame-limit recipe differs')
    require(case['implementation_sources']==worker.implementation_sources(),'smoke implementation input drift')
    return case


def stimulus(result, epoch):
    failures=[];unknowns=[];rows=result.get('rows',[]);attained=0;previous=epoch
    if result.get('complete') is not True or result.get('error') is not None or len(rows)!=68:
        failures.append('incomplete_stimulus')
    require(len(rows)<=68,'extra smoke producer occurrence')
    for i,row in enumerate(rows):
        try:
            require(row['sequence']==i and row['phase']==0 and row['offset']==i
                and row['deadline']==epoch+i and row['raw_sha256']==hashlib.sha256(worker.message(i).encode()).hexdigest(),
                'smoke schedule/occurrence differs')
            begin,end=finite(row['begin']),finite(row['end'])
            require(previous<=begin<=end and begin>=epoch+i,'smoke send chronology differs')
            previous=end
            if begin-epoch-i>.05:failures.append('send_lateness:'+str(i))
            if end-begin>.05:failures.append('send_duration:'+str(i))
            attained+=int(epoch<=begin<epoch+68)
        except (ContractError,KeyError,TypeError,ValueError):unknowns.append('send_witness:'+str(i))
    if attained/68<.99:failures.append('phase_attainment')
    if result.get('internal_retry_count','absent') is not None:unknowns.append('producer_retry_disclosure_missing')
    return dict(verdict=outcome(failures,unknowns),failures=failures,unknowns=unknowns,phase_attained=attained)


def archive_frames(root):
    """Bound a raw rescan before the existing full integrity/completion verifier."""
    frames=[];footer=None;gaps=0;rows=0;total=0
    for descriptor in sorted(Path(root).glob('segment-*.json')):
        info=load(descriptor);name=info['file']
        require(re.fullmatch('segment-[0-9]{6}\\.gz',name),'canonical archive segment required')
        with gzip.open(Path(root)/name,'rb') as handle:
            while True:
                line=handle.readline(4*1024**2+1)
                if not line:break
                rows+=1;total+=len(line)
                require(len(line)<=4*1024**2 and rows<=1024 and total<=1024**3,'smoke raw archive scan cap exceeded')
                row=json.loads(line)
                if row['kind']=='frame':
                    require(len(frames)<68,'extra smoke archive frame');frames.append(row['payload']['raw_text'])
                if row['kind']=='session_end':footer=row['payload']
                if row['kind']=='connection_gap':gaps+=1
    return frames,footer,gaps


def components(case_root, frozen):
    root=Path(case_root);case=verify_case(worker.control(root/'case.json'),frozen)
    binding=worker.control(root/'absolute-wait-plan.json');require(binding['declaration'] == declaration(), 'successor declaration differs')
    require(binding['case_sha256']==case['artifact_sha256'] and binding['declaration']==frozen['observer'],
            'smoke observer declaration binding differs')
    producer=worker.control(root/'producer.json');consumer=worker.control(root/'consumer.json')
    require(all(x['case_sha256']==case['artifact_sha256'] for x in (producer,consumer)),'smoke result case binding differs')
    frames,footer,gaps=archive_frames(root/'archive')
    require(frames==[worker.message(i) for i in range(68)],'ordered smoke archive population differs')
    completion=load(root/'completion.json',cap=32*1024**2)
    from infra.stream.recorder_completion import _sources
    expected_sources={n:frozen['sources'][n] for n in _sources()}
    verified=verify_completion(completion,root/'archive',expected_domain=consumer['domain'],expected_sources=expected_sources)
    require(consumer['domain']=='localhost.'+case['boot_id'] and completion['spec_sha256']==payload_hash(case['spec'])
        and completion['runtime']['pid']==consumer['identity']['pid'] and verified['frames']==68,
        'smoke completion actor/spec/population differs')
    require(footer==consumer['summary'],'smoke archive/consumer footer differs')
    for frame,sent in zip(completion['frames'],producer['result']['rows']):
        require(frame['returned']['before']>=sent['begin'],'application return predates original send')
    timing=timing_gate(verified['latencies'],completion['frames'],[0]*68,frozen['observer']['budgets'])
    sends=stimulus(producer['result'],case['epoch'])
    closure_failures=[]
    try:
        worker.verify_closure(producer['result'],producer['terminal_receive'],producer['controls'],
            producer['control_errors'],worker.verify_recorder_completion(root,case),case)
    except ContractError:
        # Retain all available timing/resource results alongside a known close fault.
        closure_failures.append('producer_closure_or_recorder_completion')
    resources=audit_resources(consumer['resources'],case['epoch'],67,consumer['closed'],
                              frozen['observer']['budgets'],consumer['identity'])
    failures=timing['failures']+sends['failures']+resources['failures']+closure_failures
    if gaps or consumer['error'] or consumer['observer_thread_alive'] is not False or (
        consumer['summary']['status']!='frame_limit' or consumer['summary']['frames']!=68
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
    return dict(schema_version='qcrl.recorder_persistence_smoke_components.v1',archive_integrity='pass',
        frames=68,stimulus=sends,timing=timing,resources=resources,inclusive_cost=cost,
        failures=failures,unknowns=unknowns,verdict=outcome(failures,unknowns),
        compatibility_verified=False,budget_acceptance=False,orders_authorized=False)


def verify_unit(raw, value, source, expected_pid=None):
    verified_properties(raw,value)
    require(raw['Id']==value['unit']+'.service' and raw['SubState']=='exited' and raw['ActiveState']=='active'
        and raw['Result']=='success' and raw['ExecMainStatus']=='0' and raw['ExecMainCode']=='1',
        'smoke native completion differs')
    role=value['worker_role']
    args=['-m','unittest','discover','-s','tests','-q'] if role=='tests' else [
        '-m','infra.stream.recorder_persistence_smoke','--root',str(Path(source).parent/'evidence/case'),
        '--worker',role,'--execute']
    match=re.search(r'argv\[\]=(.*?) ;',raw['ExecStart'])
    require(match is not None and match.group(1)==' '.join([PYTHON,*args]),'smoke actual command differs')
    start,end,pid=(int(raw[k]) for k in ('ExecMainStartTimestampMonotonic','ExecMainExitTimestampMonotonic','ExecMainPID'))
    require(0<start<end<=start+240_000_000 and pid>0 and (expected_pid is None or pid==expected_pid),
            'smoke native lifetime/PID differs')
    return dict(unit=value['unit']+'.service',pid=pid,start=start/1e6,end=end/1e6)


def audit(root, *, expected_inventory_file_sha256, expected_freeze_sha256):
    """Caller supplies inventory byte anchor observed independently at the origin."""
    root=Path(root);e=root/'evidence';inventory_bytes=(root/'origin-inventory.json').read_bytes()
    require(hashlib.sha256(inventory_bytes).hexdigest()==expected_inventory_file_sha256,'external origin byte anchor differs')
    inventory=json.loads(inventory_bytes);verify_artifact_hash(inventory,'inventory_sha256','smoke inventory')
    require(inventory['schema_version']=='qcrl.recorder_persistence_smoke_inventory.v1'
        and inventory['native_origin_verified'] is False,'smoke inventory schema/authority differs')
    actual={}
    for p in sorted(e.rglob('*')):
        require(not p.is_symlink(),'retained smoke symlink')
        if p.is_dir():continue
        require(p.is_file() and len(actual)<128 and p.stat().st_size<=32*1024**2,'smoke retained inventory cap')
        b=p.read_bytes();actual[str(p.relative_to(e))]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    require(inventory['files']==actual,'smoke retained population/bytes differ')
    frozen=validate_freeze(load(e/'execution-freeze.json'));require(frozen['freeze_sha256']==expected_freeze_sha256
        and inventory['freeze_sha256']==expected_freeze_sha256,'external smoke freeze anchor differs')
    launch=load(e/'launch-result.json');verify_artifact_hash(launch,'launch_sha256','smoke launch')
    require(launch['freeze_sha256']==expected_freeze_sha256 and launch['smoke_plan_sha256']==payload_hash(PLAN),
        'smoke launch binding differs')
    require(all(launch[k] is False for k in ('native_origin_verified','compatibility_verified',
        'budget_cohort_authorized','orders_authorized')),'smoke producer authority changed')
    if not launch['complete']:
        return dict(complete=False,compatibility_verified=False,unknowns=['incomplete_native_launch_all_missing_evidence_unavailable'],
                    failure=launch['error'],preservation_errors=launch['preservation_errors'],orders_authorized=False)
    require(launch['error'] is None and not launch['preservation_errors'] and launch['public_before']==launch['public_after'],
        'completed smoke retained fault/drift')
    public=launch['public_before']
    require(public==frozen['runtime']['host']['public'],'approved public source/environment binding differs')
    require(public['collectors'] and all(v==('active' if k.endswith('.timer') else 'inactive')
            for k,v in public['collectors'].items()),'smoke public prerequisites differ')
    require(load(e/'host-context.json')==frozen['runtime']['host'],'smoke host context binding differs')
    stage=launch['stage'];case=worker.control(e/'case/case.json');units={}
    for role in ('tests','producer','consumer'):
        value=spec(stage,role)
        raw=dict(line.split('=',1) for line in (e/(value['unit']+'-properties.txt')).read_text().splitlines() if '=' in line)
        units[role]=verify_unit(raw,value,stage+'/source')
        require((e/(value['unit']+'-journal.txt')).is_file(),'smoke journal missing')
        if role!='tests':
            binding=worker.control(e/'case'/(role+'-active.json'))
            verified_properties(binding['properties'],value)
            verify_binding(binding,units[role],binding['identity'],case['boot_id'],case['epoch'])
            ready=worker.control(e/'case'/('server-ready.json' if role=='producer' else 'worker-ready.json'))
            result=worker.control(e/'case'/('producer.json' if role=='producer' else 'consumer.json'))
            require(ready['identity']==binding['identity']==result['identity']
                and ready['case_sha256']==case['artifact_sha256'] and ready['at']<case['epoch']-.1,
                'smoke ready/result/native identity differs')
            require(units[role]['start']<=ready['at']<=binding['begin']<binding['end']<case['epoch']-.1,
                'smoke readiness/binding chronology differs')
    require(units['tests']['end']<=min(units['producer']['start'],units['consumer']['start'])
        and units['producer']['pid']!=units['consumer']['pid']
        and worker.control(e/'case/producer.json')['identity']['cgroup']!=worker.control(e/'case/consumer.json')['identity']['cgroup'],'smoke process order/isolation differs')
    observer=worker.control(e/'case/observer-ready.json');consumer=worker.control(e/'case/consumer.json')
    require(observer['identity']==consumer['identity'] and observer['case_sha256']==case['artifact_sha256']
        and observer['at']<case['epoch']-.1,'smoke observer readiness differs')
    closed=worker.control(e/'case/capture-closed.json')
    require(closed['case_sha256']==case['artifact_sha256'] and closed['at']==consumer['closed']
        and units['consumer']['start']<=observer['initial']['before']<=observer['initial']['after']<=observer['at']
        and units['consumer']['start']<=consumer['closed']<=units['consumer']['end'],
        'smoke capture closure/startup chronology differs')
    release=worker.control(e/'case/bindings-ready.json')
    require(release['case_sha256']==case['artifact_sha256'] and release['at']<case['epoch']-.1,
        'smoke release case/epoch differs')
    for role in ('producer','consumer'):
        binding=worker.control(e/'case'/(role+'-active.json'))
        require(binding['end']<=release['at'] and observer['at']<=release['at']
                and release[role+'_binding']==binding['artifact_sha256'],'smoke release binding hash differs')
    tests=(e/(spec(stage,'tests')['unit']+'-journal.txt')).read_text()
    require(re.findall(r'Ran (\d+) tests in [\d.]+s',tests)[-1:]==[str(frozen['linux_tests'])]
        and re.findall(r'OK \(skipped=(\d+)\)',tests)[-1:]==['1'],'smoke regression gate differs')
    report=components(e/'case',frozen)
    # Unit lifetime checks cover every producer/witness/resource timestamp.
    producer=worker.control(e/'case/producer.json')
    for row in producer['result']['rows']:
        require(units['producer']['start']<=row['begin']<=row['end']<=units['producer']['end'],'send outside producer unit')
    completion=load(e/'case/completion.json',cap=32*1024**2)
    for event in producer['terminal_receive']:
        require(units['producer']['start'] <= event['at'] <= units['producer']['end'],
                'terminal receive outside producer unit')
    for barrier in completion['barriers']:
        require(units['consumer']['start']<=barrier['begin']<=barrier['end']<=units['consumer']['end'],
            'durability barrier outside recorder unit')
    for role,reads in [('producer',[producer['initial_resource'],producer['final_resource']]),
                       ('consumer',[observer['initial']])]:
        actor=worker.control(e/'case'/(role+'.json'))['identity']
        for sample in reads:
            require(sample.get('owner')==actor and units[role]['start']<=sample['before']<=sample['after']<=units[role]['end'],
                    'startup/final resource identity/lifetime differs')
    for row in completion['frames']:
        require(units['consumer']['start']<=row['returned']['before']<=row['append_completed']<=units['consumer']['end'],
                'completion outside recorder unit')
    for row in consumer['resources']['rows']:
        for s in (row['cpu_before'],row['sample']):
            if s is not None:require(units['consumer']['start']<=s['before']<=s['after']<=units['consumer']['end'],
                                    'resource read outside recorder unit')
        for wait in row['waits'].values():
            require(units['consumer']['start']*1e9<=wait['before_ns']<=units['consumer']['end']*1e9
                and (wait['after_ns'] is None or wait['before_ns']<=wait['after_ns']<=units['consumer']['end']*1e9),
                    'wait outside recorder unit')
    report.update(unit_bindings_verified=True,complete=True,native_origin_verified=False,
                  compatibility_verified=report['verdict']=='pass',requires_observed_origin_attestation=True)
    return report
