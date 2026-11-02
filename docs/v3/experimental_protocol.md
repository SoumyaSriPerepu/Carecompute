# RescueNet V3 — Experimental Protocol

Status: DRAFT — NOT FROZEN
Project: CareCompute / RescueNet V3
Purpose: Offline research on budget-aware, stable, and safety-constrained false-negative rescue.

## 1. Historical Reference

Dataset: UCI Diabetes 130-US Hospitals (1999–2008).

Preserve the original patient-disjoint train, validation, and test
splits and all frozen V2/V2.1 artifacts.

Historical primary threshold: 0.115.

Historical test population: 15,042 encounters.
Historical primary-negative population: 7,858 encounters.
Historical false negatives: 557.

The historical test set has already been examined and must not
be represented as an untouched confirmatory evaluation set.

## 2. Review Budgets

Evaluate 5%, 10%, 15%, 20%, and 25% review budgets.

Budget count = floor(budget * eligible routing population).

Use deterministic tie-breaking by ascending encounter_id.

## 3. Router Features

Preserve the original five reference features:

1. calibrated_probability
2. model_disagreement_std
3. number_diagnoses
4. number_outpatient
5. number_emergency

Demographic attributes are excluded from the primary predictive
router and may be used for separately specified subgroup audits
and constrained-allocation experiments.

## 4. Leakage Prevention

Use patient-grouped cross-validation.

No patient may appear in both training and evaluation partitions
of the same fold.

Fit preprocessing only on each training partition.

Fit calibration without using the corresponding evaluation
partition's labels.

Generate all derived router features under a consistent
out-of-sample prediction protocol.

The exact nested or cross-fitted primary-model, calibration,
and router evaluation procedure must be specified and verified
before model training.

## 5. V3 Research Components

A. Budget-aware neural routing:
Optimize ranking quality at predefined review budgets.

B. Stability-aware selection:
Evaluate sensitivity to training seeds, patient-level resampling,
and controlled feature perturbations.

C. Safety and subgroup constraints:
Evaluate predeclared review-allocation rules, subgroup outcomes,
and conflicts between constraints and fixed budgets.

D. Statistical validation:
Use patient-clustered paired uncertainty estimation, ablations,
and independently sourced confirmation when feasible.

## 6. Baselines

Random selection.
Original rule-based router.
Original logistic-regression router.
Frozen V2 neural router.

Distinguish historical frozen results from baselines retrained
and evaluated on a corrected V3 population.

## 7. Evaluation Metrics

Primary:
- False negatives escalated at each review budget.
- False-negative coverage at each review budget.

Secondary:
- Review precision.
- Selection stability.
- Subgroup false-negative coverage.
- Safety-constraint violations.
- Runtime and computational cost.

Report uncertainty intervals and paired comparisons.
Do not claim superiority without supporting evidence.

## 8. Clinical Scope

Retrospective, offline research only.

No autonomous clinical action.
Human review is mandatory for escalated cases.
No claim of prospective clinical validation or deployment.

## 9. Freeze Requirements

Before changing status to FROZEN:

- Specify exact cross-fitting and calibration procedure.
- Specify model-selection and tuning boundaries.
- Specify budget-aware training objective.
- Specify stability metrics and perturbation policy.
- Specify safety constraints and conflict-resolution rules.
- Specify statistical tests and evaluation populations.
- Record seeds, environment versions, and artifact checksums.
- Verify no test-label access during model development.
