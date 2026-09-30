"""Rebuild the measured review from immutable local run records; no inference."""
import json
from pathlib import Path
from triage_bench.dataset import ROOT, read_jsonl

JOB_IDS = {'validation': 'c3519f8c7ec84814', 'test': '3739acf583a64c79', 'challenge': '908dac657e6740af'}
NAMES = {'ml': 'ML original', 'ml_structured': 'ML compact + impact features', 'jev': 'Jev original', 'jev_focused': 'Jev focused questions', 'baseline': 'Rules reference'}
PCT = lambda n: f'{n * 100:.1f}%'
jobs = {s: json.loads((ROOT / f'runs/app/{id}/job.json').read_text()) for s, id in JOB_IDS.items()}
for job in jobs.values():
    if job['status'] != 'completed':
        raise ValueError('Review requires completed comparisons.')
lines = ['# Northstar Telecom: measured failure review', '', 'September 30, 2026. These are actual predictions on fictional, authored incidents. They measure this benchmark, not operational accuracy, savings or readiness for automation.', '',
'## What improved', '', 'All four decisions must match an accepted reference: initial owner, priority, next diagnostic and insufficient evidence. Failed or missing responses count as errors.', '',
'| Approach | Validation: 220 records | Test: 220 records | Challenge: 24 records | Both challenge records correct: 12 pairs |', '|---|---:|---:|---:|---:|']
for p in NAMES:
    m = [jobs[s]['results'][p]['metrics'] for s in JOB_IDS]
    lines.append('| ' + NAMES[p] + ' | ' + ' | '.join(PCT(v['all_fields_accuracy']) for v in m) + ' | ' + PCT(m[-1]['pair_all_fields_accuracy']) + ' |')
lines += ['', 'Validation informed the representation and questions. Both revisions were then frozen before the test and challenge runs. An earlier user run exposed five test records and four challenge records, so these are a held-out check of the changes rather than pristine new data. Each regular set has only 11 independently authored families with 20 variations each. The challenge has four archetypes, not 24 independent failure modes.', '',
'## Separate model improvement from software rules', '', 'This counterfactual score preserves the model’s three contextual decisions and substitutes the published priority calculation. It does not overwrite saved predictions or turn failed responses into successes.', '',
'| Original approach with software priority | Validation | Test | Challenge |', '|---|---:|---:|---:|']
for p in ['ml', 'jev']:
    lines.append('| ' + NAMES[p] + ' | ' + ' | '.join(PCT(jobs[s]['results'][p]['metrics']['with_software_priority_accuracy']) for s in JOB_IDS) + ' |')
lines += ['', 'The original ML model with software priority performs better than revised ML on validation, but worse on test and challenge. That makes the tradeoff worth inspecting. The revised ML model learned the impact mapping from training labels; its 100% priority result is a learned classifier result, separate from the software-rule score.', '',
'## Walk through these validation cases', '', 'Open the [measured validation run](http://127.0.0.1:8767/?run=c3519f8c7ec84814). Use the guided buttons or the failure filters. The links below open individual cases from that saved run. Reviewing them does not make another API call.', '']
keys = {r['id']: r for r in read_jsonl(ROOT/'data/validation.labels.jsonl')}
index = {p: {r['id']: r for r in jobs['validation']['results'][p]['predictions']} for p in NAMES}
cases = [
 ('power_transfer', 'Power transfer: ML misses the impact rule', 'The equipment bus has no voltage despite healthy utility supply. The original ML model selects P3; revised ML selects P2. Keep exact impact thresholds separate from fault prose.'),
 ('noc_probe_recovery', 'Verified recovery: an old ticket should not keep priority high', 'Independent probes confirm recovery with no current impact. Original ML selects P3; revised ML selects P4. Current impact should drive priority.'),
 ('radio_scheduler', 'Radio scheduler: first investigation is not proven root cause', 'Task stalls and delay under low occupancy support radio diagnostics. Original Jev selects noc/gather_evidence and P2 on this case; focused Jev selects ran/inspect_radio and P3.'),
 ('noc_scope', 'Maintenance scope: both originals miss a diagnostic', 'Observed impact extends beyond the maintenance assets. Both originals miss the reference next check. Focused Jev selects noc/verify_change/yes. Revised ML still assigns transport, showing a remaining representation or training-data gap.'),
 ('transport_route', 'ML regression: improved priority can conceal worse routing', 'This case is selected because revised ML changes a correct original owner or diagnostic to a wrong one. Inspect all fields rather than relying on the aggregate score.')]
