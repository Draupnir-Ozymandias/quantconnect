"""Bounded native transport for unchanged comparison v2; no replay or tuning."""
import argparse
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import platform
import pwd
import re
import select
import sys
import time

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash, canonical_json
from infra.stream.recorder_absolute_wait import native
from infra.stream.recorder_wait_comparison_v2 import PLAN, SelectWait, collect_run, cancelled_run, error_text
from infra.stream.recorder_wait_comparison_audit import validate_run, evaluate
from infra.stream.recorder_wait_execution import validate_freeze
from infra.stream.recorder_wait_lifecycle import STAGE, unit_spec
from infra.stream.recorder_wait_production import Production, command, inspect_source, observe_runtime, PYTHON, SERVICES
from infra.stream.recorder_wait_compatibility_worker import load, publish

ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY_AUDIT = 'c5f7e48f1dc97f38966a0d5c7dcd51761cf2f1f5644c09b446c018bb85f3a0cb'
COMPATIBILITY_FREEZE = '8fd4a9557b16bc46fad770b5a9cd1279ce63390e5ab92624addee248c4c690c1'
LINUX_TESTS = 1093
LINUX_SKIPS = 1  # unchanged Python 3.10+ stdlib-module-inventory guard


def require(value, message):
    if not value:
        raise ContractError(message)


def prerequisite(audit, previous, frozen):
    """Admit only the independently reviewed smoke, unchanged runtime/old code."""
    validate_freeze(previous)
    validate_freeze(frozen)
    verify_artifact_hash(audit, 'audit_sha256', 'native compatibility audit')
    require(audit['audit_sha256'] == COMPATIBILITY_AUDIT
            and previous['freeze_sha256'] == COMPATIBILITY_FREEZE
            and audit['freeze_sha256'] == previous['freeze_sha256'], 'reviewed smoke identity differs')
    require(audit.get('native_origin_verified') is True and audit.get('compatibility_verified') is True
            and audit.get('private_units_inactive') is True and audit.get('public_unchanged') is True
            and audit.get('source_runtime_matches') is True, 'verified smoke prerequisite required')
    require(previous['runtime'] == frozen['runtime'], 'reviewed runtime must remain unchanged')
    for name, digest in previous['sources'].items():
        if name.endswith('.py'):
            require(frozen['sources'].get(name) == digest, 'reviewed implementation changed: '+name)
    for name in ('infra/stream/recorder_wait_comparison_native.py', 'tests/test_recorder_wait_comparison_native.py'):
        require(name in frozen['sources'], 'comparison execution source absent')
    return True


def comparison_spec(stage, index):
    require(type(index) is int and index in (0, 1), 'declared run index required')
    spec = unit_spec(stage, 'compatibility')
    spec['unit'] = spec['unit'].removesuffix('-compatibility')+'-comparison-'+str(index)
    spec['run_index'] = index
    spec['properties']['ReadWritePaths'] = stage+'/evidence/run-'+str(index)
    return spec


def bind_ready(ready, spec, frozen, binding):
    verify_artifact_hash(ready, 'ready_sha256', 'comparison readiness')
    identity = ready['identity']
    require(ready.get('unit') == spec['unit'] and type(ready.get('run_index')) is int
            and ready['run_index'] == spec['run_index']
            and ready.get('freeze_sha256') == frozen['freeze_sha256']
            and ready.get('plan_sha256') == payload_hash(PLAN), 'readiness run/source/plan differs')
    require(type(identity.get('pid')) is int and identity['pid'] > 0
            and identity.get('cgroup') == '/system.slice/'+spec['unit']+'.service'
            and type(identity.get('boot_id')) is str and bool(identity['boot_id'])
            and type(identity.get('process_start_id')) is str and bool(identity['process_start_id']), 'readiness identity invalid')
    require(binding == dict(unit=spec['unit'], identity=identity, active=True,
                            observed_properties=spec['properties']), 'live comparison binding differs')
    release = dict(ready_sha256=ready['ready_sha256'], freeze_sha256=frozen['freeze_sha256'],
                   binding_sha256=payload_hash(binding))
    release['release_sha256'] = payload_hash(release)
    return release


