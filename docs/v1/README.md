# CareCompute V1 — Selective Agentic AI

## Research Status

FROZEN_OFFLINE_RESEARCH_PROTOTYPE

CareCompute V1 investigates selective false-negative rescue
for 30-day hospital readmission risk assessment.

## Dataset

UCI Diabetes 130-US Hospitals (1999–2008).

Final held-out test population: 15,042 encounters.

## Primary Model

Frozen decision threshold: 0.115

| Metric | Value |
|---|---:|
| AUROC | 0.663350 |
| AUPRC | 0.212418 |
| Recall | 0.679147 |
| False negatives | 557 |

## Learned Rescue Router

The V1 router uses:

- Median imputation
- StandardScaler
- Balanced logistic regression
- Five routing features

Routing population: 7,858 primary-negative encounters.

## Primary Results

At the frozen 15% review budget:

| Metric | Result |
|---|---:|
| Encounters selected | 1,178 |
| False negatives escalated | 110 |
| False-negative coverage | 19.75% |
| Review precision | 9.34% |
| Rule-based comparator FN escalations | 96 |

The learned router selected 14 more false negatives
than the rule-based comparator at the same review budget.

## Agentic Architecture

Patient Context Builder
→ Rescue Review Agent
→ Explanation Agent
→ Safety Guardrail
→ Fairness Monitor
→ Human Review

Agents cannot change the frozen prediction,
decision threshold, or routing selection.

Human review is mandatory in the research workflow.

## Interactive Demonstration

https://carecompute.streamlit.app

The Streamlit demonstration uses safe synthetic or
non-identifiable demonstration cases.

It is not a clinical application.

## Limitations

- Retrospective evaluation
- Historical hospital encounter data
- No prospective clinical validation
- No actual clinical deployment
- No autonomous medical decisions
