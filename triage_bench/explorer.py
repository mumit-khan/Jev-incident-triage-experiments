"""Read-only study explorer plus an isolated, local-only evidence sandbox."""
import copy
import hashlib
import json
import math
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
from scipy.sparse import hstack

from .dataset import ROOT, read_jsonl
from .experiments import compact_packet, structured_features
from .ml import IncidentClassifier, StructuredIncidentClassifier
from .policy import OPTIONS, TEXT, VERSION, priority
from .runner import baseline, request_body

RUNS = {'validation': 'c3519f8c7ec84814', 'test': '3739acf583a64c79',
        'challenge': '908dac657e6740af'}
INITIAL = '718d977d25aa4634'
PROVIDERS = ['baseline', 'ml', 'ml_structured', 'jev', 'jev_focused']
FIELDS = list(OPTIONS)
NAMES = {'baseline': 'Rules', 'ml': 'ML · original', 'ml_structured': 'ML · revised',
         'jev': 'Jev · original', 'jev_focused': 'Jev · focused'}


def sha(value):
    return hashlib.sha256(value).hexdigest()


def trace_rules(packet):
    """Explain the existing keyword reference without changing its decisions."""
    text = ' '.join(o['detail'] for o in packet['observations']).lower()
    impact = packet['service_impact']
    none = impact['status'] == 'none'
    uncertain_words = [w for w in ['75 minutes old', 'cannot yet', 'timing alone', 'do not establish'] if w in text]
    uncertain = impact['status'] == 'unknown' or bool(uncertain_words)
    steps = [{'name': 'No current impact', 'condition': 'service_impact.status = none',
              'matched': none, 'reached': True, 'evidence': impact['status']},
             {'name': 'Unknown or uncertain evidence', 'condition': 'Unknown impact or one of four uncertainty phrases',
              'matched': uncertain, 'reached': not none, 'evidence': uncertain_words or [impact['status']]}]
    reached = not none and not uncertain
    for domain, words in [('power', ['battery', 'batteries', 'rectifier', 'breaker', 'dc ', 'generator', 'transfer switch']),
                          ('core', ['core', 'authentication', 'resolver', 'session service', 'mobility service', 'user-plane', 'policy-control']),
                          ('transport', ['aggregation', 'optical', 'crc', 'backhaul', 'non-fragmenting']),
                          ('ran', ['radio', 'antenna', 'handover', 'uplink interference', 'mobility failures', 'receive sensitivity'])]:
        hits = [w for w in words if w in text]
        steps.append({'name': domain, 'condition': 'First matching keyword group wins',
                      'matched': bool(hits), 'reached': reached, 'evidence': hits,
                      'keywords': words})
        if reached and hits:
            reached = False
    return {'steps': steps, 'predictions': baseline(packet),
            'priority': {'status': impact['status'], 'affected_sites': impact['affected_sites'],
                         'result': priority(impact)},
            'limitation': 'These rules match words in observation text. They do not resolve negation, measurement age or graph dependencies.'}


