from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from execution_truth.contracts import ContractError
from infra.stream import receive_loop_reader_comparison as compare


class ComparisonTests(unittest.TestCase):
    def fixture(self,root):
        proc=root/'proc';mount=root/'cgroup'
        (proc/'sys/kernel/random').mkdir(parents=True);(proc/'10').mkdir()
        (mount/'private').mkdir(parents=True)
        (proc/'sys/kernel/random/boot_id').write_text('boot')
        (proc/'10/stat').write_text('10 (fixture) '+' '.join(['S']+['0']*18+['123']))
        (proc/'10/cgroup').write_text('0::/private\n')
        (mount/'private/cpu.stat').write_text('usage_usec 12\nnr_periods 4\nnr_throttled 0\nthrottled_usec 0\n')
        return dict(boot_id='boot',pid=10,process_start_id='123',cgroup='/private'),proc,mount

    def test_execution_barrier(self):
        with self.assertRaises(ContractError):compare.run({})

    def test_population_order_and_no_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            own,p,m=self.fixture(Path(tmp).resolve())
            r=compare.run(own,execute=True,proc_root=p,cgroup_root=m)
            self.assertEqual([(x['round'],x['lane']) for x in r['rows']],
                             [(i,l) for i,ls in enumerate(compare.POLICY['order']) for l in ls])
            self.assertTrue(all(len(x['samples'])==100 and x['total_cpu']>=0 for x in r['rows']))
            self.assertFalse(r['probe_cost_accepted'])

    def test_wrong_expected_identity_fails_original_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            own,p,m=self.fixture(Path(tmp).resolve());own['process_start_id']='wrong'
            with self.assertRaises(ContractError):compare.run(own,execute=True,proc_root=p,cgroup_root=m)

    def test_native_fault_never_replayed(self):
        with patch.object(compare.CounterReader,'read',side_effect=OSError('fault')) as read:
            with self.assertRaises(OSError):compare.run({'pid':1},execute=True)
            self.assertEqual(read.call_count,1)
