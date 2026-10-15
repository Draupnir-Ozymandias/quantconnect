"""One prospective six-case persistence cohort; explicit execution, no replay."""
import argparse
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import pwd
import re
import shutil
import sys
import time

from execution_truth.acquisition import utc_now, utc_text
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import stream_plan
from infra.stream import recorder_persistence_worker as worker
from infra.stream.recorder_absolute_budget import declaration as observer_declaration
from infra.stream.recorder_absolute_observer import observe_absolute
from infra.stream.recorder_application_budget import declare as parent_declaration
from infra.stream.recorder_application_resources import LinuxReader
from infra.stream.recorder_wait_execution import validate_runtime
from infra.stream.recorder_wait_execution import selected
from infra.stream.recorder_wait_lifecycle import BASE_PROPERTIES
from infra.stream.recorder_wait_production import Production, CommandError, command, inspect_source, observe_runtime, PYTHON, verified_properties, seconds
from infra.stream.recorder_wait_compatibility_worker import load, publish

ROOT = Path(__file__).resolve().parents[2]
STAGE = r'/var/lib/qcrl-stream/recorder-persistence-[A-Za-z0-9]+'
PLAN = dict(schema_version='qcrl.recorder_persistence_cohort_plan.v1',
    parent='c9207f596ac734e558ca44d7397df0e6abb580ddd75fcc84f6dda44f70873ade',
    case_order=['steady-0','mixed-0','mixed-1','steady-1','steady-2','mixed-2'],
    occurrences_per_case=60000,total_occurrences=360000,epoch_lead_seconds=20,
    readiness_margin_seconds=.1,capture_seconds=180,regression_units=1,
    producer_units=6,consumer_units=6,measurement_cohorts=1,
    cpu_pre_read_lead_ns=50_000_000,persistence_reserve_seconds=1,reserve_is_guarantee=False,
    closure='all_planned_sends_and_verified_recorder_completion_and_normal_close',
    producer_wait='existing_relative_sleep_may_retry_internally_count_unknown',
    compatibility='frozen_passed_68_run_unchanged_core_and_exact_reviewed_verifier_delta_not_identical_source',
    incremental_observer_overhead_gate=False,continuous_rss_peak_gate=False,
    credit_balance_minimum=None,stopping='one_cohort_no_retry_replay_replacement_tuning',
    native_execution_authorized=False,acceptance_demonstrated=False,orders_authorized=False)
COMPATIBILITY_FREEZE='3338edbfc19048fa39787d86cc70abebd458318b4a79abd816c531f2fad3ca4f'
COMPATIBILITY_AUDIT='798a1ed0d68bb796d9805794a967ed4337f3b4183f9d7e2342b7dd7b260a2f88'
COMPATIBILITY_ORIGIN='cad3586f7fc282f53589f20a7043cc6e089d6306716669e65f2e70ceb89e32d1'
CONTROLS=('execution-freeze.json','runtime-review.json','select-review-source.c','host-context.json','compatibility-lineage.json')
READINESS_ENVELOPE = dict(schema_version='qcrl.recorder_readiness_envelope.v1',
    memory_max_bytes=1073741824, memory_max='1G', cpu_quota='75%', tasks_max='32',
    runtime_max_seconds=240, process_isolation='original_single_unittest_discovery_process',
    measurement_memory_max_bytes=536870912, coverage_reduction=False,
    prior_failed_freeze='90dfdd968ccbb584ba2da2a2e9ff7db90cb7d4673c87ecea11ce9e0ef232b686',
    earlier_failure_superseded=False, native_execution_authorized=False)


def declaration():
    from execution_truth.stream_segments import file_hash
    from infra.stream.recorder_persistence_lane import PERSISTENCE_POLICY
    value=observer_declaration();value.pop('declaration_sha256')
    value.update(schema_version='qcrl.recorder_persistence_cohort_declaration.v1',
        observer_plan=value['plan'],plan=deepcopy(PLAN),plan_sha256=payload_hash(PLAN),
        persistence_policy=deepcopy(PERSISTENCE_POLICY),readiness_envelope=deepcopy(READINESS_ENVELOPE))
    for name in ('infra/stream/recorder_persistence_lane.py','infra/stream/recorder_persistence_worker.py',
        'infra/stream/recorder_case_archive.py','infra/stream/recorder_persistence_cohort.py',
        'infra/stream/recorder_persistence_cohort_audit.py','tests/test_recorder_persistence_cohort.py',
        'docs/RECORDER_PERSISTENCE_COHORT.md','docs/RECORDER_READINESS_MEMORY_V2.md',
        'tests/test_recorder_readiness_memory.py'):
        value['sources'][name]=file_hash(ROOT/name)
    value['declaration_sha256']=payload_hash(value)
    return value


