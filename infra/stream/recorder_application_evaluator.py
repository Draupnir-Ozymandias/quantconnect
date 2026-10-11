"""Offline component gates and archive audit; independent launch binding still required."""
import gzip
import hashlib
import json
import math
from pathlib import Path

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import stream_plan
from infra.stream.recorder_application_budget import POLICY, validate
from infra.stream.recorder_application_worker import control, schedule, implementation_sources, localhost_uri
from infra.stream.recorder_application_resources import quota
from infra.stream.recorder_completion import verify_completion


def finite(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError('finite nonnegative number required')
    return value


def percentile(values, fraction=.99):
    if not values:
        raise ContractError('missing timing denominator')
    return sorted(finite(v) for v in values)[math.ceil(len(values) * fraction) - 1]


def outcome(failures, unknowns):
    return 'fail' if failures else 'unknown' if unknowns else 'pass'


def timing_gate(latencies, witnesses, phases, budgets):
    failures, unknowns, groups = [], [], {}
    if len(latencies) != len(witnesses) or len(phases) != len(latencies):
        return dict(verdict='unknown', failures=[], unknowns=['timing_population_missing'], groups={})
    # Preserve known per-row worst violations even when another row is unusable.
    for i, (latency, witness) in enumerate(zip(latencies, witnesses)):
        for key, limit in [('append_upper_seconds', budgets['return_to_append_completion_upper_seconds']['worst']),
                           ('durable_upper_seconds', budgets['return_to_successful_durable_watermark_upper_seconds']['worst'])]:
            try:
                if finite(latency[key]) > limit:
                    failures.append('row:' + str(i) + ':' + key)
            except (ContractError, KeyError, TypeError):
                unknowns.append('row:' + str(i) + ':' + key)
        try:
            width = finite(witness['returned']['after']) - finite(witness['returned']['before'])
            if width > budgets['local_utc_bracket_width_max_seconds']:
                failures.append('row:' + str(i) + ':utc_bracket')
        except (ContractError, KeyError, TypeError):
            unknowns.append('row:' + str(i) + ':utc_bracket')
    for label in ['case'] + sorted(set(phases)):
        indexes = range(len(phases)) if label == 'case' else [i for i, p in enumerate(phases) if p == label]
        try:
            indexes = list(indexes)
            append = [finite(latencies[i]['append_upper_seconds']) for i in indexes]
            durable = [finite(latencies[i]['durable_upper_seconds']) for i in indexes]
            brackets = []
            for i in indexes:
                before, after = (finite(witnesses[i]['returned'][k]) for k in ('before', 'after'))
                if after < before:
                    raise ContractError('clock bracket regressed')
                brackets.append(after - before)
            values = dict(count=len(indexes), append_p99=percentile(append),
                          append_worst=max(append), durable_worst=max(durable),
                          utc_bracket_worst=max(brackets))
            groups[str(label)] = values
            limit = budgets['return_to_append_completion_upper_seconds']
            for name, threshold in [('append_p99', limit['nearest_rank_p99']),
                                    ('append_worst', limit['worst']),
                                    ('durable_worst', budgets['return_to_successful_durable_watermark_upper_seconds']['worst']),
                                    ('utc_bracket_worst', budgets['local_utc_bracket_width_max_seconds'])]:
                if values[name] > threshold:
                    failures.append(str(label) + ':' + name)
        except (ContractError, KeyError, TypeError, ValueError):
            unknowns.append(str(label) + ':invalid_or_missing_timing')
    return dict(verdict=outcome(failures, unknowns), failures=failures, unknowns=unknowns, groups=groups)


def stimulus_gate(result, kind, epoch):
    expected = schedule(kind)
    rows = result.get('rows', [])
    failures, unknowns = [], []
    if result.get('complete') is not True or result.get('error') is not None or len(rows) != len(expected):
        failures.append('incomplete_stimulus')
    attained = [0] * len(POLICY['workloads'][kind])
    counts = [0] * len(attained)
    starts, offset = [], 0
    for phase in POLICY['workloads'][kind]:
        starts.append((epoch + offset, epoch + offset + phase['seconds']))
        offset += phase['seconds']
    previous = epoch
    for i, row in enumerate(rows[:len(expected)]):
        try:
            want = expected[i]
            if any(row[k] != want[k] for k in ('sequence', 'phase', 'offset')) or row['deadline'] != epoch + want['offset']:
                raise ContractError('producer schedule differs')
            begin, end = finite(row['begin']), finite(row['end'])
            if not previous <= begin <= end or begin < row['deadline']:
                raise ContractError('producer chronology differs')
            previous = end
            if begin - row['deadline'] > POLICY['send_start_lateness_max_seconds']:
                failures.append('send_lateness:' + str(i))
            if end - begin > POLICY['send_bracket_max_seconds']:
                failures.append('send_duration:' + str(i))
            p = want['phase']
            counts[p] += 1
            if starts[p][0] <= begin < starts[p][1]:
                attained[p] += 1
        except (ContractError, KeyError, TypeError, ValueError):
            unknowns.append('producer_witness:' + str(i))
    for phase, spec in enumerate(POLICY['workloads'][kind]):
        denominator = spec['seconds'] * spec['rate']
        if attained[phase] / denominator < POLICY['send_start_phase_attainment_min']:
            failures.append('phase_attainment:' + str(phase))
    return dict(verdict=outcome(failures, unknowns), failures=failures, unknowns=unknowns,
                phase_attained=attained, phase_observed=counts)


def resource_gate(resources, epoch, duration, closed, budgets, owner):
    failures, unknowns, windows = [], [], []
    rows = resources.get('rows', [])
    if resources.get('overflow') is True:
        failures.append('resource_observation_overflow')
    if resources.get('error') or not rows:
        unknowns.append('missing_resource_observation')
    seen, prior_cpu, prior_events, ancestry = {}, None, None, None
    for row in rows:
        slot = row.get('slot')
        if type(slot) is not int or slot < 0 or slot in seen:
            unknowns.append('resource_slot_invalid_or_duplicate')
            continue
        seen[slot] = row
        try:
            if row['target'] != epoch + slot or row.get('error'):
                raise ContractError('resource slot missing/raced')
            s = row['sample']
            before, after = finite(s['before']), finite(s['after'])
            if not epoch + slot <= before <= after or after - before > .005 or before - epoch - slot > .05:
                raise ContractError('RSS bracket/lateness invalid')
            if s['owner'] != owner or quota(s['ancestry']) != s['effective_quota']:
                raise ContractError('resource identity/quota differs')
            if ancestry is None:
                ancestry = s['ancestry']
            if s['ancestry'] != ancestry:
                raise ContractError('resource ancestry changed')
            if s['ancestry'][0]['memory_max'] != str(POLICY['unit']['memory_max_bytes']):
                raise ContractError('unit memory cap differs')
            for ancestor in s['ancestry']:
                value = ancestor['memory_max']
                if value is None and ancestor['path'] != '.':
                    raise ContractError('missing ancestor memory cap')
                if value not in (None, 'max') and int(value) < POLICY['unit']['memory_max_bytes']:
                    raise ContractError('restrictive ancestor memory cap')
            actors = s['actors']
            if not actors or len({a['pid'] for a in actors}) != len(actors) or owner not in [{k: a[k] for k in owner} for a in actors]:
                raise ContractError('live actor binding differs')
            if any(a['cgroup'] != owner['cgroup'] or a['boot_id'] != owner['boot_id'] for a in actors):
                raise ContractError('actor domain differs')
            rss = sum(finite(a['rss_bytes']) for a in actors)
            if rss != s['rss_bytes']:
                raise ContractError('current RSS sum differs')
            if rss > budgets['current_rss_sample_fraction_unit_limit_max'] * POLICY['unit']['memory_max_bytes']:
                failures.append('current_rss:' + str(slot))
            usage = finite(s['cpu']['usage_usec'])
            if prior_cpu is not None and usage < prior_cpu:
                raise ContractError('CPU counter reset')
            prior_cpu = usage
            events = s['memory_events']
            for key in ('oom', 'oom_kill', 'max'):
                value = finite(events[key])
                if prior_events is not None:
                    if value < prior_events[key]:
                        raise ContractError('memory counter reset')
                    if value > prior_events[key]:
                        failures.append('resource_limit_event:' + key)
                elif value > 0:
                    failures.append('nonzero_initial_resource_event:' + key)
            prior_events = events
        except (ContractError, KeyError, TypeError, ValueError):
            unknowns.append('resource_sample:' + str(slot))
    for slot in range(math.ceil(max(duration, closed - epoch)) + 1):
        if slot not in seen:
            unknowns.append('resource_slot_missing:' + str(slot))
    for offset in range(0, duration - 59, 60):
        try:
            a = seen[offset]['cpu_before']
            b = seen[offset + 60]['sample']
            for s in (a, b):
                if s['owner'] != owner or s['ancestry'] != ancestry or finite(s['after']) - finite(s['before']) > .005:
                    raise ContractError('CPU endpoint identity/bracket differs')
                if quota(s['ancestry']) != s['effective_quota']:
                    raise ContractError('CPU endpoint quota differs')
            if not a['after'] <= epoch + offset or not b['before'] >= epoch + offset + 60:
                raise ContractError('CPU endpoints do not enclose window')
            delta = finite(b['cpu']['usage_usec']) - finite(a['cpu']['usage_usec'])
            if delta < 0:
                raise ContractError('CPU window reset')
            fraction = delta / 1e6 / (60 * a['effective_quota'])
            windows.append(dict(offset=offset, cpu_fraction_upper=fraction))
            if fraction > budgets['cpu_fraction_effective_quota_max']:
                failures.append('cpu_window:' + str(offset))
        except (ContractError, KeyError, TypeError, ValueError, ZeroDivisionError):
            unknowns.append('cpu_window:' + str(offset))
    return dict(verdict=outcome(failures, unknowns), failures=failures, unknowns=unknowns,
                windows=windows, rss_continuous_peak_proven=False)


def large_control(path):
    with Path(path).open('rb') as handle:
        data = handle.read(32 * 1024**2 + 1)
    if len(data) > 32 * 1024**2:
        raise ContractError('producer artifact cap exceeded')
    obj = json.loads(data)
    verify_artifact_hash(obj, 'artifact_sha256', str(path))
    return obj


def audit_case(root, declaration):
    """No source/unit origin attestation from mere self-reported metrics."""
    validate(declaration)
    root = Path(root)
    case = control(root / 'case.json')
    consumer = control(root / 'consumer.json')
    producer = large_control(root / 'producer.json')
    for artifact in (consumer, producer):
        if artifact['case_sha256'] != case['artifact_sha256']:
            raise ContractError('case artifact binding differs')
    if case['plan_sha256'] != declaration['plan_sha256'] or case['case'] not in POLICY['case_order']:
        raise ContractError('case declaration differs')
    if case['implementation_sources'] != implementation_sources():
        raise ContractError('implementation source drift')
    for name in ('server-ready.json', 'worker-ready.json', 'observer-ready.json'):
        ready = control(root / name)
        if ready['case_sha256'] != case['artifact_sha256'] or not finite(ready['at']) < finite(case['epoch']):
            raise ContractError('readiness chronology differs')
        expected = producer['identity'] if name == 'server-ready.json' else consumer['identity']
        if ready['identity'] != expected:
            raise ContractError('readiness actor differs')
        if name == 'server-ready.json':
            localhost_uri(ready['uri'])
    if (consumer['identity']['boot_id'] != case['boot_id'] or producer['identity']['boot_id'] != case['boot_id']
            or consumer['identity']['cgroup'] == producer['identity']['cgroup']
            or consumer['domain'] != 'localhost.' + case['boot_id']):
        raise ContractError('clock/isolation domain differs')
    spec = stream_plan(case['raw_bundle'], segmented=True, max_seconds=180, max_frames=60000)
    if spec != case['spec']:
        raise ContractError('case stream spec differs')
    with (root / 'completion.json').open('rb') as handle:
        data = handle.read(32 * 1024**2 + 1)
    if len(data) > 32 * 1024**2:
        raise ContractError('completion artifact cap exceeded')
    completion = json.loads(data)
    verified = verify_completion(completion, root / 'archive', expected_domain=consumer['domain'])
    if completion['spec_sha256'] != payload_hash(spec):
        raise ContractError('completion spec binding differs')
    if completion['runtime']['pid'] != consumer['identity']['pid']:
        raise ContractError('completion actor differs')
    # Independently rescan raw strings, comparing exact ordered occurrences.
    population = declaration['corpus']
    sent = producer['result']['rows']
    index = 0
    footer = None
    gaps = 0
    for descriptor in sorted((root / 'archive').glob('segment-*.json')):
        item = json.loads(descriptor.read_text())
        with gzip.open(root / 'archive' / item['file'], 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                if row['kind'] == 'session_end':
                    footer = row['payload']
                if row['kind'] == 'connection_gap':
                    gaps += 1
                if row['kind'] != 'frame':
                    continue
                if index >= 60000 or index >= len(sent):
                    raise ContractError('extra archived occurrence')
                expected = population['initial'][index] if index < 2 else population['cycle'][(index-2) % 8]
                if row['payload']['raw_text'] != expected or sent[index]['raw_sha256'] != hashlib.sha256(expected.encode()).hexdigest():
                    raise ContractError('sent/archive occurrence differs')
                index += 1
    if index != 60000 or index != len(sent):
        raise ContractError('missing occurrence')
    if footer != consumer['summary']:
        raise ContractError('consumer/archive footer differs')
    kind = case['case'].split('-')[0]
    scheduled = schedule(kind)
    timing = timing_gate(verified['latencies'], completion['frames'],
                         [r['phase'] for r in scheduled], declaration['budgets'])
    stimulus = stimulus_gate(producer['result'], kind, case['epoch'])
    duration = sum(p['seconds'] for p in POLICY['workloads'][kind])
    resources = resource_gate(consumer['resources'], case['epoch'], duration,
                              consumer['closed'], declaration['budgets'], consumer['identity'])
    failures = list(timing['failures']) + stimulus['failures'] + resources['failures']
    if gaps:
        failures.append('archived_connection_gap')
    summary = consumer['summary']
    if (consumer.get('error') or consumer.get('observer_thread_alive') is not False
            or not summary or summary.get('status') != 'frame_limit' or summary.get('frames') != 60000
            or summary.get('connections') != 1
            or summary.get('book_snapshot_assets_by_connection') != {'1': ['10001', '10002']}):
        failures.append('capture_lifecycle_or_observer_failure')
    unknowns = timing['unknowns'] + stimulus['unknowns'] + resources['unknowns']
    unknowns.append('independent_execution_source_unit_origin_binding_not_implemented')
    obj = dict(schema_version='qcrl.recorder_application_component_audit.v1', case=case['case'],
               archive_verified=True, timing=timing, stimulus=stimulus, resources=resources,
               failures=failures, unknowns=unknowns, verdict=outcome(failures, unknowns),
               acceptance_demonstrated=False, execution_authorized=False, orders_authorized=False)
    obj['audit_sha256'] = payload_hash(obj)
    return obj


def audit_cohort(root, declaration):
    validate(declaration)
    reports, failures, unknowns = [], [], []
    for name in POLICY['case_order']:
        path = Path(root) / name
        # Failed workers may have no completion sideband; never erase known failure.
        for file in ('consumer.json', 'producer.json'):
            if not (path / file).exists():
                continue
            try:
                prefix = large_control(path / file)
                if file == 'consumer.json' and (prefix.get('error') or prefix.get('observer_thread_alive')):
                    failures.append(name + ':consumer_failure_prefix')
                if file == 'producer.json' and (prefix['result'].get('error') or prefix['result'].get('complete') is not True):
                    failures.append(name + ':producer_failure_prefix')
            except (ContractError, KeyError, TypeError, ValueError, OSError):
                failures.append(name + ':invalid_failure_prefix')
        try:
            report = audit_case(path, declaration)
            if report['case'] != name:
                raise ContractError('case directory identity differs')
            reports.append(report)
            failures.extend(name + ':' + reason for reason in report['failures'])
            unknowns.extend(name + ':' + reason for reason in report['unknowns'])
        except FileNotFoundError:
            unknowns.append(name + ':missing_case_artifact')
        except (ContractError, ValueError, KeyError, TypeError, OSError) as exc:
            failures.append(name + ':invalid_artifact:' + type(exc).__name__)
    obj = dict(schema_version='qcrl.recorder_application_component_cohort.v1',
               plan_sha256=declaration['plan_sha256'], reports=reports,
               failures=failures, unknowns=unknowns, verdict=outcome(failures, unknowns),
               acceptance_demonstrated=False, execution_authorized=False, orders_authorized=False)
    obj['audit_sha256'] = payload_hash(obj)
    return obj
