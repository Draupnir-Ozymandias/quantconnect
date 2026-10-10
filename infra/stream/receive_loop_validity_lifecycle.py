"""Explicit single-case process lifecycle; no systemd launcher or resource acceptance."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import time

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash
from infra.stream import receive_loop_validity_cost as plan
from infra.stream.receive_loop_validity import number
from infra.stream.receive_loop_validity_probe import CounterReader
from infra.stream.receive_loop_validity_worker import WorkloadCore, GENERATOR, verify_core
from infra.stream.receive_loop_validity_observer import ObserverCore
from infra.stream import receive_loop_validity_resources as resources

FILES = ('infra/stream/receive_loop_validity_worker.py',
         'infra/stream/receive_loop_validity_observer.py',
         'infra/stream/receive_loop_validity_lifecycle.py',
         'tests/test_receive_loop_validity_worker.py',
         'tests/test_receive_loop_validity_observer.py',
         'tests/test_receive_loop_validity_lifecycle.py',
         'infra/stream/receive_loop_validity_resources.py',
         'tests/test_receive_loop_validity_resources.py')


def sources():
    repo = Path(__file__).resolve().parents[2]
    return {name: file_hash(repo/name) for name in FILES}


def save(path, obj, field='artifact_sha256'):
    obj = dict(obj)
    obj[field] = payload_hash(obj)
    # Compact, exclusive, durable artifacts. Called only outside hot step paths.
    with Path(path).open('x') as handle:
        json.dump(obj, handle, sort_keys=True, separators=(',', ':'))
        handle.flush()
        os.fsync(handle.fileno())
    return obj


def read(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 64*1024*1024:
        raise ContractError('regular bounded lifecycle artifact required')
    obj = json.loads(path.read_text())
    verify_artifact_hash(obj, 'artifact_sha256', 'lifecycle artifact')
    return obj


def wait(path, seconds=15):
    deadline = time.monotonic()+seconds
    while time.monotonic() < deadline:
        try:
            return read(path)
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(.005)
    raise ContractError('finite handshake timeout: '+Path(path).name)


def stage(root, *, test_only=False, live_bindings=None):
    if type(test_only) is not bool or (live_bindings is not None and type(live_bindings) is not bool):
        raise ContractError('explicit lifecycle fixture/binding flags required')
    required=not test_only if live_bindings is None else live_bindings
    if not test_only and not required:
        raise ContractError('production cannot disable live unit binding')
    root = Path(root)
    root.mkdir()  # Fresh, never adopt or overwrite an existing stage.
    declaration = plan.declare()
    save(root/'declaration.json', declaration)
    receipt = save(root/'implementation.json', dict(
        schema_version='qcrl.validity_lifecycle_implementation.v1',
        plan_sha256=declaration['plan_sha256'], sources=sources(),
        generator=GENERATOR, generator_sha256=payload_hash(GENERATOR),
        resource_method=resources.METHOD,
        test_only=test_only, requires_live_bindings=required,
        units_audited=False, cohort_launcher_implemented=False,
        cohort_auditor_implemented=False, execution_authorized=False))
    return receipt


def context(root, round_index, lane, *, create=False):
    root = Path(root)
    if root.is_symlink() or root.resolve() != root:
        raise ContractError('canonical lifecycle root required')
    if type(round_index) is not int or not 0 <= round_index < 3 or lane not in plan.POLICY['lanes']:
        raise ContractError('declared round/lane required')
    declaration = read(root/'declaration.json')
    declaration.pop('artifact_sha256')
    plan.validate(declaration)
    receipt = read(root/'implementation.json')
    expected = dict(schema_version='qcrl.validity_lifecycle_implementation.v1',
                    plan_sha256=declaration['plan_sha256'], sources=sources(),
                    generator=GENERATOR, generator_sha256=payload_hash(GENERATOR),
                    resource_method=resources.METHOD,
                    test_only=receipt.get('test_only'), units_audited=False,
                    requires_live_bindings=receipt.get('requires_live_bindings'),
                    cohort_launcher_implemented=False, cohort_auditor_implemented=False,
                    execution_authorized=False)
    if (type(receipt.get('test_only')) is not bool or type(receipt.get('requires_live_bindings')) is not bool
            or not receipt['test_only'] and not receipt['requires_live_bindings']
            or {k:v for k,v in receipt.items() if k != 'artifact_sha256'} != expected):
        raise ContractError('lifecycle implementation differs')
    case = root/str(round_index)/lane
    if create:
        case.mkdir(parents=True, exist_ok=True)
    if case.resolve() != case:
        raise ContractError('case symlink refused')
    return case, receipt


def identity(test_only=False):
    if platform.system() == 'Linux':
        boot, start, group = CounterReader(os.getpid(), 1)._identity()
    elif test_only:
        boot, start, group = 'test-only-platform', 'test-only-'+str(os.getpid()), '/test-only'
    else:
        raise ContractError('production lifecycle requires native Linux identity')
    return dict(pid=os.getpid(), boot_id=boot, process_start_id=start, cgroup=group)


def schedule(test_only):
    if test_only:
        return [i*.005 for i in range(8)]
    offsets, base = [], 0
    for _ in range(plan.POLICY['cycles']):
        for phase in plan.POLICY['phases']:
            offsets.extend(base+i/phase['rate'] for i in range(phase['seconds']*phase['rate']))
            base += phase['seconds']
    return offsets


def worker(root, round_index, lane, *, execute=False):
    if execute is not True:
        raise ContractError('worker requires explicit execution')
    case, receipt = context(root, round_index, lane, create=True)
    own = identity(receipt['test_only'])
    save(case/'worker-claim.json', dict(identity=own, replay_authorized=False))
    core = WorkloadCore(lane, len(schedule(receipt['test_only'])), execute=True)
    ready = save(case/'worker-ready.json', dict(identity=own, lane=lane, round=round_index,
                  implementation_sha256=receipt['artifact_sha256'], test_only=receipt['test_only']))
    error, start, end, cpu_begin, cpu_end = None, None, None, None, None
    resource_begin, window_begin = None, time.monotonic()
    try:
        observer_ready = wait(case/'observer-ready.json')
        if (observer_ready['worker_ready_sha256'] != ready['artifact_sha256'] or
                observer_ready['identity']['pid'] == own['pid'] or
                observer_ready['identity']['boot_id'] != own['boot_id']):
            raise ContractError('observer handshake identity differs')
        if receipt['requires_live_bindings']:
            bindings=wait(case/'bindings-ready.json')
            for role in ('worker','observer'):
                binding=read(case/(role+'-active.json'))
                if bindings[role+'_binding_sha256']!=binding['artifact_sha256']:
                    raise ContractError('active binding handshake differs')
        collection_ready=wait(case/'observer-collection-ready.json')
        if collection_ready['observer_ready_sha256']!=observer_ready['artifact_sha256']:
            raise ContractError('observer CPU-window readiness differs')
        start = time.monotonic()+.05
        save(case/'start.json', dict(start=start, worker_ready_sha256=ready['artifact_sha256']))
        cpu_begin = time.process_time()
        window_begin = time.monotonic()
        resource_begin = resources.sample()
        for offset in schedule(receipt['test_only']):
            core.step(start+offset)
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:160])
    finally:
        resource_end = resources.sample()
        end, cpu_end = time.monotonic(), time.process_time()
        save(case/'worker-done.json', dict(identity=own, start=start, begin=window_begin, end=end,
             resource_samples=[resource_begin or {'error':'window_not_started','pid':own['pid']},resource_end],
             cpu_seconds=None if cpu_begin is None else cpu_end-cpu_begin,
             error=error, implementation_sha256=receipt['artifact_sha256']))
        try:
            ack = wait(case/'observer-done.json')
            if ack['worker_identity'] != own or ack['error'] is not None:
                raise ContractError('observer failed or acknowledged another worker')
        except Exception as exc:
            if error is None: error = dict(type=type(exc).__name__, message=str(exc)[:160])
        # Keep process alive through observer completion; snapshots/persistence afterward.
        save(case/'raw-deliveries.json', dict(raws=core.raws[:core.delivered], identity=own,
             delivered_occurrences=core.delivered))
        try:
            snapshot = core.finish()
        except Exception as exc:
            save(case/'snapshot-failure.json', dict(type=type(exc).__name__, raw_retained=True))
            raise
        save(case/'worker-result.json', dict(core=snapshot, identity=own, error=error,
             start=start, end=end, persisted_at=time.monotonic(),
             test_only=receipt['test_only'], units_audited=False, probe_cost_accepted=False))
    if error or not snapshot['complete']:
        raise ContractError('worker lifecycle failed; evidence retained, no retry')


def observer(root, round_index, lane, *, execute=False):
    if execute is not True:
        raise ContractError('observer requires explicit execution')
    case, receipt = context(root, round_index, lane, create=True)
    own = identity(receipt['test_only'])
    save(case/'observer-claim.json', dict(identity=own, replay_authorized=False))
    try:
        ready = wait(case/'worker-ready.json')
        target = ready['identity']
        if (ready['implementation_sha256'] != receipt['artifact_sha256'] or ready['lane'] != lane
                or ready['round'] != round_index or target['pid'] == own['pid']
                or target['boot_id'] != own['boot_id']):
            raise ContractError('worker handshake identity differs')
        core = ObserverCore(lane, target, execute=True)
    except Exception as exc:
        save(case/'observer-startup-failure.json', dict(identity=own, error=type(exc).__name__))
        raise
    observer_ready=save(case/'observer-ready.json', dict(identity=own, worker_ready_sha256=ready['artifact_sha256']))
    if receipt['requires_live_bindings']:
        try:
            wait(case/'bindings-ready.json')
        except Exception as exc:
            save(case/'observer-binding-failure.json',dict(identity=own,error=type(exc).__name__))
            raise
    error, skips = None, []
    cpu_begin, begin = time.process_time(), time.monotonic()
    resource_begin = resources.sample()
    save(case/'observer-collection-ready.json',dict(observer_ready_sha256=observer_ready['artifact_sha256']))
    try:
        start_obj = wait(case/'start.json')
        if start_obj['worker_ready_sha256'] != ready['artifact_sha256']:
            raise ContractError('start handshake binding differs')
        origin = number(start_obj['start'])
        interval = .01 if receipt['test_only'] else plan.POLICY['observer_interval_seconds']
        tick = 0
        limit = time.monotonic()+40
        while time.monotonic() < limit:
            # Fixed grid; elapsed ticks are recorded, never burst-read as catch-up.
            next_tick = max(tick, math.ceil(max(0, time.monotonic()-origin)/interval))
            if next_tick > tick:
                skips.append(dict(first=tick, last=next_tick-1))
            core.tick(origin+next_tick*interval)
            tick = next_tick+1
            if (case/'worker-done.json').exists():
                done = wait(case/'worker-done.json', 1)
                if done['identity'] != target:
                    raise ContractError('worker done identity differs')
                if done['error'] is not None:
                    raise ContractError('worker reported failure')
                break
        else:
            raise ContractError('observer exceeded finite window')
    except Exception as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:160])
    resource_end = resources.sample()
    end, cpu_end = time.monotonic(), time.process_time()
    # Acknowledge before serialization, allowing raw persistence even on failure.
    save(case/'observer-done.json', dict(worker_identity=target, identity=own,
         begin=begin, end=end, cpu_seconds=cpu_end-cpu_begin, error=error,
         resource_samples=[resource_begin, resource_end]))
    snapshot = core.finish()
    save(case/'observer-result.json', dict(core=snapshot, identity=own, worker_identity=target,
         begin=begin, end=end, skipped_ticks=skips, error=error, test_only=receipt['test_only'],
         units_audited=False, probe_cost_accepted=False))
    if error or not snapshot['complete']:
        raise ContractError('observer lifecycle failed; evidence retained, no retry')


def verify_case(root, round_index, lane):
    case, receipt = context(root, round_index, lane)
    worker_result, observer_result = read(case/'worker-result.json'), read(case/'observer-result.json')
    done, ack = read(case/'worker-done.json'), read(case/'observer-done.json')
    ready, observer_ready = read(case/'worker-ready.json'), read(case/'observer-ready.json')
    start_obj = read(case/'start.json')
    if any(o['error'] is not None for o in (worker_result, observer_result, done, ack)):
        raise ContractError('failed lifecycle cannot become successful evidence')
    core = verify_core(worker_result['core'])
    raw = read(case/'raw-deliveries.json')
    if raw['raws'] != worker_result['core']['raws'] or raw['identity'] != worker_result['identity']:
        raise ContractError('raw persistence differs from core snapshot')
    own, target = worker_result['identity'], observer_result['worker_identity']
    if (own != target or ready['identity'] != own or observer_ready['identity'] != ack['identity']
            or observer_ready['worker_ready_sha256'] != ready['artifact_sha256']
            or start_obj['worker_ready_sha256'] != ready['artifact_sha256']
            or ready['implementation_sha256'] != receipt['artifact_sha256']
            or ready['test_only'] != receipt['test_only']
            or ready['lane'] != lane or ready['round'] != round_index
            or ack['worker_identity'] != own or done['identity'] != own
            or observer_result['identity'] != ack['identity'] or own['pid'] == ack['identity']['pid']
            or own['boot_id'] != ack['identity']['boot_id']
            or not observer_result['core']['complete'] or observer_result['core']['target'] != own
            or any(o[k] is not False for o in (worker_result, observer_result)
                   for k in ('units_audited', 'probe_cost_accepted'))):
        raise ContractError('lifecycle identity/authority differs')
    start = start_obj['start']
    expected = schedule(receipt['test_only'])
    if [r['deadline'] for r in worker_result['core']['rows']] != [start+v for v in expected]:
        raise ContractError('absolute workload schedule differs')
    if not ack['begin'] <= start <= done['end'] <= ack['end'] <= worker_result['persisted_at']:
        raise ContractError('observer does not enclose worker collection window')
    measured = {'worker':resources.summarize(done,own),
                'observer':resources.summarize(ack,observer_result['identity'])}
    from infra.stream.receive_loop_validity import CounterSample, counter_interval
    band = observer_result['core']
    verify_artifact_hash(band, 'report_sha256', 'observer core')
    previous, previous_counter = None, None
    for index, row in enumerate(band['rows']):
        if row['sequence'] != index or row['decision'] > row['wake']:
            raise ContractError('observer tick ordering differs')
        if previous is not None and row['deadline'] < previous:
            raise ContractError('observer catch-up tick differs')
        previous = row['wake']
        if (not math.isclose(row['requested_sleep'], max(0,row['deadline']-row['decision']), abs_tol=1e-9)
                or not math.isclose(row['deadline_lateness_seconds'], row['wake']-row['deadline'], abs_tol=1e-9)):
            raise ContractError('observer pacing arithmetic differs')
        if lane != 'full':
            if row['counter'] is not None:
                raise ContractError('control contains counter read')
            continue
        result = row['counter']
        if result is None or result['error'] is not None or result['sample'] is None:
            raise ContractError('counter result unavailable')
        obj = dict(result['sample']); obj['counters'] = tuple(tuple(v) for v in obj['counters'])
        sample = CounterSample(**obj); sample.validate()
        if any(getattr(sample, k) != v for k,v in own.items()):
            raise ContractError('counter sample identity differs')
        if sample.read_begin < row['wake'] or sample.read_end > ack['end']:
            raise ContractError('counter read outside observer observation window')
        if previous_counter is not None and counter_interval(previous_counter,sample)['status'] == 'unavailable':
            raise ContractError('counter reset or identity change')
        previous_counter = sample
    if lane == 'full' and band['reader']['reads'] != [r['counter'] for r in band['rows']]:
        raise ContractError('counter attempts differ from tick records')
    # Independently bound sideband encoding; raw occurrences have their own artifact.
    sideband = dict(worker_result['core']); sideband.pop('raws')
    if len(json.dumps([sideband,band],sort_keys=True,separators=(',',':')).encode()) > plan.POLICY['sideband_encoded_bytes_max_per_case']:
        raise ContractError('sideband byte bound exceeded')
    return dict(verified_occurrences=core['verified_occurrences'],
                test_only=receipt['test_only'], units_audited=False,
                origin_verified=False, probe_cost_accepted=False, measurements=measured)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('stage', 'worker', 'observer', 'verify'))
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--round', type=int, default=0)
    parser.add_argument('--lane', choices=plan.POLICY['lanes'], default='control')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.role == 'stage': stage(root)
    elif args.role == 'verify': print(json.dumps(verify_case(root, args.round, args.lane)))
    else: globals()[args.role](root, args.round, args.lane, execute=args.execute)


if __name__ == '__main__': main()