def validate_envelope(envelope, result, ready, release, frozen):
    verify_artifact_hash(envelope, 'envelope_sha256', 'comparison envelope')
    validate_run(result)
    require(envelope.get('schema_version') == 'qcrl.wait_comparison_native_envelope.v1'
            and envelope.get('run_sha256') == result['run_sha256']
            and envelope.get('run_index') == result['run_index']
            and envelope.get('identity') == ready['identity']
            and envelope.get('ready_sha256') == ready['ready_sha256']
            and envelope.get('release_sha256') == release['release_sha256']
            and envelope.get('freeze_sha256') == frozen['freeze_sha256'], 'native envelope binding differs')
    for key in ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'):
        require(envelope.get(key) is False, 'envelope authority remains false')
    return envelope


def failed_run(index, exc):
    # A native setup/termination fault supplies no invented epoch or observed cells.
    result = dict(schema_version='qcrl.wait_comparison_run.v2', run_index=index,
                  plan_sha256=payload_hash(PLAN), epoch_ns=None, baseline=[], rows=[],
                  fatal_error=error_text(exc), cancelled=False, native_origin_verified=False,
                  acceptance_demonstrated=False, orders_authorized=False)
    result['run_sha256'] = payload_hash(result)
    return validate_run(result)


class WaitInterrupted(Exception):
    """Record default-handler KeyboardInterrupt without retry or handler changes."""


def retain_interrupts(function):
    def call(*args):
        try:
            return function(*args)
        except KeyboardInterrupt as exc:
            raise WaitInterrupted('KeyboardInterrupt:'+str(exc)) from exc
    return call


