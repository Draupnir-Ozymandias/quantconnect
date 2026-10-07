"""Bounded connection diagnostics, never book-state validity or control policy."""
from collections import Counter, deque
from copy import deepcopy
import json

from .contracts import ContractError, payload_hash
from .stream_freshness import epoch, milliseconds

POLICY = {"schema_version": "qcrl.connection_freshness_policy.v1", "sample_seconds": 5,
          "max_samples_per_connection": 123, "retained_transitions": 8,
          "fresh_seconds": 5, "event_types": ["book", "price_change"],
          "age_reference": "application_delivery_utc_minus_payload_timestamp",
          "unknown_is_fresh": False, "controls_reconnect": False}


def close_diagnostics(exc):
    """Inspect bounded exception causes; never guess codes from strings."""
    current, seen = exc, set()
    received = sent = order = None
    error_type = type(exc).__name__[:64]
    for _ in range(4):
        if id(current) in seen:
            break
        seen.add(id(current))
        error_type = type(current).__name__[:64]
        for field in ("rcvd", "sent"):
            value = getattr(getattr(current, field, None), "code", None)
            if type(value) is int and 0 <= value <= 4999:
                if field == "rcvd":
                    received = value
                else:
                    sent = value
        value = getattr(current, "rcvd_then_sent", None)
        if type(value) is bool:
            order = value
        cause = current.__cause__
        if cause is None:
            break
        current = cause
    reason = str(exc)
    origin = "watchdog" if reason in ("initial_books_timeout", "selected_book_data_silence",
                                       "stale_timestamped_book_flow") else "transport_or_other"
    return {"schema_version": "qcrl.close_diagnostics.v1", "origin": origin,
            "error_type": error_type, "received_code": received, "sent_code": sent,
            "received_before_sent": order, "remote_cause_proven": False}


class ConnectionFreshness:
    def __init__(self, connection, assets):
        self.connection, self.assets = connection, set(assets)
        self.counts = Counter()
        self.books, self.updates = {}, {}
        self.last_fresh = self.stale_since = self.latest = None
        self.transitions = deque(maxlen=POLICY["retained_transitions"])
        self.transition_count = self.samples = 0
        self.last_sample = None

    def _transition(self, kind, stamp):
        self.transition_count += 1
        self.transitions.append({"kind": kind, "delivery": deepcopy(stamp)})

    def observe(self, raw, classes, record):
        self.counts["messages"] += 1
        stamp = record.get("application_delivery")
        if stamp is None:
            self.counts["missing_delivery_stamp_messages"] += 1
            return
        try:
            data = json.loads(raw)
        except ValueError:
            return
        events = data if isinstance(data, list) else [data]
        if len(events) != len(classes):
            raise ContractError("freshness classification count mismatch")
        ages = []
        for event, cls in zip(events, classes):
            if cls["scope"] != "selected_market" or cls["event_type"] not in POLICY["event_types"]:
                continue
            self.counts["selected_book_events"] += 1
            try:
                source = milliseconds(event.get("timestamp"))
            except ValueError:
                self.counts["missing_or_invalid_timestamp_events"] += 1
                continue
            age = epoch(stamp["utc"]) - source
            if age < 0:
                self.counts["negative_age_events"] += 1
                continue
            ages.append(age)
            fresh = age <= POLICY["fresh_seconds"]
            self.counts["fresh_events" if fresh else "stale_events"] += 1
            marker = record.get("receive_marker")
            callback = marker["last_receive_observation"] if marker else None
            witness = {"delivery": deepcopy(stamp), "event_type": cls["event_type"],
                       "nominal_delivery_age_seconds": age,
                       "nominal_callback_age_seconds": epoch(callback["utc"]) - source if callback else None,
                       "callback_age_timing_eligible": bool(marker and
                           record["last_observation_to_delivery"]["timing_eligible"] and
                           record["first_observation_to_delivery"]["timing_eligible"])}
            self.latest = witness
            for asset in set(cls["asset_ids"]) & self.assets:
                if cls["event_type"] == "book":
                    self.books.setdefault(asset, deepcopy(witness))
                elif fresh:
                    self.updates.setdefault(asset, deepcopy(witness))
            if fresh:
                self.last_fresh = deepcopy(witness)
        if ages:
            if any(age <= POLICY["fresh_seconds"] for age in ages):
                if self.stale_since is not None:
                    self._transition("stale_cleared_by_fresh_event", stamp)
                self.stale_since = None
            elif self.stale_since is None:
                self.stale_since = deepcopy(stamp)
                self._transition("stale_flow_onset", stamp)

    def snapshot(self, now, reason):
        result = {"schema_version": "qcrl.connection_freshness_sample.v1", "connection": self.connection,
                  "sample_index": self.samples + 1, "sample_monotonic_seconds": now, "reason": reason,
                  "counts": dict(self.counts), "initial_books": deepcopy(self.books),
                  "first_fresh_price_updates": deepcopy(self.updates), "latest_timestamped_event": deepcopy(self.latest),
                  "last_fresh_event": deepcopy(self.last_fresh), "stale_since": deepcopy(self.stale_since),
                  "recent_transitions": deepcopy(list(self.transitions)), "transition_count": self.transition_count,
                  "omitted_earlier_transitions": max(0, self.transition_count - len(self.transitions)),
                  "state_freshness_proven": False, "orders_authorized": False}
        result["sample_sha256"] = payload_hash(result)
        return result

    def emit(self, log, now, reason="periodic", force=False):
        if not force and self.last_sample is not None and now - self.last_sample < POLICY["sample_seconds"]:
            return
        if self.samples >= POLICY["max_samples_per_connection"]:
            raise ContractError("freshness sample budget exceeded")
        log.append("connection_freshness", self.snapshot(now, reason))
        self.samples += 1
        self.last_sample = now
