"""Package, verify and restore the four recorded synthetic study runs; no inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNS = {'initial_validation': '718d977d25aa4634', 'validation': 'c3519f8c7ec84814',
        'test': '3739acf583a64c79', 'challenge': '908dac657e6740af'}
PROVIDERS = ['baseline', 'ml', 'ml_structured', 'jev', 'jev_focused']
MANIFEST = 'bundle-manifest.json'
FORBIDDEN_KEYS = {'api_key', 'authorization', 'access_token', 'refresh_token', 'password', 'secret', 'headers'}
SECRET_PATTERN = re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9_.-]{10,}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def allowed_paths():
    paths = {'runs/performance-freeze.json'}
    for name, identifier in RUNS.items():
        prefix = f'runs/app/{identifier}/'
        paths.update(prefix + f for f in ['job.json', 'inputs.jsonl', 'labels.jsonl'])
        providers = ['baseline', 'ml', 'jev'] if name == 'initial_validation' else PROVIDERS
        for provider in providers:
            paths.update(prefix + provider + suffix for suffix in ['.jsonl', '.meta.json', '.metrics.json'])
    return paths


def local_secrets(root):
    values = [os.environ.get('TYPESAFE_API_KEY', '')]
    env = root / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                if any(word in key.upper() for word in ['KEY', 'TOKEN', 'SECRET', 'PASSWORD']):
                    values.append(value.strip().strip('\"\''))
    return [value for value in values if len(value) >= 8]


def review(value, secrets):
    if isinstance(value, dict):
        if any(str(k).lower() in FORBIDDEN_KEYS for k in value):
            raise ValueError('Credential or request-header field in selected evidence.')
        if 'raw_response' in value and not set(value['raw_response']).issubset({'model', 'answers', 'usage'}):
            raise ValueError('Unreviewed provider response field in selected evidence.')
        for child in value.values():
            review(child, secrets)
    elif isinstance(value, list):
        for child in value:
            review(child, secrets)
    elif isinstance(value, str):
        if SECRET_PATTERN.search(value) or any(secret in value for secret in secrets):
            raise ValueError('Potential credential in selected evidence; value suppressed.')
        if '/Users/' in value or '/home/' in value:
            raise ValueError('Personal filesystem path in selected evidence.')
        if ''.join(map(chr, [84, 69, 76, 85, 83])).lower() in value.lower():
            raise ValueError('Excluded operator identity in selected evidence.')


def portable(value, root):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            if key == 'input_file' and isinstance(child, str) and Path(child).is_absolute():
                child = Path(child).relative_to(root).as_posix()
            result[key] = portable(child, root)
        return result
    if isinstance(value, list):
        return [portable(child, root) for child in value]
    return value


def verify(archive, root=ROOT):
    """Check archive contents and fingerprints before writing any restored evidence."""
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != allowed_paths() | {MANIFEST, 'RESTORE.md'}:
            raise ValueError('Bundle contains duplicate, missing or unexpected paths.')
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe archive path.')
        manifest = json.loads(z.read(MANIFEST))
        if manifest.get('schema_version') != 1 or set(manifest['files']) != allowed_paths() | {'RESTORE.md'}:
            raise ValueError('Unsupported or incomplete bundle manifest.')
        review(manifest, [])
        secrets = local_secrets(root)
        dataset = json.loads((root / 'data/manifest.json').read_text())
        if manifest['dataset_sha256'] != dataset['sha256']:
            raise ValueError('Bundle dataset manifest differs from the source checkout.')
        if sum(info.file_size for info in z.infolist()) > 64 * 1024 * 1024:
            raise ValueError('Study bundle exceeds the expected size limit.')
        for name, expected in manifest['files'].items():
            data = z.read(name)
            if sha(data) != expected['sha256'] or len(data) != expected['bytes']:
                raise ValueError(f'Bundle checksum mismatch: {name}')
            rows = ([data.decode()] if name.endswith('.md') else
                    [json.loads(line) for line in data.decode().splitlines()] if name.endswith('.jsonl') else [json.loads(data)])
            for row in rows:
                review(row, secrets)
        for name, expected in manifest['dataset_sha256'].items():
            if sha((root / 'data' / name).read_bytes()) != expected:
                raise ValueError(f'Dataset mismatch: {name}; use the release source checkout.')
        freeze = json.loads(z.read('runs/performance-freeze.json'))
        for name, expected in freeze['files'].items():
            if name not in {'triage_bench/experiments.py', 'triage_bench/ml.py', 'triage_bench/runner.py', 'triage_bench/policy.py'} or sha((root / name).read_bytes()) != expected:
                raise ValueError(f'Frozen inference source mismatch: {name}')
        for split, identifier in RUNS.items():
            prefix = f'runs/app/{identifier}/'
            job = json.loads(z.read(prefix + 'job.json'))
            if job['id'] != identifier or job['split'] != ('validation' if split == 'initial_validation' else split):
                raise ValueError('Run identity or input mismatch.')
            input_hash = sha(z.read(prefix + 'inputs.jsonl'))
            data_split = 'validation' if split == 'initial_validation' else split
            if input_hash != manifest['dataset_sha256'][data_split + '.inputs.jsonl']:
                raise ValueError('Run input hash does not match the frozen split.')
            if sha(z.read(prefix + 'labels.jsonl')) != manifest['dataset_sha256'][data_split + '.labels.jsonl']:
                raise ValueError('Run labels do not match the frozen split.')
            for provider, result in job['results'].items():
                saved = [json.loads(line) for line in z.read(prefix + provider + '.jsonl').decode().splitlines()]
                if [{k: v for k, v in row.items() if k != 'raw_response'} for row in saved] != result['predictions'] or result['metadata']['input_sha256'] != input_hash:
                    raise ValueError('Run predictions or input fingerprints disagree.')
                if result['metrics'] != json.loads(z.read(prefix + provider + '.metrics.json')) or result['metadata'] != json.loads(z.read(prefix + provider + '.meta.json')):
                    raise ValueError('Run scores or metadata disagree.')
    return manifest


def create(archive, root=ROOT):
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
        raise ValueError('Commit the handoff and bundle tooling before building a release asset.')
    payload = {}
    secrets = local_secrets(root)
    for name in sorted(allowed_paths()):
        original = (root / name).read_bytes()
        if name.endswith('.jsonl'):
            rows = [json.loads(line) for line in original.decode().splitlines()]
            for row in rows:
                review(row, secrets)
            data = original
        else:
            value = portable(json.loads(original), root)
            review(value, secrets)
            data = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
        payload[name] = data
    guide = (root / 'docs/run-bundle.md').read_text()
    for name in ['README.md', 'HANDOFF.md']:
        guide = guide.replace('(../' + name, f'(https://github.com/mumit/Jev-incident-triage-experiments/blob/{commit}/' + name)
    payload['RESTORE.md'] = guide.encode()
    review(payload['RESTORE.md'].decode(), secrets)
    dataset = json.loads((root / 'data/manifest.json').read_text())
    manifest = {'schema_version': 1, 'bundle_version': 'study-evidence-v1',
                'source_commit': commit, 'inference_checkpoint': '6a44f62',
                'jev_checkpoint': 'jev-1.13.0', 'synthetic': True,
                'operator': 'Northstar Telecom', 'runs': RUNS,
                'dataset_sha256': dataset['sha256'],
                'transformations': ['input_file metadata paths rewritten relative to the repository',
                                    'JSON metadata formatting normalized; prediction rows and responses unchanged',
                                    'Restoration guide links point to the matching source commit'],
                'review': 'Selected study files only; credential fields, known local secrets, token patterns, personal paths and excluded operator identities checked.',
                'files': {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in payload.items()}}
    review(manifest, secrets)
    payload[MANIFEST] = (json.dumps(manifest, indent=2) + '\n').encode()
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise ValueError('Output archive exists; choose a new version or destination.')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    verify(archive, root)
    checksum = archive.with_suffix(archive.suffix + '.sha256')
    checksum.write_text(f'{sha(archive.read_bytes())}  {archive.name}\n')
    print(f'Created {archive.name}: {len(payload) - 1} evidence files, {archive.stat().st_size:,} bytes; review and verification passed.')


def restore(archive, root=ROOT):
    manifest = verify(archive, root)
    with zipfile.ZipFile(archive) as z:
        # Inspect all destinations before writing. Existing matching evidence is retained.
        for name in allowed_paths():
            target = root / name
            if any((root.joinpath(*Path(name).parts[:i])).is_symlink() for i in range(1, len(Path(name).parts) + 1)):
                raise ValueError('Restore destination contains a symlink.')
            if target.exists() and target.read_bytes() != z.read(name):
                raise ValueError(f'Existing evidence differs: {name}; restore in a fresh checkout.')
        for name in allowed_paths():
            target = root / name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(z.read(name))
    print('Restored four study runs and the freeze record; no existing evidence overwritten. Restart the app to load them.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['create', 'verify', 'restore'])
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    if args.action == 'create':
        create(args.archive)
    elif args.action == 'restore':
        restore(args.archive)
    else:
        manifest = verify(args.archive)
        print(f"Verified {len(manifest['files'])} evidence files against the dataset and frozen source.")


if __name__ == '__main__':
    main()
