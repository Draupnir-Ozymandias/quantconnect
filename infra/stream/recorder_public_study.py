"""Fixed one-case public-study worker and independent descriptive report.

There is no discovery or launcher fallback in this module. A separately frozen
operator packet must supply the one discovered case and independent release.
"""
import argparse
from copy import deepcopy
from datetime import timedelta
import json
import os
from pathlib import Path
import platform
import threading
import time

from execution_truth.acquisition import utc_now, utc_text
from execution_truth.bundle import normalize_bundle
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import stream_plan, verify_stream_log
from execution_truth.rolling_stream import check_market, SOURCE, DESCRIPTION
from execution_truth.stream_segments import exclusive_json, file_hash
from infra.stream.recorder_absolute_observer import observe_absolute
from infra.stream.recorder_application_resources import LinuxReader
from infra.stream.recorder_completion import CompletionWitnesses, verify_completion
from infra.stream.recorder_persistence_worker import publish, control
from infra.stream.recorder_application_worker import load
from infra.stream.recorder_public_capture import collect, short_error, StorageGuard, normal_completion_proven, STOP_POLICY, PUBLICATION_POLICY, NOTICE_POLICY
from infra.stream.recorder_public_counts import PLAN, require, utc, epoch_ns, bins, supported_plan, version_plan

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/opt/qcrl-stream/venv/bin/python'


RESOURCE_PUBLICATION_POLICY = dict(
    schema_version='qcrl.public_preclose_resources.policy.v1',
    stop='after_acquisition_checkpoint_before_final_close', join_seconds=3,
    population='completed_existing_observer_result_only_no_mutable_prefix_copy',
    alive='unavailable_no_retry_no_catch_up', max_bytes=4*1024**2,
    timing='existing_grid_reads_brackets_thresholds_unchanged_earlier_terminal_stop',
    bounds='within_existing_acquisition_publication_guard_and_spool_budget',
    close='separate_cleanup_return_not_peer_handshake',
    publication='exclusive_final_with_no_pending_file_not_visibility_alone',
    acceptance_demonstrated=False)


def resource_publication_enabled(frozen):
    """Absent on every historical freeze; presence must bind the exact new policy."""
    key='resource_publication_policy_sha256'
    if key not in frozen:return False
    require(frozen[key]==payload_hash(RESOURCE_PUBLICATION_POLICY),
            'pre-close resource publication policy differs')
    return True


def publish_preclose_resources(root,checkpoint,resources,alive):
    """One bounded component; caller owns stop/join and never reads live state."""
    from infra.stream.recorder_absolute_budget import PLAN as resource_plan
    root=Path(root)
    require(type(alive) is bool and (resources is None if alive else isinstance(resources,dict)),
            'live observer cannot publish mutable resources')
    value=dict(schema_version='qcrl.public_preclose_resources.v1',
        policy_sha256=payload_hash(RESOURCE_PUBLICATION_POLICY),
        checkpoint_sha256=checkpoint['artifact_sha256'],
        completion_sha256=file_hash(root/'completion.json'),
        case_sha256=checkpoint['case_sha256'],identity=checkpoint['identity'],
        epoch_ns=checkpoint['epoch_ns'],domain=checkpoint['domain'],
        resource_plan_sha256=payload_hash(resource_plan),
        observer_thread_alive=alive,resources=None if alive else deepcopy(resources),
        close_verified=False,resource_qualification=None,
        original_application_verdict='fail',orders_authorized=False)
    # Include final hash/newline and reject NaN/Infinity before any publication.
    encoded=json.dumps(dict(value,artifact_sha256=payload_hash(value)),sort_keys=True,allow_nan=False)+'\n'
    require(len(encoded.encode())<=RESOURCE_PUBLICATION_POLICY['max_bytes'],
            'pre-close resource component cap reached')
    return publish(root/'preclose-resources.json',value)


