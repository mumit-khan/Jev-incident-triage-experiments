# Northstar Telecom: learning from Jev, ML and rules

## Purpose

I am testing how Jev, a conventional machine learning (ML) classifier and simple rules support telecom incident decisions. I want to identify their failures and test whether better inputs, clearer questions or software calculations improve their decisions.

I start with incident interpretation and the next diagnostic step, as preparation for workflows such as a RAN KPI analyzer or an intelligent field services agent. The lab uses the fictional Northstar Telecom network and recommends diagnostics without executing network changes. It interprets KPI anomalies described in incident summaries; raw time-series anomaly detection is a separate experiment.

I ask each approach to make four decisions:

| Decision | Meaning |
|---|---|
| Initial owner | The first investigating team: radio access network (RAN), transport, power, core services or the network operations center (NOC). |
| Priority | P1 to P4 under the fictional impact policy. |
| Next check | Inspect a domain, verify a change, gather evidence or monitor recovery. |
| Insufficient evidence | Whether current evidence is insufficient to choose an investigating domain or a defined monitoring disposition. |

### Policy example

I wrote the policy to define the decisions and the evidence they require. It tells the approaches to:

- Select an initial investigating team without claiming a confirmed root cause.
- Keep missing, stale or conflicting evidence with NOC. Gather current evidence, unless verifying a relevant change scope is the immediate next step.
- Assign P1 to an outage at 10 or more sites; P2 to an outage at 1–9 sites or degradation at 10 or more sites; P3 to other degradation or unknown impact; and P4 to no current unplanned impact.
- Recommend diagnostics only, without changing configurations or executing rollback.

For example, fresh evidence of scheduler task stalls at one degraded site supports `ran / P3 / inspect_radio / no`. If the supporting measurement becomes stale, NOC should gather current evidence. Priority still follows the current impact.

## Synthetic data

### How I created it

I used AI assistance to write fictional incident scenarios and their expected decisions. “Authored” means I defined the observations, service impact, investigating team, next check and evidence sufficiency for each scenario. I did not derive these scenarios or answer keys from real incident records.

For the radio scheduler scenario, I specified elevated scheduling delay, low resource occupancy, repeated task stalls and a healthy uplink. I set RAN as the initial owner and radio inspection as the next check. Those choices form the reference against which I score the approaches.

A deterministic generator expands each regular scenario into 20 packets. It varies dates, identifiers, affected-site counts and presentation details while generally retaining the central evidence wording. It calculates priority from the fictional policy.

Each packet includes observations, report timestamps, impact, an illustrative topology and change information. I keep the answer keys, rationales and family identifiers in separate files and exclude them from model requests. The observations are narrative summaries, not simulated network measurements.

### What a family means

A **family** consists of one written scenario and its generated variations. The 20 scheduler records repeat the same underlying situation. Their owner and diagnostic references stay the same, while priority can change with affected-site count.

These are related examples, not 20 independent failure modes. A perfect family score shows consistency within that scenario, not performance across 20 different types of incident.

### Training, learning and evaluation sets

| Set | Records | Families or challenge types | Use |
|---|---:|---:|---|
| Training | 600 | 30 families | Fit ML features and classifiers. |
| Validation | 220 | 11 families | Inspect failures and choose improvements. |
| Learning | 11 | 11 families | Explore one record from each validation family. These records already count toward validation. |
| Held-out test | 220 | 11 families | Check frozen approaches on different scenario families. |
| Paired challenge | 24 | 4 types | Evaluate 12 controlled pairs. |

The **learning set** is a teaching view of validation, not an additional independent evaluation set.

**Held-out** means kept out of training and tuning. I fit ML only on training records, use validation to choose changes, then freeze those changes before test evaluation. Regular training, validation and test families do not overlap, although some policy language and network structures recur.

Five test records and four challenge records had appeared in earlier runs. The full evaluations therefore check the frozen revisions but do not constitute an entirely untouched benchmark. Having examined their failures, I will use new evaluation cases for the next improvement round.

A **paired challenge** changes one controlled factor. I check whether the decisions change appropriately or stay stable when the added information is irrelevant.

| Controlled change | Expected behavior |
|---|---|
| Outage grows from nine sites to ten | Change priority from P2 to P1. |
| Supporting power measurements become stale | Retain NOC ownership and gather current evidence. |
| An unrelated change appears after verified recovery | Continue monitoring. |
| Affected sites stop depending on the alarmed uplink | Stop using that uplink alarm to justify transport ownership. |

