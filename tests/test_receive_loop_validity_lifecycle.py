from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream import receive_loop_validity_lifecycle as life
from infra.stream.receive_loop_validity import CounterSample
from infra.stream.receive_loop_validity_probe import CounterRead


def fixture(role, root, lane, fault=None):
    # Tiny synthetic process tests, not protocol workloads or real cost evidence.
    if role == 'worker':
        if fault == 'prepare':
            with patch('infra.stream.receive_loop_validity_worker.prepare', side_effect=OSError('fixture prepare fault')):
                life.worker(root, 0, lane, execute=True)
        elif fault == 'snapshot':
            with patch.object(life.WorkloadCore, 'finish', side_effect=ContractError('fixture snapshot fault')):
                life.worker(root, 0, lane, execute=True)
        else: life.worker(root, 0, lane, execute=True)
    else:
        class FixtureReader:
            def __init__(self, pid, capacity): self.rows = []
            def read(self):
                own = life.read(Path(root)/'0'/lane/'worker-ready.json')['identity']
                t = time.monotonic()
                sample = CounterSample(**own, read_begin=t, read_end=time.monotonic(),
                                       counters=(('usage_usec', len(self.rows)+1),))
                result = CounterRead(sample, None)
                self.rows.append(result)
                return result
            def finish(self): return dict(reads=tuple(self.rows), complete=True)
        with patch('infra.stream.receive_loop_validity_observer.CounterReader', FixtureReader):
            life.observer(root, 0, lane, execute=True)


class LifecycleTests(unittest.TestCase):
    def run_case(self, root, lane, fault=None):
        repo = str(Path(__file__).resolve().parents[1])
        procs = []
        for role in ('worker', 'observer'):
            code = 'from tests.test_receive_loop_validity_lifecycle import fixture; fixture(%r,%r,%r,%r)' % (role,str(root),lane,fault)
            procs.append(subprocess.Popen([sys.executable, '-c', code], cwd=repo,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        try:
            outputs = [p.communicate(timeout=8) for p in procs]
            return [p.returncode for p in procs], outputs
        finally:
            for p in procs:
                if p.poll() is None: p.kill(); p.communicate()

    def test_separate_processes_all_lanes_order_identity_raw_and_windows(self):
        for lane in ('control', 'pacing', 'full'):
            with self.subTest(lane=lane), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()/'trial'; life.stage(root, test_only=True)
                codes, output = self.run_case(root, lane)
                self.assertEqual(codes, [0,0], output)
                report = life.verify_case(root, 0, lane)
                self.assertEqual(report['verified_occurrences'], 8)
                self.assertTrue(report['test_only'])
                self.assertFalse(report['units_audited'])
                with self.assertRaises(FileExistsError): life.worker(root,0,lane,execute=True)

    def test_prepare_fault_acknowledges_and_preserves_no_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'trial'; life.stage(root,test_only=True)
            codes, _ = self.run_case(root,'control','prepare')
            self.assertTrue(all(c != 0 for c in codes))
            case = root/'0/control'
            self.assertTrue((case/'observer-done.json').is_file())
            self.assertTrue((case/'raw-deliveries.json').is_file())
            with self.assertRaises(ContractError): life.verify_case(root,0,'control')

    def test_snapshot_fault_retains_all_raws_without_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'trial'; life.stage(root,test_only=True)
            codes, _ = self.run_case(root,'pacing','snapshot')
            self.assertNotEqual(codes[0],0)
            case = root/'0/pacing'
            self.assertEqual(len(life.read(case/'raw-deliveries.json')['raws']),8)
            self.assertTrue((case/'snapshot-failure.json').is_file())
            self.assertFalse((case/'worker-result.json').exists())

    def test_no_execution_no_claims_and_fresh_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'trial'; life.stage(root,test_only=True)
            with self.assertRaises(FileExistsError): life.stage(root,test_only=True)
            for role in (life.worker, life.observer):
                with self.assertRaises(ContractError): role(root,0,'control')
            self.assertFalse((root/'0').exists())

    def test_finite_timeout_invalid_round_and_source_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'trial'; life.stage(root,test_only=True)
            with self.assertRaises(ContractError): life.wait(root/'missing', .01)
            with self.assertRaises(ContractError): life.context(root,True,'control')
            with patch.object(life,'sources',return_value={}):
                with self.assertRaises(ContractError): life.context(root,0,'control')

    def test_observer_startup_timeout_retains_claim_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'trial'; life.stage(root,test_only=True)
            with patch.object(life,'wait',side_effect=ContractError('fixture timeout')):
                with self.assertRaises(ContractError): life.observer(root,0,'control',execute=True)
            case = root/'0/control'
            self.assertTrue((case/'observer-claim.json').is_file())
            self.assertTrue((case/'observer-startup-failure.json').is_file())
            self.assertFalse((case/'observer-result.json').exists())

    def test_offline_verification_missing_case_does_not_create_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()/'trial'; life.stage(root,test_only=True)
            with self.assertRaises(FileNotFoundError): life.verify_case(root,0,'control')
            self.assertFalse((root/'0').exists())

    def test_production_cannot_disable_binding_and_tiny_fixture_can_require_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'trial'
            with self.assertRaises(ContractError):life.stage(root,live_bindings=False)
            self.assertFalse(root.exists())
            life.stage(root,test_only=True,live_bindings=True)
            _,r=life.context(root,0,'control')
            self.assertTrue(r['requires_live_bindings'])
            self.assertTrue(r['test_only'])


if __name__ == '__main__': unittest.main()