def verify_preclose_resources(root,case,consumer):
    """Verify component linkage, not resource qualification or peer handshake."""
    from infra.stream.recorder_absolute_budget import PLAN as resource_plan
    root=Path(root)
    path=root/'preclose-resources.json'
    pending=path.with_name(path.name+'.pending')
    require(path.is_file() and not path.is_symlink()
            and not pending.exists() and not pending.is_symlink()
            and path.stat().st_size<=RESOURCE_PUBLICATION_POLICY['max_bytes'],
            'bounded regular pre-close resource component required')
    value=control(path)
    checkpoint=control(root/'acquisition-checkpoint.json')
    policy=payload_hash(RESOURCE_PUBLICATION_POLICY)
    require(value['schema_version']=='qcrl.public_preclose_resources.v1'
            and value['policy_sha256']==checkpoint['resource_publication_policy_sha256']
                ==consumer['resource_publication_policy_sha256']==policy
            and value['checkpoint_sha256']==checkpoint['artifact_sha256']
            and value['completion_sha256']==file_hash(root/'completion.json')
            and checkpoint['schema_version']=='qcrl.public_acquisition_checkpoint.v1'
            and checkpoint['close_verified'] is False
            and checkpoint['result']['closed'] is None
            and checkpoint['result']['close_completed'] is False
            and checkpoint['result']['publication_policy_sha256']==payload_hash(PUBLICATION_POLICY)
            and checkpoint['result']['epoch_ns']==checkpoint['epoch_ns'],
            'pre-close resource publication linkage differs')
    for key,want in dict(case_sha256=case['artifact_sha256'],identity=consumer['identity'],
                         epoch_ns=consumer['epoch_ns'],domain=consumer['domain']).items():
        require(value[key]==checkpoint[key]==want,'pre-close resource '+key+' differs')
    require(value['resource_plan_sha256']==payload_hash(resource_plan)
            and value['close_verified'] is False and value['resource_qualification'] is None
            and value['original_application_verdict']=='fail' and value['orders_authorized'] is False,
            'pre-close resource contract differs')
    alive=value['observer_thread_alive']
    require(type(alive) is bool and (value['resources'] is None if alive else isinstance(value['resources'],dict)),
            'pre-close resource availability differs')
    if not alive and 'schema_version' in value['resources']:
        result=value['resources']
        require(result['schema_version']=='qcrl.recorder_absolute_resources.v1'
                and result['plan_sha256']==value['resource_plan_sha256']
                and result['epoch_ns']==value['epoch_ns'], 'resource result epoch/plan differs')
    if consumer.get('schema_version')!='qcrl.public_acquisition_checkpoint.v1':
        require('preclose_resources_sha256' in consumer,'final resource component reference missing')
    if 'preclose_resources_sha256' in consumer:
        require(consumer['result']['summary']==checkpoint['result']['summary']
                and consumer['result']['acquisition_ended']==checkpoint['result']['acquisition_ended']
                and consumer['result']['acquisition_deadline']==checkpoint['result']['acquisition_deadline'],
                'final consumer/acquisition checkpoint differs')
        require(consumer['preclose_resources_sha256']==value['artifact_sha256'],
                'final consumer/resource component differs')
    return value


def validate_case(case, *, study_plan=PLAN):
    PLAN=supported_plan(study_plan)
    verify_artifact_hash(case,'artifact_sha256','public study case')
    require(case['study_plan_sha256']==payload_hash(PLAN) and case['case']==PLAN['case'],
            'fixed public study case differs')
    raw=case['raw_bundle']
    start=int(utc(PLAN['event_start']).timestamp())
    check_market(raw,start,dict(resolution_source=SOURCE,description_sha256=payload_hash(DESCRIPTION)))
    normalized=normalize_bundle(raw)['market_contract']
    require({o['label'] for o in normalized['outcomes']}=={'Up','Down'}, 'Up/Down outcome binding required')
    require(case['spec']==stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000,
            resilient="recovery_policy_sha256" in PLAN),
            'public study transport/storage spec differs')
    require(utc(PLAN['discovery'])<=utc(case['discovered_at_utc'])
            <=utc(PLAN['discovery'])+timedelta(seconds=30),
            'single metadata discovery window differs')
    return case


