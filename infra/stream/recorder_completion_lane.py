"""Isolated recorder completion prototype; frozen legacy collector stays unchanged."""
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


class CompletionStreamLog(SegmentedStreamLog):
    def __init__(self, path, clock, monotonic, policy, profiler=None, completion_observer=None):
        verify_reference_sources()
        self.completion_observer = completion_observer
        super().__init__(path, clock, monotonic, policy, profiler=profiler)

    def _witness(self, event, **fields):
        if self.completion_observer is not None:
            try:
                self.completion_observer.boundary(event, **fields)
            except Exception as exc:
                # Observation must never swallow/replay a native write or barrier.
                try:
                    self.completion_observer.disable(type(exc).__name__)
                except Exception:
                    pass
                self.completion_observer = None

    def sync(self):
        started = self.monotonic() if self.profiler else None
        try:
            self.writer.flush()
            self.raw.flush()
        except Exception as exc:
            if self.completion_observer is not None:
                self._witness("sync_failed", error=type(exc).__name__)
            raise
        if self.completion_observer is not None:
            self._witness("sync_begin", ordinal=self.ordinal-1, record_sha256=self.previous)
        try:
            os.fsync(self.raw.fileno())
        except Exception as exc:
            if self.completion_observer is not None:
                self._witness("sync_failed", error=type(exc).__name__)
            raise
        if self.completion_observer is not None:
            self._witness("sync_complete")
        self.pending, self.last_sync = 0, self.monotonic()
        if self.profiler:
            self.profiler.record("fsync", self.monotonic() - started)

    def _seal(self):
        started = self.monotonic() if self.profiler else None
        try:
            self.writer.close()
            self.raw.flush()
        except Exception as exc:
            if self.completion_observer is not None:
                self._witness("sync_failed", error=type(exc).__name__)
            raise
        if self.completion_observer is not None:
            self._witness("sync_begin", ordinal=self.ordinal-1, record_sha256=self.previous)
        try:
            os.fsync(self.raw.fileno())
        except Exception as exc:
            if self.completion_observer is not None:
                self._witness("sync_failed", error=type(exc).__name__)
            raise
        if self.completion_observer is not None:
            self._witness("sync_complete")
        self.raw.close()
        target = self.root / ("segment-%06d.gz" % self.index)
        self.partial.rename(target)
        artifact = {"schema_version": SEGMENT_SCHEMA, "index": self.index,
                    "file": target.name, "compressed_sha256": file_hash(target),
                    "compressed_bytes": target.stat().st_size,
                    "uncompressed_bytes": self.segment_bytes, "records": self.segment_records,
                    "first_ordinal": self.first_ordinal, "first_previous_sha256": self.first_previous,
                    "last_record_sha256": self.previous,
                    "previous_segment_sha256": self.segments[-1]["segment_sha256"] if self.segments else None}
        artifact["segment_sha256"] = payload_hash(artifact)
        exclusive_json(self.root / ("segment-%06d.json" % self.index), artifact)
        self.segments.append(artifact)
        self.compressed_size += artifact["compressed_bytes"]
        self.raw = self.writer = None
        if self.profiler:
            self.profiler.record("seal", self.monotonic() - started)

    def append(self, kind, payload):
        started = self.monotonic() if self.profiler else None
        row = {"schema_version": "qcrl.public_market_stream_record.v1", "ordinal": self.ordinal,
               "previous_sha256": self.previous, "received_at_utc": utc_text(self.clock()),
               "local_monotonic_seconds": self.monotonic(), "kind": kind, "payload": payload}
        row["record_sha256"] = payload_hash(row)
        content = (json.dumps(row, sort_keys=True) + "\n").encode("utf-8")
        if self.profiler:
            self.profiler.record("encode_hash", self.monotonic() - started)
        if len(content) > 4 * 1024**2:
            raise StreamQuotaError("encoded stream record exceeds bounded reserve")
        # Reserve room for a terminal failure/quota summary, even at the data cap.
        if kind != "session_end" and (
                self.size + len(content) > self.policy["max_uncompressed_bytes"]
                or self.compressed_size + self.raw.tell() + len(content) > self.policy["max_compressed_bytes"] - 4 * 1024**2):
            raise StreamQuotaError("segmented stream total-byte budget reached")
        if self.segment_records and self.segment_bytes + len(content) > self.policy["segment_uncompressed_bytes"]:
            self._seal()
            self._open()
        write_started = self.monotonic() if self.profiler else None
        try:
            self.writer.write(content)
        except Exception as exc:
            if self.completion_observer is not None:
                self._witness("append_failed", error=type(exc).__name__)
            raise
        if self.completion_observer is not None:
            self._witness("append_complete", row=row)
        if self.profiler:
            self.profiler.record("compress_write", self.monotonic() - write_started)
        self.pending += 1
        self.size += len(content)
        self.segment_bytes += len(content)
        self.segment_records += 1
        self.ordinal += 1
        self.previous = row["record_sha256"]
        self.final = kind == "session_end"
        if kind != "frame" or self.pending >= 64 or self.monotonic() - self.last_sync >= 1:
            self.sync()
        if self.profiler:
            self.profiler.record("append", self.monotonic() - started)


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
        log = (CompletionStreamLog(path, clock, monotonic, spec["storage"], profiler=profiler) if profiler
               else CompletionStreamLog(path, clock, monotonic, spec["storage"]))
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
                        frame = socket.recv(timeout=min(1, max(0.001, spec["max_seconds"] - (now - started))))
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
