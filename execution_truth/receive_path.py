"""Opt-in receive-path telemetry contracts and bounded sideband accounting.

No networking, order interfaces, queue replacement, or deployment. A future
adapter must observe library data-frame callbacks without altering flow control.
"""

from collections import deque
from copy import deepcopy
from datetime import datetime
import hashlib
import math
import re
import threading

from .acquisition import utc_text
from .contracts import ContractError, payload_hash, verify_artifact_hash


POLICY = {
    "schema_version": "qcrl.receive_path_policy.v1",
    "library_version": "websockets==15.0.1",
    "receiver_boundary": "library_data_frame_callback_entry_before_assembler",
    "delivery_boundary": "application_recv_return_before_classification",
    "library_queue_high_water_frames": 16,
    "max_pending_message_markers": 64,
    "max_fragments_per_message": 64,
    "max_message_bytes": 262144,
    "max_clock_bracket_seconds": 0.001,
    "clock_sampling": "monotonic_before_utc_monotonic_after",
    "overflow": "disable_sideband_for_connection_preserve_transport",
    "matching": "connection_scoped_fifo_occurrence_then_raw_utf8_or_binary_sha256",
    "elapsed_role": "callback_to_delivery_not_pure_queue_wait_or_network_latency",
}
POLICY_V2 = {**deepcopy(POLICY), "schema_version": "qcrl.receive_path_policy.v2",
             "overflow": "drain_identified_fifo_prefix_then_unknown_until_reconnect"}
POLICY_V3 = {**deepcopy(POLICY), "schema_version": "qcrl.receive_path_policy.v3",
             "overflow": "drain_prefix_then_unknown_until_equal_occurrence_counters_at_complete_message_fence",
             "matching": "connection_scoped_complete_message_and_delivery_ordinals_then_raw_sha256",
             "max_observed_messages": 1000000, "max_observed_frames": 64000000,
             "recovery": "no_incomplete_fragment_no_pending_markers_equal_observed_and_delivered_counts"}


def policy_for(version):
    if version not in ("v1", "v2", "v3"):
        raise ContractError("unsupported receive policy version")
    return deepcopy({"v1": POLICY, "v2": POLICY_V2, "v3": POLICY_V3}[version])


def policy_version(value):
    for version in ("v1", "v2", "v3"):
        if value == policy_for(version):
            return version
    raise ContractError("receive policy differs from a fixed version")


def _number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _domain(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value):
        raise ContractError("clock domain must identify one observer/boot monotonic clock")
    return value


def declare(source_plan_sha256, clock_domain, *, stream_spec_sha256, policy_version="v1"):
    for value in (source_plan_sha256, stream_spec_sha256):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ContractError("source plan/spec hashes must be lowercase SHA-256")
    policy = policy_for(policy_version)
    result = {"schema_version": "qcrl.receive_path_contract." + policy_version,
              "source_plan_sha256": source_plan_sha256, "clock_domain": _domain(clock_domain),
              "stream_spec_sha256": stream_spec_sha256,
              "policy": policy, "policy_sha256": payload_hash(policy),
              "orders_authorized": False, "wire_arrival_measured": False,
              "cross_host_clock_accuracy_proven": False}
    result["contract_sha256"] = payload_hash(result)
    return result


def validate_contract(value):
    if not isinstance(value, dict) or not {"source_plan_sha256", "clock_domain", "stream_spec_sha256"} <= set(value):
        raise ContractError("invalid receive-path contract")
    verify_artifact_hash(value, "contract_sha256", "receive-path contract")
    version = policy_version(value.get("policy"))
    if value != declare(value["source_plan_sha256"], value["clock_domain"], stream_spec_sha256=value["stream_spec_sha256"],
                        policy_version=version):
        raise ContractError("receive-path contract differs from fixed policy")
    return value


