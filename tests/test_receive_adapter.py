from contextlib import contextmanager
import importlib.util
import threading
import time
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, verify_artifact_hash
from execution_truth.receive_adapter import ObservedSocket, _load_library, validate_adapter_failure
from execution_truth.receive_path import ReceivePathTracker, declare, validate_delivery


AVAILABLE = importlib.util.find_spec("websockets") is not None


def tracker():
    return ReceivePathTracker(declare("a" * 64, "loopback:boot-test", stream_spec_sha256="b" * 64))


@contextmanager
def local_server(handler):
    from websockets.sync.server import serve
    failures = []
    def checked(connection):
        try:
            handler(connection)
        except Exception as exc:
            failures.append(exc)
    with serve(checked, "127.0.0.1", 0, compression=None, ping_interval=None, close_timeout=.5) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield "ws://127.0.0.1:" + str(server.socket.getsockname()[1])
        finally:
            server.shutdown()
            thread.join(3)
        if thread.is_alive():
            raise AssertionError("Loopback server failed to shut down")
    if failures:
        raise AssertionError("Loopback handler failed: " + repr(failures))


class AdapterBoundaryTests(unittest.TestCase):
    def test_version_mismatch_rejected_before_network(self):
        with patch("execution_truth.receive_adapter.version", return_value="99.0"):
            with self.assertRaisesRegex(ContractError, "15.0.1"):
                _load_library()

    def test_unapproved_uri_rejected_before_network(self):
        for uri in ("wss://example.com/orders", "ws://user:password@127.0.0.1:1", "ws://192.168.1.2:1"):
            with self.assertRaisesRegex(ContractError, "public market"):
                ObservedSocket(uri, tracker(), 1)


