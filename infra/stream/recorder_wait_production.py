"""Bounded private Linux adapters for the declared compatibility smoke only."""
import argparse
import ctypes
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import platform
import pwd
import selectors
import select
import signal
import shutil
import subprocess
import sys
import time

from execution_truth.contracts import ContractError, canonical_json, payload_hash, verify_artifact_hash
from infra.stream.recorder_absolute_wait import Timespec
from infra.stream.recorder_wait_execution import SELECT_POLICY, source_inventory, validate_runtime, validate_freeze
from infra.stream.recorder_wait_lifecycle import STAGE, rehearse, unit_spec
from infra.stream.recorder_wait_compatibility_worker import load, publish

ROOT = Path(__file__).resolve().parents[2]
PYTHON = '/opt/qcrl-stream/venv/bin/python'
SERVICES = ('qcrl-collector.timer', 'qcrl-stream-pilot.service', 'qcrl-stream-observer.service')


class CommandError(ContractError):
    def __init__(self, message, output):
        super().__init__(message)
        self.output = output


def command(args, *, timeout=10, cap=262144, execute=False):
    """Drain a pipe incrementally; cap and timeout kill only this helper group."""
    if execute is not True:
        raise ContractError('explicit bounded helper execution required')
    if (type(args) is not list or not args or any(type(arg) is not str for arg in args)
            or type(cap) is not int or not 0 < cap <= 262144
            or type(timeout) not in (int, float) or not 0 < timeout <= 30):
        raise ContractError('bounded helper arguments required')
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    data = bytearray()
    deadline = time.monotonic()+timeout
    try:
        with selectors.DefaultSelector() as watcher:
            watcher.register(proc.stdout, selectors.EVENT_READ)
            while watcher.get_map():
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise CommandError('helper deadline exceeded', bytes(data))
                for key, _ in watcher.select(min(remaining, .1)):
                    block = os.read(key.fileobj.fileno(), min(65536, cap-len(data)+1))
                    if not block:
                        watcher.unregister(key.fileobj)
                        continue
                    if len(data)+len(block) > cap:
                        data.extend(block[:cap-len(data)])
                        raise CommandError('helper output cap exceeded', bytes(data))
                    data.extend(block)
        code = proc.wait(timeout=max(.001, deadline-time.monotonic()))
        if code != 0:
            raise CommandError('helper nonzero exit '+str(code), bytes(data))
        try:
            return bytes(data).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise CommandError('helper output is not UTF-8', bytes(data)) from exc
    except subprocess.TimeoutExpired as exc:
        raise CommandError('helper exit deadline exceeded', bytes(data)) from exc
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=2)
        proc.stdout.close()


def digest(path, cap=64*1024*1024):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or path.stat().st_size > cap:
        raise ContractError('bounded regular binary/source required')
    value, size = hashlib.sha256(), 0
    with path.open('rb') as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            size += len(block)
            if size > cap:
                raise ContractError('binary/source grew beyond cap')
            value.update(block)
    return value.hexdigest()


def inspect_source(source):
    source = Path(source)
    if source.resolve(strict=True) != source:
        raise ContractError('canonical source checkout required')
    prefix = ['sudo', '-u', 'qcrl'] if os.geteuid() == 0 else []
    git = prefix+['git', '-C', str(source)]
    if command(git+['status', '--porcelain'], execute=True).strip():
        raise ContractError('clean committed source required')
    names = command(git+['ls-files', '-z'], execute=True).rstrip('\0').split('\0')
    commit = command(git+['rev-parse', 'HEAD'], execute=True).strip()
    return source_inventory(source, names), commit


