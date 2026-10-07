"""Explicit opt-in, websockets-15.0.1 adapter; legacy collector is untouched."""

from importlib.metadata import PackageNotFoundError, version
import hashlib
import threading
import time
from urllib.parse import urlsplit

from .acquisition import utc_now
from .contracts import ContractError, payload_hash, verify_artifact_hash
from .receive_path import ReceivePathTracker, sample_clock, validate_contract


def _load_library():
    try:
        installed = version("websockets")
    except PackageNotFoundError as exc:
        raise ContractError("receive adapter requires exactly websockets 15.0.1") from exc
    if installed != "15.0.1":
        raise ContractError("receive adapter requires exactly websockets 15.0.1")
    from websockets.frames import Frame
    from websockets.sync.client import ClientConnection, connect
    return Frame, ClientConnection, connect


def validate_adapter_failure(record, contract, message):
    """A diagnostic failure binds raw data but contains no elapsed-time claim."""
    validate_contract(contract)
    verify_artifact_hash(record, "telemetry_sha256", "receive adapter failure")
    expected = {"schema_version", "contract_sha256", "connection", "raw_message_sha256",
                "unavailable_reason", "error_type", "orders_authorized", "wire_arrival_measured", "telemetry_sha256"}
    raw = message.encode("utf-8") if isinstance(message, str) else message
    if (set(record) != expected or record["schema_version"] != "qcrl.receive_adapter_failure.v1"
            or record["contract_sha256"] != contract["contract_sha256"]
            or type(record["connection"]) is not int or record["connection"] < 1
            or record["unavailable_reason"] != "application_telemetry_error"
            or not isinstance(record["error_type"], str) or not 1 <= len(record["error_type"]) <= 128
            or record["orders_authorized"] is not False or record["wire_arrival_measured"] is not False
            or not isinstance(raw, bytes) or len(raw) > 262144
            or record["raw_message_sha256"] != hashlib.sha256(raw).hexdigest()):
        raise ContractError("invalid adapter failure binding")
    return record


class ObservedSocket:
    """Separate adapter: recv returns raw data unchanged plus optional metadata.

    Queue diagnostics use version-specific assembler internals under its mutex.
    Metadata locks are NEVER held while calling the parent process_event/recv.
    No wire/kernel arrival time is observed. No background telemetry writer.
    """

    def __init__(self, uri, tracker, connection, *, clock=utc_now, monotonic=time.monotonic):
        parsed = urlsplit(uri)
        public = uri == "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        loopback = parsed.scheme == "ws" and parsed.hostname in ("127.0.0.1", "::1", "localhost")
        if not (public or loopback) or parsed.username is not None or parsed.password is not None:
            raise ContractError("adapter permits public market feed or local loopback only")
        if not isinstance(tracker, ReceivePathTracker):
            raise ContractError("adapter requires an explicitly declared tracker")
        Frame, ClientConnection, connect = _load_library()
        self.tracker, self.number = tracker, connection
        self.clock, self.monotonic = clock, monotonic
        self.reader_lock = threading.Lock()
        self.last_exit = None
        self.reset = tracker.begin_connection(connection)
        adapter = self

        class InstrumentedConnection(ClientConnection):
            def process_event(self, event):
                if isinstance(event, Frame):
                    try:
                        stamp = sample_clock(adapter.clock, adapter.monotonic, adapter.tracker.domain)
                        adapter.tracker.observe_frame(adapter.number, int(event.opcode), bool(event.fin),
                                                      bytes(event.data), stamp)
                    except Exception:
                        # Observation failures must not swallow protocol events or
                        # disable a new connection due to a retired callback.
                        with adapter.tracker.lock:
                            if adapter.tracker.connection == adapter.number:
                                adapter.tracker._disable("receiver_observation_error")
                super().process_event(event)

        self.connection = connect(uri, create_connection=InstrumentedConnection,
                                  open_timeout=10, close_timeout=5, max_size=262144,
                                  max_queue=16, compression=None, ping_interval=None, proxy=None)
        try:
            self.queue_snapshot()  # Fail closed on unsupported assembler layout.
        except Exception:
            self.connection.close()
            raise

    def queue_snapshot(self):
        assembler = self.connection.recv_messages
        # Avoid acquiring tracker.lock here: library mutex -> metadata mutex
        # inversion would create a deadlock risk with incoming callbacks.
        with assembler.mutex:
            # Closed assemblers may contain an EOF sentinel, not a data frame.
            depth = None if assembler.closed else assembler.frames.qsize()
            paused = assembler.paused
        if (depth is not None and (type(depth) is not int or depth < 0)) or type(paused) is not bool:
            raise ContractError("unexpected pinned assembler diagnostics")
        return {"library_queue_depth": depth, "library_backpressure_active": paused}

    def send(self, message):
        return self.connection.send(message)

    def recv(self, timeout):
        """Raw message and hash-bound delivery metadata; idle timeout stays idle.

        Reader-loop elapsed is time OUTSIDE recv since its previous return or
        timeout. It includes observer work and caller processing; not pure stalls.
        Queue snapshot is after the delivery bracket, before marker consumption.
        """
        if not self.reader_lock.acquire(blocking=False):
            raise ContractError("receive adapter permits only one application reader")
        try:
            entered = self.monotonic()
            outside = None if self.last_exit is None else entered - self.last_exit
            if outside is not None and outside < 0:
                raise ContractError("reader-loop monotonic clock moved backwards")
            try:
                message = self.connection.recv(timeout=timeout)
            except TimeoutError:
                self.last_exit = self.monotonic()
                raise
            try:
                delivery = sample_clock(self.clock, self.monotonic, self.tracker.domain)
                self.last_exit = delivery["monotonic_after"]
                record = self.tracker.deliver(self.number, message, delivery,
                    reader_loop_stall_seconds=outside, **self.queue_snapshot())
            except Exception as exc:
                with self.tracker.lock:
                    if self.tracker.connection == self.number:
                        self.tracker._disable("application_telemetry_error")
                raw = message.encode("utf-8") if isinstance(message, str) else message
                record = {"schema_version": "qcrl.receive_adapter_failure.v1",
                          "contract_sha256": self.tracker.contract["contract_sha256"],
                          "connection": self.number, "raw_message_sha256": hashlib.sha256(raw).hexdigest(),
                          "unavailable_reason": "application_telemetry_error",
                          "error_type": type(exc).__name__, "orders_authorized": False,
                          "wire_arrival_measured": False}
                record["telemetry_sha256"] = payload_hash(record)
            return message, record
        finally:
            self.reader_lock.release()

    def close(self):
        # No telemetry lock while waiting for the library's receiver to exit.
        return self.connection.close()
