"""One recorder compatibility smoke; no cohort path, replay or timing experiment."""
import argparse
from copy import deepcopy
from datetime import timedelta
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
from infra.stream.recorder_wait_production import Production, command, inspect_source, observe_runtime, PYTHON, verified_properties
from infra.stream.recorder_wait_compatibility_worker import load, publish

ROOT = Path(__file__).resolve().parents[2]
STAGE = r'/var/lib/qcrl-stream/recorder-absolute-[A-Za-z0-9]+'
PLAN = dict(schema_version='qcrl.recorder_persistence_smoke_plan.v2',
    failed_predecessor_freeze='f045b0612401874948d307bde0e1cc11447d64837c082de9510a050d8de1da93',
    persistence_reserve_seconds=1, reserve_is_guarantee=False,
    closure='all_planned_sends_and_verified_recorder_completion_and_normal_close',
    observer_policy_sha256='bdd41717abfb6b5d02e21fb11cf8059fab27723b80497a893a66c28adc50e52f',
    cpu_pre_read_lead_ns=50_000_000, previous_lead_ns=2_000_000,
    measurement_timing_changed=True, earlier_results_superseded=False,
    occurrences=68, offsets_seconds=list(range(68)), capture_seconds=180,
    epoch_lead_seconds=20, readiness_margin_seconds=.1, resource_duration_seconds=67,
    required_complete_cpu_windows=[0], resource_slots_max=184,
    unit_cpu_percent=75, unit_memory_bytes=536870912, unit_tasks=32, unit_seconds=240,
    regression_units=1, producer_units=1, consumer_units=1, measurement_runs=1,
    regression_skip_count=1, compatibility_control_case='steady-0',
    population='first_68_unmodified_parent_corpus_occurrences',
    producer_wait='existing_relative_sleep_may_retry_internally_count_unknown',
    stopping='one_smoke_then_independent_review_no_cohort_no_replay_no_tuning',
    native_execution_authorized=False, compatibility_verified=False,
    budget_acceptance=False, orders_authorized=False)


def declaration():
    from execution_truth.stream_segments import file_hash
    value = observer_declaration()
    value.pop('declaration_sha256')
    value['schema_version'] = 'qcrl.recorder_persistence_declaration.v2'
    value['observer_plan'] = value['plan']
    value['plan'] = deepcopy(PLAN)
    value['plan_sha256'] = payload_hash(PLAN)
    from infra.stream.recorder_persistence_lane import PERSISTENCE_POLICY
    value['successor_runtime_policy'] = deepcopy(PERSISTENCE_POLICY)
    value['successor_smoke_plan_sha256'] = payload_hash(PLAN)
    for name in ('infra/stream/recorder_persistence_lane.py',
                 'infra/stream/recorder_persistence_worker.py',
                 'infra/stream/recorder_persistence_smoke.py',
                 'infra/stream/recorder_persistence_smoke_audit.py',
                 'tests/test_recorder_persistence_runtime.py',
                 'docs/RECORDER_PERSISTENCE_SMOKE_PREPARATION.md'):
        value['sources'][name] = file_hash(ROOT/name)
    value['declaration_sha256'] = payload_hash(value)
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


