# CareCompute Methodology

## 1. Study Objective

CareCompute investigates whether a selective agentic AI system can identify potentially missed 30-day hospital readmission cases while limiting the number of encounters requiring additional AI-assisted human review.

The central design question is:

> Can a learned rescue router prioritize primary-model-negative encounters for additional review more effectively than simple rule-based or always-on review strategies?

CareCompute is designed as a human-in-the-loop research framework. The rescue layer does not replace or modify the primary prediction model.

---

## 2. Dataset

Experiments use the **Diabetes 130-US Hospitals for Years 1999–2008** dataset from the UCI Machine Learning Repository.

The dataset contains hospital encounters involving patients with diabetes and includes demographic, diagnostic, medication, utilization, and encounter-level information.

The prediction task is formulated as identifying risk of hospital readmission within 30 days.

The final held-out test population contains:

```text id="51x3kk"
15,042 encounters
```

---

## 3. Primary Prediction System

A primary machine-learning classifier produces a probability of 30-day readmission.

The final decision threshold was frozen at:

```text id="fmljrs"
0.115
```

The frozen test-set confusion matrix is:

| Outcome | Count |
|---|---:|
| True Negatives | 7,301 |
| False Positives | 6,005 |
| False Negatives | 557 |
| True Positives | 1,179 |

Performance:

| Metric | Value |
|---|---:|
| AUROC | 0.663350 |
| AUPRC | 0.212418 |
| Recall | 0.679147 |
| FNR | 0.320853 |

Once frozen, the primary model and its decision threshold were not modified by downstream CareCompute components.

---

## 4. False-Negative Rescue Formulation

CareCompute focuses the rescue stage on encounters receiving a negative prediction from the primary model.

The resulting routing population contains:

```text id="wm0p6f"
Primary-negative encounters: 7,858
False negatives: 557
False-negative prevalence: 7.09%
```

The objective of the router is not to generate a second clinical prediction.

Instead, it produces a ranking indicating which primary-negative encounters should receive additional review.

---

## 5. Review Budget

A fixed review budget controls how many primary-negative encounters can be escalated.

The final system uses:

```text id="1mpf40"
Review budget: 15%
```

This corresponds to:

```text id="thwudq"
1,178 of 7,858 primary-negative encounters
```

The fixed budget enables routing approaches to be compared under the same review capacity.

---

## 6. Learned Rescue Router

The final rescue router is implemented as a machine-learning pipeline consisting of:

```text id="e8ox7v"
Median Imputer
      ↓
StandardScaler
      ↓
LogisticRegression
```

The logistic-regression model uses class balancing and a fixed random state.

### Router Features

Five features are used:

1. `calibrated_probability`
2. `model_disagreement_std`
3. `number_diagnoses`
4. `number_outpatient`
5. `number_emergency`

These features capture primary-model confidence, model disagreement, clinical complexity, and prior healthcare utilization.

Demographic attributes are not used as routing features.

---

## 7. Learned-Router Performance

At the frozen 15% review budget:

| Measure | Result |
|---|---:|
| Encounters reviewed | 1,178 |
| False negatives escalated | 110 |
| FN coverage | 19.75% |
| Review precision | 9.34% |

Therefore, the learned router concentrates a subset of the primary model's missed positive cases within a limited review population.

---

## 8. Rule-Based Comparator

A rule-based router was constructed using the same five signals.

Each feature was standardized and combined using an equal-weight score.

At the same review budget:

```text id="1mquud"
Rule router false negatives escalated: 96
Learned router false negatives escalated: 110
```

The learned router therefore escalated:

```text id="o0o97w"
14 additional false negatives
```

at the matched review budget.

This corresponds to an absolute false-negative coverage improvement of approximately:

```text id="8ws4y9"
2.51 percentage points
```

and a relative increase in false-negative escalation of approximately:

```text id="sok4vn"
14.58%
```

---

## 9. Always-On Comparator

An always-on agent strategy would process all:

```text id="83hvvi"
7,858 primary-negative encounters
```

The learned router processes only:

```text id="vl10kh"
1,178 encounters
```

This reduces the number of encounters receiving agent-assisted review by approximately:

```text id="75o83x"
85.01%
```

