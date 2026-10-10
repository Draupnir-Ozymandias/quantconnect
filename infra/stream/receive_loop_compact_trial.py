"""Private fixed localhost workers and offline audit; no cohort/deployment launcher."""
import argparse
from bisect import bisect_left
from contextlib import contextmanager
from datetime import timedelta
import json
import math
from pathlib import Path
import time
from unittest.mock import patch

from execution_truth import market_stream
from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.receive_adapter import ObservedSocket
from execution_truth.stream_receive_analysis import _sealed_rows
from execution_truth.stream_segments import file_hash
from infra.stream import burst_reader_comparison as burst, marker_cap_pair as cap
from infra.stream import receive_loop_compact_overhead as plan, receive_loop_compact_lane as lane
from infra.stream.single_pass_encoder import SinglePassStreamLog, encode_row

IMPLEMENTATION_FILES = ('infra/stream/receive_loop_compact_trial.py',
                        'tests/test_receive_loop_compact_trial.py', 'docs/RECEIVE_LOOP_COMPACT_WORKERS.md',
                        'infra/stream/receive_loop_compact_launch.py', 'tests/test_receive_loop_compact_launch.py',
                        'docs/RECEIVE_LOOP_COMPACT_LAUNCHER.md', 'infra/stream/receive_loop_compact_audit.py',
                        'tests/test_receive_loop_compact_audit.py', 'docs/RECEIVE_LOOP_COMPACT_AUDIT.md')

def signed(path, obj, field):
    return burst.signed(Path(path), obj, field)


def stage(root, declaration, corpus):
    """Create new private evidence root; original preregistration remains unchanged."""
    plan.validate(declaration, corpus)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    burst.persist(root/'corpus.json', burst.load_corpus(corpus))
    burst.persist(root/'preregistration.json', declaration)
    repo = Path(__file__).resolve().parents[2]
    return signed(root/'implementation.json', {
        'schema_version': 'qcrl.receive_loop_compact_trial_implementation.v1',
        'preregistration_sha256': declaration['plan_sha256'],
        'sources': {name: file_hash(repo/name) for name in IMPLEMENTATION_FILES},
        'cohort_launcher_implemented': True, 'public_rollout_authorized': False,
        'orders_authorized': False}, 'implementation_sha256')


def context(root, mode='recorder', receive_policy='v3'):
    if mode != 'recorder' or receive_policy != 'v3': raise ContractError('fixed recorder/v3 only')
    root = Path(root)
    declaration = burst.read(root/'preregistration.json', 'plan_sha256')
    plan.validate(declaration, root/'corpus.json')
    implementation = burst.read(root/'implementation.json', 'implementation_sha256')
    repo = Path(__file__).resolve().parents[2]
    expected = {'schema_version': 'qcrl.receive_loop_compact_trial_implementation.v1',
        'preregistration_sha256': declaration['plan_sha256'],
        'sources': {name: file_hash(repo/name) for name in IMPLEMENTATION_FILES},
        'cohort_launcher_implemented': True, 'public_rollout_authorized': False,
        'orders_authorized': False}
    if {k:v for k,v in implementation.items() if k!='implementation_sha256'} != expected:
        raise ContractError('trial implementation source/policy differs')
    corpus = burst.load_corpus(root/'corpus.json')
    # Called inside diagnostic cap scope; identical spec for both lanes.
    spec = market_stream.stream_plan(corpus['bundle'], segmented=True, profiling=True,
        resilient=True, receive_path=True, freshness_telemetry=True, receive_policy='v3',
        source_plan_sha256=implementation['implementation_sha256'], max_seconds=90,
        max_frames=len(burst.offsets()))
    return dict(declaration, plan_sha256=implementation['implementation_sha256']), corpus, spec


@contextmanager
def scope():
    with cap.scope('cap128'), patch.object(burst, 'context', context), patch.object(
            market_stream, 'SegmentedStreamLog', SinglePassStreamLog):
        yield


def case_path(root, pair, selected):
    if type(pair) is not int or pair not in (0,1,2) or selected not in ('baseline','instrumented'):
        raise ContractError('only six fixed pair/lane workers allowed')
    return Path(root)/str(pair)/selected


def produce(root, pair, selected):
    case = case_path(root,pair,selected)
    with scope():
        context(root)
        case.mkdir(parents=True, exist_ok=False)
        return burst.produce(root,case,'recorder','v3')