def observe_runtime(review, *, review_source, execute=False):
    if execute is not True or platform.system() != 'Linux':
        raise ContractError('explicit Linux runtime inspection required')
    verify_artifact_hash(review, 'review_sha256', 'installed select review')
    if (review.get('schema_version') != 'qcrl.installed_select_review.v1'
            or review.get('installed_binary_verified') is not True
            or review.get('distribution_source_verified') is not True
            or review.get('retry_policy') != SELECT_POLICY):
        raise ContractError('verified installed select/source review required')
    with Path('/proc/self/maps').open('rb') as handle:
        maps = handle.read(262145)
    if len(maps) > 262144:
        raise ContractError('process maps exceeds cap')
    libraries = {line.split()[-1] for line in maps.decode('ascii').splitlines()
                 if line.split() and line.split()[-1].startswith('/') and '/libc.so' in line.split()[-1]}
    if len(libraries) != 1:
        raise ContractError('unique loaded libc required')
    select_path = getattr(select, '__file__', None)
    if select_path is None:
        if getattr(select.__spec__, 'origin', None) != 'built-in' or 'select' not in sys.builtin_module_names:
            raise ContractError('select binary origin unavailable')
        select_path, binary_kind = sys.executable, 'builtin'
    else:
        binary_kind = 'extension'
    if review.get('binary_kind') != binary_kind:
        raise ContractError('select binary kind differs from review')
    select_hash = digest(select_path)
    source_hash = digest(review_source, cap=4*1024*1024)
    if review.get('select_binary_sha256') != select_hash or review.get('source_sha256') != source_hash:
        raise ContractError('installed select/source bytes differ from review')
    library = ctypes.CDLL(None)
    function = library.clock_nanosleep
    function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(Timespec), ctypes.c_void_p]
    function.restype = ctypes.c_int
    handlers = {}
    for name in ('SIGINT', 'SIGTERM', 'SIGHUP', 'SIGALRM', 'SIGUSR1', 'SIGUSR2', 'SIGPIPE'):
        handler = signal.getsignal(getattr(signal, name))
        handlers[name] = int(handler) if isinstance(handler, int) else handler.__module__+'.'+handler.__name__
    info = time.get_clock_info('monotonic')
    runtime = dict(system=platform.system(), libc=platform.libc_ver()[0], libc_version=platform.libc_ver()[1],
                   python=platform.python_version(), machine=platform.machine(), kernel=platform.release(),
                   gil_enabled=not bool(sysconfig_value('Py_GIL_DISABLED')),
                   long_bits=ctypes.sizeof(ctypes.c_long)*8, pointer_bits=ctypes.sizeof(ctypes.c_void_p)*8,
                   timespec_size=ctypes.sizeof(Timespec), tv_sec_offset=Timespec.tv_sec.offset,
                   tv_nsec_offset=Timespec.tv_nsec.offset, clock_monotonic_id=getattr(time, 'CLOCK_MONOTONIC', None),
                   timer_abstime=1, monotonic_implementation=info.implementation, monotonic_resolution=str(info.resolution),
                   clock_nanosleep_symbol='clock_nanosleep', argtypes=['c_int', 'c_int', 'POINTER(Timespec)', 'c_void_p'],
                   restype='c_int', select_retry_policy=SELECT_POLICY,
                   signal_context_policy='observe_existing_handlers_no_changes', signal_handlers=canonical_json(handlers),
                   python_binary_sha256=digest(sys.executable), libc_binary_sha256=digest(next(iter(libraries))),
                   select_binary_sha256=select_hash, select_binary_kind=binary_kind, select_review_source_sha256=source_hash,
                   select_review_receipt_sha256=review['review_sha256'])
    return validate_runtime(runtime)


def sysconfig_value(name):
    import sysconfig
    return sysconfig.get_config_var(name)


def seconds(value):
    import re
    scales = {'us': Decimal('.000001'), 'ms': Decimal('.001'), 's': Decimal(1), 'min': Decimal(60)}
    parts = re.findall(r'([0-9]+(?:\.[0-9]+)?)(us|ms|min|s)', value)
    if not parts or ''.join(number+unit for number, unit in parts) != value.replace(' ', ''):
        raise ContractError('unsupported systemd duration')
    return sum(Decimal(number)*scales[unit] for number, unit in parts)


