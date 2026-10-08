"""Offline paired localhost delay intervals; never wire latency or fill evidence."""
import argparse
from array import array
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import verify_stream_log
from execution_truth.stream_freshness import statistics
from execution_truth.stream_receive_analysis import _sealed_rows
from infra.stream import marker_cap_pair as cap

POLICY = {"schema_version": "qcrl.delay_decomposition_policy.v1", "max_messages_per_case": 30000,
          "max_source_bytes": 256*1024**2, "tail_fraction": .01, "max_tail_examples": 12,
          "split_boundary": "last_data_frame_callback_bracket_before_assembler",
          "tail_selection": "descending_total_upper_then_ascending_delivery_index_within_phase",
          "tail_denominator": "all_deliveries_keep_unknown_and_ineligible",
          "quantiles": "linear_interpolation_on_matched_eligible_population",
          "clock_correction": "none", "causal_attribution": "none"}


def load(path, field):
    with Path(path).open('rb') as handle:
        raw = handle.read(POLICY['max_source_bytes']+1)
    if len(raw) > POLICY['max_source_bytes']:
        raise ContractError('decomposition source byte budget exceeded')
    obj = json.loads(raw)
    verify_artifact_hash(obj, field, str(path))
    return obj


def verify_origin(review):
    evidence = Path(review)/'evidence'
    names = set()
    for line in (Path(review)/'origin-inventory.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = Path(name)
        if (not name.startswith('./') or '..' in path.parts or path.is_absolute()
                or name in names or len(names) >= 10000):
            raise ContractError('invalid originating inventory')
        target = evidence/path
        if any(p.is_symlink() for p in [target, *target.parents]):
            raise ContractError('symlink in originating evidence')
        h = hashlib.sha256()
        with target.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024**2), b''): h.update(chunk)
        if h.hexdigest() != digest:
            raise ContractError('originating evidence bytes changed')
        names.add(name)
    if not names: raise ContractError('empty originating inventory')
    return len(names)


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError('invalid shared-host monotonic clock')
    return value


def split(begin, record):
    """Bracket-aware per-message split; unknown/ineligible never gets a split."""
    begin = finite(begin)
    delivery = record['application_delivery']
    dl, du = finite(delivery['monotonic_before']), finite(delivery['monotonic_after'])
    if not begin <= dl <= du: raise ContractError('delivery precedes producer or bracket regresses')
    total = [dl-begin, du-begin]
    marker = record.get('receive_marker')
    if marker is None: return {'status':'unknown', 'total':total}
    if not (record['first_observation_to_delivery']['timing_eligible']
            and record['last_observation_to_delivery']['timing_eligible']):
        return {'status':'ineligible', 'total':total}
    callback = marker['last_receive_observation']
    cl, cu = finite(callback['monotonic_before']), finite(callback['monotonic_after'])
    if callback['clock_domain'] != delivery['clock_domain'] or not begin <= cl <= cu <= dl:
        raise ContractError('invalid shared callback/delivery interval')
    upstream, downstream = [cl-begin, cu-begin], [dl-cu, du-cl]
    width = cu-cl
    if (abs(upstream[0]+downstream[0]+width-total[0]) > 1e-9
            or abs(upstream[1]+downstream[1]-width-total[1]) > 1e-9):
        raise ContractError('paired interval closure failed')
    dominance = ('pre_callback' if upstream[0] > downstream[1] else
                 'post_callback' if downstream[0] > upstream[1] else 'overlapping_bounds')
    return {'status':'eligible', 'total':total, 'pre_callback':upstream,
            'post_callback':downstream, 'dominance':dominance}


def population(indices, observations, records):
    counts = Counter({'deliveries':0, 'eligible':0, 'unknown':0, 'ineligible':0})
    values = {stage:{bound:array('d') for bound in ('lower','upper','midpoint')}
              for stage in ('total','pre_callback','post_callback')}
    all_upper = array('d'); dominance = Counter()
    for i in indices:
        sample = split(observations[i]['begin'], records[i])
        counts['deliveries'] += 1; counts[sample['status']] += 1
        all_upper.append(sample['total'][1])
        if sample['status'] != 'eligible': continue
        dominance[sample['dominance']] += 1
        for stage in values:
            lower, upper = sample[stage]
            for bound, value in [('lower',lower),('upper',upper),('midpoint',(lower+upper)/2)]:
                values[stage][bound].append(value)
    means = {stage:sum(v['midpoint'])/len(v['midpoint']) if v['midpoint'] else None
             for stage,v in values.items()}
    return {'counts':dict(counts), 'all_delivery_total_upper':statistics(all_upper),
            'matched_eligible':{s:{k:statistics(v) for k,v in b.items()} for s,b in values.items()},
            'paired_midpoint_means_seconds':means, 'interval_dominance':dict(dominance),
            'component_quantiles_are_not_additive':True}


def summarize(observations, records):
    if not 0 < len(records) == len(observations) <= POLICY['max_messages_per_case']:
        raise ContractError('decomposition population budget or lengths invalid')
    groups = {'all':list(range(len(records)))}
    for rate in (500,3000):
        groups[str(rate)] = [i for i,o in enumerate(observations) if o['phase_rate']==rate]
    if len(groups['500'])+len(groups['3000']) != len(records):
        raise ContractError('unknown producer phase')
    if not groups['500'] or not groups['3000']:
        raise ContractError('missing producer phase')
    out = {}
    for phase, indices in groups.items():
        if not indices: raise ContractError('missing producer phase')
        ranked = sorted(indices, key=lambda i:(-split(observations[i]['begin'], records[i])['total'][1],i))
        tail = ranked[:max(1,math.ceil(len(indices)*POLICY['tail_fraction']))]
        examples = [{'delivery_index':i, 'split':split(observations[i]['begin'],records[i]),
                     'producer_deadline_lateness_seconds':observations[i]['begin']-observations[i]['deadline'],
                     'producer_send_call_seconds':observations[i]['send_end']-observations[i]['send_start'],
                     'library_queue_depth':records[i]['library_queue_depth'],
                     'library_backpressure_active':records[i]['library_backpressure_active'],
                     'reader_time_outside_recv_seconds':records[i]['reader_loop_stall_seconds']}
                    for i in tail[:POLICY['max_tail_examples']]]
        out[phase] = {'population':population(indices, observations, records),
                      'total_upper_tail':population(tail, observations, records),
                      'tail_examples':examples}
    return out