def require(value, message):
    if not value:
        raise ContractError(message)


def boot():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def dependencies():
    """Installed package bytes only; no package import, installation or credentials."""
    dist = importlib.metadata.distribution('websockets')
    require(dist.version == '15.0.1', 'fixed websockets version required')
    root = Path(dist.locate_file('')).resolve(strict=True)
    files = {}
    for entry in sorted(dist.files or [], key=str):
        name = str(entry)
        if '__pycache__' in name or name.endswith('.pyc'):
            continue
        if name == '../../../bin/websockets':
            path = root.parent.parent.parent/'bin/websockets'
            name = '@venv-bin/websockets'
        else:
            require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and name.startswith(('websockets/', 'websockets-15.0.1.dist-info/')),
                'package inventory path outside declared dependency')
            path = root/name
        require(path.resolve(strict=True) == path and path.is_file()
                and path.stat().st_size <= 4*1024**2 and len(files) < 256,
                'bounded regular package dependency required')
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    require(files and 'websockets/sync/client.py' in files
            and 'websockets/sync/server.py' in files, 'complete installed distribution inventory required')
    return dict(version=dist.version, root=str(root), files=files)


def runtime(root):
    root = Path(root)
    return dict(wait=observe_runtime(load(root/'runtime-review.json'),
                review_source=root/'select-review-source.c', execute=True), websockets=dependencies(),
                boot_id=boot(),host=load(root/'host-context.json'))


def validate_lineage(value, sources, installed):
    old=value['freeze'];verify_artifact_hash(old,'freeze_sha256','historical smoke freeze')
    require(old['freeze_sha256']==COMPATIBILITY_FREEZE,
        'exact historical compatibility freeze required')
    attestation=value['origin_attestation'];verify_artifact_hash(attestation,'attestation_sha256','observed smoke origin')
    require(attestation['attestation_sha256']==COMPATIBILITY_ORIGIN
        and attestation['freeze_sha256']==old['freeze_sha256'],'observed historical origin differs')
    text=value['audit_text']
    require(hashlib.sha256(text.encode()).hexdigest()==COMPATIBILITY_AUDIT,
        'independent historical compatibility audit bytes differ')
    report=json.loads(text)
    require(report['verdict']=='pass' and report['complete'] is True and report['compatibility_verified'] is True
        and report['native_origin_verified'] is False and not report['failures'] and not report['unknowns'],
        'historical compatibility did not pass')
    for name,h in old['sources'].items():
        if name.endswith('.py') and name!='infra/stream/recorder_persistence_worker.py':
            require(sources.get(name)==h,'smoke-tested Python source changed: '+name)
    name='infra/stream/recorder_persistence_worker.py';before=value['worker_original']
    require(hashlib.sha256(before.encode()).hexdigest()==old['sources'][name],'original worker bytes differ')
    after=before.replace('from infra.stream.recorder_absolute_smoke_audit import archive_frames',
        'from infra.stream.recorder_case_archive import archive_frames').replace(
        "archive_frames(root/'archive')","archive_frames(root/'archive', case['spec']['max_frames'])")
    require(after!=before and hashlib.sha256(after.encode()).hexdigest()==sources[name],
        'worker delta exceeds reviewed case-count verifier substitution')
    for key in ('instance_id','region','instance_type','credit_mode'):
        require(installed['host'][key]==old['runtime']['host'][key],'host configuration changed')
    for key in ('wait','websockets','boot_id'):
        require(installed[key]==old['runtime'][key],'tested installed runtime/boot differs')
    return value


