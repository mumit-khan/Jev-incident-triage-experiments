# Evaluation plan

This plan covers the Jev, trained ML and rules comparison. Saved app runs contain measured predictions and field metrics. Jev results remain empty until real API calls complete. No operational benefit is measured.

## Shared task

Give each model identical visible evidence, a versioned benchmark policy, and the same candidate decisions. Preserve equivalent question semantics when adapting API formats. Record any input truncation, unsupported output, timeout, or adapter failure.

## Metrics

- Initial-owner accuracy and macro-F1.
- Priority confusion matrix and severe-incident miss rate under the fictional policy.
- Accepted diagnostic-step accuracy, allowing explicitly recorded alternatives.
- Insufficient-evidence accuracy, macro-F1 and confusion matrix.
- Calibration using Brier score and reliability plots for supported probability outputs.
- Error versus automation coverage after selecting model-specific thresholds on validation data.
- Median and p95 per-incident latency, and failed/missing request counts.
- Jev's returned token usage per call. Cost estimates and throughput experiments are future work.

Define whether each probability is over candidate answers or represents a separate confidence estimate. Do not treat all exposed confidence fields as interchangeable or invent probabilities for models that do not return them.

## Experimental controls

Pin models, library versions, prompts, policies, hardware, context limits and serving configurations. Report hosted API latency separately from local classifier latency. ML training time is recorded separately from inference. Use a rule-based reference to establish whether a model adds value.

Jev receives the policy and incident evidence without telecom fine-tuning. The ML classifier uses only the 600 training inputs and their labels; its TF-IDF vocabulary and four logistic classifiers are fitted there. Hyperparameters are fixed before validation. Both receive the same state string, but have different training histories. Keep later prompt optimization and calibration separate and disclose the data used.

Use grouped uncertainty estimates over independent incident families, not individual paraphrases. Report performance by scenario category. A balanced synthetic suite does not estimate production incident frequencies, production calibration, or operational savings.

The learning set is 11 validation records, one per family. It overlaps validation and is not an additional independent evaluation set. Brier scoring and coverage curves use candidate-answer probabilities. Jev's provider confidence is retained separately and should not be substituted for these probabilities. Classical ML probabilities are uncalibrated fitted estimates.

## Integrity checks before publication

Confirm disjoint split families; reject duplicate or near-duplicate leakage; check that future evidence and labels never enter requests; validate policy-label consistency; verify all reported results against raw run records. Review project files and publication metadata to ensure only the fictional operator identity appears.