def analyze_case(review, lane, number, audited):
    case = Path(review)/'evidence'/lane/str(number)
    producer = load(case/'producer.json','producer_sha256')
    delivery = load(case/'deliveries.json','delivery_sha256')
    ready = load(case/'ready.json','ready_sha256')
    if (producer['ready_sha256'] != ready['ready_sha256']
            or producer['producer_identity'] != ready['producer_identity']
            or producer['producer_identity']['boot_id'] != delivery['consumer_identity']['boot_id']
            or producer['producer_identity']['pid'] == delivery['consumer_identity']['pid']
            or payload_hash(delivery['raws']) != producer['raw_messages_sha256']):
        raise ContractError('producer/consumer identity or raw binding mismatch')
    with cap.scope(lane), cap.original.lane('single_pass'):
        declaration, _, spec = cap.original.burst.context(case.parent,'recorder','v3')
        verified = verify_stream_log(case/'stream')
    if verified['frames'] != len(delivery['receive_records']) or len(delivery['raws']) != verified['frames']:
        raise ContractError('decomposition frame population mismatch')
    index = 0
    for row in _sealed_rows(case/'stream', verified):
        if row['kind'] != 'frame': continue
        if (row['payload']['raw_text'] != delivery['raws'][index]
                or row['payload']['receive_path'] != delivery['receive_records'][index]
                or delivery['stamps'][index] != delivery['receive_records'][index]['application_delivery']):
            raise ContractError('saved application record differs from verified archive')
        index += 1
    schedule = cap.original.burst.offsets()
    if len(producer['messages']) != len(schedule) or index != len(schedule):
        raise ContractError('source differs from frozen diagnostic workload')
    for i,(obs,target,raw) in enumerate(zip(producer['messages'],schedule,delivery['raws'])):
        if (obs['sequence'] != i or obs['phase_rate'] != target['phase_rate']
                or abs(obs['deadline']-producer['messages'][0]['deadline']-target['offset']) > 1e-8):
            raise ContractError('producer occurrence or target phase mismatch')
        if target.get('synthetic_pong'):
            if raw != 'PONG': raise ContractError('synthetic heartbeat mismatch')
        else:
            events = json.loads(raw)
            for event in events if isinstance(events,list) else [events]:
                if event['_qcrl_probe'] != {'sequence':i,'producer_begin_monotonic':obs['begin']}:
                    raise ContractError('producer probe mismatch')
    phases = summarize(producer['messages'],delivery['receive_records'])
    for phase,key in [('500','baseline_p99_seconds'),('3000','burst_p99_seconds')]:
        if phases[phase]['population']['all_delivery_total_upper']['p99_seconds'] != audited[key]:
            raise ContractError('decomposition total differs from bound independent audit')
    return {'lane':lane,'pair':number,'source':{'producer_sha256':producer['producer_sha256'],
        'delivery_sha256':delivery['delivery_sha256'],'plan_sha256':declaration['plan_sha256'],
        'spec_sha256':payload_hash(spec),'final_record_sha256':verified['final_record_sha256']},
        'phases':phases}


def analyze_review(review, expected_audit_sha256):
    audit = load(Path(review)/'independent-audit.json','audit_sha256')
    if (audit['audit_sha256'] != expected_audit_sha256
            or audit['schema_version'] != 'qcrl.marker_cap_pair_independent_audit.v1'
            or {(c['encoder'],c['round']) for c in audit['cases']} != {(l,r) for l in cap.LANES for r in range(3)}
            or len(audit['cases']) != 6):
        raise ContractError('decomposition requires explicitly pinned six-case audit')
    files = verify_origin(review)
    cases = [analyze_case(review,c['encoder'],c['round'],c) for c in audit['cases']]
    out = {'schema_version':'qcrl.delay_decomposition.v1','policy':deepcopy(POLICY),
           'policy_sha256':payload_hash(POLICY),'source_audit_sha256':audit['audit_sha256'],
           'origin_files_reverified':files,'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'cases':cases,'orders_authorized':False,'public_rollout_authorized':False,
           'wire_arrival_measured':False,'clock_domain':'same_verified_host_boot_monotonic',
           'limitations':['pre_callback_includes_serialization_send_transport_and_receiver_backpressure',
               'post_callback_includes_adapter_assembler_queue_scheduling_and_caller_work',
               'unknown_and_ineligible_not_reconstructed','top_tail_components_share_message_population',
               'profiling_samples_not_event_specific_causes','synthetic_localhost_not_exchange_or_fill_latency']}
    out['analysis_sha256'] = payload_hash(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    parser.add_argument('--audit-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = analyze_review(args.review,args.audit_sha256)
    with args.output.open('x',encoding='utf-8') as handle:
        json.dump(out,handle,indent=2,sort_keys=True); handle.write('\n')
    print(json.dumps({'analysis_sha256':out['analysis_sha256'],'cases':len(out['cases'])}))


if __name__ == '__main__': main()
