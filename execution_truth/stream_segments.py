"""Exclusive compressed segments with row and segment integrity chains."""
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

from .acquisition import utc_text
from .contracts import ContractError, payload_hash, verify_artifact_hash

SEGMENT_SCHEMA = "qcrl.stream_segment.v1"
MANIFEST_SCHEMA = "qcrl.stream_manifest.v1"


class StreamQuotaError(ContractError):
    pass


def exclusive_json(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    directory_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SegmentedStreamLog:
    def __init__(self, path, clock, monotonic, policy, profiler=None):
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=False)
        self.clock, self.monotonic, self.policy = clock, monotonic, policy
        self.profiler = profiler
        self.ordinal, self.previous, self.size = 0, None, 0
        self.pending, self.last_sync = 0, monotonic()
        self.segments, self.compressed_size, self.final = [], 0, False
        self.raw = self.writer = None
        self._open()

    def _open(self):
        self.index = len(self.segments)
        self.partial = self.root / ("segment-%06d.gz.partial" % self.index)
        self.raw = self.partial.open("xb")
        self.writer = gzip.GzipFile(filename="", fileobj=self.raw, mode="wb", compresslevel=1, mtime=0)
        self.segment_bytes, self.segment_records = 0, 0
        self.first_ordinal, self.first_previous = self.ordinal, self.previous

    def sync(self):
        started = self.monotonic() if self.profiler else None
        self.writer.flush()
        self.raw.flush()
        os.fsync(self.raw.fileno())
        self.pending, self.last_sync = 0, self.monotonic()
        if self.profiler:
            self.profiler.record("fsync", self.monotonic() - started)

    def sync_if_due(self):
        if self.pending and self.monotonic() - self.last_sync >= 1:
            self.sync()

    def _seal(self):
        started = self.monotonic() if self.profiler else None
        self.writer.close()
        self.raw.flush()
        os.fsync(self.raw.fileno())
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
        self.writer.write(content)
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

    def close(self):
        if self.writer is None:
            return
        self._seal()
        manifest = {"schema_version": MANIFEST_SCHEMA, "segments": len(self.segments),
                    "records": self.ordinal, "final_segment_sha256": self.segments[-1]["segment_sha256"],
                    "final_record_sha256": self.previous, "session_end_present": self.final,
                    "compressed_bytes": self.compressed_size, "uncompressed_bytes": self.size,
                    "continuous_coverage_proven": False}
        manifest["manifest_sha256"] = payload_hash(manifest)
        exclusive_json(self.root / "manifest.json", manifest)


