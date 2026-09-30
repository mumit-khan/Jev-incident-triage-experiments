"""Inference receives public inputs only. No answer keys are read here."""
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .dataset import read_jsonl, write_jsonl
from .policy import OPTIONS, TEXT, priority, questions


def clean_api_key(value):
    """Accept a raw key or commonly pasted header wrapper without logging it."""
    if not isinstance(value, str):
        raise ValueError('API key must be text.')
    key = value.strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
        key = key[1:-1].strip()
    if key.lower().startswith('authorization:'):
        key = key.partition(':')[2].strip()
    if key.lower().startswith('bearer '):
        key = key[7:].strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
        key = key[1:-1].strip()
    if any(c.isspace() or ord(c) < 32 for c in key):
        raise ValueError('API key contains whitespace or invalid characters. Paste the complete API key only.')
    return key


def http_error_message(status):
    messages = {
        401: 'Authentication failed (HTTP 401): TypeSafe rejected the API key. Replace it with an active TypeSafe API key in Model settings.',
        403: 'Access denied (HTTP 403): check the API key permissions and account access.',
        422: 'Request validation failed (HTTP 422): check the model identifier and question format.',
        429: 'Rate limit reached (HTTP 429): wait before retrying or use a smaller batch.',
        529: 'TypeSafe is temporarily overloaded (HTTP 529): retry later.',
    }
    return messages.get(status, f'Provider request failed (HTTP {status}).')


def request_body(record, model, variant='original'):
    # Explicit allowlist prevents metadata/labels from being sent accidentally.
    if variant == 'focused':
        from .experiments import compact_packet, focused_questions
        return {'model': model, 'state': TEXT + '\nCurrent incident evidence:\n' + json.dumps(compact_packet(record['input']), ensure_ascii=False, sort_keys=True),
                'questions': focused_questions()}
    if variant != 'original':
        raise ValueError('Unknown request variant.')
    return {'model': model, 'state': TEXT + '\nIncident packet:\n' + json.dumps(record['input'], ensure_ascii=False, sort_keys=True),
            'questions': questions()}


def normalize(response):
    answers = response['answers']
    predictions, probabilities, confidence = {}, {}, {}
    for field, choices in OPTIONS.items():
        answer = answers[field]
        chosen = answer['choice']
        if chosen not in choices:
            raise ValueError(f'Invalid choice for {field}')
        predictions[field] = chosen
        dist = answer.get('probabilities')
        if dist is not None:
            if not isinstance(dist, dict) or set(dist) != set(choices):
                raise ValueError(f'Incomplete distribution for {field}')
            if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1 for p in dist.values()):
                raise ValueError(f'Invalid probability for {field}')
            total = sum(dist.values())
            if abs(total - 1) > 0.001:
                # Jev responses observed in this lab round probabilities to two decimals.
                # Permit only the worst-case rounding error for that precision; reject
                # arbitrary malformed distributions and keep raw values in the run.
                if total > 0 and all(abs(p - round(p, 2)) < 1e-10 for p in dist.values()) and abs(total - 1) <= .005 * len(dist) + 1e-10:
                    dist = {c: p / total for c, p in dist.items()}
                else:
                    raise ValueError(f'Distribution does not sum to one for {field}')
            probabilities[field] = dist
        if 'confidence' in answer:
            confidence[field] = answer['confidence']
    return predictions, probabilities, confidence


def baseline(packet):
    """Deliberately simple keyword routing, plus exact structured priority rule."""
    text = ' '.join(o['detail'] for o in packet['observations']).lower()
    if packet['service_impact']['status'] == 'none':
        owner, check, uncertain = 'noc', 'monitor', 'no'
    elif packet['service_impact']['status'] == 'unknown' or any(w in text for w in ['75 minutes old', 'cannot yet', 'timing alone', 'do not establish']):
        owner, check, uncertain = 'noc', ('verify_change' if 'change' in text or 'maintenance' in text else 'gather_evidence'), 'yes'
    else:
        owner = 'noc'
        for domain, words in [('power', ['battery', 'batteries', 'rectifier', 'breaker', 'dc ', 'generator', 'transfer switch']),
                              ('core', ['core', 'authentication', 'resolver', 'session service', 'mobility service', 'user-plane', 'policy-control']),
                              ('transport', ['aggregation', 'optical', 'crc', 'backhaul', 'non-fragmenting']),
                              ('ran', ['radio', 'antenna', 'handover', 'uplink interference', 'mobility failures', 'receive sensitivity'])]:
            if any(word in text for word in words):
                owner = domain
                break
        check = 'inspect_' + ('radio' if owner == 'ran' else owner) if owner != 'noc' else 'gather_evidence'
        uncertain = 'yes' if owner == 'noc' else 'no'
    return dict(initial_owner=owner, next_check=check, insufficient_evidence=uncertain,
                priority=priority(packet['service_impact']))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Endpoint redirects are not accepted; configure the final URL.')


