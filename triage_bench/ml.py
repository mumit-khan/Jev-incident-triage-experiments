"""Train-only classical comparison. Evaluation labels never enter inference."""
import hashlib
import json
import time
from pathlib import Path

import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .dataset import ROOT, read_jsonl
from .policy import OPTIONS


class IncidentClassifier:
    def __init__(self, root=ROOT):
        from .runner import request_body
        root = Path(root)
        started = time.perf_counter()
        inputs = root / 'data/train.inputs.jsonl'
        labels = root / 'data/train.labels.jsonl'
        records = read_jsonl(inputs)
        keys = {row['id']: row for row in read_jsonl(labels)}
        if {r['id'] for r in records} != set(keys):
            raise ValueError('Training input and label IDs must match exactly.')
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2,
                                        max_features=20000, sublinear_tf=True)
        states = [request_body(r, 'ml')['state'] for r in records]
        features = self.vectorizer.fit_transform(states)
        self.heads = {}
        for field in OPTIONS:
            targets = [keys[r['id']]['labels'][field] for r in records]
            if set(targets) != set(OPTIONS[field]):
                raise ValueError('Training data must cover every class for ' + field)
            head = LogisticRegression(C=2.0, max_iter=2000, random_state=17,
                                      class_weight='balanced')
            head.fit(features, targets)
            self.heads[field] = head
        self.metadata = {
            'method': 'TF-IDF unigrams/bigrams + four logistic regression classifiers',
            'sklearn_version': sklearn.__version__,
            'training_records': len(records),
            'training_families': len({k['incident_family_id'] for k in keys.values()}),
            'training_inputs_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
            'training_labels_sha256': hashlib.sha256(labels.read_bytes()).hexdigest(),
            'feature_count': features.shape[1],
            'training_seconds': time.perf_counter() - started,
            'parameters': {'C': 2.0, 'class_weight': 'balanced', 'random_state': 17,
                           'max_iter': 2000, 'min_df': 2, 'max_features': 20000},
            'calibration': 'Raw fitted classifier probabilities; not calibrated for operations.',
            'comparison': 'Same exact policy and incident state string as Jev; no label, ID or family metadata.',
            'hyperparameters': 'Fixed before evaluating validation, test or challenge records.',
        }

    def predict(self, record):
        from .runner import request_body
        body = request_body(record, 'ml')
        features = self.vectorizer.transform([body['state']])
        predictions, probabilities = {}, {}
        for field, head in self.heads.items():
            dist = {str(c): float(p) for c, p in zip(head.classes_, head.predict_proba(features)[0])}
            probabilities[field] = {c: dist[c] for c in OPTIONS[field]}
            predictions[field] = max(dist, key=dist.get)
        return predictions, probabilities, hashlib.sha256(body['state'].encode()).hexdigest()
