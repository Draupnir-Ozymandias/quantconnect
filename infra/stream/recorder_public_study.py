"""Fixed one-case public-study worker and independent descriptive report.

There is no discovery or launcher fallback in this module. A separately frozen
operator packet must supply the one discovered case and independent release.
"""
import argparse
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
from infra.stream.recorder_public_capture import collect, short_error, StorageGuard
from infra.stream.recorder_public_counts import PLAN, require, utc, epoch_ns, bins

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/opt/qcrl-stream/venv/bin/python'


def validate_case(case):
    verify_artifact_hash(case,'artifact_sha256','public study case')
    require(case['study_plan_sha256']==payload_hash(PLAN) and case['case']==PLAN['case'],
            'fixed public study case differs')
    raw=case['raw_bundle']
    start=int(utc(PLAN['event_start']).timestamp())
    check_market(raw,start,dict(resolution_source=SOURCE,description_sha256=payload_hash(DESCRIPTION)))
    normalized=normalize_bundle(raw)['market_contract']
    require({o['label'] for o in normalized['outcomes']}=={'Up','Down'}, 'Up/Down outcome binding required')
    require(case['spec']==stream_plan(raw,segmented=True,max_seconds=90,max_frames=60000),
            'public study transport/storage spec differs')
    require(utc(PLAN['discovery'])<=utc(case['discovered_at_utc'])
            <=utc(PLAN['discovery'])+timedelta(seconds=30),
            'single metadata discovery window differs')
    return case


def consume(root, frozen, *, execute=False):
    """Linux production entry: frozen approval + actual unit binding before I/O."""
    require(execute is True and platform.system()=='Linux'
            and os.path.abspath(__import__('sys').executable)==PYTHON,
            'explicit installed Linux study worker required')
    root=Path(root)
    require(root.is_absolute() and root.resolve(strict=True)==root and not root.is_symlink(),
            'canonical private study root required')
    verify_artifact_hash(frozen,'freeze_sha256','public study freeze')
    require(frozen['study_plan']==PLAN and frozen['study_plan_sha256']==payload_hash(PLAN),
            'public study source/plan freeze differs')
    # Byte checks do not grant execution authority: the external approval receipt
    # is bound literally by the operator freeze, with independent unit release.
    for name,want in frozen['sources'].items():
        require(not (ROOT/name).is_symlink() and file_hash(ROOT/name)==want,'study source drift')
    approval=control(root.parent/'operator-approval.json')
    require(approval['artifact_sha256']==frozen['operator_approval_sha256']
            and approval['case']==PLAN['case'] and approval['one_case_only'] is True,
            'one-case operator approval unavailable')
    case=validate_case(control(root/'case.json'))
    require(case['freeze_sha256']==frozen['freeze_sha256'],'case/freeze binding differs')
    lock=control(root.parent/'case-lock.json')
    require(lock['case_sha256']==case['artifact_sha256'] and lock['freeze_sha256']==frozen['freeze_sha256']
            and utc(lock['locked_at_utc'])<utc(PLAN['freeze_cutoff']), 'prospective market lock unavailable')
    require(utc(PLAN['arm'])<=utc_now()<utc(PLAN['nominal_epoch']), 'fixed arm window missed')
    reader=LinuxReader(execute=True,rss_thread_cpu=False)
    require(reader.expected['boot_id']==frozen['boot_id'],'study boot changed')
    from infra.stream.recorder_public_operator import pinned_tls
    tls=pinned_tls(frozen)
    guard=StorageGuard(root)
    initial=reader.read(rss=True)
    before=time.monotonic();now=utc_text(utc_now());after=time.monotonic()
    epoch=epoch_ns(before,now,after)
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
            resources.update(observe_absolute(reader,epoch/1e9,stop,execute=True))
        except BaseException as exc:
            resources.update(error=short_error(exc))
    thread=threading.Thread(target=monitor,daemon=True)
    thread.start()
    result,error=None,None
    try:
        result=collect(case['raw_bundle'],case['spec'],root/'archive',epoch_ns=epoch,
            observer=witness,execute=True,guard=guard,tls_context=tls)
    except BaseException as exc:
        error=short_error(exc)
    finally:
        stop.set();thread.join(timeout=3)
        try:
            exclusive_json(root/'completion.json',witness.snapshot(root/'archive'))
        except BaseException as exc:
            publish(root/'completion-error.json',dict(error=short_error(exc)))
        try:
            final_resource=reader.read(rss=True)
        except BaseException as exc:
            final_resource=dict(error=short_error(exc))
        publish(root/'consumer.json',dict(case_sha256=case['artifact_sha256'],result=result,error=error,
            identity=reader.expected,epoch_ns=epoch,domain=domain,resources=resources,
            final_resource=final_resource,observer_thread_alive=thread.is_alive(),
            original_application_verdict='fail',orders_authorized=False))


def report(root):
    """Independent linkage prerequisite; no overall pass/acceptance output."""
    root=Path(root)
    case=validate_case(control(root/'case.json'))
    try:
        consumer=control(root/'consumer.json')
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
                lower=None,upper_archived=None,feed_activity_upper=None) for k in range(60)])
        return value
    try:
        archive=verify_stream_log(root/'archive')
        require(archive['header_spec']==case['spec'] and 0<=archive['frames']<=60000,
                'public archive spec/population differs')
        require(archive['terminal_summary'] is None or archive['terminal_summary']==result['summary'],
                'public consumer/archive footer differs')
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        value=bins([],consumer['epoch_ns'])
        value.update(population=None,archive_linkage=dict(error=short_error(exc)),
                     case=PLAN['case'],origin_attestation_required=True)
        for row in value['rows']:
            row.update(coverage='unresolved_archive',upper_archived=None,possible_unplaced=None)
        return value
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
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        value=bins([dict(sequence=i) for i in range(archive['frames'])],consumer['epoch_ns'])
        value.update(case=PLAN['case'],archive_linkage=dict(error=short_error(exc)),
                     capture_result=result,origin_attestation_required=True)
        return value
    # Full primary local coverage requires normal scheduled end plus observed
    # subscription before the original epoch and all receipts. This is not feed
    # completeness and is never used as an aggregate application badge.
    complete=(result['summary']['status']=='scheduled_stop' and result['error'] is None
        and not result['close_errors'] and consumer['error'] is None
        and consumer['observer_thread_alive'] is False
        and result['ready']<consumer['epoch_ns']/1e9-1
        and result['acquisition_ended']>=consumer['epoch_ns']/1e9+65
        and result['acquisition_deadline']>=consumer['epoch_ns']/1e9+65
        and archive['connection_gaps']==0 and archive['manifest_present']
        and archive['session_end_present'] and result['summary']['connections']==1)
    censor=None if complete else result['last_safe']
    value=bins(completion['frames'],consumer['epoch_ns'],censored_from=censor,
               coverage_complete=complete)
    value.update(case=PLAN['case'],archive_linkage=verified,
                 capture_result=result,origin_attestation_required=True,
                 original_application_budget_pass=False)
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['consume','report'])
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.action=='consume':
        consume(args.root,load(args.root.parent/'execution-freeze.json'),execute=args.execute)
    else:
        require(not args.execute,'offline report does not acquire data')
        publish(args.root/'description.json',report(args.root))


if __name__=='__main__':main()