def worker(stage, index, *, execute=False):
    stage = Path(stage)
    require(execute is True and platform.system() == 'Linux'
            and os.geteuid() == pwd.getpwnam('qcrl').pw_uid
            and re.fullmatch(STAGE, str(stage)) and stage.resolve(strict=True) == stage
            and ROOT == stage/'source' and os.path.abspath(sys.executable) == PYTHON,
            'canonical explicit qcrl Linux comparison worker required')
    spec = comparison_spec(str(stage), index)
    evidence = stage/'evidence'/('run-'+str(index))
    require(evidence.resolve(strict=True) == evidence, 'canonical run evidence required')
    frozen = validate_freeze(load(stage/'execution-freeze.json'))
    prerequisite(load(stage/'compatibility-audit.json'), load(stage/'compatibility-freeze.json'), frozen)
    sources, commit = inspect_source(ROOT)
    runtime = observe_runtime(load(stage/'runtime-review.json'), review_source=stage/'select-review-source.c', execute=True)
    require(sources == frozen['sources'] and commit == frozen['source_commit'] and runtime == frozen['runtime'],
            'comparison worker source/runtime differs')
    if index == 1:
        prior = stage/'evidence'/'run-0'
        previous = validate_run(load(prior/'run.json'))
        require(previous['run_index'] == 0 and previous['fatal_error'] is None,
                'run one requires published nonfatal run zero')
        previous_ready, previous_release = load(prior/'ready.json'), load(prior/'release.json')
        active = load(prior/'active-binding.json')
        require(bind_ready(previous_ready, comparison_spec(str(stage), 0), frozen, active['binding']) == previous_release,
                'prior run release differs')
        validate_envelope(load(prior/'run-envelope.json'), previous, previous_ready, previous_release, frozen)
    from infra.stream.recorder_application_resources import LinuxReader
    from infra.stream.recorder_wake_worker import context
    reader = LinuxReader(execute=True)
    ready = dict(unit=spec['unit'], run_index=index, identity=reader.expected,
                 freeze_sha256=frozen['freeze_sha256'], plan_sha256=payload_hash(PLAN),
                 context_before=context(reader))
    ready['ready_sha256'] = payload_hash(ready)
    publish(evidence/'ready.json', ready)
    deadline = time.monotonic()+15
    while not (evidence/'release.json').exists() and time.monotonic() < deadline:
        time.sleep(.01)
    require(time.monotonic() < deadline, 'release deadline missed; no late adoption')
    release = load(evidence/'release.json')
    verify_artifact_hash(release, 'release_sha256', 'comparison release')
    require(release['ready_sha256'] == ready['ready_sha256']
            and release['freeze_sha256'] == frozen['freeze_sha256'], 'comparison release differs')
    binding = dict(unit=spec['unit'], identity=reader.expected, active=True, observed_properties=spec['properties'])
    require(release['binding_sha256'] == payload_hash(binding), 'release live binding differs')
    try:
        absolute = native(execute=True)
        clock = retain_interrupts(time.monotonic_ns)
        absolute.clock_ns = clock
        absolute.syscall = retain_interrupts(absolute.syscall)
        relative = SelectWait(clock_ns=clock, select_call=retain_interrupts(select.select))
    except (Exception, KeyboardInterrupt) as exc:
        result = failed_run(index, exc)
    else:
        # An escaping BaseException after collection begins must not invent a null-epoch setup receipt.
        result = collect_run(run_index=index, clock_ns=clock,
                             select_wait=relative, absolute_wait=absolute, execute=True)
    validate_run(result)
    # Publication remains after collection. Journal retains collected rows if file publication fails.
    print('QCRL_COMPARISON_RUN='+canonical_json(result), flush=True)
    publish(evidence/'run.json', result)
    envelope = dict(schema_version='qcrl.wait_comparison_native_envelope.v1', run_index=index,
                    run_sha256=result['run_sha256'], ready_sha256=ready['ready_sha256'],
                    release_sha256=release['release_sha256'], freeze_sha256=frozen['freeze_sha256'],
                    identity=reader.expected, context_after=context(reader), native_origin_verified=False,
                    acceptance_demonstrated=False, orders_authorized=False)
    envelope['envelope_sha256'] = payload_hash(envelope)
    validate_envelope(envelope, result, ready, release, frozen)
    publish(evidence/'run-envelope.json', envelope)


def completion(captured, spec):
    require(captured == dict(unit=spec['unit'], result='success', exec_status=0,
                            substate='exited', observed_properties=spec['properties']),
            'unit completion/effective limits differ')


def regression_population(journal):
    counts = re.findall(r'\bRan (\d+) tests in ([\d.]+)s', journal)
    outcomes = re.findall(r'\bOK(?: \(skipped=(\d+)\))?$', journal, re.MULTILINE)
    require(bool(counts) and bool(outcomes), 'regression journal success missing')
    result = dict(discovered=int(counts[-1][0]), seconds=counts[-1][1], skipped=int(outcomes[-1] or 0))
    require(result['discovered'] == LINUX_TESTS and result['skipped'] == LINUX_SKIPS,
            'frozen Linux regression population differs')
    return result


def unknown_cells(runs):
    cells = []
    by_index = {run['run_index']: run for run in runs}
    for index in (0, 1):
        run = by_index.get(index)
        rows = {} if run is None else {(row['arm'], row['interval_ns']): row for row in run['rows']}
        for arm in ('select', 'absolute'):
            for interval in PLAN['interval_ns']:
                row = rows.get((arm, interval))
                obs = None if row is None else row['observation']
                if obs is None or obs['status'] != 'observed' or row['error'] is not None:
                    if run is None:
                        reason = 'unavailable_validated_run_receipt'
                    elif row is None:
                        reason = run['fatal_error']
                    else:
                        reason = row['error'] or (obs['error'] if obs else run['fatal_error'])
                    cells.append(dict(run_index=index, arm=arm, interval_ns=interval, reason=reason))
    return cells


