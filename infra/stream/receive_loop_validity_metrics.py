"""Pure offline paired cost gates; self-reports never verify origin or units."""
import math

from execution_truth.contracts import ContractError
from infra.stream import receive_loop_validity_cost as plan
from infra.stream.receive_loop_validity import number


def positive(value):
    if value is None: return None
    if number(value)<0: raise ContractError('negative cost measurement')
    return value


def case_metrics(verified, worker, observer, done, ack):
    p=plan.POLICY; gate=p['acceptance']; failures=[]; unknown=[]
    if verified['test_only']: unknown.append('test_only_fixture')
    values=verified['measurements']
    combined={}
    for key in ('cpu_seconds','rss_max_bytes'):
        v=[positive(values[r][key]) for r in ('worker','observer')]
        combined[key]=None if None in v else sum(v)
    rows=worker['core']['rows']; position=0; tails={}
    for cycle in range(p['cycles']):
        for phase in p['phases']:
            n=phase['seconds']*phase['rate']; segment=rows[position:position+n];position+=n
            key=f"{cycle}:{phase['rate']}"
            if len(segment)!=n:
                unknown.append('producer_population');tails[key]=None;continue
            span=segment[-1]['begin']-segment[0]['begin']
            if span<=0: unknown.append('producer_span');tails[key]=None;continue
            if (n-1)/span<phase['rate']*gate['producer_phase_attainment_min']:
                failures.append('producer_attainment')
            delays=[max(0,number(r['begin'])-number(r['deadline'])) for r in segment]
            values_sorted=sorted(delays)
            tails[key]={'p99':values_sorted[math.ceil(.99*len(values_sorted))-1], 'worst':values_sorted[-1]}
            if tails[key]['worst']>gate['producer_deadline_lateness_max_seconds']:
                failures.append('producer_lateness')
    if observer['skipped_ticks']: failures.append('observer_skipped_ticks')
    for row in observer['core']['rows']:
        if max(0,number(row['deadline_lateness_seconds']))>gate['observer_lateness_max_seconds']:
            failures.append('observer_lateness')
        if worker['core']['lane']=='full':
            sample=row['counter']['sample']
            if sample['read_end']-sample['read_begin']>gate['counter_read_bracket_max_seconds']:
                failures.append('counter_bracket')
            if not set(gate['required_counters']) <= set(dict(sample['counters'])):
                unknown.append('missing_counter_fields')
    for pair in worker['core']['cpu_pairs']:
        for stamp in pair:
            if stamp['wall_after']-stamp['wall_before']>gate['max_inline_clock_bracket_seconds']:
                failures.append('inline_cpu_bracket')
    return dict(combined_cpu=combined['cpu_seconds'],combined_rss=combined['rss_max_bytes'],
                tails=tails,failures=sorted(set(failures)),unknown=sorted(set(unknown)))


def evaluate(cases):
    expected={(r,lane) for r in range(3) for lane in plan.POLICY['lanes']}
    if (len(cases)!=9 or any(type(c['round']) is not int for c in cases)
            or {(c['round'],c['lane']) for c in cases}!=expected):
        raise ContractError('nine unique declared cases required')
    indexed={(c['round'],c['lane']):c for c in cases};failures=[];unknown=[];pairs=[]
    gate=plan.POLICY['acceptance']
    for key,c in indexed.items():
        failures.extend(str(key)+':'+f for f in c['metrics']['failures'])
        unknown.extend(str(key)+':'+f for f in c['metrics']['unknown'])
    for r in range(3):
        baseline=indexed[r,'control']['metrics']
        for lane in ('pacing','full'):
            candidate=indexed[r,lane]['metrics'];ratios={};added={}
            for key,limit in (('combined_cpu',gate['combined_cpu_ratio_max_each_lane_vs_round_control']),
                              ('combined_rss',gate['combined_sampled_rss_ratio_max_each_lane_vs_round_control'])):
                b,c=positive(baseline[key]),positive(candidate[key])
                ratios[key]=None if b in (None,0) or c is None else c/b
                if ratios[key] is None: unknown.append(f'{r}/{lane}:{key}_missing_or_zero_control')
                elif ratios[key]>limit:failures.append(f'{r}/{lane}:{key}_regression')
            for rate in (f'{cycle}:{rate}' for cycle in range(6) for rate in ('500','3000')):
                b,c=baseline['tails'][rate],candidate['tails'][rate]
                for field,limit in (('p99',gate['p99_begin_lateness_added_seconds_max']),
                                    ('worst',gate['worst_begin_lateness_added_seconds_max'])):
                    k=rate+'_'+field
                    added[k]=None if b is None or c is None else positive(c[field])-positive(b[field])
                    if added[k] is None:unknown.append(f'{r}/{lane}:{k}_missing')
                    elif added[k]>limit:failures.append(f'{r}/{lane}:{k}_regression')
            pairs.append(dict(round=r,lane=lane,ratios=ratios,added_seconds=added))
    return dict(metric_gate='inconclusive' if unknown else 'reject' if failures else 'pass',
                failures=sorted(set(failures)),inconclusive_reasons=sorted(set(unknown)),pairs=pairs,
                origin_and_resources='not_verified',probe_cost_accepted=False,
                public_rollout_authorized=False,orders_authorized=False)
