"""Prospective, read-only exited-unit inspection; never authorizes a stop/run."""
import os
from pathlib import Path
import platform
import re
import stat

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_validity_probe import process_start
from infra.stream.recorder_wait_production import command


POLICY = dict(schema_version='qcrl.exited_unit_inspection.policy.v1',
              rounds=2, missing_tasks='unknown_not_zero',
              required='exact_invocation_exited_bound_processes_gone_cgroup_empty_or_removed',
              authority='read_only_no_stop_no_scientific_acceptance')
PUBLIC_POLICY = dict(POLICY,schema_version='qcrl.exited_unit_inspection.policy.v2',
                     bound_processes='one_public_worker_or_parent_child')
FIELDS = ('Id', 'InvocationID', 'WorkingDirectory', 'ExecStart',
          'ExecMainStartTimestampMonotonic', 'ActiveState', 'SubState',
          'MainPID', 'ControlGroup', 'TasksCurrent', 'Result', 'ExecMainCode',
          'ExecMainStatus', 'ExecMainExitTimestampMonotonic')
IDENTITY_FIELDS = FIELDS[:5]
COMMAND_IDENTITY = dict(schema_version='qcrl.systemd_exec_identity.v1',
                        stable='path_argv_ignore_errors',
                        lifecycle='retain_start_stop_pid_code_status_not_command_identity',
                        unsupported='reject_structured_unknown_or_multiple_commands')


def command_identity(value):
    """Parse only the bounded single-command display; never shell-split argv.

    Lifecycle fields in systemd's ExecStart display change after exit. Keep the
    complete raw display in observations and compare the stable prefix exactly.
    Opaque legacy bindings still require byte equality, with no normalization.
    """
    require(type(value) is str and 0 < len(value) <= 8192, 'bounded ExecStart required')
    if not value.startswith('{'):
        return value
    match = re.fullmatch(
        r'\{ (path=/[^\s;{}]+ ; argv\[\]=[^;{}\r\n]+ ; ignore_errors=(?:yes|no))'
        r' ; start_time=\[[^\[\]\r\n]*\] ; stop_time=\[[^\[\]\r\n]*\]'
        r' ; pid=[0-9]+ ; code=(?:\(null\)|exited|killed|dumped)'
        r' ; status=[0-9]+/[A-Za-z0-9]+ \}', value)
    require(match is not None, 'unsupported systemd ExecStart display')
    return match.group(1)


def require(value, message):
    if not value:
        raise ContractError(message)


def positive(value):
    return type(value) is str and re.fullmatch(r'[1-9][0-9]{0,19}', value) is not None


def validate(expected, policy=POLICY):
    require(policy in (POLICY,PUBLIC_POLICY),'unsupported inspection policy')
    require(type(expected) is dict and set(expected) == {'properties', 'boot_id', 'cgroup', 'processes'},
            'explicit independent unit/process binding required')
    props = expected['properties']
    require(type(props) is dict and set(props) == set(IDENTITY_FIELDS)
            and all(type(v) is str and 0 < len(v) <= 8192 for v in props.values()),
            'complete exact invocation properties required')
    require(re.fullmatch(r'qcrl-[A-Za-z0-9_-]+\.service', props['Id']) is not None
            and re.fullmatch(r'[0-9a-f]{32}', props['InvocationID']) is not None
            and positive(props['ExecMainStartTimestampMonotonic']), 'invalid unit invocation')
    command_identity(props['ExecStart'])
    group = expected['cgroup']
    require(type(group) is str and group.startswith('/system.slice/')
            and group == '/system.slice/' + props['Id'], 'exact private cgroup required')
    require(type(expected['boot_id']) is str and 0 < len(expected['boot_id']) <= 64,
            'boot binding required')
    processes = expected['processes']
    require(type(processes) is list and len(processes) in ((1,2) if policy==PUBLIC_POLICY else (2,)),
            'explicit process bindings required')
    for row in processes:
        require(type(row) is dict and set(row) == {'pid', 'start_id'}
                and type(row['pid']) is int and 0 < row['pid'] <= 2**31-1
                and positive(row['start_id']), 'invalid process binding')
    require(len({p['pid'] for p in processes})==len(processes), 'distinct process bindings required')