def freeze(commit, sources, installed, linux_tests):
    validate_runtime(installed['wait'])
    require(re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',installed['boot_id']), 'observed boot required')
    host=installed['host']
    require(host['instance_id']=='i-039c11d5ea49cf413' and host['region']=='us-east-2'
        and host['instance_type']=='t4g.small' and host['credit_mode']=='standard'
        and host['boot_id']==installed['boot_id'] and host['method']=='read_only_ec2_console'
        and host['credit_balance'] is None and re.fullmatch('[0-9a-f]{64}',host['console_text_sha256'])
        and host['observed_utc'], 'observed host/credit envelope required')
    require(re.fullmatch('[0-9a-f]{40}', commit) and type(linux_tests) is int and linux_tests > 1114,
            'exact candidate and declared Linux regression population required')
    require(installed['websockets']['version'] == '15.0.1' and {'websockets/sync/client.py','websockets/sync/server.py'}<=set(installed['websockets']['files'])
            and all(re.fullmatch('[0-9a-f]{64}',h) for h in installed['websockets']['files'].values()),
            'observed installed dependency required')
    required=set(declaration()['sources'])|{'infra/stream/recorder_persistence_smoke.py',
        'infra/stream/recorder_persistence_smoke_audit.py','tests/test_recorder_persistence_runtime.py',
        'docs/RECORDER_PERSISTENCE_SMOKE_PREPARATION.md'}
    require(required<=set(sources) and all(selected(n) and re.fullmatch('[0-9a-f]{64}',h) for n,h in sources.items()),
            'complete smoke source inventory required')
    value = dict(schema_version='qcrl.recorder_persistence_smoke_freeze.v1',
        source_commit=commit, sources=deepcopy(sources), runtime=deepcopy(installed),
        smoke_plan_sha256=payload_hash(PLAN), observer=declaration(),
        linux_tests=linux_tests, linux_skips=1, native_execution_authorized=False,
        compatibility_verified=False, acceptance_demonstrated=False, orders_authorized=False)
    value['freeze_sha256'] = payload_hash(value)
    return value


def validate_freeze(value):
    verify_artifact_hash(value, 'freeze_sha256', 'recorder smoke freeze')
    require(value == freeze(value['source_commit'], value['sources'], value['runtime'], value['linux_tests']),
            'recorder smoke freeze/declaration differs')
    for name, digest in value['observer']['sources'].items():
        require(value['sources'].get(name) == digest, 'observer source absent from execution freeze')
    return value


def prepare(root, freeze_hash, *, execute=False):
    require(execute is True, 'explicit smoke preparation required')
    require(re.fullmatch('[0-9a-f]{64}',freeze_hash),'exact smoke freeze binding required')
    from tests.test_taker_replay import raw_bundle, revise
    root = Path(root); root.mkdir(exist_ok=False)
    before = time.monotonic(); now = utc_now(); after = time.monotonic()
    epoch = after+20; epoch_utc = now+timedelta(seconds=epoch-before)
    raw = raw_bundle()
    revise(raw, 'gamma_market', startDate=utc_text(epoch_utc-timedelta(seconds=60)),
           eventStartTime=utc_text(epoch_utc-timedelta(seconds=10)),
           endDate=utc_text(epoch_utc+timedelta(seconds=290)))
    spec = stream_plan(raw, segmented=True, max_frames=68, max_seconds=180)
    case = worker.publish(root/'case.json', dict(case='steady-0',
        plan_sha256=parent_declaration()['plan_sha256'],freeze_sha256=freeze_hash,
        smoke_plan_sha256=payload_hash(PLAN), smoke_only=True,
        epoch=epoch, epoch_utc=utc_text(epoch_utc), epoch_clock=dict(before=before, after=after,utc=utc_text(now)),
        raw_bundle=raw, spec=spec, fixture_is_synthetic=True,
        implementation_sources=worker.implementation_sources(),
        boot_id=boot()))
    worker.publish(root/'absolute-wait-plan.json', dict(case_sha256=case['artifact_sha256'], declaration=declaration()))
    return case


def transmit(conn, kind, epoch, *, clock=time.monotonic, pause=time.sleep):
    rows, error = [], None
    try:
        for i in range(68):
            deadline=epoch+i; pause(max(0, deadline-clock())); begin=clock()
            raw=worker.message(i); conn.send(raw)
            rows.append(dict(sequence=i, phase=0, offset=i, deadline=deadline,
                begin=begin, end=clock(), raw_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    except (Exception, KeyboardInterrupt) as exc:
        error=(type(exc).__name__+':'+str(exc))[:160]
    return dict(rows=rows, error=error, complete=error is None and len(rows)==68,
                internal_retry_count=None)


def spec(stage, role):
    require(re.fullmatch(STAGE, stage) and role in ('tests','producer','consumer'), 'fixed smoke unit required')
    tag=stage.rsplit('recorder-absolute-',1)[1]
    evidence=stage+'/evidence'+('' if role=='tests' else '/case')
    props=dict(BASE_PROPERTIES,ReadWritePaths=evidence,ReadOnlyPaths=stage+'/source',
        InaccessiblePaths='-/etc/qcrl-stream.env -/etc/qcrl-collector.env',
        RestrictAddressFamilies='AF_UNIX AF_INET',IPAddressAllow='127.0.0.1/32')
    return dict(unit='qcrl-recorder68-'+tag+'-'+role,role='tests',worker_role=role,
                properties=props,working_directory=stage+'/source')


def worker_main(root, role, *, execute=False):
    root=Path(root)
    require(execute is True and platform.system()=='Linux'
        and os.geteuid()==pwd.getpwnam('qcrl').pw_uid and root==ROOT.parent/'evidence/case'
        and re.fullmatch(STAGE,str(ROOT.parent)) and os.path.abspath(sys.executable)==PYTHON,
        'canonical explicit qcrl Linux recorder smoke worker required')
    frozen=validate_freeze(load(ROOT.parent/'execution-freeze.json'))
    sources,commit=inspect_source(ROOT)
    require(sources==frozen['sources'] and commit==frozen['source_commit']
            and runtime(ROOT.parent)==frozen['runtime'], 'smoke worker source/runtime drift')
    if role=='prepare': return prepare(root,frozen['freeze_sha256'],execute=True)
    case=worker.control(root/'case.json')
    require(case['smoke_only'] is True and case['smoke_plan_sha256']==payload_hash(PLAN)
        and case['freeze_sha256']==frozen['freeze_sha256']
        and case['spec']['max_frames']==68 and case['spec']['max_seconds']==180,
        'only the fixed recorder smoke may execute')
    binding=worker.control(root/'absolute-wait-plan.json')
    require(binding['case_sha256']==case['artifact_sha256'] and binding['declaration']==declaration(),
        'successor case/declaration differs')
    from infra.stream.recorder_application_budget import declare
    if role=='producer': return worker.produce(root,declare(),execute=True,transmitter=transmit)
    require(role=='consumer','unknown smoke worker role')
    return worker.consume(root,declare(),execute=True,resource_observer=lambda reader,epoch,stop: observe_absolute(reader,epoch,stop,execute=True))


class SmokeProduction(Production):
    def __init__(self, root, frozen, *, execute=False):
        self.root=Path(root);self.frozen=validate_freeze(frozen);self.evidence=self.root/'evidence';self.specs={}
        require(execute is True and platform.system()=='Linux' and os.geteuid()==0
            and re.fullmatch(STAGE,str(self.root)) and self.root.resolve(strict=True)==self.root
            and ROOT==self.root/'source' and os.path.abspath(sys.executable)==PYTHON,
            'explicit canonical Linux root smoke stage required')

    def recheck(self, stage, frozen):
        sources,commit=inspect_source(self.root/'source')
        return dict(clean_source=True,source_freeze_matches=sources==frozen['sources'] and commit==frozen['source_commit'],
                    runtime_freeze_matches=runtime(self.root)==frozen['runtime'])

    def preflight(self):
        require(all(self.recheck(str(self.root),self.frozen).values()),'source/runtime preflight failed')
        for name in ('evidence','launch-claim.json','origin-inventory.json'):
            require(not (self.root/name).exists() and not (self.root/name).is_symlink(),'fresh smoke stage required')
        require(shutil.disk_usage(self.root).free>4*1024**3,'four GiB reserve required')
        tag=spec(str(self.root),'tests')['unit'].removesuffix('-tests')
        require(not command(['systemctl','list-units','--all','--full','--no-legend',tag+'-*'],execute=True).strip(),
                'private smoke unit prefix exists')
        require((self.root/'source').stat().st_uid==pwd.getpwnam('qcrl').pw_uid,'qcrl source ownership required')
        for name in ('execution-freeze.json','runtime-review.json','select-review-source.c','host-context.json'):
            require((self.root/name).is_file() and not (self.root/name).is_symlink(),'regular smoke controls required')
            command(['sudo','-u','qcrl','test','-r',str(self.root/name)],execute=True)
        before=self.public_state()
        require(before==self.frozen['runtime']['host']['public'],'approved public source/environment drift')
        require(before['collectors']=={n:'active' if n.endswith('.timer') else 'inactive' for n in before['collectors']},
                'public prerequisites differ')
        return before

    def start(self, value):
        role=value['worker_role'];require(value==spec(str(self.root),role),'fixed smoke unit only')
        self.specs[value['unit']]=value
        args=['-m','unittest','discover','-s','tests','-q'] if role=='tests' else [
            '-m','infra.stream.recorder_persistence_smoke','--root',str(self.root/'evidence/case'),
            '--worker',role,'--execute']
        command(['systemd-run','--unit='+value['unit'],'--working-directory='+str(self.root/'source'),
            *['--property='+k+'='+v for k,v in value['properties'].items()],PYTHON,*args],execute=True)

    def claim(self):
        publish(self.root/'launch-claim.json',dict(freeze_sha256=self.frozen['freeze_sha256'],replay_authorized=False))
        command(['install','-d','-o','qcrl','-g','qcrl','-m','750',str(self.evidence)],execute=True)
        for name in ('execution-freeze.json','runtime-review.json','select-review-source.c','host-context.json'):
            with (self.evidence/name).open('xb') as out:out.write((self.root/name).read_bytes())
        text=command(['ps','-eo','pid,ppid,comm,pcpu'],cap=65536,execute=True)
        (self.evidence/'host-processes-before.txt').open('x').write(text)

    def prepare(self):
        command(['sudo','-u','qcrl',PYTHON,'-B','-m','infra.stream.recorder_persistence_smoke',
            '--root',str(self.evidence/'case'),'--worker','prepare','--execute'],timeout=30,execute=True)

    def ready(self, filename, deadline):
        while time.monotonic()<deadline:
            if (self.evidence/'case'/filename).exists():return worker.control(self.evidence/'case'/filename)
            time.sleep(.01)
        raise ContractError('smoke readiness missed; no late adoption')

    def bind(self, role, ready, deadline):
        begin=time.monotonic()
        value=spec(str(self.root),role);_,raw=self.properties(value['unit']);verified_properties(raw,value)
        require(time.monotonic()<deadline,'binding missed original epoch')
        identity=ready['identity'];reader=LinuxReader(execute=True,pid=identity['pid']);sample=reader.read(rss=True)
        end=time.monotonic()
        require(reader.expected==identity and identity['boot_id']==self.frozen['runtime']['boot_id']
            and raw.get('Id')==value['unit']+'.service' and raw.get('MainPID')==str(identity['pid'])
            and raw.get('ExecMainPID')==str(identity['pid']) and raw.get('ControlGroup')==identity['cgroup']
            and raw.get('ActiveState')=='active' and raw.get('SubState')=='running' and end<deadline,
            'independent live smoke binding differs')
        return worker.publish(self.evidence/'case'/(role+'-active.json'),dict(unit=value['unit']+'.service',
            begin=begin,end=end,identity=identity,properties=raw,sample=sample))

    def publish_report(self, report):
        try:
            (self.evidence/'host-processes-after.txt').open('x').write(command(['ps','-eo','pid,ppid,comm,pcpu'],cap=65536,execute=True))
        except Exception as exc:
            report['preservation_errors'].append(dict(host_process_capture_error=str(exc)[:160]));report['complete']=False
        report['launch_sha256']=payload_hash(report);publish(self.evidence/'launch-result.json',report)
        files={}
        for p in sorted(self.evidence.rglob('*')):
            require(not p.is_symlink(),'evidence symlink refused')
            if p.is_dir():continue
            require(p.is_file() and len(files)<128 and p.stat().st_size<=32*1024**2,'bounded smoke inventory required')
            files[str(p.relative_to(self.evidence))]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        value=dict(schema_version='qcrl.recorder_persistence_smoke_inventory.v1',files=files,
            freeze_sha256=self.frozen['freeze_sha256'],native_origin_verified=False)
        value['inventory_sha256']=payload_hash(value);publish(self.root/'origin-inventory.json',value)


def execute_smoke(ops, *, execute=False):
    require(execute is True,'explicit finite smoke launch required')
    frozen=ops.frozen;before=ops.preflight();ops.claim()
    report=dict(schema_version='qcrl.recorder_persistence_smoke_launch.v1',
        stage=str(ops.root),freeze_sha256=frozen['freeze_sha256'],smoke_plan_sha256=payload_hash(PLAN),
        public_before=before,public_after=None,complete=False,error=None,preservation_errors=[],
        native_origin_verified=False,compatibility_verified=False,budget_cohort_authorized=False,orders_authorized=False)
    started=[];captured=set();stopped=set()
    def start(role):
        value=spec(str(ops.root),role);started.append(value);ops.start(value);return value
    def capture(value):
        captured.add(value['unit']);result=ops.capture(value['unit'],max_journal_bytes=65536)
        require(result==dict(unit=value['unit'],result='success',exec_status=0,substate='exited',observed_properties=value['properties']),
            'smoke unit exit/effective properties differ')
    def stop(value):ops.stop(value['unit']);stopped.add(value['unit'])
    try:
        tests=start('tests');ops.finish(tests['unit'],timeout_seconds=240);capture(tests)
        text=(ops.evidence/(tests['unit']+'-journal.txt')).read_text()
        require(re.findall(r'Ran (\d+) tests in [\d.]+s',text)[-1:]==[str(frozen['linux_tests'])]
                and re.findall(r'OK \(skipped=(\d+)\)',text)[-1:]==['1'],'Linux readiness population/success differs')
        stop(tests)
        require(all(ops.recheck(str(ops.root),frozen).values()) and ops.public_state()==before,'post-regression drift')
        ops.prepare();case=worker.control(ops.evidence/'case/case.json');deadline=case['epoch']-.1
        producer=start('producer');server=ops.ready('server-ready.json',deadline);pb=ops.bind('producer',server,deadline)
        consumer=start('consumer');ready=ops.ready('worker-ready.json',deadline);observer=ops.ready('observer-ready.json',deadline)
        require(all(v['case_sha256']==case['artifact_sha256'] and v['at']<deadline
                    for v in (server,ready,observer)), 'smoke readiness case/epoch differs')
        require(ready['identity']==observer['identity'] and ready['identity']['boot_id']==server['identity']['boot_id']
                and ready['identity']['cgroup']!=server['identity']['cgroup'],'smoke actor isolation differs')
        cb=ops.bind('consumer',ready,deadline)
        require(time.monotonic()<deadline,'release missed original epoch')
        worker.publish(ops.evidence/'case/bindings-ready.json',dict(case_sha256=case['artifact_sha256'],at=time.monotonic(),
                       producer_binding=pb['artifact_sha256'],consumer_binding=cb['artifact_sha256']))
        for value in (consumer,producer):ops.finish(value['unit'],timeout_seconds=240);capture(value);stop(value)
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
    p.add_argument('--worker',choices=('prepare','producer','consumer'));p.add_argument('--execute',action='store_true')
    a=p.parse_args();require(a.execute,'explicit smoke --execute required')
    if a.worker:return worker_main(a.root,a.worker,execute=True)
    report=execute_smoke(SmokeProduction(a.root,load(a.root/'execution-freeze.json'),execute=True),execute=True)
    require(report['complete'],'smoke incomplete; retained, no replay')


if __name__=='__main__':main()
