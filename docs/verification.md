# Verification: September 30, 2026

During initial verification, the local app was started and the ML learning set was run through the browser. The paired challenge comparison was run through the local app API. Jev had not yet been configured at that stage.

| Synthetic set | Approach | All four decisions correct | Initial owner correct | Both records in pair fully correct |
|---|---|---:|---:|---:|
| 11 learning records from validation | TF-IDF + logistic regression | 54.5% | 100.0% | Not applicable |
| 24 challenge records / 12 pairs | TF-IDF + logistic regression | 16.7% | 83.3% | 0.0% |
| Same 24 challenge records | Rules reference | 87.5% | 87.5% | 75.0% |

These are actual local predictions on a small authored dataset. They do not rank Jev, establish production accuracy or demonstrate operational savings. The ML hyperparameters were fixed before these runs; no changes were made to improve the measured scores.

The poor ML challenge result is useful for learning. Surface-pattern classification can select a plausible team while missing a numeric priority boundary, a stale-evidence condition or a topology intervention. Keep exact calculations in software and examine whether a decision model improves the remaining contextual judgments.

Run records remain in the ignored `runs/app/` directory. Training metadata records dataset hashes, parameters, library version, feature count and training time. Export a run from the app to preserve its public result record.

Verification completed:

- 21 passing unit tests, including train-only fitting, inference label exclusion, no network calls in local comparison mode, missing-key handling and the Jev-shaped HTTP fixture.
- Dataset validation across all four splits, including split separation, paired challenges and SHA-256 checksums.
- JavaScript syntax check and browser inspection of learning selection, predictions and reference decisions.
- Source and documentation identity scan with no excluded real-operator name found.
- Documentation link checks.

## Authentication follow-up

The first configured Jev runs returned HTTP 401 for every attempted incident. The endpoint and Bearer authorization format matched the official TypeSafe API documentation. After the user replaced the API key, the live learning-set run `fe8d287bfd3d4f2d` completed with **11 successful Jev responses and zero failed requests**. This confirms connectivity and authentication for that run; it does not establish operational accuracy or calibration.

The source now gives actionable HTTP error messages, normalizes common pasted authorization wrappers and stops a provider batch after its first 401 or 403. The expanded suite has **24 passing tests**, including actual local HTTP fixtures for correctly formed authorization headers, authentication short-circuiting and exclusion of echoed secrets from saved errors. Dataset and JavaScript validation also pass. Backend improvements take effect on the next app restart; the working server was kept running to preserve the user's in-memory key.

Raw KPI time-series anomaly detection is not implemented in this first incident-triage lab.

## Failure-review follow-up

The updated server runs at port **8767**, with a separately entered in-memory key. Port 8766 was left running. The new server includes the authentication fixes and revised comparison approaches.

Actual full comparisons completed with zero failed or missing responses on all three sets:

| Approach | Validation, 220 records | Test, 220 records | Challenge, 24 records |
|---|---:|---:|---:|
| Original ML | 58.6% | 59.5% | 16.7% |
| Revised ML | 86.4% | 96.8% | 58.3% |
| Original Jev | 50.9% | 57.7% | 79.2% |
| Focused Jev | 100.0% | 90.9% | 87.5% |

All percentages require all four decisions to match an accepted reference. [The measured review](performance-review.md) records immutable run IDs, input hashes, software-priority scores, regressions and remaining gaps. The prior five test and four challenge records had already been exposed; the regular sets each contain only 11 authored scenario families. This is synthetic benchmark evidence.

The suite now has **29 passing tests**, including train-only revised fitting, unchanged-prose impact boundaries, bounded rounding normalization, focused configuration secrecy and failure-inclusive software-priority scoring. Dataset validation and JavaScript syntax checks pass. Browser verification covers failure filtering, regressions, request versions and paired evidence comparison.