def inspect_exited_unit(expected, reader, *, policy=POLICY):
    """Keep partial observations/errors. No retries, unit mutation or pass badge.

    Two equal rounds detect observable replacement/restart/boot/PID/cgroup races;
    they cannot promise atomicity or authorize a later stop across a TOCTOU gap.
    Reader failures are unresolved, including permission errors and partial reads.
    """
    validate(expected,policy)
    result = dict(schema_version='qcrl.exited_unit_inspection.v1',
                  policy_sha256=payload_hash(policy), binding_sha256=payload_hash(expected),
                  command_identity_sha256=payload_hash(COMMAND_IDENTITY),
                  observations=[], errors=[], exited_binding_observed=False,
                  tasks_current=None, resource_qualification=None, stop_authorized=False)
    try:
        for _ in range(POLICY['rounds']):
            row = dict(boot_id=reader.boot(), properties=reader.unit(expected['properties']['Id']))
            result['observations'].append(row)
            props = row['properties']
            require(row['boot_id'] == expected['boot_id'], 'boot changed')
            require(all((command_identity(props.get(k)) == command_identity(v)
                         if k == 'ExecStart' else props.get(k) == v)
                        for k, v in expected['properties'].items()),
                    'unit invocation identity differs')
            require((props.get('ActiveState'), props.get('SubState')) in
                    (('active', 'exited'), ('inactive', 'dead'), ('failed', 'failed'))
                    and props.get('MainPID') == '0', 'unit not exited')
            require(props.get('ControlGroup') in ('', expected['cgroup']), 'unit cgroup differs')
            raw = props.get('TasksCurrent')
            row['tasks_current_raw'] = raw
            if raw in (None, '', '[not set]'):
                row['tasks_current'] = None
            else:
                require(type(raw) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', raw) is not None,
                        'malformed TasksCurrent')
                row['tasks_current'] = int(raw)
                require(row['tasks_current'] == 0, 'unit reports remaining tasks')
            row['processes'] = []
            for bound in expected['processes']:
                current = reader.process(bound['pid'])
                row['processes'].append(dict(pid=bound['pid'], current_start_id=current))
                require(current is None or positive(current), 'malformed process start')
                require(current != bound['start_id'], 'bound process still exists')
            row['cgroup'] = reader.group(expected['cgroup'])
            group = row['cgroup']
            require(type(group) is dict and group.get('state') in ('removed', 'exists'),
                    'cgroup observation unavailable')
            require(group.get('members') == [], 'original cgroup populated')
            if group['state'] == 'exists':
                require(type(group.get('identity')) is list and len(group['identity']) == 2
                        and all(type(v) is int and v >= 0 for v in group['identity']),
                        'cgroup inode identity required')
        require(result['observations'][0] == result['observations'][1],
                'inspection changed between rounds')
        require(reader.boot() == expected['boot_id'], 'boot changed after inspection')
        result['tasks_current'] = result['observations'][-1]['tasks_current']
        result['exited_binding_observed'] = True
    except Exception as exc:
        result['errors'].append((type(exc).__name__ + ':' + str(exc))[:160])
    result['artifact_sha256'] = payload_hash(result)
    return result


class LinuxReader:
    """Bounded read-only adapter. Local tests inject roots/command, no SSH."""
    def __init__(self, *, execute=False, proc='/proc', cgroup='/sys/fs/cgroup', run=command):
        require(execute is True and platform.system() == 'Linux', 'explicit Linux inspection required')
        self.proc, self.cgroup, self.run = Path(proc), Path(cgroup), run
        require(all(p.is_absolute() and p.resolve(strict=True) == p for p in (self.proc, self.cgroup)),
                'canonical observation roots required')

    @staticmethod
    def text(path):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            require(stat.S_ISREG(os.fstat(fd).st_mode), 'regular observation file required')
            data = bytearray()
            while True:
                block = os.read(fd, 4097-len(data))
                if not block:
                    break
                data.extend(block)
                require(len(data) <= 4096, 'observation read cap exceeded')
            return bytes(data).decode('ascii')
        finally:
            os.close(fd)

    def boot(self):
        return self.text(self.proc / 'sys/kernel/random/boot_id').strip()

    def unit(self, unit):
        require(re.fullmatch(r'qcrl-[A-Za-z0-9_-]+\.service', unit) is not None, 'private unit required')
        raw = self.run(['systemctl', 'show', unit, '--property=' + ','.join(FIELDS)],
                       execute=True, timeout=5, cap=32768)
        rows = [line.split('=', 1) for line in raw.splitlines()]
        require(all(len(row) == 2 and row[0] in FIELDS for row in rows)
                and len({row[0] for row in rows}) == len(rows), 'malformed unit properties')
        return dict(rows)

    def process(self, pid):
        try:
            return process_start(self.text(self.proc / str(pid) / 'stat'), pid)
        except FileNotFoundError:
            return None

    def group(self, group):
        require(re.fullmatch(r'/system.slice/qcrl-[A-Za-z0-9_-]+\.service', group) is not None,
                'private cgroup path required')
        path = self.cgroup / group.lstrip('/')
        try:
            # Reject symlinks in every component, including dangling replacements.
            for parent in (self.cgroup, self.cgroup / 'system.slice', path):
                require(not parent.is_symlink(), 'cgroup symlink')
            before = path.stat()
        except FileNotFoundError:
            require(self.cgroup.is_dir() and (self.cgroup / 'system.slice').is_dir(),
                    'cgroup mount/slice unavailable')
            return dict(state='removed', members=[])
        require(stat.S_ISDIR(before.st_mode), 'cgroup directory required')
        text = self.text(path / 'cgroup.procs')
        members = text.split()
        require(all(positive(v) for v in members), 'malformed cgroup members')
        after = path.stat()
        require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino),
                'cgroup replaced during read')
        return dict(state='exists', identity=[after.st_dev, after.st_ino], members=members)