class Study:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.records, self.keys = {}, {}
        for split in ['train', 'validation', 'test', 'challenge']:
            self.records[split] = {r['id']: r for r in read_jsonl(self.root / f'data/{split}.inputs.jsonl')}
            self.keys[split] = {r['id']: r for r in read_jsonl(self.root / f'data/{split}.labels.jsonl')}
        self.jobs, self.rows = {}, {}
        for name, identifier in {**RUNS, 'initial': INITIAL}.items():
            directory = self.root / 'runs/app' / identifier
            if not (directory / 'job.json').exists():
                continue
            self.jobs[name] = json.loads((directory / 'job.json').read_text())
            self.rows[name] = {}
            for provider in self.jobs[name]['results']:
                path = directory / f'{provider}.jsonl'
                self.rows[name][provider] = {r['id']: r for r in read_jsonl(path)} if path.exists() else {}
        freeze_path = self.root / 'runs/performance-freeze.json'
        self.freeze = json.loads(freeze_path.read_text()) if freeze_path.exists() else {}
        self.source_matches = {p: (self.root / p).exists() and sha((self.root / p).read_bytes()) == h
                               for p, h in self.freeze.get('files', {}).items()}
        self.models = {}
        self.model_lock = threading.Lock()

    def model(self, variant):
        if variant not in {'ml', 'ml_structured'}:
            raise ValueError('Choose an ML variant.')
        with self.model_lock:
            if variant not in self.models:
                self.models[variant] = (IncidentClassifier if variant == 'ml' else StructuredIncidentClassifier)(self.root)
        return self.models[variant]

    def record(self, split, identifier):
        if split not in self.records or identifier not in self.records[split]:
            raise ValueError('Unknown case or split.')
        return self.records[split][identifier]

    def catalog(self):
        splits = {}
        for split, records in self.records.items():
            families = defaultdict(list)
            for identifier, record in records.items():
                key = self.keys[split][identifier]
                outcomes = {}
                for provider in PROVIDERS:
                    row = self.rows.get(split, {}).get(provider, {}).get(identifier)
                    outcomes[provider] = None if row is None else {
                        'correct': row.get('status') == 'ok' and all(row.get('predictions', {}).get(f) in key['accepted_answers'][f] for f in FIELDS),
                        'wrong_fields': [f for f in FIELDS if row.get('status') != 'ok' or row.get('predictions', {}).get(f) not in key['accepted_answers'][f]],
                        'high_probability_wrong': any(row.get('probabilities', {}).get(f, {}).get(row.get('predictions', {}).get(f), 0) >= .8
                                                      and row.get('predictions', {}).get(f) not in key['accepted_answers'][f] for f in FIELDS)}
                families[key['incident_family_id']].append({'id': identifier, 'impact': record['input']['service_impact'],
                                                           'outcomes': outcomes, 'pair_id': key.get('pair_id'),
                                                           'changed_path': key.get('changed_path')})
            if split == 'challenge':
                for cases in families.values():
                    cases.sort(key=lambda c: (c['pair_id'], c['id'].endswith('-b')))
            splits[split] = {'records': len(records), 'families': [{'name': name, 'cases': cases} for name, cases in families.items()]}
        summaries = {}
        for split, job in self.jobs.items():
            summaries[split] = {'id': job['id'], 'split': job['split'], 'count': job['count'],
                                'created_at': job['created_at'], 'providers': {}}
            for provider, result in job['results'].items():
                if 'metrics' not in result:
                    continue
                meta = result['metadata']
                summaries[split]['providers'][provider] = {
                    'metrics': result['metrics'],
                    'metadata': {k: meta[k] for k in ['requested_model', 'input_sha256', 'policy_sha256', 'questions_sha256',
                                                       'request_variant', 'training', 'successful_records', 'failed_records'] if k in meta}}
        return {'splits': splits, 'runs': summaries, 'providers': NAMES, 'fields': OPTIONS,
                'policy': TEXT, 'policy_version': VERSION,
                'freeze': {'selection': self.freeze.get('selection'), 'previous_exposure': self.freeze.get('previous_exposure'),
                           'source_matches': self.source_matches},
                'learning_ids': [v['cases'][0]['id'] for v in splits['validation']['families']],
                'report_available': (self.root / 'docs/experiment-overview.md').exists()}

    def case(self, split, identifier):
        record = self.record(split, identifier)
        key = self.keys[split][identifier]
        rows = {}
        for provider, indexed in self.rows.get(split, {}).items():
            if identifier not in indexed:
                continue
            row = indexed[identifier]
            safe = {k: row[k] for k in ['status', 'predictions', 'probabilities', 'provider_confidence', 'distribution_sums',
                                      'probability_adjustments', 'resolved_model', 'usage', 'latency_ms', 'state_sha256', 'request_sha256'] if k in row}
            raw = row.get('raw_response', {})
            # Provider payloads are untrusted. Export only the response schema, never arbitrary headers or extra keys.
            if raw:
                safe['raw_response'] = {'model': raw.get('model'), 'answers': {
                    f: {k: a[k] for k in ['type', 'choice', 'confidence', 'probabilities'] if k in a}
                    for f, a in raw.get('answers', {}).items() if f in OPTIONS and isinstance(a, dict)}}
            rows[provider] = safe
        requests = {}
        for provider in ['jev', 'jev_focused']:
            meta = self.jobs.get(split, {}).get('results', {}).get(provider, {}).get('metadata', {})
            body = request_body(record, meta.get('requested_model') or 'jev-1.13.0',
                                'focused' if provider == 'jev_focused' else 'original')
            saved = rows.get(provider, {})
            requests[provider] = {'body': body, 'utf8_bytes': len(json.dumps(body, ensure_ascii=False).encode()),
                                  'state_sha256': sha(body['state'].encode()),
                                  'matches_saved_state': saved.get('state_sha256') == sha(body['state'].encode()) if 'state_sha256' in saved else None,
                                  'matches_saved_request': saved.get('request_sha256') == sha(json.dumps(body, ensure_ascii=False).encode()) if 'request_sha256' in saved else None}
        partner = next((k['id'] for k in self.keys[split].values() if key.get('pair_id') and
                        k.get('pair_id') == key['pair_id'] and k['id'] != identifier), None)
        paired = None if partner is None else {
            'id': partner, 'input': self.records[split][partner]['input'],
            'reference': self.keys[split][partner],
            'predictions': {p: {k: r[k] for k in ['status','predictions','probabilities'] if k in r}
                            for p, index in self.rows.get(split, {}).items() if (r := index.get(partner))}}
        return {'id': identifier, 'split': split, 'input': record['input'], 'reference': key,
                'predictions': rows, 'requests': requests, 'compact': compact_packet(record['input']),
                'rules': trace_rules(record['input']), 'partner': partner, 'paired': paired,
                'initial_predictions': {p: {k: row[k] for k in ['status', 'predictions', 'probabilities'] if k in row}
                                        for p, index in self.rows.get('initial', {}).items() if (row := index.get(identifier))}}

    def features(self, model, record, variant, field):
        body = request_body(record, 'ml', 'focused' if variant == 'ml_structured' else 'original')
        if variant == 'ml':
            return model.vectorizer.transform([body['state']]), ['word:' + n for n in model.vectorizer.get_feature_names_out()]
        impact = model.impact.transform([structured_features(record['input'])])
        impact_names = ['impact:' + n for n in model.impact.get_feature_names_out()]
        if field == 'priority':
            return impact, impact_names
        vector = hstack([model.words.transform([body['state']]), model.chars.transform([body['state']]), impact], format='csr')
        return vector, (['word:' + n for n in model.words.get_feature_names_out()] +
                        ['character:' + n for n in model.chars.get_feature_names_out()] + impact_names)

    def microscope(self, split, identifier, variant, field, alternative=None):
        if field not in OPTIONS:
            raise ValueError('Unknown decision field.')
        record = self.record(split, identifier)
        model = self.model(variant)
        head = model.heads[field]
        vector, names = self.features(model, record, variant, field)
        probs = head.predict_proba(vector)[0]
        chosen_index = int(np.argmax(probs))
        chosen = str(head.classes_[chosen_index])
        if alternative is not None and alternative not in head.classes_:
            raise ValueError('Unknown comparison class.')
        other_index = (int(np.where(head.classes_ == alternative)[0][0]) if alternative and alternative != chosen
                       else sorted(range(len(probs)), key=lambda i: probs[i], reverse=True)[1])
        if len(head.classes_) == 2:
            sign = 1 if chosen_index == 1 else -1
            coefficients = sign * head.coef_[0]
            intercept = float(sign * head.intercept_[0])
        else:
            coefficients = head.coef_[chosen_index] - head.coef_[other_index]
            intercept = float(head.intercept_[chosen_index] - head.intercept_[other_index])
        contributions = [{'feature': str(names[i]), 'value': float(v), 'weight_difference': float(coefficients[i]),
                          'contribution': float(v * coefficients[i])} for i, v in zip(vector.indices, vector.data)]
        contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)
        margin = intercept + sum(c['contribution'] for c in contributions)
        expected = float(math.log(probs[chosen_index] / probs[other_index]))
        groups = defaultdict(float)
        for c in contributions:
            groups[c['feature'].split(':')[0]] += c['contribution']
        predictions, all_probabilities, state_sha = model.predict(record)
        saved = self.rows.get(split, {}).get(variant, {}).get(identifier, {})
        stored_training = self.jobs.get(split, {}).get('results', {}).get(variant, {}).get('metadata', {}).get('training', {})
        training_matches = all(stored_training.get(k) == model.metadata.get(k) for k in
                               ['training_inputs_sha256', 'training_labels_sha256', 'sklearn_version', 'parameters']) if stored_training else None
        delta = max(abs(all_probabilities[f][c] - saved.get('probabilities', {}).get(f, {}).get(c, -1))
                    for f in FIELDS for c in OPTIONS[f]) if saved.get('status') == 'ok' else None
        vectorizer = model.vectorizer if variant == 'ml' else model.words
        training = list(self.records['train'].values())
        states = [request_body(r, 'ml', 'focused' if variant == 'ml_structured' else 'original')['state'] for r in training]
        similarity = (vectorizer.transform(states) @ vectorizer.transform([request_body(record, 'ml', 'focused' if variant == 'ml_structured' else 'original')['state']]).T).toarray().ravel()
        nearest = [{'id': training[i]['id'], 'family': self.keys['train'][training[i]['id']]['incident_family_id'],
                    'similarity': float(similarity[i]), 'observation': training[i]['input']['observations'][0]['detail'],
                    'reference': self.keys['train'][training[i]['id']]['labels']}
                   for i in np.argsort(-similarity)[:5]]
        return {'variant': variant, 'field': field, 'chosen': chosen, 'alternative': str(head.classes_[other_index]),
                'probabilities': {str(c): float(p) for c, p in zip(head.classes_, probs)},
                'intercept': intercept, 'margin': margin, 'expected_log_odds': expected,
                'reconstruction_error': abs(margin - expected), 'feature_count': len(names),
                'active_features': len(contributions), 'contributions': contributions, 'groups': dict(groups),
                'metadata': model.metadata, 'nearest_training': nearest,
                'saved_match': {'training': training_matches, 'max_probability_difference': delta,
                                'state': saved.get('state_sha256') == state_sha if saved else None,
                                'source': bool(self.source_matches) and all(self.source_matches.values())}}

    def sandbox(self, data):
        record = copy.deepcopy(self.record(data.get('split'), data.get('id')))
        impact = record['input']['service_impact']
        status = data.get('status')
        count = data.get('affected_sites')
        if status not in {'outage', 'degraded', 'unknown', 'none'}:
            raise ValueError('Choose a valid impact status.')
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 1000:
            raise ValueError('Site count must be an integer from 0 to 1000.')
        if status in {'outage', 'degraded'} and count == 0:
            raise ValueError('An outage or degradation needs at least one affected site.')
        observation = data.get('observation')
        if not isinstance(observation, str) or not 1 <= len(observation) <= 5000:
            raise ValueError('Enter 1 to 5000 characters of synthetic evidence.')
        impact.update(status=status, affected_sites=None if status == 'unknown' else 0 if status == 'none' else count)
        record['input']['observations'][0]['detail'] = observation
        # Keep the summary consistent with this edited observation; leave other observations intact.
        record['input']['ticket']['description'] = observation
        outputs = {'baseline': {'predictions': baseline(record['input'])}}
        for variant in ['ml', 'ml_structured']:
            predictions, probabilities, _ = self.model(variant).predict(record)
            outputs[variant] = {'predictions': predictions, 'probabilities': probabilities}
        return {'mode': 'Local sandbox. No reference score and no Jev request.', 'input': record['input'],
                'outputs': outputs, 'rules': trace_rules(record['input'])}