relative to the always-on strategy.

---

## 10. Probability-Ranking Audit

A probability-ranking audit was conducted to examine the behavior of simple ranking based on primary-model probability.

At the relevant cutoff:

```text id="v7ifph"
Probability cutoff: 0.085928489
Tied encounters: 1,767
Available review slots among tied cases: 309
```

The large tie group demonstrates an important limitation of relying exclusively on primary-model probability for selective review.

---

## 11. Agent-Assisted Review

Only encounters selected by the frozen learned router proceed to the agent-assisted review system.

The runtime pipeline contains:

```text id="drh3cg"
Patient Context Builder
        ↓
Rescue Review Agent
        ↓
Explanation Agent
        ↓
Safety Guardrail
        ↓
Fairness Monitor
        ↓
Agent Orchestrator
        ↓
Human Review
```

A total of:

```text id="z0r8pc"
1,178
```

selected encounters enter this pipeline.

Ground-truth outcomes are not exposed to runtime agents.

---

## 12. Rescue Review Agent

The Rescue Review Agent summarizes structured risk information for cases already selected by the router.

Its purpose is to support prioritization and human interpretation.

The agent cannot:

- modify the primary prediction;
- modify the frozen threshold;
- override routing;
- access ground-truth outcomes; or
- make autonomous clinical decisions.

---

## 13. Explanation Layer

A deterministic explanation layer generates structured explanations for all routed encounters.

The explanation process was evaluated for fidelity and safety.

The frozen explanation population contains:

```text id="8ix70b"
1,178 explanations
```

The explanation system is advisory and cannot modify predictions or routing.

---

## 14. Safety Evaluation

Safety constraints were defined before final system integration.

The system enforces the following principles:

- primary predictions remain frozen;
- the primary decision threshold remains frozen;
- routing decisions remain frozen;
- ground truth is unavailable to runtime agents;
- demographics are excluded from routing;
- human review is mandatory.

A pre-declared uncertainty-based safety analysis was also conducted using frozen uncertainty and near-threshold criteria.

---

## 15. Fairness Evaluation

Subgroup performance was evaluated across gender, race, and age.

Bootstrap confidence intervals were calculated using:

```text id="kyiqsl"
2,000 bootstrap iterations
```

Fairness monitoring is separated from routing.

Demographic attributes are used for evaluation and monitoring rather than determining which encounters receive rescue review.

---

## 16. Scientific System Comparison

Four system configurations were compared:

| System | Configuration |
|---|---|
| A | ML only |
| B | Always-on agents |
| C | Rule-based router |
| D | Learned router |

The final selected configuration was:

```text id="uv7c3d"
System D — Learned Router
```

This configuration retains the 15% review budget while providing stronger false-negative capture than the matched-budget rule router.

---

## 17. Reproducibility Verification

The frozen learned-router pipeline was replayed against the final evaluation population.

The final replay produced:

```text id="kmplpj"
Maximum numerical difference: 1.11e-16
Selection mismatches: 0
```

This verifies that the frozen router reproduces the final selection.

---

## 18. End-to-End Runtime Validation

The integrated CareCompute runtime was subjected to failure-oriented validation.

Final results:

```text id="18kbbs"
Failure tests: 28 / 28 PASSED
Router selection mismatches: 0
Ground truth exposed: No
Demographics used for routing: No
Human review required: Yes
```

The final system artifacts were subsequently frozen with cross-phase provenance verification.

---

## 19. Final Methodological Principle

CareCompute follows a selective-compute strategy:

```text id="fjr6x6"
Primary ML prediction
        ↓
Identify primary-negative population
        ↓
Learned rescue ranking
        ↓
Apply fixed review budget
        ↓
Agent assistance only for selected cases
        ↓
Safety and fairness monitoring
        ↓
Mandatory human review
```

The goal is not to allow agents to replace the predictive model or human decision-maker.

Instead, CareCompute investigates whether limited AI-assisted review capacity can be allocated more effectively toward cases that may warrant additional attention.

---

## Research-Use Disclaimer

CareCompute is a research prototype.

The system has not been prospectively validated for clinical deployment and is not intended for diagnosis, treatment, or autonomous patient-care decisions.