def execute_pair(stage, frozen, ops, *, execute=False):
    """Injected finite launcher; native faults retain missing cells without fabricating runs."""
    require(execute is True, 'explicit comparison launch required')
    validate_freeze(frozen)
    checked = ops.preflight(stage, deepcopy(frozen))
    expected = dict(fresh_stage=True, clean_source=True, source_freeze_matches=True,
                    runtime_freeze_matches=True, canonical_qcrl_owner=True, fixed_interpreter=True,
                    disk_reserve_over_4_gib=True, public_prerequisites_match=True, private_units_absent=True)
    require(checked == expected and all(value is True for value in checked.values()), 'comparison preflight differs')
    before = ops.public_state()
    ops.claim(stage, frozen['freeze_sha256'])
    started, captured, stopped, runs = [], set(), set(), []
    report = dict(schema_version='qcrl.wait_comparison_launch.v1', stage=stage, freeze_sha256=frozen['freeze_sha256'],
                  plan_sha256=payload_hash(PLAN), complete=False, error=None, preservation_errors=[],
                  stop_reason=None, summary=None, unknown_cells=[], public_before=before, public_after=None,
                  native_origin_verified=False, acceptance_demonstrated=False, orders_authorized=False)
    try:
        spec = unit_spec(stage, 'tests')
        started.append(spec)
        ops.start(spec)
        ops.finish(spec['unit'], timeout_seconds=240)
        captured.add(spec['unit'])
        completion(ops.capture(spec['unit'], max_journal_bytes=65536), spec)
        ops.stop(spec['unit'])
        stopped.add(spec['unit'])
        for index in (0, 1):
            if index == 1 and runs[0]['fatal_error'] is not None:
                result = cancelled_run(1)
                ops.cancel(result)
                runs.append(result)
                report['stop_reason'] = 'run_zero_fatal_second_cancelled'
                break
            require(ops.recheck(stage, frozen) == dict(clean_source=True, source_freeze_matches=True,
                                                     runtime_freeze_matches=True), 'source/runtime changed between units')
            require(ops.public_state() == before, 'public state changed; no restoration')
            spec = comparison_spec(stage, index)
            ops.activate(index)
            started.append(spec)
            ops.start(spec)
            ready = ops.ready(spec['unit'], timeout_seconds=12, max_bytes=262144)
            release = bind_ready(ready, spec, frozen, ops.bind(spec['unit'], ready))
            ops.release(spec['unit'], release)
            ops.finish(spec['unit'], timeout_seconds=240)
            captured.add(spec['unit'])
            completion(ops.capture(spec['unit'], max_journal_bytes=65536), spec)
            result, envelope = ops.comparison_result(index)
            require(result.get('run_index') == index, 'published run index differs')
            validate_envelope(envelope, result, ready, release, frozen)
            runs.append(result)
            ops.stop(spec['unit'])
            stopped.add(spec['unit'])
        report['summary'] = evaluate(runs)
        if runs[-1]['fatal_error'] is not None and report['stop_reason'] is None:
            report['stop_reason'] = 'run_one_fatal_remaining_attempts_stopped'
        report['complete'] = True  # transport completion, separate from scientific completeness/fatal state
    except Exception as exc:
        report['error'] = error_text(exc)
        report['stop_reason'] = 'native_gate_fault_no_further_unit'
    finally:
        for spec in reversed(started):
            unit = spec['unit']
            ops.select_evidence(spec)
            if unit not in captured:
                captured.add(unit)
                try:
                    ops.capture(unit, max_journal_bytes=65536)
                except Exception as exc:
                    report['preservation_errors'].append(dict(unit=unit, capture_error=error_text(exc)))
            if unit not in stopped:
                try:
                    ops.stop(unit)
                except Exception as exc:
                    report['preservation_errors'].append(dict(unit=unit, stop_error=error_text(exc)))
        try:
            report['public_after'] = ops.public_state()
            require(report['public_after'] == before, 'public drift; no restoration')
            require(ops.recheck(stage, frozen) == dict(clean_source=True, source_freeze_matches=True,
                                                     runtime_freeze_matches=True), 'final source/runtime drift')
        except Exception as exc:
            report['error'] = report['error'] or error_text(exc)
        report['complete'] = report['complete'] and report['error'] is None and not report['preservation_errors']
        # Every planned cell without a validated published observation remains explicitly unknown.
        report['unknown_cells'] = unknown_cells(runs)
        report['launch_sha256'] = payload_hash(report)
        ops.publish_comparison(report)
    return report


