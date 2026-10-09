"""Isolated compact-buffer transport adapter: numeric localhost, no recorder lane."""
import hashlib
import json
import threading
from pathlib import Path
from urllib.parse import urlsplit

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from infra.stream import receive_loop_compact as model, receive_loop_probe as reference
from infra.stream.receive_loop_contract import bindings

SCHEMA = 'qcrl.receive_loop_compact_sideband.transport.v1'


def sources():
    return {name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for name, path in (('transport', __file__), ('compact', model.__file__),
                               ('proxies', reference.__file__))}


class TransportBuffer(model.CompactBuffer):
    def __init__(self, contract, **kwargs):
        super().__init__(contract, **kwargs)
        self.receiver_thread = None
        self.parent_entries = 0
        self.parent_exits = 0
        self.connection_outcome = None
        self.connection_error_type = None

    def snapshot(self):
        with self.lock:
            if (self.receiver_thread is None or self.receiver_thread.is_alive()
                    or self.parent_entries != 1 or self.parent_exits != 1
                    or self.connection_outcome not in ('connected', 'error')):
                raise ContractError('native receiver must exit and be joined before snapshot')
        out = super().snapshot()
        out.update(schema_version=SCHEMA, model_only=False,
                   transport_installation_verified=self.installed,
                   transport_sources=sources(), parent_entries=1, parent_exits=1,
                   receiver_thread_exited=True, recorder_integration_verified=False,
                   connection_outcome=self.connection_outcome,
                   connection_error_type=self.connection_error_type)
        out['sideband_sha256'] = payload_hash({k: v for k, v in out.items() if k != 'sideband_sha256'})
        # Lifecycle/source fields count towards the unchanged encoded budget too.
        if len(json.dumps(out, sort_keys=True).encode()) > self.limits['max_encoded_sideband_bytes']:
            self.disable('encoded_sideband_budget')
            raise ContractError('transport sideband exceeds bound; preserve buffers')
        return out


def scan_transport(sideband, contract):
    verify_artifact_hash(sideband, 'sideband_sha256', 'compact transport sideband')
    expected = {'transport_sources': sources(), 'parent_entries': 1, 'parent_exits': 1,
                'receiver_thread_exited': True, 'recorder_integration_verified': False}
    outcome, error = sideband.get('connection_outcome'), sideband.get('connection_error_type')
    if (len(json.dumps(sideband, sort_keys=True).encode()) > contract['policy']['max_encoded_sideband_bytes']
            or sideband.get('schema_version') != SCHEMA or sideband.get('model_only') is not False
            or type(sideband.get('transport_installation_verified')) is not bool
            or 'connection_error_type' not in sideband
            or outcome not in ('connected', 'error')
            or (outcome == 'connected' and error is not None)
            or (outcome == 'error' and (not isinstance(error, str) or not 1 <= len(error) <= 128))
            or sideband.get('transport_installation_verified') is not sideband.get('installed_before_parent_loop')
            or any(sideband.get(k) != v or type(sideband.get(k)) is not type(v)
                   for k, v in expected.items())):
        raise ContractError('compact transport lifecycle/source/scope differs')
    # Structural projection exists only in memory; never serialize it as model evidence.
    view = {k: v for k, v in sideband.items() if k not in expected
            and k not in ('sideband_sha256', 'connection_outcome', 'connection_error_type')}
    view.update(schema_version='qcrl.receive_loop_compact_sideband.model.v1', model_only=True,
                transport_installation_verified=False)
    view['sideband_sha256'] = payload_hash(view)
    result = model.scan_model(view, contract)
    return dict(result, model_only=False,
                transport_installation_verified=sideband['transport_installation_verified'],
                recorder_integration_verified=False)


def _connection_class(observer):
    from websockets.frames import Frame
    from websockets.sync.client import ClientConnection

    class CompactConnection(ClientConnection):
        def recv_events(self):
            with observer.lock:
                observer.receiver_thread = threading.current_thread()
                observer.parent_entries += 1
            reference.install(self, observer)
            try:
                return super().recv_events()
            finally:
                observer.loop_finished(getattr(self, 'recv_exc', None))
                with observer.lock:
                    observer.parent_exits += 1

        def process_event(self, event):
            token = observer.dispatch_begin(isinstance(event, Frame))
            try:
                result = super().process_event(event)
            except BaseException as exc:
                observer.dispatch_end(token, error=exc)
                raise
            observer.dispatch_end(token)
            return result
    return CompactConnection


def connect_loopback(uri, observer):
    if type(observer) is not TransportBuffer:
        raise ContractError('explicit isolated compact transport buffer required')
    try:
        parsed = urlsplit(uri)
        allowed = (parsed.scheme == 'ws' and parsed.hostname in ('127.0.0.1', '::1')
                   and parsed.port is not None and 0 < parsed.port <= 65535
                   and parsed.username is None and parsed.password is None
                   and not parsed.query and not parsed.fragment and parsed.path in ('', '/'))
    except (ValueError, TypeError):
        allowed = False
    if not allowed:
        raise ContractError('compact transport permits numeric localhost only')
    # Fail closed on changed library/source/methods before claim or network.
    if bindings() != observer.contract['runtime_receipt']['methods']:
        raise ContractError('compact transport method bindings differ from declaration')
    with observer.lock:
        if observer.claimed or observer.finished or observer.installed:
            raise ContractError('compact transport buffer permits one connection only')
        observer.claimed = True
    from websockets.sync.client import connect
    try:
        connection = connect(uri, create_connection=_connection_class(observer), open_timeout=10,
                             close_timeout=5, max_size=262144, max_queue=16, compression=None,
                             ping_interval=None, proxy=None)
    except BaseException as exc:
        with observer.lock:
            observer.connection_outcome = 'error'
            observer.connection_error_type = type(exc).__name__[:128]
        raise
    with observer.lock:
        observer.connection_outcome = 'connected'
    return connection
