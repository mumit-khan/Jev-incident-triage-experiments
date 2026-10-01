# Walkthrough guide

The decision observatory is built into the comparison app. Choose **Study walkthrough** in the header. **Comparison lab** returns to the saved run and selected case. Narrow screens expose all eight chapters in **Study chapter**.

The default startup port is 8766. The current session is at [port 8768](http://127.0.0.1:8768/explorer). Start the app with [the README commands](../README.md#start), then use `/explorer` on that server.

## Eight chapters

1. **The study.** Start the guided tour with the radio scheduler validation case. The four decisions are investigating team, priority, next diagnostic and evidence sufficiency. Recommendations are diagnostic only.
2. **Data atlas.** Select a dataset and colour packets by a recorded approach. Each square is a packet; an outlined validation packet belongs to the learning subset. Select a square to open its evidence with that approach selected. Training packets have no saved evaluation predictions.
3. **Rules, ML & Jev.** Read how the three methods work and how experiment 2 changes ML and Jev. Open the policy, training configuration or an inspection view.
4. **What changed.** Compare the original and compact packets, impact band, report age and question definitions. Expand JSON when needed. Download a complete request or open selectable text with **Copy request JSON**. A matching hash confirms the reconstruction against the saved request.
5. **Results.** Switch between validation, held-out test and paired challenges. Choose all-four accuracy, individual fields, semantic decisions or the separate software-priority score. Pair scoring appears only for challenges. Family cells always show all-four correctness; select one to inspect an incorrect packet, or a correct one if the approach passed that family.
6. **Case workbench.** Follow **Evidence**, **Decisions** and **Inside an approach**. **Choose a packet** opens dataset and family selectors; **Failure filters** selects mistakes for an approach. Previous/next moves within matching packets. Hide the reference to try a decision first. **Paired change** compares both graphs or exact changed fields. Browser Back restores the case or inspection step. An empty filter explains that the previously opened evidence remains visible.
7. **Evidence sandbox.** Edit impact or the first observation and run rules and both local ML variants. The before/after table marks changed choices. Edits persist across chapters; selecting another packet starts a new sandbox. Further edits mark the replay stale. Reset discards edits. Jev is not rerun, and edited evidence has no new reference score.
8. **Next experiment.** Read the planned tests of dependency coverage and measurement freshness on new families. The experiment has not run. The existing saved results stay unchanged.

## Read the study

**Read study** opens the formatted experiment overview in another tab. Desktop readers get a section list; narrow screens use **Jump to section**. **Expand table** opens a larger comparison view. Code examples expand for inspection and offer **Copy code**, with selectable text if clipboard access is unavailable.

Case identifiers and inspection links open the relevant workbench or chapter. Referenced study guides use the same reader. **Return to walkthrough** restores the packet, approach, field, inspection view and chapter selected when the article opened. **Download Markdown** provides the original source. Edits to repository Markdown appear on the next page load.

## Inspect an approach

**Rules** exposes executed branches and the separate priority calculation. It does not infer graph dependencies or reliably resolve negation in observations.

Either **ML** variant exposes active features, fitted weight differences and their contribution to a selected class versus another. Search features, filter groups or expand from 15 to 50 visible contributions. Downloads contain every active contribution. Nearby training packets use word TF-IDF cosine similarity; they are not a causal explanation.

The complete feature sum plus intercept reconstructs the log probability ratio. Before marking a historical reconstruction as matching, the microscope checks training fingerprints, parameters, library version, input state, frozen source and saved probabilities. A training packet instead shows an explicitly labelled local replay without inventing a historical prediction.

Either **Jev** variant exposes its task definition, exact request, returned answer, probabilities and response audit. Provider confidence is separate from candidate-answer probabilities. Hosted weights, activations and internal reasoning are unavailable.

## Sandbox boundaries

The sandbox edits a copy and updates the ticket summary to match the first observation. Other observations and topology stay unchanged. Impact edits do not rewrite prose; update both when they describe the same fact. Unknown impact has an unknown count, and no impact has zero sites.

The sandbox reuses trained models. It does not fit a new model, call Jev, change saved runs or score edited evidence against the original key. Feature contributions describe a classifier's score, not the cause of a network fault.

## Comparison lab and settings

The comparison lab presents saved results first. Expand **Run a new comparison** to configure another run; hosted Jev calls incur provider charges. **Model settings** puts key entry first. Expand **Model and connection details** for the checkpoint, endpoint and declared context capacity. Save remains visible while those details are open.

For a server that is already running, the optional loopback connection can reuse its comparison session:

```bash
uv run --locked python -m triage_bench.app --port 8768 --comparison-port 8767
```

Use this only when a comparison process actually runs at port 8767. Both processes must remain running. The connection forwards comparison requests and keeps configuration and credentials in the original process. Without `--comparison-port`, the app owns its comparison session.

## Saved study and fresh clones

The walkthrough reads the fixed run IDs in `triage_bench/explorer.py`, documented in [the measured review](performance-review.md). Raw runs and the freeze record remain local and ignored by Git. A fresh clone still supports data inspection and local models, but historical predictions and hash verification require the original run files. New comparisons appear in the comparison lab without replacing the walkthrough's fixed experiments.

These are constructed teaching scenarios, with correlated family variations. Scores measure agreement with the synthetic policy, not reliability on a real network. See [the dataset card](dataset-card.md) and [verification](verification.md).
