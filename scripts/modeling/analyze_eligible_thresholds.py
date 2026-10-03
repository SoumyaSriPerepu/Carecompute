import pandas as pd
import numpy as np
import joblib
import os

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)


# ==========================================
# 1. LOAD VALIDATION DATA
# ==========================================

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


# ==========================================
# 2. LOAD GRADIENT BOOSTING MODEL
# ==========================================

model = joblib.load(
    "src/models/saved/eligible/"
    "gradient_boosting.joblib"
)


# ==========================================
# 3. GET PROBABILITIES
# ==========================================

probabilities = model.predict_proba(
    X_val
)[:, 1]


print()
print("PROBABILITY CHECK")
print("-------------------------")

print(
    "Minimum:",
    probabilities.min()
)

print(
    "Maximum:",
    probabilities.max()
)

print(
    "Average:",
    probabilities.mean()
)

print(
    "Actual positive rate:",
    y_val.mean()
)


# ==========================================
# 4. TEST MANY THRESHOLDS
# ==========================================

thresholds = np.arange(
    0.05,
    0.51,
    0.01
)

rows = []

for threshold in thresholds:

    predictions = (
        probabilities >= threshold
    ).astype(int)

    precision = precision_score(
        y_val,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_val,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_val,
        predictions,
        zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_val,
        predictions
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


# ==========================================
# 5. SHOW BEST F1
# ==========================================

best_f1 = results.loc[
    results["f1"].idxmax()
]

print()
print("BEST F1 THRESHOLD")
print("-------------------------")

print(best_f1)


# ==========================================
# 6. FIND THRESHOLD FOR ~70% RECALL
# ==========================================

recall_candidates = results[
    results["recall"] >= 0.70
]

if len(recall_candidates) > 0:

    recall70 = (
        recall_candidates
        .sort_values(
            "precision",
            ascending=False
        )
        .iloc[0]
    )

    print()
    print("BEST THRESHOLD WITH RECALL >= 70%")
    print("-------------------------")

    print(recall70)


# ==========================================
# 7. FIND THRESHOLD FOR ~80% RECALL
# ==========================================

recall_candidates = results[
    results["recall"] >= 0.80
]

if len(recall_candidates) > 0:

    recall80 = (
        recall_candidates
        .sort_values(
            "precision",
            ascending=False
        )
        .iloc[0]
    )

    print()
    print("BEST THRESHOLD WITH RECALL >= 80%")
    print("-------------------------")

    print(recall80)


# ==========================================
# 8. SAVE EVERYTHING
# ==========================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)

results.to_csv(
    "results/eligible/"
    "threshold_analysis.csv",
    index=False
)

print()
print(
    "Saved:",
    os.path.exists(
        "results/eligible/"
        "threshold_analysis.csv"
    )
)
