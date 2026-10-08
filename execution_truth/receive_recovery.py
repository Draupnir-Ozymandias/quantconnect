"""Opt-in v3 bounded occurrence fence; not integrated into public collectors."""
from copy import deepcopy
import hashlib
from itertools import zip_longest

from .contracts import ContractError, payload_hash, verify_artifact_hash
from .receive_path import (ReceivePathTracker, declare, elapsed_bounds, policy_version,
                          validate_contract, validate_delivery, validate_stamp, _validate_diagnostics)


class ReceiveRecoveryTracker(ReceivePathTracker):
    """Observe ALL completed message occurrences, including unretained markers.

    Assumes the pinned adapter observes every library data callback exactly once
    and a single reader reports every successful recv exactly once, in order.
    Counter equality is not a wire-arrival observation or a queue-depth heuristic.
    Protocol, clock, digest and counter violations fail closed until reconnect.
    """
    def __init__(self, contract):
        super().__init__(contract)
        if self.version != "v3":
            raise ContractError("recovery tracker requires explicit v3 contract")
        self.delivered_messages = 0
        self.generation = 0
        self.overflow = self.recovery_fence = None

    def begin_connection(self, connection):
        with self.lock:
            unknown = max(0, self.message_sequence-self.delivered_messages-len(self.pending))
            generation = self.generation
            reset = super().begin_connection(connection)
            reset.update(discarded_unknown_backlog=unknown, previous_generation=generation)
            self.delivered_messages = self.generation = 0
            self.overflow = self.recovery_fence = None
            return reset

    def observe_frame(self, connection, opcode, final, data, stamp):
        with self.lock:
            if type(connection) is not int or connection != self.connection or self.connection == 0:
                raise ContractError("stale or uninitialized receive connection")
            if self.disabled_reason not in (None, "pending_marker_budget"):
                return False
            try:
                stamp = deepcopy(validate_stamp(stamp, self.domain))
            except ContractError:
                self._disable("invalid_receiver_clock")
                raise
            if self.last_receiver_after is not None and stamp["monotonic_before"] < self.last_receiver_after:
                self._disable("receiver_monotonic_regression")
                return False
            if type(opcode) is not int or type(final) is not bool or not isinstance(data, bytes):
                self._disable("invalid_frame_metadata")
                return False
            self.last_receiver_after = stamp["monotonic_after"]
            if self.frame_sequence >= self.policy["max_observed_frames"]:
                self._disable("occurrence_counter_budget")
                return False
            self.frame_sequence += 1
            if opcode in (8, 9, 10):
                if not final or len(data)>125:
                    self._disable("invalid_control_frame")
                    return False
                return True
            if opcode in (1, 2):
                if self.fragment is not None:
                    self._disable("interleaved_data_messages")
                    return False
                self.fragment = {"first": stamp, "first_frame": self.frame_sequence,
                    "opcode": opcode, "bytes": 0, "fragments": 0,
                    "digest": hashlib.sha256() if self.disabled_reason is None else None}
            elif opcode != 0 or self.fragment is None:
                self._disable("unexpected_continuation_or_opcode")
                return False
            f = self.fragment
            f["bytes"] += len(data); f["fragments"] += 1
            if f["bytes"]>self.policy["max_message_bytes"] or f["fragments"]>self.policy["max_fragments_per_message"]:
                self._disable("message_telemetry_budget")
                return False
            if f["digest"] is not None:
                f["digest"].update(data)
            if not final:
                return True
            if self.message_sequence >= self.policy["max_observed_messages"]:
                self._disable("occurrence_counter_budget")
                return False
            self.message_sequence += 1
            self.fragment = None
            if self.disabled_reason == "pending_marker_budget":
                return False  # Count full messages without retaining their payload or marker.
            if len(self.pending) == self.policy["max_pending_message_markers"]:
                self.overflow = {"generation_before": self.generation,
                    "last_retained_message_sequence": self.message_sequence-1,
                    "first_unretained_message_sequence": self.message_sequence,
                    "observation": stamp}
                self.disabled_reason = "pending_marker_budget"
                return False
            self.pending.append({"message_sequence": self.message_sequence,
                "first_frame_sequence": f["first_frame"], "last_frame_sequence": self.frame_sequence,
                "fragment_count": f["fragments"], "message_bytes": f["bytes"], "opcode": f["opcode"],
                "raw_message_sha256": f["digest"].hexdigest(),
                "first_receive_observation": f["first"], "last_receive_observation": stamp})
            return True

    def deliver(self, connection, message, stamp, *, library_queue_depth=None,
                library_backpressure_active=None, reader_loop_stall_seconds=None):
        with self.lock:
            if type(connection) is not int or connection != self.connection or self.connection == 0:
                raise ContractError("stale or uninitialized delivery connection")
            _validate_diagnostics(library_queue_depth, library_backpressure_active, reader_loop_stall_seconds)
            try:
                delivery = deepcopy(validate_stamp(stamp, self.domain))
            except ContractError:
                self._disable("invalid_application_clock")
                raise
            if self.last_delivery_after is not None and delivery["monotonic_before"] < self.last_delivery_after:
                self._disable("application_monotonic_regression")
                raise ContractError("application delivery clock moved backwards")
            marker = None
            if self.delivered_messages < self.policy["max_observed_messages"]:
                self.delivered_messages += 1
            else:
                self._disable("occurrence_counter_budget")
            if self.disabled_reason in (None, "pending_marker_budget"):
                if self.delivered_messages > self.message_sequence:
                    self._disable("delivery_occurrence_ahead_of_observation")
                elif self.pending:
                    candidate = self.pending[0]
                    try:
                        raw = message.encode("utf-8") if isinstance(message, str) else message
                    except UnicodeEncodeError:
                        raw = None
                    if (candidate["message_sequence"] != self.delivered_messages
                            or not isinstance(raw, bytes) or len(raw)>self.policy["max_message_bytes"]
                            or (candidate["opcode"]==1) != isinstance(message,str)
                            or hashlib.sha256(raw).hexdigest()!=candidate["raw_message_sha256"]):
                        self._disable("fifo_message_mismatch")
                    else:
                        try:
                            elapsed_bounds(candidate["last_receive_observation"], delivery, self.domain)
                        except ContractError:
                            self._disable("delivery_timing_error")
                            raise
                        marker = self.pending.popleft()
                elif self.disabled_reason is None:
                    self._disable("missing_receive_marker")
            reason = None if marker is not None else self.disabled_reason
            # This delivery remains unknown: only a later observed occurrence can
            # acquire a marker under the restored alignment generation.
            if (self.disabled_reason == "pending_marker_budget" and not self.pending
                    and self.fragment is None and self.message_sequence == self.delivered_messages
                    and self.last_receiver_after <= delivery["monotonic_before"]):
                self.generation += 1
                self.recovery_fence = {"generation": self.generation,
                    "observed_messages": self.message_sequence, "delivered_messages": self.delivered_messages,
                    "observed_frames": self.frame_sequence, "incomplete_fragment": False, "observation": delivery}
                self.disabled_reason = None
            state = ("aligned" if self.disabled_reason is None else
                     "draining" if self.disabled_reason == "pending_marker_budget" else "terminal")
            record = {"schema_version": "qcrl.receive_path_delivery.v3", "contract_sha256": self.contract["contract_sha256"],
                "connection": connection, "application_delivery": delivery, "receive_marker": marker,
                "telemetry_available": marker is not None, "unavailable_reason": reason,
                "pending_marker_depth": len(self.pending), "library_queue_depth": library_queue_depth,
                "library_backpressure_active": library_backpressure_active,
                "reader_loop_stall_seconds": reader_loop_stall_seconds,
                "diagnostic_scope": "same_connection_external_adapter_observation",
                "wire_arrival_measured": False, "orders_authorized": False,
                "alignment": {"observed_messages": self.message_sequence,
                    "delivered_messages": self.delivered_messages, "observed_frames": self.frame_sequence,
                    "generation": self.generation, "state": state,
                    "overflow": deepcopy(self.overflow), "recovery_fence": deepcopy(self.recovery_fence)}}
            if marker is not None:
                for field, start in (("first_observation_to_delivery", marker["first_receive_observation"]),
                                     ("last_observation_to_delivery", marker["last_receive_observation"])):
                    record[field] = elapsed_bounds(start, delivery, self.domain)
            record["telemetry_sha256"] = payload_hash(record)
            self.last_delivery_after = delivery["monotonic_after"]
            return record