def consume(root, pair, selected, *, require_isolation=True):
    case = case_path(root,pair,selected)
    # Refuse replay even after a failure; keep an exclusive claim artifact.
    with (case/'consumer-claim.json').open('x') as handle:
        json.dump({'identity':burst.identity(),'lane':selected,'pair':pair},handle)
    with scope():
        declaration,corpus,spec = context(root)
        ready = burst.read(case/'ready.json','ready_sha256')
        burst.localhost_uri(ready['uri'])  # baseline adapter alone permits public; never pass it an unchecked URI.
        if (ready['plan_sha256']!=declaration['plan_sha256'] or ready['mode']!='recorder'
                or ready['receive_policy']!='v3'):
            raise ContractError('ready source/mode differs')
        identity = burst.identity()
        if identity['pid']==ready['producer_identity']['pid'] or identity['boot_id']!=ready['producer_identity']['boot_id']:
            raise ContractError('separate processes on same boot required')
        if require_isolation and (identity['boot_id'] is None or identity['cgroup'] is None
                or ready['producer_identity']['cgroup'] is None
                or identity['cgroup']==ready['producer_identity']['cgroup']):
            raise ContractError('Linux workers require distinct cgroups on a known boot')
        base = _time(ready['fixture_base_utc'])
        def clock(): return base+timedelta(seconds=time.monotonic()-ready['origin_monotonic'])
        clients=[]; raws=[]; records=[]; stamps=[]
        def connector(tracker,number,**kwargs):
            if selected=='baseline': client=ObservedSocket(ready['uri'],tracker,number,**kwargs)
            else: client=lane.CompactDiagnosticSocket(ready['uri'],tracker,number,
                                              loop_contract=declaration['loop_contract'],**kwargs)
            clients.append(client)
            wire = lane.RecorderTransport(client)
            class Traced:
                reset=client.reset
                def send(self,message): return wire.send(message)
                def recv(self,timeout):
                    raw,record=wire.recv(timeout)
                    raws.append(raw); records.append(record); stamps.append(record.get('application_delivery'))
                    return raw,record
                def close(self): return client.close()
            return Traced()
        burst.persist(case/('market-'+str(spec['market_id'])+'.json'),corpus['bundle'])
        failure=None; summary={'status':'worker_failed'}
        begin=time.monotonic(); cpu_start=time.process_time()
        try:
            summary=market_stream.collect_market_stream(corpus['bundle'],spec,case/'stream',
                connector=connector,clock=clock,monotonic=time.monotonic,clock_domain='localhost.burst')
        except BaseException as exc:
            failure=exc
        finally:
            for client in clients:
                try:
                    client.close()
                except Exception as exc:
                    if failure is None: failure=exc
                try:
                    client.connection.recv_events_thread.join(5)
                    if client.connection.recv_events_thread.is_alive(): raise ContractError('receiver did not finish')
                except Exception as exc:
                    if failure is None: failure=exc
        cpu_seconds=time.process_time()-cpu_start; end=time.monotonic()
        # No audits or sideband snapshot in the timed window.
        delivery=signed(case/'deliveries.json', {'consumer_identity':identity,'raws':raws,'stamps':stamps,
            'receive_records':records,'bare_queue_samples':[], 'timed_cpu_seconds':cpu_seconds,
            'recorder_summary':summary},'delivery_sha256')
        bands=[]
        if selected=='instrumented':
            try:
                bands=[{'connection':client.number,'sideband':client.observer.snapshot()} for client in clients]
            except Exception as exc:
                if failure is None: failure=exc
        signed(case/'measurement.json', {'schema_version':'qcrl.receive_loop_compact_trial_measurement.v1',
            'plan_sha256':declaration['plan_sha256'],'pair':pair,'lane':selected,
            'begin_monotonic':begin,'end_monotonic':end,'consumer_identity':identity,
            'delivery_sha256':delivery['delivery_sha256'],'stream_spec_sha256':payload_hash(spec),
            'connections':bands,'post_window_cpu_seconds':time.process_time()-cpu_start-cpu_seconds,
            'post_window_finished_monotonic':time.monotonic(),
            'benchmark_performed':True,'public_rollout_authorized':False,'orders_authorized':False},
            'measurement_sha256')
        if failure is not None:
            signed(case/'failure.json',{'error_type':type(failure).__name__,
                'raw_deliveries_retained':len(raws),'replay_authorized':False},'failure_sha256')
            raise ContractError('private worker failed; partial artifacts retained') from failure


