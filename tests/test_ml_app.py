import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from triage_bench.app import App
from triage_bench.dataset import ROOT, read_jsonl
from triage_bench.ml import IncidentClassifier
from triage_bench.runner import request_body


class MLAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read_paths = []
        original = Path.read_text
        def track(path, *args, **kwargs):
            if path.suffix == '.jsonl':
                read_paths.append(str(path))
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', track):
            cls.model = IncidentClassifier()
        cls.read_paths = read_paths
        cls.record = read_jsonl(ROOT / 'data/validation.inputs.jsonl')[0]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / 'data').symlink_to(ROOT / 'data', target_is_directory=True)
        self.app = App(root)
        self.app.ml_model = self.model

    def tearDown(self):
        self.temp.cleanup()

    def test_fit_reads_training_only(self):
        self.assertEqual({Path(p).name for p in self.read_paths},
                         {'train.inputs.jsonl', 'train.labels.jsonl'})
        self.assertEqual(self.model.metadata['training_records'], 600)
        self.assertEqual(self.model.metadata['training_families'], 30)

    def test_inference_ignores_poisoned_answer_metadata(self):
        poisoned = copy.deepcopy(self.record)
        poisoned['labels'] = {'initial_owner': 'LABEL_LEAK_SENTINEL'}
        poisoned['incident_family_id'] = 'FAMILY_LEAK_SENTINEL'
        poisoned['id'] = 'RECORD_ID_SENTINEL'
        self.assertEqual(self.model.predict(self.record), self.model.predict(poisoned))
        self.assertNotIn('SENTINEL', request_body(poisoned, 'jev')['state'])

    def test_learning_examples_have_unique_families_and_no_labels_in_request(self):
        rows = self.app.incidents('learning')
        self.assertEqual(len(rows), 11)
        self.assertEqual(len({r['family'] for r in rows}), 11)
        for row in rows:
            self.assertEqual(set(row['request']), {'model', 'state', 'questions'})
            self.assertEqual(row['request']['state'], request_body({'input': row['input']}, 'ml')['state'])
            self.assertNotIn('accepted_answers', row['request']['state'])

    def test_local_batch_makes_no_network_calls_and_has_real_probabilities(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('Unexpected network call')):
            job = self.app.start({'split': 'learning', 'providers': ['ml', 'baseline'], 'count': 11})
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                job = self.app.snapshot(job['id'])
                if job['status'] not in {'queued', 'running'}:
                    break
                time.sleep(.02)
        self.assertEqual(job['status'], 'completed')
        self.assertEqual(job['completed'], 22)
        result = job['results']['ml']
        self.assertEqual(result['metrics']['records'], 11)
        self.assertEqual(result['metrics']['failed_records'], 0)
        self.assertIn('training_inputs_sha256', result['metadata']['training'])
        for row in result['predictions']:
            self.assertEqual(row['status'], 'ok')
            self.assertNotIn('provider_confidence', row)
            for dist in row['probabilities'].values():
                self.assertAlmostEqual(sum(dist.values()), 1.0)

    def test_jev_key_is_not_returned_or_saved_in_config(self):
        cfg = self.app.config()['jev']
        self.app.configure({'provider': 'jev', **cfg, 'api_key': 'test-only-secret'})
        self.assertNotIn('test-only-secret', json.dumps(self.app.config()))
        self.app.configure({'provider': 'jev', **cfg, 'clear_key': True})
        self.assertFalse(self.app.config()['jev']['key_configured'])

    def test_missing_key_prevents_jev_job(self):
        self.app.profiles['jev']['api_key'] = ''
        with self.assertRaisesRegex(ValueError, 'API key'):
            self.app.start({'split': 'learning', 'providers': ['jev', 'ml'], 'count': 1})
        self.assertEqual(self.app.jobs, {})

    def test_challenge_selection_keeps_pairs_complete(self):
        with self.assertRaisesRegex(ValueError, 'even'):
            self.app.start({'split': 'challenge', 'providers': ['ml'], 'count': 3})


if __name__ == '__main__':
    unittest.main()
