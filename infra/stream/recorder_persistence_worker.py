"""Successor isolated recorder workers; no public collector or historical mutation."""
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from execution_truth.acquisition import utc_now
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import exclusive_json
from infra.stream.recorder_application_worker import (context, control, transmit,
    LoopbackSocket as LegacyLoopbackSocket, implementation_sources, message, localhost_uri)
from infra.stream.recorder_application_resources import LinuxReader, observe
from infra.stream.recorder_completion import CompletionWitnesses, verify_completion, _sources
from infra.stream.recorder_persistence_lane import collect_with_completion


def publish(path, obj):
    # Expose only a complete exclusive control artifact. In particular, producer
    # verification must not race consumer.json's incremental JSON serialization.
    path=Path(path);pending=path.with_name(path.name+'.pending')
    value=dict(obj,artifact_sha256=payload_hash(obj))
    exclusive_json(pending,value)
    os.link(pending,path)  # exclusive final name, no replacement
    fd=os.open(str(path.parent),os.O_RDONLY)
    try:
        os.fsync(fd)
        pending.unlink()
        os.fsync(fd)
    finally:os.close(fd)
    return value


class LoopbackSocket(LegacyLoopbackSocket):
    def send(self,value):
        self.conn.send(value)
        if not self.ready:
            self.ready=True
            publish(self.root/'worker-ready.json',dict(case_sha256=self.case['artifact_sha256'],
                at=time.monotonic(),identity=self.identity))


def require(value, message):
    if not value: raise ContractError(message)


def verify_recorder_completion(root, case):
    root = Path(root)
    closed = control(root/'capture-closed.json')
    consumer = control(root/'consumer.json')
    require(closed['case_sha256'] == consumer['case_sha256'] == case['artifact_sha256']
        and closed['at'] == consumer['closed'] <= case['epoch']+185,
        'recorder closure binding/deadline differs')
    summary = consumer['summary']
    require(consumer['error'] is None and consumer['observer_thread_alive'] is False
        and summary['status'] == 'frame_limit' and summary['frames'] == case['spec']['max_frames']
        and summary['connections'] == 1, 'recorder did not complete planned capture')
    report = json.loads((root/'completion.json').read_text())
    require(report['runtime']['pid'] == consumer['identity']['pid']
        and report['spec_sha256'] == payload_hash(case['spec']),
        'recorder completion identity/spec differs')
    verified = verify_completion(report, root/'archive', expected_domain='localhost.'+case['boot_id'],
                                 expected_sources=_sources())
    require(verified['frames'] == case['spec']['max_frames'], 'recorder completion population differs')
    from infra.stream.recorder_absolute_smoke_audit import archive_frames
    frames, footer, gaps = archive_frames(root/'archive')
    require(not gaps and footer == summary and frames == [message(i) for i in range(case['spec']['max_frames'])],
            'recorder ordered population/footer differs')
    return dict(consumer=consumer, completion=report, closed=closed)


def verify_closure(result, terminal, controls, errors, verified, case):
    require(not errors and all(r['text'] == 'PING' for r in controls), 'producer control/drain fault')
    rows = result['rows']; count = case['spec']['max_frames']
    require(result['complete'] is True and result['error'] is None and len(rows) == count
        and [r['sequence'] for r in rows] == list(range(count)), 'planned sends incomplete')
    previous = case['epoch']
    for i, row in enumerate(rows):
        require(previous <= row['begin'] <= row['end']
            and row['raw_sha256'] == hashlib.sha256(message(i).encode()).hexdigest(), 'send order/bytes differ')
        previous = row['end']
    require(len(terminal) == 1, 'terminal receive event unavailable')
    event = terminal[0]
    require(event['normal'] is True and event['type'] == 'ConnectionClosedOK'
        and event['received_code'] in (1000,1001) and event['sent_code'] in (1000,1001)
        and rows[-1]['end'] <= event['at'] <= case['epoch']+185, 'premature or abnormal close')
    require(verified['closed']['at'] <= case['epoch']+185, 'recorder completion unavailable')
    return True


def produce(root, declaration, *, execute=False, transmitter=None):
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
        controls, errors, terminal = [], [], []
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
                    # Keep the fault even if stopped changes during recv.
                    from websockets.exceptions import ConnectionClosedOK
                    terminal.append(dict(at=time.monotonic(), type=type(exc).__name__,
                        normal=isinstance(exc, ConnectionClosedOK),
                        received_code=getattr(getattr(exc, 'rcvd', None), 'code', None),
                        sent_code=getattr(getattr(exc, 'sent', None), 'code', None)))
                    if not isinstance(exc, ConnectionClosedOK):
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
            result = (transmit if transmitter is None else transmitter)(conn, case['case'].split('-')[0], case['epoch'])
            # Keep the connection alive while the recorder drains, never send extras.
            while not (root / 'consumer.json').exists() and time.monotonic() < case['epoch'] + 185:
                time.sleep(.01)
        except Exception as exc:
            result['error'] = (type(exc).__name__ + ':' + str(exc))[:160]
            result['complete'] = False
        finally:
            stopped.set()
            if thread is not None:
                thread.join(timeout=1)
                if thread.is_alive(): errors.append('drain_thread_alive')
            try:
                completion = verify_recorder_completion(root, case)
                verify_closure(result, terminal, controls, errors, completion, case)
            except Exception as exc:
                errors.append((type(exc).__name__+':'+str(exc))[:160])
            try:
                final_resource = reader.read(rss=True)
            except Exception as exc:
                final_resource = dict(error=(type(exc).__name__ + ':' + str(exc))[:160])
            publish(root / 'producer.json', dict(case_sha256=case['artifact_sha256'],
                    result=result, controls=controls, control_errors=errors, terminal_receive=terminal,
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


def consume(root, declaration, *, execute=False, resource_observer=None):
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
            resources.update((observe if resource_observer is None else resource_observer)(reader, case['epoch'], stop))
        except Exception as exc:
            resources.update(rows=[], overflow=False, error=(type(exc).__name__ + ':' + str(exc))[:160])
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    summary, error = None, None
    try:
        summary = collect_with_completion(case['raw_bundle'], case['spec'], root / 'archive',
                    connector=lambda: LoopbackSocket(ready['uri'], root, case, reader.expected),
                    clock=utc_now, monotonic=time.monotonic, completion_observer=observer)
    except Exception as exc:
        error = (type(exc).__name__ + ':' + str(exc))[:160]
    finally:
        closed = time.monotonic()
        stop.set()
        publish(root / 'capture-closed.json', dict(case_sha256=case['artifact_sha256'], at=closed))
        thread.join(timeout=3)
        try:
            exclusive_json(root / 'completion.json', observer.snapshot(root / 'archive'))
        except Exception as exc:
            publish(root / 'completion-error.json', dict(error=(type(exc).__name__ + ':' + str(exc))[:160]))
        publish(root / 'consumer.json', dict(case_sha256=case['artifact_sha256'],
                summary=summary, error=error, closed=closed, domain=domain,
                identity=reader.expected, resources=resources, observer_thread_alive=thread.is_alive()))
