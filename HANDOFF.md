# Handoff: Jev incident triage experiments

## Purpose and current state

I compare hosted Jev, trained ML and rules on incident decisions for the fictional **Northstar Telecom** network. The study examines failures and whether clearer inputs, questions or software calculations improve decisions. It recommends diagnostics without executing network changes.

Two experiments are complete. The app includes an eight-chapter study walkthrough, saved-case inspection, an ML feature microscope, a local evidence sandbox and a formatted study reader at `/study`. The reader uses the repository Markdown and preserves the selected walkthrough context. The next experiment has not run.

The current handoff and historical evidence belong to the [`study-evidence-v1` release](https://github.com/mumit/Jev-incident-triage-experiments/releases/tag/study-evidence-v1). Its tag identifies the source version; the bundle manifest records the full source commit. The frozen inference checkpoint is `6a44f62`. Later UI and documentation work preserves its four inference files.

## Read first

1. [AGENTS.md](AGENTS.md): project conventions and experimental controls.
2. [README](README.md): installation, startup and checks.
3. [Experiment overview](docs/experiment-overview.md): data definitions, both experiments, actual Jev input changes and interpretation.
4. [Measured review](docs/performance-review.md): scores, regressions, individual cases and fingerprints.
5. [Run bundle](docs/run-bundle.md): download, verification and restoration.
6. [Walkthrough guide](docs/observatory.md): inspecting requests, responses, local scores and paired changes.

## What the results support

All-four test accuracy was 90.9% for rules, 59.5% for original ML, 96.8% for revised ML, 57.7% for original Jev and 90.9% for focused Jev. Focused Jev's 100% validation accuracy did not carry over to test. Dependency changes remain difficult, and high-probability errors occur.

Priority explains much of the improvement. The separate software-priority score replaces priority with the policy calculation while retaining the three model decisions. It does not change saved predictions. Several input and feature changes happened together, so the results do not isolate their individual effects.

The scenarios are constructed teaching examples, with correlated variations within families. They do not establish operational accuracy, scenario realism, calibrated probabilities or restoration-time savings. Five test packets and four challenge packets had appeared in earlier runs; subsequent review exposed their failures. Future improvements need new development and evaluation families.

## Historical evidence and setup

The repository contains synthetic inputs, separate answer keys, code and measured reports. The release bundle adds the four documented runs and freeze record under ignored `runs/`. Without it, data inspection and local ML replay work, but historical comparisons and request-hash checks are unavailable.

Follow the [restore instructions](docs/run-bundle.md), then start the app and open `/explorer` on your server. Port 8766 is the default. Existing case links use the original working session at port 8768; substitute your own port. Restoring and inspecting the bundle requires no Jev calls. New hosted comparisons require your own key in **Model settings** and incur provider charges.

## Next task

I will test explicit dependency coverage and measurement freshness separately before combining them:

- Calculate which affected sites depend on an observed faulty node. Supply supporting paths and a coverage summary alongside the raw topology. Missing or incomplete topology must stay unknown.
- Distinguish report arrival time from measurement time. Add explicit measurement age and freshness status; a missing measurement time must stay unknown.
- Write new scenarios with independent layouts, related and unrelated alarms, conflicting evidence and irrelevant changes. Obtain network-specialist review of realism and ambiguous diagnostic references before freezing the answer keys.
- Compare one change at a time on new development families, including correct cases to detect regressions. Freeze transformations and questions before evaluating separate families.
- Retain all four outputs, score software priority separately and inspect semantic accuracy, paired sensitivity, high-probability errors and failures. Fit ML features and classifiers only on training data; keep the policy and Jev checkpoint fixed.

The [overview](docs/experiment-overview.md#next-experiment) and [evaluation plan](docs/evaluation-plan.md#next-experiment) give the full plan. Raw KPI time-series anomaly detection remains a separate future experiment. The existing dataset has narrative observations, not raw KPI time series.

## Working with Codex

Open the cloned repository as a Codex project so it reads `AGENTS.md`. A useful first task is:

> Read HANDOFF.md and the linked study docs. Verify the restored historical evidence and inspect the dependency and stale-measurement failures. Prepare the new development and evaluation families and a comparison plan for dependency coverage and measurement freshness. Keep recorded results and inference unchanged while designing the next experiment. Do not make hosted Jev calls during this preparation.

API keys, `.env`, local environments and run files stay out of Git. Preserve input/answer-key separation and report missing results explicitly. The ML microscope explains a fitted score, not physical causation; Jev's hosted weights and internal reasoning remain unavailable.