@unittest.skipUnless(AVAILABLE, "optional pinned websockets library is not installed")
class RealAdapterTests(unittest.TestCase):
    def test_fragmented_utf8_duplicates_binary_and_shutdown(self):
        finished = threading.Event()
        def handler(conn):
            conn.send([b"\xe2", b"\x82\xac"], text=True)
            conn.send("€")
            conn.send(b"binary")
            conn.ping(b"control").wait(2)
            conn.recv(timeout=3)
            finished.set()
        t = tracker()
        with local_server(handler) as uri:
            client = ObservedSocket(uri, t, 1)
            try:
                records = []
                for expected in ("€", "€", b"binary"):
                    message, record = client.recv(3)
                    self.assertEqual(message, expected)
                    validate_delivery(record, t.contract, message)
                    records.append(record)
                self.assertGreaterEqual(records[0]["receive_marker"]["fragment_count"], 2)
                self.assertEqual([r["receive_marker"]["message_sequence"] for r in records], [1, 2, 3])
                self.assertEqual(records[0]["receive_marker"]["raw_message_sha256"], records[1]["receive_marker"]["raw_message_sha256"])
                client.send("done")
                self.assertTrue(finished.wait(3))
            finally:
                client.close()
            self.assertFalse(client.connection.recv_events_thread.is_alive())

    def test_idle_timeout_does_not_consume_metadata(self):
        release = threading.Event()
        def handler(conn):
            if not release.wait(3):
                raise RuntimeError("test release missing")
            conn.send("after-idle")
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                with self.assertRaises(TimeoutError):
                    client.recv(.05)
                self.assertIsNone(t.disabled_reason)
                release.set()
                message, record = client.recv(3)
                validate_delivery(record, t.contract, message)
                self.assertEqual(record["receive_marker"]["message_sequence"], 1)
                self.assertGreaterEqual(record["reader_loop_stall_seconds"], 0)
                client.send("done")
            finally:
                release.set()
                client.close()

    def test_partial_fragment_timeout_resumes_without_double_counting(self):
        first, release = threading.Event(), threading.Event()
        def fragments():
            yield "part-"
            first.set()
            if not release.wait(3):
                raise RuntimeError("fragment release missing")
            yield "two"
        def handler(conn):
            conn.send(fragments())
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                self.assertTrue(first.wait(3))
                with self.assertRaises(TimeoutError):
                    client.recv(.05)
                release.set()
                message, record = client.recv(3)
                self.assertEqual(message, "part-two")
                self.assertEqual(record["receive_marker"]["message_sequence"], 1)
                validate_delivery(record, t.contract, message)
                client.send("done")
            finally:
                release.set()
                client.close()

    def test_fragment_budget_overflow_preserves_raw_message(self):
        def handler(conn):
            conn.send(["x"] * 65)
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                message, record = client.recv(3)
                self.assertEqual(message, "x" * 65)
                self.assertFalse(record["telemetry_available"])
                self.assertEqual(record["unavailable_reason"], "message_telemetry_budget")
                validate_delivery(record, t.contract, message)
                client.send("done")
            finally:
                client.close()

    def test_real_backpressure_preserved_and_queue_drains(self):
        sent = threading.Event()
        def handler(conn):
            for i in range(32):
                conn.send(str(i))
            sent.set()
            conn.recv(timeout=5)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                self.assertTrue(sent.wait(3))
                deadline = time.monotonic() + 3
                while not client.queue_snapshot()["library_backpressure_active"] and time.monotonic() < deadline:
                    threading.Event().wait(.01)
                snapshot = client.queue_snapshot()
                self.assertTrue(snapshot["library_backpressure_active"])
                self.assertGreater(snapshot["library_queue_depth"], 16)
                for i in range(32):
                    message, record = client.recv(3)
                    self.assertEqual(message, str(i))
                    validate_delivery(record, t.contract, message)
                self.assertEqual(client.queue_snapshot()["library_queue_depth"], 0)
                self.assertFalse(client.queue_snapshot()["library_backpressure_active"])
                client.send("done")
            finally:
                client.close()

    def test_telemetry_failure_does_not_drop_a_valid_message(self):
        def handler(conn):
            conn.send("raw-survives")
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                with patch.object(t, "deliver", side_effect=RuntimeError("diagnostic failure")):
                    message, record = client.recv(3)
                self.assertEqual(message, "raw-survives")
                self.assertEqual(record["schema_version"], "qcrl.receive_adapter_failure.v1")
                self.assertNotIn("last_observation_to_delivery", record)
                verify_artifact_hash(record, "telemetry_sha256", "adapter failure")
                validate_adapter_failure(record, t.contract, message)
                with self.assertRaises(ContractError):
                    validate_adapter_failure(record, t.contract, "changed")
                client.send("done")
            finally:
                client.close()

    def test_receiver_callback_failure_preserves_message_and_diagnostic_reason(self):
        release = threading.Event()
        def handler(conn):
            if not release.wait(3):
                raise RuntimeError("release missing")
            conn.send("callback-survives")
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                with patch.object(t, "observe_frame", side_effect=RuntimeError("callback failure")):
                    release.set()
                    message, record = client.recv(3)
                self.assertEqual(message, "callback-survives")
                self.assertFalse(record["telemetry_available"])
                self.assertEqual(record["unavailable_reason"], "receiver_observation_error")
                validate_delivery(record, t.contract, message)
                client.send("done")
            finally:
                release.set()
                client.close()

    def test_reader_loop_diagnostic_captures_time_outside_recv(self):
        def handler(conn):
            conn.send("one")
            conn.send("two")
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            try:
                client.recv(3)
                threading.Event().wait(.015)
                message, record = client.recv(3)
                self.assertEqual(message, "two")
                self.assertGreaterEqual(record["reader_loop_stall_seconds"], .014)
                self.assertEqual(record["diagnostic_scope"], "same_connection_external_adapter_observation")
                client.send("done")
            finally:
                client.close()

    def test_second_reader_rejected_without_poisoning_first_reader(self):
        release = threading.Event()
        def handler(conn):
            if not release.wait(3):
                raise RuntimeError("reader release missing")
            conn.send("one-reader")
            conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            client = ObservedSocket(uri, t, 1)
            results, failures = [], []
            def read():
                try:
                    results.append(client.recv(3))
                except Exception as exc:
                    failures.append(exc)
            thread = threading.Thread(target=read, daemon=True)
            try:
                thread.start()
                deadline = time.monotonic() + 2
                while not client.reader_lock.locked() and time.monotonic() < deadline:
                    threading.Event().wait(.001)
                self.assertTrue(client.reader_lock.locked())
                with self.assertRaisesRegex(ContractError, "one application reader"):
                    client.recv(.1)
                release.set()
                thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertFalse(failures)
                self.assertEqual(results[0][0], "one-reader")
                validate_delivery(results[0][1], t.contract, results[0][0])
                client.send("done")
            finally:
                release.set()
                client.close()
                thread.join(3)

    def test_reconnect_and_retired_callbacks_cannot_poison_new_connection(self):
        send_late, late_sent = threading.Event(), threading.Event()
        count, lock = [0], threading.Lock()
        def handler(conn):
            with lock:
                count[0] += 1
                which = count[0]
            if which == 1:
                if not send_late.wait(3):
                    raise RuntimeError("late callback release missing")
                conn.send("retired")
                late_sent.set()
                conn.recv(timeout=3)
            else:
                conn.send("current")
                conn.recv(timeout=3)
        with local_server(handler) as uri:
            t = tracker()
            old = ObservedSocket(uri, t, 1)
            current = ObservedSocket(uri, t, 2)
            try:
                send_late.set()
                self.assertTrue(late_sent.wait(3))
                # Drain the retired transport to ensure its callback ran; its
                # metadata is unavailable, while the new observer stays intact.
                message, failure = old.recv(3)
                self.assertEqual(message, "retired")
                self.assertEqual(failure["schema_version"], "qcrl.receive_adapter_failure.v1")
                message, record = current.recv(3)
                self.assertEqual(message, "current")
                self.assertIsNone(t.disabled_reason)
                validate_delivery(record, t.contract, message)
                old.send("done")
                current.send("done")
            finally:
                send_late.set()
                old.close()
                current.close()


if __name__ == "__main__":
    unittest.main()