def validate_recovery_delivery(record, contract, message):
    validate_contract(contract)
    if policy_version(contract["policy"]) != "v3":
        raise ContractError("recovery record requires v3 contract")
    verify_artifact_hash(record, "telemetry_sha256", "recovery delivery")
    if record.get("schema_version")!="qcrl.receive_path_delivery.v3" or record.get("contract_sha256")!=contract["contract_sha256"]:
        raise ContractError("recovery binding mismatch")
    # Validate all common shapes/raw clocks BEFORE indexing marker diagnostics.
    # The legacy validator has no v2 saturated-prefix restrictions; v3 alignment
    # and recovery provenance are checked separately below.
    domain=contract["clock_domain"]
    legacy_contract=declare(contract["source_plan_sha256"],domain,stream_spec_sha256=contract["stream_spec_sha256"])
    legacy={k:deepcopy(v) for k,v in record.items() if k not in ("alignment","telemetry_sha256")}
    legacy.update(schema_version="qcrl.receive_path_delivery.v1",contract_sha256=legacy_contract["contract_sha256"])
    legacy["telemetry_sha256"]=payload_hash(legacy)
    validate_delivery(legacy,legacy_contract,message)
    alignment = record.get("alignment")
    keys = {"observed_messages","delivered_messages","observed_frames","generation","state","overflow","recovery_fence"}
    if not isinstance(alignment,dict) or set(alignment)!=keys:
        raise ContractError("unexpected alignment fields")
    p = contract["policy"]
    for key, maximum in (("observed_messages",p["max_observed_messages"]),
                         ("delivered_messages",p["max_observed_messages"]),
                         ("observed_frames",p["max_observed_frames"]),("generation",p["max_observed_messages"])):
        if type(alignment[key]) is not int or not 0<=alignment[key]<=maximum:
            raise ContractError("unbounded alignment counter")
    if alignment["state"] not in ("aligned","draining","terminal"):
        raise ContractError("unexpected alignment state")
    obs, delivered, gen = alignment["observed_messages"],alignment["delivered_messages"],alignment["generation"]
    if delivered<1 or obs>alignment["observed_frames"]:
        raise ContractError("inconsistent occurrence counters")
    marker = record.get("receive_marker")
    if marker is not None and (alignment["state"]=="terminal" or marker["message_sequence"]!=delivered
                               or marker["message_sequence"]>obs or marker["last_frame_sequence"]>alignment["observed_frames"]):
        raise ContractError("marker is not this delivery occurrence")
    if alignment["state"] != "terminal":
        if obs<delivered or not 0<=record["pending_marker_depth"]<=obs-delivered:
            raise ContractError("backlog differs from occurrence counters")
        if alignment["state"]=="aligned" and record["pending_marker_depth"]!=obs-delivered:
            raise ContractError("aligned backlog must have complete markers")
    fence = alignment["recovery_fence"]
    overflow = alignment["overflow"]
    domain = contract["clock_domain"]
    if overflow is not None:
        if (not isinstance(overflow,dict) or set(overflow)!={"generation_before","last_retained_message_sequence",
                "first_unretained_message_sequence","observation"}
                or any(type(overflow[k]) is not int for k in ("generation_before","last_retained_message_sequence","first_unretained_message_sequence"))
                or not 0<=overflow["generation_before"]<=gen
                or not 64<=overflow["last_retained_message_sequence"]<p["max_observed_messages"]
                or overflow["first_unretained_message_sequence"]!=overflow["last_retained_message_sequence"]+1
                or overflow["first_unretained_message_sequence"]>obs):
            raise ContractError("invalid overflow provenance")
        validate_stamp(overflow["observation"],domain)
    if alignment["state"]=="draining" and (overflow is None or overflow["generation_before"]!=gen):
        raise ContractError("draining requires current-generation overflow")
    if alignment["state"]=="aligned" and gen==0 and overflow is not None:
        raise ContractError("initial aligned generation cannot retain overflow")
    if alignment["state"]=="terminal" and record.get("unavailable_reason")=="pending_marker_budget":
        raise ContractError("recoverable overflow is draining, not terminal")
    if alignment["state"]=="draining" and marker is None and (
            record.get("unavailable_reason")!="pending_marker_budget" or record["pending_marker_depth"]!=0):
        raise ContractError("unknown overflow delivery must have drained retained prefix")
    if gen>0:
        if (not isinstance(fence,dict) or set(fence)!={"generation","observed_messages","delivered_messages",
                "observed_frames","incomplete_fragment","observation"}
                or any(type(fence[k]) is not int for k in ("generation","observed_messages","delivered_messages","observed_frames"))
                or fence["generation"]!=gen or fence["incomplete_fragment"] is not False
                or not 1<=fence["observed_messages"]==fence["delivered_messages"]<=delivered
                or not fence["observed_messages"]<=fence["observed_frames"]<=alignment["observed_frames"]):
            raise ContractError("invalid complete-message recovery fence")
        validate_stamp(fence["observation"],domain)
        if fence["observation"]["monotonic_after"]>record["application_delivery"]["monotonic_after"]:
            raise ContractError("recovery fence follows delivery")
        if overflow is None:
            raise ContractError("recovery requires retained overflow provenance")
        if alignment["state"]=="aligned" and (overflow["generation_before"]!=gen-1
                or fence["observed_messages"]<overflow["first_unretained_message_sequence"]):
            raise ContractError("recovery fence does not cover overflow")
        if marker is not None and alignment["state"]=="aligned" and marker["message_sequence"]<=fence["delivered_messages"]:
            raise ContractError("recovered marker cannot precede recovery fence")
    elif fence is not None:
        raise ContractError("initial generation cannot claim recovery")
    if marker is not None and alignment["state"]=="draining":
        end=overflow["last_retained_message_sequence"]
        if (not end-64<marker["message_sequence"]<=end
                or record["pending_marker_depth"]!=end-marker["message_sequence"]
                or marker["last_receive_observation"]["monotonic_after"]>overflow["observation"]["monotonic_before"]):
            raise ContractError("marker is outside retained prefix")
    if marker is None and alignment["state"]=="aligned":
        if record.get("unavailable_reason")!="pending_marker_budget" or fence is None or delivered!=fence["delivered_messages"]:
            raise ContractError("only fence-closing delivery may be aligned but unknown")
    return record


