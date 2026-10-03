# CareCompute System Architecture

## 1. Overview

CareCompute is a selective agentic AI research framework designed to support human review of potentially missed 30-day hospital readmission risk cases.

Rather than applying agent assistance to every case, CareCompute operates on cases predicted negative by the primary classifier and uses a learned rescue router to selectively escalate a limited subset for additional review.

The final system combines a frozen primary model, learned rescue router, structured AI agents, safety guardrails, fairness monitoring, orchestration, and mandatory human review.

---

## 2. System Pipeline

```text
Patient Encounter
       |
       v
Primary Readmission Model
       |
       | Primary-negative cases
       v
Patient Context Builder
       |
       v
Frozen Learned Rescue Router
       |
       | Selected for review
       v
Rescue Review Agent
       |
       v
Explanation Agent
       |
       v
Safety Guardrail
       |
       v
Fairness Monitor
       |
       v
Agent Orchestrator
       |
       v
Human Review
```

Human review is mandatory for all escalated cases.

---

## 3. Primary Model

The primary classifier estimates 30-day hospital readmission risk.

The final frozen decision threshold is:

```text
0.115
```

The final test population contains:

```text
15,042 encounters
```

### Frozen Confusion Matrix

| Outcome | Count |
|---|---:|
| True Negatives | 7,301 |
| False Positives | 6,005 |
| False Negatives | 557 |
| True Positives | 1,179 |

### Primary Model Performance

| Metric | Value |
|---|---:|
| AUROC | 0.663350 |
| AUPRC | 0.212418 |
| Recall | 0.679147 |
| False Negative Rate | 0.320853 |

The rescue system does not modify the primary model or its frozen decision threshold.

---

## 4. Rescue Population

The rescue router operates only on encounters classified negative by the frozen primary model.

```text
Primary-negative population: 7,858
False negatives: 557
False-negative prevalence: 7.09%
```

The final review budget is:

```text
15%
```

This corresponds to:

```text
1,178 encounters
```

selected for additional review.

---

## 5. Learned Rescue Router

The final learned rescue router is a logistic-regression pipeline.

### Router Features

The router uses five features:

1. Calibrated primary-model probability
2. Model disagreement standard deviation
3. Number of diagnoses
4. Number of outpatient visits
5. Number of emergency visits

### Pipeline

```text
Median Imputation
       |
       v
Standard Scaling
       |
       v
Balanced Logistic Regression
```

The router is used only to prioritize primary-negative encounters for review.

### Frozen Router Results

At the 15% review budget:

```text
Cases selected: 1,178
False negatives escalated: 110
False-negative coverage: 19.75%
Review precision: 9.34%
```

A matched-budget rule-based router escalated 96 false negatives.

Therefore, the learned router escalated:

```text
14 additional false negatives
```

at the same review budget.

Compared with applying agents to all 7,858 primary-negative encounters, selective routing reduces the review population by approximately:

```text
85.01%
```

---

## 6. Patient Context Builder

For every encounter selected by the frozen router, the Patient Context Builder constructs a structured packet for downstream components.

The context builder provides only the information required by the runtime system.

Ground-truth outcomes are not exposed to runtime agents.

Demographic attributes are not used by the learned rescue router.

---

## 7. Rescue Review Agent

The Rescue Review Agent processes encounters that have already been selected by the frozen router.

Its role is to organize information for human review.

The agent may:

- summarize structured risk signals;
- identify uncertainty;
- highlight information relevant to review;
- assign review priority; and
- prepare structured information for downstream components.

The agent may not:

- change the primary prediction;
- change the primary threshold;
- change the routing decision;
- access ground-truth outcomes;
- diagnose a patient; or
- make an autonomous clinical decision.

---

## 8. Explanation Agent

The Explanation Agent generates a structured explanation to help a human reviewer understand the information associated with an escalated encounter.

The explanation layer is advisory.

It does not modify:

```text
Primary prediction
Primary threshold
Routing decision
```

---

## 9. Safety Guardrail

The Safety Guardrail enforces runtime restrictions.

Core requirements include:

```text
Primary prediction remains frozen.
Primary threshold remains frozen.
Routing decision remains frozen.
Ground truth remains unavailable to runtime agents.
Human review remains mandatory.
```

CareCompute is therefore designed as a human-in-the-loop research system rather than an autonomous clinical decision-making system.

---

## 10. Fairness Monitor

Fairness evaluation is separated from routing.

Protected demographic information is used for evaluation and monitoring rather than for determining whether an encounter should be selected by the learned rescue router.

The final evaluation includes subgroup analysis across:

- gender;
- race; and
- age groups.

The Fairness Monitor is intended to surface potential performance disparities for evaluation and human inspection.

It does not alter individual routing decisions.

---

## 11. Agent Orchestrator

The Agent Orchestrator combines the frozen outputs required to construct the final human-review packet.

The integrated runtime produced:

```text
1,178 human-review packets
```

### Runtime Priority Distribution

| Priority | Cases |
|---|---:|
| LOW | 504 |
| MODERATE | 666 |
| HIGH | 8 |
| **Total** | **1,178** |

The orchestrator does not modify the frozen primary-model prediction or routing decision.

---

## 12. Human-in-the-Loop Design

Every escalated CareCompute case terminates in human review.

```text
AI-assisted risk organization
            |
            v
Structured review packet
            |
            v
Human Reviewer
            |
            v
Human retains decision authority
```

CareCompute does not autonomously initiate clinical interventions.

---

## 13. End-to-End Validation

The frozen integrated runtime was subjected to end-to-end validation.

```text
Failure tests passed: 28 / 28
Learned-router selection mismatches: 0
Ground truth exposed to agents: No
Demographics used for routing: No
Human review required: Yes
```

These checks verify that the executable runtime remains consistent with the frozen experimental design.

---

## 14. Final System Configuration

The final scientific comparison selected:

```text
System D — Learned Router
```

The final CareCompute architecture is therefore:

```text
Primary Readmission Model
           |
           v
Primary-Negative Population
           |
           v
Learned Rescue Router
           |
           v
Selective Agent Assistance
           |
           v
Safety + Fairness Monitoring
           |
           v
Human Review
```

CareCompute demonstrates a selective-compute architecture in which agent assistance is concentrated on a limited review population rather than applied to every primary-negative encounter.

---

## Disclaimer

CareCompute is a research prototype.

It is not a medical device and is not intended for diagnosis, treatment, or deployment in real-world patient-care environments without additional clinical validation, prospective evaluation, security assessment, and appropriate regulatory review.
