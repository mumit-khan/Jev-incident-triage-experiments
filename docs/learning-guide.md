# Learning guide

I use the lab to understand how Jev, ML and rules turn incident evidence into four bounded decisions. I start with saved cases, then use local replays or new comparisons to investigate disagreements.

## Explore the completed study

Start the app as described in [the README](../README.md#start). The current working session is at [port 8768](http://127.0.0.1:8768/explorer); the default startup port is 8766.

Choose **Study walkthrough** and start the guided tour. It begins with radio scheduler case `NS-b073aba91088` from validation. Follow the eight chapters in [the walkthrough guide](observatory.md). In **Case workbench**, read **Evidence**, compare **Decisions**, then open **Inside an approach**. **Paired change** compares the controlled inputs.

The walkthrough reads the fixed saved experiment runs. A fresh clone has no historical run files, so it shows missing results while keeping data inspection and local ML replay available.

## Run a new comparison

In **Comparison lab**, expand **Run a new comparison**. Select **Learning set · one case per family** and **ML · original** to run the 11 teaching cases locally. Read the packet before revealing **Benchmark reference decisions**; the reference is separate from the model prediction.

To compare Jev, enter a key in **Model settings** and select **Jev · original** with **ML · original** on the same cases. Hosted calls incur provider charges. Both receive the same original state, but only ML learns from this lab's labelled training examples.

For experiment 2 variants, select **ML · revised** and **Jev · focused**. They receive the same compact state; focused Jev also receives more explicit questions, and revised ML derives structured impact features. Both ML variants fit only the original 600 training packets.

Use **Run history** to choose recorded comparisons. Compare an earlier run only when its input fingerprint matches. **Export JSON** preserves public predictions, probabilities, metrics, usage and training metadata. Keys are excluded. New runs appear in the comparison lab; they do not replace the walkthrough's fixed run IDs.

## Inspect what produced a decision

| Approach | What to inspect |
|---|---|
| Rules | Executed keyword branches and the separate priority calculation. Healthy-domain words can still trigger routing. |
| ML · original / revised | Active features, fitted weight differences and their contribution to one class versus another. The complete sum plus intercept reconstructs the log probability ratio. |
| Jev · original / focused | State, Choice definitions, exact request, returned answers and response audit. Hosted weights and internal reasoning are unavailable. |

In **What changed**, compare the original and transformed packets, impact bands, report age and questions. Open the complete JSON when needed. In the comparison lab, **What Jev receives → Request version** exposes the same request variants.

Jev returns a chosen answer, candidate-answer probabilities and a separate provider confidence value. ML returns fitted class probabilities. Neither has been calibrated for operations. Feature contributions explain the fitted score, not a network's physical cause.

## Review failures

In the workbench, expand **Choose a packet**, select a family and open **Failure filters**. Select the approach before filtering for wrong decisions or wrong choices at 80% probability or higher. The ML regression filter finds a newly wrong field even when another field was already wrong. Previous/next stays within the matching packets. An empty filter explains that the previously opened evidence remains visible.

In the comparison lab, **Show cases** provides original-model errors, regressions, high-probability wrong choices and failed responses. Guided validation buttons cover priority, recovery, radio evidence, maintenance scope and an ML regression.

Start with these cases in [the measured review](performance-review.md):

- Radio scheduler: direct task stalls support RAN diagnostics despite an unknown exact cause.
- Power transfer: healthy utility supply does not erase the observed outage; priority follows current impact.
- Maintenance scope: impact extends beyond the maintenance assets, so the policy calls for verification before domain assignment.
- ML regression: a corrected priority can accompany a newly incorrect owner or next check.

Use validation to develop changes. Having inspected the existing test and challenge failures, I will use new development and evaluation families for the next experiment.

## Use the paired challenges and sandbox

The 12 challenge pairs change one factor: the nine/ten-site boundary, measurement freshness, irrelevant change timing after recovery, or dependency topology. A decision should change only when the changed evidence warrants it.

In **Evidence sandbox**, edit impact or the first observation and run a local replay. The before/after table highlights changed choices for rules and both ML variants. Jev is not rerun. Edits persist across chapters; selecting another packet starts a new sandbox. A stale-result notice appears after further edits. Reset discards the edits.

Impact edits do not rewrite observation text, so update both when they describe the same fact. Other observations and topology remain unchanged. The edited packet has no new reference answer and is not scored against the original key.

## Read the scores

**All four decisions** requires every output to match an accepted reference. Failed and missing responses count as failures. **With software priority** retains the three contextual model decisions and separately calculates priority; it does not overwrite predictions. Pair accuracy requires all four decisions to match on both packets.

P1 miss rate is undefined when the sample has no P1 references. ML inference latency includes feature transformation and prediction; training time is separate. Jev latency includes network and serving time. The exported reliability bins and coverage curves describe these synthetic cases; they do not set operational permission thresholds.

The learning set overlaps validation. Regular family variations are correlated, and some test/challenge packets had prior exposure. Read [the dataset card](dataset-card.md) before interpreting a high score.

## Configuration and failures

Keys entered in **Model settings** last for the server process. An optional `.env` can load configuration at startup and remains ignored by Git. Restarting clears keys entered through the interface.

If a response fails, inspect its recorded status and settings. The app stops that provider's remaining requests after an authentication rejection, records skipped incidents as missing and lets other selected approaches continue. It accepts only bounded rounding drift in probabilities and retains the original values. Exported errors exclude credentials.

## Next experiment

I will test explicit dependency coverage and measurement freshness on new families, one input change at a time, then evaluate the frozen revisions on separate families. I will score software priority separately and inspect regressions and high-probability errors. [The overview](experiment-overview.md#next-experiment) records the plan. Raw KPI time-series anomaly detection remains a later, separate experiment.