def validate_stamp(value, clock_domain):
    if not isinstance(value, dict) or set(value) != {"schema_version", "clock_domain", "utc", "monotonic_before", "monotonic_after"}:
        raise ContractError("unexpected bracketed clock fields")
    if value["schema_version"] != "qcrl.bracketed_clock.v1" or value["clock_domain"] != clock_domain:
        raise ContractError("bracketed clock domain/schema mismatch")
    before, after = value["monotonic_before"], value["monotonic_after"]
    if not _number(before) or not _number(after) or after < before:
        raise ContractError("clock bracket must be finite and monotonic")
    try:
        parsed = datetime.fromisoformat(value["utc"].replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError("not explicit UTC")
    except (TypeError, AttributeError, ValueError) as exc:
        raise ContractError("bracket requires timezone-aware UTC") from exc
    return value


def sample_clock(clock, monotonic, clock_domain):
    before = monotonic()
    utc = clock()
    after = monotonic()
    # utc_text can normalize aware offsets; never let it invent UTC for naive input.
    if not isinstance(utc, datetime) or utc.tzinfo is None or utc.utcoffset() is None:
        raise ContractError("sampling clock must return an aware datetime")
    value = {"schema_version": "qcrl.bracketed_clock.v1", "clock_domain": _domain(clock_domain),
             "utc": utc_text(utc), "monotonic_before": before, "monotonic_after": after}
    return validate_stamp(value, clock_domain)


def elapsed_bounds(first, last, clock_domain):
    validate_stamp(first, clock_domain)
    validate_stamp(last, clock_domain)
    lower = last["monotonic_before"] - first["monotonic_after"]
    upper = last["monotonic_after"] - first["monotonic_before"]
    if upper < 0:
        raise ContractError("delivery precedes receive observation")
    warnings = []
    if lower < 0:
        warnings.append("overlapping_clock_brackets")
    if any(s["monotonic_after"] - s["monotonic_before"] > POLICY["max_clock_bracket_seconds"]
           for s in (first, last)):
        warnings.append("wide_clock_bracket")
    return {"lower_seconds": lower, "upper_seconds": upper,
            "timing_eligible": not warnings, "warnings": warnings}


def validate_delivery(record, contract, message):
    """Independently bind an archived delivery to its declared clock and raw message."""
    validate_contract(contract)
    version = policy_version(contract["policy"])
    if version == "v3":
        from .receive_recovery import validate_recovery_delivery
        return validate_recovery_delivery(record, contract, message)
    limits = contract["policy"] if version == "v2" else POLICY
    verify_artifact_hash(record, "telemetry_sha256", "receive-path delivery")
    if (record.get("schema_version") != "qcrl.receive_path_delivery." + version
            or record.get("contract_sha256") != contract["contract_sha256"]
            or record.get("wire_arrival_measured") is not False or record.get("orders_authorized") is not False
            or type(record.get("connection")) is not int or record["connection"] < 1
            or type(record.get("pending_marker_depth")) is not int
            or not 0 <= record["pending_marker_depth"] <= limits["max_pending_message_markers"]):
        raise ContractError("invalid delivery binding or authority")
    domain = contract["clock_domain"]
    validate_stamp(record["application_delivery"], domain)
    marker = record.get("receive_marker")
    expected_keys = {"schema_version", "contract_sha256", "connection", "application_delivery", "receive_marker",
                     "telemetry_available", "unavailable_reason", "pending_marker_depth", "library_queue_depth",
                     "library_backpressure_active", "reader_loop_stall_seconds", "diagnostic_scope",
                     "wire_arrival_measured", "orders_authorized", "telemetry_sha256"}
    if marker is not None:
        expected_keys |= {"first_observation_to_delivery", "last_observation_to_delivery"}
    if version == "v2":
        expected_keys.add("saturation")
    if set(record) != expected_keys or record["diagnostic_scope"] != "same_connection_external_adapter_observation":
        raise ContractError("unexpected delivery fields or diagnostic scope")
    _validate_diagnostics(record["library_queue_depth"], record["library_backpressure_active"],
                          record["reader_loop_stall_seconds"])
    if type(record.get("telemetry_available")) is not bool or record["telemetry_available"] != (marker is not None):
        raise ContractError("delivery availability differs from marker")
    saturation = record.get("saturation")
    if version == "v2" and saturation is not None:
        if (not isinstance(saturation, dict) or set(saturation) != {
                "last_retained_message_sequence", "overflow_frame_sequence", "retained_prefix_messages", "observation"}
                or type(saturation["last_retained_message_sequence"]) is not int
                or saturation["last_retained_message_sequence"] < 64
                or type(saturation["overflow_frame_sequence"]) is not int or saturation["overflow_frame_sequence"] < 65
                or type(saturation["retained_prefix_messages"]) is not int or saturation["retained_prefix_messages"] != 64):
            raise ContractError("invalid saturation provenance")
        validate_stamp(saturation["observation"], domain)
    if version == "v2" and marker is None and record["pending_marker_depth"] != 0:
        raise ContractError("unknown delivery cannot retain drainable markers")
    if version == "v2" and record.get("unavailable_reason") == "pending_marker_budget" and saturation is None:
        raise ContractError("overflow requires saturation provenance")
    if marker is None:
        if (not isinstance(record.get("unavailable_reason"), str) or not record["unavailable_reason"]
                or "last_observation_to_delivery" in record or "first_observation_to_delivery" in record):
            raise ContractError("unknown telemetry cannot contain elapsed claims")
        return record
    required = {"message_sequence", "first_frame_sequence", "last_frame_sequence", "fragment_count",
                "message_bytes", "opcode", "raw_message_sha256", "first_receive_observation", "last_receive_observation"}
    if not isinstance(marker, dict) or set(marker) != required or record.get("unavailable_reason") is not None:
        raise ContractError("invalid receive marker")
    for field in ("message_sequence", "first_frame_sequence", "last_frame_sequence", "fragment_count"):
        if type(marker[field]) is not int or marker[field] < 1:
            raise ContractError("invalid occurrence/fragment identity")
    if (marker["last_frame_sequence"] < marker["first_frame_sequence"]
            or marker["fragment_count"] > min(limits["max_fragments_per_message"],
                marker["last_frame_sequence"] - marker["first_frame_sequence"] + 1)):
        raise ContractError("fragment provenance exceeds declared bounds")
    try:
        raw = message.encode("utf-8") if isinstance(message, str) else message
    except UnicodeEncodeError as exc:
        raise ContractError("invalid delivered UTF-8") from exc
    if (not isinstance(raw, bytes) or len(raw) > limits["max_message_bytes"]
            or type(marker["message_bytes"]) is not int or marker["message_bytes"] != len(raw)
            or type(marker["opcode"]) is not int or marker["opcode"] not in (1, 2)
            or (marker["opcode"] == 1) != isinstance(message, str)
            or marker["raw_message_sha256"] != hashlib.sha256(raw).hexdigest()):
        raise ContractError("marker differs from delivered message")
    first, last = marker["first_receive_observation"], marker["last_receive_observation"]
    validate_stamp(first, domain)
    validate_stamp(last, domain)
    if saturation is not None:
        end = saturation["last_retained_message_sequence"]
        if (not end - 64 < marker["message_sequence"] <= end
                or record["pending_marker_depth"] != end - marker["message_sequence"]
                or marker["last_frame_sequence"] >= saturation["overflow_frame_sequence"]
                or last["monotonic_after"] > saturation["observation"]["monotonic_before"]):
            raise ContractError("delivery outside identified saturated FIFO prefix")
    if marker["fragment_count"] == 1:
        if first != last or marker["first_frame_sequence"] != marker["last_frame_sequence"]:
            raise ContractError("single fragment has inconsistent observations")
    elif first["monotonic_after"] > last["monotonic_before"]:
        raise ContractError("fragment observation chronology is inconsistent")
    for field, start in (("first_observation_to_delivery", first), ("last_observation_to_delivery", last)):
        if record.get(field) != elapsed_bounds(start, record["application_delivery"], domain):
            raise ContractError("elapsed interval differs from retained clock brackets")
    return record


def _validate_diagnostics(depth, backpressure, stall):
    if depth is not None and (type(depth) is not int or not 0 <= depth <= 1000000):
        raise ContractError("queue depth must be a bounded measured count or unknown")
    if backpressure is not None and type(backpressure) is not bool:
        raise ContractError("backpressure must be measured boolean or unknown")
    if stall is not None and not _number(stall):
        raise ContractError("reader stall must be finite nonnegative or unknown")


class ReceivePathTracker:
    """Bounded metadata only; does not implement or measure the library queue.

    Feed text/binary/continuation callbacks in library order, then application
    messages in recv-return order. A mutex protects receiver/consumer threads.
    No raw payload is retained; fragments are incrementally hashed. Invalid
    protocols/mismatches disable this connection's sideband, never guess a match.
    """

    def __init__(self, contract):
        self.contract = deepcopy(validate_contract(contract))
        self.domain = contract["clock_domain"]
        self.version = policy_version(contract["policy"])
        if self.version == "v3" and type(self) is ReceivePathTracker:
            raise ContractError("v3 requires explicit ReceiveRecoveryTracker; collector integration is not enabled")
        self.policy = self.contract["policy"]
        self.saturation = None
        self.lock = threading.RLock()
        self.connection = 0
        self.pending = deque()
        self.fragment = None
        self.disabled_reason = None
        self.frame_sequence = self.message_sequence = 0
        self.last_receiver_after = None
        self.last_delivery_after = None

    def begin_connection(self, connection):
        with self.lock:
            if type(connection) is not int or connection != self.connection + 1:
                raise ContractError("connection identity must advance exactly once")
            reset = {"previous_connection": self.connection, "new_connection": connection,
                     "discarded_pending_markers": len(self.pending),
                     "discarded_incomplete_fragment": self.fragment is not None,
                     "previous_disabled_reason": self.disabled_reason}
            self.connection = connection
            self.pending.clear()
            self.fragment = None
            self.disabled_reason = None
            self.saturation = None
            self.frame_sequence = self.message_sequence = 0
            return reset

    def _disable(self, reason):
        self.disabled_reason = reason
        self.pending.clear()
        self.fragment = None

    def observe_frame(self, connection, opcode, final, data, stamp):
        with self.lock:
            if type(connection) is not int or connection != self.connection or self.connection == 0:
                raise ContractError("stale or uninitialized receive connection")
            draining = self.version == "v2" and self.disabled_reason == "pending_marker_budget"
            if self.disabled_reason and not draining:
                return False
            try:
                stamp = deepcopy(validate_stamp(stamp, self.domain))
            except ContractError:
                if self.version == "v2":
                    self._disable("invalid_receiver_clock")
                raise
            if (self.last_receiver_after is not None
                    and stamp["monotonic_before"] < self.last_receiver_after):
                self._disable("receiver_monotonic_regression")
                return False
            if type(opcode) is not int or type(final) is not bool or not isinstance(data, bytes):
                self._disable("invalid_frame_metadata")
                return False
            self.last_receiver_after = stamp["monotonic_after"]
            if draining:
                if opcode not in (0, 1, 2, 8, 9, 10):
                    self._disable("invalid_frame_metadata")
                return False  # Clock/header checks only; never add future markers.
            self.frame_sequence += 1
            if opcode in (8, 9, 10):
                return True  # Protocol close/ping/pong do not consume message IDs.
            if opcode in (1, 2):
                if self.fragment is not None:
                    self._disable("interleaved_data_messages")
                    return False
                self.fragment = {"first": stamp, "first_frame": self.frame_sequence,
                                 "opcode": opcode, "digest": hashlib.sha256(), "bytes": 0, "fragments": 0}
            elif opcode != 0 or self.fragment is None:
                self._disable("unexpected_continuation_or_opcode")
                return False
            f = self.fragment
            limits = self.policy if self.version == "v2" else POLICY
            f["bytes"] += len(data)
            f["fragments"] += 1
            if (f["bytes"] > limits["max_message_bytes"]
                    or f["fragments"] > limits["max_fragments_per_message"]):
                self._disable("message_telemetry_budget")
                return False
            f["digest"].update(data)
            if not final:
                return True
            if len(self.pending) >= limits["max_pending_message_markers"]:
                if self.version == "v2":
                    self.saturation = {"last_retained_message_sequence": self.message_sequence,
                                       "overflow_frame_sequence": self.frame_sequence,
                                       "retained_prefix_messages": len(self.pending), "observation": stamp}
                    self.disabled_reason = "pending_marker_budget"
                    self.fragment = None
                    return False
                self._disable("pending_marker_budget")
                return False
            self.message_sequence += 1
            self.pending.append({"message_sequence": self.message_sequence,
                "first_frame_sequence": f["first_frame"], "last_frame_sequence": self.frame_sequence,
                "fragment_count": f["fragments"], "message_bytes": f["bytes"], "opcode": f["opcode"],
                "raw_message_sha256": f["digest"].hexdigest(),
                "first_receive_observation": f["first"], "last_receive_observation": stamp})
            self.fragment = None
            return True

    def deliver(self, connection, message, stamp, *, library_queue_depth=None,
                library_backpressure_active=None, reader_loop_stall_seconds=None):
        with self.lock:
            if type(connection) is not int or connection != self.connection or self.connection == 0:
                raise ContractError("stale or uninitialized delivery connection")
            _validate_diagnostics(library_queue_depth, library_backpressure_active, reader_loop_stall_seconds)
            delivery = deepcopy(validate_stamp(stamp, self.domain))
            if self.last_delivery_after is not None and delivery["monotonic_before"] < self.last_delivery_after:
                if self.version == "v2":
                    self._disable("application_monotonic_regression")
                raise ContractError("application delivery clock moved backwards")
            marker = None
            if self.disabled_reason is None or (self.version == "v2" and
                    self.disabled_reason == "pending_marker_budget" and self.pending):
                if not self.pending:
                    self._disable("missing_receive_marker")
                else:
                    candidate = self.pending[0]
                    try:
                        raw = message.encode("utf-8") if isinstance(message, str) else message
                    except UnicodeEncodeError:
                        raw = None
                    if (not isinstance(raw, bytes) or len(raw) > POLICY["max_message_bytes"]
                            or (candidate["opcode"] == 1) != isinstance(message, str)
                            or hashlib.sha256(raw).hexdigest() != candidate["raw_message_sha256"]):
                        self._disable("fifo_message_mismatch")
                    else:
                        try:
                            elapsed_bounds(candidate["last_receive_observation"], delivery, self.domain)
                        except ContractError:
                            if self.version == "v2":
                                self._disable("delivery_timing_error")
                            raise
                        marker = self.pending.popleft()
            record = {"schema_version": "qcrl.receive_path_delivery." + self.version,
                      "contract_sha256": self.contract["contract_sha256"], "connection": connection,
                      "application_delivery": delivery, "receive_marker": marker,
                      "telemetry_available": marker is not None,
                      "unavailable_reason": None if marker else self.disabled_reason,
                      "pending_marker_depth": len(self.pending),
                      "library_queue_depth": library_queue_depth,
                      "library_backpressure_active": library_backpressure_active,
                      "reader_loop_stall_seconds": reader_loop_stall_seconds,
                      "diagnostic_scope": "same_connection_external_adapter_observation",
                      "wire_arrival_measured": False, "orders_authorized": False}
            if self.version == "v2":
                record["saturation"] = deepcopy(self.saturation)
            if marker:
                record["last_observation_to_delivery"] = elapsed_bounds(
                    marker["last_receive_observation"], delivery, self.domain)
                record["first_observation_to_delivery"] = elapsed_bounds(
                    marker["first_receive_observation"], delivery, self.domain)
            record["telemetry_sha256"] = payload_hash(record)
            self.last_delivery_after = delivery["monotonic_after"]
            return record
