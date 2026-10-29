"""Prospective bounded recovery contract; no launcher or retrospective repair."""
from copy import deepcopy
import json

from execution_truth.contracts import ContractError, payload_hash, _levels
from execution_truth.stream_resilience import POLICY as WATCHDOG_POLICY, DataWatchdog, retry_delay
from execution_truth.stream_freshness import epoch, milliseconds
from infra.stream.recorder_public_counts import bins, number, require

POLICY = dict(schema_version='qcrl.public_acquisition_recovery.v1',
    max_connections=3, max_retries=2, watchdog=deepcopy(WATCHDOG_POLICY),
    fresh_books='new_valid_full_snapshot_each_selected_asset_per_connection',
    nominal_book_age_seconds=5, bootstrap_frame_eligible=False,
    count_population='all_incoming_text_occurrences_no_dedup_or_batch_expansion',
    eligible_population='whole_return_interval_inside_fresh_book_connection_window',
    gap_start='last_return_before_or_subscription_or_attempt',
    recovery_does_not_recover_missed_messages=True,
    acquisition_hard_seconds=90, frame_cap=60000, close_hard_seconds=5,
    original_thresholds_unchanged=True, orders_authorized=False)


def policy():
    return deepcopy(POLICY)


class Epochs:
    def __init__(self, spec):
        self.spec, self.rows, self.current, self.watchdog = spec, [], None, None

    def begin(self, at):
        require(len(self.rows)<POLICY['max_connections'], 'connection budget exhausted')
        number(at)
        self.current=dict(connection=len(self.rows)+1,attempted=at,subscribed=None,
            eligible_after=None,books={},last_return_before=None,ended=None,
            available_until=None,error=None,normal=False)
        self.rows.append(self.current)
        return self.current['connection']

    def subscribe(self, at):
        self.current['subscribed']=at
        self.watchdog=DataWatchdog(self.spec['asset_ids'],at)

    def reason(self, now):
        if self.current['eligible_after'] is None and now-self.current['subscribed']>=WATCHDOG_POLICY['initial_books_seconds']:
            return 'initial_books_timeout'
        return self.watchdog.reason(now,True)

    def observe(self, raw, classes, returned):
        # Uses existing delivery clocks only, after the unchanged return bracket.
        self.current['last_return_before']=returned['before']
        self.watchdog.observe(raw,classes,returned['after'],epoch(returned['utc']))
        try:obj=json.loads(raw)
        except ValueError:return
        events=obj if isinstance(obj,list) else [obj]
        for event,cls in zip(events,classes):
            if not isinstance(event,dict) or cls['scope']!='selected_market' or cls['event_type']!='book':continue
            asset=event.get('asset_id')
            if asset not in self.spec['asset_ids']:continue
            try:
                _levels(event,'bids');_levels(event,'asks')
                age=epoch(returned['utc'])-milliseconds(event.get('timestamp'))
                if not 0<=age<=POLICY['nominal_book_age_seconds']:continue
            except (ContractError,ValueError,TypeError):continue
            self.current['books'][asset]=dict(before=returned['before'],after=returned['after'])
        books=self.current['books']
        # Both book receipts must still be nominally fresh at bootstrap completion.
        if (self.current['eligible_after'] is None and set(books)==set(self.spec['asset_ids'])
                and all(returned['after']-v['after']<=5 for v in books.values())):
            self.current['eligible_after']=returned['after']

    def end(self, at, error, *, normal=False):
        row=self.current
        row['ended'],row['error'],row['normal']=at,error,normal
        row['available_until']=(at if normal else row['last_return_before']
            if row['last_return_before'] is not None else row['subscribed']
            if row['subscribed'] is not None else row['attempted'])
        return deepcopy(row)


