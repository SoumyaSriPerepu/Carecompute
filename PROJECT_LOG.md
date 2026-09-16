# Project Log

## 2026-09-15

**What I did:**
- Fixed the project skeleton: removed placeholder empty directories that had
  been created with file-like names (`.gitgnore`, `README.md`,
  `requirements.txt` were directories, not files), renamed `config` →
  `configs` and `results/tabels` → `results/tables` to match the guide, and
  added the missing `artifacts/` directory.
- Wrote real `.gitignore`, `requirements.txt`, and `README.md`.
- Confirmed the existing `.venv` (Python 3.9.6) already has `pandas` and
  `scikit-learn` installed; `python -c "import pandas, sklearn"` runs clean.
- Wrote `src/data/make_synthetic_data.py` and generated a 200-row synthetic
  ICU patient CSV (`data/raw/synthetic_patients.csv`) covering the Phase 1
  feature list (vitals min/mean/max, labs, admission type, comorbidities)
  with a binary `outcome` column.
- Wrote `src/models/train_baseline.py` (logistic regression baseline per
  Phase 2, step 2.1) with a preprocessing pipeline (median impute + scale
  for numeric, one-hot for categorical).

**Errors / issues hit:**
- First training run threw `RuntimeWarning: overflow encountered in matmul`
  from sklearn's LBFGS solver and collapsed to `recall = 0`. Root cause:
  200 rows with a ~12% outcome rate pushes an unregularized logistic
  regression toward quasi-complete separation. Fixed by adding
  `class_weight="balanced"`, `C=0.5`, and switching to `solver="liblinear"`.
  Clean run now, no warnings; AUROC ~0.6–0.8 depending on split (expected —
  this is a synthetic sanity check, not a real result).

**Next step:**
- Start/confirm PhysioNet credentialing + CITI training for MIMIC-IV access
  (Phase 1 prerequisite; not something I can do — needs the user's own
  PhysioNet account).
- Once real MIMIC-IV access is approved, replace
  `data/raw/synthetic_patients.csv` with the real cohort via
  `src/data/build_cohort.py` (not yet written) and `src/data/split_patients.py`
  for the fixed, non-overlapping patient-level train/val/test split
  (Phase 1, sections 4.1–4.4).
- Only after that: Phase 2 model comparison (LR vs RF vs XGBoost),
  calibration, uncertainty estimation, and onward through the agents/router
  phases in the project guide.
