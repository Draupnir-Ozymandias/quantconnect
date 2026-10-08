from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from execution_truth import receive_path
from execution_truth.contracts import ContractError
from execution_truth.receive_recovery import ReceiveRecoveryTracker, validate_recovery_connection
from infra.stream import marker_cap_pair as cap
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE
from tests.test_receive_path import stamp, DOMAIN


class MarkerCapPairTests(unittest.TestCase):
    def test_only_receiver_marker_limit_changes(self):
        base = deepcopy(receive_path.POLICY_V3)
        with cap.scope('cap128'):
            self.assertEqual({k for k in base if base[k] != receive_path.POLICY_V3[k]},
                             {'max_pending_message_markers'})
            self.assertEqual(receive_path.POLICY_V3['max_pending_message_markers'], 128)
        self.assertEqual(receive_path.POLICY_V3, base)
        self.assertEqual(cap.POLICY['encoders'], ['single_pass'])

    def test_variant_is_rejected_outside_scope(self):
        with cap.scope('cap128'):
            contract = receive_path.declare('a'*64, DOMAIN, stream_spec_sha256='b'*64, policy_version='v3')
            receive_path.validate_contract(contract)
        with self.assertRaises(ContractError): receive_path.validate_contract(contract)
        with self.assertRaises(ContractError): cap.lane_policy('cap256')

    def test_scope_restores_on_exception(self):
        original = cap.original.POLICY
        base = receive_path.POLICY_V3
        with self.assertRaises(RuntimeError):
            with cap.scope('cap128'): raise RuntimeError('test')
        self.assertIs(cap.original.POLICY, original)
        self.assertIs(receive_path.POLICY_V3, base)

    def test_same_100_callbacks_overflow_only_the_64_lane(self):
        for lane, unknown in [('cap64', 36), ('cap128', 0)]:
            with cap.scope(lane):
                t = ReceiveRecoveryTracker(receive_path.declare('a'*64, DOMAIN,
                    stream_spec_sha256='b'*64, policy_version='v3'))
                t.begin_connection(1)
                for i in range(100): t.observe_frame(1, 1, True, b'same', stamp(i+1))
                records = [t.deliver(1, 'same', stamp(200+i)) for i in range(100)]
                self.assertEqual(sum(r['receive_marker'] is None for r in records), unknown)
                self.assertEqual(validate_recovery_connection(records, t.contract,
                    ['same']*100)['unknown'], unknown)

    def test_launcher_changes_only_paths_labels_and_cap_order(self):
        repo = Path(__file__).resolve().parents[1]
        expected = (repo/'infra/stream/run_encoding_pair.sh').read_text().replace(
            'encoding-pair-*', 'marker-cap-*').replace('encoding_pair.py', 'marker_cap_pair.py').replace(
            'qcrl-encoding-', 'qcrl-marker-cap-').replace('FINITE_ENCODING_PAIR_MEASURED',
            'FINITE_MARKER_CAP_PAIR_MEASURED').replace('encoders=(single_pass reference)',
            'encoders=(cap128 cap64)').replace('encoders=(reference single_pass)',
            'encoders=(cap64 cap128)').replace('--encoder "$encoder"', '--lane "$encoder"')
        self.assertEqual(expected, (repo/'infra/stream/run_marker_cap_pair.sh').read_text())

    @unittest.skipUnless(AVAILABLE, 'pinned optional WebSocket library required')
    def test_both_caps_real_socket_and_bound_verification(self):
        policy = dict(cap.POLICY, cycles=1, phases=[{'rate':500,'seconds':.01}, {'rate':3000,'seconds':.001}])
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp, patch.object(cap, 'POLICY', policy):
            root = Path(tmp); source = root/'input.json'; source.write_text(json.dumps(corpus()))
            cap.declare_run(source, root)
            for lane in cap.LANES:
                case = root/lane/'0'
                prefix = 'import json; from infra.stream import marker_cap_pair as c; c.POLICY=json.loads('+repr(json.dumps(policy))+'); c.execute('
                def command(role):
                    return [sys.executable, '-c', prefix+repr(role)+','+repr(str(root/lane))+','+repr(str(case))+','+repr(lane)+')']
                producer = subprocess.Popen(command('produce'), cwd=repo)
                try:
                    deadline = time.monotonic()+10
                    while True:
                        try: cap.original.burst.read(case/'ready.json','ready_sha256'); break
                        except (FileNotFoundError,json.JSONDecodeError):
                            if time.monotonic() >= deadline: raise
                            time.sleep(.01)
                    result = subprocess.run(command('consume'), cwd=repo, timeout=20, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(producer.wait(timeout=15), 0)
                    verified = cap.execute('verify', root/lane, case, lane)
                    self.assertTrue(verified['logical_hashes_and_representation_verified'])
                    with self.assertRaises(ContractError): cap.declare_run(source, root)
                finally:
                    if producer.poll() is None: producer.terminate(); producer.wait(timeout=5)


if __name__ == '__main__': unittest.main()
