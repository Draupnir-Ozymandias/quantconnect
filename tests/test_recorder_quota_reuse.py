"""Per-read quota reuse: complete inputs, fresh acquisition and fail-closed races."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream import recorder_application_resources as resources
from tests import test_recorder_application_components as fixtures


class QuotaReuseTests(unittest.TestCase):
    def test_snapshot_covers_validator_dependencies_and_structure(self):
        accessed = set()
        presence = set()

        class Tracked(dict):
            def __getitem__(self, key):
                accessed.add(key)
                return super().__getitem__(key)

            def __iter__(self):
                presence.update(self.keys())
                return super().__iter__()

        with TemporaryDirectory() as d:
            reader = fixtures.ResourceTests().ohio_fixture(Path(d).resolve())
            rows = reader.read()['ancestry']
            self.assertTrue(all(set(row) == {'path', 'cpu_max', 'cpuset_effective',
                'memory_max', 'controllers', 'subtree_control'} for row in rows))
            tracked = [Tracked(row) for row in rows]
            before = deepcopy(tracked)
            accessed.clear()
            presence.clear()
            self.assertEqual(resources.quota(tracked), .75)
            self.assertEqual(tracked, before)  # Validation does not mutate inputs.
            self.assertEqual(accessed, set(rows[0]) - {'memory_max'})
            self.assertEqual(presence, set(rows[0]))
            # Full equality includes key presence, every value and ordered ancestry;
            # even changes with an equal numeric quota cannot silently match.
            for index, row in enumerate(rows):
                for key in row:
                    for operation in ('delete', 'change'):
                        changed = deepcopy(rows)
                        if operation == 'delete':
                            del changed[index][key]
                        else:
                            changed[index][key] = 'different'
                        self.assertNotEqual(changed, rows, (index, key, operation))
            for changed in (rows[:-1], rows[::-1], rows + [rows[-1]]):
                self.assertNotEqual(changed, rows)

    def test_fresh_reads_and_brackets_one_validation_no_cross_read_cache(self):
        with TemporaryDirectory() as d:
            reader = fixtures.ResourceTests().ohio_fixture(Path(d).resolve())
            events, reads = [], []
            original_text, original_quota = resources.text, resources.quota
            stamps = iter((10, 10.006, 20, 20.006))
            def wall():
                events.append('wall')
                return next(stamps)
            def text(path):
                reads.append(str(path))
                return original_text(path)
            def quota(rows):
                events.append('quota')
                return original_quota(rows)
            def cpu():
                events.append('cpu')
                return 100
            reader.clock, reader.rss_thread_cpu, reader.thread_cpu_ns = wall, True, cpu
            with patch.object(resources, 'text', side_effect=text), patch.object(
                    resources, 'quota', side_effect=quota):
                first = reader.read(rss=True)
                first_reads = list(reads)
                self.assertEqual(events, ['wall', 'cpu', 'quota', 'cpu', 'wall'])
                self.assertEqual(len(first_reads), 48)
                self.assertEqual(first_reads.count(str(reader.proc/'10/status')), 1)
                self.assertEqual(first_reads.count(str(reader.group/'cpu.max')), 2)
                (reader.group/'cpu.max').write_text('25000 100000')
                events.clear()
                reads.clear()
                second = reader.read(rss=True)
            self.assertEqual(reads, first_reads)
            self.assertEqual(events, ['wall', 'cpu', 'quota', 'cpu', 'wall'])
            self.assertEqual((first['effective_quota'], second['effective_quota']), (.75, .25))
            self.assertEqual((first['rss_bytes'], second['rss_bytes']), (102400, 102400))
            self.assertAlmostEqual(first['after']-first['before'], .006)
            resources.verify_rss_thread_cpu(first,
                expected_thread_id=first['rss_thread_cpu']['thread_id'])

    def test_valid_closing_changes_even_same_quota_are_races(self):
        changes = (
            ('system.slice/unit/cpu.max', '50000 100000'),
            ('cpuset.cpus.effective', '0'),
            ('system.slice/unit/cgroup.controllers', 'memory cpu'),
            ('cgroup.subtree_control', 'memory cpu'),
            ('system.slice/unit/memory.max', '268435456'),
        )
        for relative, value in changes:
            with self.subTest(relative=relative), TemporaryDirectory() as d:
                reader = fixtures.ResourceTests().ohio_fixture(Path(d).resolve())
                members = reader.members
                calls = []
                def acquire():
                    calls.append(1)
                    result = members()
                    if len(calls) == 2:
                        (reader.mount/relative).write_text(value)
                    return result
                with patch.object(reader, 'members', side_effect=acquire), patch.object(
                        resources, 'quota', wraps=resources.quota) as validate:
                    with self.assertRaisesRegex(ContractError, 'ancestry raced'):
                        reader.read(rss=True)
                self.assertEqual(validate.call_count, 2)

    def test_malformed_first_and_closing_inputs_keep_validation_faults(self):
        changes = (
            ('system.slice/unit/cpu.max', '1 0', 'invalid CPU quota'),
            ('cpuset.cpus.effective', '0-65536', 'CPU set outside cap'),
            ('cgroup.controllers', 'cpu cpu', 'invalid controller declaration'),
            ('cgroup.subtree_control', 'cpu +memory', 'invalid controller declaration'),
            ('system.slice/unit/cpuset.cpus.effective', '0', 'file/controller state differs'),
        )
        for closing in (False, True):
            for relative, value, error in changes:
                with self.subTest(closing=closing, relative=relative), TemporaryDirectory() as d:
                    reader = fixtures.ResourceTests().ohio_fixture(Path(d).resolve())
                    members = reader.members
                    calls = []
                    def acquire():
                        calls.append(1)
                        result = members()
                        if len(calls) == 2:
                            (reader.mount/relative).write_text(value)
                        return result
                    if not closing:
                        (reader.mount/relative).write_text(value)
                    with patch.object(reader, 'members', side_effect=acquire), patch.object(
                            resources, 'quota', wraps=resources.quota) as validate:
                        with self.assertRaisesRegex(ContractError, error):
                            reader.read(rss=True)
                    self.assertEqual(validate.call_count, 2 if closing else 1)

    def test_changed_ancestor_order_depth_and_missing_parent_rejected(self):
        for change in ('reverse', 'omit', 'duplicate', 'over_cap'):
            with self.subTest(change=change), TemporaryDirectory() as d:
                reader = fixtures.ResourceTests().ohio_fixture(Path(d).resolve())
                members = reader.members
                calls = []
                def acquire():
                    calls.append(1)
                    result = members()
                    if len(calls) == 2:
                        if change == 'reverse': reader.ancestors.reverse()
                        if change == 'omit': reader.ancestors.pop(1)
                        if change == 'duplicate': reader.ancestors.append(reader.mount)
                        if change == 'over_cap': reader.ancestors *= 11
                    return result
                with patch.object(reader, 'members', side_effect=acquire):
                    with self.assertRaises(ContractError):
                        reader.read(rss=True)

    def test_validator_ancestry_cap_and_cpu_boundaries(self):
        for count in (1, 32, 33):
            rows = []
            for index in range(count):
                depth = count-index-1
                rows.append(dict(path='/'.join(['unit']*depth) if depth else '.',
                    cpu_max='max 100000', cpuset_effective='0,65535',
                    memory_max=None, controllers='cpuset cpu memory',
                    subtree_control='cpuset cpu memory'))
            if count <= 32:
                self.assertEqual(resources.quota(rows), 2)
            else:
                with self.assertRaisesRegex(ContractError, 'bounded CPU ancestry'):
                    resources.quota(rows)
        for malformed in ('65536', '-1', '1-0', '0,,1'):
            rows = [dict(path='.', cpu_max=None, cpuset_effective=malformed,
                controllers='cpuset', subtree_control='')]
            with self.subTest(malformed=malformed), self.assertRaises(ContractError):
                resources.quota(rows)

    def test_membership_identity_path_and_io_races_still_fail(self):
        for change, error in (('membership', 'actor membership raced'),
                              ('identity', 'actor identity raced'),
                              ('path', 'cgroup directory identity changed'),
                              ('missing', '')):
            with self.subTest(change=change), TemporaryDirectory() as d:
                reader = fixtures.ResourceTests().ohio_fixture(Path(d).resolve())
                original = resources.text
                count = 0
                def read(path):
                    nonlocal count
                    value = original(path)
                    if path == reader.proc/'10/status':
                        if change == 'membership':
                            (reader.group/'cgroup.procs').write_text('10 11')
                        if change == 'identity':
                            stat = reader.proc/'10/stat'
                            stat.write_text(stat.read_text().replace('123', '124'))
                        if change == 'missing':
                            (reader.group/'cpu.max').unlink()
                    if path == reader.group/'cgroup.subtree_control':
                        count += 1
                        if change == 'path' and count == 2:
                            moved = reader.group.with_name('old-unit')
                            reader.group.rename(moved)
                            reader.group.mkdir()
                    return value
                with patch.object(resources, 'text', side_effect=read):
                    with self.assertRaisesRegex((ContractError, FileNotFoundError), error):
                        reader.read(rss=True)


if __name__ == '__main__':
    unittest.main()
