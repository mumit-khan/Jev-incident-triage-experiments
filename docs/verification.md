# Verification: September 30, 2026

The local app was started and the ML learning set was run through the browser. The paired challenge comparison was run through the local app API. No Jev API call was made.

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

Live Jev inference, its telecom accuracy, its calibration and its latency remain unmeasured. Raw KPI time-series anomaly detection is not implemented in this first incident-triage lab.
