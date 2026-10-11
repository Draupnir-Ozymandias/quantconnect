"""Finite real-loopback worker components. No cohort launcher or cloud mutation."""
from datetime import timedelta
import json
import hashlib
import argparse
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from execution_truth.acquisition import utc_now, utc_text
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import stream_plan, StreamTransportError
from execution_truth.stream_segments import exclusive_json
from execution_truth.stream_segments import file_hash
from infra.stream.recorder_application_budget import POLICY, corpus, validate
from infra.stream.recorder_completion import CompletionWitnesses
from infra.stream.recorder_completion_lane import collect_with_completion
from infra.stream.recorder_application_resources import LinuxReader, observe


def implementation_sources():
    root = Path(__file__).resolve().parents[2]
    names = ['infra/stream/recorder_application_worker.py',
             'infra/stream/recorder_application_resources.py',
             'infra/stream/recorder_application_evaluator.py',
             'infra/stream/receive_loop_validity_probe.py',
             'infra/stream/receive_loop_validity.py',
             'tests/test_taker_replay.py', 'tests/test_execution_truth_acquisition.py',
             'tests/test_recorder_application_components.py',
             'tests/test_recorder_application_loopback.py']
    names += [str(p.relative_to(root)) for p in sorted((root / 'tests/fixtures/polymarket').glob('*.json'))]
    return {name: file_hash(root / name) for name in names}


