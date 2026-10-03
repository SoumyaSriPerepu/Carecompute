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

Interactive demonstration: **In development**

## Disclaimer

CareCompute is a research prototype and is not a medical device or clinical decision-support system. It must not be used for diagnosis, treatment, or real-world patient-care decisions.
