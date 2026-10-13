import unittest
from execution_truth.contracts import ContractError, verify_artifact_hash
from infra.stream import recorder_wait_comparison as comparison
from infra.stream.recorder_absolute_wait import MAX_NS


class WaitComparisonTests(unittest.TestCase):
    def test_preregistered_protocol_hash_is_pinned(self):
        self.assertEqual(
            comparison.declaration()['plan_sha256'],
            'a5d43bd01b36c616edd4bd594f673126f392e327bdf1f2d9d98929ae3d7bd3ee',
        )

    def test_locked_integer_population_balanced_order_and_duration(self):
        for index, order in enumerate((['select', 'absolute'], ['absolute', 'select'])):
            rows = comparison.targets(17, index)
            self.assertEqual(len(rows), 12)
            self.assertEqual([rows[0]['arm'], rows[6]['arm']], order)
            self.assertEqual(rows[-1]['target_ns'], 133_300_000_017)
            previous = 17
            for row in rows:
                self.assertEqual(row['target_ns']-previous, row['interval_ns'])
                previous = row['target_ns']
            self.assertEqual(rows[5]['target_ns'], 66_650_000_017)

    def test_invalid_indices_epochs_and_overflow_refused(self):
        for index in (True, -1, 2, 0.0):
            with self.assertRaises(ContractError): comparison.targets(0, index)
        for epoch in (True, -1, 0.0, MAX_NS-133_300_000_000+1):
            with self.assertRaises(ContractError): comparison.targets(epoch, 0)
        self.assertEqual(comparison.targets(MAX_NS-133_300_000_000, 1)[-1]['target_ns'], MAX_NS)

    def test_declaration_hash_and_mutation_isolation(self):
        value = comparison.declaration()
        verify_artifact_hash(value, 'plan_sha256', 'comparison')
        value['run_blocks'][0].reverse()
        self.assertEqual(comparison.declaration()['run_blocks'][0], ['select', 'absolute'])
        for key in ('native_execution_authorized', 'resource_changes_authorized',
                    'acceptance_demonstrated', 'orders_authorized'):
            self.assertIs(comparison.declaration()[key], False)


if __name__ == '__main__': unittest.main()
