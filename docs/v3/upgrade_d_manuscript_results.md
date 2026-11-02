# RescueNet V3 — Manuscript Results and Discussion Draft

Status: DRAFT — NOT SUBMISSION READY

## Results

### Patient-Grouped Evaluation

The retrospective evaluation comprised five patient-grouped outer folds, with 49,046 eligible primary-negative encounters, 3,909 false negatives, and 42,144 patient clusters across the evaluated routing population. Review budgets of 5%, 10%, 15%, 20%, and 25% were applied separately within each outer fold.

### Matched-Budget Router Comparison

| Budget | LR FN captured | MLP FN captured | Random expected | LR coverage | MLP coverage |
|---|---:|---:|---:|---:|---:|
| 5% | 303 | 256 | 195.50 | 7.75% | 6.55% |
| 10% | 591 | 513 | 390.85 | 15.12% | 13.12% |
| 15% | 858 | 752 | 586.36 | 21.95% | 19.24% |
| 20% | 1,115 | 999 | 781.79 | 28.52% | 25.56% |
| 25% | 1,382 | 1,235 | 977.29 | 35.35% | 31.59% |

At the 15% review budget, the logistic regression router captured 858 false negatives (21.95% coverage), compared with 752 (19.24%) for the MLP router and 586.36 expected captures under random selection. The LR configuration captured 106 more false negatives than the MLP.

### Conditional Uncertainty Analysis

A 2,000-replicate patient-cluster bootstrap, resampling within outer folds, estimated the LR-minus-MLP false-negative coverage difference at the 15% review budget as +2.71 percentage points, with a conditional 95% interval of [+1.39, +4.00] percentage points. This analysis held the original review selections fixed and therefore did not incorporate model retraining, recalibration, or reranking variability.

### Exploratory Subgroup Audit

At the 15% budget, the LR female-minus-male false-negative coverage difference was +0.98 percentage points (conditional 95% interval [-1.71, +3.67]). The AfricanAmerican-minus-Caucasian difference was +0.14 percentage points ([-3.42, +3.58]). These subgroup comparisons were exploratory and do not establish clinical fairness.

## Discussion

The results illustrate that a budget-constrained secondary routing stage can prioritize some false-negative readmission predictions for retrospective review. Across all five evaluated budgets, the specified logistic regression configuration captured more false negatives than the specified MLP configuration.

These findings should not be interpreted as an architecture-only comparison because the LR router used balanced class weighting whereas the MLP did not. Neither the retrospective comparison nor the conditional bootstrap establishes universal superiority.

## Limitations

- Retrospective offline evaluation without prospective clinical validation.
- The bootstrap conditions on fixed trained models and review selections.
- The historical test set had previously been inspected.
- Router configurations differ beyond architecture.
- Subgroup analyses are exploratory and sample sizes vary.
- No demonstrated clinical effectiveness or deployment readiness.

## Contribution Statement

This study presents a reproducible patient-grouped evaluation framework for budget-constrained false-negative review, including separate primary fitting, calibration, and router development partitions; frozen matched-budget comparisons; deterministic selection; and patient-clustered conditional uncertainty analysis.

