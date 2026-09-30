# Northstar Telecom: Jev learning lab

A local synthetic demo for learning how Jev makes bounded decisions inside a telecom workflow, with a conventional trained ML classifier for comparison.

**This is a learning exercise.** Northstar Telecom is fictional. No private tickets, real inventory or operational runbooks are included. No network actions are executed.

## Start

With `uv` installed, run from this directory:

```bash
uv sync --locked
uv run --locked python -m triage_bench.app --port 8766
```

Open **http://127.0.0.1:8766**. Alternatively, double-click `start.command` on a Mac. If `uv` is unavailable, the launcher uses Python 3.11+ and installs the pinned requirements into a local virtual environment.

The app does not download language-model weights or call Jev on startup. The ML classifier trains locally when first selected; later comparisons reuse it within that server session.

## First experiment

1. Select **Learning set** and **ML · original**. Run the 11 learning cases, one per validation scenario family.
2. Choose an incident. Read its full evidence and then reveal **Benchmark reference decisions**. These are authored answers, not model predictions.
3. Inspect the actual ML decisions and probability distributions. Look at where it chooses the wrong investigating team, misses missing evidence or misreads priority.
4. Open **Model settings**, enter your own Jev key and save. The key stays in server memory. The default is the pinned `jev-1.13.0` model.
5. Select **Jev · original** and **ML · original**, then run the same cases. Both receive the same policy and incident state. Calls to the hosted API incur your provider's charges.
6. Try **Paired challenge**. A single changed fact can change the correct decision, or should leave it unchanged.
7. Export JSON to retain predictions, answer probabilities, latency, failures, model version and training fingerprints.

For the current failure-review session, the updated app is running at **http://127.0.0.1:8767/**. It adds **ML · compact + impact features** and **Jev · focused questions**, failure filters, regression review and paired evidence inspection. Read [the measured performance review](docs/performance-review.md) for actual before/after results and remaining gaps.

Read [the learning guide](docs/learning-guide.md) for the questions to ask while comparing results.

## What is compared

| Component | How it works | What it needs |
|---|---|---|
| Jev | Evaluates a supplied policy, incident state and four Choice questions | Your API key; no telecom fine-tuning in this lab |
| ML classifier | TF-IDF unigram/bigram features and one logistic regression classifier per output | 600 labeled synthetic training examples from 30 families |
| Rules reference | Simple keyword routing and an exact impact-priority rule | No training or API key |

The four outputs are initial investigating team, fictional policy priority, next diagnostic check and whether evidence is insufficient. This version uses Choice questions for all four outputs to maintain a common comparison contract. It does not demonstrate Score or Noul yet.

The ML text features use the **same exact state string** supplied to Jev. Record IDs, labels and family metadata are excluded. The original ML parameters were fixed before validation. The revised representation and focused Jev questions were designed after reviewing original validation failures, then frozen before test and challenge checks. Jev is not trained on the telecom labels. Consequently, this compares two approaches to the task, rather than equal training histories. Rules are included to show which parts are better handled by software.

## Anomaly detection boundary

RAN KPI deviations, abnormal scheduling delay and optical degradation appear as incident evidence. The lab tests their interpretation and next investigation step. It does not yet detect anomalies from raw KPI time series, simulate network physics or forecast faults. A later anomaly experiment should compare a numerical detector and Jev on clearly matched tasks.

## Dataset and verification

Frozen dataset: 600 training records, 220 validation records, 220 test records and 24 challenge records in 12 pairs. Each regular scenario has 20 surface variations. The learning set reuses one record from each of the 11 validation families and is not an extra held-out split.

Training, validation and test scenario families are disjoint. The small number of independently authored families, templated language and artificial incident distribution limit what these scores establish. Labels have not been certified by a telecom specialist. Local classifier probabilities have not been calibrated for operations. Jev's returned confidence is separate from its selected-option probability.

```bash
uv run --locked python -m triage_bench validate
uv run --locked python -m unittest discover -s tests -v
```

[Dataset card](docs/dataset-card.md) · [Fictional policy](docs/policy.md) · [Evaluation plan](docs/evaluation-plan.md) · [Sample incidents](docs/samples.md)

## References

- [TypeSafe introduction and decision primitives](https://docs.typesafe.ai/introduction)
- [Jev quickstart](https://docs.typesafe.ai/introduction/quickstart)
- [Current Jev models](https://docs.typesafe.ai/models)
- [Jev limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- [Scikit-learn logistic regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression)

The source was adapted from the earlier local Northstar synthetic incident benchmark. The trained ML comparison and focused learning workflow are additions in this project.
