# CareCompute Reproducibility Scripts

This directory contains the earlier-stage model development, explainability,
and routing scripts that lead into the frozen CareCompute evaluation and agent
runtime under `src/`.

## Structure

### modeling/
Eligible-cohort preparation, train/validation/test splitting, model training,
calibration, threshold analysis, and final test evaluation.

### explainability/
SHAP-based explanation generation, explanation audits, and global feature
importance analysis for the eligible cohort.

### routing/
Uncertainty analysis, model disagreement, router validation, false-negative
rescue routing, and matched-strategy comparison.

## Notes

- Raw and processed data are not included in this repository.
- Saved model artifacts are not included.
- Generated results are not included.
- Scripts expect the project directory structure documented in the repository.
- The frozen CareCompute runtime and final validation logic live under `src/`.
