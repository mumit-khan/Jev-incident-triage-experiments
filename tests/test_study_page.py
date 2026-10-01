import html
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

from triage_bench.app import App, handler_for
from triage_bench.dataset import ROOT
from triage_bench.study_page import DEFAULT_RETURN, DOCUMENTS, render_study, return_path


class StudyPageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'docs').mkdir()
        self.source = self.root / DOCUMENTS['overview']
        self.study = SimpleNamespace(root=self.root, records={
            'validation': {'NS-b073aba91088': {}}, 'challenge': {'NS-pair-b': {}}})

    def render(self, source, params=None):
        self.source.write_text(source)
        return render_study(self.study, params or {}).decode()

    def test_return_action_accepts_only_local_walkthrough_and_escapes_attributes(self):
        for unsafe in [None, '', '//outside.example/explorer', 'https://outside.example/explorer',
                       '/study', '/explorer#unknown', '/explorer?x=\\evil', '/explorer?' + 'x' * 4096]:
            self.assertEqual(return_path(unsafe), DEFAULT_RETURN)
        back = '/explorer?split=validation&case=NS-b073aba91088&model=ml&field=priority&view=decisions#cases'
        page = self.render('# Northstar Telecom: learning\n\n## Purpose\nText.', {'return': back})
        self.assertIn('href="' + html.escape(back, quote=True) + '"', page)
        self.assertIn('<h1 id="section-northstar-telecom-learning">Learning</h1>', page)
        injected = '/explorer?case=" onmouseover="bad'
        page = self.render('# Study', {'return': injected})
        self.assertNotIn(' onmouseover="bad', page)

    def test_reader_keeps_case_context_and_routes_reference_links(self):
        back = '/explorer?split=validation&case=NS-b073aba91088&model=ml_structured&field=priority&view=decisions#models'
        page = self.render('''# Study

## Results
`NS-pair-b` [Policy](policy.md#priority) [Case](http://127.0.0.1:8768/?case=NS-pair-b) [Walkthrough](http://127.0.0.1:8766/explorer)
''', {'return': back})
        self.assertIn('split=challenge&amp;case=NS-pair-b&amp;model=ml_structured&amp;field=initial_owner&amp;view=evidence#cases', page)
        self.assertIn(html.escape('/study?' + urlencode({'return': back, 'doc': 'policy'}) + '#section-priority', quote=True), page)
        self.assertIn('field=priority&amp;view=decisions#results', page)
        self.assertIn('href="/explorer">Walkthrough', page)
        self.assertNotIn('127.0.0.1:8766', page)

    def test_markdown_is_safe_and_code_tables_and_anchors_remain_inspectable(self):
        page = self.render('''# Study

## One
<script>alert(1)</script>
[unsafe](javascript:alert(1))

## One
| A | B |
|---|---|
| 1 | 2 |

```json
{"unsafe":"<script>", "value":1}
```
''')
        self.assertNotIn('<script>alert', page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn('id="section-one"', page)
        self.assertIn('id="section-one-2"', page)
        self.assertIn('data-expand-table', page)
        self.assertIn('data-copy-code', page)
        self.assertIn('{&quot;unsafe&quot;:&quot;&lt;script&gt;&quot;, &quot;value&quot;:1}', page)

    def test_source_is_read_each_request_and_document_selector_is_allowlisted(self):
        self.assertIn('First wording', self.render('# Study\nFirst wording'))
        self.source.write_text('# Study\nUpdated wording')
        self.assertIn('Updated wording', render_study(self.study, {}).decode())
        for unknown in ['../.env', '/etc/passwd', 'missing']:
            with self.assertRaises(ValueError):
                render_study(self.study, {'doc': unknown})

    def test_every_reference_renders_with_unique_heading_ids_and_valid_local_anchors(self):
        study = SimpleNamespace(root=ROOT, records=self.study.records)
        for document in DOCUMENTS:
            with self.subTest(document=document):
                page = render_study(study, {'doc': document}).decode()
                identifiers = re.findall(r'\bid="([^"]+)"', page)
                self.assertEqual(len(identifiers), len(set(identifiers)))
                for anchor in re.findall(r'href="#([^"]+)"', page):
                    self.assertIn(anchor, identifiers)

    def test_app_serves_article_source_assets_and_rejects_foreign_origin(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(App()))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            for path, mime in [('/study', 'text/html'), ('/study.css', 'text/css'), ('/study.js', 'text/javascript')]:
                with urllib.request.urlopen(base + path) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.headers['Content-Type'].startswith(mime))
                    self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])
            for document in ['overview', 'policy']:
                with urllib.request.urlopen(base + '/study.md?doc=' + document) as response:
                    self.assertEqual(response.read(), (ROOT / DOCUMENTS[document]).read_bytes())
            for path, status, headers in [('/study?doc=../.env', 400, {}),
                                           ('/study', 403, {'Origin': 'https://outside.example'})]:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(base + path, headers=headers))
                self.assertEqual(error.exception.code, status)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