Each type has three pairs. The 24 records cover four challenge types, not 24 independent failure modes.

### Is it representative of a real network?

**I designed teaching data around telecom incident themes. I have not established that it represents a real network.** The scenarios cover radio, transport, power, core services, maintenance and recovery. I chose their mix to exercise decisions, not to match observed incident frequencies.

I did not calibrate the generated counts, simplified topologies or clean summaries against network telemetry. They do not reproduce a measured mix of equipment, traffic, alarm bursts, delayed reports, incomplete notes or competing diagnoses. A telecom specialist has not validated the scenarios, policy or answer keys.

The dataset lets me inspect policy application and failures under controlled changes. Its scores do not estimate performance on real incidents. That will require specialist review and evaluation on independently labeled, anonymized incidents using the evidence available at each decision time.

## First experiment: establish the comparison

I compared three approaches on the same incident evidence and candidate decisions.

### Jev

I used hosted `jev-1.13.0` through the TypeSafe API. Each request contained a **state**, consisting of the policy and full incident packet, and four **Choice** questions with fixed options and descriptions. Jev returned its decisions, answer probabilities and a separate confidence value. The request format follows the [TypeSafe quickstart](https://docs.typesafe.ai/introduction/quickstart).

I did not train or fine-tune Jev on the telecom labels.

### Rules

I built keyword rules for power, core, transport and RAN, with explicit handling for selected missing-evidence, maintenance and recovery phrases. I calculated priority directly from impact status and site count.

The rules provided a comparison point for how much straightforward software could solve. They did not learn from examples or analyze full dependency paths.

### ML

I used scikit-learn to convert the same policy-and-incident state sent to Jev into TF-IDF features for individual words and two-word sequences. TF-IDF represents text numerically and weights terms that distinguish documents. See [scikit-learn’s text feature documentation](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction).

I trained four logistic regression classifiers, one per decision, on the 600 training records. I fixed their settings before validation and fitted both the vocabulary and classifiers only on training data.

ML learned the fictional task from labeled examples. Jev used an existing model with supplied policy and instructions, so the comparison does not assume equivalent training histories.

### Initial results

I started with the learning cases, then reviewed full validation. A record passes only when all four decisions match the accepted references. Failed or missing responses count as errors.

| Original approach | All four decisions correct: 220 validation records | Failed responses |
|---|---:|---:|
| Rules | 90.9% | 0 |
| ML | 58.6% | 0 |
| Jev | 49.1% | 5 |

ML chose the correct owner on every validation record but often missed priority and the maintenance-scope diagnostic. Jev also missed priority and sometimes requested more evidence despite a directly observed domain malfunction.

The app rejected five Jev responses because their probability distributions did not sum to one within its original tolerance. I counted those response-handling failures in the score.

## Second experiment: improve the inputs and questions

I used the validation failures to revise Jev’s requests and ML’s features. I kept the dataset, policy, reference answers and Jev checkpoint unchanged, and continued fitting ML only on the original training data.

### Jev input before and after

For scheduler case `NS-b073aba91088`, I removed the duplicate ticket description and operator note. I retained observations, impact, topology and change information, and added derived impact bands and report age.

These excerpts show the actual impact and observation fields. Both complete requests also contained the same policy text, topology and change record.

**Original state excerpt**

```json
{
  "service_impact": {
    "affected_sites": 1,
    "basis": "Current independent service checks",
    "status": "degraded"
  },
  "observations": [
    {
      "detail": "Scheduling delay is elevated despite low resource occupancy. The radio scheduler reports repeated task stalls; the site uplink is healthy.",
      "observed_at": "2026-01-22T21:37:00Z",
      "source": "Synthetic operations evidence feed"
    }
  ]
}
```

**Revised state excerpt**

```json
{
  "service_impact": {
    "affected_sites": 1,
    "basis": "Current independent service checks",
    "status": "degraded",
    "affected_sites_band": "one_to_nine"
  },
  "observations": [
    {
      "detail": "Scheduling delay is elevated despite low resource occupancy. The radio scheduler reports repeated task stalls; the site uplink is healthy.",
      "report_age_minutes": 1.0
    }
  ]
}
```

I derived the band and report age from existing counts and timestamps; the observation stayed the same. I did not supply any reference answers in the request. The revised state also explains that report age can differ from measurement age and that inventory alone does not prove a fault.

I changed the questions and option descriptions. The following are excerpts from the actual instructions:

| Input | Original | Revised |
|---|---|---|
| Owner instruction | Which domain should initially investigate under the policy? | Choose the first investigating team using observations. This is NOT confirmed root cause. A directly observed malfunction is enough to begin domain investigation even if its exact cause is unknown. |
| Priority instruction | What is the incident priority under the supplied impact policy? | Apply ONLY service_impact.status and affected_sites_band. outage + ten_or_more => P1; outage + one_to_nine => P2; degraded + ten_or_more => P2; degraded + one_to_nine => P3; unknown => P3; none => P4. Do not use fault type or alarm severity. |
| Evidence instruction | Is evidence insufficient to select a unique investigating fault domain, using the policy definition? | Is current evidence insufficient to choose an initial investigating domain under the policy? Unknown exact root cause is NOT enough for yes. A directly observed domain malfunction is sufficient for no. |
| RAN option | Radio access: radio resource, interference, antenna, timing or mobility evidence. | Observed radio-access performance or hardware malfunction: scheduling, RF reception, antenna, interference, timing or mobility. |

I also clarified the NOC option and when to verify a change, gather evidence or monitor recovery. In the walkthrough, **What changed** compares the packets and questions and exposes each complete request. In the comparison lab, **What Jev receives → Request version** shows the same variants.

| Saved response for this case | Owner | Priority | Next check | Insufficient evidence |
|---|---|---|---|---|
| Original Jev | `noc` | `P2` | `gather_evidence` | `no` |
| Jev · focused | `ran` | `P3` | `inspect_radio` | `no` |
| Reference | `ran` | `P3` | `inspect_radio` | `no` |

The original priority conflicted with the stated impact: one degraded site requires P3. The revised request made that mapping explicit. The original owner and diagnostic also conflicted with the directly observed scheduler malfunction. I named scheduling in the RAN option and explained that initial investigation does not require a proven root cause.

I changed the state, questions and option descriptions together. This result establishes the combined improvement on this case, not the contribution of each individual change.

### How to identify the next Jev transformation

Start with the incorrect decision, read its policy rule and trace that rule to the input fields. Then I will check whether the request omits useful evidence, repeats it, requires a calculation or leaves the decision definition ambiguous.

| What to look for | Transformation to test | Status |
|---|---|---|
| A count requires comparison with a policy threshold | Calculate a named impact band in software and specify how the question uses it. | Included in experiment two. |
| Ticket text duplicates an observation | Keep one complete observation. Preserve any additional facts that occur only in the ticket. | Included in experiment two for these duplicate summaries. |
| The question asks for a unique fault domain, but the policy asks who should investigate first | Define evidence sufficiency in terms of the initial investigation. | Included in experiment two. |
| An option description omits the relevant evidence type | Include policy-supported evidence types, such as scheduling faults in the RAN description. | Included in experiment two. |
| A recent report contains an old measurement | Represent measurement time and report time separately; mark missing measurement time as unknown. | Next experiment. Current report age does not solve this. |
| An alarm names a faulty component, but its relationship to affected sites is unclear | Calculate dependency paths and provide whether the affected sites depend on that component, or whether the relationship is unknown. | Next experiment. |

For each candidate, change one element at a time and compare it with the unchanged request on the same validation cases. Include correct cases to detect regressions, keep the Jev checkpoint and policy fixed, and inspect both decisions and errors. Do not assume that shorter text or more instructions always helps.

Use the cases already reviewed to develop improvements. Then keep the revised input transformations and questions unchanged while evaluating them on new scenario families that were not used to develop the changes. This checks whether the improvements work beyond the familiar examples.

### ML and response handling

I gave revised ML the same compact state as focused Jev. I added short character sequences and structured features for impact status, site-count band and their combination. I trained priority on those impact features alone and the other three decisions on text and structured features. Priority remained a learned classifier result.

The rules stayed unchanged. I also scored each model **with software priority**: retain its three contextual decisions and substitute the exact priority calculation, without overwriting its saved predictions.

I updated response handling to normalize only bounded rounding differences in two-decimal probabilities, including observed totals of 0.99, while retaining raw values. Larger or otherwise malformed distributions still fail. This fixes response handling, not selected decisions.

I froze the revisions after validation review and ran all five approaches on validation, test and challenge. I reran the originals with the same updated response handler used for focused Jev.

## Results

| Approach | Validation: 220 records | Test: 220 records | Challenge: 24 records | Both records correct: 12 pairs |
|---|---:|---:|---:|---:|
| Rules | 90.9% | 90.9% | 87.5% | 75.0% |
| ML · original | 58.6% | 59.5% | 16.7% | 0.0% |
| ML · revised | 86.4% | 96.8% | 58.3% | 50.0% |
| Jev · original, rerun | 50.9% | 57.7% | 79.2% | 58.3% |
| Jev · focused | 100.0% | 90.9% | 87.5% | 75.0% |

All full comparison runs completed without failed or missing responses. A pair passes only when all four decisions are correct on both sides of the controlled change.

Revised ML passed 213 of 220 test records; focused Jev passed 200. Jev’s perfect validation score did not carry across to test, and its challenge score matched the rules.

### Interpretation

**Priority accounts for much of the gain.** Software priority raises original ML’s test score from 59.5% to 79.1% and original Jev’s from 57.7% to 90.9%. Focused Jev also scores 90.9%, so its revision did not improve aggregate correctness of the other three test decisions. It did improve those decisions on validation and challenge.

**ML’s overall improvement includes regressions.** Validation owner accuracy fell from 100.0% to 86.4%. In some transport cases, revised ML fixed priority but changed a correct owner to power. Original ML with software priority beat revised ML on validation, 90.9% versus 86.4%, but that ordering reversed on test. I introduced several ML changes together and cannot attribute each gain or regression to a single feature change.

**Some diagnostic references need review.** Revised ML still misses maintenance scope and some return-path transport cases. Focused Jev chooses `verify_change` rather than the reference `inspect_radio` on all 20 test variations involving a new neighbor relation, while getting owner, priority and evidence sufficiency right. I will ask a telecom specialist whether the reference should accept an alternative before defining the next evaluation set.

**Dependency reasoning remains weak.** Focused Jev assigns transport on three challenge variations after affected sites stop depending on the faulty uplink. On one case, it assigns 99% probability to that wrong owner. Revised ML also fails this challenge. High answer probability does not establish operational reliability.

The rules scores show how much of these written scenarios keywords and explicit policy can solve. I will use the results to choose further tests, not to estimate production accuracy, restoration-time savings or a generally superior model.

## Next experiment

I will test whether explicit dependency facts and measurement freshness reduce unsupported owner assignments and improve requests for evidence.

I will write fresh scenarios with independent network layouts, related and unrelated alarms, current and stale measurements, missing topology, conflicting evidence and irrelevant changes. I will keep the existing results unchanged and obtain specialist review of ambiguous diagnostic references before freezing the new answer keys.

I will compare the frozen revised approaches with versions that add dependency facts, measurement-age facts, or both. I will retain all four model outputs and score software-calculated priority separately. Jev and ML will still choose the investigating team, diagnostic and evidence disposition.

I will fit new ML features only on the new training split, choose changes on new validation families and evaluate on separate test families. Controlled pairs will test appropriate decision changes and stability when added information is irrelevant.

I will measure owner, diagnostic and evidence accuracy; both-record pair accuracy; high-probability errors; and how often the system retains NOC ownership to gather evidence. Improvement must reduce unsupported assignments without losing correct decisions elsewhere. The results will determine whether to proceed to read-only diagnostic tools.

I will evaluate raw KPI anomaly detection separately, measuring detection quality and false alarms before testing Jev’s interpretation of the detected evidence.

## Evidence

I checked these results against saved run records on September 30, 2026. The inference checkpoint is `6a44f62`. Later walkthrough and documentation changes preserve its four frozen inference files.

| Run | Identifier |
|---|---|
| Initial validation | `718d977d25aa4634` |
| Original and revised validation | `c3519f8c7ec84814` |
| Full test | `3739acf583a64c79` |
| Paired challenge | `908dac657e6740af` |

The [failure review](performance-review.md) includes individual cases and input fingerprints. The [dataset card](dataset-card.md) and [evaluation plan](evaluation-plan.md) record construction, limitations and scoring controls.

## Interactive inspection

I built the study walkthrough into the comparison app. Its eight chapters connect the data, methods, transformations and saved results. The case workbench follows **Evidence**, **Decisions** and **Inside an approach**, with **Paired change** for controlled comparisons. The local sandbox shows before/after choices without changing the original packet or recorded results.

[The walkthrough guide](observatory.md) explains the controls. Historical run files remain local and ignored by Git; a fresh clone can inspect the data and local models but needs those files to display the historical comparisons. [Verification](verification.md) records the current checks.
