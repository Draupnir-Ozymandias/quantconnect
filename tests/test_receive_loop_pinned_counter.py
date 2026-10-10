import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_pinned_counter import PinnedCounterReader


class PinnedTests(unittest.TestCase):
    def test_nonregular_leaf_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r=self.fixture(root)
            path=root/'cgroup/private/cpu.stat';path.unlink();os.mkfifo(path)
            self.assertIsNone(r.read().sample);self.assertEqual(r.fds,[])

    def test_close_fault_preserved_other_descriptors_closed_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.fixture(Path(tmp).resolve());r.read()
            close=os.close;calls=[]
            def closed(fd):
                calls.append(fd);close(fd)
                if len(calls)==1:raise OSError('ambiguous close result')
            with patch('infra.stream.receive_loop_pinned_counter.os.close',side_effect=closed):
                report=r.finish()
            self.assertFalse(report['complete']);self.assertEqual(len(report['cleanup_errors']),1)
            self.assertEqual(len(calls),len(set(calls)));self.assertEqual(r.fds,[])

    def fixture(self,root,capacity=3):
        proc=root/'proc';mount=root/'cgroup'
        (proc/'sys/kernel/random').mkdir(parents=True);(proc/'10').mkdir()
        (mount/'private').mkdir(parents=True)
        (proc/'sys/kernel/random/boot_id').write_text('boot')
        (proc/'10/stat').write_text('10 (fixture) '+' '.join(['S']+['0']*18+['123']))
        (proc/'10/cgroup').write_text('0::/private\n')
        (mount/'private/cpu.stat').write_text('usage_usec 12\nnr_throttled 0\n')
        return PinnedCounterReader(dict(boot_id='boot',pid=10,process_start_id='123',cgroup='/private'),
                                   capacity,execute=True,proc_root=proc,cgroup_root=mount,
                                   monotonic=Mock(side_effect=range(100)))

    def test_reads_fresh_data_retains_partial_fields_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r=self.fixture(root)
            self.assertIsNone(r.read().error);fds=list(r.fds)
            (root/'cgroup/private/cpu.stat').write_text('usage_usec 20\n')
            self.assertEqual(dict(r.read().sample.counters),{'usage_usec':20})
            self.assertTrue(r.finish()['complete']);self.assertEqual(r.fds,[])
            for fd in fds:
                with self.assertRaises(OSError):os.fstat(fd)
            with self.assertRaises(ContractError):r.finish()

    def test_identity_change_before_read_and_no_replay(self):
        for file,text in (('stat','10 (new) '+' '.join(['S']+['0']*18+['124'])),
                          ('cgroup','0::/other\n')):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();r=self.fixture(root);r.read()
                (root/'proc/10'/file).write_text(text)
                self.assertIsNone(r.read().sample);self.assertFalse(r.finish()['complete'])
                with self.assertRaises(ContractError):r.read()

    def test_identity_change_during_counter_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r=self.fixture(root);original=r._text
            def text(key):
                value=original(key)
                if key=='counter':(root/'proc/10/cgroup').write_text('0::/other\n')
                return value
            with patch.object(r,'_text',side_effect=text):self.assertIsNone(r.read().sample)
            self.assertEqual(r.fds,[]);self.assertFalse(r.finish()['complete'])

    def test_replaced_leaf_deleted_leaf_parent_and_symlink_refused(self):
        for mutation in ('replace','delete','parent','symlink'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();r=self.fixture(root);r.read()
                path=root/'cgroup/private/cpu.stat'
                if mutation=='replace':
                    other=path.with_name('new');other.write_text('usage_usec 99');other.replace(path)
                elif mutation=='delete':path.unlink()
                elif mutation=='parent':
                    path.parent.rename(root/'cgroup/old');path.parent.mkdir();path.write_text('usage_usec 99')
                else:path.unlink();path.symlink_to(root/'proc/10/stat')
                self.assertIsNone(r.read().sample);self.assertEqual(r.fds,[])
                self.assertFalse(r.finish()['complete'])

    def test_initial_symlink_and_open_failure_release_descriptors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();r=self.fixture(root)
            path=root/'cgroup/private/cpu.stat';path.unlink();path.symlink_to(root/'proc/10/stat')
            self.assertIsNone(r.read().sample);self.assertEqual(r.fds,[])
        with tempfile.TemporaryDirectory() as tmp:
            r=self.fixture(Path(tmp).resolve())
            original=os.open;calls=[]
            def opened(*args,**kwargs):
                if len(calls)==3:raise PermissionError('fault')
                fd=original(*args,**kwargs);calls.append(fd);return fd
            with patch('infra.stream.receive_loop_pinned_counter.os.open',side_effect=opened):
                self.assertEqual(r.read().error,'PermissionError')
            for fd in calls:
                with self.assertRaises(OSError):os.fstat(fd)

    def test_byte_bounds_and_bad_encoding(self):
        for text in ('x'*4097,'usage_usec -1','usage_usec 1\nusage_usec 2','é'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve();r=self.fixture(root)
                (root/'cgroup/private/cpu.stat').write_text(text)
                self.assertIsNone(r.read().sample);self.assertFalse(r.finish()['complete'])

    def test_capacity_blocks_extra_reads_context_closes_and_barrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.fixture(Path(tmp).resolve(),1);r.read()
            with patch.object(r,'_paths') as paths:
                with self.assertRaises(ContractError):r.read()
                paths.assert_not_called()
            self.assertTrue(r.finish()['overflow'])
        with tempfile.TemporaryDirectory() as tmp:
            with self.fixture(Path(tmp).resolve()) as r:r.read()
            self.assertEqual(r.fds,[])
        with self.assertRaises(ContractError):PinnedCounterReader({})

    def test_wrong_initial_identity_and_owner_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=self.fixture(Path(tmp).resolve());r.expected['boot_id']='wrong'
            self.assertIsNone(r.read().sample);self.assertEqual(r.fds,[])
        with tempfile.TemporaryDirectory() as tmp:
            r=self.fixture(Path(tmp).resolve())
            with patch('infra.stream.receive_loop_pinned_counter.threading.get_ident',return_value=-1):
                self.assertIsNone(r.read().sample)
            self.assertEqual(r.fds,[])
