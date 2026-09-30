# Northstar Telecom: measured failure review

September 30, 2026. These are actual predictions on fictional, authored incidents. They measure this benchmark, not operational accuracy, savings or readiness for automation.

## What improved

All four decisions must match an accepted reference: initial owner, priority, next diagnostic and insufficient evidence. Failed or missing responses count as errors.

| Approach | Validation: 220 records | Test: 220 records | Challenge: 24 records | Both challenge records correct: 12 pairs |
|---|---:|---:|---:|---:|
| ML original | 58.6% | 59.5% | 16.7% | 0.0% |
| ML compact + impact features | 86.4% | 96.8% | 58.3% | 50.0% |
| Jev original | 50.9% | 57.7% | 79.2% | 58.3% |
| Jev focused questions | 100.0% | 90.9% | 87.5% | 75.0% |
| Rules reference | 90.9% | 90.9% | 87.5% | 75.0% |

Validation informed the representation and questions. Both revisions were then frozen before the test and challenge runs. An earlier user run exposed five test records and four challenge records, so these are a held-out check of the changes rather than pristine new data. Each regular set has only 11 independently authored families with 20 variations each. The challenge has four archetypes, not 24 independent failure modes.

## Separate model improvement from software rules

This counterfactual score preserves the model’s three contextual decisions and substitutes the published priority calculation. It does not overwrite saved predictions or turn failed responses into successes.

| Original approach with software priority | Validation | Test | Challenge |
|---|---:|---:|---:|
| ML original | 90.9% | 79.1% | 50.0% |
| Jev original | 72.7% | 90.9% | 79.2% |

The original ML model with software priority performs better than revised ML on validation, but worse on test and challenge. That makes the tradeoff worth inspecting. The revised ML model learned the impact mapping from training labels; its 100% priority result is a learned classifier result, separate from the software-rule score.

## Walk through these validation cases

