import pandas as pd
import numpy as np
import joblib
import os

from sklearn.isotonic import IsotonicRegression

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss
)


# =====================================================
# 1. LOAD VALIDATION DATA
# =====================================================

val = pd.read_csv(
    "data/processed/eligible/validation.csv",
    low_memory=False
)

y_val = val["target_30d"]

X_val = val.drop(
    columns=[
        "patient_nbr",
        "encounter_id",
        "target_30d"
    ]
)


# =====================================================
# 2. LOAD SELECTED MODEL
# =====================================================

model = joblib.load(
    "src/models/saved/eligible/"
    "gradient_boosting.joblib"
)


# =====================================================
# 3. RAW PROBABILITIES
# =====================================================

raw_prob = model.predict_proba(
    X_val
)[:, 1]


# =====================================================
# 4. FIT ISOTONIC CALIBRATOR
# =====================================================

calibrator = IsotonicRegression(
    out_of_bounds="clip"
)

calibrator.fit(
    raw_prob,
    y_val
)

cal_prob = calibrator.predict(
    raw_prob
)


# =====================================================
# 5. COMPARE RAW VS CALIBRATED
# =====================================================

raw_auroc = roc_auc_score(
    y_val,
    raw_prob
)

cal_auroc = roc_auc_score(
    y_val,
    cal_prob
)

raw_auprc = average_precision_score(
    y_val,
    raw_prob
)

cal_auprc = average_precision_score(
    y_val,
    cal_prob
)

raw_brier = brier_score_loss(
    y_val,
    raw_prob
)

cal_brier = brier_score_loss(
    y_val,
    cal_prob
)


print()
print("CALIBRATION CHECK")
print("-------------------------")

print(
    "Actual positive rate:",
    y_val.mean()
)

print()
print("RAW")
print("Average probability:", raw_prob.mean())
print("AUROC:", raw_auroc)
print("AUPRC:", raw_auprc)
print("Brier:", raw_brier)

print()
print("CALIBRATED")
print("Average probability:", cal_prob.mean())
print("AUROC:", cal_auroc)
print("AUPRC:", cal_auprc)
print("Brier:", cal_brier)


# =====================================================
# 6. SAVE CALIBRATOR
# =====================================================

joblib.dump(
    calibrator,
    "src/models/saved/eligible/"
    "isotonic_calibrator.joblib"
)


# =====================================================
# 7. SAVE VALIDATION PROBABILITIES
# =====================================================

results = pd.DataFrame({
    "encounter_id":
        val["encounter_id"],

    "actual_30d":
        y_val,

    "raw_probability":
        raw_prob,

    "calibrated_probability":
        cal_prob
})

results[
    "uncertainty"
] = 1 - abs(
    2 * results[
        "calibrated_probability"
    ] - 1
)

results.to_csv(
    "results/eligible/"
    "calibration_validation.csv",
    index=False
)


print()
print(
    "Calibrator saved:",
    os.path.exists(
        "src/models/saved/eligible/"
        "isotonic_calibrator.joblib"
    )
)

print(
    "Predictions saved:",
    os.path.exists(
        "results/eligible/"
        "calibration_validation.csv"
    )
)
