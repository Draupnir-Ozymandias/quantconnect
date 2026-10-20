"""Single-attempt public-study acquisition; frozen legacy collectors stay unchanged.

No CLI/default launch. Caller must supply a source/runtime-bound, approved case.
"""
import json
import os
import re
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


STOP_POLICY = dict(schema_version='qcrl.public_acquisition_stop_ownership.v1',
    normal_owner='acquisition_thread', emergency_owner='socket_deadline_thread',
    emergency_grace_seconds=.25, acquisition_hard_seconds=90,
    close_hard_seconds=5, normal_requires='deadline_reached_open_transport_no_emergency',
    ordering='claim_and_disarm_before_local_close', faults='never_clear_on_timer_fire',
    process_guard='unchanged_default_SIGTERM', unit_hard_seconds=240)


NOTICE_POLICY = dict(schema_version='qcrl.public_creation_notice.v1',
    event_type='new_market', minimum_assets=2, maximum_assets=64,
    foreign_creation_metadata='retain_count_unconfirmed_never_book_state',
    other_foreign_bindings='fatal', ambiguous_or_mixed_envelope='no_exemption')
PUBLICATION_POLICY = dict(schema_version='qcrl.public_acquisition_publication.v1',
    order=['end_acquisition','seal_archive','publish_completion_and_checkpoint','close','publish_final_consumer'],
    close_hard_seconds=5, checkpoint_close_verified=False,
    guard_faults='fired_state_survives_cancel',
    publication_margin_is_guarantee=False, original_thresholds_unchanged=True)


class ConnectDeadline:
    """Last-resort process bound for blocked connect, acquisition or close.

    Default SIGTERM is required, never installed or replaced. Abrupt exit may
    leave only the synced archive prefix and missing in-memory witness tails.
    """
    def __init__(self, deadline, *, clock=time.monotonic):
        require(signal.getsignal(signal.SIGTERM)==signal.SIG_DFL,
                'connection deadline requires unchanged default SIGTERM')
        self.lock, self.armed = threading.Lock(), True
        self.fired=threading.Event()
        self.timer=threading.Timer(max(0,deadline-clock()),self.interrupt)
        self.timer.daemon=True
        self.timer.start()

    def interrupt(self):
        with self.lock:
            if self.armed:
                self.armed=False
                self.fired.set()
                os.kill(os.getpid(),signal.SIGTERM)

    def cancel(self):
        with self.lock:
            self.armed=False
        self.timer.cancel();self.timer.join(timeout=1)


class DeadlineInterrupt:
    """Emergency interruption and normal completion have exclusive owners.

    Normal completion claims/disarms under the same lock used by the callback,
    before local close. A callback that already won cannot become normal success.
    No lock, timer or I/O is added inside the application-return clock brackets.
    """
    def __init__(self, raw_socket, deadline, *, clock=time.monotonic,
                 normal_deadline=None, phase='socket', timer_factory=None):
        self.socket, self.fired, self.error = raw_socket, threading.Event(), None
        self.lock, self.armed, self.owner = threading.Lock(), True, 'pending'
        self.clock=clock
        self.deadline, self.normal_deadline, self.phase = deadline, normal_deadline, phase
        self.completed_at = None
        self.timer = (threading.Timer if timer_factory is None else timer_factory)(
            max(0, deadline-clock()), self.interrupt)
        self.timer.daemon = True
        self.timer.start()

    def interrupt(self):
        with self.lock:
            if not self.armed:
                return
            self.armed, self.owner = False, 'emergency'
            self.fired.set()
            try:
                # Do not mutate SSLSocket's Python _sslobj during SSL_write.
                socket.socket.shutdown(self.socket, socket.SHUT_RDWR)
            except OSError as exc:
                self.error = short_error(exc)

    def claim_normal(self, connection, at):
        with self.lock:
            require(self.armed and self.owner=='pending' and not self.fired.is_set(),
                    'emergency interruption cannot establish normal completion')
            require(self.normal_deadline is not None
                    and number(self.normal_deadline)<=number(at)<number(self.deadline),
                    'normal completion outside declared stop interval')
            require(connection.state==State.OPEN,
                    'transport already closing at stop; closure timing unknown')
            completed=self.clock()
            require(number(at)<=number(completed)<number(self.deadline),
                    'normal completion missed emergency cutoff or clock regressed')
            self.armed, self.owner, self.completed_at = False, 'acquisition_thread', completed
            self.timer.cancel()
            return completed

    def cancel(self):
        with self.lock:
            self.armed=False
            if self.owner=='pending':
                self.owner='cancelled'
        self.timer.cancel()
        self.timer.join(timeout=1)

    def receipt(self):
        with self.lock:
            return dict(phase=self.phase,owner=self.owner,fired=self.fired.is_set(),
                error=self.error,normal_deadline=self.normal_deadline,
                emergency_deadline=self.deadline,completed_at=self.completed_at)