def describe(result, completion, *, study_plan=None):
    """Caller verifies archive witnesses and final lifecycle marker before use.

    Raw counts remain complete. Eligibility is a separate descriptive population;
    no feed upper bound or venue continuity is inferred, including zero-text bins.
    """
    require(result['recovery_policy_sha256']==payload_hash(POLICY),'recovery policy differs')
    epochs=result['connection_epochs'];frames=completion['frames']
    require(isinstance(epochs,list) and 1<=len(epochs)<=3,'bounded connection epochs required')
    previous=0
    for i,row in enumerate(epochs,1):
        require(type(row['connection']) is int and row['connection']==i,'ordered connection epochs required')
        start,end=number(row['attempted']),number(row['ended'])
        require(previous<=start<=end,'epoch chronology differs');previous=end
        require(type(row['normal']) is bool and (row['error'] is None or
            isinstance(row['error'],str) and len(row['error'])<=160),'epoch disposition differs')
        eligible=row['eligible_after']
        require(start<=number(row['available_until'])<=end,'epoch availability differs')
        if row['subscribed'] is not None:require(start<=number(row['subscribed'])<=end,'subscription chronology differs')
        if eligible is not None:
            require(row['subscribed'] is not None and number(row['subscribed'])<=number(eligible)<=end,'bootstrap chronology differs')
    require(len(frames)==result['summary']['frames'],'recovery occurrence population differs')
    eligible_frames=[]
    for i,f in enumerate(frames):
        require(type(f['connection']) is int and 1<=f['connection']<=len(epochs),'frame epoch differs')
        row=epochs[f['connection']-1];a,b=number(f['returned']['before']),number(f['returned']['after'])
        require(number(row['attempted'])<=a<=b<=number(row['ended']),'frame outside epoch')
        if (row['eligible_after'] is not None and a>number(row['eligible_after'])
                and b<number(row['available_until'])):
            eligible_frames.append(dict(f,sequence=len(eligible_frames)))
    value=bins(frames,result['epoch_ns'],**({'study_plan':study_plan} if study_plan is not None else {}))
    # This is a method contract, not authorization to reuse the expired v5 target.
    value['counting_method_reference_plan_sha256']=value.pop('plan_sha256')
    value['study_plan_sha256']=None
    sub=bins(eligible_frames,result['epoch_ns'],**({'study_plan':study_plan} if study_plan is not None else {}))
    origin=number(result['epoch_ns'])/10**9
    for raw,good in zip(value['rows'],sub['rows']):
        a,b=origin+raw['slot'],origin+raw['slot']+1
        connected=any(e['subscribed'] is not None and number(e['subscribed'])<a
            and b<number(e['available_until']) for e in epochs)
        eligible=any(e['eligible_after'] is not None and number(e['eligible_after'])<a
            and b<number(e['available_until']) for e in epochs)
        raw.update(eligible_lower=good['lower'],eligible_upper_archived=good['upper_archived'],
            acquisition=('observed_local_interval' if connected else 'unavailable_or_boundary'),
            book_eligibility=('eligible_local_interval' if eligible else 'unavailable_or_bootstrap'),
            silence=('observed_zero_archived_texts' if connected and raw['upper_archived']==0
                     else 'texts_observed' if raw['lower'] else 'unknown'))
    horizon=number(result['acquisition_deadline'])
    def windows(key):
        return [dict(connection=e['connection'],start=e[key],end=e['available_until'])
                for e in epochs if e[key] is not None and number(e[key])<number(e['available_until'])]
    def gaps(wins):
        cursor=number(result['attempted']);out=[]
        for window in wins:
            start,end=number(window['start']),min(horizon,number(window['end']))
            if start>cursor:out.append(dict(start=float(cursor),end=float(min(start,horizon))))
            cursor=max(cursor,end)
            if cursor>=horizon:break
        if cursor<horizon:out.append(dict(start=float(cursor),end=float(horizon)))
        return out
    raw_windows,eligible_windows=windows('subscribed'),windows('eligible_after')
    value.update(acquisition_windows=raw_windows,book_eligible_windows=eligible_windows,
        unavailable_intervals=gaps(raw_windows),book_ineligible_intervals=gaps(eligible_windows))
    from infra.stream.recorder_public_capture import STOP_POLICY
    receipts=result['deadline_interrupts']
    last=receipts[-1] if receipts else {}
    normal_end=(epochs[-1]['normal'] and last.get('phase')=='acquisition'
        and last.get('owner')=='acquisition_thread' and last.get('fired') is False
        and last.get('error') is None and last.get('completed_at')==epochs[-1]['ended']
        and last.get('normal_deadline')==result['acquisition_deadline']
        and result['stop_policy_sha256']==payload_hash(STOP_POLICY)
        and number(last['normal_deadline'])<=number(last['completed_at'])<number(last['emergency_deadline'])
        and all(x['fired'] is False and x['error'] is None for x in receipts))
    require(not epochs[-1]['normal'] or normal_end,'normal epoch ownership differs')
    value.update(normal_acquisition_end_proven=bool(normal_end),
        cleanup_close_completed=result['close_completed'],prior_faults_preserved=result['terminal_receive'])
    value.update(schema_version='qcrl.public_recovery_description.v1',
        recovery_policy_sha256=payload_hash(POLICY),connection_epochs=deepcopy(epochs),
        eligible_population=len(eligible_frames),coverage_complete=False,
        missed_messages_recovered=False,full_minute_feed_population=None)
    return value


