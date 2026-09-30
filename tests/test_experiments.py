import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from triage_bench.app import App
from triage_bench.dataset import ROOT, read_jsonl, write_jsonl
from triage_bench.evaluate import evaluate
from triage_bench.ml import StructuredIncidentClassifier
from triage_bench.policy import OPTIONS
from triage_bench.runner import normalize, request_body


class ExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = []
        original = Path.read_text
        def track(path, *args, **kwargs):
            if path.suffix == '.jsonl':
                paths.append(path.name)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', track):
            cls.model = StructuredIncidentClassifier()
        cls.paths = paths
        cls.record = read_jsonl(ROOT / 'data/validation.inputs.jsonl')[0]

    def test_revised_fit_reads_only_training_and_inference_ignores_metadata(self):
        self.assertEqual(set(self.paths), {'train.inputs.jsonl', 'train.labels.jsonl'})
        poisoned = {**copy.deepcopy(self.record), 'id': 'ID_SENTINEL',
                    'labels': {'initial_owner': 'ANSWER_SENTINEL'}, 'incident_family_id': 'FAMILY_SENTINEL'}
        self.assertEqual(self.model.predict(self.record), self.model.predict(poisoned))
        state = request_body(poisoned, 'jev', 'focused')['state']
        self.assertNotIn('SENTINEL', state)
        self.assertEqual(self.model.predict(poisoned)[2], hashlib.sha256(state.encode()).hexdigest())

    def test_learned_priority_follows_impact_when_prose_does_not_change(self):
        for status, count, expected in [('outage', 9, 'P2'), ('outage', 10, 'P1'),
                                        ('degraded', 9, 'P3'), ('degraded', 10, 'P2'), ('none', 0, 'P4')]:
            record = copy.deepcopy(self.record)
            record['input']['service_impact'].update(status=status, affected_sites=count)
            self.assertEqual(self.model.predict(record)[0]['priority'], expected)

    def test_rounding_adjustment_is_bounded_and_does_not_change_choice(self):
        response = {'answers': {f: {'choice': next(iter(choices)),
                    'probabilities': {c: int(c == next(iter(choices))) for c in choices}}
                    for f, choices in OPTIONS.items()}}
        dist = response['answers']['next_check']['probabilities']
        response['answers']['next_check']['choice'] = 'inspect_radio'
        dist.update(inspect_radio=.81, inspect_transport=.09, inspect_power=.03, inspect_core=.02,
                    verify_change=.02, gather_evidence=.02, monitor=0)
        pred, probs, _ = normalize(response)
        self.assertEqual(pred['next_check'], 'inspect_radio')
        self.assertAlmostEqual(sum(probs['next_check'].values()), 1)
        self.assertAlmostEqual(probs['next_check']['inspect_radio'], .81/.99)
        dist['inspect_radio'] = .5
        with self.assertRaisesRegex(ValueError, 'sum to one'):
            normalize(response)
        dist['inspect_radio'] = .819
        with self.assertRaisesRegex(ValueError, 'sum to one'):
            normalize(response)

    def test_software_priority_score_is_separate_and_failure_inclusive(self):
        keys = read_jsonl(ROOT / 'data/validation.labels.jsonl')[:2]
        records = read_jsonl(ROOT / 'data/validation.inputs.jsonl')[:2]
        predictions = copy.deepcopy(keys[0]['labels'])
        predictions['priority'] = 'P4' if predictions['priority'] != 'P4' else 'P1'
        rows = [{'id': keys[0]['id'], 'status': 'ok', 'predictions': predictions},
                {'id': keys[1]['id'], 'status': 'error'}]
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for filename, data in [('keys', keys), ('inputs', records), ('predictions', rows)]:
                write_jsonl(root / filename, data)
            metrics = evaluate(root/'keys', root/'predictions', inputs_path=root/'inputs')
            self.assertEqual(metrics['all_fields_accuracy'], 0)
            self.assertEqual(metrics['with_software_priority_accuracy'], .5)
            self.assertEqual(read_jsonl(root/'predictions'), rows)

    def test_focused_config_shares_key_without_exporting_it(self):
        with tempfile.TemporaryDirectory() as name:
            app = App(name)
            config = app.config()['jev']
            app.configure({'provider': 'jev', **config, 'api_key': 'test-secret'})
            self.assertTrue(app.config()['jev_focused']['key_configured'])
            self.assertNotIn('api_key', app.config()['jev_focused'])
            app.configure({'provider': 'jev', **config, 'clear_key': True})
            self.assertFalse(app.config()['jev_focused']['key_configured'])


if __name__ == '__main__':
    unittest.main()
