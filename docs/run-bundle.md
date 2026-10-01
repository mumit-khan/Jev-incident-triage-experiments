# Historical study run bundle

The [`study-evidence-v1` release](https://github.com/mumit/Jev-incident-triage-experiments/releases/tag/study-evidence-v1) carries the recorded evidence for both completed experiments. The archive is a release asset; `runs/` remains ignored by Git.

## Contents

| Recorded run | Identifier |
|---|---|
| Experiment 1 validation | `718d977d25aa4634` |
| Experiment 2 validation | `c3519f8c7ec84814` |
| Experiment 2 test | `3739acf583a64c79` |
| Experiment 2 paired challenge | `908dac657e6740af` |

The archive contains each run's inputs, separate answer keys, predictions, metrics, metadata and job record, plus `runs/performance-freeze.json`. Successful Jev rows retain their recorded provider responses. The first validation run retains its five probability-format failures; experiment 2 has no failed or missing responses.

`bundle-manifest.json` records the source commit, inference checkpoint, Jev checkpoint, dataset fingerprints, file sizes and SHA-256 checksums. `RESTORE.md` repeats these instructions. Personal absolute paths in `input_file` metadata become repository-relative paths. JSON metadata formatting is normalized; prediction rows, returned probabilities and responses remain unchanged.

The archive contains only the four selected synthetic runs. It excludes credentials, `.env`, configuration files, local environments and unrelated runs. Creation checks credential fields, known local keys, token patterns, personal paths and excluded operator identities. The bundle has no model weights.

## Download and restore

Use a fresh clone to avoid conflicts with existing local evidence. The commands below use GitHub CLI; the same files can be downloaded from the release page.

```bash
git clone https://github.com/mumit/Jev-incident-triage-experiments.git
cd Jev-incident-triage-experiments
git switch --detach study-evidence-v1
uv sync --locked
mkdir -p runs/bundles
gh release download study-evidence-v1 --repo mumit/Jev-incident-triage-experiments --dir runs/bundles --pattern 'northstar-study-evidence-v1.zip*'
```

Check the downloaded archive checksum:

```bash
(cd runs/bundles && shasum -a 256 -c northstar-study-evidence-v1.zip.sha256)
```

Then verify and restore it:

```bash
uv run --locked python -m scripts.study_bundle verify runs/bundles/northstar-study-evidence-v1.zip
uv run --locked python -m scripts.study_bundle restore runs/bundles/northstar-study-evidence-v1.zip
uv run --locked python -m triage_bench.app --port 8766
```

Open [the walkthrough](http://127.0.0.1:8766/explorer). Restart an already-running app after restoring, so it loads the historical runs.

Verification checks every file, frozen dataset and inference source before restoration. Restore accepts existing identical files and refuses to overwrite different evidence or write through symlinks. It writes only the selected `runs/` paths. A changed inference checkout will fail verification; use the release tag to inspect the recorded experiment first.

To continue development, create a branch from the release checkout. Keep the original runs intact and store new comparisons under new IDs. Restoring or inspecting evidence makes no hosted API calls. Enter your own Jev key only when running new hosted comparisons.

## Check the restored study

Run the checks listed in the [README](../README.md#checks). With the bundle restored, the historical-request and provider-export checks run rather than skip. Rebuild the measured report with your own server URL if needed:

```bash
uv run --locked python -m scripts.review_performance --base-url http://127.0.0.1:8766
```

Changing the server URL changes only the report's local links. The script reads recorded scores without fitting models or calling Jev. [The handoff](../HANDOFF.md) explains the next experiment and the limits of this evidence.

## Build a new bundle version

Commit the matching source and documentation first, then create the archive outside the tracked tree or under ignored `runs/`:

```bash
uv run --locked python -m scripts.study_bundle create runs/bundles/northstar-study-evidence-v1.zip
```

The builder requires a clean working tree and refuses to overwrite an archive. This version packages only the four fixed study runs. A future experiment needs an updated run selection, manifest version, release tag and documentation; do not replace the v1 asset with different results.