def normal_completion_proven(result):
    """Prospective linkage only; never reinterpret an older recording."""
    try:
        value=result['normal_completion']
        receipts=result['deadline_interrupts']
        number(result['attempted'])
        return (result['stop_policy_sha256']==payload_hash(STOP_POLICY)
            and isinstance(receipts,list) and len(receipts)==2 and value==receipts[1]
            and receipts[0]['phase']=='subscription'
            and all(x['fired'] is False and x['error'] is None for x in receipts)
            and value['phase']=='acquisition'
            and value['owner']=='acquisition_thread' and value['fired'] is False
            and value['error'] is None
            and value['normal_deadline']==result['acquisition_deadline']
            and value['completed_at']==result['acquisition_ended']
            and number(value['normal_deadline'])<=number(value['completed_at'])
                <number(value['emergency_deadline'])
            and value['emergency_deadline']==min(result['acquisition_deadline']
                +STOP_POLICY['emergency_grace_seconds'],
                result['attempted']+STOP_POLICY['acquisition_hard_seconds']))
    except (ContractError, KeyError, TypeError, ValueError):
        return False


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


def creation_notice(obj, spec):
    """Narrow raw CTF creation metadata; never accept disguised book/trade data."""
    if not isinstance(obj,dict) or obj.get('event_type')!='new_market':return False
    condition=obj.get('market');assets=obj.get('assets_ids');outcomes=obj.get('outcomes')
    if (not isinstance(condition,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',condition)
            or not isinstance(assets,list) or not 2<=len(assets)<=64
            or any(not isinstance(v,str) or not v.isascii() or not v.isdecimal() for v in assets)
            or len(set(assets))!=len(assets) or not isinstance(outcomes,list)
            or len(outcomes)!=len(assets) or any(not isinstance(v,str) or not v for v in outcomes)):
        return False
    if any(k in obj for k in ('asset_id','price_changes','bids','asks','price','size','side','payload','type','winning_asset_id')):
        return False
    if 'condition_id' in obj and obj['condition_id']!=condition:return False
    if 'clob_token_ids' in obj and obj['clob_token_ids']!=assets:return False
    selected=set(spec['asset_ids'])
    return (set(assets)==selected if condition==spec['condition_id']
            else not selected.intersection(assets))


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
    if creation_notice(obj,spec):return False
    for name in ('market','condition_id'):
        if isinstance(obj.get(name),str) and obj[name]!=spec['condition_id']:return True
    for name in ('asset_id','winning_asset_id'):
        if isinstance(obj.get(name),str) and obj[name] not in spec['asset_ids']:return True
    for name in ('assets_ids','clob_token_ids'):
        values=obj.get(name)
        if isinstance(values,list) and any(isinstance(v,str) and v not in spec['asset_ids'] for v in values):return True
    changes = obj.get('price_changes')
    if isinstance(changes, list):
        return any(isinstance(change, dict) and isinstance(change.get('asset_id'), str)
                   and change['asset_id'] not in spec['asset_ids'] for change in changes)
    return False


def collect(raw_bundle, spec, root, *, epoch_ns, observer, execute=False,
            clock=utc_now, monotonic=time.monotonic, connect_factory=None,
            guard=None, interrupt_factory=DeadlineInterrupt, connect_guard_factory=ConnectDeadline,
            tls_context=None, before_close=None, recovery_policy=None,
            pause=time.sleep, uniform=None):
    """Actual public connection by default; tests explicitly inject local transport.

    Source/runtime/market approval is checked by the outer worker before this
    explicit acquisition gate. This function never starts a unit or schedules one.
    """
    require(execute is True, 'explicit public study acquisition required')
    require(type(epoch_ns) is int and epoch_ns >= 0, 'fixed integer study epoch required')
    from infra.stream.recorder_public_recovery import Epochs, POLICY as RECOVERY_POLICY, retry_delay
    recovering = recovery_policy is not None
    require(not recovering or recovery_policy == RECOVERY_POLICY, 'prospective recovery policy drift')
    expected = stream_plan(raw_bundle, segmented=True, max_seconds=90, max_frames=60000, resilient=recovering)
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
    conn, interrupt, hard_stop = None, None, None
    normal_completion = None
    frames, ready, attempted, closed, acquisition_ended, deadline = 0, None, None, None, None, None
    status, error, last_safe = 'before_connect', None, None
    terminal, interrupt_receipts, close_errors = [], [], []
    snapshots, connections, epochs = [], 0, Epochs(spec) if recovering else None
    snapshots_by_connection = {}
    transport_error = None

    def finish_interrupt():
        nonlocal interrupt
        if interrupt is not None:
            interrupt.cancel()
            receipt=interrupt.receipt()
            interrupt_receipts.append(receipt)
            interrupt = None
            return receipt

    def transport(call, *args, **kwargs):
        nonlocal transport_error
        from websockets.exceptions import ConnectionClosed
        try:
            return call(*args, **kwargs)
        except (OSError,ConnectionClosed) as exc:
            transport_error=exc
            raise

    def run_connection():
        nonlocal conn, interrupt, frames, ready, last_safe, status, snapshots
        connection_started = monotonic()
        readiness = min(epoch-1 if connections==1 else deadline, connection_started+10)
        require(readiness > connection_started, 'connection readiness missed')
        # connect() enforces its own handshake timeout; after return the control
        # watchdog also bounds a blocked subscription write and later sends.
        connecting=connect_guard_factory(readiness,clock=monotonic)
        try:
            conn = transport(connect_factory, ENDPOINT, open_timeout=readiness-connection_started,
                close_timeout=5, max_size=262144, max_queue=16, compression=None,
                ping_interval=None, proxy=None, **({'ssl':tls_context} if tls_context is not None else {}))
        finally:
            connecting.cancel()
        require(not connecting.fired.is_set(),'connection process guard fired')
        interrupt = interrupt_factory(conn.socket, readiness, clock=monotonic,phase='subscription')
        transport(conn.send,json.dumps(spec['subscription']))
        ready = monotonic()
        require(ready < readiness, 'subscription readiness missed')
        subscription=finish_interrupt()
        require(not subscription['fired'] and subscription['error'] is None,
                'emergency interruption during subscription')
        emergency=min(deadline+STOP_POLICY['emergency_grace_seconds'],
                      attempted+STOP_POLICY['acquisition_hard_seconds'])
        interrupt = interrupt_factory(conn.socket, emergency, clock=monotonic,
                                      normal_deadline=deadline,phase='acquisition')
        log.append('subscribed', dict(connection=connections))
        if recovering: epochs.subscribe(ready)
        last_ping = last_pong = ready
        status = 'scheduled_stop'
        while True:
            require(not interrupt.fired.is_set(),'emergency acquisition interruption')
            now = monotonic()
            if now >= deadline:
                break
            if frames >= 60000:
                status = 'frame_limit'
                break
            if recovering:
                reason = epochs.reason(now)
                if reason: raise ContractError(reason)
            if now-last_pong >= 30:
                raise ContractError('pong_timeout')
            if now-last_ping >= 10:
                transport(conn.send,'PING')
                last_ping = monotonic()
                log.append('ping_sent', dict(connection=connections))
            try:
                remaining = deadline-monotonic()
                if remaining <= 0:
                    break
                timeout = log.receive_timeout(min(1, remaining))
                remaining = deadline-monotonic()  # A sync must not adopt a stale receive budget.
                if remaining <= 0:
                    break
                frame = transport(conn.recv,timeout=min(timeout, remaining))
            except TimeoutError:
                log.sync_if_due()
                continue
            # Placement is unchanged: no validation/classification before the
            # existing monotonic/UTC/monotonic application-return operation.
            observer.application_return(frame, connections)
            timing_failure=observer.failure
            require(isinstance(frame, str) and len(frame.encode('utf-8')) <= 262144,
                    'binary_or_oversize_frame')
            classes = classify_frame(frame, spec)
            log.append('frame', dict(connection=connections, raw_text=frame, classification=classes))
            frames += 1
            require(timing_failure is None and observer.failure is None and len(observer.frames) == frames,
                    'required occurrence linkage/clock fault: '+str(observer.failure))
            last_safe = observer.frames[-1]['returned']['before']
            if frame == 'PONG':
                last_pong = monotonic()
            for event in classes:
                if event['scope'] == 'selected_market' and event['event_type'] == 'book':
                    snapshots = sorted(set(snapshots+event['asset_ids']))
            if recovering:
                epochs.observe(frame, classes, observer.frames[-1]['returned'])
            require(not contamination(frame, spec), 'explicit foreign asset/condition binding')
            if frames >= 60000:
                status = 'frame_limit'
                break
        if recovering and status=='scheduled_stop':
            at=interrupt.claim_normal(conn,monotonic())
            return at
        return monotonic()

    def close_for_retry():
        nonlocal conn
        if conn is None:return
        closing_conn,conn=conn,None
        closing=connect_guard_factory(min(monotonic()+5,attempted+90),clock=monotonic)
        try:
            closing_conn.close()
        except BaseException as exc:
            close_errors.append(short_error(exc))
            raise
        finally:
            closing.cancel()
            if closing.fired.is_set():
                close_errors.append('ContractError:retry close process guard fired')
                raise ContractError('retry close process guard fired')

    try:
        header=dict(spec=spec, spec_sha256=payload_hash(spec))
        if recovering:header['recovery_policy_sha256']=payload_hash(RECOVERY_POLICY)
        log.append('session_start', header)
        attempted = monotonic()
        deadline = min(epoch+65, attempted+90)
        hard_stop=connect_guard_factory(attempted+STOP_POLICY['acquisition_hard_seconds'],clock=monotonic)
        while connections < (RECOVERY_POLICY['max_connections'] if recovering else 1):
            connections += 1
            snapshots=[]
            if recovering:epochs.begin(monotonic())
            log.append('connect_attempt', dict(connection=connections))
            try:
                ended=run_connection()
                if recovering:
                    log.append('connection_epoch',epochs.end(ended,None,normal=status=='scheduled_stop'))
                break
            except BaseException as exc:
                if not recovering:raise
                fault=short_error(exc)
                terminal.append(dict(connection=connections,type=type(exc).__name__,error=fault))
                if error is None:error=fault
                row=epochs.end(monotonic(),fault)
                log.append('connection_gap',dict(connection=connections,reason=fault[:120],
                    unavailable_from=row['available_until']))
                log.append('connection_epoch',row)
                from websockets.exceptions import ConnectionClosed
                recoverable=(exc is transport_error and isinstance(exc,(OSError,ConnectionClosed))
                    and not isinstance(exc,ssl.SSLCertVerificationError)
                    or type(exc) is ContractError and str(exc) in
                        ('initial_books_timeout','selected_book_data_silence','stale_timestamped_book_flow','pong_timeout'))
                receipt=finish_interrupt()
                if receipt and (receipt['fired'] or receipt['error']):recoverable=False
                if not recoverable:raise
                status='connection_limit' if connections>=RECOVERY_POLICY['max_connections'] else 'interrupted'
                if connections>=RECOVERY_POLICY['max_connections'] or monotonic()>=deadline:break
                # Only the acquisition owner closes/retries, before another socket exists.
                # Keep the original total process guard armed through close/backoff.
                close_for_retry()
                delay=retry_delay(connections,**({'uniform':uniform} if uniform is not None else {}))
                until=min(monotonic()+delay,deadline)
                log.append('retry_wait',dict(connection=connections,seconds=until-monotonic()))
                while monotonic()<until:
                    guard.check();log.sync_if_due()
                    pause(min(.1,until-monotonic()))
                if monotonic()>=deadline:break
            finally:
                snapshots_by_connection[str(connections)]=snapshots
    except BaseException as exc:
        # Never clear a receive/close fault just because the deadline fired.
        status, error = 'interrupted', short_error(exc)
        terminal.append(dict(type=type(exc).__name__, error=error))
        try:
            if not recovering:log.append('connection_gap', dict(connection=connections, reason=error[:120]))
        except BaseException as log_exc:
            close_errors.append(short_error(log_exc))
    finally:
        acquisition_ended = monotonic()
        if conn is not None and status=='scheduled_stop' and error is None and not recovering:
            try:
                acquisition_ended=interrupt.claim_normal(conn,acquisition_ended)
            except BaseException as exc:
                status,error='interrupted',short_error(exc)
                terminal.append(dict(type=type(exc).__name__,error=error))
                try:
                    log.append('connection_gap',dict(connection=1,reason=error[:120]))
                except BaseException as log_exc:
                    close_errors.append(short_error(log_exc))
        receipt=finish_interrupt()
        if receipt is not None and receipt['fired'] and error is None:
            status,error='interrupted','ContractError:emergency socket interruption'
            terminal.append(dict(type='ContractError',error=error))
            try:
                log.append('connection_gap',dict(connection=1,reason=error))
            except BaseException as log_exc:
                close_errors.append(short_error(log_exc))
        if receipt is not None and receipt['owner']=='acquisition_thread':
            normal_completion=receipt
        summary = dict(status=status, frames=frames, connections=connections,
            event_counts={}, book_snapshot_assets_by_connection=snapshots_by_connection,
            continuous_coverage_proven=False, orders_authorized=False)
        if recovering:
            if epochs.current is not None and epochs.current['ended'] is None:
                epochs.end(acquisition_ended,error or 'incomplete_epoch')
            # Final linked marker includes failed attempts and preserves their faults.
            try:log.append('recovery_end',dict(policy_sha256=payload_hash(RECOVERY_POLICY),epochs=epochs.rows))
            except BaseException as exc:close_errors.append(short_error(exc))
        # Seal the actual writer/watermarks before a potentially blocking close.
        # The existing acquisition process guard still bounds this work; it is
        # not a guarantee that finalization or publication can finish in time.
        try:
            log.append('session_end', summary)
        except BaseException as exc:
            close_errors.append(short_error(exc))
        try:
            log.close()
        except BaseException as exc:
            close_errors.append(short_error(exc))
        if close_errors and error is None:error=close_errors[0]

        def result_at(closed, close_completed):
            value = dict(summary=summary,error=error,close_errors=list(close_errors),
                terminal_receive=list(terminal),deadline_interrupts=list(interrupt_receipts),
                stop_policy_sha256=payload_hash(STOP_POLICY),normal_completion=normal_completion,
                publication_policy_sha256=payload_hash(PUBLICATION_POLICY),
                notice_policy_sha256=payload_hash(NOTICE_POLICY),close_completed=close_completed,
                ready=ready,attempted=attempted,closed=closed,last_safe=last_safe,
                acquisition_ended=acquisition_ended,acquisition_deadline=deadline,
                epoch_ns=epoch_ns,original_application_verdict='fail',orders_authorized=False)
            if recovering:
                from copy import deepcopy
                value.update(recovery_policy_sha256=payload_hash(RECOVERY_POLICY),connection_epochs=deepcopy(epochs.rows))
            return value

        if before_close is not None:
            try:before_close(result_at(None,False))
            except BaseException as exc:
                close_errors.append(short_error(exc))
                if error is None:error=close_errors[0]
        if hard_stop is not None:
            hard_stop.cancel()
            if hard_stop.fired.is_set():
                close_errors.append('ContractError:acquisition process guard fired')
        close_completed=False
        if conn is not None:
            closing=connect_guard_factory(monotonic()+STOP_POLICY['close_hard_seconds'],clock=monotonic)
            try:
                conn.close()
                close_completed=True
            except BaseException as exc:
                close_errors.append(short_error(exc))
            finally:
                closing.cancel()
                if closing.fired.is_set():
                    close_completed=False
                    close_errors.append('ContractError:close process guard fired')
        closed=monotonic()
        if close_errors and error is None:error=close_errors[0]
    return result_at(closed,close_completed)