class ComparisonProduction(Production):
    def preflight(self, stage, frozen):
        prerequisite(load(self.root/'compatibility-audit.json'), load(self.root/'compatibility-freeze.json'), frozen)
        for name in ('compatibility-audit.json', 'compatibility-freeze.json'):
            command(['sudo', '-u', 'qcrl', 'test', '-r', str(self.root/name)], execute=True)
        return super().preflight(stage, frozen)

    def claim(self, stage, freeze_hash):
        super().claim(stage, freeze_hash)
        for name in ('compatibility-audit.json', 'compatibility-freeze.json'):
            publish(self.evidence/name, load(self.root/name))

    def activate(self, index):
        comparison_spec(str(self.root), index)
        path = self.root/'evidence'/('run-'+str(index))
        require(not path.exists() and not path.is_symlink(), 'fresh run directory required')
        command(['install', '-d', '-o', 'qcrl', '-g', 'qcrl', '-m', '750', str(path)], execute=True)
        self.evidence = path

    def select_evidence(self, spec):
        self.evidence = self.root/'evidence'
        if 'run_index' in spec:
            self.evidence = self.evidence/('run-'+str(spec['run_index']))

    def start(self, spec):
        if 'run_index' not in spec:
            return super().start(spec)
        require(spec == comparison_spec(str(self.root), spec['run_index']), 'only fixed comparison units may start')
        self.specs[spec['unit']] = spec
        command(['systemd-run', '--unit='+spec['unit'], '--working-directory='+spec['working_directory'],
                 *['--property='+key+'='+value for key, value in spec['properties'].items()], PYTHON,
                 '-m', 'infra.stream.recorder_wait_comparison_native', '--root', str(self.root),
                 '--worker', '--run-index', str(spec['run_index']), '--execute'], execute=True)

    def comparison_result(self, index):
        return load(self.evidence/'run.json'), load(self.evidence/'run-envelope.json')

    def capture(self, unit, *, max_journal_bytes):
        result = super().capture(unit, max_journal_bytes=max_journal_bytes)
        if self.specs[unit]['role'] == 'tests':
            path = self.evidence/(unit+'-journal.txt')
            require(not path.is_symlink() and path.is_file(), 'regular regression journal required')
            with path.open('rb') as handle:
                data = handle.read(max_journal_bytes+1)
            require(len(data) <= max_journal_bytes, 'regression journal exceeds cap')
            regression_population(data.decode('utf-8'))
        return result

    def cancel(self, result):
        validate_run(result)
        require(result == cancelled_run(1), 'only declared fatal cancellation may publish')
        publish(self.root/'evidence'/'cancelled-run-1.json', result)

    def publish_comparison(self, report):
        self.evidence = self.root/'evidence'
        if report['summary'] is not None:
            publish(self.evidence/'summary.json', report['summary'])
        publish(self.evidence/'comparison-launch.json', report)
        files = {}
        for path in sorted(self.evidence.rglob('*')):
            require(not path.is_symlink(), 'evidence symlink refused')
            if path.is_dir():
                continue
            require(path.is_file() and len(files) < 32 and path.stat().st_size <= 4*1024*1024,
                    'bounded regular comparison evidence required')
            data = path.read_bytes()
            require(len(data) <= 4*1024*1024, 'evidence grew beyond cap')
            files[str(path.relative_to(self.evidence))] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        inventory = dict(schema_version='qcrl.wait_comparison_origin_inventory.v1', files=files,
                         freeze_sha256=self.frozen['freeze_sha256'], native_origin_verified=False)
        inventory['inventory_sha256'] = payload_hash(inventory)
        publish(self.root/'origin-inventory.json', inventory)


