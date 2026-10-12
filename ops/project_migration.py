"""Private, curated source/evidence transfer. No secrets, jobs or cloud actions."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile

ROOTS = ['.qcrl/campaigns', '.qcrl/execution_truth', '.qcrl/syntheses'] + [
    '.qcrl/reviews/'+name for name in (
        'application-native-smoke-20261011-57dVZwah',
        'application-native-smoke-20261011-BUW0erCW',
        'application-cohort-20261012-cBCDc6eB',
        'counter-native-smoke-20261012-YWdUTQYU',
        'wake-native-20261012-pXnHwCVg')]
WHEEL = 'websockets-15.0.1-py3-none-any.whl'
WHEEL_SHA = 'f7a866fbc1e97b5c617ee4116daaa09b722101d4a3c170c787450ba409f9736f'
FILES = {'source.bundle', 'evidence.tar.gz', 'project_migration.py', 'bootstrap.sh', 'README.md', WHEEL}
REMOTE = 'https://github.com/Draupnir-Ozymandias/quantconnect.git'
MAX_BYTES = 2*1024**3


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''): value.update(block)
    return value.hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write('\n')


def git(repo, *args):
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args],
                          check=True, text=True, capture_output=True).stdout.strip()


def excluded(path):
    return (any(part in ('__pycache__', '.venv', 'venv', '.ssh', '.aws') for part in path.parts)
            or path.name == '.DS_Store' or path.suffix in ('.pyc', '.pyo', '.pem', '.key')
            or path.name.startswith('.env')
            or path.name.lower() in ('credentials', 'id_rsa', 'id_ed25519', 'poly.py', 'poly2.py'))


def selected(repo):
    files = {}
    for name in ROOTS:
        root = repo/name
        if not root.is_dir() or root.is_symlink() or root.resolve() != root:
            raise ValueError('required evidence root missing/aliased: '+name)
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(repo)
            if excluded(relative): continue
            if path.is_symlink(): raise ValueError('symlink refused: '+str(relative))
            if path.is_file():
                files[str(relative)] = dict(sha256=digest(path), bytes=path.stat().st_size)
    if sum(value['bytes'] for value in files.values()) > MAX_BYTES:
        raise ValueError('curated evidence exceeds two GiB')
    return files


def build(repo, output, wheel):
    repo, output = Path(repo).resolve(strict=True), Path(output).absolute()
    if git(repo, 'status', '--porcelain'): raise ValueError('commit and clean source first')
    commit = git(repo, 'rev-parse', 'HEAD')
    if not re.fullmatch('[0-9a-f]{40}', commit): raise ValueError('exact Git commit required')
    wheel = Path(wheel)
    if wheel.is_symlink() or wheel.name != WHEEL or digest(wheel) != WHEEL_SHA:
        raise ValueError('pinned public wheel differs')
    evidence = selected(repo)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    git(repo, 'bundle', 'create', str(output/'source.bundle'), 'HEAD')
    with tarfile.open(output/'evidence.tar.gz', 'x:gz') as archive:
        for name in evidence:
            info = archive.gettarinfo(str(repo/name), arcname=name)
            if not info.isfile(): raise ValueError('regular evidence required')
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mode = 0o700 if info.mode & 0o111 else 0o600
            with (repo/name).open('rb') as handle: archive.addfile(info, handle)
    for source, destination in ((repo/'ops/project_migration.py','project_migration.py'),
                                (repo/'ops/bootstrap_migration.sh','bootstrap.sh'), (wheel,WHEEL)):
        with source.open('rb') as src, (output/destination).open('xb') as dst:
            shutil.copyfileobj(src, dst)
    with (output/'README.md').open('x') as handle:
        handle.write('Private QCRL migration package\n\nSource commit: '+commit+'\n\n'
                     'Copy this whole package directory to the Intel Mac. Do not upload it publicly.\n'
                     'Use the manifest SHA-256 received separately with the bootstrap command.\n'
                     'Command: bash bootstrap.sh /absolute/path/to/python3.14 /absolute/new/project/path MANIFEST_SHA256\n'
                     'The destination must not exist. No credentials, jobs or cloud sync are imported.\n'
                     'Virtual environments are rebuilt. Older bulk reviews remain on the originating Mac.\n')
    if selected(repo) != evidence or git(repo,'rev-parse','HEAD') != commit or git(repo,'status','--porcelain'):
        raise ValueError('source/evidence changed during packaging; do not use partial package')
    included = {Path(name).name for name in ROOTS if name.startswith('.qcrl/reviews/')}
    older = sorted(path.name for path in (repo/'.qcrl/reviews').iterdir()
                   if path.is_dir() and path.name not in included)
    manifest = dict(schema_version='qcrl.project_migration.v1', source_commit=commit,
                    remote=REMOTE, python='3.14.6', websockets='15.0.1',
                    evidence_roots=ROOTS, evidence=evidence, omitted_review_directories=older,
                    files={name:dict(sha256=digest(output/name), bytes=(output/name).stat().st_size)
                           for name in sorted(FILES)},
                    secrets_imported=False, jobs_imported=False, cloud_sync_authorized=False)
    write_json(output/'manifest.json', manifest)
    verify(output, digest(output/'manifest.json'))
    return manifest


def verify(package, expected_manifest_sha256):
    package = Path(package).resolve(strict=True)
    path = package/'manifest.json'
    if (not re.fullmatch('[0-9a-f]{64}', expected_manifest_sha256)
            or path.is_symlink() or path.stat().st_size > 16*1024**2
            or digest(path) != expected_manifest_sha256):
        raise ValueError('manifest differs from external byte anchor')
    manifest = json.loads(path.read_text())
    if (manifest['schema_version'] != 'qcrl.project_migration.v1'
            or not re.fullmatch('[0-9a-f]{40}', manifest['source_commit'])
            or manifest['remote'] != REMOTE or manifest['python'] != '3.14.6'
            or manifest['websockets'] != '15.0.1' or manifest['evidence_roots'] != ROOTS
            or any(manifest[name] is not False for name in
                   ('secrets_imported','jobs_imported','cloud_sync_authorized'))
            or set(manifest['files']) != FILES
            or {p.name for p in package.iterdir()} != FILES|{'manifest.json'}):
        raise ValueError('unexpected migration contract/population')
    for name, info in manifest['files'].items():
        file = package/name
        if file.is_symlink() or not file.is_file() or file.stat().st_size != info['bytes'] or digest(file) != info['sha256']:
            raise ValueError('package file differs: '+name)
    if digest(package/WHEEL) != WHEEL_SHA: raise ValueError('public wheel hash differs')
    with tarfile.open(package/'evidence.tar.gz') as archive:
        members = archive.getmembers()
        if not 1 <= len(members) <= 20000 or sum(m.size for m in members) > MAX_BYTES:
            raise ValueError('evidence population/size exceeds cap')
        actual = {}
        for member in members:
            p = PurePosixPath(member.name)
            if (not member.isfile() or p.is_absolute() or str(p) != member.name
                    or '..' in p.parts or excluded(p) or member.name in actual
                    or not any(member.name.startswith(root+'/') for root in ROOTS)):
                raise ValueError('unsafe/duplicate evidence member')
            value = hashlib.sha256()
            with archive.extractfile(member) as handle:
                for block in iter(lambda: handle.read(1024**2), b''): value.update(block)
            actual[member.name] = dict(sha256=value.hexdigest(), bytes=member.size)
        if actual != manifest['evidence']: raise ValueError('exact evidence inventory differs')
    return manifest


def install(package, destination, expected_manifest_sha256):
    package = Path(package).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink(): raise ValueError('new destination required; never overwrite')
    if destination.resolve() != destination: raise ValueError('canonical destination required')
    manifest = verify(package, expected_manifest_sha256)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git','-c','core.hooksPath=/dev/null','clone',str(package/'source.bundle'),str(destination)],check=True)
    git(destination,'checkout','--detach',manifest['source_commit'])
    if git(destination,'rev-parse','HEAD') != manifest['source_commit']:
        raise ValueError('installed source commit differs')
    git(destination,'remote','set-url','origin',REMOTE)
    (destination/'.qcrl').mkdir(mode=0o700, exist_ok=False)
    with tarfile.open(package/'evidence.tar.gz') as archive:
        seen = set()
        for member in archive.getmembers():
            if (not member.isfile() or member.name not in manifest['evidence']
                    or member.name in seen
                    or member.size != manifest['evidence'][member.name]['bytes']):
                raise ValueError('evidence changed after verification')
            seen.add(member.name)
            path = destination/member.name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with archive.extractfile(member) as src, path.open('xb') as dst:
                shutil.copyfileobj(src,dst)
            path.chmod(0o700 if member.mode & 0o111 else 0o600)
            if digest(path) != manifest['evidence'][member.name]['sha256']:
                raise ValueError('installed evidence differs')
        if seen != set(manifest['evidence']): raise ValueError('installed evidence population differs')
    verify(package, expected_manifest_sha256)
    write_json(destination/'.qcrl/migration-receipt.json', dict(source_commit=manifest['source_commit'],
        manifest_sha256=expected_manifest_sha256, evidence_files=len(manifest['evidence']),
        secrets_imported=False, jobs_imported=False, cloud_sync_authorized=False))
    if git(destination,'status','--porcelain'): raise ValueError('installed Git tree not clean')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build_parser = commands.add_parser('build')
    build_parser.add_argument('--repo', required=True, type=Path)
    build_parser.add_argument('--output', required=True, type=Path)
    build_parser.add_argument('--wheel', required=True, type=Path)
    for command in ('verify','install'):
        sub = commands.add_parser(command)
        sub.add_argument('--package', required=True, type=Path)
        sub.add_argument('--expected-manifest-sha256', required=True)
        if command == 'install': sub.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'build':
        value = build(args.repo,args.output,args.wheel)
        print(json.dumps(dict(source_commit=value['source_commit'], evidence_files=len(value['evidence']),
                              manifest_sha256=digest(args.output/'manifest.json'))))
    elif args.command == 'verify':
        verify(args.package,args.expected_manifest_sha256)
        print('Exact package/source/evidence inventory verified.')
    else:
        install(args.package,args.destination,args.expected_manifest_sha256)
        print('Source/evidence installed; no credentials or jobs imported.')


if __name__ == '__main__': main()
