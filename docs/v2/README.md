# RescueNet V2 — Neural False-Negative Rescue

## Research Status

FROZEN_OFFLINE_RESEARCH_EVALUATION

RescueNet V2 extends CareCompute V1 by evaluating a neural
rescue router against the frozen logistic regression baseline.

## Dataset and Evaluation

- Dataset: UCI Diabetes 130-US Hospitals (1999–2008)
- Target: 30-day hospital readmission
- Split: Patient-disjoint train/validation/test
- Test encounters: 15,042
- Primary-negative encounters: 7,858
- False negatives: 557
- Primary classifier threshold: 0.115
- Review budgets: 5%, 10%, 15%, 20%, 25%

## Neural Router

Selected model: MLP-B

- Hidden layers: (16,)
- Activation: ReLU
- Alpha: 0.01
- Maximum iterations: 300
- Random state: 42

The router uses five features:

1. Calibrated probability
2. Model disagreement standard deviation
3. Number of diagnoses
4. Number of outpatient visits
5. Number of emergency visits

## Primary Results

At the frozen 15% review budget:

| Metric | V1 Logistic Regression | V2 MLP-B |
|---|---:|---:|
| Encounters reviewed | 1,178 | 1,178 |
| False negatives escalated | 110 | 112 |
| False-negative coverage | 19.75% | 20.11% |

The neural router selected two additional false negatives.

However, statistically reliable superiority over the frozen
logistic regression router was not demonstrated.

## Limitations

- Retrospective evaluation
- Exploratory neural architecture selection
- Development cross-validation protocol changes
- Final-test outcome exposure before later exploratory analyses
- Fairness disparities and small subgroup sizes
- No verified V2 agent integration or human-review enforcement
- No clinical deployment validation
- Complete retraining reproducibility not established

## Artifact Integrity

The frozen V2 manifest contains 16 verified artifact records.

See:
research_release/verification/frozen_artifact_inventory.json

The underlying frozen experimental artifacts are retained
locally and are not automatically included in the public repository.
