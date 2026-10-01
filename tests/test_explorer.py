import copy
import hashlib
import json
import math
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from triage_bench.app import App, handler_for
from triage_bench.dataset import ROOT
from triage_bench.explorer import FIELDS, Study, trace_rules
from triage_bench.runner import baseline


class ExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study = Study()

    def test_rule_trace_agrees_with_reference_for_every_packet(self):
        for split, rows in self.study.records.items():
            for record in rows.values():
                trace = trace_rules(record['input'])
                self.assertEqual(trace['predictions'], baseline(record['input']))
                hits = [s for s in trace['steps'] if s['reached'] and s['matched']]
                self.assertLessEqual(len(hits), 1, (split, record['id']))

    def test_catalog_explains_learning_subset_and_actual_saved_coverage(self):
        catalog = self.study.catalog()
        self.assertEqual([catalog['splits'][s]['records'] for s in ['train','validation','test','challenge']], [600,220,220,24])
        self.assertEqual(len(catalog['learning_ids']), 11)
        self.assertTrue(set(catalog['learning_ids']) <= set(self.study.records['validation']))
        for family in catalog['splits']['train']['families']:
            self.assertTrue(all(v is None for c in family['cases'] for v in c['outcomes'].values()))

    def test_exact_saved_jev_requests_have_no_reference_metadata(self):
        if not self.study.jobs.get('validation'):
            self.skipTest('Local study artifacts are not checked into Git.')
        for split in ['validation','test','challenge']:
            for identifier in self.study.records[split]:
                case = self.study.case(split, identifier)
                for request in case['requests'].values():
                    self.assertTrue(request['matches_saved_request'])
                    self.assertTrue(request['matches_saved_state'])
                    self.assertEqual(set(request['body']), {'state','questions','model'})
                    self.assertNotIn('incident_family_id', request['body']['state'])
                    self.assertNotIn('label_rationale', request['body']['state'])

    def test_ml_contributions_reconstruct_binary_and_multiclass_log_odds(self):
        for variant in ['ml','ml_structured']:
            for identifier in ['NS-f53e2040618c','NS-b073aba91088']:
                for field in FIELDS:
                    lens = self.study.microscope('validation', identifier, variant, field)
                    self.assertLess(lens['reconstruction_error'], 1e-10)
                    self.assertAlmostEqual(lens['intercept'] + sum(c['contribution'] for c in lens['contributions']), lens['margin'], 10)
                    self.assertAlmostEqual(lens['margin'], math.log(lens['probabilities'][lens['chosen']] / lens['probabilities'][lens['alternative']]), 10)
                    if lens['saved_match']['max_probability_difference'] is not None:
                        self.assertEqual(lens['saved_match']['max_probability_difference'], 0)
                    self.assertTrue(all(n['id'] in self.study.records['train'] for n in lens['nearest_training']))

    def test_revised_priority_microscope_contains_only_impact_features(self):
        lens = self.study.microscope('validation','NS-847827ec5900','ml_structured','priority')
        self.assertTrue(lens['contributions'])
        self.assertTrue(all(c['feature'].startswith('impact:') for c in lens['contributions']))

    def test_challenge_atlas_keeps_partners_adjacent_and_case_exposes_actual_pair(self):
        for family in self.study.catalog()['splits']['challenge']['families']:
            cases=family['cases']
            for index in range(0,len(cases),2):
                self.assertEqual(cases[index]['pair_id'],cases[index+1]['pair_id'])
                self.assertFalse(cases[index]['id'].endswith('-b'))
                case=self.study.case('challenge',cases[index]['id'])
                self.assertEqual(case['paired']['id'],cases[index+1]['id'])
                self.assertEqual(case['paired']['input'],self.study.records['challenge'][cases[index+1]['id']]['input'])

    def test_sandbox_does_not_mutate_inputs_or_saved_runs_or_call_jev(self):
        study = self.study
        before = copy.deepcopy((study.records, study.rows))
        job = ROOT / 'runs/app/c3519f8c7ec84814/job.json'
        saved = hashlib.sha256(job.read_bytes()).hexdigest() if job.exists() else None
        payload = {'split':'validation','id':'NS-847827ec5900','status':'degraded','affected_sites':9,
                   'observation':'Radio scheduler reports stalls. The uplink is healthy.'}
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('No provider calls')):
            nine = study.sandbox(payload)
            ten = study.sandbox({**payload,'affected_sites':10})
        self.assertEqual(set(nine['outputs']), {'baseline','ml','ml_structured'})
        self.assertEqual(nine['outputs']['baseline']['predictions']['priority'], 'P3')
        self.assertEqual(ten['outputs']['baseline']['predictions']['priority'], 'P2')
        self.assertEqual(nine['outputs']['ml_structured']['predictions']['priority'], 'P3')
        self.assertEqual(ten['outputs']['ml_structured']['predictions']['priority'], 'P2')
        self.assertNotIn('reference', nine)
        self.assertEqual((study.records, study.rows), before)
        if saved:
            self.assertEqual(hashlib.sha256(job.read_bytes()).hexdigest(),saved)

    def test_sandbox_rejects_invalid_counts_and_unknown_cases(self):
        base = {'split':'validation','id':'NS-847827ec5900','status':'outage','affected_sites':1,'observation':'Synthetic fault.'}
        for override in [{'affected_sites':True},{'affected_sites':-1},{'affected_sites':0},{'affected_sites':1.5},
                         {'id':'../../secret'},{'status':'broken'},{'observation':''}]:
            with self.assertRaises(ValueError):
                self.study.sandbox({**base,**override})

    def test_export_drops_arbitrary_provider_response_fields(self):
        row = self.study.rows.get('validation',{}).get('jev',{}).get('NS-b073aba91088')
        if row is None:
            self.skipTest('No saved study artifacts.')
        original = copy.deepcopy(row)
        try:
            row['raw_response']['private_headers'] = {'Authorization':'sentinel-secret'}
            row['raw_response']['answers']['initial_owner']['hidden_trace'] = 'sentinel-secret'
            self.assertNotIn('sentinel-secret',json.dumps(self.study.case('validation','NS-b073aba91088')))
        finally:
            row.clear(); row.update(original)

    def test_walkthrough_is_served_inside_comparison_app_and_rejects_foreign_origin(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(App()))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base+'/explorer') as response:
                self.assertIn(b'Decision observatory',response.read())
            with urllib.request.urlopen(base+'/api/study-status') as response:
                self.assertTrue(json.load(response)['available'])
            with urllib.request.urlopen(base+'/api/export?kind=focused-request&split=validation&id=NS-b073aba91088') as response:
                self.assertIn('attachment',response.headers['Content-Disposition'])
                payload=json.load(response)
                self.assertEqual(set(payload),{'model','state','questions'})
                self.assertEqual(payload,self.study.case('validation','NS-b073aba91088')['requests']['jev_focused']['body'])
            with urllib.request.urlopen(base+'/api/config') as response:
                self.assertNotIn('api_key',json.load(response)['jev'])
            request=urllib.request.Request(base+'/api/sandbox',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://outside.example'})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request)
            self.assertEqual(error.exception.code,403)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_loopback_session_bridge_preserves_config_without_exporting_key(self):
        original_app=App();original_app.profiles['jev']['api_key']='sentinel-secret'
        original=ThreadingHTTPServer(('127.0.0.1',0),handler_for(original_app))
        bridge=ThreadingHTTPServer(('127.0.0.1',0),handler_for(App(),original.server_port))
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in [original,bridge]]
        for thread in threads:thread.start()
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{bridge.server_port}/api/config') as response:
                config=json.load(response)
                self.assertTrue(config['jev']['key_configured'])
                self.assertNotIn('sentinel-secret',json.dumps(config))
            self.assertEqual(original_app.profiles['jev']['api_key'],'sentinel-secret')
        finally:
            for server in [bridge,original]:server.shutdown();server.server_close()
            for thread in threads:thread.join()


if __name__ == '__main__':
    unittest.main()
