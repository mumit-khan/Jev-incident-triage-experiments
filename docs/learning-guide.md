# Learn Jev through telecom incident decisions

Start with **Learning set**. Run the ML classifier first. It works without an API key. Add Jev when you have a key, using the same incidents. Compare disagreements, not just the overall percentage.

## Understand the request

Open **What Jev receives** beneath an incident. The app shows the exact model name, state and questions. **Copy request** lets you inspect the request separately. It includes the fictional policy and evidence but no reference answers or credentials.

- **State:** what the investigator knows now, including impact, observations, topology and change information.
- **Questions:** bounded decisions with an explicit list of options and descriptions.
- **Response:** the selected option, option probabilities and Jev's separate confidence value.

For this first lab all questions use Choice. A binary Choice is used for insufficient evidence so both approaches return the same output shape. Jev also offers Noul for a yes/no probability and Score for an ordered rubric; those can be explored later without changing the initial experiment.

## Review failures and improvements

Open the updated lab at **http://127.0.0.1:8767/** for this session. Select the saved full validation run containing both original and revised approaches. Use **Show cases** to find errors by original ML, original Jev, both, regressions or high-probability wrong choices. The guided buttons cover priority, recovery, radio evidence, maintenance scope and ML regressions.

The revised ML approach uses compact evidence, word/character features and structured impact. Priority is learned from impact features alone. All fitting still uses only the original training split. The revised Jev approach uses the same checkpoint with compact evidence and clearer independent questions. Each matched pair of approaches receives the same state: original ML/original Jev, or compact ML/focused Jev.

**With software priority** is a separate score: retain the model’s three contextual decisions and compute priority from the fictional policy. It does not overwrite original predictions. Inspect owner and diagnostic regressions even when the overall percentage improves.

**What Jev receives** now lets you switch between original and focused requests. In the paired challenges, inspect **Changed evidence fields**, then move to the paired incident. A topology change can invalidate a plausible routing answer even when the fault description stays unchanged.

Use validation for changes. Freeze the approach before test or challenge evaluation, and use newly authored scenarios for the next tuning round. Earlier saved runs retain their predictions. The full [measured failure review](performance-review.md) records scores, case links, remaining gaps and proposed next experiments.

## Three cases to inspect

**Radio scheduler.** Delay rises despite low radio resource occupancy. The scheduler reports task stalls, while the uplink is healthy. Does each approach select RAN and radio diagnostics? Which evidence supports that selection?

**Transport optics.** Optical power declines from its own baseline and frame errors increase. Radio alarms follow packet loss. Does the approach investigate transport, or does the word “radio” pull it toward the wrong team?

**Unknown alarm clock offsets.** Alarm timestamps disagree and current service impact and dependencies are unverified. Does the approach retain the incident at operations and ask for evidence, or guess a fault domain?

These examples exercise anomaly interpretation, dependency reasoning and missing information. These are fictional reference cases. The measured review records actual Jev decisions separately.

## Explore paired challenges

Each pair has one controlled change:

- **Impact boundary:** nine affected outage sites become ten; only priority should change under the fictional policy.
- **Stale evidence:** current power evidence becomes stale; the next step should shift to gathering current evidence.
- **Irrelevant change:** a recent change is added after independently confirmed recovery; timing alone should not create an active fault.
- **Topology dependency:** affected sites stop depending on the failing uplink; the apparent transport explanation should no longer justify that investigating team.

The current rules and ML classifier may fail these tests. That is useful: inspect how their decisions differ from the references and from actual Jev responses.

## Read the results carefully

“All decisions correct” requires all four outputs to match an accepted reference. Failed and missing calls count against accuracy. P1 miss rate is blank when the selected sample has no P1 references. Latency includes feature transformation and prediction for ML, and network plus serving time for Jev. ML training is recorded separately and excluded from per-incident inference latency.

Exports include field-level accuracy, confusion matrices, Brier scores, reliability bins and selected-probability coverage curves. These are measured on synthetic cases. A probability threshold that works here is not an operational permission threshold. In particular, Jev's `confidence` and selected-option probability are different values; the exported coverage curves use selected-option probability for a common measure across models.

The learning set overlaps validation. Do not present it as additional held-out evidence. Keep the test and paired challenges out of prompt changes, feature fitting and threshold selection.

## If Jev requests fail

**HTTP 401** means the provider rejected the credential. Open Model settings and replace it with an active API key from [the official TypeSafe dashboard](https://console.typesafe.ai). The app accepts the raw key and strips common pasted `Bearer` or `Authorization: Bearer` wrappers and enclosing quotes. Keys containing internal whitespace are rejected locally. Saving a nonempty key confirms that it was stored, not that the provider accepted it.

Compare one incident before running a batch. A 401 or 403 stops the remaining requests to that provider; skipped incidents are reported as missing, and other selected approaches can still run. Historical runs retain their original results.

The app sends `Authorization: Bearer <key>` to the configured endpoint. Its default is `https://api.typesafe.ai/v1/systemone`, following [TypeSafe's API reference](https://docs.typesafe.ai/api). A 422 indicates request validation, a 429 indicates rate limiting and a 529 indicates provider overload. The app displays those separately from authentication errors.

Keys live only in the server process unless you explicitly put one in the ignored `.env` file. Restarting the app clears keys entered through Model settings. Re-enter the key there after a restart.

## Suggested next experiment

After learning the request/response pattern, add a separate synthetic KPI time-series exercise. Start with a daily load pattern, inject persistent degradation and telemetry gaps, compute deviations in software, and compare a numerical anomaly detector with Jev's interpretation. Evaluate anomaly detection separately from incident routing.
