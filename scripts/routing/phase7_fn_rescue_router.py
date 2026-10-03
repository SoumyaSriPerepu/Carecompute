import pandas as pd
import numpy as np
import os

from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    roc_auc_score,
    average_precision_score
)


# ============================================================
# PHASE 7.6.3 — FALSE NEGATIVE RESCUE ROUTER
# ============================================================

INPUT_PATH = (
    "results/eligible/router_validation.csv"
)

OUTPUT_PREDICTIONS = (
    "results/eligible/"
    "fn_rescue_router_predictions.csv"
)

OUTPUT_ANALYSIS = (
    "results/eligible/"
    "fn_rescue_router_analysis.csv"
)


print("=" * 70)
print("PHASE 7.6.3 — FALSE NEGATIVE RESCUE ROUTER")
print("=" * 70)


# ============================================================
# 1. LOAD VALIDATION ROUTER DATA
# ============================================================

df = pd.read_csv(
    INPUT_PATH,
    low_memory=False
)


# ============================================================
# 2. KEEP ONLY GB-NEGATIVE CASES
#
# These consist of:
#
# TN = correctly predicted negative
# FN = dangerous missed readmission
#
# The router's job is to distinguish FN from TN.
# ============================================================

low_risk = df[
    df["predicted_30d"] == 0
].copy()


low_risk["router_target"] = (
    low_risk["case_type"] == "FN"
).astype(int)


print()
print("LOW-RISK CASES")
print("-" * 50)

print(
    low_risk["case_type"].value_counts()
)

print(
    "FN prevalence:",
    low_risk["router_target"].mean()
)


# ============================================================
# 3. ROUTER FEATURES
#
# IMPORTANT:
#
# We use only distinct candidate signals.
#
# Do NOT simultaneously use probability_uncertainty,
# boundary_distance and boundary_uncertainty because they are
# deterministic transformations of calibrated probability.
# ============================================================

router_features = [

    "calibrated_probability",

    "model_disagreement_std",

    "number_diagnoses",

    "number_outpatient",

    "number_emergency"
]


X = low_risk[
    router_features
].copy()

y = low_risk[
    "router_target"
].astype(int)


print()
print("ROUTER FEATURES")
print("-" * 50)

for feature in router_features:
    print(feature)


# ============================================================
# 4. SIMPLE INTERPRETABLE ROUTER
#
# Logistic Regression keeps this experiment understandable.
#
# class_weight balanced helps because FN is much less common
# than TN.
# ============================================================

router_model = Pipeline(

    steps=[

        (
            "imputer",
            SimpleImputer(
                strategy="median"
            )
        ),

        (
            "scaler",
            StandardScaler()
        ),

        (
            "classifier",
            LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=42
            )
        )
    ]
)


# ============================================================
# 5. STRATIFIED CROSS-VALIDATION
#
# Generate out-of-fold probabilities.
#
# Every patient's router probability comes from a model that
# DID NOT train on that patient.
# ============================================================

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)


oof_probability = np.zeros(
    len(low_risk)
)


fold_number = np.zeros(
    len(low_risk),
    dtype=int
)


print()
print("RUNNING 5-FOLD CROSS-VALIDATION")
print("-" * 50)


for fold, (train_idx, eval_idx) in enumerate(
    cv.split(X, y),
    start=1
):

    X_train = X.iloc[
        train_idx
    ]

    y_train = y.iloc[
        train_idx
    ]

    X_eval = X.iloc[
        eval_idx
    ]


    router_model.fit(
        X_train,
        y_train
    )


    fold_prob = (
        router_model.predict_proba(
            X_eval
        )[:, 1]
    )


    oof_probability[
        eval_idx
    ] = fold_prob

    fold_number[
        eval_idx
    ] = fold


    print(
        f"Fold {fold}: "
        f"train={len(train_idx)}, "
        f"eval={len(eval_idx)}"
    )


# ============================================================
# 6. SAVE OOF ROUTER PROBABILITY
# ============================================================

low_risk[
    "fn_router_probability"
] = oof_probability

low_risk[
    "cv_fold"
] = fold_number


# ============================================================
# 7. BASIC DISCRIMINATION
# ============================================================

router_auroc = roc_auc_score(
    y,
    oof_probability
)

router_auprc = average_precision_score(
    y,
    oof_probability
)


print()
print("ROUTER PERFORMANCE")
print("-" * 50)

