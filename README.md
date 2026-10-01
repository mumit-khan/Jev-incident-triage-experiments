# Jev incident triage experiments

I compare Jev, trained machine learning (ML) and rules on incident decisions for **Northstar Telecom**, a fictional network. The lab exposes failures, compares changes to inputs and questions, and keeps measured results available for review.

The lab recommends diagnostics. It does not execute network changes. The data consists of constructed teaching scenarios; scores do not establish performance on a real network. Raw KPI time-series anomaly detection remains a separate future experiment.

## Start

Clone this repository and start the local app with Python 3.11+ and `uv`:

```bash
git clone git@github.com:mumit/Jev-incident-triage-experiments.git
cd Jev-incident-triage-experiments
uv sync --locked
uv run --locked python -m triage_bench.app --port 8766
```

Open [the comparison lab](http://127.0.0.1:8766/) or [the study walkthrough](http://127.0.0.1:8766/explorer). On a Mac, `start.command` starts the app at port 8766; its fallback installs the pinned requirements into a local virtual environment when `uv` is unavailable.

The current working session uses [port 8768](http://127.0.0.1:8768/explorer). Links to individual saved cases in the measured review use that session. Substitute your server's port when following those links.

Startup does not call Jev or download language-model weights. The app fits local classifiers when first needed and reuses them within the server session. Enter a key in **Model settings** to run new hosted Jev comparisons. Hosted calls incur provider charges. Keys entered there stay in server memory; `.env` is an optional ignored configuration file.

## Continue the work

Start with [HANDOFF.md](HANDOFF.md) for the current state, experimental controls and next task. Restore the four historical runs from the [study evidence release](https://github.com/mumit/Jev-incident-triage-experiments/releases/tag/study-evidence-v1) using the [bundle guide](docs/run-bundle.md). The archive stays outside Git history; `runs/` remains ignored.

## Read and explore

| Document | What it covers |
|---|---|
| [Experiment overview](docs/experiment-overview.md) | Purpose, data definitions, both experiments, input changes, results and the next experiment. |
| [Walkthrough guide](docs/observatory.md) | The eight chapters, case inspection, ML microscope, Jev requests and local sandbox. |
| [Learning guide](docs/learning-guide.md) | Running comparisons and interpreting disagreements. |
| [Measured performance review](docs/performance-review.md) | Scores, saved case links, regressions, run IDs and fingerprints. |
| [Dataset card](docs/dataset-card.md) | Construction, family splits, paired challenges and realism limits. |
| [Policy](docs/policy.md) | The four decisions and fictional priority rules. |
| [Evaluation plan](docs/evaluation-plan.md) | Scoring, experimental controls and proposed future checks. |
| [Samples](docs/samples.md) | Input excerpts and separate reference decisions. |
| [Run bundle](docs/run-bundle.md) | Download, verify and restore historical study evidence. |
| [Verification](docs/verification.md) | Current tests, browser checks and publication limits. |
| [Hosting on Gizmos](docs/gizmos.md) | The hosted app and frozen doc on Gizmos, how they run and how to deploy them. |

Choose **Read study** for the formatted experiment overview at `/study`, with section navigation, expandable tables, copyable code and links into case inspection. **Return to walkthrough** restores the selected packet, approach, field and chapter. **Download Markdown** keeps the source available for editors. The page reads the Markdown on each request.

In the walkthrough, start the guided tour with the radio scheduler validation case. Move through **Evidence**, **Decisions** and **Inside an approach**. **Paired change** compares controlled inputs. The sandbox changes a copy and runs only rules and the two local ML variants; it does not call Jev or change saved results.

## Approaches and experiments

Every approach selects an initial investigating team, priority, next diagnostic check and whether evidence is insufficient.

| Approach in the app | Implementation |
|---|---|
| Rules | Fixed keyword routing and the exact impact-priority calculation. |
| ML · original | Word TF-IDF features and four logistic regression classifiers. |
| ML · revised | Compact evidence, word/character features and structured impact. Its priority classifier uses impact features alone. |
| Jev · original | Hosted `jev-1.13.0`, the original state and short Choice definitions. |
| Jev · focused | The same checkpoint and policy, compact evidence and explicit Choice definitions. |

Experiment 1 evaluated the original approaches. Experiment 2 revised ML's features and Jev's state and questions after validation review, then froze them before full test and challenge checks. Both ML variants fit only the original 600 training records. Each ML/Jev pair receives the same state string; their training histories differ. The rules use observation text and structured impact.

**With software priority** is a separate score that replaces priority with the exact policy calculation while retaining the three model decisions. Saved predictions remain unchanged. The next experiment will isolate dependency coverage and measurement freshness on new development and evaluation families; it has not run.

## Data and saved results

The frozen dataset contains 600 training, 220 validation, 220 test and 24 challenge packets. Regular families contain 20 correlated variations; the challenge has 12 pairs across four types. The 11-packet learning set is a subset of validation. Training, validation and test families are disjoint. Five test and four challenge packets had appeared in earlier runs, so the full checks were not entirely untouched evaluations.

The repository contains the synthetic inputs, separate answer keys, source code and measured reports. Raw local runs and the freeze record remain in ignored `runs/`. A fresh clone can explore the data, fit local ML and use the sandbox, but cannot display historical predictions or verify their hashes without those run files. Missing results remain explicit. New comparisons populate the comparison lab; the walkthrough reads the fixed run IDs documented in the measured review.

Jev's hosted weights and reasoning are unavailable. The app exposes its requests and returned answers. ML contributions reconstruct the fitted classifier's score; they do not establish causes in a network. Neither model's probabilities have been calibrated for operations.

## Checks

Node.js is needed for the browser-script checks, not for running the Python app.

```bash
uv run --locked python -m triage_bench validate
uv run --locked python -m unittest discover -s tests -v
node --test tests/explorer-ui.test.cjs
node --check triage_bench/web/app.js
node --check triage_bench/web/explorer.js
node --check triage_bench/web/study.js
bash -n start.command
```

The working checkout passes 51 Python tests and nine JavaScript tests. Two Python checks depend on historical run files and skip on a fresh clone. See [verification](docs/verification.md) for their scope.

## References

- [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart)
- [Jev model information](https://docs.typesafe.ai/models)
- [Jev limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13)
- [Scikit-learn text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction)
- [Scikit-learn logistic regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression)

I adapted the source from an earlier local synthetic incident benchmark. This repository adds the trained ML comparison, focused Jev requests and interactive study walkthrough.
