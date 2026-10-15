# CareCompute

**Selective Agentic AI for False-Negative Rescue in Hospital Readmission Risk Assessment**

CareCompute is a research prototype for selectively escalating potentially missed high-risk hospital readmission cases for human review.

The system combines a primary machine-learning classifier, a learned rescue router, structured review agents, safety guardrails, fairness monitoring, and mandatory human review.

## System Overview

CareCompute follows the pipeline:

Patient Context  
→ Primary Risk Model  
→ Learned Rescue Router  
→ Rescue Review Agent  
→ Explanation Agent  
→ Safety Guardrail  
→ Fairness Monitor  
→ Human Review

The AI agents do not modify the primary prediction, decision threshold, or routing decision. Final interpretation and action remain with a human reviewer.

## Research Objective

The project investigates whether selective review can identify additional false-negative cases while substantially reducing the number of cases requiring agent-assisted review compared with an always-on system.

## Dataset

Experiments use the UCI Diabetes 130-US Hospitals for Years 1999–2008 dataset.

The repository does not contain identifiable patient information.

## Status

Research pipeline: **Frozen**

Interactive demonstration: **V1 demo available**

## Disclaimer

CareCompute is a research prototype and is not a medical device or clinical decision-support system. It must not be used for diagnosis, treatment, or real-world patient-care decisions.

## Research Versions

| Version | Description | Documentation |
|---|---|---|
| CareCompute V1 | Logistic regression rescue router and agentic workflow | [V1](docs/v1/README.md) |
| RescueNet V2 | Neural router and multi-budget evaluation | [V2](docs/v2/README.md) |
| RescueNet V2.1 | Segmentation, uncertainty analysis, and offline orchestration | [V2.1](docs/v2_1/README.md) |

### Interactive Demonstration

**CareCompute V1 Streamlit Demo:**
https://carecompute.streamlit.app

The demonstration represents CareCompute V1.
V2 and V2.1 remain offline research evaluations.

### Research Integrity

All 29 manifest-listed V2 and V2.1 research artifacts
were verified against their frozen SHA-256 checksums.

Verification inventory:
[Research Artifact Inventory](research_release/verification/frozen_artifact_inventory.json)

The frozen experimental artifacts remain excluded from
the public repository pending release review.

MLP superiority over the V1 logistic regression router
was not statistically established.

The system is not clinically deployed.

