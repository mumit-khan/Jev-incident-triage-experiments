import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import study_bundle as bundle


class StudyBundleTests(unittest.TestCase):
    def test_review_rejects_credentials_without_echoing_values(self):
        for value in [{'api_key': 'sentinel-private-key'}, 'sentinel-private-key',
                      {'raw_response': {'private_trace': 'hidden'}}]:
            with self.assertRaises(ValueError) as raised:
                bundle.review(value, ['sentinel-private-key'])
            self.assertNotIn('sentinel-private-key', str(raised.exception))

    def test_archive_rejects_unexpected_and_traversal_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('../outside.json', '{}')
            with self.assertRaisesRegex(ValueError, 'unexpected paths'):
                bundle.verify(archive)

    def test_archive_detects_changed_payload_before_parsing_or_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'changed.zip'
            names = bundle.allowed_paths() | {'RESTORE.md'}
            fingerprint = hashlib.sha256(b'{}').hexdigest()
            manifest = {'schema_version': 1,
                        'dataset_sha256': json.loads((bundle.ROOT / 'data/manifest.json').read_text())['sha256'],
                        'files': {name: {'sha256': fingerprint, 'bytes': 2} for name in ['RESTORE.md', *sorted(bundle.allowed_paths())]}}
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr(bundle.MANIFEST, json.dumps(manifest))
                for name in names:
                    z.writestr(name, 'changed' if name == 'RESTORE.md' else '{}')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                bundle.verify(archive)

    def test_restore_preflights_all_conflicts_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'evidence.zip'
            names = ['runs/a.json', 'runs/b.json']
            with zipfile.ZipFile(archive, 'w') as z:
                for name in names:
                    z.writestr(name, '{}')
            existing = root / names[1]
            existing.parent.mkdir()
            existing.write_text('original evidence')
            with patch.object(bundle, 'verify', return_value={'files': dict.fromkeys(names)}), patch.object(bundle, 'allowed_paths', return_value=names):
                with self.assertRaisesRegex(ValueError, 'Existing evidence differs'):
                    bundle.restore(archive, root)
            self.assertFalse((root / names[0]).exists())
            self.assertEqual(existing.read_text(), 'original evidence')

    def test_restore_refuses_symlink_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outside').mkdir()
            (root / 'runs').symlink_to(root / 'outside', target_is_directory=True)
            archive = root / 'evidence.zip'
            names = ['runs/a.json']
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr(names[0], '{}')
            with patch.object(bundle, 'verify', return_value={'files': dict.fromkeys(names)}), patch.object(bundle, 'allowed_paths', return_value=names):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    bundle.restore(archive, root)
            self.assertFalse((root / 'outside/a.json').exists())


if __name__ == '__main__':
    unittest.main()
