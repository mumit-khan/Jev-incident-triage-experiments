import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from triage_bench.app import App
from triage_bench.dataset import ROOT, read_jsonl
from triage_bench.policy import OPTIONS
from triage_bench.runner import clean_api_key, run


class AuthenticationTests(unittest.TestCase):
    def test_header_wrappers_are_normalized(self):
        for value in ['fixture-key', ' fixture-key ', 'Bearer fixture-key',
                      'Authorization: Bearer fixture-key', '"fixture-key"',
                      "'Bearer fixture-key'", 'Bearer "fixture-key"']:
            self.assertEqual(clean_api_key(value), 'fixture-key')
        with self.assertRaisesRegex(ValueError, 'whitespace'):
            clean_api_key('fixture key')

    def test_saved_configuration_does_not_expose_normalized_key(self):
        with tempfile.TemporaryDirectory() as folder:
            app = App(folder)
            cfg = app.config()['jev']
            app.configure({'provider': 'jev', **cfg, 'api_key': 'Bearer fixture-key'})
            self.assertEqual(app.profiles['jev']['api_key'], 'fixture-key')
            self.assertNotIn('fixture-key', json.dumps(app.config()))

    def test_real_request_header_and_authentication_short_circuit(self):
        for status in [200, 401, 403]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                captured = []
                class Handler(BaseHTTPRequestHandler):
                    def do_POST(self):
                        captured.append(self.headers.get('Authorization'))
                        self.rfile.read(int(self.headers['Content-Length']))
                        self.send_response(status)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        if status == 200:
                            body = {'model': 'fixture-model', 'answers': {
                                f: {'choice': next(iter(choices)), 'probabilities': {
                                    c: 1 / len(choices) for c in choices}, 'confidence': .5}
                                for f, choices in OPTIONS.items()}}
                        else:
                            # Provider error bodies can echo sensitive data; never save them.
                            body = {'error': 'fixture-key'}
                        self.wfile.write(json.dumps(body).encode())
                    def log_message(self, *args):
                        pass
                server = HTTPServer(('127.0.0.1', 0), Handler)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    output = Path(folder) / 'predictions.jsonl'
                    meta = run(ROOT / 'data/validation.inputs.jsonl', output, provider='jev',
                               model='fixture-model', api_key='Authorization: Bearer fixture-key',
                               endpoint=f'http://127.0.0.1:{server.server_port}/v1/systemone',
                               limit=3, context_tokens=32768, deployment='Local authentication fixture')
                    self.assertTrue(all(h == 'Bearer fixture-key' for h in captured))
                    rows = read_jsonl(output)
                    if status == 200:
                        self.assertEqual(len(captured), 3)
                        self.assertEqual(meta['successful_records'], 3)
                    else:
                        self.assertEqual(len(captured), 1)
                        self.assertEqual(meta['not_attempted_records'], 2)
                        self.assertFalse(meta['cancelled'])
                        self.assertEqual(rows[0]['http_status'], status)
                        self.assertIn('HTTP ' + str(status), rows[0]['error'])
                    self.assertNotIn('fixture-key', output.read_text())
                    self.assertNotIn('fixture-key', output.with_suffix('.meta.json').read_text())
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join()


if __name__ == '__main__':
    unittest.main()