print(
    "AUROC:",
    router_auroc
)

print(
    "AUPRC:",
    router_auprc
)

print(
    "No-skill AUPRC:",
    y.mean()
)


# ============================================================
# 8. RANK CASES BY FN-LIKE PROBABILITY
# ============================================================

ranked = (
    low_risk
    .sort_values(
        "fn_router_probability",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


total_fn = int(
    y.sum()
)

total_low_risk = len(
    low_risk
)


# ============================================================
# 9. REVIEW BUDGET EXPERIMENT
#
# Among GB-negative cases:
#
# If we manually review the top X% ranked by router,
# how many false negatives can we rescue?
# ============================================================

review_budgets = [

    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.40,
    0.50
]


analysis_rows = []


for budget in review_budgets:

    n_review = int(
        np.ceil(
            total_low_risk
            * budget
        )
    )


    reviewed = ranked.iloc[
        :n_review
    ]


    fn_captured = int(
        reviewed[
            "router_target"
        ].sum()
    )


    fn_capture_rate = (
        fn_captured
        / total_fn
    )


    review_precision = (
        fn_captured
        / n_review
    )


    overall_review_rate = (
        n_review
        / len(df)
    )


    minimum_router_probability = (
        reviewed[
            "fn_router_probability"
        ].min()
    )


    analysis_rows.append({

        "low_risk_review_budget":
            budget,

        "patients_reviewed":
            n_review,

        "overall_validation_review_rate":
            overall_review_rate,

        "fn_captured":
            fn_captured,

        "fn_capture_rate":
            fn_capture_rate,

        "review_precision":
            review_precision,

        "minimum_router_probability":
            minimum_router_probability
    })


analysis = pd.DataFrame(
    analysis_rows
)


# ============================================================
# 10. PRINT REVIEW RESULTS
# ============================================================

print()
print("FN RESCUE — REVIEW BUDGET")
print("-" * 70)

print(
    analysis.to_string(
        index=False
    )
)


# ============================================================
# 11. COMPARE ROUTER SCORES FOR TN VS FN
# ============================================================

print()
print("ROUTER PROBABILITY BY CASE TYPE")
print("-" * 70)

print(

    low_risk.groupby(
        "case_type"
    )[
        "fn_router_probability"
    ]
    .describe()
)


# ============================================================
# 12. FIT FINAL VALIDATION ROUTER
#
# This model is saved ONLY as an experimental router.
#
# Do not evaluate it on validation again after fitting here.
# ============================================================

router_model.fit(
    X,
    y
)


# ============================================================
# 13. INSPECT COEFFICIENTS
# ============================================================

classifier = (
    router_model
    .named_steps[
        "classifier"
    ]
)


coefficients = pd.DataFrame({

    "feature":
        router_features,

    "coefficient":
        classifier.coef_[0]
})


coefficients[
    "absolute_coefficient"
] = np.abs(
    coefficients[
        "coefficient"
    ]
)


coefficients = (
    coefficients
    .sort_values(
        "absolute_coefficient",
        ascending=False
    )
)


print()
print("ROUTER COEFFICIENTS")
print("-" * 70)

print(
    coefficients.to_string(
        index=False
    )
)


# ============================================================
# 14. SAVE RESULTS
# ============================================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)


low_risk.to_csv(
    OUTPUT_PREDICTIONS,
    index=False
)


analysis.to_csv(
    OUTPUT_ANALYSIS,
    index=False
)


coefficients.to_csv(

    "results/eligible/"
    "fn_rescue_router_coefficients.csv",

    index=False
)


# ============================================================
# 15. SAVE EXPERIMENTAL ROUTER MODEL
# ============================================================

import joblib


os.makedirs(
    "src/models/saved/eligible/router",
    exist_ok=True
)


joblib.dump(

    router_model,

    "src/models/saved/eligible/router/"
    "fn_rescue_router.joblib"
)


print()
print("FILES SAVED")
print("-" * 70)

print(
    os.path.exists(
        OUTPUT_PREDICTIONS
    )
)

print(
    os.path.exists(
        OUTPUT_ANALYSIS
    )
)

print(
    os.path.exists(
        "src/models/saved/eligible/router/"
        "fn_rescue_router.joblib"
    )
)


print()
print("=" * 70)
print("PHASE 7.6.3 COMPLETE")
print("=" * 70)
