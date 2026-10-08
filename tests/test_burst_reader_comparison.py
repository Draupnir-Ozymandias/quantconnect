import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import burst_reader_comparison as burst
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE


class BurstReaderTests(unittest.TestCase):
    def test_only_numeric_loopback_producer_is_allowed(self):
        burst.localhost_uri("ws://127.0.0.1:12345")
        for uri in ("ws://127.0.0.1:12@evil.invalid", "wss://127.0.0.1:12",
                    "ws://localhost:12", "ws://127.0.0.1:12/path", "ws://127.0.0.1:99999"):
            with self.assertRaises(ContractError): burst.localhost_uri(uri)
    def test_fixed_schedule_has_six_cycles_and_30000_messages(self):
        targets = burst.offsets()
        self.assertEqual(len(targets), 30000)
        self.assertEqual(targets[2000], {"offset": 4.0, "phase_rate": 3000})
        self.assertEqual(targets[5000], {"offset": 5.0, "phase_rate": 500})
        self.assertAlmostEqual(targets[-1]["offset"], 30-1/3000)
        self.assertEqual(sum(t.get("synthetic_pong") is True for t in targets), 6)
        self.assertTrue(all(b["offset"] > a["offset"] for a,b in zip(targets, targets[1:])))
        with self.assertRaises(ContractError): burst.offsets(cycles=7)
        with self.assertRaises(ContractError): burst.offsets(phases=[{"rate": 3001, "seconds": 1}])

    @unittest.skipUnless(AVAILABLE, "pinned optional WebSocket library required")
    def test_separate_processes_all_modes_raw_identity_and_exclusive_report(self):
        # Short test-only policy is explicitly declared and injected into each
        # subprocess; production CLI cannot select it or alter its fixed policy.
        policy = dict(burst.POLICY, cycles=1, phases=[{"rate": 500, "seconds": .01},
                                                     {"rate": 3000, "seconds": .001}])
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp, patch.object(burst, "POLICY", policy):
            root = Path(tmp)
            source = root / "input.json"
            source.write_text(json.dumps(corpus()))
            burst.declare_run(source, root)
            with self.assertRaises(FileExistsError): burst.declare_run(source, root)
            for mode in policy["modes"]:
                case = root / mode
                command = ("import json; from infra.stream import burst_reader_comparison as b; "
                           "b.POLICY=json.loads(" + repr(json.dumps(policy)) + "); b.")
                producer = subprocess.Popen([sys.executable, "-c", command +
                    "produce("+repr(str(root))+","+repr(str(case))+","+repr(mode)+")"], cwd=repo)
                try:
                    deadline = time.monotonic()+10
                    while not (case/"ready.json").exists() and time.monotonic()<deadline:
                        time.sleep(.01)
                    # Exclusive JSON publication can be observed before close;
                    # tests wait for valid complete JSON, as the Linux launcher
                    # does before starting the consumer.
                    while True:
                        try:
                            burst.read(case/"ready.json", "ready_sha256")
                            break
                        except (FileNotFoundError, json.JSONDecodeError):
                            if time.monotonic() >= deadline: raise
                            time.sleep(.01)
                    consumer = subprocess.run([sys.executable, "-c", command +
                        "consume("+repr(str(root))+","+repr(str(case))+","+repr(mode)+")"],
                        cwd=repo, timeout=20, capture_output=True, text=True)
                    self.assertEqual(consumer.returncode, 0, consumer.stderr)
                    self.assertEqual(producer.wait(timeout=15), 0)
                    result = burst.verify_case(root, case, mode)
                    self.assertEqual(result["messages"], 8)
                    self.assertTrue(result["raw_identity_verified"])
                    self.assertEqual(burst.read(case/"deliveries.json", "delivery_sha256")["raws"][-1], "PONG")
                    self.assertNotEqual(result["producer_identity"]["pid"],result["consumer_identity"]["pid"])
                    with self.assertRaises(FileExistsError): burst.verify_case(root, case, mode)
                    data = burst.read(case/"deliveries.json", "delivery_sha256")
                    data["raws"][0] = "{}"
                    data.pop("delivery_sha256")
                    data["delivery_sha256"] = payload_hash(data)
                    (case/"deliveries.json").write_text(json.dumps(data))
                    with self.assertRaises(ContractError): burst.verify_case(root, case, mode)
                finally:
                    if producer.poll() is None:
                        producer.terminate(); producer.wait(timeout=5)
