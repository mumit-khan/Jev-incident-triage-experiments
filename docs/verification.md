# Verification

September 30, 2026. This document records the current implementation checks and their limits. [The measured review](performance-review.md) records experiment results; [the overview](experiment-overview.md) explains the study.

## Automated checks

The working checkout passes **45 Python tests and nine JavaScript tests**. Dataset validation confirms 600 training, 220 validation, 220 test and 24 challenge packets. Both browser scripts pass syntax checks, and the launcher passes its shell syntax check.

The checks cover:

- Train-only ML fitting, shared allowlisted states and exclusion of labels and generation metadata from inference.
- Failure-inclusive scoring, separate software-priority scoring, controlled pairs and bounded probability normalization.
- Request construction, local HTTP fixtures, configuration secrecy and credential exclusion from errors and exports.
- Exact reconstructed Jev request hashes for the three full saved runs and unchanged frozen inference source.
- Binary and multiclass ML score reconstruction, impact-only priority features and training-only neighbours.
- Local sandbox isolation: no hosted Jev calls, input mutation, answer-key reuse or saved-run changes.
- Family/failure filter selection, empty matches, browser navigation state and delayed-response handling.
- Explicit separation between a local ML replay and a missing saved or hosted prediction.
- Bundle credential rejection, unexpected archive paths, payload checksums and restoration that refuses conflicting evidence or symlink destinations.

Run the checks in [the README](../README.md#checks). Two Python tests require local historical runs: exact saved-request hash matching and saved provider-response export allowlisting. They skip on a fresh clone; the other tests still exercise request construction, secrecy and export routes.

## Browser review

The browser review covered all eight walkthrough chapters at wide, tablet and phone widths, including a 390-pixel viewport. Checks also covered the comparison lab, its connection to the walkthrough and the settings dialog. The pages did not spill horizontally; wide comparison tables scroll within their containers. Browser error logs were empty.

The reviewed flows include:

- Four separately stated decisions and a guided tour that starts with the radio scheduler validation case.
- Narrow-screen chapter selection, family selection, failure filters, empty states and previous/next movement.
- Evidence, decisions and model inspection, with a separate paired-input view and browser Back restoring the previous case or step.
- Hidden references, missing saved training predictions and explicitly labelled local ML replay probabilities.
- Exact Jev requests, raw returned answers, response audits and selectable JSON export dialogs.
- ML score reconstruction, alternative-class comparison, feature search and expansion from 15 to 50 visible contributions.
- Paired graphs, individual-field scores and pair scoring restricted to the challenge set.
- Before/after sandbox decisions at nine and ten sites, preserved edits, stale-result notices and disabled counts for unknown/no impact.
- Saved results before optional new-run setup; key entry first in settings, expandable connection details and a visible Save action.

## Experiment integrity

The four inference files still match `runs/performance-freeze.json`: `experiments.py`, `ml.py`, `runner.py` and `policy.py`. The walkthrough and UX work did not change the frozen dataset, reference answers, predictions or inference behavior. Interface work and checks ran locally without hosted Jev calls.

The experiment 2 validation, test and challenge runs completed with zero failed or missing responses. The first experiment's validation run had five response-validation failures, which count against its score. These were probability-format failures, not evidence of a selected decision's quality.

## Repository boundary

The GitHub repository contains source, the synthetic dataset, separate answer keys and measured reports. It excludes `.env`, raw `runs/`, local virtual environments and generated caches. Historical predictions and the freeze record remain in the working checkout.

A fresh clone can inspect data and policy, fit local ML, reconstruct local scores and use the sandbox. It cannot show the historical comparisons or confirm historical hashes without the recorded run files. Missing results remain explicit. Newly created app runs do not replace the walkthrough's fixed experiment run IDs.

The checks establish the behavior of this teaching tool. They do not certify scenario realism, diagnostic references, probability calibration, operational reliability or savings.

## Historical evidence release

The `study-evidence-v1` release provides the four documented synthetic runs and freeze record as an archive outside Git history. Its manifest binds the evidence to a source commit, dataset fingerprints and per-file checksums. Metadata paths become repository-relative; prediction rows and returned responses remain unchanged. [The bundle guide](run-bundle.md) explains restoration, and [HANDOFF.md](../HANDOFF.md) describes the next task.

A fresh local clone restored the archive and passed all 45 Python tests without skips. Rebuilding the measured review from those restored runs reproduced the committed report exactly. Restoration did not require a Jev key or make hosted calls.