def finite(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:
        raise ContractError('invalid finite nonnegative metric')
    return value


def verify_case(root,pair,selected,require_isolation=True):
    """Offline only: full archive, raw occurrence, physical encoding and dispatch checks."""
    case=case_path(root,pair,selected)
    if (case/'failure.json').exists(): raise ContractError('failed compact worker cannot produce successful audit')
    with scope():
        declaration,_,spec=context(root)
        ready=burst.read(case/'ready.json','ready_sha256')
        burst.localhost_uri(ready['uri'])
        measurement=burst.read(case/'measurement.json','measurement_sha256')
        fields={'schema_version','plan_sha256','pair','lane','begin_monotonic','end_monotonic',
                'consumer_identity','delivery_sha256','stream_spec_sha256','connections',
                'post_window_cpu_seconds','post_window_finished_monotonic','benchmark_performed',
                'public_rollout_authorized','orders_authorized','measurement_sha256'}
        if (set(measurement)!=fields or measurement['schema_version']!='qcrl.receive_loop_compact_trial_measurement.v1'
                or measurement['pair']!=pair or type(measurement['pair']) is not int
                or measurement['lane']!=selected or measurement['plan_sha256']!=declaration['plan_sha256']
                or measurement['stream_spec_sha256']!=payload_hash(spec)
                or measurement['benchmark_performed'] is not True
                or measurement['orders_authorized'] is not False or measurement['public_rollout_authorized'] is not False):
            raise ContractError('measurement shape/source binding differs')
        if not finite(measurement['begin_monotonic'])<=finite(measurement['end_monotonic'])<=finite(measurement['post_window_finished_monotonic']):
            raise ContractError('measurement ordering invalid')
        finite(measurement['post_window_cpu_seconds'])
        def detached(path,obj,field):
            obj[field]=payload_hash(obj)
            return obj
        # Recompute without overwriting or requiring a previously cached audit.
        with patch.object(burst,'signed',detached):
            result=burst.verify_case(root,case,'recorder',require_isolation=require_isolation,receive_policy='v3')
        delivery=burst.read(case/'deliveries.json','delivery_sha256')
        if (measurement['delivery_sha256']!=delivery['delivery_sha256']
                or measurement['consumer_identity']!=delivery['consumer_identity']):
            raise ContractError('measurement/delivery binding differs')
        finite(delivery['timed_cpu_seconds'])
        if delivery['stamps']!=[r.get('application_delivery') for r in delivery['receive_records']]:
            raise ContractError('saved delivery stamps differ from archived receive records')
        producer=burst.read(case/'producer.json','producer_sha256')
        previous=None
        for obs in producer['messages']:
            begin,send,end=(finite(obs[k]) for k in ('begin','send_start','send_end'))
            finite(obs['deadline'])
            if not begin<=send<=end or (previous is not None and begin<previous):
                raise ContractError('producer operation ordering invalid')
            previous=end
        scans={}
        bands=measurement['connections']
        if not isinstance(bands,list) or len(bands)>spec['max_connections']: raise ContractError('sideband population invalid')
        if selected=='baseline' and bands: raise ContractError('baseline must not contain probe sidebands')
        for entry in bands:
            if set(entry)!={'connection','sideband'}: raise ContractError('unexpected connection fields')
            number=lane.integer(entry['connection'],1)
            if number in scans: raise ContractError('duplicate connection sideband')
            if entry['sideband'].get('connection_outcome')!='connected': raise ContractError('compact sideband connection did not succeed')
            scans[number]=lane.transport.scan_transport(entry['sideband'],declaration['loop_contract'])
        frames=[]; rss=[]; linked=eligible=0; connections=set()
        verified=result['verification']
        import gzip
        for path in sorted((case/'stream').glob('segment-*.gz')):
            with gzip.open(path,'rb') as handle:
                for line in handle:
                    obj=json.loads(line); digest=obj.pop('record_sha256')
                    expected_digest,encoded=encode_row(obj)
                    if digest!=expected_digest or line!=encoded: raise ContractError('physical row encoding differs')
        for row in _sealed_rows(case/'stream',verified):
            payload=row['payload']
            if row['kind']=='session_start' and payload['spec_sha256']!=measurement['stream_spec_sha256']:
                raise ContractError('archive spec differs')
            if row['kind']=='profiling_sample':
                value=payload.get('resources',{}).get('rss_bytes')
                if value is not None: rss.append(finite(value))
            if row['kind']!='frame': continue
            record=payload['receive_path']; frames.append(record); connection=record['connection']; connections.add(connection)
            stamp=record['application_delivery']
            if not measurement['begin_monotonic']<=stamp['monotonic_before']<=stamp['monotonic_after']<=measurement['end_monotonic']:
                raise ContractError('delivery outside measured window')
            eligible+=bool(record.get('receive_marker') and record['first_observation_to_delivery']['timing_eligible']
                           and record['last_observation_to_delivery']['timing_eligible'])
            if selected=='baseline': continue
            if connection not in scans: raise ContractError('missing archived connection sideband')
            scan=scans[connection]
            if scan['complete'] and scan['frame_callbacks']<record['alignment']['observed_frames']:
                raise ContractError('sideband omits observed frames')
            marker=record['receive_marker']
            if not marker or not scan['complete']: continue
            for ordinal_field,stamp_field in [('first_frame_sequence','first_receive_observation'),
                                             ('last_frame_sequence','last_receive_observation')]:
                ordinal=marker[ordinal_field]; position=bisect_left(scan['ends'],ordinal)
                if position>=len(scan['ranges']) or ordinal<scan['ranges'][position]['frame_first']:
                    raise ContractError('marker has no dispatch range')
                dispatch=scan['ranges'][position]; stamp=marker[stamp_field]
                if not dispatch['dispatch_first_begin']<=stamp['monotonic_before']<=stamp['monotonic_after']<=dispatch['dispatch_last_end']:
                    raise ContractError('marker outside dispatch bounds')
            linked+=1
        if [r for r in frames]!=delivery['receive_records']: raise ContractError('saved/archive receive records differ')
        if selected=='instrumented' and connections!=set(scans): raise ContractError('sideband/archive connection population differs')
        # Unknown/overflow generations are explicit, never rescued by raw preservation.
        from execution_truth.receive_recovery import validate_recovery_connection
        header=next(_sealed_rows(case/'stream',verified))['payload']
        recovery=validate_recovery_connection(frames,header['receive_path_contract'],delivery['raws'])
        return {'pair':pair,'lane':selected,'case_report_sha256':result['report_sha256'],
            'measurement_sha256':measurement['measurement_sha256'],'metrics':result,
            'measurement':measurement,'eligible':eligible,'linked':linked,
            'sideband_complete':all(s['complete'] for s in scans.values()) if selected=='instrumented' else True,
            'rss_sample_count':len(rss),'rss_max_bytes':max(rss,default=None),'recovery':recovery}


def evaluate_metrics(cases):
    """Pure gate over independently recomputed case metrics; resource/origin gate separate."""
    if len(cases)!=6 or {(c['pair'],c['lane']) for c in cases}!={(p,s) for p in range(3) for s in ('baseline','instrumented')}:
        raise ContractError('six unique case metrics required')
    gates=plan.POLICY['acceptance']; failures=[]; missing=[]; comparisons=[]
    for pair in range(3):
        chosen={c['lane']:c for c in cases if c['pair']==pair}
        for selected,c in chosen.items():
            m=c['metrics']; n=m['messages']
            if n!=30000 or c['eligible']!=n or not c['sideband_complete'] or (selected=='instrumented' and c['linked']!=n):
                failures.append(f'{pair}/{selected}:coverage')
            alignment=c.get('recovery',{}).get('last_alignment',{})
            if (m['unknown_receive_records'] or m['recovery_generations']
                    or alignment.get('overflow') is not None or alignment.get('state','aligned')!='aligned'):
                failures.append(f'{pair}/{selected}:recovery')
            for w in m['phase_windows']:
                value=w['attained_begin_messages_per_second']
                if value is None: missing.append(f'{pair}/{selected}:producer_attainment')
                elif finite(value)<w['target_rate']*gates['producer_phase_attainment_fraction_min']:
                    missing.append(f'{pair}/{selected}:producer_invalid')
            for rate in ('500','3000'):
                if finite(m['phases'][rate]['producer_deadline_lateness']['max_seconds'])>gates['producer_max_deadline_lateness_seconds']:
                    missing.append(f'{pair}/{selected}:producer_late')
        b,c=chosen['baseline'],chosen['instrumented']
        if b['rss_sample_count']!=c['rss_sample_count'] or b['rss_sample_count']==0:
            missing.append(f'{pair}:inconsistent_rss_sampling')
        values={'cpu':(b['metrics']['consumer_timed_cpu_seconds'],c['metrics']['consumer_timed_cpu_seconds'],gates['each_pair_cpu_ratio_max']),
                'rss':(b['rss_max_bytes'],c['rss_max_bytes'],gates['each_pair_sampled_rss_max_ratio_max'])}
        for rate in ('500','3000'):
            values['p99_'+rate]=(b['metrics']['phases'][rate]['producer_begin_to_delivery_upper'].get('p99_seconds'),
                                c['metrics']['phases'][rate]['producer_begin_to_delivery_upper'].get('p99_seconds'),
                                gates['each_pair_low_rate_p99_ratio_max'] if rate=='500' else gates['each_pair_burst_p99_ratio_max'])
        values['worst']=(max(b['metrics']['phases'][r]['producer_begin_to_delivery_upper'].get('max_seconds',0) for r in ('500','3000')),
                         max(c['metrics']['phases'][r]['producer_begin_to_delivery_upper'].get('max_seconds',0) for r in ('500','3000')),gates['each_pair_worst_delivery_upper_bound_ratio_max'])
        ratios={}
        for key,(baseline,candidate,limit) in values.items():
            if baseline is None or candidate is None or finite(baseline)==0:
                missing.append(f'{pair}:{key}_missing'); ratios[key]=None
            else:
                ratios[key]=finite(candidate)/baseline
                if ratios[key]>limit: failures.append(f'{pair}:{key}_regression')
        comparisons.append({'pair':pair,'ratios':ratios})
    return {'metric_gate':'inconclusive' if missing else 'reject' if failures else 'pass',
            'failures':failures,'inconclusive_reasons':missing,'pairs':comparisons,
            'resource_and_origin_gate':'not_verified','advancement':'inconclusive',
            'public_rollout_authorized':False,'orders_authorized':False}


def measured_order(cases):
    """Check consumer intervals only; never substitute them for actual worker exits."""
    by_case={(c['pair'],c['lane']):c for c in cases}
    ordered=[by_case[(pair,selected)] for pair,lanes in enumerate(plan.POLICY['pair_order']) for selected in lanes]
    boots={c['measurement']['consumer_identity']['boot_id'] for c in ordered}
    if len(boots)!=1 or None in boots: return False
    return all(a['measurement']['post_window_finished_monotonic']<=b['measurement']['begin_monotonic']
               for a,b in zip(ordered,ordered[1:]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role',choices=['stage','produce','consume','verify','evaluate'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--pair',type=int,choices=[0,1,2])
    parser.add_argument('--lane',choices=['baseline','instrumented'])
    parser.add_argument('--declaration',type=Path); parser.add_argument('--corpus',type=Path)
    parser.add_argument('--execute',action='store_true',help='explicit private worker execution, never implied by staging')
    args=parser.parse_args()
    if args.role=='stage':
        if args.declaration is None or args.corpus is None: parser.error('stage requires declaration and corpus')
        stage(args.root,json.loads(args.declaration.read_text()),args.corpus)
    elif args.role=='evaluate':
        cases=[verify_case(args.root,p,s) for p in range(3) for s in ('baseline','instrumented')]
        result=evaluate_metrics(cases)
        result['consumer_interval_order_verified']=measured_order(cases)
        result['case_bindings']=[{'pair':c['pair'],'lane':c['lane'],
            'measurement_sha256':c['measurement_sha256'],'case_report_sha256':c['case_report_sha256']}
            for c in cases]
        signed(args.root/'evaluation.json',result,'evaluation_sha256')
        print(json.dumps(result))
    else:
        if args.pair is None or args.lane is None: parser.error('worker requires fixed pair and lane')
        if args.role in ('produce','consume') and not args.execute:
            parser.error('numeric-localhost worker requires explicit --execute')
        result=globals()[{'verify':'verify_case'}.get(args.role,args.role)](args.root,args.pair,args.lane)
        if result is not None: print(json.dumps(result))


if __name__=='__main__': main()
