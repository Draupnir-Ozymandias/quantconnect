"""Prospective deadline-aware isolated recorder; original lane remains frozen."""
from datetime import timedelta
import json
import os
from pathlib import Path
import time

from execution_truth.acquisition import utc_now, utc_text
from execution_truth.binance_source import _time
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.market_stream import (StreamLog, StreamTransportError, stream_plan, live_connector,
                            observed_connector, classify_frame)
from execution_truth.stream_segments import (SegmentedStreamLog, StreamQuotaError, SEGMENT_SCHEMA,
                              exclusive_json, file_hash)

REFERENCE_FILES = {
    "execution_truth/market_stream.py": "3fdce54db2c3596175afdc2403ac0a140f8f99db1e43a78c72c750cc90694a47",
    "execution_truth/stream_segments.py": "ed3245df20a4d6cd3fdc21481d576aeb5c135d093b876a6cb09949af4791462c",
}


def verify_reference_sources():
    root = Path(__file__).resolve().parents[2]
    if any(file_hash(root/name) != digest for name, digest in REFERENCE_FILES.items()):
        raise ContractError("isolated completion reference source changed")


from infra.stream.recorder_completion_lane import CompletionStreamLog

PERSISTENCE_POLICY = dict(schema_version='qcrl.recorder_persistence_schedule.v2',
    durable_bound_seconds=2, persistence_reserve_seconds=1,
    pending_age_seconds=1, sync_interval_seconds=1, fsync_every_records=64,
    reserve_is_guarantee=False, earlier_results_superseded=False)


class DeadlineStreamLog(CompletionStreamLog):
    def __init__(self, *args, **kwargs):
        self.pending_deadline = None
        super().__init__(*args, **kwargs)

    def append(self, kind, payload):
        if kind == 'frame' and self.pending_deadline is None:
            pending = getattr(self.completion_observer, 'pending', None)
            returned = pending['returned']['before'] if pending else self.monotonic()
            self.pending_deadline = returned + PERSISTENCE_POLICY['pending_age_seconds']
        super().append(kind, payload)
        # Parent count/time checks are retained; also check oldest return age.
        self.sync_if_due()

    def sync(self):
        super().sync()
        self.pending_deadline = None

    def sync_if_due(self):
        if self.pending and self.monotonic() >= self.sync_deadline():
            self.sync()

    def sync_deadline(self):
        return min(self.last_sync + PERSISTENCE_POLICY['sync_interval_seconds'],
                   self.pending_deadline if self.pending_deadline is not None else float('inf'))

    def receive_timeout(self, cap):
        self.sync_if_due()
        if not self.pending:
            return cap
        remaining = self.sync_deadline() - self.monotonic()
        if remaining <= 0:
            self.sync()
            return cap
        return min(cap, remaining)