def publish_acquisition_checkpoint(root,case,result,witness,identity,domain, *, resource_policy=None):
    """Existing completion sideband plus a durable acquisition result, not a close receipt."""
    root=Path(root)
    require(result['closed'] is None and result['close_completed'] is False
            and result['publication_policy_sha256']==payload_hash(PUBLICATION_POLICY),
            'pre-close publication contract differs')
    extension={} if resource_policy is None else dict(resource_publication_policy_sha256=resource_policy)
    require(not extension or resource_policy==payload_hash(RESOURCE_PUBLICATION_POLICY),
            'checkpoint resource publication policy differs')
    exclusive_json(root/'completion.json',witness.snapshot(root/'archive'))
    return publish(root/'acquisition-checkpoint.json',dict(
        schema_version='qcrl.public_acquisition_checkpoint.v1',
        case_sha256=case['artifact_sha256'],result=result,error=None,
        identity=identity,epoch_ns=result['epoch_ns'],domain=domain,
        close_verified=False,observer_thread_alive=True,
        original_application_verdict='fail',orders_authorized=False,**extension))


def consume(root, frozen, *, execute=False):
    """Linux production entry: frozen approval + actual unit binding before I/O."""
    require(execute is True and platform.system()=='Linux'
            and os.path.abspath(__import__('sys').executable)==PYTHON,
            'explicit installed Linux study worker required')
    PLAN=supported_plan(frozen['study_plan'])
    preclose_resources=resource_publication_enabled(frozen)
    require('phase_quota_policy_sha256' not in PLAN or preclose_resources,
            'BTC20 requires prospectively frozen preclose publication')
    root=Path(root)
    require(root.is_absolute() and root.resolve(strict=True)==root and not root.is_symlink(),
            'canonical private study root required')
    verify_artifact_hash(frozen,'freeze_sha256','public study freeze')
    require(frozen['study_plan']==PLAN and frozen['study_plan_sha256']==payload_hash(PLAN)
            and PLAN['stop_policy_sha256']==payload_hash(STOP_POLICY)
            and PLAN['notice_policy_sha256']==payload_hash(NOTICE_POLICY)
            and PLAN['publication_policy_sha256']==payload_hash(PUBLICATION_POLICY),
            'public study source/plan freeze differs')
    if 'recovery_policy_sha256' in PLAN:
        from infra.stream.recorder_public_recovery import policy as recovery_policy
        require(PLAN['recovery_policy_sha256']==payload_hash(recovery_policy()),'recovery plan/source differs')
    # Byte checks do not grant execution authority: the external approval receipt
    # is bound literally by the operator freeze, with independent unit release.
    for name,want in frozen['sources'].items():
        require(not (ROOT/name).is_symlink() and file_hash(ROOT/name)==want,'study source drift')
    approval=control(root.parent/'operator-approval.json')
    require(approval['artifact_sha256']==frozen['operator_approval_sha256']
            and approval['case']==PLAN['case'] and approval['one_case_only'] is True,
            'one-case operator approval unavailable')
    case=validate_case(control(root/'case.json'),study_plan=PLAN)
    require(case['freeze_sha256']==frozen['freeze_sha256'],'case/freeze binding differs')
    lock=control(root.parent/'case-lock.json')
    require(lock['case_sha256']==case['artifact_sha256'] and lock['freeze_sha256']==frozen['freeze_sha256']
            and utc(lock['locked_at_utc'])<utc(PLAN['freeze_cutoff']), 'prospective market lock unavailable')
    require(utc(PLAN['arm'])<=utc_now()<utc(PLAN['nominal_epoch']), 'fixed arm window missed')
    reader=LinuxReader(execute=True,rss_thread_cpu=False)
    require(reader.expected['boot_id']==frozen['boot_id'],'study boot changed')
    from infra.stream.recorder_public_operator import pinned_tls
    tls=pinned_tls(frozen)
    guard=StorageGuard(root,study_plan=PLAN)
    initial=reader.read(rss=True)
    before=time.monotonic();now=utc_text(utc_now());after=time.monotonic()
    epoch=epoch_ns(before,now,after,study_plan=PLAN)
    publish(root/'worker-ready.json',dict(case_sha256=case['artifact_sha256'],identity=reader.expected,
        epoch_ns=epoch,anchor=dict(before=before,utc=now,after=after),initial_resource=initial))
    while not (root/'release.json').exists() and time.monotonic()<epoch/1e9-1:
        time.sleep(.01)
    release=control(root/'release.json')
    require(release['case_sha256']==case['artifact_sha256'] and release['identity']==reader.expected
            and release['epoch_ns']==epoch and release['at']<epoch/1e9-1,
            'independent unit binding release missed')
    domain='public-study.'+reader.expected['boot_id']
    witness=CompletionWitnesses(case['spec'],domain,clock=utc_now,monotonic=time.monotonic,execute=True)
    stop=threading.Event();resources={}
    def monitor():
        try:
            resources.update(observe_absolute(reader,epoch/1e9,stop,execute=True,epoch_ns=epoch))
        except BaseException as exc:
            resources.update(error=short_error(exc))
    thread=threading.Thread(target=monitor,daemon=True)
    thread.start()
    result,error=None,None
    resource_component=None
    observer_stop_requested=False
    def checkpoint(value):
        nonlocal resource_component,observer_stop_requested
        checkpoint=publish_acquisition_checkpoint(root,case,value,witness,reader.expected,domain,
            resource_policy=payload_hash(RESOURCE_PUBLICATION_POLICY) if preclose_resources else None)
        if preclose_resources:
            stop.set();observer_stop_requested=True
            thread.join(timeout=RESOURCE_PUBLICATION_POLICY['join_seconds'])
            alive=thread.is_alive()
            guard.check()
            resource_component=publish_preclose_resources(root,checkpoint,None if alive else resources,alive)
            guard.check()
    try:
        result=collect(case['raw_bundle'],case['spec'],root/'archive',epoch_ns=epoch,
            observer=witness,execute=True,guard=guard,tls_context=tls,before_close=checkpoint,
            **({'recovery_policy':recovery_policy()} if 'recovery_policy_sha256' in PLAN else {}),
            **({'study_plan':PLAN} if 'phase_quota_policy_sha256' in PLAN else {}))
    except BaseException as exc:
        error=short_error(exc)
    finally:
        if not observer_stop_requested:
            stop.set();thread.join(timeout=3)
        try:
            if not witness.closed:
                exclusive_json(root/'completion.json',witness.snapshot(root/'archive'))
            elif not (root/'completion.json').is_file():
                raise ContractError('single-use completion snapshot was not published')
        except BaseException as exc:
            publish(root/'completion-error.json',dict(error=short_error(exc)))
        try:
            final_resource=reader.read(rss=True)
        except BaseException as exc:
            final_resource=dict(error=short_error(exc))
        extension={}
        if preclose_resources:
            extension=dict(resource_publication_policy_sha256=payload_hash(RESOURCE_PUBLICATION_POLICY),
                preclose_resources_sha256=None if resource_component is None else resource_component['artifact_sha256'])
        final_alive=thread.is_alive()
        publish(root/'consumer.json',dict(case_sha256=case['artifact_sha256'],result=result,error=error,
            identity=reader.expected,epoch_ns=epoch,domain=domain,
            resources=({} if preclose_resources and final_alive else resources),
            final_resource=final_resource,observer_thread_alive=final_alive,
            original_application_verdict='fail',orders_authorized=False,**extension))


