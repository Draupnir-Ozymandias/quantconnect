import io
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from ops import project_migration as migration


@patch.object(migration,'WHEEL_SHA',hashlib.sha256(b'fixture wheel').hexdigest())
class MigrationTests(unittest.TestCase):
    def fixture(self, directory):
        repo, package = directory/'repo', directory/'package'
        repo.mkdir()
        for root in migration.ROOTS:
            path = repo/root
            path.mkdir(parents=True)
            with (path/'evidence.json').open('x') as handle: handle.write('{"fixture":true}\n')
        (repo/'ops').mkdir()
        actual = Path(__file__).resolve().parents[1]
        for name in ('project_migration.py', 'bootstrap_migration.sh'):
            shutil.copyfile(actual/'ops'/name, repo/'ops'/name)
        with (repo/migration.WHEEL).open('xb') as handle: handle.write(b'fixture wheel')
        with (repo/'.qcrl/campaigns/.env').open('x') as handle: handle.write('EXCLUDED')
        cache = repo/'.qcrl/campaigns/__pycache__'
        cache.mkdir()
        with (cache/'cache.pyc').open('xb') as handle: handle.write(b'EXCLUDED')
        def git(repo, *args):
            if args[0] == 'bundle':
                with Path(args[2]).open('xb') as handle: handle.write(b'fixture git bundle')
            return 'a'*40 if args[0] == 'rev-parse' else ''
        with patch.object(migration, 'git', side_effect=git):
            manifest = migration.build(repo,package,repo/migration.WHEEL)
        return repo, package, manifest, git

    def test_curated_package_exact_verification_and_exclusions(self):
        with tempfile.TemporaryDirectory() as directory:
            repo,package,manifest,git = self.fixture(Path(directory).resolve())
            self.assertEqual(len(manifest['evidence']),len(migration.ROOTS))
            self.assertFalse(any('.env' in name or '__pycache__' in name for name in manifest['evidence']))
            self.assertEqual(migration.verify(package,migration.digest(package/'manifest.json')),manifest)
            with patch.object(migration,'git',side_effect=git):
                with self.assertRaises(FileExistsError): migration.build(repo,package,repo/migration.WHEEL)

    def test_tampering_wrong_anchor_and_extra_files_refused(self):
        for fault in ('anchor','tamper','extra'):
            with tempfile.TemporaryDirectory() as directory:
                _,package,_,_ = self.fixture(Path(directory).resolve())
                anchor = migration.digest(package/'manifest.json')
                if fault == 'anchor': anchor = 'b'*64
                if fault == 'tamper':
                    with (package/'README.md').open('a') as handle: handle.write('changed')
                if fault == 'extra':
                    with (package/'extra').open('x') as handle: handle.write('unexpected')
                with self.assertRaises(ValueError): migration.verify(package,anchor)

    def test_unsafe_and_duplicate_archive_members_refused_even_if_resigned(self):
        for fault in ('parent','absolute','symlink','duplicate','secret'):
            with tempfile.TemporaryDirectory() as directory:
                _,package,manifest,_ = self.fixture(Path(directory).resolve())
                # A signed manifest is not permission for unsafe extraction.
                with tarfile.open(package/'evidence.tar.gz','w:gz') as archive:
                    name = {'parent':'../escape','absolute':'/escape','secret':'.qcrl/campaigns/.env'}.get(fault,'.qcrl/campaigns/fixture')
                    member = tarfile.TarInfo(name)
                    member.size = 1
                    if fault == 'symlink': member.type = tarfile.SYMTYPE; member.linkname = '/escape'; member.size = 0
                    archive.addfile(member, io.BytesIO(b'x') if member.isfile() else None)
                    if fault == 'duplicate': archive.addfile(member,io.BytesIO(b'x'))
                manifest['files']['evidence.tar.gz'] = dict(sha256=migration.digest(package/'evidence.tar.gz'),bytes=(package/'evidence.tar.gz').stat().st_size)
                with (package/'manifest.json').open('w') as handle: json.dump(manifest,handle)
                with self.assertRaises(ValueError): migration.verify(package,migration.digest(package/'manifest.json'))

    def test_existing_destination_refused_before_verification_or_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            existing = root/'existing'
            existing.mkdir()
            with patch.object(migration,'verify') as verify, patch.object(migration.subprocess,'run') as command:
                with self.assertRaises(ValueError): migration.install(root,existing,'a'*64)
                verify.assert_not_called(); command.assert_not_called()

    def test_install_restores_bytes_receipt_and_only_offline_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _,package,manifest,git = self.fixture(root)
            destination = root/'new-checkout'
            commands = []
            def command(args, **kwargs):
                commands.append(args)
                Path(args[-1]).mkdir()
            with patch.object(migration,'git',side_effect=git), patch.object(migration.subprocess,'run',side_effect=command):
                migration.install(package,destination,migration.digest(package/'manifest.json'))
            self.assertEqual(len(commands),1)
            self.assertIn('clone',commands[0])
            self.assertEqual(commands[0][-2],str(package/'source.bundle'))
            for name, info in manifest['evidence'].items(): self.assertEqual(migration.digest(destination/name),info['sha256'])
            receipt = json.loads((destination/'.qcrl/migration-receipt.json').read_text())
            self.assertEqual(receipt['source_commit'],'a'*40)
            self.assertFalse(receipt['secrets_imported'])
            self.assertFalse(receipt['jobs_imported'])

    def test_selected_symlink_and_dirty_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            repo,_,_,_ = self.fixture(Path(directory).resolve())
            (repo/'.qcrl/campaigns/alias').symlink_to(repo/'.qcrl/campaigns/evidence.json')
            with self.assertRaises(ValueError): migration.selected(repo)
            with patch.object(migration,'git',return_value='dirty'):
                with self.assertRaises(ValueError): migration.build(repo,repo/'new-package',repo/migration.WHEEL)


if __name__ == '__main__': unittest.main()