def verify_segments(root):
    root = Path(root)
    previous, previous_segment, rows, final = None, None, 0, False
    first_received, last_received, header_spec, terminal = None, None, None, None
    compressed, uncompressed = 0, 0
    frames, baselines, gaps = 0, {}, 0
    receive_contract, active_connection = None, 0
    receive_counts = {"available": 0, "unavailable": 0, "timing_eligible": 0}
    message_sequence, frame_sequence, delivery_after, receiver_after = 0, 0, None, None
    sideband_disabled = False
    reset_seen = False
    retained_saturation = None
    recovery_audit = None
    recovery_summaries = {}
    freshness_started = freshness_finished = freshness_samples = 0
    descriptors = sorted(root.glob("segment-*.json"))
    if not descriptors:
        raise ContractError("no sealed stream segments; preserve partial files")
    for index, path in enumerate(descriptors):
        descriptor = json.loads(path.read_text())
        verify_artifact_hash(descriptor, "segment_sha256", "stream segment")
        filename = "segment-%06d.gz" % index
        if (path.name != "segment-%06d.json" % index or descriptor["schema_version"] != SEGMENT_SCHEMA
                or descriptor["index"] != index or descriptor["file"] != filename
                or descriptor["previous_segment_sha256"] != previous_segment
                or descriptor["first_ordinal"] != rows or descriptor["first_previous_sha256"] != previous):
            raise ContractError("stream segment order/link mismatch")
        data = root / filename
        if data.stat().st_size != descriptor["compressed_bytes"] or file_hash(data) != descriptor["compressed_sha256"]:
            raise ContractError("compressed stream segment mismatch")
        segment_rows, segment_bytes = 0, 0
        if not 0 < descriptor["uncompressed_bytes"] <= 12 * 1024**2:
            raise ContractError("segment decompression budget invalid")
        with gzip.open(data, "rb") as handle:
            while True:
                line = handle.readline(4 * 1024**2 + 1)
                if not line:
                    break
                if len(line) > 4 * 1024**2 or segment_bytes + len(line) > descriptor["uncompressed_bytes"]:
                    raise ContractError("segment exceeds decompression budget")
                if not line.endswith(b"\n"):
                    raise ContractError("truncated segment row")
                row = json.loads(line)
                verify_artifact_hash(row, "record_sha256", "stream record")
                if (final or row.get("schema_version") != "qcrl.public_market_stream_record.v1"
                        or row["ordinal"] != rows or row["previous_sha256"] != previous
                        or (rows == 0 and row["kind"] != "session_start")):
                    raise ContractError("stream row chain/boundary mismatch")
                if rows == 0 and payload_hash(row["payload"]["spec"]) != row["payload"]["spec_sha256"]:
                    raise ContractError("stream header spec mismatch")
                if rows == 0:
                    first_received, header_spec = row["received_at_utc"], row["payload"]["spec"]
                    if not isinstance(header_spec, dict):
                        raise ContractError("stream spec must be an object")
                    if header_spec.get("schema_version") in ("qcrl.public_market_stream_spec.v4", "qcrl.public_market_stream_spec.v5", "qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
                        from .receive_path import validate_contract, policy_for
                        receive_contract = validate_contract(row["payload"].get("receive_path_contract"))
                        from .receive_path import policy_version
                        version = policy_version(header_spec["receive_path"])
                        allowed={"qcrl.public_market_stream_spec.v4":("v1",),
                                 "qcrl.public_market_stream_spec.v5":("v2",),
                                 "qcrl.public_market_stream_spec.v6":("v1","v2"),
                                 "qcrl.public_market_stream_spec.v7":("v3",)}
                        if version not in allowed[header_spec["schema_version"]]:
                            raise ContractError("receive schema/policy version mismatch")
                        if (header_spec.get("receive_path") != policy_for(version)
                                or receive_contract["policy"] != policy_for(version)
                                or receive_contract["stream_spec_sha256"] != payload_hash(header_spec)
                                or receive_contract["source_plan_sha256"] != header_spec.get("source_plan_sha256")):
                            raise ContractError("receive contract differs from stream/source policy")
                    if header_spec.get("schema_version") in ("qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
                        from .connection_freshness import POLICY as FRESHNESS_POLICY
                        from .stream_resilience import POLICY as RESILIENCE_POLICY
                        if header_spec.get("freshness_telemetry") != FRESHNESS_POLICY or header_spec.get("resilience") != RESILIENCE_POLICY:
                            raise ContractError("freshness telemetry policy mismatch")
                        freshness_replay = None
                        freshness_ended = True
                elif row["kind"] == "session_start":
                    raise ContractError("duplicate stream session header")
                last_received = row["received_at_utc"]
                if receive_contract and row["kind"] == "connect_attempt":
                    connection = row["payload"].get("connection")
                    if type(connection) is not int or connection != active_connection + 1:
                        raise ContractError("receive connection order mismatch")
                    active_connection, message_sequence, frame_sequence = connection, 0, 0
                    if header_spec.get('schema_version')=='qcrl.public_market_stream_spec.v7':
                        from .receive_recovery import RecoveryConnectionAudit
                        if recovery_audit is not None:
                            recovery_summaries[str(connection-1)]=recovery_audit.summary()
                        recovery_audit=RecoveryConnectionAudit(receive_contract,connection)
                    reset_seen = False
                    sideband_disabled = False
                    retained_saturation = None
                if receive_contract and row["kind"] == "receive_path_reset":
                    reset = row["payload"]
                    reset_keys={"new_connection", "previous_connection", "discarded_pending_markers",
                                "discarded_incomplete_fragment", "previous_disabled_reason"}
                    if recovery_audit is not None:
                        reset_keys|={'discarded_unknown_backlog','previous_generation'}
                        if any(type(reset.get(k)) is not int or reset[k]<0 or reset[k]>1000000
                               for k in ('discarded_unknown_backlog','previous_generation')):
                            raise ContractError('invalid recovery reset counters')
                        prior=recovery_summaries.get(str(active_connection-1),{}).get('last_alignment')
                        if reset['previous_generation']!=(prior['generation'] if prior else 0):
                            raise ContractError('recovery reset generation differs from prior trajectory')
                    if (reset_seen or not active_connection or reset.get("new_connection") != active_connection
                            or reset.get("previous_connection") != active_connection - 1
                            or set(reset) != reset_keys
                            or type(reset["discarded_pending_markers"]) is not int
                            or not 0 <= reset["discarded_pending_markers"] <= 64
                            or type(reset["discarded_incomplete_fragment"]) is not bool
                            or (reset["previous_disabled_reason"] is not None and
                                not isinstance(reset["previous_disabled_reason"], str))):
                        raise ContractError("receive reset provenance mismatch")
                    reset_seen = True
                if row["kind"] == "connection_gap":
                    gaps += 1
                    if header_spec.get("schema_version") in ("qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
                        diagnostic = row["payload"].get("close_diagnostics")
                        keys = {"schema_version", "origin", "error_type", "received_code", "sent_code",
                                "received_before_sent", "remote_cause_proven"}
                        if (not isinstance(diagnostic, dict) or set(diagnostic) != keys
                                or diagnostic["schema_version"] != "qcrl.close_diagnostics.v1"
                                or diagnostic["origin"] not in ("watchdog", "transport_or_other")
                                or not isinstance(diagnostic["error_type"], str) or not 1 <= len(diagnostic["error_type"]) <= 64
                                or diagnostic["remote_cause_proven"] is not False
                                or any(v is not None and (type(v) is not int or not 0 <= v <= 4999)
                                       for v in (diagnostic["received_code"], diagnostic["sent_code"]))
                                or (diagnostic["received_before_sent"] is not None and type(diagnostic["received_before_sent"]) is not bool)):
                            raise ContractError("invalid structured close diagnostics")
                        watchdog_reason = row["payload"].get("reason") in (
                            "initial_books_timeout", "selected_book_data_silence", "stale_timestamped_book_flow")
                        if ((diagnostic["origin"] == "watchdog") != watchdog_reason
                                or (watchdog_reason and any(diagnostic[k] is not None for k in
                                    ("received_code", "sent_code", "received_before_sent")))):
                            raise ContractError("watchdog close diagnostics claim transport codes")
                if header_spec.get("schema_version") in ("qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
                    from .connection_freshness import ConnectionFreshness
                    if row["kind"] == "subscribed":
                        if not freshness_ended or row["payload"].get("connection") != active_connection:
                            raise ContractError("freshness connection reset mismatch")
                        freshness_replay = ConnectionFreshness(active_connection, header_spec["asset_ids"])
                        freshness_ended = False
                        freshness_started += 1
                    if row["kind"] == "connection_freshness":
                        sample = row["payload"]
                        now = sample.get("sample_monotonic_seconds")
                        if (freshness_replay is None or freshness_ended or type(now) not in (int, float)
                                or not math.isfinite(now) or now < 0 or now > row["local_monotonic_seconds"]
                                or (freshness_replay.last_sample is not None and now < freshness_replay.last_sample)
                                or sample.get("reason") not in ("subscribed", "periodic", "connection_end")
                                or (freshness_replay.samples == 0 and sample.get("reason") != "subscribed")
                                or (freshness_replay.samples > 0 and sample.get("reason") == "subscribed")
                                or freshness_replay.samples >= 123
                                or sample != freshness_replay.snapshot(now, sample.get("reason"))):
                            raise ContractError("freshness sample differs from retained raw evidence")
                        freshness_replay.samples += 1
                        freshness_replay.last_sample = now
                        freshness_ended = sample["reason"] == "connection_end"
                        freshness_samples += 1
                        freshness_finished += int(freshness_ended)
                    if row["kind"] == "session_end" and not freshness_ended and row["payload"].get("status") != "storage_limit":
                        raise ContractError("missing final connection freshness sample")
                if row["kind"] == "frame" and header_spec.get("schema_version") in (
                        "qcrl.public_market_stream_spec.v3", "qcrl.public_market_stream_spec.v4", "qcrl.public_market_stream_spec.v5", "qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
                    from .market_stream import classify_frame
                    payload = row["payload"]
                    classes = classify_frame(payload["raw_text"], header_spec)
                    if payload["classification"] != classes or type(payload["connection"]) is not int:
                        raise ContractError("frame classification/connection differs from raw evidence")
                    if receive_contract:
                        from .receive_path import validate_delivery
                        from .receive_adapter import validate_adapter_failure
                        record = payload.get("receive_path")
                        if not isinstance(record, dict) or not reset_seen or payload["connection"] != active_connection:
                            raise ContractError("missing receive record or connection reset")
                        if record.get("schema_version") == "qcrl.receive_adapter_failure.v1":
                            if recovery_audit is not None:
                                raise ContractError('v3 recovery trajectory unavailable after adapter failure; preserve raw archive')
                            validate_adapter_failure(record, receive_contract, payload["raw_text"])
                        else:
                            validate_delivery(record, receive_contract, payload["raw_text"])
                            if recovery_audit is not None:
                                recovery_audit.consume(record,payload['raw_text'])
                            stamp = record["application_delivery"]
                            if delivery_after is not None and stamp["monotonic_before"] < delivery_after:
                                raise ContractError("receive delivery chronology reversed")
                            delivery_after = stamp["monotonic_after"]
                        if record["connection"] != active_connection:
                            raise ContractError("receive connection binding mismatch")
                        marker = record.get("receive_marker")
                        if record.get("schema_version") == "qcrl.receive_path_delivery.v2":
                            saturation = record["saturation"]
                            if retained_saturation is not None and saturation != retained_saturation:
                                raise ContractError("saturation provenance changed within connection")
                            if saturation is not None and retained_saturation is None:
                                if marker and marker["message_sequence"] != saturation["last_retained_message_sequence"] - 63:
                                    raise ContractError("saturated FIFO prefix starts after a skipped marker")
                                retained_saturation = saturation
                            if (saturation is not None and not marker and record["unavailable_reason"] == "pending_marker_budget"
                                    and message_sequence != saturation["last_retained_message_sequence"]):
                                raise ContractError("saturated FIFO prefix was not fully drained")
                        if marker:
                            if ((recovery_audit is None and (sideband_disabled or marker["message_sequence"] != message_sequence + 1))
                                    or marker["first_frame_sequence"] <= frame_sequence
                                    or (receiver_after is not None and
                                        marker["first_receive_observation"]["monotonic_before"] < receiver_after)):
                                raise ContractError("receive occurrence order mismatch")
                            message_sequence, frame_sequence = marker["message_sequence"], marker["last_frame_sequence"]
                            receiver_after = marker["last_receive_observation"]["monotonic_after"]
                            receive_counts["available"] += 1
                            receive_counts["timing_eligible"] += int(record["last_observation_to_delivery"]["timing_eligible"])
                        else:
                            if recovery_audit is None:
                                sideband_disabled = True
                            receive_counts["unavailable"] += 1
                    if header_spec.get("schema_version") in ("qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
                        if freshness_replay is None or freshness_ended:
                            raise ContractError("frame outside declared freshness connection")
                        freshness_replay.observe(payload["raw_text"], classes, record)
                    frames += 1
                    for event in classes:
                        if event["scope"] == "selected_market" and event["event_type"] == "book":
                            baselines.setdefault(str(payload["connection"]), set()).update(event["asset_ids"])
                if row["kind"] == "session_end":
                    terminal = row["payload"]
                previous, final = row["record_sha256"], row["kind"] == "session_end"
                rows += 1
                segment_rows += 1
                segment_bytes += len(line)
        if (segment_rows != descriptor["records"] or segment_bytes != descriptor["uncompressed_bytes"]
                or previous != descriptor["last_record_sha256"]):
            raise ContractError("segment record totals mismatch")
        previous_segment = descriptor["segment_sha256"]
        compressed += descriptor["compressed_bytes"]
        uncompressed += segment_bytes
    if {p.name for p in root.glob("segment-*.gz")} != {"segment-%06d.gz" % i for i in range(len(descriptors))}:
        raise ContractError("unlisted compressed segment; preserve incomplete publication")
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        verify_artifact_hash(manifest, "manifest_sha256", "stream manifest")
        expected = {"schema_version": MANIFEST_SCHEMA, "segments": len(descriptors), "records": rows,
                    "final_segment_sha256": previous_segment, "final_record_sha256": previous,
                    "session_end_present": final, "compressed_bytes": compressed,
                    "uncompressed_bytes": uncompressed, "continuous_coverage_proven": False}
        if {k: v for k, v in manifest.items() if k != "manifest_sha256"} != expected or list(root.glob("*.partial")):
            raise ContractError("stream manifest differs from sealed data")
    result = {"records": rows, "final_record_sha256": previous, "session_end_present": final,
            "manifest_present": manifest_path.exists(), "segments": len(descriptors),
            "compressed_bytes": compressed, "uncompressed_bytes": uncompressed,
            "first_received_at_utc": first_received, "last_received_at_utc": last_received,
            "header_spec": header_spec, "terminal_summary": terminal,
            "frames": frames, "book_snapshot_assets_by_connection": {k: sorted(v) for k, v in baselines.items()},
            "connection_gaps": gaps,
            "continuous_coverage_proven": False}
    if receive_contract:
        if final and (terminal.get("frames") != frames or terminal.get("connections") != active_connection):
            raise ContractError("receive stream footer totals differ from evidence")
        result["receive_path_verification"] = {"contract_sha256": receive_contract["contract_sha256"], **receive_counts,
                                               "wire_arrival_measured": False}
    if recovery_audit is not None:
        recovery_summaries[str(active_connection)]=recovery_audit.summary()
        result['receive_recovery_verification']={'schema_version':'qcrl.receive_recovery_verification.v1',
            'connections':recovery_summaries,'retained_delivery_trajectories_verified':True,
            'finalized_session':final}
    if header_spec and header_spec.get("schema_version") in ("qcrl.public_market_stream_spec.v6", "qcrl.public_market_stream_spec.v7"):
        result["freshness_verification"] = {"schema_version": "qcrl.connection_freshness_verification.v1",
            "raw_replayed_samples": freshness_samples, "subscribed_connections": freshness_started,
            "final_snapshots": freshness_finished, "all_final_snapshots_present": freshness_started == freshness_finished,
            "state_freshness_proven": False}
    return result