def audit_retained(root):
    """Offline bytes/identity/arithmetic verification; hashes alone cannot prove origin."""
    root = Path(root)
    evidence = root/'evidence'
    frozen = validate_freeze(load(evidence/'execution-freeze.json'))
    prerequisite(load(evidence/'compatibility-audit.json'), load(evidence/'compatibility-freeze.json'), frozen)
    inventory = load(root/'origin-inventory.json')
    verify_artifact_hash(inventory, 'inventory_sha256', 'comparison inventory')
    require(inventory.get('schema_version') == 'qcrl.wait_comparison_origin_inventory.v1'
            and inventory.get('freeze_sha256') == frozen['freeze_sha256']
            and inventory.get('native_origin_verified') is False, 'origin inventory binding differs')
    actual = {}
    for path in sorted(evidence.rglob('*')):
        require(not path.is_symlink(), 'retained evidence symlink refused')
        if path.is_dir():
            continue
        require(path.is_file() and path.stat().st_size <= 4*1024*1024 and len(actual) < 32,
                'retained evidence bounds differ')
        data = path.read_bytes()
        require(len(data) <= 4*1024*1024, 'retained evidence grew beyond cap')
        actual[str(path.relative_to(evidence))] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    require(actual == inventory['files'], 'retained file population/bytes differ')
    report = load(evidence/'comparison-launch.json')
    verify_artifact_hash(report, 'launch_sha256', 'comparison launch')
    require(report['freeze_sha256'] == frozen['freeze_sha256'] and report['plan_sha256'] == payload_hash(PLAN),
            'launch source/plan differs')
    for key in ('native_origin_verified', 'acceptance_demonstrated', 'orders_authorized'):
        require(report.get(key) is False, 'launch authority differs')
    require(report.get('schema_version') == 'qcrl.wait_comparison_launch.v1'
            and type(report.get('complete')) is bool and re.fullmatch(STAGE, report.get('stage', '')),
            'launch schema/stage differs')
    require(report['public_before'].get('collectors') == {
        name: 'active' if name.endswith('.timer') else 'inactive' for name in SERVICES}, 'public prerequisites differ')
    test_summary = None
    checked, unknown_context, exit_us, previous_process = [], [], None, None
    if report['complete']:
        require(report['error'] is None and not report['preservation_errors']
                and report['public_before'] == report['public_after'], 'complete launch retained faults/drift')
        from infra.stream.recorder_wait_production import verified_properties
        tests = unit_spec(report['stage'], 'tests')
        test_props = dict(line.split('=', 1) for line in (evidence/(tests['unit']+'-properties.txt')).read_text().splitlines() if '=' in line)
        verified_properties(test_props, tests)
        require(test_props['Id'] == tests['unit']+'.service' and test_props['Result'] == 'success'
                and test_props['ExecMainStatus'] == '0' and test_props['SubState'] == 'exited', 'regression unit gate differs')
        journal = (evidence/(tests['unit']+'-journal.txt')).read_text()
        test_summary = regression_population(journal)
        exit_us = int(test_props['ExecMainExitTimestampMonotonic'])
        for index in (0, 1):
            if index == 1 and checked[0]['fatal_error'] is not None:
                result = load(evidence/'cancelled-run-1.json')
                require(result == cancelled_run(1), 'cancelled run receipt differs')
                require(not (evidence/'run-1').exists(), 'unit/evidence after fatal run zero')
                checked.append(result)
                break
            runroot = evidence/('run-'+str(index))
            result, envelope = load(runroot/'run.json'), load(runroot/'run-envelope.json')
            ready, release, active = load(runroot/'ready.json'), load(runroot/'release.json'), load(runroot/'active-binding.json')
            verify_artifact_hash(release, 'release_sha256', 'comparison release')
            spec = comparison_spec(report['stage'], index)
            require(bind_ready(ready, spec, frozen, active['binding']) == release
                    and active['binding_sha256'] == release['binding_sha256'], 'retained release/live binding differs')
            validate_envelope(envelope, result, ready, release, frozen)
            verified_properties(active['raw_properties'], spec)
            identity = ready['identity']
            process = (identity['boot_id'], identity['pid'], identity['process_start_id'])
            require(process != previous_process, 'comparison worker process was reused')
            previous_process = process
            raw = active['raw_properties']
            require(raw['Id'] == spec['unit']+'.service' and raw['ActiveState'] == 'active'
                    and raw['SubState'] == 'running' and raw['MainPID'] == raw['ExecMainPID'] == str(identity['pid'])
                    and raw['ControlGroup'] == identity['cgroup'] and active['sample']['owner'] == identity,
                    'retained active PID/cgroup differs')
            for label, context in (('before', ready['context_before']), ('after', envelope['context_after'])):
                require(context['resource']['owner'] == identity and context['resource']['effective_quota'] == .75,
                        'retained worker resource identity/quota differs')
                group = context['resource']['ancestry'][0]
                require(group['cpu_max'] == '75000 100000' and group['memory_max'] == '536870912',
                        'retained worker effective cpu/memory limits differ')
                for name, value in context['files'].items():
                    if value['status'] != 'observed':
                        unknown_context.append(dict(run_index=index, context=label, path=name, observation=value))
            props = dict(line.split('=', 1) for line in (runroot/(spec['unit']+'-properties.txt')).read_text().splitlines() if '=' in line)
            require((runroot/(spec['unit']+'-journal.txt')).is_file(), 'comparison journal absent')
            verified_properties(props, spec)
            require(props['Id'] == spec['unit']+'.service' and props['Result'] == 'success'
                    and props['ExecMainStatus'] == '0' and props['SubState'] == 'exited'
                    and props['ExecMainPID'] == str(identity['pid']), 'retained completion differs')
            start, end = int(props['ExecMainStartTimestampMonotonic']), int(props['ExecMainExitTimestampMonotonic'])
            require(end >= start and (exit_us is None or start >= exit_us), 'native runs overlap/regress')
            if result['epoch_ns'] is not None:
                require(start*1000 <= result['baseline'][0]['before_ns'] <= result['epoch_ns'] <= end*1000,
                        'run clock outside unit lifetime')
                for row in result['rows']:
                    if row['observation'] and row['observation']['after_ns'] is not None:
                        require(row['observation']['after_ns'] <= end*1000, 'wait after unit lifetime')
            exit_us = end
            checked.append(result)
        require(evaluate(checked) == report['summary'] == load(evidence/'summary.json'), 'summary differs from retained runs')
        require(unknown_cells(checked) == report['unknown_cells'], 'unknown cell population differs')
    return dict(structure_verified=True, transport_complete=report['complete'],
                comparison_complete=report['summary']['comparison_complete'] if report['summary'] else False,
                unknown_cells=report['unknown_cells'], unknown_context=unknown_context, linux_regression=test_summary,
                select_internal_retry_count=None, native_origin_verified=False,
                acceptance_demonstrated=False, orders_authorized=False)


def launch(stage, *, execute=False):
    require(execute is True and platform.system() == 'Linux' and os.geteuid() == 0,
            'explicit root Linux comparison execution required')
    stage = Path(stage)
    require(re.fullmatch(STAGE, str(stage)), 'private comparison stage required')
    frozen = validate_freeze(load(stage/'execution-freeze.json'))
    return execute_pair(str(stage), frozen, ComparisonProduction(stage, frozen, execute=True), execute=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--run-index', type=int)
    args = parser.parse_args()
    if args.worker:
        worker(args.root, args.run_index, execute=args.execute)
    else:
        require(args.run_index is None, 'run index is worker-only')
        report = launch(args.root, execute=args.execute)
        require(report['complete'], 'comparison launch incomplete; retained, no replay')


if __name__ == '__main__':
    main()
