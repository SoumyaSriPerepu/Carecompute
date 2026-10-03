import pandas as pd
import numpy as np
import os

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)


# =====================================================
# 1. LOAD CALIBRATED VALIDATION PREDICTIONS
# =====================================================

df = pd.read_csv(
    "results/eligible/calibration_validation.csv"
)

y_true = df["actual_30d"]

prob = df["calibrated_probability"]


# =====================================================
# 2. TEST MANY THRESHOLDS
# =====================================================

# Use small steps because calibrated probabilities
# may behave differently from raw probabilities.
thresholds = np.arange(
    0.01,
    0.51,
    0.005
)

rows = []

for threshold in thresholds:

    pred = (
        prob >= threshold
    ).astype(int)

    precision = precision_score(
        y_true,
        pred,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        pred,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        pred,
        zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        pred
    ).ravel()

    fnr = fn / (fn + tp)

    rows.append({
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_negative_rate": fnr,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn
    })


results = pd.DataFrame(rows)


# =====================================================
# 3. BEST F1
# =====================================================

best_f1 = results.loc[
    results["f1"].idxmax()
]

print()
print("BEST F1")
print("-------------------------")
print(best_f1)


# =====================================================
# 4. BEST PRECISION WITH >= 70% RECALL
# =====================================================

candidates70 = results[
    results["recall"] >= 0.70
]

if len(candidates70) > 0:

    best70 = (
        candidates70
        .sort_values(
            ["precision", "threshold"],
            ascending=[False, False]
        )
        .iloc[0]
    )

    print()
    print("BEST WITH RECALL >= 70%")
    print("-------------------------")
    print(best70)


# =====================================================
# 5. BEST PRECISION WITH >= 80% RECALL
# =====================================================

candidates80 = results[
    results["recall"] >= 0.80
]

if len(candidates80) > 0:

    best80 = (
        candidates80
        .sort_values(
            ["precision", "threshold"],
            ascending=[False, False]
        )
        .iloc[0]
    )

    print()
    print("BEST WITH RECALL >= 80%")
    print("-------------------------")
    print(best80)


# =====================================================
# 6. SAVE
# =====================================================

results.to_csv(
    "results/eligible/"
    "calibrated_threshold_analysis.csv",
    index=False
)

print()
print(
    "Saved:",
    os.path.exists(
        "results/eligible/"
        "calibrated_threshold_analysis.csv"
    )
)