def _validate_recovery_connection(records, contract, messages, *, connection=1, _state=None):
    """Audit an entire connection's delivery trajectory, not an arbitrary slice.

    Checks occurrence progression and fence transitions across archived records.
    Origin callback completeness still rests on the pinned adapter invariant;
    hashes/counters are not signatures or independently observed wire events.
    """
    validate_contract(contract)
    if policy_version(contract["policy"])!="v3" or type(connection) is not int or connection<1:
        raise ContractError("complete-connection audit requires explicit v3 identity")
    sentinel=object()
    previous=None if _state is None else _state.get('previous')
    count=0 if _state is None else _state.get('count',0)
    known=0 if _state is None else _state.get('known',0)
    recovered=0 if _state is None else _state.get('recovered',0)
    for record, message in zip_longest(records,messages,fillvalue=sentinel):
        if record is sentinel or message is sentinel:
            raise ContractError("raw/delivery trajectory lengths differ")
        count+=1
        if count>contract["policy"]["max_observed_messages"]:
            raise ContractError("complete-connection audit exceeds budget")
        validate_recovery_delivery(record,contract,message)
        a=record["alignment"]
        if record["connection"]!=connection or a["delivered_messages"]!=count:
            raise ContractError("delivery trajectory must begin at occurrence one and advance once")
        gen_before=0 if previous is None else previous["generation"]
        if previous is not None:
            if (a["observed_messages"]<previous["observed_messages"]
                    or a["observed_frames"]<previous["observed_frames"]):
                raise ContractError("observed occurrence counters moved backwards")
            if previous["state"]=="terminal" and (a["state"]!="terminal" or a["generation"]!=gen_before):
                raise ContractError("terminal connection cannot recover")
            if previous["state"]=="draining" and a["overflow"]!=previous["overflow"]:
                raise ContractError("one draining episode cannot rewrite overflow provenance")
        if a["generation"]==gen_before+1:
            fence=a["recovery_fence"]
            if (a["state"]!="aligned" or record["receive_marker"] is not None
                    or record["unavailable_reason"]!="pending_marker_budget"
                    or record["pending_marker_depth"]!=0 or a["observed_messages"]!=count
                    or fence["observed_messages"]!=count
                    or fence["observation"]!=record["application_delivery"]):
                raise ContractError("generation must advance on this exact unknown fence-closing delivery")
            recovered+=1
        elif a["generation"]!=gen_before:
            raise ContractError("generation cannot skip or move backwards")
        elif previous is not None:
            if a["recovery_fence"]!=previous["recovery_fence"]:
                raise ContractError("unchanged generation cannot rewrite its recovery fence")
            if previous["state"]=="draining" and a["state"]=="aligned":
                raise ContractError("draining cannot rearm without a new fence generation")
        known+=record["receive_marker"] is not None
        previous=a
    if _state is not None:
        _state.update(previous=deepcopy(previous),count=count,known=known,recovered=recovered)
    return {"connection":connection,"deliveries":count,"known":known,"unknown":count-known,
            "recovery_generations":recovered,"last_alignment":deepcopy(previous),
            "wire_arrival_measured":False,"orders_authorized":False}


def validate_recovery_connection(records, contract, messages, *, connection=1):
    return _validate_recovery_connection(records,contract,messages,connection=connection)


class RecoveryConnectionAudit:
    """Incremental sealed-stream audit: bounded previous-record state only."""
    def __init__(self, contract, connection):
        self.contract=deepcopy(contract)
        self.connection=connection
        self.state={}
        self.result=_validate_recovery_connection([],contract,[],connection=connection)

    def consume(self, record, message):
        self.result=_validate_recovery_connection([record],self.contract,[message],
            connection=self.connection,_state=self.state)

    def summary(self):
        return deepcopy(self.result)
