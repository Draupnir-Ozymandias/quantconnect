"""One fixed public-study operator. No default execution or alternate target."""
import argparse
from datetime import timedelta
import hashlib
import importlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler, HTTPSHandler, Request

from execution_truth.acquisition import PublicPolymarketAcquirer, utc_now, utc_text
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream.recorder_application_worker import load
from infra.stream.recorder_persistence_worker import publish, control
from infra.stream.recorder_public_counts import PLAN, require, utc
from infra.stream.recorder_public_study import validate_case, ROOT, PYTHON
from infra.stream.recorder_public_capture import short_error
from infra.stream.recorder_wait_production import command, digest, inspect_source, seconds
from infra.stream.recorder_wait_lifecycle import BASE_PROPERTIES

STAGE='/var/lib/qcrl-stream/public-feed-20261020T160000Z'
UNIT='qcrl-public-counts-20261020T160000Z'


def tls_profile():
    import ssl
    modules={}
    for name in ('_socket','_ssl','http.client','selectors','socket','ssl','tempfile','threading','urllib.request'):
        module=importlib.import_module(name)
        modules[name]=dict(path=module.__file__,sha256=digest(module.__file__))
    paths={line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
           if line.split()[-1].startswith('/')
           and any(v in line.split()[-1] for v in ('libssl.so','libcrypto.so'))}
    require(len(paths)==2,'unique installed OpenSSL libraries required')
    ca=ssl.get_default_verify_paths().cafile
    require(ca is not None,'default CA file unavailable')
    return dict(openssl=ssl.OPENSSL_VERSION,modules=modules,
                libraries={p:digest(p) for p in sorted(paths)},ca_file=ca,ca_sha256=digest(ca))


def pinned_tls(frozen):
    import ssl
    require(tls_profile()==frozen['tls'],'installed socket/TLS bytes or CA snapshot changed')
    path=Path(frozen['tls']['ca_file'])
    with path.open('rb') as handle:
        data=handle.read(4*1024**2+1)
    require(len(data)<=4*1024**2,'bounded system CA bundle required')
    require(hashlib.sha256(data).hexdigest()==frozen['tls']['ca_sha256'],'system CA bytes changed')
    # OpenSSL's file loader accepts bundle comments without a Python ASCII decode.
    # Feed it only the verified bytes in a private anonymous snapshot, so replacing
    # the original CA pathname after hashing cannot change the loaded trust roots.
    require(platform.system() in ('Linux','Darwin'),'CA descriptor interface unavailable')
    with tempfile.TemporaryFile(mode='w+b') as snapshot:
        require(snapshot.write(data)==len(data),'incomplete private CA snapshot')
        snapshot.flush();snapshot.seek(0)
        descriptor=('/proc/self/fd/' if platform.system()=='Linux' else '/dev/fd/')+str(snapshot.fileno())
        context=ssl.create_default_context(cafile=descriptor)
    require(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED,'verified TLS context required')
    return context


def properties():
    value=dict(BASE_PROPERTIES,ReadWritePaths=STAGE+'/evidence',ReadOnlyPaths=STAGE+'/source',
        InaccessiblePaths='-/etc/qcrl-stream.env -/etc/qcrl-collector.env',
        RestrictAddressFamilies='AF_UNIX AF_INET AF_INET6',
        IPAddressDeny='169.254.169.254/32 169.254.170.2/32 fd00:ec2::254/128')
    return value


def verify_properties(raw):
    want=properties()
    for key in ('User','Group','TasksMax','RemainAfterExit','NoNewPrivileges','PrivateTmp','ProtectSystem','ProtectHome'):
        require(raw.get(key)==want[key],'effective public unit property differs: '+key)
    require(raw.get('MemoryMax')=='536870912' and seconds(raw.get('CPUQuotaPerSecUSec',''))==.75
            and seconds(raw.get('RuntimeMaxUSec',''))==240,'effective public resource limits differ')
    for key in ('ReadWritePaths','ReadOnlyPaths','InaccessiblePaths','RestrictAddressFamilies'):
        require({v.lstrip('-') for v in raw.get(key,'').split()}=={v.lstrip('-') for v in want[key].split()},
                'effective public isolation differs: '+key)
    try:
        deny={str(ipaddress.ip_network(v)) for v in raw.get('IPAddressDeny','').split()}
    except ValueError as exc:
        raise ContractError('invalid effective metadata network isolation') from exc
    require(deny=={str(ipaddress.ip_network(v)) for v in want['IPAddressDeny'].split()}
            and not raw.get('IPAddressAllow',''),'metadata network isolation differs')
    return want


