"""Freeze the study walkthrough into a Gizmos Worker that needs no container.

Renders every response the walkthrough reads (catalog, each case, the study reader) with the same
code the local server uses, then packs them gzip-compressed into bundle.js beside gizmos-doc/worker.js.
The ML microscope and sandbox compute live, so the frozen copy points to the app for those.

Usage: uv run python scripts/build_gizmos_doc.py [output-dir]
       gizmos push --app jev-triage-experiments-doc <output-dir>
"""
import base64
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from triage_bench.explorer import Study  # noqa: E402
from triage_bench.study_page import DOCUMENTS, render_study  # noqa: E402

APP_URL = 'https://jev-triage-experiments-app.telus.gizmos.run'
WEB = ROOT / 'triage_bench' / 'web'

# Exact-match edits to the doc's copy of explorer.js; the build fails if the source changes under them.
PATCHES = {
    "const comparisonURL='/?run='": f"const comparisonURL='{APP_URL}/?run='",
}
HTML_PATCHES = {
    'Saved study + local sandbox': 'Frozen study · read-only',
}


def patched(text, patches, name):
    for old, new in patches.items():
        if text.count(old) != 1:
            raise SystemExit(f'{name}: expected exactly one "{old}" to patch; update build_gizmos_doc.py.')
        text = text.replace(old, new)
    return text


def dumps(body):
    return json.dumps(body, ensure_ascii=False, allow_nan=False)


def pack(files):
    """files: {key: text} -> base64 of gzip-compressed JSON."""
    raw = dumps(files).encode()
    return base64.b64encode(gzip.compress(raw, 9)).decode(), len(raw)


def source_state():
    def git(*args):
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = git('status', '--porcelain', '--', 'triage_bench', 'data', 'docs', 'README.md', 'HANDOFF.md')
    return {'commit': git('rev-parse', 'HEAD'), 'tracked_changes': bool(dirty)}


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'jev-triage-gizmos-doc').resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit('Output must be outside the repo; gizmos push skips gitignored files.')
    study = Study()

    core = {
        'explorer.html': patched((WEB / 'explorer.html').read_text(), HTML_PATCHES, 'explorer.html'),
        'explorer.js': patched((WEB / 'explorer.js').read_text(), PATCHES, 'explorer.js'),
        'explorer.css': (WEB / 'explorer.css').read_text(),
        'study.css': (WEB / 'study.css').read_text(),
        'study.js': (WEB / 'study.js').read_text(),
        'api/study': dumps(study.catalog()),
    }
    for doc, path in DOCUMENTS.items():
        if (ROOT / path).exists():
            core[f'study/{doc}'] = render_study(study, {'doc': doc}).decode()
            core[f'study.md/{doc}'] = (ROOT / path).read_text()

    catalog = study.catalog()
    for split, run in catalog['runs'].items():
        core[f'export/results/{split}'] = dumps(run)

    # Per case: the case itself and both Jev request exports, serialized exactly as the server does.
    groups = {'core': pack(core)}
    for split, records in study.records.items():
        cases = {}
        for identifier in records:
            case = study.case(split, identifier)
            cases[identifier] = {'case': dumps(case), 'original-request': dumps(case['requests']['jev']['body']),
                                 'focused-request': dumps(case['requests']['jev_focused']['body'])}
        groups[f'cases-{split}'] = pack(cases)
    sizes = {name: raw for name, (_, raw) in groups.items()}

    manifest = {'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'source': source_state(),
                'runs': {split: run['id'] for split, run in catalog['runs'].items()},
                'cases': {split: len(records) for split, records in study.records.items()},
                'app_url': APP_URL, 'live_only': ['ML microscope', 'sandbox', 'new comparisons']}

    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / 'gizmos-doc' / 'worker.js', out / 'worker.js')
    shutil.copy(ROOT / 'gizmos-doc' / 'wrangler.toml', out / 'wrangler.toml')
    with open(out / 'bundle.js', 'w') as f:
        f.write(f'export const MANIFEST = {dumps(manifest)};\n')
        f.write('export const GROUPS = {\n')
        for name, (data, _) in groups.items():
            f.write(f'  {json.dumps(name)}: "{data}",\n')
        f.write('};\n')
    if manifest['source']['tracked_changes']:
        print('warning: uncommitted changes in study sources; the manifest records this.', file=sys.stderr)
    print(json.dumps({'raw_mb': {k: round(v / 1e6, 2) for k, v in sizes.items()},
                      'bundle_mb': round(os.path.getsize(out / 'bundle.js') / 1e6, 2)}), file=sys.stderr)
    print(out)


if __name__ == '__main__':
    main()