def freeze(commit,sources,installed,linux_tests,lineage):
    from infra.stream.recorder_application_audit import verify_host
    validate_runtime(installed['wait']);verify_host(installed['host'])
    require(installed['host']['boot_id']==installed['boot_id'] and installed['host']['observed_utc']
        and installed['host']['public']['collectors'],'fresh anchored host context required')
    require(re.fullmatch('[0-9a-f]{40}',commit) and type(linux_tests) is int and linux_tests>=1156,
        'exact candidate and readiness population required')
    validate_lineage(lineage,sources,installed)
    require(set(declaration()['sources'])<=set(sources) and all(selected(n) and re.fullmatch('[0-9a-f]{64}',h)
        for n,h in sources.items()),'complete cohort source inventory required')
    value=dict(schema_version='qcrl.recorder_persistence_cohort_freeze.v2',source_commit=commit,
        sources=deepcopy(sources),runtime=deepcopy(installed),observer=declaration(),
        cohort_plan_sha256=payload_hash(PLAN),linux_tests=linux_tests,linux_skips=1,
        lineage_sha256=payload_hash(lineage),native_execution_authorized=False,
        acceptance_demonstrated=False,orders_authorized=False)
    value['freeze_sha256']=payload_hash(value);return value


def validate_freeze(value,lineage=None):
    verify_artifact_hash(value,'freeze_sha256','cohort freeze')
    require(value['schema_version']=='qcrl.recorder_persistence_cohort_freeze.v2'
        and value['observer']==declaration() and value['cohort_plan_sha256']==payload_hash(PLAN)
        and all(value[k] is False for k in ('native_execution_authorized','acceptance_demonstrated','orders_authorized')),
        'cohort declaration/authority differs')
    for name,h in value['observer']['sources'].items():
        require(value['sources'].get(name)==h,'cohort declaration source absent')
    if lineage is not None:
        require(value==freeze(value['source_commit'],value['sources'],value['runtime'],value['linux_tests'],lineage),
            'cohort full freeze/lineage differs')
    return value


def prepare(root, freeze_hash, case_name, *, execute=False):
    require(execute is True, 'explicit cohort preparation required')
    require(re.fullmatch('[0-9a-f]{64}',freeze_hash),'exact smoke freeze binding required')
    from tests.test_taker_replay import raw_bundle, revise
    root = Path(root); root.mkdir(exist_ok=False)
    before = time.monotonic(); now = utc_now(); after = time.monotonic()
    epoch = after+20; epoch_utc = now+timedelta(seconds=epoch-before)
    raw = raw_bundle()
    revise(raw, 'gamma_market', startDate=utc_text(epoch_utc-timedelta(seconds=60)),
           eventStartTime=utc_text(epoch_utc-timedelta(seconds=10)),
           endDate=utc_text(epoch_utc+timedelta(seconds=290)))
    require(case_name in PLAN['case_order'],'fixed cohort case required')
    spec = stream_plan(raw, segmented=True, max_frames=60000, max_seconds=180)
    case = worker.publish(root/'case.json', dict(case=case_name,
        plan_sha256=parent_declaration()['plan_sha256'],freeze_sha256=freeze_hash,
        cohort_plan_sha256=payload_hash(PLAN), cohort_only=True,
        epoch=epoch, epoch_utc=utc_text(epoch_utc), epoch_clock=dict(before=before, after=after,utc=utc_text(now)),
        raw_bundle=raw, spec=spec, fixture_is_synthetic=True,
        implementation_sources=worker.implementation_sources(),
        boot_id=boot()))
    worker.publish(root/'absolute-wait-plan.json', dict(case_sha256=case['artifact_sha256'], declaration=declaration()))
    return case


