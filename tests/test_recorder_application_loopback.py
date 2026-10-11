"""Tiny functional socket test only; not the preregistered performance cohort."""
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from execution_truth.acquisition import utc_now, utc_text
from execution_truth.contracts import ContractError
from execution_truth.market_stream import stream_plan
from infra.stream.recorder_application_worker import LoopbackSocket, message, control
from infra.stream.recorder_completion import CompletionWitnesses, verify_completion
from infra.stream.recorder_completion_lane import collect_with_completion
from tests.test_taker_replay import raw_bundle, revise


class LoopbackTests(unittest.TestCase):
    def test_real_socket_recorder_duplicate_links_and_exclusive_ready(self):
        from websockets.sync.server import serve
        raw = raw_bundle()
        now = utc_now()
        revise(raw, 'gamma_market', startDate=utc_text(now-timedelta(seconds=60)),
               eventStartTime=utc_text(now-timedelta(seconds=10)),
               endDate=utc_text(now+timedelta(seconds=290)))
        spec = stream_plan(raw, segmented=True, max_seconds=5, max_frames=68)
        frames = [message(i) for i in range(68)]
        errors, subscriptions = [], []
        def handler(conn):
            try:
                subscriptions.append(json.loads(conn.recv(timeout=2)))
                for frame in frames:
                    conn.send(frame)
                try:
                    conn.recv(timeout=2)
                except Exception:
                    pass  # Client close after finite recorder stop.
            except Exception as exc:
                errors.append(str(exc))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with serve(handler, '127.0.0.1', 0, compression=None, ping_interval=None,
                       max_size=262144, max_queue=16, close_timeout=1) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                uri = 'ws://127.0.0.1:' + str(server.socket.getsockname()[1])
                observer = CompletionWitnesses(spec, 'test-loopback', clock=utc_now,
                                                monotonic=time.monotonic, execute=True)
                summary = collect_with_completion(raw, spec, root/'archive',
                    connector=lambda: LoopbackSocket(uri, root, {'artifact_sha256': 'test-case'}, {'pid': 1}),
                    clock=utc_now, monotonic=time.monotonic, completion_observer=observer)
                server.shutdown()
                thread.join(timeout=2)
            report = observer.snapshot(root/'archive')
            verified = verify_completion(report, root/'archive', expected_domain='test-loopback')
            self.assertEqual(verified['frames'], 68)
            self.assertEqual(summary['status'], 'frame_limit')
            self.assertEqual(summary['connections'], 1)
            self.assertEqual(summary['book_snapshot_assets_by_connection'], {'1': ['10001', '10002']})
            self.assertEqual(subscriptions, [spec['subscription']])
            self.assertEqual(errors, [])
            ready = control(root/'worker-ready.json')
            self.assertEqual(ready['case_sha256'], 'test-case')
            self.assertFalse(verified['acceptance_demonstrated'])

    def test_remote_uri_refused_before_connect(self):
        with patch('websockets.sync.client.connect') as connect:
            for uri in ('wss://127.0.0.1:1234', 'ws://example.com:1234',
                        'ws://localhost:1234', 'ws://127.0.0.1:1234/path'):
                with self.assertRaises(ContractError):
                    LoopbackSocket(uri, '/does-not-exist', {}, {})
            connect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