Open the [measured validation run](http://127.0.0.1:8767/?run=c3519f8c7ec84814). Use the guided buttons or the failure filters. The links below open individual cases from that saved run. Reviewing them does not make another API call.

### [Power transfer: ML misses the impact rule](http://127.0.0.1:8767/?run=c3519f8c7ec84814&case=NS-847827ec5900)

The equipment bus has no voltage despite healthy utility supply. The original ML model selects P3; revised ML selects P2. Keep exact impact thresholds separate from fault prose.

| Approach | Owner | Priority | Next diagnostic | Insufficient evidence |
|---|---|---|---|---|
| ML original | power | P3 | inspect_power | no |
| ML compact + impact features | power | P2 | inspect_power | no |
| Jev original | power | P2 | inspect_power | no |
| Jev focused questions | power | P2 | inspect_power | no |
| Reference | power | P2 | inspect_power | no |

### [Verified recovery: an old ticket should not keep priority high](http://127.0.0.1:8767/?run=c3519f8c7ec84814&case=NS-f42acd27ee24)

Independent probes confirm recovery with no current impact. Original ML selects P3; revised ML selects P4. Current impact should drive priority.

| Approach | Owner | Priority | Next diagnostic | Insufficient evidence |
|---|---|---|---|---|
| ML original | noc | P3 | monitor | no |
| ML compact + impact features | noc | P4 | monitor | no |
| Jev original | noc | P4 | monitor | no |
| Jev focused questions | noc | P4 | monitor | no |
| Reference | noc | P4 | monitor | no |

### [Radio scheduler: first investigation is not proven root cause](http://127.0.0.1:8767/?run=c3519f8c7ec84814&case=NS-b073aba91088)

Task stalls and delay under low occupancy support radio diagnostics. Original Jev selects noc/gather_evidence and P2 on this case; focused Jev selects ran/inspect_radio and P3.

| Approach | Owner | Priority | Next diagnostic | Insufficient evidence |
|---|---|---|---|---|
| ML original | ran | P3 | inspect_radio | no |
| ML compact + impact features | ran | P3 | inspect_radio | no |
| Jev original | noc | P2 | gather_evidence | no |
| Jev focused questions | ran | P3 | inspect_radio | no |
| Reference | ran | P3 | inspect_radio | no |

### [Maintenance scope: both originals miss a diagnostic](http://127.0.0.1:8767/?run=c3519f8c7ec84814&case=NS-f53e2040618c)

Observed impact extends beyond the maintenance assets. Both originals miss the reference next check. Focused Jev selects noc/verify_change/yes. Revised ML still assigns transport, showing a remaining representation or training-data gap.

| Approach | Owner | Priority | Next diagnostic | Insufficient evidence |
|---|---|---|---|---|
| ML original | noc | P2 | inspect_transport | no |
| ML compact + impact features | transport | P2 | inspect_transport | no |
| Jev original | transport | P2 | gather_evidence | yes |
| Jev focused questions | noc | P2 | verify_change | yes |
| Reference | noc | P2 | verify_change | yes |

### [ML regression: improved priority can conceal worse routing](http://127.0.0.1:8767/?run=c3519f8c7ec84814&case=NS-bed90468cf79)

This case is selected because revised ML changes a correct original owner or diagnostic to a wrong one. Inspect all fields rather than relying on the aggregate score.

| Approach | Owner | Priority | Next diagnostic | Insufficient evidence |
|---|---|---|---|---|
| ML original | transport | P3 | inspect_transport | no |
| ML compact + impact features | power | P2 | inspect_power | no |
| Jev original | transport | P2 | inspect_transport | no |
| Jev focused questions | transport | P2 | inspect_transport | no |
| Reference | transport | P2 | inspect_transport | no |

## Remaining failures and the next experiment

| Observed gap | Measured evidence | Proposed next step, not yet validated |
|---|---|---|
| ML maintenance scope | All 20 validation variations still miss the next diagnostic and evidence decision; compact ML also changes the owner incorrectly. | Add independently authored training examples for scope mismatch, fully explained maintenance and directly observed faults after changes. Evaluate on new scenario families. |
| ML direction of transport failure | Revised ML misses the next diagnostic in 7 test variations and owner in 6. | Add contrastive training examples separating a faulty return path from healthy radio and outbound paths; isolate structured impact from semantic feature changes in an ablation. |
| Jev diagnostic after a new neighbor relation | All 20 test variations select verify_change instead of the reference inspect_radio, while owner, priority and evidence decisions are correct. | Clarify the policy for a supported domain after a change. Have a domain reviewer assess whether verify_change should also be accepted before designing fresh evaluation cases. |
| Changed topology dependency | Focused Jev misses 3 variations after affected sites no longer depend on the failed uplink. Revised ML misses 6 cases across both sides of this topology archetype. | Compute affected-site dependency paths in software and pass supported/unsupported relationships as explicit evidence. Evaluate on new graph shapes. |
| Stale evidence | Revised ML misses 4 owner/diagnostic decisions and 3 evidence decisions in the stale-evidence archetype. | Represent measurement age separately from report arrival age and add fresh-versus-stale training pairs. |

These proposed changes were not applied after inspecting test or challenge results. Model probabilities are uncalibrated; a high-probability wrong answer remains possible. No decision authorizes a network change.

## What changed in this experiment

- **ML:** compact current evidence, word and character features, structured impact bands, and a priority classifier trained only on impact features. All fitting uses the original 600 training records from 30 families. No validation labels enter fitting. This bundles several representation changes, so it does not establish which one caused each semantic gain or regression.
- **Jev:** the same checkpoint, compact evidence without the duplicate ticket summary, explicit impact bands, and clearer independent questions. The questions distinguish an initial investigating domain from confirmed root cause, define insufficient evidence, and make the priority mapping explicit. No telecom fine-tuning was performed.
- **Response handling:** the fresh validation run contained six original and two focused responses with a probability distribution totaling 0.99. The adapter now permits only bounded rounding drift from two-decimal probabilities, renormalizes it, and retains the original values and adjustment metadata. Grossly malformed distributions still fail. This fixes response handling, not model choices. Both request variants used the same adapter for these comparisons.
- **Interface:** failure filters, regression review, high-probability errors, guided validation cases, original/revised request inspection, and paired evidence differences. Earlier runs can be compared only when input fingerprints match.

## Evidence and repeatability

| Split | Immutable run ID | Input SHA-256 |
|---|---|---|
| validation | `c3519f8c7ec84814` | `20fc9bc12f1a29259df9d2518c0c19f63e227c166ec15c3f2d16cb1bc39eb013` |
| test | `3739acf583a64c79` | `f4867bc22440414ad2ffe3d54d3d9957fc0cb62d9bd8da4fc2127255dd89e34b` |
| challenge | `908dac657e6740af` | `0dc3260d64172eb529191addf517f83834ba07b103926247319c3aa5534a1770` |

Raw responses, predictions, normalized probabilities, distribution sums, latency, question fingerprints, training fingerprints and field metrics remain in the ignored local `runs/app/<run-id>/` directories. All comparisons completed with zero failed or missing responses. The freeze record is `runs/performance-freeze.json`. Use Export JSON for public results, which exclude raw response bodies and API keys.

Rebuild this report from this checkout with `.venv/bin/python -m scripts.review_performance`. The script reads existing runs and does not fit models or call the API.

## Sources for the design choices

The [official Jev limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) describe precision limitations and recommend explicit instructions and smaller contexts. [Scikit-learn’s feature extraction documentation](https://scikit-learn.org/stable/modules/feature_extraction.html) explains text and dictionary features. The experiment above supplies the evidence for this lab’s results; these sources do not establish telecom performance.