def handler_for(study):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def trusted(self):
            port = self.server.server_port
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            origin = self.headers.get('Origin')
            return self.headers.get('Host') in hosts and (not origin or origin in {f'http://{h}' for h in hosts})

        def send(self, status, body, mime='application/json; charset=utf-8'):
            payload = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            if status == 200 and urlparse(self.path).path == '/api/export':
                self.send_header('Content-Disposition', 'attachment; filename="Northstar-inspection.json"')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if not self.trusted():
                return self.send(403, {'error': 'Local origin required.'})
            parsed = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            try:
                if parsed.path == '/api/study':
                    return self.send(200, study.catalog())
                if parsed.path == '/api/case':
                    return self.send(200, study.case(params.get('split'), params.get('id')))
                if parsed.path == '/api/microscope':
                    return self.send(200, study.microscope(params.get('split'), params.get('id'), params.get('variant'), params.get('field'), params.get('alternative')))
                if parsed.path == '/api/export':
                    kind, split, identifier = params.get('kind'), params.get('split'), params.get('id')
                    if kind == 'results':
                        if split not in study.jobs:
                            raise ValueError('No saved results for this split.')
                        return self.send(200, study.catalog()['runs'][split])
                    if kind == 'lens':
                        return self.send(200, study.microscope(split, identifier, params.get('variant'), params.get('field'), params.get('alternative')))
                    case = study.case(split, identifier)
                    if kind in {'original-request', 'focused-request'}:
                        provider = 'jev' if kind == 'original-request' else 'jev_focused'
                        return self.send(200, case['requests'][provider]['body'])
                    if kind == 'case':
                        return self.send(200, case)
                    raise ValueError('Unknown export type.')
                if parsed.path == '/study':
                    from .study_page import render_study
                    return self.send(200, render_study(study, params), 'text/html; charset=utf-8')
                if parsed.path == '/study.md':
                    from .study_page import DOCUMENTS
                    document = params.get('doc', 'overview')
                    if document not in DOCUMENTS:
                        raise ValueError('Unknown study document.')
                    path = study.root / DOCUMENTS[document]
                    if path.exists():
                        return self.send(200, path.read_bytes(), 'text/markdown; charset=utf-8')
                assets = {'/': ('explorer.html', 'text/html; charset=utf-8'),
                          '/explorer': ('explorer.html', 'text/html; charset=utf-8'),
                          '/explorer.js': ('explorer.js', 'text/javascript; charset=utf-8'),
                          '/explorer.css': ('explorer.css', 'text/css; charset=utf-8'),
                          '/study.css': ('study.css', 'text/css; charset=utf-8'),
                          '/study.js': ('study.js', 'text/javascript; charset=utf-8')}
                if parsed.path in assets:
                    name, mime = assets[parsed.path]
                    return self.send(200, (Path(__file__).parent / 'web' / name).read_bytes(), mime)
                return self.send(404, {'error': 'Not found.'})
            except (ValueError, KeyError, TypeError) as exc:
                return self.send(400, {'error': str(exc)})

        def do_POST(self):
            if not self.trusted():
                return self.send(403, {'error': 'Local origin required.'})
            if self.path != '/api/sandbox':
                return self.send(404, {'error': 'Not found.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send(415, {'error': 'Use JSON.'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    raise ValueError('Invalid request size.')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object.')
                return self.send(200, study.sandbox(data))
            except (ValueError, TypeError, KeyError) as exc:
                return self.send(400, {'error': str(exc)})
    return Handler