def report(root, *, study_plan=PLAN):
    """Independent linkage prerequisite; no overall pass/acceptance output."""
    PLAN=supported_plan(study_plan)
    consumer=None
    def decorate(value):
        if (root/'preclose-resources.json').exists() or (consumer is not None and
                'resource_publication_policy_sha256' in consumer):
            try:
                require(value.get('archive_linkage',{}).get('completion_linkage_verified') is True,
                        'resource component requires independently linked acquisition')
                value['preclose_resource_component']=verify_preclose_resources(root,case,consumer)
            except (ContractError,OSError,ValueError,KeyError,TypeError) as exc:
                value['preclose_resource_component']=dict(error=short_error(exc),resource_qualification=None)
        if 'recovery_policy_sha256' in PLAN:
            value.update(study_plan_sha256=payload_hash(PLAN))
            value.setdefault('eligible_population',None)
            value.setdefault('normal_acquisition_end_proven',None)
            value.setdefault('full_minute_feed_population',None)
            value.setdefault('coverage_complete',False)
            for row in value['rows']:
                for key in ('eligible_lower','eligible_upper_archived'):row.setdefault(key,None)
                for key in ('acquisition','book_eligibility'):row.setdefault(key,'unresolved_linkage')
                row.setdefault('silence','unknown')
        if 'phase_quota_policy_sha256' in PLAN:
            value.update(original_60_second_cpu_window=None,original_60_second_cpu_window_status='unavailable_short_primary_no_prorating')
            if consumer is not None:
                value['received_occurrence_disclosure']=consumer.get('result',{}).get('phase_allocations')
                if value.get('archive_linkage',{}).get('completion_linkage_verified'):
                    try:
                        from infra.stream.recorder_phase_quotas import verify_archive_allocations
                        value['verified_phase_allocations']=verify_archive_allocations(result,completion,root/'archive')
                    except (ContractError,OSError,ValueError,KeyError,TypeError) as exc:
                        value['allocation_linkage_error']=short_error(exc)
                        value['eligible_population']=None
                        for row in value['rows']:
                            row.update(eligible_lower=None,eligible_upper_archived=None,
                                book_eligibility='unresolved_allocation',silence='unknown')
        return value
    root=Path(root)
    case=validate_case(control(root/'case.json'),study_plan=PLAN)
    final_path=root/'consumer.json'
    final_consumer=final_path.exists() or final_path.is_symlink()
    try:
        path=final_path if final_consumer else root/'acquisition-checkpoint.json'
        require(path.is_file() and not path.is_symlink(),'regular final consumer or checkpoint required')
        consumer=control(path)
        if not final_consumer:
            require(consumer['schema_version']=='qcrl.public_acquisition_checkpoint.v1'
                and consumer['close_verified'] is False and consumer['observer_thread_alive'] is True
                and consumer['result']['closed'] is None and consumer['result']['close_completed'] is False
                and consumer['result']['publication_policy_sha256']==payload_hash(PUBLICATION_POLICY),
                'unsupported pre-close checkpoint')
        require(consumer['case_sha256']==case['artifact_sha256'],'consumer/case differs')
        result=consumer['result']
        require(isinstance(result,dict) and result['epoch_ns']==consumer['epoch_ns'],
                'public result/epoch unavailable')
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        # A connection watchdog can terminate the worker before final controls.
        # Do not infer an empty archive or a clock anchor from that absence.
        value=dict(schema_version='qcrl.public_feed_interval_counts.description.v1',
            case=PLAN['case'],original_application_verdict='fail',population=None,
            archive_linkage=dict(error=short_error(exc)),epoch_ns=None,
            origin_attestation_required=True,venue_completeness_proven=False,
            orders_authorized=False,rows=[dict(slot=k,coverage='unresolved_consumer',
                lower=None,upper_archived=None,feed_activity_upper=None) for k in range(PLAN['seconds'])])
        return decorate(value)
    try:
        archive=verify_stream_log(root/'archive')
        require(archive['header_spec']==case['spec'] and 0<=archive['frames']<=60000,
                'public archive spec/population differs')
        require(archive['terminal_summary'] is None or archive['terminal_summary']==result['summary'],
                'public consumer/archive footer differs')
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        value=bins([],consumer['epoch_ns'],study_plan=PLAN)
        value.update(population=None,archive_linkage=dict(error=short_error(exc)),
                     case=PLAN['case'],origin_attestation_required=True)
        for row in value['rows']:
            row.update(coverage='unresolved_archive',lower=None,upper_linked=None,upper_archived=None,possible_unplaced=None)
        return decorate(value)
    try:
        completion_path=root/'completion.json'
        require(not completion_path.is_symlink() and completion_path.stat().st_size<=32*1024**2,
                'bounded regular completion artifact required')
        completion=json.loads(completion_path.read_bytes())
        verified=verify_completion(completion,root/'archive',expected_domain=consumer['domain'])
        require(completion['runtime']['pid']==consumer['identity']['pid']
                and completion['spec_sha256']==payload_hash(case['spec']),
                'public completion runtime/spec differs')
        require(result['summary']['frames']==verified['frames'],'public population differs')
        if 'recovery_policy_sha256' in PLAN:
            require(result['recovery_policy_sha256']==PLAN['recovery_policy_sha256'],'result recovery policy differs')
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        value=bins([dict(sequence=i) for i in range(archive['frames'])],consumer['epoch_ns'],study_plan=PLAN)
        value.update(case=PLAN['case'],archive_linkage=dict(error=short_error(exc)),
                     capture_result=result,origin_attestation_required=True)
        return decorate(value)
    if 'recovery_policy_sha256' in PLAN:
        from infra.stream.recorder_public_recovery import describe_archive
        try:
            value=describe_archive(result,completion,root/'archive',expected_domain=consumer['domain'],
                **({'study_plan':PLAN} if 'phase_quota_policy_sha256' in PLAN else {}))
        except (ContractError,OSError,ValueError,KeyError,TypeError,IndexError) as exc:
            # Keep verified raw occurrence counts while withholding lifecycle eligibility.
            value=bins(completion['frames'],consumer['epoch_ns'],study_plan=PLAN)
            value.update(recovery_linkage=dict(error=short_error(exc)),eligible_population=None,
                connection_epochs=None,coverage_complete=False)
            for row in value['rows']:
                row.update(eligible_lower=None,eligible_upper_archived=None,
                    acquisition='unresolved_lifecycle',book_eligibility='unresolved_lifecycle',silence='unknown')
        value.update(case=PLAN['case'],study_plan_sha256=payload_hash(PLAN),
            plan_sha256=payload_hash(PLAN),archive_linkage=verified,capture_result=result,
            final_consumer_present=final_consumer,close_verified=final_consumer and result.get('close_completed') is True,
            origin_attestation_required=True,original_application_budget_pass=False)
        return decorate(value)
    # Full primary local coverage requires normal scheduled end plus observed
    # subscription before the original epoch and all receipts. This is not feed
    # completeness and is never used as an aggregate application badge.
    complete=(final_consumer and result.get('close_completed') is True
        and normal_completion_proven(result)
        and result['summary']['status']=='scheduled_stop' and result['error'] is None
        and not result['close_errors'] and consumer['error'] is None
        and consumer['observer_thread_alive'] is False
        and result['ready']<consumer['epoch_ns']/1e9-1
        and result['acquisition_ended']>=consumer['epoch_ns']/1e9+65
        and result['acquisition_deadline']>=consumer['epoch_ns']/1e9+65
        and archive['connection_gaps']==0 and archive['manifest_present']
        and archive['session_end_present'] and result['summary']['connections']==1)
    censor=None if complete else result['last_safe']
    value=bins(completion['frames'],consumer['epoch_ns'],censored_from=censor,
               coverage_complete=complete,study_plan=PLAN)
    value.update(case=PLAN['case'],archive_linkage=verified,
                 final_consumer_present=final_consumer,close_verified=final_consumer and result.get('close_completed') is True,
                 capture_result=result,origin_attestation_required=True,
                 original_application_budget_pass=False)
    return decorate(value)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['consume','report'])
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--study-version',choices=['v5','v6','v7'],default='v5')
    args=parser.parse_args()
    if args.action=='consume':
        frozen=load(args.root.parent/'execution-freeze.json')
        require(frozen['study_plan']==version_plan(args.study_version),'worker CLI study version differs')
        consume(args.root,frozen,execute=args.execute)
    else:
        require(not args.execute,'offline report does not acquire data')
        publish(args.root/'description.json',report(args.root,study_plan=version_plan(args.study_version)))


if __name__=='__main__':main()