def verified_properties(raw, spec):
    expected = spec['properties']
    for key in ('User', 'Group', 'TasksMax', 'RemainAfterExit', 'NoNewPrivileges', 'PrivateTmp', 'ProtectSystem', 'ProtectHome'):
        if raw.get(key) != expected[key]:
            raise ContractError('effective property differs: '+key)
    if (raw.get('MemoryMax') != '536870912' or seconds(raw.get('CPUQuotaPerSecUSec', '')) != Decimal('.75')
            or seconds(raw.get('RuntimeMaxUSec', '')) != 240):
        raise ContractError('effective limits differ')
    for key in ('ReadWritePaths', 'ReadOnlyPaths', 'InaccessiblePaths', 'RestrictAddressFamilies'):
        if {v.lstrip('-') for v in raw.get(key, '').split()} != {v.lstrip('-') for v in expected[key].split()}:
            raise ContractError('effective isolation differs: '+key)
    deny = set(raw.get('IPAddressDeny', '').split())
    if deny not in ({'any'}, {'0.0.0.0/0', '::/0'}):
        raise ContractError('effective network deny differs')
    allow = set(raw.get('IPAddressAllow', '').split())
    if allow != ({'127.0.0.1/32'} if spec['role'] == 'tests' else set()):
        raise ContractError('effective network allow differs')
    return deepcopy_dict(expected)


def deepcopy_dict(value):
    from copy import deepcopy
    return deepcopy(value)


