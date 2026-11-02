# RescueNet V3 — Upgrade D Methodology

Status: RETROSPECTIVE RESEARCH EVALUATION COMPLETE

## Study Objective

Evaluate budget-constrained false-negative rescue for
30-day hospital readmission prediction using patient-grouped
outer-fold evaluation.

This is an offline retrospective study, not clinical validation.

## Dataset

UCI Diabetes 130-US Hospitals dataset (1999–2008).

Upgrade D evaluation source:
data/processed/eligible/train.csv

Total eligible encounters: 69,956.
Patient identifiers: 49,312.

The historical V1/V2 test set is not used as a new
confirmatory test set.

## Evaluation Design

Five outer folds created using StratifiedGroupKFold.

No patient appears in both the training and held-out
evaluation partitions of an outer fold.

Within each outer-training partition, patient-disjoint
partitions are used for:

- Primary-model fitting
- Probability calibration
- Router development

Held-out outer-test outcomes are used only during
the final evaluation stage.

## Primary Model

The evaluated primary system uses logistic regression,
random forest, and gradient-boosting model predictions.

Gradient-boosting probabilities are calibrated using
isotonic regression on a separate calibration partition.

Primary-negative routing eligibility is determined using
a calibrated probability threshold of 0.115.

## Router Features

Both routers use five features:

1. calibrated_probability
2. model_disagreement_std
3. number_diagnoses
4. number_outpatient
5. number_emergency

## Router Configurations

Logistic regression:

- Median imputation
- Standard scaling
- LogisticRegression
- class_weight=balanced
- max_iter=2000
- random_state=42

Neural MLP:

- Median imputation
- Standard scaling
- MLPClassifier
- hidden_layer_sizes=(32, 16)
- activation=relu
- alpha=0.001
- learning_rate_init=0.001
- max_iter=300
- early_stopping=False
- random_state=42

The evaluated LR and MLP configurations differ in
class weighting as well as model architecture.
This is not an architecture-only comparison.

## Matched Review Budgets

Review budgets: 5%, 10%, 15%, 20%, and 25%.

Per-fold selection count:
round(review_budget * routing_population_size).

Candidates are ranked by descending router score,
with ascending encounter_id as deterministic tie-break.

Comparators:

- Logistic regression router
- Neural MLP router
- Random-selection expectation

## Evaluation Population

Five-fold combined routing encounters: 49,046.

False negatives within the routing population: 3,909.

These are encounter counts, not unique-patient counts.

## Statistical Analysis

Patient-cluster bootstrap within outer folds.

Bootstrap replicates: 2,000.
Random seed: 42.

The primary bootstrap conditions on trained models
and fixed original review selections.

It does not account for model retraining,
recalibration, or reranking variability.

## Subgroup Analysis

Exploratory gender and race audits at 15% review.

Eligibility for subgroup gap comparisons:

- Routing encounters >= 100
- False negatives >= 30

Small groups are reported descriptively.

No clinical fairness certification is claimed.

## Reproducibility Environment

Python 3.13.5
NumPy 2.1.3
Pandas 2.2.3
Scikit-learn 1.6.1
Platform: macOS (darwin)

## Research Limitations

- Retrospective offline evaluation
- No prospective clinical validation
- No autonomous clinical decisions
- Historical test data previously examined
- Conditional bootstrap uncertainty
- Different LR and MLP training configurations
- Limited subgroup sample sizes
- No claim of neural-router superiority
- No established clinical effectiveness

## Frozen Research Record

results/eligible/v3/upgrade_d/final_research_summary.json

Five fold-level matched-budget protocols and results
are retained in their original research directories.

The original V3 draft protocol is preserved separately.
