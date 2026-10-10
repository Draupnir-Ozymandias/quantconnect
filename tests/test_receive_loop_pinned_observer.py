import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from execution_truth.contracts import ContractError
from infra.stream.receive_loop_pinned_observer import PinnedObserverCore
from tests import test_receive_loop_pinned_counter as fixtures


class PinnedObserverTests(unittest.TestCase):
    def core(self,root,lane='full',capacity=2):
        fixture=fixtures.PinnedTests().fixture(root)
        return PinnedObserverCore(lane,fixture.expected,execute=True,capacity=capacity,
            monotonic=Mock(side_effect=[i/1000 for i in range(100)]),sleep=Mock(),
            proc_root=fixture.proc,cgroup_root=fixture.mount)

    def test_control_never_opens_reader(self):
        with patch('infra.stream.receive_loop_pinned_observer.PinnedCounterReader') as factory:
            for lane in ('control','pacing'):
                core=PinnedObserverCore(lane,dict(pid=1,boot_id='b',process_start_id='s',cgroup='/g'),
                    execute=True,monotonic=Mock(side_effect=[0,.1]),sleep=Mock())
                core.tick(.01);r=core.finish()
                self.assertIsNone(r['reader']);self.assertTrue(r['cleanup']['cleanup_complete'])
            factory.assert_not_called()

    def test_cleanup_before_materialization_and_no_more_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.core(Path(tmp).resolve());c.tick(.001);fds=list(c.reader.fds)
            receipt=c.cleanup();self.assertTrue(receipt['cleanup_complete'])
            for fd in fds:
                with self.assertRaises(OSError):os.fstat(fd)
            with self.assertRaises(ContractError):c.tick(.1)
            r=c.finish();self.assertTrue(r['complete']);self.assertFalse(r['probe_cost_accepted'])
            with self.assertRaises(ContractError):c.finish()

    def test_sleep_fault_after_read_releases_handles(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.core(Path(tmp).resolve());c.tick(.001);c.sleep.side_effect=OSError('sleep')
            with self.assertRaises(OSError):c.tick(.1)
            self.assertEqual(c.reader.fds,[]);self.assertFalse(c.finish()['complete'])

    def test_replaced_counter_retains_failed_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();c=self.core(root);c.tick(.001)
            p=root/'cgroup/private/cpu.stat';p.unlink();p.write_text('usage_usec 99')
            with self.assertRaises(ContractError):c.tick(.1)
            r=c.finish();self.assertEqual(len(r['rows']),2);self.assertFalse(r['complete'])
            self.assertIsNone(r['rows'][-1]['counter']['sample'])

    def test_close_error_cannot_be_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.core(Path(tmp).resolve());c.tick(.001)
            close=os.close
            def closed(fd):close(fd);raise OSError('ambiguous')
            with patch('infra.stream.receive_loop_pinned_counter.os.close',side_effect=closed):c.cleanup()
            self.assertFalse(c.finish()['complete'])

    def test_execution_barrier(self):
        with patch('infra.stream.receive_loop_pinned_observer.PinnedCounterReader') as factory:
            with self.assertRaises(ContractError):PinnedObserverCore('full',{})
            factory.assert_not_called()