class Production:
    def __init__(self, root, frozen, *, execute=False):
        import re
        self.root, self.frozen = Path(root), validate_freeze(frozen)
        if (execute is not True or platform.system() != 'Linux' or os.geteuid() != 0
                or not re.fullmatch(STAGE, str(self.root))
                or self.root.resolve(strict=True) != self.root or ROOT != self.root/'source'
                or os.path.abspath(sys.executable) != PYTHON):
            raise ContractError('explicit canonical root Linux stage/interpreter required')
        self.evidence = self.root/'evidence'
        self.specs = {}

    def recheck(self, stage, frozen):
        sources, commit = inspect_source(self.root/'source')
        runtime = observe_runtime(load(self.root/'runtime-review.json'), review_source=self.root/'select-review-source.c', execute=True)
        return dict(clean_source=True, source_freeze_matches=sources == frozen['sources'] and commit == frozen['source_commit'],
                    runtime_freeze_matches=runtime == frozen['runtime'])

    def preflight(self, stage, frozen):
        for name in ('evidence', 'launch-claim.json', 'origin-inventory.json'):
            if (self.root/name).exists() or (self.root/name).is_symlink():
                raise ContractError('fresh stage required; never replay or adopt evidence')
        for name in ('execution-freeze.json', 'runtime-review.json', 'select-review-source.c'):
            path = self.root/name
            if path.is_symlink() or not path.is_file():
                raise ContractError('regular staged controls required')
            command(['sudo', '-u', 'qcrl', 'test', '-r', str(path)], execute=True)
        command(['sudo', '-u', 'qcrl', 'test', '-x', str(self.root)], execute=True)
        checked = self.recheck(stage, frozen)
        tag = 'qcrl-wait-'+self.root.name[len('recorder-wait-'):]
        if command(['systemctl', 'list-units', '--all', '--full', '--no-legend', tag+'-*'], execute=True).strip():
            raise ContractError('private unit prefix already present')
        state = self.public_state()
        return dict(checked, fresh_stage=True,
                    canonical_qcrl_owner=(self.root/'source').stat().st_uid == pwd.getpwnam('qcrl').pw_uid,
                    fixed_interpreter=Path(PYTHON).is_file(), disk_reserve_over_4_gib=shutil.disk_usage(self.root).free > 4*1024**3,
                    public_prerequisites_match=state['collectors'] == {name: 'active' if name.endswith('.timer') else 'inactive' for name in SERVICES},
                    private_units_absent=True)

    def public_state(self):
        states = {}
        for name in SERVICES:
            # show succeeds for inactive units; never mutate collector state.
            value = command(['systemctl', 'show', name, '--property=ActiveState', '--value'], execute=True).strip()
            if value not in ('active', 'inactive'):
                raise ContractError('public service transitional/unknown')
            states[name] = value
        return dict(collectors=states, environment_sha256=digest('/etc/qcrl-stream.env', cap=1048576),
                    public_head=command(['git', '-c', 'safe.directory=/opt/qcrl-stream', '-C', '/opt/qcrl-stream', 'rev-parse', 'HEAD'], execute=True).strip())

    def claim(self, stage, freeze_hash):
        publish(self.root/'launch-claim.json', dict(freeze_sha256=freeze_hash, pid=os.getpid(), replay_authorized=False))
        command(['install', '-d', '-o', 'qcrl', '-g', 'qcrl', '-m', '750', str(self.evidence)], execute=True)
        publish(self.evidence/'execution-freeze.json', self.frozen)
        publish(self.evidence/'runtime-review.json', load(self.root/'runtime-review.json'))
        source = self.root/'select-review-source.c'
        if source.is_symlink() or source.stat().st_size > 4*1024*1024:
            raise ContractError('bounded nonsymlink reviewed source required')
        with source.open('rb') as src, (self.evidence/'select-review-source.c').open('xb') as dst:
            total = 0
            while True:
                block = src.read(65536)
                if not block:
                    break
                total += len(block)
                if total > 4*1024*1024:
                    raise ContractError('reviewed source grew beyond copy cap')
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        for name in ('execution-freeze.json', 'runtime-review.json', 'select-review-source.c'):
            os.chmod(self.evidence/name, 0o644)

    def start(self, spec):
        if spec != unit_spec(str(self.root), spec.get('role')):
            raise ContractError('only declared private unit specifications may start')
        self.specs[spec['unit']] = spec
        args = (['-m', 'unittest', 'discover', '-s', 'tests', '-q'] if spec['role'] == 'tests' else
                ['-m', 'infra.stream.recorder_wait_compatibility_worker', '--root', str(self.evidence), '--execute'])
        command(['systemd-run', '--unit='+spec['unit'], '--working-directory='+spec['working_directory'],
                 *['--property='+key+'='+value for key, value in spec['properties'].items()], PYTHON, *args], execute=True)

    def properties(self, unit, *, timeout=10):
        if unit not in self.specs:
            raise ContractError('only started private units may be inspected')
        text = command(['systemctl', 'show', unit+'.service'], timeout=timeout, execute=True)
        raw = {}
        for line in text.splitlines():
            key, separator, value = line.partition('=')
            if separator:
                if key in raw:
                    raise ContractError('duplicate unit property')
                raw[key] = value
        return text, raw

    def ready(self, unit, *, timeout_seconds, max_bytes):
        deadline = time.monotonic()+timeout_seconds
        while time.monotonic() < deadline:
            if (self.evidence/'ready.json').exists():
                return load(self.evidence/'ready.json', cap=max_bytes)
            time.sleep(.01)
        raise ContractError('readiness deadline missed')

    def bind(self, unit, ready):
        from infra.stream.recorder_application_resources import LinuxReader
        _, raw = self.properties(unit)
        observed = verified_properties(raw, self.specs[unit])
        identity = ready['identity']
        reader = LinuxReader(execute=True, pid=identity['pid'])
        sample = reader.read(rss=True)
        if (reader.expected != identity or raw.get('Id') != unit+'.service'
                or raw.get('MainPID') != str(identity['pid']) or raw.get('ExecMainPID') != str(identity['pid'])
                or raw.get('ControlGroup') != identity['cgroup'] or raw.get('SubState') != 'running'
                or raw.get('ActiveState') != 'active'):
            raise ContractError('live PID/unit/cgroup binding differs')
        binding = dict(unit=unit, identity=identity, active=True, observed_properties=observed)
        publish(self.evidence/'active-binding.json', dict(binding=binding, raw_properties=raw, sample=sample, binding_sha256=payload_hash(binding)))
        return binding

    def release(self, unit, release):
        publish(self.evidence/'release.json', release)

    def finish(self, unit, *, timeout_seconds):
        deadline = time.monotonic()+timeout_seconds
        while time.monotonic() < deadline:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                break
            _, raw = self.properties(unit, timeout=min(10, remaining))
            if raw.get('SubState') in ('exited', 'failed', 'dead'):
                return
            time.sleep(.1)
        raise ContractError('private unit completion deadline exceeded')

    def capture(self, unit, *, max_journal_bytes):
        errors, raw = [], None
        try:
            text, raw = self.properties(unit)
            with (self.evidence/(unit+'-properties.txt')).open('x') as handle:
                handle.write(text)
        except Exception as exc:
            errors.append(type(exc).__name__)
            if isinstance(exc, CommandError):
                with (self.evidence/(unit+'-properties.partial')).open('xb') as handle:
                    handle.write(exc.output)
        try:
            try:
                journal = command(['journalctl', '-u', unit+'.service', '--no-pager', '-o', 'short-monotonic'], cap=max_journal_bytes, execute=True).encode()
            except CommandError as exc:
                journal = exc.output
                errors.append(str(exc)[:160])
            with (self.evidence/(unit+'-journal.txt')).open('xb') as handle:
                handle.write(journal)
        except Exception as exc:
            errors.append(type(exc).__name__)
        if errors:
            publish(self.evidence/(unit+'-capture-error.json'), dict(errors=errors, truncated_or_incomplete=True))
            raise ContractError('journal/property capture incomplete; retained partial evidence')
        return dict(unit=unit, result=raw.get('Result'), exec_status=int(raw.get('ExecMainStatus', '-1')),
                    substate=raw.get('SubState'), observed_properties=verified_properties(raw, self.specs[unit]))

    def result(self, unit, *, max_bytes):
        return load(self.evidence/'compatibility-result.json', cap=max_bytes)

    def stop(self, unit):
        if unit not in self.specs:
            raise ContractError('only started private units may be stopped')
        command(['systemctl', 'stop', unit+'.service'], execute=True)

    def publish(self, result, *, max_bytes):
        publish(self.evidence/'launch-result.json', result)
        entries = {}
        for path in sorted(self.evidence.iterdir()):
            if path.is_symlink() or not path.is_file() or len(entries) >= 32:
                raise ContractError('origin inventory population differs')
            entries[path.name] = dict(bytes=path.stat().st_size, sha256=digest(path, cap=4*1024*1024))
        inventory = dict(schema_version='qcrl.wait_origin_inventory.v1', files=entries, freeze_sha256=self.frozen['freeze_sha256'], native_origin_verified=False)
        inventory['inventory_sha256'] = payload_hash(inventory)
        publish(self.root/'origin-inventory.json', inventory)


def launch(root, *, execute=False):
    if execute is not True or platform.system() != 'Linux' or os.geteuid() != 0:
        raise ContractError('explicit root Linux compatibility execution required')
    import re
    if not re.fullmatch(STAGE, str(root)):
        raise ContractError('dedicated private compatibility stage required')
    frozen = validate_freeze(load(Path(root)/'execution-freeze.json'))
    result = rehearse(stage=str(root), frozen=frozen, ops=Production(root, frozen, execute=True), execute=True)
    if not result['complete']:
        raise ContractError('compatibility launch incomplete; retained, no replay')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    launch(args.root, execute=args.execute)


if __name__ == '__main__': main()
