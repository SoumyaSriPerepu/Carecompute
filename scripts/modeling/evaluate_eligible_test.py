import pandas as pd
import numpy as np
import joblib
import os

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    recall_score,
    precision_score,
    f1_score,
    confusion_matrix,
    brier_score_loss
)


# =====================================================
# 1. LOCKED OPERATING THRESHOLD
# =====================================================

THRESHOLD = 0.115


# =====================================================
# 2. LOAD UNTOUCHED TEST SET
# =====================================================

test = pd.read_csv(
    "data/processed/eligible/test.csv",
    low_memory=False
)

y_test = test["target_30d"]

X_test = test.drop(
    columns=[
        "patient_nbr",
        "encounter_id",
        "target_30d"
    ]
)


# =====================================================
# 3. LOAD LOCKED MODEL + CALIBRATOR
# =====================================================

model = joblib.load(
    "src/models/saved/eligible/"
    "gradient_boosting.joblib"
)

calibrator = joblib.load(
    "src/models/saved/eligible/"
    "isotonic_calibrator.joblib"
)


# =====================================================
# 4. GENERATE TEST PROBABILITIES
# =====================================================

raw_prob = model.predict_proba(
    X_test
)[:, 1]

cal_prob = calibrator.predict(
    raw_prob
)

pred = (
    cal_prob >= THRESHOLD
).astype(int)


# =====================================================
# 5. FINAL TEST METRICS
# =====================================================

auroc = roc_auc_score(
    y_test,
    cal_prob
)

auprc = average_precision_score(
    y_test,
    cal_prob
)

recall = recall_score(
    y_test,
    pred
)

precision = precision_score(
    y_test,
    pred,
    zero_division=0
)

f1 = f1_score(
    y_test,
    pred
)

brier = brier_score_loss(
    y_test,
    cal_prob
)

cm = confusion_matrix(
    y_test,
    pred
)

tn, fp, fn, tp = cm.ravel()

fnr = fn / (fn + tp)

specificity = tn / (tn + fp)


# =====================================================
# 6. PRINT FINAL RESULTS
# =====================================================

print()
print("=" * 50)
print("FINAL ELIGIBLE-COHORT TEST RESULTS")
print("=" * 50)

print("Test encounters:", len(test))
print("Actual positive rate:", y_test.mean())

print()
print("LOCKED THRESHOLD:", THRESHOLD)

print()
print("AUROC:", auroc)
print("AUPRC:", auprc)
print("Recall:", recall)
print("Precision:", precision)
print("F1:", f1)
print("False Negative Rate:", fnr)
print("Specificity:", specificity)
print("Brier Score:", brier)

print()
print("CONFUSION MATRIX")
print("-------------------------")

print(cm)

print()
print("True Negative:", tn)
print("False Positive:", fp)
print("False Negative:", fn)
print("True Positive:", tp)


# =====================================================
# 7. SAVE PATIENT-LEVEL RESULTS
# =====================================================

uncertainty = (
    1 - abs(
        2 * cal_prob - 1
    )
)

predictions = pd.DataFrame({
    "encounter_id":
        test["encounter_id"],

    "patient_nbr":
        test["patient_nbr"],

    "actual_30d":
        y_test,

    "raw_probability":
        raw_prob,

    "calibrated_probability":
        cal_prob,

    "uncertainty":
        uncertainty,

    "threshold":
        THRESHOLD,

    "predicted_30d":
        pred
})

os.makedirs(
    "results/eligible",
    exist_ok=True
)

predictions.to_csv(
    "results/eligible/"
    "test_predictions.csv",
    index=False
)


# =====================================================
# 8. SAVE FINAL METRICS
# =====================================================

metrics = pd.DataFrame([
    {
        "threshold": THRESHOLD,
        "AUROC": auroc,
        "AUPRC": auprc,
        "Recall": recall,
        "Precision": precision,
        "F1": f1,
        "FNR": fnr,
        "Specificity": specificity,
        "Brier": brier,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "TP": tp
    }
])

metrics.to_csv(
    "results/eligible/"
    "final_test_metrics.csv",
    index=False
)

print()
print(
    "Predictions saved:",
    os.path.exists(
        "results/eligible/"
        "test_predictions.csv"
    )
)

print(
    "Metrics saved:",
    os.path.exists(
        "results/eligible/"
        "final_test_metrics.csv"
    )
)
