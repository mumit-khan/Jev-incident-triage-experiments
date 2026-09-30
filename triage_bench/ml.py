"""Train-only classical comparison. Evaluation labels never enter inference."""
import hashlib
import json
import time
from pathlib import Path

import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import hstack

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


class StructuredIncidentClassifier:
    """Same compact evidence as focused Jev; learn impact separately from prose."""
    def __init__(self, root=ROOT):
        from .runner import request_body
        from .experiments import structured_features
        root = Path(root)
        started = time.perf_counter()
        inputs, labels = root / 'data/train.inputs.jsonl', root / 'data/train.labels.jsonl'
        records = read_jsonl(inputs)
        keys = {r['id']: r for r in read_jsonl(labels)}
        if set(keys) != {r['id'] for r in records}:
            raise ValueError('Training IDs must match.')
        self.words = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        self.chars = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, sublinear_tf=True)
        self.impact = DictVectorizer()
        states = [request_body(r, 'ml', 'focused')['state'] for r in records]
        words = self.words.fit_transform(states)
        chars = self.chars.fit_transform(states)
        structured = self.impact.fit_transform([structured_features(r['input']) for r in records])
        semantic = hstack([words, chars, structured], format='csr')
        self.heads = {}
        for field in OPTIONS:
            head = LogisticRegression(C=2.0, max_iter=2000, random_state=17, class_weight='balanced')
            targets = [keys[r['id']]['labels'][field] for r in records]
            if set(targets) != set(OPTIONS[field]):
                raise ValueError('Missing training class: ' + field)
            head.fit(structured if field == 'priority' else semantic, targets)
            self.heads[field] = head
        self.metadata = {
            'method': 'Compact evidence, word/character TF-IDF and structured impact; priority is a learned impact-only logistic classifier',
            'training_records': len(records), 'training_families': len({k['incident_family_id'] for k in keys.values()}),
            'training_inputs_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
            'training_labels_sha256': hashlib.sha256(labels.read_bytes()).hexdigest(),
            'sklearn_version': sklearn.__version__, 'training_seconds': time.perf_counter() - started,
            'parameters': {'C': 2.0, 'class_weight': 'balanced', 'word_ngrams': [1, 2], 'character_ngrams': [3, 5]},
            'comparison': 'Same compact state as focused Jev; structured impact is already present in that state.',
            'calibration': 'Uncalibrated fitted probabilities.',
            'selection': 'Representation proposed after original validation failure review; fitted only on original training data.'}

    def predict(self, record):
        from .runner import request_body
        from .experiments import structured_features
        body = request_body(record, 'ml', 'focused')
        structured = self.impact.transform([structured_features(record['input'])])
        semantic = hstack([self.words.transform([body['state']]), self.chars.transform([body['state']]), structured], format='csr')
        predictions, probabilities = {}, {}
        for field, head in self.heads.items():
            features = structured if field == 'priority' else semantic
            dist = {str(c): float(p) for c, p in zip(head.classes_, head.predict_proba(features)[0])}
            probabilities[field] = dist
            predictions[field] = max(dist, key=dist.get)
        return predictions, probabilities, hashlib.sha256(body['state'].encode()).hexdigest()
