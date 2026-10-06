"""Bounded public five-minute market recorder; no account or order interfaces."""

import json
import os
from pathlib import Path
import time
from datetime import timedelta

from .acquisition import utc_now, utc_text
from .binance_source import _time
from .bundle import normalize_bundle
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .stream_segments import SegmentedStreamLog, StreamQuotaError, verify_segments


ENDPOINT = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
SPEC_SCHEMA = "qcrl.public_market_stream_spec.v2"
ROW_SCHEMA = "qcrl.public_market_stream_record.v1"


class StreamTransportError(RuntimeError):
    pass


def transport_reason(exc):
    """Preserve bounded close codes, not arbitrary server text or credentials."""
    reason = type(exc).__name__
    for field in ("rcvd", "sent"):
        code = getattr(getattr(exc, field, None), "code", None)
        if type(code) is int:
            reason += ":" + field + "_code=" + str(code)
    return reason


def stream_plan(raw_bundle, *, max_seconds=360, max_frames=100000, segmented=False, profiling=False):
    market = normalize_bundle(raw_bundle)["market_contract"]
    if (_time(market["terms"]["end_at_utc"]) - _time(market["terms"]["event_start_at_utc"])).total_seconds() != 300:
        raise ContractError("stream lane requires an explicit five-minute market interval")
    if type(segmented) is not bool:
        raise ContractError("segmented must be a boolean")
    if type(profiling) is not bool or (profiling and not segmented):
        raise ContractError("profiling requires explicit segmented mode")
    for value, maximum in ((max_seconds, 600), (max_frames, 1000000 if segmented else 100000)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ContractError("stream duration/frame limit outside bounded range")
    plan = {
        "schema_version": "qcrl.public_market_stream_spec.v3" if segmented else SPEC_SCHEMA, "endpoint": ENDPOINT,
        "raw_bundle_sha256": raw_bundle["bundle_sha256"],
        "market_contract_sha256": market["contract_sha256"],
        "market_id": market["identity"]["market_id"], "condition_id": market["identity"]["condition_id"],
        "asset_ids": [o["token_id"] for o in market["outcomes"]],
        "event_start_at_utc": market["terms"]["event_start_at_utc"], "event_end_at_utc": market["terms"]["end_at_utc"],
        "max_seconds": max_seconds, "max_frames": max_frames,
        "preopen_seconds": 30, "postclose_seconds": 30,
        "max_frame_bytes": 262144, "max_log_bytes": 134217728,
        "fsync_every_records": 64, "fsync_interval_seconds": 1,
        "heartbeat_seconds": 10, "pong_timeout_seconds": 30,
        "max_connections": 3, "reconnect_pause_seconds": 2,
        "subscription": {"type": "market", "assets_ids": [o["token_id"] for o in market["outcomes"]],
                         "custom_feature_enabled": True},
        "orders_authorized": False,
    }
    if segmented:
        plan["storage"] = {"format": "hash_linked_gzip_segments.v1", "segment_uncompressed_bytes": 8 * 1024**2,
                           "max_uncompressed_bytes": 1024**3, "max_compressed_bytes": 256 * 1024**2,
                           "gzip_level": 1, "footer_reserve_bytes": 4 * 1024**2,
                           "max_encoded_record_bytes": 4 * 1024**2, "counter_key_limit": 128}
        plan.pop("max_log_bytes")
    if profiling:
        from copy import deepcopy
        from .stream_profiling import POLICY
        plan["profiling"] = deepcopy(POLICY)
    return plan


def classify_frame(frame, spec):
    """Classify without changing raw bytes, applying book deltas, or claiming fills."""
    if frame == "PONG":
        return [{"event_type": "PONG", "scope": "heartbeat"}]
    try:
        data = json.loads(frame)
    except (ValueError, TypeError):
        return [{"event_type": "unparsed", "scope": "unknown"}]
    events = data if isinstance(data, list) else [data]
    result = []
    for event in events:
        if not isinstance(event, dict):
            result.append({"event_type": "unparsed", "scope": "unknown"})
            continue
        kind = event.get("event_type", "unknown")
        condition = event.get("market", event.get("condition_id"))
        assets = []
        if event.get("asset_id"):
            assets.append(event["asset_id"])
        if isinstance(event.get("price_changes"), list):
            assets.extend(c.get("asset_id") for c in event["price_changes"] if isinstance(c, dict))
        if isinstance(event.get("assets_ids"), list):
            assets.extend(event["assets_ids"])
        scoped = condition == spec["condition_id"] and bool(assets) and all(a in spec["asset_ids"] for a in assets)
        if kind == "book" and (not isinstance(event.get("bids"), list) or not isinstance(event.get("asks"), list)):
            scoped = False
        result.append({"event_type": kind if isinstance(kind, str) else "unknown",
                       "scope": "selected_market" if scoped else "unconfirmed_or_other_market",
                       "asset_ids": assets})
    return result


class StreamLog:
    def __init__(self, path, clock, monotonic, maximum):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("x", encoding="utf-8")
        self.clock, self.monotonic, self.maximum = clock, monotonic, maximum
        self.ordinal, self.previous, self.size = 0, None, 0
        self.pending, self.last_sync = 0, monotonic()

    def sync(self):
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.pending, self.last_sync = 0, self.monotonic()

    def sync_if_due(self):
        if self.pending and self.monotonic() - self.last_sync >= 1:
            self.sync()

    def append(self, kind, payload):
        row = {"schema_version": ROW_SCHEMA, "ordinal": self.ordinal,
               "previous_sha256": self.previous, "received_at_utc": utc_text(self.clock()),
               "local_monotonic_seconds": self.monotonic(), "kind": kind, "payload": payload}
        row["record_sha256"] = payload_hash(row)
        content = json.dumps(row, sort_keys=True) + "\n"
        size = len(content.encode("utf-8"))
        if self.size + size > self.maximum:
            raise ContractError("stream log size limit reached; existing prefix retained")
        self.handle.write(content)
        self.handle.flush()
        self.pending += 1
        if kind != "frame" or self.pending >= 64 or self.monotonic() - self.last_sync >= 1:
            self.sync()
        self.size += size
        self.ordinal += 1
        self.previous = row["record_sha256"]

    def close(self):
        if self.pending:
            self.sync()
        self.handle.close()


def live_connector():
    try:
        from websockets.sync.client import connect
        from websockets.exceptions import WebSocketException
    except ImportError as exc:
        raise ContractError("stream runtime requires infra/stream/requirements.txt; existing collector is unchanged") from exc
    class Socket:
        def __init__(self):
            try:
                self.connection = connect(ENDPOINT, open_timeout=10, close_timeout=5,
                                          max_size=262144, max_queue=16, compression=None,
                                          ping_interval=None, proxy=None)
            except (OSError, WebSocketException, TimeoutError) as exc:
                raise StreamTransportError(transport_reason(exc)) from exc

        def send(self, value):
            try:
                self.connection.send(value)
            except (OSError, WebSocketException) as exc:
                raise StreamTransportError(transport_reason(exc)) from exc

        def recv(self, timeout):
            try:
                return self.connection.recv(timeout=timeout)
            except TimeoutError:
                # TimeoutError is an OSError subclass: idle reads must reach
                # the recorder's idle branch, not consume reconnect attempts.
                raise
            except (OSError, WebSocketException) as exc:
                raise StreamTransportError(transport_reason(exc)) from exc

        def close(self):
            self.connection.close()
    return Socket


def collect_market_stream(raw_bundle, spec, path, *, connector=None, clock=utc_now,
                          monotonic=time.monotonic, pause=time.sleep):
    segmented = spec.get("schema_version") == "qcrl.public_market_stream_spec.v3"
    expected = stream_plan(raw_bundle, max_seconds=spec.get("max_seconds"), max_frames=spec.get("max_frames"),
                           segmented=segmented, profiling="profiling" in spec)
    if expected != spec:
        raise ContractError("stream spec differs from verified public-only plan")
    stop = _time(spec["event_end_at_utc"]) + timedelta(seconds=spec["postclose_seconds"])
    begin = _time(spec["event_start_at_utc"]) - timedelta(seconds=spec["preopen_seconds"])
    if not begin <= clock() < stop:
        raise ContractError("capture must start within declared market lifecycle window")
    connector = connector or live_connector()
    started = monotonic()
    profiler = None
    if "profiling" in spec:
        from .stream_profiling import StreamProfiler
        profiler = StreamProfiler(monotonic=monotonic)
    if segmented:
        log = (SegmentedStreamLog(path, clock, monotonic, spec["storage"], profiler=profiler) if profiler
               else SegmentedStreamLog(path, clock, monotonic, spec["storage"]))
    else:
        log = StreamLog(path, clock, monotonic, spec["max_log_bytes"])
    counts, snapshots = {}, {}
    frames, connections, status = 0, 0, "duration_limit"
    try:
        log.append("session_start", {"spec": spec, "spec_sha256": payload_hash(spec)})
        if profiler:
            profiler.sample(log, force=True)
        while monotonic() - started < spec["max_seconds"] and frames < spec["max_frames"] and clock() < stop:
            if connections >= spec["max_connections"]:
                status = "connection_limit"
                break
            connections += 1
            socket = None
            try:
                log.append("connect_attempt", {"connection": connections})
                socket = connector()
                socket.send(json.dumps(spec["subscription"]))
                log.append("subscribed", {"connection": connections})
                snapshots[str(connections)] = []
                last_ping = last_pong = monotonic()
                while monotonic() - started < spec["max_seconds"] and frames < spec["max_frames"] and clock() < stop:
                    now = monotonic()
                    if now - last_ping >= spec["heartbeat_seconds"]:
                        socket.send("PING")
                        last_ping = now
                        log.append("ping_sent", {"connection": connections})
                    if now - last_pong >= spec["pong_timeout_seconds"]:
                        raise StreamTransportError("pong_timeout")
                    try:
                        read_started = monotonic() if profiler else None
                        frame = socket.recv(timeout=min(1, max(0.001, spec["max_seconds"] - (now - started))))
                    except TimeoutError:
                        if profiler:
                            profiler.record("recv_wait", monotonic() - read_started)
                            profiler.sample(log)
                        log.sync_if_due()
                        continue
                    if profiler:
                        received_mono, received_utc = monotonic(), utc_text(clock())
                        profiler.record("recv_wait", received_mono - read_started)
                    if not isinstance(frame, str) or len(frame.encode("utf-8")) > spec["max_frame_bytes"]:
                        raise StreamTransportError("binary_or_oversize_frame")
                    classify_started = monotonic() if profiler else None
                    classes = classify_frame(frame, spec)
                    frame_payload = {"connection": connections, "raw_text": frame, "classification": classes}
                    if profiler:
                        profiler.record("classify", monotonic() - classify_started)
                        frame_payload.update(socket_received_at_utc=received_utc,
                                             socket_received_monotonic_seconds=received_mono)
                    log.append("frame", frame_payload)
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
                log.append("connection_gap", {"connection": connections, "reason": str(exc)[:120]})
                if monotonic() - started < spec["max_seconds"]:
                    pause(min(spec["reconnect_pause_seconds"], spec["max_seconds"] - (monotonic() - started)))
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


def verify_stream_log(path):
    if Path(path).is_dir():
        return verify_segments(path)
    previous, rows, final = None, 0, False
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.endswith("\n"):
                raise ContractError("truncated stream log line; preserve original prefix")
            row = json.loads(line)
            verify_artifact_hash(row, "record_sha256", "stream record")
            if row.get("schema_version") != ROW_SCHEMA or row["ordinal"] != rows or row["previous_sha256"] != previous:
                raise ContractError("stream log chain mismatch")
            if final or (rows == 0 and row["kind"] != "session_start"):
                raise ContractError("invalid stream session boundary")
            final = row["kind"] == "session_end"
            if rows == 0:
                payload = row["payload"]
                if payload_hash(payload["spec"]) != payload["spec_sha256"]:
                    raise ContractError("stream header spec hash mismatch")
            previous = row["record_sha256"]
            rows += 1
    if not rows:
        raise ContractError("empty stream log")
    return {"records": rows, "final_record_sha256": previous, "session_end_present": final,
            "continuous_coverage_proven": False}