def public_state():
    services=('qcrl-collector.timer','qcrl-stream-pilot.service','qcrl-stream-observer.service')
    return dict(collectors={name:command(['systemctl','show',name,'--property=ActiveState','--value'],execute=True).strip()
                            for name in services},
        environment_sha256=digest('/etc/qcrl-stream.env',cap=1048576),
        public_head=command(['git','-c','safe.directory=/opt/qcrl-stream','-C','/opt/qcrl-stream',
                            'rev-parse','HEAD'],execute=True).strip())


def make_freeze(source, runtime, tls, public, approval_sha):
    sources,commit=inspect_source(source)
    value=dict(schema_version='qcrl.public_feed_interval_counts.freeze.v1',study_plan=PLAN,
        study_plan_sha256=payload_hash(PLAN),source_commit=commit,sources=sources,
        runtime=runtime,tls=tls,public_state=public,operator_approval_sha256=approval_sha,
        boot_id=runtime['boot_id'],native_public_path_previously_validated=False,
        original_application_verdict='fail',historical_application_experiments=['Cohort02','RssCpu01'],
        internal_socket_tls_retry_count=None,unit_properties=properties(),orders_authorized=False)
    return dict(value,freeze_sha256=payload_hash(value))


def verify_freeze(root, frozen):
    verify_artifact_hash(frozen,'freeze_sha256','public study freeze')
    require(frozen['study_plan']==PLAN and frozen['study_plan_sha256']==payload_hash(PLAN)
            and frozen['unit_properties']==properties(),'public study frozen plan differs')
    sources,commit=inspect_source(ROOT)
    require(sources==frozen['sources'] and commit==frozen['source_commit'],'public study source drift')
    from infra.stream.recorder_rss_thread_cpu_validation import runtime
    require(runtime(root)==frozen['runtime'],'installed runtime drift')
    pinned_tls(frozen)  # Read-only context construction is a readiness requirement.
    require(public_state()==frozen['public_state'],'public collector source/environment/state drift')
    approval=control(Path(root)/'operator-approval.json')
    require(approval['artifact_sha256']==frozen['operator_approval_sha256']
            and approval['case']==PLAN['case'] and approval['one_case_only'] is True,
            'target authorization differs')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ContractError('public discovery redirect refused')


