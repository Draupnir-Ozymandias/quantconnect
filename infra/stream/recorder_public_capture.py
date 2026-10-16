"""Single-attempt public-study acquisition; frozen legacy collectors stay unchanged.

No CLI/default launch. Caller must supply a source/runtime-bound, approved case.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import ssl
import threading
import time
from websockets.protocol import State

from execution_truth.acquisition import utc_now
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import ENDPOINT, classify_frame, stream_plan
from infra.stream.recorder_completion import CompletionWitnesses
from infra.stream.recorder_persistence_lane import DeadlineStreamLog
from infra.stream.recorder_public_counts import PLAN, number, require


def short_error(exc):
    return (type(exc).__name__+':'+str(exc))[:160]


class ConnectDeadline:
    """A blocked resolver has no socket FD yet: stop this worker, never retry.

    Default SIGTERM is required, never installed or replaced. Abrupt exit may
    leave only the synced archive prefix and missing in-memory witness tails.
    """
    def __init__(self, deadline, *, clock=time.monotonic):
        require(signal.getsignal(signal.SIGTERM)==signal.SIG_DFL,
                'connection deadline requires unchanged default SIGTERM')
        self.timer=threading.Timer(max(0,deadline-clock()),self.interrupt)
        self.timer.daemon=True
        self.timer.start()

    @staticmethod
    def interrupt():
        os.kill(os.getpid(),signal.SIGTERM)

    def cancel(self):
        self.timer.cancel();self.timer.join(timeout=1)


class DeadlineInterrupt:
    """Control deadline interrupts blocked socket I/O; no timing subtraction.

    A raced receive exception is always retained, even when this interrupt fired.
    Timer scheduling has no real-time guarantee; actual overruns remain evidence.
    """
    def __init__(self, raw_socket, deadline, *, clock=time.monotonic):
        self.socket, self.fired, self.error = raw_socket, threading.Event(), None
        self.timer = threading.Timer(max(0, deadline-clock()), self.interrupt)
        self.timer.daemon = True
        self.timer.start()

    def interrupt(self):
        self.fired.set()
        try:
            # Bypass SSLSocket.shutdown's Python _sslobj mutation while another
            # thread can be inside SSL_write. Interrupt the underlying FD only.
            socket.socket.shutdown(self.socket, socket.SHUT_RDWR)
        except OSError as exc:
            self.error = short_error(exc)

    def cancel(self):
        self.timer.cancel()
        self.timer.join(timeout=1)


class StorageGuard:
    """Necessary storage-limit enforcement, outside unchanged timestamp brackets."""
    def __init__(self, root):
        self.root = Path(root)
        require(self.root.is_dir() and not self.root.is_symlink(), 'private storage root required')
        require(shutil.disk_usage(self.root).free >= PLAN['disk_start_bytes'],
                'two GiB free disk required before acquisition')

    def check(self):
        # Reserve both terminal publication and the largest next bounded write.
        reserve = PLAN['auxiliary_cap_bytes']+8*1024**2
        require(shutil.disk_usage(self.root).free >= PLAN['disk_reserve_bytes']+reserve,
                'disk reserve reached')
        total, files = 0, 0
        for path in self.root.rglob('*'):
            require(not path.is_symlink(), 'symlink in private study spool')
            if path.is_file():
                files += 1
                total += path.stat().st_size
                require(files <= 1024 and total+reserve <= PLAN['spool_cap_bytes'],
                        'private spool cap reached')


class StudyLog(DeadlineStreamLog):
    def __init__(self, *args, guard, **kwargs):
        self.guard = guard
        super().__init__(*args, **kwargs)

    def append(self, kind, payload):
        if kind != 'session_end':
            self.guard.check()
        return super().append(kind, payload)


def contamination(raw, spec):
    """Only explicit contradictions; malformed/unknown schema stays a raw frame."""
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return False
    if isinstance(obj, list):
        return any(contamination(json.dumps(value), spec) for value in obj)
    if not isinstance(obj, dict):
        return False
    if isinstance(obj.get('market'), str) and obj['market'] != spec['condition_id']:
        return True
    if isinstance(obj.get('asset_id'), str) and obj['asset_id'] not in spec['asset_ids']:
        return True
    changes = obj.get('price_changes')
    if isinstance(changes, list):
        return any(isinstance(change, dict) and isinstance(change.get('asset_id'), str)
                   and change['asset_id'] not in spec['asset_ids'] for change in changes)
    return False


def collect(raw_bundle, spec, root, *, epoch_ns, observer, execute=False,
            clock=utc_now, monotonic=time.monotonic, connect_factory=None,
            guard=None, interrupt_factory=DeadlineInterrupt, connect_guard_factory=ConnectDeadline,
            tls_context=None):
    """Actual public connection by default; tests explicitly inject local transport.

    Source/runtime/market approval is checked by the outer worker before this
    explicit acquisition gate. This function never starts a unit or schedules one.
    """
    require(execute is True, 'explicit public study acquisition required')
    require(type(epoch_ns) is int and epoch_ns >= 0, 'fixed integer study epoch required')
    expected = stream_plan(raw_bundle, segmented=True, max_seconds=90, max_frames=60000)
    require(spec == expected, 'public study spec drift')
    require(isinstance(observer, CompletionWitnesses) and observer.clock == clock
            and observer.monotonic == monotonic, 'unchanged matching completion observer required')
    observer.validate_spec(spec)
    epoch = epoch_ns/1000000000
    require(number(monotonic()) < number(epoch)-1, 'subscription readiness already missed')
    root = Path(root)
    guard = StorageGuard(root.parent) if guard is None else guard
    guard.check()
    if connect_factory is None:
        require(isinstance(tls_context,ssl.SSLContext) and tls_context.check_hostname
                and tls_context.verify_mode==ssl.CERT_REQUIRED,'frozen verified TLS context required')
        from websockets.sync.client import connect
        connect_factory = connect
    log = StudyLog(root, clock, monotonic, spec['storage'],
                   completion_observer=observer, guard=guard)
    conn, interrupt = None, None
    frames, ready, attempted, closed, acquisition_ended, deadline = 0, None, None, None, None, None
    status, error, last_safe = 'before_connect', None, None
    terminal, interrupt_receipts, close_errors = [], [], []
    snapshots = []

    def finish_interrupt():
        nonlocal interrupt
        if interrupt is not None:
            interrupt.cancel()
            interrupt_receipts.append(dict(fired=interrupt.fired.is_set(), error=interrupt.error))
            interrupt = None

    try:
        log.append('session_start', dict(spec=spec, spec_sha256=payload_hash(spec)))
        log.append('connect_attempt', dict(connection=1))
        attempted = monotonic()
        readiness = min(epoch-1, attempted+10)
        require(readiness > attempted, 'connection readiness missed')
        # connect() enforces its own handshake timeout; after return the control
        # watchdog also bounds a blocked subscription write and later sends.
        connecting=connect_guard_factory(readiness,clock=monotonic)
        try:
            conn = connect_factory(ENDPOINT, open_timeout=readiness-attempted,
                close_timeout=5, max_size=262144, max_queue=16, compression=None,
                ping_interval=None, proxy=None, **({'ssl':tls_context} if tls_context is not None else {}))
        finally:
            connecting.cancel()
        interrupt = interrupt_factory(conn.socket, readiness, clock=monotonic)
        conn.send(json.dumps(spec['subscription']))
        ready = monotonic()
        require(ready < epoch-1, 'subscription readiness missed')
        finish_interrupt()
        deadline = min(epoch+65, attempted+90)
        interrupt = interrupt_factory(conn.socket, deadline, clock=monotonic)
        log.append('subscribed', dict(connection=1))
        last_ping = last_pong = ready
        status = 'scheduled_stop'
        while True:
            now = monotonic()
            if now >= deadline:
                break
            if frames >= 60000:
                status = 'frame_limit'
                break
            if now-last_pong >= 30:
                raise ContractError('pong_timeout')
            if now-last_ping >= 10:
                conn.send('PING')
                last_ping = monotonic()
                log.append('ping_sent', dict(connection=1))
            try:
                remaining = deadline-monotonic()
                if remaining <= 0:
                    break
                timeout = log.receive_timeout(min(1, remaining))
                remaining = deadline-monotonic()  # A sync must not adopt a stale receive budget.
                if remaining <= 0:
                    break
                frame = conn.recv(timeout=min(timeout, remaining))
            except TimeoutError:
                log.sync_if_due()
                continue
            # Placement is unchanged: no validation/classification before the
            # existing monotonic/UTC/monotonic application-return operation.
            observer.application_return(frame, 1)
            timing_failure=observer.failure
            require(isinstance(frame, str) and len(frame.encode('utf-8')) <= 262144,
                    'binary_or_oversize_frame')
            classes = classify_frame(frame, spec)
            log.append('frame', dict(connection=1, raw_text=frame, classification=classes))
            frames += 1
            require(timing_failure is None and observer.failure is None and len(observer.frames) == frames,
                    'required occurrence linkage/clock fault: '+str(observer.failure))
            last_safe = observer.frames[-1]['returned']['before']
            if frame == 'PONG':
                last_pong = monotonic()
            for event in classes:
                if event['scope'] == 'selected_market' and event['event_type'] == 'book':
                    snapshots = sorted(set(snapshots+event['asset_ids']))
            require(not contamination(frame, spec), 'explicit foreign asset/condition binding')
            if frames >= 60000:
                status = 'frame_limit'
                break
    except BaseException as exc:
        # Never clear a receive/close fault just because the deadline fired.
        status, error = 'interrupted', short_error(exc)
        terminal.append(dict(type=type(exc).__name__, error=error))
        try:
            log.append('connection_gap', dict(connection=1, reason=error[:120]))
        except BaseException as log_exc:
            close_errors.append(short_error(log_exc))
    finally:
        acquisition_ended = monotonic()
        finish_interrupt()
        if conn is not None and status=='scheduled_stop' and error is None:
            try:
                require(conn.state==State.OPEN,'transport already closing at stop; closure timing unknown')
            except BaseException as exc:
                status,error='interrupted',short_error(exc)
                terminal.append(dict(type=type(exc).__name__,error=error))
                try:
                    log.append('connection_gap',dict(connection=1,reason=error[:120]))
                except BaseException as log_exc:
                    close_errors.append(short_error(log_exc))
        if conn is not None:
            try:
                conn.close()
            except BaseException as exc:
                close_errors.append(short_error(exc))
        closed = monotonic()
        if close_errors and error is None:
            error = close_errors[0]
        summary = dict(status=status, frames=frames, connections=int(attempted is not None),
            event_counts={}, book_snapshot_assets_by_connection={'1': snapshots},
            continuous_coverage_proven=False, orders_authorized=False)
        try:
            log.append('session_end', summary)
        except BaseException as exc:
            close_errors.append(short_error(exc))
        try:
            log.close()
        except BaseException as exc:
            close_errors.append(short_error(exc))
    return dict(summary=summary, error=error, close_errors=close_errors,
        terminal_receive=terminal, deadline_interrupts=interrupt_receipts,
        ready=ready, attempted=attempted, closed=closed, last_safe=last_safe,
        acquisition_ended=acquisition_ended, acquisition_deadline=deadline,
        epoch_ns=epoch_ns, original_application_verdict='fail', orders_authorized=False)
