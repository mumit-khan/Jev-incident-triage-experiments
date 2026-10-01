# Evaluation plan

I compare four incident decisions under the [fictional policy](policy.md). [The measured review](performance-review.md) records the completed experiment 2 runs. This plan separates implemented scoring from future work.

## Task and inputs

The outputs are `initial_owner`, `priority`, `next_check` and `insufficient_evidence`. Correctness uses the accepted answers in the separate key. Selecting an initial team does not establish a root cause or authorize a network change.

In experiment 1, original ML and original Jev receive the same allowlisted policy-and-incident state. In experiment 2, revised ML and focused Jev receive the same compact state. Revised ML also derives structured impact features from that state; focused Jev receives more explicit questions. Rules read observations and impact. No approach receives reference labels, family IDs or generation metadata during inference.

I fit each ML vocabulary and classifier only on the 600 training records. Jev uses the fixed hosted checkpoint `jev-1.13.0`; I did not fine-tune it on telecom examples. These approaches have different training histories.

## Implemented scores

| Measure | Definition |
|---|---|
| All four decisions correct | Every field matches an accepted reference. Failed and missing responses count as failures. |
| Three semantic decisions | Owner, next check and evidence sufficiency match; priority is excluded. |
| With software priority | The three model decisions match, and the separately calculated policy priority matches. Failed responses remain failures; saved predictions stay unchanged. |
| Field accuracy and macro-F1 | Each decision is scored separately, with confusion matrices and error entries. |
| P1 miss rate | Incorrect priority among P1 reference packets. Undefined when the set has no P1 cases. |
| Both packets correct | Every decision matches on both sides of each challenge pair. |
| Brier score and reliability bins | Candidate-answer probabilities are compared with a unique reference. Brier scoring skips fields with multiple accepted answers. |
| Coverage curves | Error and fraction retained at fixed selected-answer probability thresholds. These are descriptive curves, not calibrated permissions for automation. |
| Family bootstrap intervals | Resample scenario families rather than treating their variations as independent incidents. |
| Median and p95 latency | Successful calls only. Local latency includes feature transformation and prediction; hosted latency includes network and serving time. ML fitting time is recorded separately. |
| Failure and usage records | Attempted, failed and missing responses; returned model identity, usage and probability-adjustment metadata where available. |

Jev's provider confidence is separate from its candidate-answer probabilities. Common probability scores use the latter. Rules return decisions without probability distributions. I do not fabricate missing probabilities or predictions.

## Completed experiment controls

I fixed the original ML settings before validation. I used validation failures to develop revised ML features and focused Jev requests, then froze the inference source before the full test and challenge runs. Both Jev variants used the same updated response handler, which normalizes only bounded rounding drift and retains raw values.

The 11 learning packets already belong to validation. Training, validation and test families are disjoint, but repeated wording and network structures can recur. Five test packets and four challenge packets appeared in earlier runs. I report that exposure rather than describing the full checks as entirely unseen.

Each regular evaluation set has 11 families with 20 correlated variations per family. The challenge has four types and 12 pairs. This sample does not establish real incident frequencies, production calibration, operational savings or model superiority.

## Next experiment

I will use new development families to test explicit dependency coverage and measurement freshness, changing one input element at a time and including correct cases to detect regressions. I will keep the policy and Jev checkpoint fixed and fit any revised ML features only on training data.

I will freeze the transformations and questions before checking new evaluation families that did not influence them. I will retain all four outputs, score software priority separately, inspect high-probability errors and review ambiguous diagnostic references with network specialists. See [the overview](experiment-overview.md#next-experiment).

Threshold selection, operational calibration, cost estimates, throughput tests and raw KPI anomaly detection remain future work. The existing coverage curves do not validate an automation threshold.

## Before publishing results

I check split-family separation, input/answer-key isolation, timestamp availability, paired interventions and checksums. I verify reported scores against the saved runs and record the input, question, training and source fingerprints. I keep credentials out of tracked files and exports and use the fictional operator identity throughout.

Historical runs remain local and ignored by Git. The repository includes their measured reports; a fresh clone does not contain the raw evidence needed to re-audit those historical predictions. See [verification](verification.md).