def localhost_uri(uri):
    try:
        parsed = urlsplit(uri)
        valid = (parsed.scheme == 'ws' and parsed.hostname == '127.0.0.1'
                 and parsed.port is not None and 0 < parsed.port < 65536
                 and parsed.username is None and parsed.password is None
                 and not parsed.path and not parsed.query and not parsed.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ContractError('numeric loopback URI required')


def schedule(kind):
    if kind not in POLICY['workloads']:
        raise ContractError('unknown workload')
    rows, offset = [], 0
    for phase, value in enumerate(POLICY['workloads'][kind]):
        for j in range(value['seconds'] * value['rate']):
            rows.append(dict(sequence=len(rows), phase=phase, offset=offset + j / value['rate']))
        offset += value['seconds']
    return rows


def message(index):
    if type(index) is not int or not 0 <= index < 60000:
        raise ContractError('occurrence outside fixed population')
    values = corpus()
    return values['initial'][index] if index < 2 else values['cycle'][(index - 2) % 8]


def load(path):
    # Case control artifacts are deliberately small and exclusively published.
    with Path(path).open('rb') as handle:
        data = handle.read(2 * 1024**2 + 1)
    if len(data) > 2 * 1024**2:
        raise ContractError('control artifact exceeds cap')
    return json.loads(data)


def publish(path, obj):
    value = dict(obj, artifact_sha256=payload_hash(obj))
    exclusive_json(path, value)
    return value


def control(path):
    from execution_truth.contracts import verify_artifact_hash
    value = load(path)
    verify_artifact_hash(value, 'artifact_sha256', str(path))
    return value


def prepare(path, declaration, case, *, execute=False):
    if execute is not True or case not in POLICY['case_order']:
        raise ContractError('explicit finite case required')
    validate(declaration)
    # Retained fixture source/dependencies must enter the later execution freeze.
    from tests.test_taker_replay import raw_bundle, revise
    root = Path(path)
    root.mkdir(exist_ok=False)
    before = time.monotonic()
    now = utc_now()
    after = time.monotonic()
    epoch = after + 20
    epoch_utc = now + timedelta(seconds=epoch - before)
    raw = raw_bundle()
    revise(raw, 'gamma_market', startDate=utc_text(epoch_utc - timedelta(seconds=60)),
           eventStartTime=utc_text(epoch_utc - timedelta(seconds=10)),
           endDate=utc_text(epoch_utc + timedelta(seconds=290)))
    spec = stream_plan(raw, segmented=True, max_seconds=180, max_frames=60000)
    if spec['condition_id'] != POLICY['synthetic_condition_id'] or spec['asset_ids'] != ['10001', '10002']:
        raise ContractError('synthetic fixture identity mismatch')
    publish(root / 'case.json', dict(case=case, plan_sha256=declaration['plan_sha256'],
            epoch=epoch, epoch_utc=utc_text(epoch_utc), epoch_clock=dict(before=before, after=after),
            raw_bundle=raw, spec=spec, fixture_is_synthetic=True,
            implementation_sources=implementation_sources(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
    return root


def context(root, declaration, execute):
    if execute is not True:
        raise ContractError('explicit execution required')
    validate(declaration)
    case = control(Path(root) / 'case.json')
    if case['plan_sha256'] != declaration['plan_sha256'] or case['case'] not in POLICY['case_order']:
        raise ContractError('case binding differs')
    if case['implementation_sources'] != implementation_sources():
        raise ContractError('worker/resource/evaluator source drift')
    if case['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
        raise ContractError('shared monotonic boot changed')
    if time.monotonic() >= case['epoch'] - .1:
        raise ContractError('missed readiness deadline; no late adoption')
    return case


def transmit(conn, kind, epoch, *, clock=time.monotonic, pause=time.sleep):
    rows = []
    error = None
    payloads = corpus()
    try:
        for row in schedule(kind):
            deadline = epoch + row['offset']
            pause(max(0, deadline - clock()))
            begin = clock()
            i = row['sequence']
            raw = payloads['initial'][i] if i < 2 else payloads['cycle'][(i-2) % 8]
            conn.send(raw)
            rows.append(dict(row, deadline=deadline, begin=begin, end=clock(),
                             raw_sha256=hashlib.sha256(raw.encode()).hexdigest()))
    except Exception as exc:
        error = type(exc).__name__ + ':' + str(exc)[:160]
    return dict(rows=rows, error=error, complete=error is None and len(rows) == 60000)


def produce(root, declaration, *, execute=False):
    from websockets.sync.server import serve
    root = Path(root)
    case = context(root, declaration, execute)
    reader = LinuxReader(execute=True)
    initial_resource = reader.read(rss=True)
    finished = threading.Event()
    attempted = threading.Event()
    attempt_lock = threading.Lock()
    def handler(conn):
        with attempt_lock:
            if attempted.is_set():
                conn.close()
                return
            attempted.set()
        result = dict(rows=[], complete=False, error='before_subscription')
        controls, errors = [], []
        stopped = threading.Event()
        def drain():
            while not stopped.is_set():
                try:
                    value = conn.recv(timeout=.2)
                    if len(controls) >= 256:
                        raise ContractError('control traffic cap exceeded')
                    controls.append(dict(at=time.monotonic(), text=value))
                except TimeoutError:
                    continue
                except Exception as exc:
                    if not stopped.is_set():
                        errors.append(type(exc).__name__)
                    return
        thread = None
        try:
            if json.loads(conn.recv(timeout=5)) != case['spec']['subscription']:
                raise ContractError('subscription differs')
            identities = []
            for name in ('worker-ready.json', 'observer-ready.json'):
                while not (root / name).exists() and time.monotonic() < case['epoch'] - .1:
                    time.sleep(.01)
                value = control(root / name)
                if value['case_sha256'] != case['artifact_sha256'] or value['at'] >= case['epoch']:
                    raise ContractError('readiness binding differs')
                identities.append(value['identity'])
            if (identities[0] != identities[1] or identities[0]['boot_id'] != reader.expected['boot_id']
                    or identities[0]['cgroup'] == reader.expected['cgroup']):
                raise ContractError('producer and recorder isolation differs')
            while not (root/'bindings-ready.json').exists() and time.monotonic() < case['epoch']-.1:
                time.sleep(.01)
            binding = control(root/'bindings-ready.json')
            if binding['case_sha256'] != case['artifact_sha256'] or binding['at'] >= case['epoch']:
                raise ContractError('independent bindings missed epoch')
            thread = threading.Thread(target=drain, daemon=True)
            thread.start()
            result = transmit(conn, case['case'].split('-')[0], case['epoch'])
            # Keep the connection alive while the recorder drains, never send extras.
            while not (root / 'capture-closed.json').exists() and time.monotonic() < case['epoch'] + 185:
                time.sleep(.01)
        except Exception as exc:
            result['error'] = type(exc).__name__ + ':' + str(exc)[:160]
            result['complete'] = False
        finally:
            stopped.set()
            if thread is not None:
                thread.join(timeout=1)
            try:
                final_resource = reader.read(rss=True)
            except Exception as exc:
                final_resource = dict(error=type(exc).__name__ + ':' + str(exc)[:160])
            publish(root / 'producer.json', dict(case_sha256=case['artifact_sha256'],
                    result=result, controls=controls, control_errors=errors,
                    identity=reader.expected, initial_resource=initial_resource,
                    final_resource=final_resource))
            finished.set()
    with serve(handler, '127.0.0.1', 0, compression=None, ping_interval=None,
               max_size=262144, max_queue=16, close_timeout=1) as server:
        publish(root / 'server-ready.json', dict(case_sha256=case['artifact_sha256'],
                uri='ws://127.0.0.1:' + str(server.socket.getsockname()[1]), at=time.monotonic(),
                identity=reader.expected))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        finished.wait(max(0, case['epoch'] + 190 - time.monotonic()))
        server.shutdown()
        thread.join(timeout=2)
    if not finished.is_set():
        publish(root / 'producer-timeout.json', dict(case_sha256=case['artifact_sha256'], error='no_completed_handler'))


class LoopbackSocket:
    def __init__(self, uri, root, case, identity):
        from websockets.sync.client import connect
        localhost_uri(uri)
        self.root, self.case, self.identity = Path(root), case, identity
        self.conn = connect(uri, compression=None, ping_interval=None,
                            max_size=262144, max_queue=16, open_timeout=5, close_timeout=1)
        self.ready = False

    def send(self, value):
        self.conn.send(value)
        if not self.ready:
            self.ready = True
            publish(self.root / 'worker-ready.json', dict(case_sha256=self.case['artifact_sha256'],
                    at=time.monotonic(), identity=self.identity))

    def recv(self, timeout):
        from websockets.exceptions import WebSocketException
        try:
            return self.conn.recv(timeout=timeout)
        except WebSocketException as exc:
            raise StreamTransportError(type(exc).__name__) from exc

    def close(self):
        self.conn.close()


def consume(root, declaration, *, execute=False):
    root = Path(root)
    case = context(root, declaration, execute)
    ready = control(root / 'server-ready.json')
    if ready['case_sha256'] != case['artifact_sha256']:
        raise ContractError('server binding differs')
    localhost_uri(ready['uri'])
    reader = LinuxReader(execute=True)
    if (ready['identity']['boot_id'] != reader.expected['boot_id']
            or ready['identity']['cgroup'] == reader.expected['cgroup']):
        raise ContractError('server boot/cgroup isolation differs')
    domain = 'localhost.' + case['boot_id']
    observer = CompletionWitnesses(case['spec'], domain, clock=utc_now,
                                   monotonic=time.monotonic, execute=True)
    stop = threading.Event()
    resources = {}
    def monitor():
        try:
            initial = reader.read(rss=True)
            publish(root / 'observer-ready.json', dict(case_sha256=case['artifact_sha256'],
                    at=time.monotonic(), identity=reader.expected, initial=initial))
            resources.update(observe(reader, case['epoch'], stop))
        except Exception as exc:
            resources.update(rows=[], overflow=False, error=type(exc).__name__ + ':' + str(exc)[:160])
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    summary, error = None, None
    try:
        summary = collect_with_completion(case['raw_bundle'], case['spec'], root / 'archive',
                    connector=lambda: LoopbackSocket(ready['uri'], root, case, reader.expected),
                    clock=utc_now, monotonic=time.monotonic, completion_observer=observer)
    except Exception as exc:
        error = type(exc).__name__ + ':' + str(exc)[:160]
    finally:
        closed = time.monotonic()
        stop.set()
        publish(root / 'capture-closed.json', dict(case_sha256=case['artifact_sha256'], at=closed))
        thread.join(timeout=3)
        try:
            exclusive_json(root / 'completion.json', observer.snapshot(root / 'archive'))
        except Exception as exc:
            publish(root / 'completion-error.json', dict(error=type(exc).__name__ + ':' + str(exc)[:160]))
        publish(root / 'consumer.json', dict(case_sha256=case['artifact_sha256'],
                summary=summary, error=error, closed=closed, domain=domain,
                identity=reader.expected, resources=resources, observer_thread_alive=thread.is_alive()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--declaration', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('action', choices=('prepare', 'produce', 'consume'))
    parser.add_argument('--case', choices=POLICY['case_order'])
    args = parser.parse_args()
    if not args.execute:
        parser.error('finite worker requires explicit --execute')
    declaration = load(args.declaration)
    if args.action == 'prepare':
        prepare(args.root, declaration, args.case, execute=True)
    elif args.action == 'produce':
        produce(args.root, declaration, execute=True)
    else:
        consume(args.root, declaration, execute=True)


if __name__ == '__main__':
    main()