def run(inputs, output, provider='baseline', model=None, endpoint=None, key_env=None,
        limit=None, timeout=60, context_tokens=None, deployment=None,
        api_key=None, progress=None, stop_event=None, ml_model=None):
    records = read_jsonl(inputs)
    if limit is not None:
        if limit < 1:
            raise ValueError('limit must be positive')
        records = records[:limit]
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.with_suffix('.meta.json').exists():
        raise ValueError('Choose a new output path; runs are immutable.')
    if provider not in {'baseline', 'ml', 'ml_structured', 'jev', 'jev_focused'}:
        raise ValueError('Choose an available comparison approach.')
    if provider in {'jev', 'jev_focused'}:
        if not model or not endpoint or not context_tokens or not deployment:
            raise ValueError('Model runs require --model, --endpoint, --context-tokens and --deployment.')
        u = urllib.parse.urlparse(endpoint)
        if u.username or u.password or u.query or u.fragment:
            raise ValueError('Endpoint must not contain credentials, query parameters or fragments.')
        if u.scheme != 'https' and not (u.scheme == 'http' and u.hostname in {'localhost', '127.0.0.1', '::1'}):
            raise ValueError('Use HTTPS except for a loopback server.')
    api_key = clean_api_key(api_key or (os.environ.get(key_env) if key_env else '') or '')
    if key_env and not api_key:
        raise ValueError(f'Set the {key_env} environment variable before running.')
    meta = {'provider': provider, 'requested_model': model, 'endpoint': endpoint,
            'request_variant': 'focused' if provider in {'ml_structured', 'jev_focused'} else 'original',
            'deployment': deployment, 'declared_context_tokens': context_tokens,
            'input_file': str(inputs), 'input_sha256': hashlib.sha256(Path(inputs).read_bytes()).hexdigest(),
            'started_at': datetime.now(timezone.utc).isoformat(), 'records': len(records),
            'execution': 'serial; first request cold/unknown, remaining requests warm/unknown; no warmup or retries',
            'policy_sha256': hashlib.sha256(TEXT.encode()).hexdigest(), 'benchmark_version': '0.1.0'}
    if provider in {'ml', 'ml_structured', 'jev', 'jev_focused'}:
        meta['questions_sha256'] = hashlib.sha256(json.dumps(request_body(records[0], model or provider, meta['request_variant'])['questions'], sort_keys=True).encode()).hexdigest()
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    opener = urllib.request.build_opener(NoRedirect())
    if provider in {'ml', 'ml_structured'}:
        if ml_model is None:
            from .ml import IncidentClassifier, StructuredIncidentClassifier
            ml_model = StructuredIncidentClassifier() if provider == 'ml_structured' else IncidentClassifier()
        meta['training'] = ml_model.metadata
    started = time.perf_counter()
    failures = 0
    attempted = 0
    stopped_reason = None
    with output.open('x') as stream:
        for record in records:
            if stop_event is not None and stop_event.is_set():
                break
            attempted += 1
            row = {'id': record['id'], 'status': 'ok', 'predictions': {}, 'probabilities': {}}
            t = time.perf_counter()
            try:
                if provider == 'baseline':
                    row['predictions'] = baseline(record['input'])
                elif provider in {'ml', 'ml_structured'}:
                    row['predictions'], row['probabilities'], row['state_sha256'] = ml_model.predict(record)
                else:
                    body = request_body(record, model, variant='focused' if provider == 'jev_focused' else 'original')
                    body_bytes = json.dumps(body, ensure_ascii=False).encode()
                    # UTF-8 bytes are a deliberately conservative preflight proxy, not a tokenizer.
                    # Require reserve for server-specific wrappers as well.
                    if len(body_bytes) + 512 > context_tokens:
                        raise ValueError('Context preflight failed: request byte bound plus 512 exceeds declared context. No request sent.')
                    headers = {'Content-Type': 'application/json'}
                    if api_key:
                        headers['Authorization'] = 'Bearer ' + api_key
                    req = urllib.request.Request(endpoint, data=body_bytes, headers=headers, method='POST')
                    with opener.open(req, timeout=timeout) as resp:
                        raw = json.load(resp)
                    # Numeric diagnostics survive a response-validation failure.
                    row['distribution_sums'] = {f: sum(a['probabilities'].values())
                        for f, a in raw.get('answers', {}).items() if f in OPTIONS
                        and isinstance(a, dict) and isinstance(a.get('probabilities'), dict)
                        and all(isinstance(v, (int, float)) and math.isfinite(v) for v in a['probabilities'].values())}
                    row['predictions'], row['probabilities'], row['provider_confidence'] = normalize(raw)
                    row['probability_adjustments'] = {f: {'original_sum': s, 'method': 'Renormalized rounding of two-decimal probabilities'}
                        for f, s in row['distribution_sums'].items() if abs(s - 1) > .001}
                    row['resolved_model'] = raw.get('model')
                    row['usage'] = raw.get('usage')
                    row['raw_response'] = raw
                    row['request_sha256'] = hashlib.sha256(body_bytes).hexdigest()
                    row['state_sha256'] = hashlib.sha256(body['state'].encode()).hexdigest()
            except urllib.error.HTTPError as exc:
                # Status-specific guidance is safe. Do not save arbitrary provider bodies,
                # which could echo credentials or request content.
                row.update(status='error', error=http_error_message(exc.code), http_status=exc.code)
                if exc.code in {401, 403}:
                    stopped_reason = 'authentication_failed' if exc.code == 401 else 'access_denied'
            except (ValueError, KeyError, TypeError, OSError) as exc:
                message = str(exc)
                if api_key:
                    message = message.replace(api_key, '[redacted]')
                row.update(status='error', error=f'{type(exc).__name__}: {message}')
            failures += int(row['status'] != 'ok')
            row['latency_ms'] = (time.perf_counter() - t) * 1000
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
            stream.flush()
            if progress:
                progress(attempted, len(records), row)
            if stopped_reason:
                break
    meta['failed_records'] = failures
    meta['attempted_records'] = attempted
    meta['cancelled'] = bool(stop_event is not None and stop_event.is_set() and attempted < len(records))
    meta['stopped_reason'] = stopped_reason
    meta['not_attempted_records'] = len(records) - attempted
    meta['successful_records'] = attempted - failures
    meta['wall_seconds'] = time.perf_counter() - started
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    return meta