def collect_with_completion(raw_bundle, spec, path, *, connector=None, clock=utc_now,
                          monotonic=time.monotonic, pause=time.sleep, clock_domain=None,
                          completion_observer=None):
    verify_reference_sources()
    if completion_observer is None:
        raise ContractError("isolated completion prototype requires explicit observer")
    if connector is None:
        raise ContractError("isolated completion prototype requires an injected offline connector")
    segmented = spec.get("schema_version") in ("qcrl.public_market_stream_spec.v3", "qcrl.public_market_stream_spec.v4",
                                               "qcrl.public_market_stream_spec.v5", "qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7")
    from execution_truth.receive_path import policy_version
    version = policy_version(spec["receive_path"]) if "receive_path" in spec else "v1"
    expected = stream_plan(raw_bundle, max_seconds=spec.get("max_seconds"), max_frames=spec.get("max_frames"),
                           segmented=segmented, profiling="profiling" in spec, resilient="resilience" in spec,
                           receive_path="receive_path" in spec, source_plan_sha256=spec.get("source_plan_sha256"),
                           receive_policy=version, freshness_telemetry="freshness_telemetry" in spec)
    if expected != spec:
        raise ContractError("stream spec differs from verified public-only plan")
    if completion_observer is not None:
        from .recorder_completion import CompletionWitnesses
        if not isinstance(completion_observer, CompletionWitnesses) or not segmented:
            raise ContractError("completion witnesses require explicit segmented prototype observer")
        if completion_observer.clock!=clock or completion_observer.monotonic!=monotonic:
            raise ContractError("completion witnesses must share the recorder's actual clocks")
        completion_observer.validate_spec(spec)
    stop = _time(spec["event_end_at_utc"]) + timedelta(seconds=spec["postclose_seconds"])
    begin = _time(spec["event_start_at_utc"]) - timedelta(seconds=spec["preopen_seconds"])
    if not begin <= clock() < stop:
        raise ContractError("capture must start within declared market lifecycle window")
    tracker = None
    header = {"spec": spec, "spec_sha256": payload_hash(spec)}
    if "receive_path" in spec:
        import uuid
        from execution_truth.receive_path import declare, ReceivePathTracker
        contract = declare(spec["source_plan_sha256"], clock_domain or "capture." + uuid.uuid4().hex,
                           stream_spec_sha256=payload_hash(spec), policy_version=version)
        if version == "v3":
            from execution_truth.receive_recovery import ReceiveRecoveryTracker
            tracker = ReceiveRecoveryTracker(contract)
        else:
            tracker = ReceivePathTracker(contract)
        header["receive_path_contract"] = contract
        connector = connector or observed_connector
    else:
        connector = connector or live_connector()
    started = monotonic()
    profiler = None
    if "profiling" in spec:
        from execution_truth.stream_profiling import StreamProfiler
        profiler = StreamProfiler(monotonic=monotonic)
    if segmented:
        log = (DeadlineStreamLog(path, clock, monotonic, spec["storage"], profiler=profiler) if profiler
               else DeadlineStreamLog(path, clock, monotonic, spec["storage"]))
    else:
        log = StreamLog(path, clock, monotonic, spec["max_log_bytes"])
    if completion_observer is not None:
        log.completion_observer = completion_observer
    counts, snapshots = {}, {}
    frames, connections, status = 0, 0, "duration_limit"
    try:
        log.append("session_start", header)
        if profiler:
            profiler.sample(log, force=True)
        while monotonic() - started < spec["max_seconds"] and frames < spec["max_frames"] and clock() < stop:
            if connections >= spec["max_connections"]:
                status = "connection_limit"
                break
            connections += 1
            socket = None
            freshness = None
            try:
                log.append("connect_attempt", {"connection": connections})
                socket = (connector(tracker, connections, clock=clock, monotonic=monotonic) if tracker else connector())
                if tracker:
                    log.append("receive_path_reset", socket.reset)
                socket.send(json.dumps(spec["subscription"]))
                log.append("subscribed", {"connection": connections})
                if "freshness_telemetry" in spec:
                    from execution_truth.connection_freshness import ConnectionFreshness
                    freshness = ConnectionFreshness(connections, spec["asset_ids"])
                    freshness.emit(log, monotonic(), "subscribed", force=True)
                watchdog = None
                if "resilience" in spec:
                    from execution_truth.stream_resilience import DataWatchdog
                    watchdog = DataWatchdog(spec["asset_ids"], monotonic())
                snapshots[str(connections)] = []
                last_ping = last_pong = monotonic()
                while monotonic() - started < spec["max_seconds"] and frames < spec["max_frames"] and clock() < stop:
                    now = monotonic()
                    if watchdog:
                        reason = watchdog.reason(now, _time(spec["event_start_at_utc"]) <= clock() < _time(spec["event_end_at_utc"]))
                        if reason:
                            raise StreamTransportError(reason)
                    if now - last_ping >= spec["heartbeat_seconds"]:
                        socket.send("PING")
                        last_ping = now
                        log.append("ping_sent", {"connection": connections})
                    if now - last_pong >= spec["pong_timeout_seconds"]:
                        raise StreamTransportError("pong_timeout")
                    try:
                        read_started = monotonic() if profiler else None
                        # One-second prospective persistence reserve inside the unchanged
                        # two-second end-to-end bound. No hard timing guarantee.
                        cap = min(1, max(0.001, spec["max_seconds"] - (monotonic() - started)))
                        frame = socket.recv(timeout=log.receive_timeout(cap))
                        if completion_observer is not None:
                            try:
                                completion_observer.application_return(frame, connections)
                            except Exception as exc:
                                try:
                                    completion_observer.disable(type(exc).__name__)
                                except Exception:
                                    pass
                                log.completion_observer = None
                                completion_observer = None
                        if tracker:
                            frame, receive_record = frame
                    except TimeoutError:
                        if profiler:
                            profiler.record("recv_wait", monotonic() - read_started)
                            profiler.sample(log)
                        log.sync_if_due()
                        if freshness:
                            freshness.emit(log, monotonic())
                        continue
                    if profiler:
                        received_mono, received_utc = monotonic(), utc_text(clock())
                        profiler.record("recv_wait", received_mono - read_started)
                    if not isinstance(frame, str) or len(frame.encode("utf-8")) > spec["max_frame_bytes"]:
                        raise StreamTransportError("binary_or_oversize_frame")
                    classify_started = monotonic() if profiler else None
                    classes = classify_frame(frame, spec)
                    if watchdog:
                        watchdog.observe(frame, classes, monotonic(), clock().timestamp())
                    frame_payload = {"connection": connections, "raw_text": frame, "classification": classes}
                    if tracker:
                        frame_payload["receive_path"] = receive_record
                    if profiler:
                        profiler.record("classify", monotonic() - classify_started)
                        frame_payload.update(socket_received_at_utc=received_utc,
                                             socket_received_monotonic_seconds=received_mono)
                    log.append("frame", frame_payload)
                    if freshness:
                        freshness.observe(frame, classes, receive_record)
                        freshness.emit(log, monotonic())
                    if profiler:
                        profiler.sample(log)
                    frames += 1
                    if frame == "PONG":
                        last_pong = monotonic()
                    for event in classes:
                        kind = event["event_type"] if len(event["event_type"]) <= 64 else "oversized_event_name"
                        key = event["scope"] + ":" + kind
                        if key not in counts and len(counts) >= 128:
                            key = "overflow_event_types"
                        counts[key] = counts.get(key, 0) + 1
                        if event["scope"] == "selected_market" and event["event_type"] == "book":
                            snapshots[str(connections)] = sorted(set(snapshots[str(connections)] + event["asset_ids"]))
            except StreamTransportError as exc:
                gap = {"connection": connections, "reason": str(exc)[:120]}
                if "freshness_telemetry" in spec:
                    from execution_truth.connection_freshness import close_diagnostics
                    gap["close_diagnostics"] = close_diagnostics(exc)
                log.append("connection_gap", gap)
                # Resilient mode closes before its jittered wait. Legacy wait
                # ordering remains unchanged for controlled comparisons.
                if "resilience" in spec and socket is not None:
                    socket.close()
                    socket = None
                if monotonic() - started < spec["max_seconds"] and connections < spec["max_connections"]:
                    delay = spec["reconnect_pause_seconds"]
                    if "resilience" in spec:
                        from execution_truth.stream_resilience import retry_delay
                        delay = retry_delay(connections)
                        log.append("retry_wait", {"connection": connections, "seconds": delay})
                    pause(max(0, min(delay, spec["max_seconds"] - (monotonic() - started), (stop - clock()).total_seconds())))
            finally:
                try:
                    if freshness:
                        freshness.emit(log, monotonic(), "connection_end", force=True)
                finally:
                    if socket is not None:
                        socket.close()
        if frames >= spec["max_frames"]:
            status = "frame_limit"
        elif clock() >= stop:
            status = "lifecycle_stop"
        summary = {"status": status, "frames": frames, "connections": connections,
                   "event_counts": counts, "book_snapshot_assets_by_connection": snapshots,
                   "continuous_coverage_proven": False, "orders_authorized": False}
        if profiler:
            profiler.sample(log, force=True)
        log.append("session_end", summary)
        return summary
    except StreamQuotaError as exc:
        summary = {"status": "storage_limit", "frames": frames, "connections": connections,
                   "event_counts": counts, "book_snapshot_assets_by_connection": snapshots,
                   "reason": str(exc), "continuous_coverage_proven": False, "orders_authorized": False}
        log.append("session_end", summary)
        return summary
    finally:
        log.close()
