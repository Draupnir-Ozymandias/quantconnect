"""Offline regressions for retained v6 termination/publication limits.

No production policy changes. Real library close paths use a deterministic join
seam rather than a peer or wall-clock sleeps; one subprocess tests the real guard.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from websockets.protocol import Protocol, Side, State
from websockets.sync.connection import Connection

from infra.stream import recorder_public_capture as capture
from infra.stream import recorder_public_recovery as recovery
from infra.stream.recorder_completion import verify_completion
from tests.test_public_fault_publication import setup
from tests.test_public_recovery import Harness
from tests.test_recorder_public_study import DummyInterrupt


def timeout_connection(on_timeout=lambda: None):
    """Exercise installed Connection.close/send_context/close_socket unchanged.

    The join seam represents a receive thread still alive at the handshake
    deadline, then terminated by close_socket. It does not model native timing.
    """
    conn = Connection.__new__(Connection)
    conn.protocol = Protocol(Side.CLIENT)
    conn.protocol_mutex = threading.Lock()
    conn.close_timeout = 5
    conn.close_deadline = None
    conn.send_in_progress = False
    conn.recv_exc = None
    conn.debug = False
    conn.send_data = Mock()
    conn.socket = Mock()
    conn.recv_messages = Mock()
    conn.acknowledge_pending_pings = Mock()
    joins = []

    def join(timeout=None):
        joins.append(timeout)
        if len(joins) == 1:
            on_timeout()

    conn.recv_events_thread = SimpleNamespace(join=join, is_alive=lambda: True)
    return conn, joins


class PublicTerminationReviewTests(unittest.TestCase):
    def test_library_close_return_can_follow_timeout_without_peer_close(self):
        conn, joins = timeout_connection()
        conn.close()
        self.assertEqual(conn.protocol.state, State.CLOSED)
        self.assertIsNone(conn.protocol.close_rcvd)
        self.assertIsInstance(conn.recv_exc, TimeoutError)
        self.assertEqual(len(joins), 2)
        self.assertLessEqual(joins[0], 5)
        self.assertIsNone(joins[1])  # Cleanup join has no library timeout.
        conn.socket.shutdown.assert_called_once()
        conn.socket.close.assert_called_once()

    def test_process_guard_wins_even_if_library_close_then_returns(self):
        with TemporaryDirectory() as d, patch.object(capture.os, 'kill') as kill:
            root = Path(d)
            _, _, _, conn, invoke, checkpoint, _ = setup(root)
            guards = []

            def guard(*args, **kwargs):
                value = capture.ConnectDeadline(*args, **kwargs)
                guards.append(value)
                return value

            library, _ = timeout_connection(lambda: guards[-1].interrupt())
            conn.close = library.close
            result = invoke(before_close=checkpoint, connect_guard_factory=guard)
            kill.assert_called_once_with(os.getpid(), signal.SIGTERM)
            self.assertTrue(guards[-1].fired.is_set())
            self.assertFalse(result['close_completed'])
            self.assertIn('close process guard fired', result['error'])
            # Acquisition ownership survives; it is separate from failed close.
            self.assertTrue(capture.normal_completion_proven(result))
            self.assertFalse(json.loads((root/'acquisition-checkpoint.json').read_text())['close_verified'])

    def test_actual_shared_frame_cap_seals_before_failed_close(self):
        # Release the 60,000-witness population at process exit rather than
        # retain its allocation arenas across the rest of a large test suite.
        with TemporaryDirectory() as d:
            program = (
                'from pathlib import Path;'
                'from tests.test_public_termination_review import PublicTerminationReviewTests;'
                'PublicTerminationReviewTests()._exercise_shared_frame_cap(Path('+repr(d)+'))')
            result = subprocess.run([sys.executable, '-c', program], capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)

    def _exercise_shared_frame_cap(self, root):
        h = Harness(root/'archive', [dict(recv=lambda *args: 'PONG',
                                         close_error=OSError('retained close fault'))])
        checkpoints = []

        def checkpoint(value):
            completion = h.witness.snapshot(h.root)
            verified = verify_completion(completion, h.root, expected_domain='test.recovery')
            self.assertEqual(verified['frames'], 60000)
            self.assertIsNone(value['closed'])
            self.assertFalse(value['close_completed'])
            checkpoints.append(value)

        # Harness normally snapshots after collect; snapshot is single-use.
        original = h.witness.snapshot
        with patch.object(h.witness, 'snapshot', side_effect=original) as snapshot:
            # Call the actual recorder directly to avoid a second snapshot.
            result = capture.collect(h.raw, h.spec, h.root, epoch_ns=20_000_000_000,
                observer=h.witness, execute=True, clock=h.clock.utc, monotonic=h.clock.mono,
                connect_factory=h.connect, guard=SimpleNamespace(check=lambda: None),
                interrupt_factory=DummyInterrupt,
                connect_guard_factory=DummyInterrupt,
                recovery_policy=recovery.policy(),
                before_close=checkpoint)
            snapshot.assert_called_once()
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(result['summary']['status'], 'frame_limit')
        self.assertEqual(result['summary']['frames'], 60000)
        self.assertEqual(h.calls, 1)
        self.assertLess(result['acquisition_ended'], result['acquisition_deadline'])
        self.assertIsNone(result['normal_completion'])
        self.assertFalse(result['close_completed'])
        self.assertIn('retained close fault', result['close_errors'][0])
        self.assertTrue(h.witness.closed)

    def test_library_protocol_lock_is_still_bounded_by_real_process_guard(self):
        with TemporaryDirectory() as d:
            program = '''
import threading
from pathlib import Path
from tests.test_public_fault_publication import setup
from infra.stream.recorder_public_capture import ConnectDeadline
from websockets.sync.connection import Connection
clock,spec,w,conn,invoke,checkpoint,case=setup(Path(ROOT))
library=Connection.__new__(Connection)
library.protocol_mutex=threading.Lock()
library.protocol_mutex.acquire()
conn.close=library.close
invoke(before_close=checkpoint,connect_guard_factory=ConnectDeadline)
'''.replace('ROOT', repr(d))
            result = subprocess.run([sys.executable, '-c', program], capture_output=True, timeout=9)
            self.assertEqual(result.returncode, -signal.SIGTERM, result.stderr)
            checkpoint = json.loads((Path(d)/'acquisition-checkpoint.json').read_text())
            self.assertFalse(checkpoint['close_verified'])
            self.assertTrue((Path(d)/'completion.json').is_file())
            self.assertFalse((Path(d)/'consumer.json').exists())


if __name__ == '__main__':
    unittest.main()