for family, title, description in cases:
    ids = [k['id'] for k in keys.values() if k['incident_family_id'] == family]
    if family == 'transport_route':
        chosen = next(id for id in ids if any(index['ml'][id]['predictions'][f] in keys[id]['accepted_answers'][f] and index['ml_structured'][id]['predictions'][f] not in keys[id]['accepted_answers'][f] for f in ['initial_owner','next_check']))
    elif family in ['radio_scheduler','noc_scope']:
        chosen = next(id for id in ids if any(index['jev'][id]['predictions'][f] not in keys[id]['accepted_answers'][f] for f in ['initial_owner','next_check','insufficient_evidence']))
    else:
        chosen = ids[0]
    lines += [f'### [{title}](http://127.0.0.1:8767/?run={JOB_IDS["validation"]}&case={chosen})', '', description, '', '| Approach | Owner | Priority | Next diagnostic | Insufficient evidence |', '|---|---|---|---|---|']
    for p in ['ml','ml_structured','jev','jev_focused']:
        pred = index[p][chosen]['predictions']
        lines.append('| '+NAMES[p]+' | '+' | '.join(pred[f] for f in ['initial_owner','priority','next_check','insufficient_evidence'])+' |')
    ref = keys[chosen]['labels']
    lines += ['| Reference | '+' | '.join(ref[f] for f in ['initial_owner','priority','next_check','insufficient_evidence'])+' |', '']
lines += ['## Remaining failures and the next experiment', '',
'| Observed gap | Measured evidence | Proposed next step, not yet validated |', '|---|---|---|',
'| ML maintenance scope | All 20 validation variations still miss the next diagnostic and evidence decision; compact ML also changes the owner incorrectly. | Add independently authored training examples for scope mismatch, fully explained maintenance and directly observed faults after changes. Evaluate on new scenario families. |',
'| ML direction of transport failure | Revised ML misses the next diagnostic in 7 test variations and owner in 6. | Add contrastive training examples separating a faulty return path from healthy radio and outbound paths; isolate structured impact from semantic feature changes in an ablation. |',
'| Jev diagnostic after a new neighbor relation | All 20 test variations select verify_change instead of the reference inspect_radio, while owner, priority and evidence decisions are correct. | Clarify the policy for a supported domain after a change. Have a domain reviewer assess whether verify_change should also be accepted before designing fresh evaluation cases. |',
'| Changed topology dependency | Focused Jev misses 3 variations after affected sites no longer depend on the failed uplink. Revised ML misses 6 cases across both sides of this topology archetype. | Compute affected-site dependency paths in software and pass supported/unsupported relationships as explicit evidence. Evaluate on new graph shapes. |',
'| Stale evidence | Revised ML misses 4 owner/diagnostic decisions and 3 evidence decisions in the stale-evidence archetype. | Represent measurement age separately from report arrival age and add fresh-versus-stale training pairs. |', '',
'These proposed changes were not applied after inspecting test or challenge results. Model probabilities are uncalibrated; a high-probability wrong answer remains possible. No decision authorizes a network change.', '',
'## What changed in this experiment', '',
'- **ML:** compact current evidence, word and character features, structured impact bands, and a priority classifier trained only on impact features. All fitting uses the original 600 training records from 30 families. No validation labels enter fitting. This bundles several representation changes, so it does not establish which one caused each semantic gain or regression.',
'- **Jev:** the same checkpoint, compact evidence without the duplicate ticket summary, explicit impact bands, and clearer independent questions. The questions distinguish an initial investigating domain from confirmed root cause, define insufficient evidence, and make the priority mapping explicit. No telecom fine-tuning was performed.',
'- **Response handling:** the fresh validation run contained six original and two focused responses with a probability distribution totaling 0.99. The adapter now permits only bounded rounding drift from two-decimal probabilities, renormalizes it, and retains the original values and adjustment metadata. Grossly malformed distributions still fail. This fixes response handling, not model choices. Both request variants used the same adapter for these comparisons.',
'- **Interface:** failure filters, regression review, high-probability errors, guided validation cases, original/revised request inspection, and paired evidence differences. Earlier runs can be compared only when input fingerprints match.', '',
'## Evidence and repeatability', '',
'| Split | Immutable run ID | Input SHA-256 |', '|---|---|---|']
for split, job in jobs.items():
    lines.append('| '+split+' | `'+job['id']+'` | `'+job['results']['ml']['metadata']['input_sha256']+'` |')
lines += ['', 'Raw responses, predictions, normalized probabilities, distribution sums, latency, question fingerprints, training fingerprints and field metrics remain in the ignored local `runs/app/<run-id>/` directories. All comparisons completed with zero failed or missing responses. The freeze record is `runs/performance-freeze.json`. Use Export JSON for public results, which exclude raw response bodies and API keys.', '',
'Rebuild this report from this checkout with `.venv/bin/python -m scripts.review_performance`. The script reads existing runs and does not fit models or call the API.', '',
'## Sources for the design choices', '',
'The [official Jev limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) describe precision limitations and recommend explicit instructions and smaller contexts. [Scikit-learn’s feature extraction documentation](https://scikit-learn.org/stable/modules/feature_extraction.html) explains text and dictionary features. The experiment above supplies the evidence for this lab’s results; these sources do not establish telecom performance.', '']
(ROOT/'docs/performance-review.md').write_text('\n'.join(lines))
print(ROOT/'docs/performance-review.md')