class MetadataTransport:
    def __init__(self,root,*,tls_context=None):
        self.root=Path(root);self.requests=0
        self.opener=build_opener(ProxyHandler({}),NoRedirect(),HTTPSHandler(context=tls_context))

    def get_json(self,url,params=None):
        require(self.requests<5,'single metadata request budget reached')
        parsed=urlsplit(url)
        require(parsed.scheme=='https' and parsed.hostname in
                ('gamma-api.polymarket.com','clob.polymarket.com')
                and parsed.netloc==parsed.hostname and not parsed.query and not parsed.fragment,
                'public GET endpoint differs')
        if parsed.hostname=='gamma-api.polymarket.com':
            slug='btc-updown-5m-'+str(int(utc(PLAN['event_start']).timestamp()))
            require(not params and (parsed.path=='/markets/slug/'+slug
                    or re.fullmatch(r'/markets/[0-9]+',parsed.path)), 'public market metadata path differs')
        elif parsed.path=='/book':
            require(isinstance(params,dict) and set(params)=={'token_id'}
                    and isinstance(params['token_id'],str) and params['token_id'].isdecimal(),
                    'public book token query differs')
        else:
            require(not params and re.fullmatch(r'/clob-markets/0x[0-9a-fA-F]{64}',parsed.path),
                    'public condition metadata path differs')
        self.requests+=1
        if params:url+='?'+urlencode(params)
        before=utc_text(utc_now())
        publish(self.root/('request-%d.json'%self.requests),dict(url=url,before_utc=before,
            timeout_seconds=10,global_deadline_enforced_by_parent=True))
        request=Request(url,headers={'User-Agent':'QCRL-execution-truth/1'})
        partial=self.root/('response-%d.partial'%self.requests)
        chunks=[];size=0
        with self.opener.open(request,timeout=10) as response, partial.open('xb') as handle:
            while True:
                chunk=response.read(min(65536,2*1024**2+1-size))
                if not chunk:break
                size+=len(chunk);chunks.append(chunk);handle.write(chunk);handle.flush()
                require(size<=2*1024**2,'public metadata response cap reached')
            os.fsync(handle.fileno())
        data=b''.join(chunks)
        path=self.root/('response-%d.body'%self.requests)
        os.link(partial,path);partial.unlink()
        publish(self.root/('response-%d.json'%self.requests),dict(url=url,before_utc=before,
            after_utc=utc_text(utc_now()),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
        value=json.loads(data)
        require(isinstance(value,dict),'metadata JSON object required')
        return value


def discover(root, frozen, *, execute=False, clock=utc_now, acquirer_factory=PublicPolymarketAcquirer):
    require(execute is True,'explicit fixed metadata acquisition required')
    now=clock()
    require(utc(PLAN['discovery'])<=now<utc(PLAN['discovery'])+timedelta(seconds=30),
            'fixed metadata opportunity missed')
    root=Path(root)
    publish(root/'metadata-attempt.json',dict(case=PLAN['case'],at_utc=utc_text(now),retry_authorized=False))
    directory=root/'metadata';directory.mkdir(exist_ok=False)
    transport=MetadataTransport(directory,tls_context=pinned_tls(frozen))
    acquirer=acquirer_factory(transport=transport,clock=clock)
    slug='btc-updown-5m-'+str(int(utc(PLAN['event_start']).timestamp()))
    resolution=acquirer.resolve_market_slug(slug,'market')
    publish(directory/'resolution.json',resolution)
    raw=acquirer.acquire_market_bundle(resolution['resolved_market_id'])
    from execution_truth.market_stream import stream_plan
    value=dict(case=PLAN['case'],study_plan_sha256=payload_hash(PLAN),
        freeze_sha256=frozen['freeze_sha256'],discovered_at_utc=utc_text(clock()),
        raw_bundle=raw,spec=stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000))
    require(len(json.dumps(value).encode())<=2*1024**2,'case control cap reached')
    case=dict(value,artifact_sha256=payload_hash(value));validate_case(case)
    publish(root/'case.json',value)
    return case


def run_controller(ops):
    """Finite order only: one lookup then one capture unit, or retained not-run."""
    started=False
    try:
        ops.preflight()
        ops.wait_until('discovery')
        case=ops.discover()
        ops.lock(case)
        ops.wait_until('arm')
        ops.preflight()
        try:
            ops.start()
        finally:
            started=ops.submission_attempted
        ops.release(case)
        ops.await_exit()
    except BaseException as exc:
        ops.failure(short_error(exc),started)
    finally:
        if started:ops.stop_and_seal()


class Production:
    def __init__(self,root,freeze_sha,*,execute=False):
        self.root=Path(root)
        require(execute is True and platform.system()=='Linux' and os.geteuid()==0
            and str(self.root)==STAGE and self.root.resolve(strict=True)==self.root
            and ROOT==self.root/'source' and os.path.abspath(sys.executable)==PYTHON,
            'explicit canonical root Linux public-study operator required')
        require(utc(PLAN['discovery'])-timedelta(minutes=10)<=utc_now()<utc(PLAN['discovery']),
                'fixed operator preparation window missed; no early or late adoption')
        self.frozen=load(self.root/'execution-freeze.json')
        require(self.frozen['freeze_sha256']==freeze_sha,'operator freeze byte anchor differs')
        self.evidence=self.root/'evidence'
        self.submission_attempted=False
        publish(self.root/'controller-claim.json',dict(freeze_sha256=freeze_sha,pid=os.getpid(),
            case=PLAN['case'],one_case_only=True))

    def preflight(self):
        verify_freeze(self.root,self.frozen)
        require(shutil.disk_usage(self.root).free>=PLAN['disk_start_bytes'],'study disk readiness failed')
        require(not (self.root/'cancel').exists(),'public study cancelled')

    def wait_until(self,key):
        target=utc(PLAN[key])
        while utc_now()<target:
            require(not (self.root/'cancel').exists(),'public study cancelled')
            time.sleep(min(1,max(0,(target-utc_now()).total_seconds())))

    def discover(self):
        self.preflight()
        require(not self.evidence.exists(),'fresh public evidence namespace required')
        command(['install','-d','-o','qcrl','-g','qcrl','-m','750',str(self.evidence)],execute=True)
        remaining=(utc(PLAN['discovery'])+timedelta(seconds=30)-utc_now()).total_seconds()
        require(0<remaining<=30,'metadata deadline missed')
        try:
            command(['sudo','-u','qcrl',PYTHON,'-m','infra.stream.recorder_public_operator',
                'metadata','--root',str(self.root),'--freeze-sha256',self.frozen['freeze_sha256'],'--execute'],
                timeout=remaining,execute=True)
        except Exception as exc:
            if hasattr(exc,'output'):
                with (self.root/'metadata-worker-output.partial').open('xb') as handle:handle.write(exc.output)
            raise
        return validate_case(control(self.evidence/'case.json'))

    def lock(self,case):
        require(utc_now()<utc(PLAN['freeze_cutoff']),'case lock cutoff missed')
        publish(self.root/'case-lock.json',dict(case_sha256=case['artifact_sha256'],
            freeze_sha256=self.frozen['freeze_sha256'],locked_at_utc=utc_text(utc_now()),
            target_authorization_sha256=self.frozen['operator_approval_sha256']))

    def start(self):
        require(utc(PLAN['arm'])<=utc_now()<utc(PLAN['nominal_epoch']),'arm window missed')
        require(not command(['systemctl','list-units','--all','--no-legend',UNIT+'*'],execute=True).strip(),
                'public study unit namespace already used')
        self.submission_attempted=True
        command(['systemd-run','--unit='+UNIT,'--working-directory='+str(ROOT),
            '--setenv=PYTHONDONTWRITEBYTECODE=1',
            *['--property='+k+'='+v for k,v in properties().items()],PYTHON,
            '-m','infra.stream.recorder_public_study','consume','--root',str(self.evidence),'--execute'],execute=True)

    def release(self,case):
        ready=self.evidence/'worker-ready.json'
        stop=time.monotonic()+15
        while not ready.exists() and time.monotonic()<stop:time.sleep(.05)
        value=control(ready);identity=value['identity']
        require(value['case_sha256']==case['artifact_sha256'],'study worker binding differs')
        text=command(['systemctl','show',UNIT+'.service'],execute=True)
        props=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
        verify_properties(props)
        require(props.get('MainPID')==str(identity['pid']) and props.get('ControlGroup')==identity['cgroup']
            and props.get('WorkingDirectory')==str(ROOT) and 'infra.stream.recorder_public_study' in props.get('ExecStart',''),
            'actual study unit identity/command differs')
        from infra.stream.recorder_application_resources import LinuxReader
        require(LinuxReader(execute=True,pid=identity['pid']).expected==identity,'external study PID/start/boot differs')
        require(time.monotonic()<value['epoch_ns']/1e9-1,'unit release missed original epoch')
        with (self.root/'unit-before.txt').open('x') as handle:handle.write(text)
        publish(self.evidence/'release.json',dict(case_sha256=case['artifact_sha256'],identity=identity,
            epoch_ns=value['epoch_ns'],at=time.monotonic()))

    def await_exit(self):
        end=time.monotonic()+240
        while time.monotonic()<end:
            require(not (self.root/'cancel').exists(),'public study cancelled')
            state=command(['systemctl','show',UNIT+'.service','--property=SubState','--value'],execute=True).strip()
            if state in ('exited','dead','failed'):
                require((self.evidence/'consumer.json').exists(),'worker exited without consumer receipt')
                publish(self.root/'controller-outcome.json',dict(case=PLAN['case'],
                    capture_unit_submission_attempted=True,disposition='collected_pending_independent_audit',
                    unit_substate=state,original_application_verdict='fail',orders_authorized=False))
                return
            time.sleep(1)
        raise ContractError('public unit completion deadline reached')

    def failure(self,error,started):
        publish(self.root/'controller-outcome.json',dict(case=PLAN['case'],capture_unit_submission_attempted=started,
            disposition='partial_or_unresolved' if started else 'not_run',error=error,
            original_application_verdict='fail',orders_authorized=False))

    def stop_and_seal(self):
        # Never touch other unit names, public collectors or historical stages.
        errors=[]
        try:
            text=command(['systemctl','show',UNIT+'.service'],execute=True)
            props=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
            require(props.get('WorkingDirectory')==str(ROOT)
                and 'infra.stream.recorder_public_study' in props.get('ExecStart',''),
                'cannot adopt or stop a foreign unit')
            with (self.root/'unit-after.txt').open('x') as handle:handle.write(text)
            try:
                journal=command(['journalctl','-u',UNIT+'.service','--no-pager','-o','short-monotonic'],cap=262144,execute=True)
                with (self.root/'unit-journal.txt').open('x') as handle:handle.write(journal)
            except Exception as exc:
                errors.append(short_error(exc))
                if hasattr(exc,'output'):
                    with (self.root/'unit-journal.partial').open('xb') as handle:handle.write(exc.output)
        except Exception as exc:
            errors.append(short_error(exc))
        finally:
            # A newly submitted unit can have disappeared on a start failure.
            # Stop only after its frozen command/root binding was actually seen.
            if 'props' in locals() and props.get('WorkingDirectory')==str(ROOT) and \
                    'infra.stream.recorder_public_study' in props.get('ExecStart',''):
                try:
                    command(['systemctl','stop',UNIT+'.service'],execute=True)
                except Exception as exc:
                    errors.append(short_error(exc))
        try:
            verify_freeze(self.root,self.frozen)
        except Exception as exc:
            errors.append(short_error(exc))
        files={}
        for path in sorted(self.evidence.rglob('*')):
            require(not path.is_symlink(),'study evidence symlink')
            if path.is_file():files[str(path.relative_to(self.evidence))]=dict(bytes=path.stat().st_size,sha256=file_hash(path))
        require(len(files)<=1024 and sum(v['bytes'] for v in files.values())<=PLAN['spool_cap_bytes'],
                'study evidence inventory cap exceeded')
        publish(self.root/'origin-inventory.json',dict(files=files,freeze_sha256=self.frozen['freeze_sha256'],
            case=PLAN['case'],native_origin_verified=False,requires_observed_origin_attestation=True))
        publish(self.root/'post-run-checks.json',dict(errors=errors,
            observed_utc=utc_text(utc_now()),public_after=public_state()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['metadata','controller'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--freeze-sha256',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.action=='controller':run_controller(Production(args.root,args.freeze_sha256,execute=args.execute))
    else:
        require(args.execute and platform.system()=='Linux' and str(args.root)==STAGE
                and args.root.resolve(strict=True)==args.root and ROOT==args.root/'source'
                and os.path.abspath(sys.executable)==PYTHON,'explicit installed fixed metadata worker required')
        frozen=load(args.root/'execution-freeze.json')
        verify_artifact_hash(frozen,'freeze_sha256','metadata source freeze')
        require(frozen['freeze_sha256']==args.freeze_sha256,'metadata freeze anchor differs')
        discover(args.root/'evidence',frozen,execute=True)


if __name__=='__main__':main()
