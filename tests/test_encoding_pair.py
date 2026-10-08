import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from infra.stream import encoding_pair as pair
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE


class EncodingPairTests(unittest.TestCase):
    @unittest.skipUnless(AVAILABLE, "pinned optional WebSocket library required")
    def test_both_encoders_real_loopback_separate_processes_and_restored_reference(self):
        policy = dict(pair.POLICY, cycles=1, phases=[{"rate":500,"seconds":.01},
                                                    {"rate":3000,"seconds":.001}])
        repo = Path(__file__).resolve().parents[1]
        original_class = pair.market_stream.SegmentedStreamLog
        original_policy = pair.burst.POLICY
        with tempfile.TemporaryDirectory() as tmp, patch.object(pair, "POLICY", policy):
            root = Path(tmp)
            source = root/"corpus-input.json"
            source.write_text(json.dumps(corpus()))
            pair.declare_run(source, root)
            for encoder in pair.POLICY["encoders"]:
                lane, case = root/encoder, root/encoder/"0"
                prefix = ("import json; from infra.stream import encoding_pair as p; p.POLICY=json.loads("
                          +repr(json.dumps(policy))+"); p.execute(")
                def command(role):
                    return [sys.executable,"-c",prefix+repr(role)+","+repr(str(lane))+","+
                            repr(str(case))+","+repr(encoder)+")"]
                producer = subprocess.Popen(command("produce"), cwd=repo)
                try:
                    deadline = time.monotonic()+10
                    while True:
                        try:
                            pair.burst.read(case/"ready.json", "ready_sha256"); break
                        except (FileNotFoundError,json.JSONDecodeError):
                            if time.monotonic() >= deadline: raise
                            time.sleep(.01)
                    consumed = subprocess.run(command("consume"), cwd=repo,timeout=20,capture_output=True,text=True)
                    self.assertEqual(consumed.returncode,0,consumed.stderr)
                    self.assertEqual(producer.wait(timeout=15),0)
                    verified = pair.execute("verify", lane, case, encoder)
                    self.assertTrue(verified["logical_hashes_and_representation_verified"])
                    report = pair.burst.read(case/"report.json","report_sha256")
                    self.assertEqual(report["messages"],8)
                    self.assertEqual(report["verification"]["frames"],8)
                    with self.assertRaises(FileExistsError): pair.execute("verify",lane,case,encoder)
                finally:
                    if producer.poll() is None: producer.terminate(); producer.wait(timeout=5)
            self.assertIs(pair.market_stream.SegmentedStreamLog,original_class)
            self.assertIs(pair.burst.POLICY,original_policy)