def describe_archive(result, completion, root, *, expected_domain, study_plan=None):
    """Reuse completion/archive verification, then bind lifecycle and replay books.

    No public transport or consumer creation occurs. A caller must separately bind
    the final consumer/checkpoint to its approved case, runtime and clock domain.
    """
    import gzip
    from pathlib import Path
    from infra.stream.recorder_completion import verify_completion
    verified=verify_completion(completion,root,expected_domain=expected_domain)
    root=Path(root);replay=None;ended=[];final=None;sequence=0;footer=None
    for descriptor in sorted(root.glob('segment-*.json')):
        name=json.loads(descriptor.read_bytes())['file']
        with gzip.open(root/name,'rt') as h:
            for line in h:
                row=json.loads(line);kind=row['kind'];value=row['payload']
                if kind=='session_start':
                    require(value['recovery_policy_sha256']==payload_hash(POLICY),'archive recovery policy differs')
                    replay=Epochs(value['spec'])
                elif kind=='connect_attempt':
                    # The exact attempted instant is retained in the linked epoch marker.
                    i=value['connection']
                    require(type(i) is int and i==len(replay.rows)+1 and i<=len(result['connection_epochs']), 'attempt linkage differs')
                    replay.begin(result['connection_epochs'][i-1]['attempted'])
                elif kind=='subscribed':
                    require(value['connection']==replay.current['connection'],'subscription epoch differs')
                    replay.subscribe(result['connection_epochs'][value['connection']-1]['subscribed'])
                elif kind=='frame':
                    f=completion['frames'][sequence];sequence+=1
                    require(value['connection']==replay.current['connection'],'raw frame epoch differs')
                    replay.observe(value['raw_text'],value['classification'],f['returned'])
                elif kind=='connection_epoch':
                    actual=replay.end(value['ended'],value['error'],normal=value['normal'])
                    require(actual==value,'replayed book/epoch differs');ended.append(actual)
                elif kind=='recovery_end':
                    require(final is None and value['policy_sha256']==payload_hash(POLICY),'recovery end differs')
                    final=value['epochs']
                elif kind=='session_end':footer=value
    require(final==result['connection_epochs'] and ended==final,'result/archive lifecycle differs')
    require(footer==result['summary'] and sequence==verified['frames'],'recovery footer/population differs')
    value=describe(result,completion,study_plan=study_plan)
    value.update(archive_linkage=verified,origin_attestation_required=True)
    return value
