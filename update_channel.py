import hashlib
import json
from pathlib import Path
import re
import sys


def validate(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'delivery.json').read_text())
    version = manifest['version']
    build = manifest['build']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise ValueError('Invalid version')
    if type(build) is not int or build < 1:
        raise ValueError('Invalid build number')
    if not re.fullmatch(r'[0-9a-f]{40}', manifest['source']):
        raise ValueError('Invalid source revision')
    expected = f'FlClash-{version}-windows-amd64.zip'
    if manifest['file'] != expected:
        raise ValueError('Unexpected package filename')
    package = directory / expected
    if not package.is_file() or package.is_symlink():
        raise ValueError('Missing package')
    if not 0 < package.stat().st_size < 100 * 1024 * 1024:
        raise ValueError('Package exceeds the delivery limit')
    with package.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if manifest['sha256'] != digest:
        raise ValueError('Package checksum mismatch')
    if (directory / 'SHA256SUMS.txt').read_text() != f'{digest}  {expected}\n':
        raise ValueError('Checksum file mismatch')
    return manifest


def prepare(filename, version, build, source):
    package = Path(filename)
    with package.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = dict(version=version, build=int(build), source=source,
                    file=package.name, sha256=digest)
    directory = package.parent
    (directory / 'delivery.json').write_text(json.dumps(manifest) + '\n')
    (directory / 'SHA256SUMS.txt').write_text(f'{digest}  {package.name}\n')
    validate(directory)


def release_key(tag):
    match = re.fullmatch(r'build-v([0-9]+)\.([0-9]+)\.([0-9]+)\+([0-9]+)', tag)
    if not match:
        raise ValueError('Invalid release tag')
    return tuple(map(int, match.groups()))


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare(*sys.argv[2:])
    elif sys.argv[1] == 'validate':
        manifest = validate(sys.argv[2])
        print(f'build-v{manifest["version"]}+{manifest["build"]}')
    elif sys.argv[1] == 'newer':
        sys.exit(0 if release_key(sys.argv[2]) > release_key(sys.argv[3]) else 1)
    else:
        raise ValueError('Unknown command')
