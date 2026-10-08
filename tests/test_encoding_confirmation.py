import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from infra.stream import encoding_confirmation as confirmation
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE


class EncodingConfirmationTests(unittest.TestCase):
    def test_only_policy_identity_and_order_change(self):
        changed={key for key in confirmation.POLICY
                 if confirmation.POLICY[key]!=confirmation.original.POLICY.get(key)}
        self.assertEqual(changed,{"schema_version","encoder_order","confirmation_of_source"})

    def test_launcher_diff_is_only_paths_order_and_labels(self):
        repo=Path(__file__).resolve().parents[1]
        original=(repo/"infra/stream/run_encoding_pair.sh").read_text()
        expected=original.replace("encoding-pair-*","encoding-confirmation-*").replace(
            "encoding_pair.py","encoding_confirmation.py").replace(
            'qcrl-encoding-','qcrl-encoding-confirm-').replace(
            'then encoders=(single_pass reference); else encoders=(reference single_pass)',
            'then encoders=(reference single_pass); else encoders=(single_pass reference)').replace(
            'FINITE_ENCODING_PAIR_MEASURED','FINITE_ENCODING_CONFIRMATION_MEASURED')
        self.assertEqual(expected,(repo/"infra/stream/run_encoding_confirmation.sh").read_text())

    @unittest.skipUnless(AVAILABLE,"pinned optional WebSocket library required")
    def test_both_lanes_short_separate_process_smoke(self):
        policy=dict(confirmation.POLICY,cycles=1,phases=[{"rate":500,"seconds":.01},{"rate":3000,"seconds":.001}])
        repo=Path(__file__).resolve().parents[1]
        original_policy=confirmation.original.POLICY
        with tempfile.TemporaryDirectory() as tmp,patch.object(confirmation,"POLICY",policy):
            root=Path(tmp); source=root/"input.json"
            source.write_text(json.dumps(corpus()))
            confirmation.declare_run(source,root)
            for encoder in policy["encoders"]:
                lane,case=root/encoder,root/encoder/"0"
                prefix="import json; from infra.stream import encoding_confirmation as c; c.POLICY=json.loads("+repr(json.dumps(policy))+"); c.execute("
                def command(role):
                    return [sys.executable,"-c",prefix+repr(role)+","+repr(str(lane))+","+repr(str(case))+","+repr(encoder)+")"]
                producer=subprocess.Popen(command("produce"),cwd=repo)
                try:
                    deadline=time.monotonic()+10
                    while True:
                        try: confirmation.original.burst.read(case/"ready.json","ready_sha256"); break
                        except (FileNotFoundError,json.JSONDecodeError):
                            if time.monotonic()>=deadline: raise
                            time.sleep(.01)
                    result=subprocess.run(command("consume"),cwd=repo,timeout=20,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(producer.wait(timeout=15),0)
                    verified=confirmation.execute("verify",lane,case,encoder)
                    self.assertTrue(verified["logical_hashes_and_representation_verified"])
                finally:
                    if producer.poll() is None: producer.terminate(); producer.wait(timeout=5)
            self.assertIs(confirmation.original.POLICY,original_policy)