def transmit(conn,kind,epoch,*,clock=time.monotonic,pause=time.sleep):
    from infra.stream.recorder_application_worker import schedule
    from infra.stream.recorder_application_budget import corpus
    rows=[];error=None;population=corpus()
    try:
        for row in schedule(kind):
            deadline=epoch+row['offset'];pause(max(0,deadline-clock()));begin=clock();i=row['sequence']
            raw=population['initial'][i] if i<2 else population['cycle'][(i-2)%8]
            conn.send(raw)
            rows.append(dict(row,deadline=deadline,begin=begin,end=clock(),raw_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    except (Exception,KeyboardInterrupt) as exc:error=(type(exc).__name__+':'+str(exc))[:160]
    return dict(rows=rows,error=error,complete=error is None and len(rows)==60000,internal_retry_count=None)


def spec(stage, role, case_name=None):
    require(re.fullmatch(STAGE, stage) and role in ('tests','producer','consumer'), 'fixed cohort unit required')
    require((role=='tests' and case_name is None) or (role!='tests' and case_name in PLAN['case_order']),'fixed unit case required')
    tag=stage.rsplit('recorder-persistence-',1)[1]+('' if role=='tests' else '-'+case_name)
    evidence=stage+'/evidence'+('' if role=='tests' else '/'+case_name)
    props=dict(BASE_PROPERTIES,ReadWritePaths=evidence,ReadOnlyPaths=stage+'/source',
        InaccessiblePaths='-/etc/qcrl-stream.env -/etc/qcrl-collector.env',
        RestrictAddressFamilies='AF_UNIX AF_INET',IPAddressAllow='127.0.0.1/32')
    if role=='tests':props['MemoryMax']=READINESS_ENVELOPE['memory_max']
    return dict(unit='qcrl-persistence-'+tag+'-'+role,role='tests',worker_role=role,
                properties=props,working_directory=stage+'/source')


def verify_cohort_properties(raw, value):
    """Separate prospective readiness allowance; never relax measurement limits."""
    if value['worker_role']!='tests':return verified_properties(raw,value)
    expected=value['properties']
    require(expected['MemoryMax']=='1G' and raw.get('MemoryMax')=='1073741824',
        'readiness memory envelope differs')
    require(seconds(raw.get('CPUQuotaPerSecUSec',''))==Decimal('.75')
        and seconds(raw.get('RuntimeMaxUSec',''))==240,'readiness CPU/runtime differs')
    for key in ('User','Group','TasksMax','RemainAfterExit','NoNewPrivileges','PrivateTmp','ProtectSystem','ProtectHome'):
        require(raw.get(key)==expected[key],'readiness effective property differs: '+key)
    for key in ('ReadWritePaths','ReadOnlyPaths','InaccessiblePaths','RestrictAddressFamilies'):
        require({v.lstrip('-') for v in raw.get(key,'').split()}==
            {v.lstrip('-') for v in expected[key].split()},'readiness isolation differs: '+key)
    require(set(raw.get('IPAddressDeny','').split()) in ({'any'},{'0.0.0.0/0','::/0'})
        and set(raw.get('IPAddressAllow','').split())=={'127.0.0.1/32'},'readiness network differs')
    return deepcopy(expected)


def worker_main(root, role, case_name, *, execute=False):
    root=Path(root)
    require(execute is True and platform.system()=='Linux'
        and os.geteuid()==pwd.getpwnam('qcrl').pw_uid and case_name in PLAN['case_order'] and root==ROOT.parent/'evidence'/case_name
        and re.fullmatch(STAGE,str(ROOT.parent)) and os.path.abspath(sys.executable)==PYTHON,
        'canonical explicit qcrl Linux recorder cohort worker required')
    frozen=validate_freeze(load(ROOT.parent/'execution-freeze.json'),load(ROOT.parent/'compatibility-lineage.json'))
    sources,commit=inspect_source(ROOT)
    require(sources==frozen['sources'] and commit==frozen['source_commit']
            and runtime(ROOT.parent)==frozen['runtime'], 'cohort worker source/runtime drift')
    if role=='prepare': return prepare(root,frozen['freeze_sha256'],case_name,execute=True)
    case=worker.control(root/'case.json')
    require(case['cohort_only'] is True and case['cohort_plan_sha256']==payload_hash(PLAN) and case['case']==case_name
        and case['freeze_sha256']==frozen['freeze_sha256']
        and case['spec']['max_frames']==60000 and case['spec']['max_seconds']==180,
        'only the fixed cohort case may execute')
    binding=worker.control(root/'absolute-wait-plan.json')
    require(binding['case_sha256']==case['artifact_sha256'] and binding['declaration']==declaration(),
        'successor case/declaration differs')
    from infra.stream.recorder_application_budget import declare
    if role=='producer': return worker.produce(root,declare(),execute=True,transmitter=transmit)
    require(role=='consumer','unknown cohort worker role')
    return worker.consume(root,declare(),execute=True,resource_observer=lambda reader,epoch,stop: observe_absolute(reader,epoch,stop,execute=True))


class CohortProduction(Production):
    def __init__(self, root, frozen, *, execute=False):
        self.root=Path(root);self.frozen=validate_freeze(frozen,load(Path(root)/'compatibility-lineage.json'));self.evidence=self.root/'evidence';self.specs={};self.case_name=None
        require(execute is True and platform.system()=='Linux' and os.geteuid()==0
            and re.fullmatch(STAGE,str(self.root)) and self.root.resolve(strict=True)==self.root
            and ROOT==self.root/'source' and os.path.abspath(sys.executable)==PYTHON,
            'explicit canonical Linux root cohort stage required')

    def recheck(self, stage, frozen):
        sources,commit=inspect_source(self.root/'source')
        return dict(clean_source=True,source_freeze_matches=sources==frozen['sources'] and commit==frozen['source_commit'],
                    runtime_freeze_matches=runtime(self.root)==frozen['runtime'])

    def preflight(self):
        require(all(self.recheck(str(self.root),self.frozen).values()),'source/runtime preflight failed')
        for name in ('evidence','launch-claim.json','origin-inventory.json'):
            require(not (self.root/name).exists() and not (self.root/name).is_symlink(),'fresh cohort stage required')
        require(shutil.disk_usage(self.root).free>4*1024**3,'four GiB reserve required')
        tag=spec(str(self.root),'tests')['unit'].removesuffix('-tests')
        require(not command(['systemctl','list-units','--all','--full','--no-legend',tag+'-*'],execute=True).strip(),
                'private cohort unit prefix exists')
        require((self.root/'source').stat().st_uid==pwd.getpwnam('qcrl').pw_uid,'qcrl source ownership required')
        for name in CONTROLS:
            require((self.root/name).is_file() and not (self.root/name).is_symlink(),'regular cohort controls required')
            command(['sudo','-u','qcrl','test','-r',str(self.root/name)],execute=True)
        before=self.public_state()
        require(before==self.frozen['runtime']['host']['public'],'approved public source/environment drift')
        require(before['collectors']=={n:'active' if n.endswith('.timer') else 'inactive' for n in before['collectors']},
                'public prerequisites differ')
        return before

    def start(self, value):
        role=value['worker_role'];require(value==spec(str(self.root),role,self.case_name),'fixed cohort unit only')
        self.specs[value['unit']]=value
        args=['-m','unittest','discover','-s','tests','-q'] if role=='tests' else [
            '-m','infra.stream.recorder_persistence_cohort','--root',str(self.evidence/self.case_name),
            '--worker',role,'--case',self.case_name,'--execute']
        command(['systemd-run','--unit='+value['unit'],'--working-directory='+str(self.root/'source'),
            *['--property='+k+'='+v for k,v in value['properties'].items()],PYTHON,*args],execute=True)

    def capture(self, unit, *, max_journal_bytes):
        if self.specs[unit]['worker_role']!='tests':
            return super().capture(unit,max_journal_bytes=max_journal_bytes)
        # Keep the historical production adapter frozen. Retain the actual 1-GiB
        # properties before verifying the prospectively distinct readiness spec.
        errors=[];raw=None
        try:
            text,raw=self.properties(unit)
            with (self.evidence/(unit+'-properties.txt')).open('x') as handle:handle.write(text)
        except Exception as exc:
            errors.append(type(exc).__name__)
            if isinstance(exc,CommandError):
                with (self.evidence/(unit+'-properties.partial')).open('xb') as handle:handle.write(exc.output)
        try:
            try:
                journal=command(['journalctl','-u',unit+'.service','--no-pager','-o','short-monotonic'],
                    cap=max_journal_bytes,execute=True).encode()
            except CommandError as exc:
                journal=exc.output;errors.append(str(exc)[:160])
            with (self.evidence/(unit+'-journal.txt')).open('xb') as handle:handle.write(journal)
        except Exception as exc:errors.append(type(exc).__name__)
        if errors:
            publish(self.evidence/(unit+'-capture-error.json'),dict(errors=errors,truncated_or_incomplete=True))
            raise ContractError('readiness capture incomplete; retained partial evidence')
        return dict(unit=unit,result=raw.get('Result'),exec_status=int(raw.get('ExecMainStatus','-1')),
            substate=raw.get('SubState'),observed_properties=verify_cohort_properties(raw,self.specs[unit]))

    def claim(self):
        publish(self.root/'launch-claim.json',dict(freeze_sha256=self.frozen['freeze_sha256'],replay_authorized=False))
        command(['install','-d','-o','qcrl','-g','qcrl','-m','750',str(self.evidence)],execute=True)
        for name in CONTROLS:
            with (self.evidence/name).open('xb') as out:out.write((self.root/name).read_bytes())
        text=command(['ps','-eo','pid,ppid,comm,pcpu'],cap=65536,execute=True)
        (self.evidence/'host-processes-before.txt').open('x').write(text)

    def prepare(self,case_name):
        self.case_name=case_name
        command(['sudo','-u','qcrl',PYTHON,'-B','-m','infra.stream.recorder_persistence_cohort',
            '--root',str(self.evidence/case_name),'--worker','prepare','--case',case_name,'--execute'],timeout=30,execute=True)

    def ready(self, filename, deadline):
        while time.monotonic()<deadline:
            if (self.evidence/self.case_name/filename).exists():return worker.control(self.evidence/self.case_name/filename)
            time.sleep(.01)
        raise ContractError('cohort readiness missed; no late adoption')

    def bind(self, role, ready, deadline):
        begin=time.monotonic()
        value=spec(str(self.root),role,self.case_name);_,raw=self.properties(value['unit']);verified_properties(raw,value)
        require(time.monotonic()<deadline,'binding missed original epoch')
        identity=ready['identity'];reader=LinuxReader(execute=True,pid=identity['pid']);sample=reader.read(rss=True)
        end=time.monotonic()
        require(reader.expected==identity and identity['boot_id']==self.frozen['runtime']['boot_id']
            and raw.get('Id')==value['unit']+'.service' and raw.get('MainPID')==str(identity['pid'])
            and raw.get('ExecMainPID')==str(identity['pid']) and raw.get('ControlGroup')==identity['cgroup']
            and raw.get('ActiveState')=='active' and raw.get('SubState')=='running' and end<deadline,
            'independent live cohort binding differs')
        return worker.publish(self.evidence/self.case_name/(role+'-active.json'),dict(unit=value['unit']+'.service',
            begin=begin,end=end,identity=identity,properties=raw,sample=sample))

    def publish_report(self, report):
        try:
            (self.evidence/'host-processes-after.txt').open('x').write(command(['ps','-eo','pid,ppid,comm,pcpu'],cap=65536,execute=True))
        except Exception as exc:
            report['preservation_errors'].append(dict(host_process_capture_error=str(exc)[:160]));report['complete']=False
        report['launch_sha256']=payload_hash(report);publish(self.evidence/'launch-result.json',report)
        files={};total=0
        for p in sorted(self.evidence.rglob('*')):
            require(not p.is_symlink(),'evidence symlink refused')
            if p.is_dir():continue
            require(p.is_file() and len(files)<1024 and p.stat().st_size<=256*1024**2,'bounded cohort inventory required')
            total+=p.stat().st_size;require(total<=4*1024**3,'cohort inventory total cap')
            files[str(p.relative_to(self.evidence))]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        value=dict(schema_version='qcrl.recorder_persistence_cohort_inventory.v1',files=files,
            freeze_sha256=self.frozen['freeze_sha256'],native_origin_verified=False)
        value['inventory_sha256']=payload_hash(value);publish(self.root/'origin-inventory.json',value)


def verify_case_lifecycle(root,case):
    from infra.stream.recorder_application_evaluator import large_control
    producer=large_control(Path(root)/'producer.json')
    require(producer['case_sha256']==case['artifact_sha256'],'producer case differs')
    worker.verify_closure(producer['result'],producer['terminal_receive'],producer['controls'],
        producer['control_errors'],worker.verify_recorder_completion(root,case),case)


def execute_cohort(ops, *, execute=False):
    require(execute is True,'explicit finite smoke launch required')
    frozen=ops.frozen;before=ops.preflight();ops.claim()
    report=dict(schema_version='qcrl.recorder_persistence_cohort_launch.v1',
        stage=str(ops.root),freeze_sha256=frozen['freeze_sha256'],cohort_plan_sha256=payload_hash(PLAN),
        public_before=before,public_after=None,complete=False,completed=[],error=None,preservation_errors=[],
        native_origin_verified=False,compatibility_verified=False,budget_cohort_authorized=False,orders_authorized=False)
    started=[];captured=set();stopped=set()
    def start(role):
        value=spec(str(ops.root),role,ops.case_name);started.append(value);ops.start(value);return value
    def capture(value):
        captured.add(value['unit']);result=ops.capture(value['unit'],max_journal_bytes=65536)
        require(result==dict(unit=value['unit'],result='success',exec_status=0,substate='exited',observed_properties=value['properties']),
            'cohort unit exit/effective properties differ')
    def stop(value):ops.stop(value['unit']);stopped.add(value['unit'])
    try:
        tests=start('tests');ops.finish(tests['unit'],timeout_seconds=240);capture(tests)
        text=(ops.evidence/(tests['unit']+'-journal.txt')).read_text()
        require(re.findall(r'Ran (\d+) tests in [\d.]+s',text)[-1:]==[str(frozen['linux_tests'])]
                and re.findall(r'OK \(skipped=(\d+)\)',text)[-1:]==['1'],'Linux readiness population/success differs')
        stop(tests)
        require(all(ops.recheck(str(ops.root),frozen).values()) and ops.public_state()==before,'post-regression drift')
        for case_name in PLAN['case_order']:
            ops.prepare(case_name);case=worker.control(ops.evidence/case_name/'case.json');deadline=case['epoch']-.1
            producer=start('producer');server=ops.ready('server-ready.json',deadline);pb=ops.bind('producer',server,deadline)
            consumer=start('consumer');ready=ops.ready('worker-ready.json',deadline);observer=ops.ready('observer-ready.json',deadline)
            require(all(v['case_sha256']==case['artifact_sha256'] and v['at']<deadline
                        for v in (server,ready,observer)), 'cohort readiness case/epoch differs')
            require(ready['identity']==observer['identity'] and ready['identity']['boot_id']==server['identity']['boot_id']
                    and ready['identity']['cgroup']!=server['identity']['cgroup'],'cohort actor isolation differs')
            cb=ops.bind('consumer',ready,deadline)
            require(time.monotonic()<deadline,'release missed original epoch')
            worker.publish(ops.evidence/case_name/'bindings-ready.json',dict(case_sha256=case['artifact_sha256'],at=time.monotonic(),
                           producer_binding=pb['artifact_sha256'],consumer_binding=cb['artifact_sha256']))
            for value in (consumer,producer):ops.finish(value['unit'],timeout_seconds=240);capture(value);stop(value)
            verify_case_lifecycle(ops.evidence/case_name,case)
            require(all(ops.recheck(str(ops.root),frozen).values()) and ops.public_state()==before,'between-case source/runtime/public drift')
            report['completed'].append(case_name)
        report['complete']=True
    except (Exception,KeyboardInterrupt) as exc:
        report['error']=(type(exc).__name__+':'+str(exc))[:160]
    finally:
        for value in reversed(started):
            unit=value['unit']
            if unit not in captured:
                captured.add(unit)
                try:ops.capture(unit,max_journal_bytes=65536)
                except Exception as exc:report['preservation_errors'].append(dict(unit=unit,capture_error=str(exc)[:160]))
            if unit not in stopped:
                try:ops.stop(unit)
                except Exception as exc:report['preservation_errors'].append(dict(unit=unit,stop_error=str(exc)[:160]))
        try:
            report['public_after']=ops.public_state()
            require(report['public_after']==before and all(ops.recheck(str(ops.root),frozen).values()),'final public/source/runtime drift')
        except Exception as exc:report['error']=report['error'] or str(exc)[:160]
        report['complete']=report['complete'] and report['error'] is None and not report['preservation_errors']
        ops.publish_report(report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--case',choices=PLAN['case_order']);p.add_argument('--worker',choices=('prepare','producer','consumer'));p.add_argument('--execute',action='store_true')
    a=p.parse_args();require(a.execute,'explicit cohort --execute required')
    if a.worker:return worker_main(a.root,a.worker,a.case,execute=True)
    report=execute_cohort(CohortProduction(a.root,load(a.root/'execution-freeze.json'),execute=True),execute=True)
    require(report['complete'],'cohort incomplete; retained, no replay')


if __name__=='__main__':main()
