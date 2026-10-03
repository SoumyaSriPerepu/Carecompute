import pandas as pd
import numpy as np
import joblib
import os


# ============================================================
# PHASE 7.5 — MODEL DISAGREEMENT ANALYSIS
#
# Locked predictive model:
# Gradient Boosting
#
# Additional models are ONLY used to estimate disagreement.
# ============================================================


# ============================================================
# SETTINGS
# ============================================================

TEST_PATH = (
    "data/processed/eligible/test.csv"
)

PREDICTIONS_PATH = (
    "results/eligible/test_predictions.csv"
)

MODEL_DIR = (
    "src/models/saved/eligible"
)

OUTPUT_PATH = (
    "results/eligible/"
    "model_disagreement_predictions.csv"
)

SUMMARY_PATH = (
    "results/eligible/"
    "model_disagreement_analysis.csv"
)

RISK_THRESHOLD = 0.115


# ============================================================
# 1. LOAD TEST DATA
# ============================================================

test = pd.read_csv(
    TEST_PATH,
    low_memory=False
)

locked = pd.read_csv(
    PREDICTIONS_PATH
)


print()
print("=" * 70)
print("PHASE 7.5 — MODEL DISAGREEMENT")
print("=" * 70)

print(
    "Test encounters:",
    len(test)
)


# ============================================================
# 2. CREATE FEATURES
# ============================================================

X_test = test.drop(
    columns=[
        "patient_nbr",
        "encounter_id",
        "target_30d"
    ]
)

y_test = test[
    "target_30d"
].astype(int)


# ============================================================
# 3. LOAD THREE MODELS
# ============================================================

logistic_model = joblib.load(
    MODEL_DIR
    + "/logistic_regression.joblib"
)

random_forest_model = joblib.load(
    MODEL_DIR
    + "/random_forest.joblib"
)

gradient_model = joblib.load(
    MODEL_DIR
    + "/gradient_boosting.joblib"
)


print(
    "Models loaded: PASSED"
)


# ============================================================
# 4. GET RAW PROBABILITIES
# ============================================================

print()
print(
    "Generating model probabilities..."
)


lr_prob = (
    logistic_model
    .predict_proba(
        X_test
    )[:, 1]
)

rf_prob = (
    random_forest_model
    .predict_proba(
        X_test
    )[:, 1]
)

gb_raw_prob = (
    gradient_model
    .predict_proba(
        X_test
    )[:, 1]
)


print(
    "Probabilities generated: PASSED"
)


# ============================================================
# IMPORTANT
#
# We DO NOT threshold all three models at 0.115.
#
# The 0.115 threshold was selected specifically for the
# calibrated Gradient Boosting model.
#
# Instead, we use probability disagreement directly.
# ============================================================


# ============================================================
# 5. MODEL DISAGREEMENT — STANDARD DEVIATION
# ============================================================

probability_matrix = np.column_stack(
    [
        lr_prob,
        rf_prob,
        gb_raw_prob
    ]
)


probability_std = np.std(
    probability_matrix,
    axis=1
)


# ============================================================
# 6. MODEL DISAGREEMENT — RANGE
# ============================================================

probability_range = (
    np.max(
        probability_matrix,
        axis=1
    )
    -
    np.min(
        probability_matrix,
        axis=1
    )
)


# ============================================================
# 7. MEAN MODEL PROBABILITY
# ============================================================

mean_probability = np.mean(
    probability_matrix,
    axis=1
)


# ============================================================
# 8. BUILD PATIENT-LEVEL TABLE
# ============================================================

result = pd.DataFrame({

    "encounter_id":
        test[
            "encounter_id"
        ].values,

    "actual_30d":
        y_test.values,

    "lr_probability":
        lr_prob,

    "rf_probability":
        rf_prob,

    "gb_raw_probability":
        gb_raw_prob,

    "model_mean_probability":
        mean_probability,

    "model_disagreement_std":
        probability_std,

    "model_disagreement_range":
        probability_range
})


# ============================================================
# 9. ADD LOCKED GB RESULTS
# ============================================================

locked_small = locked[
    [
        "encounter_id",
        "calibrated_probability",
        "predicted_30d"
    ]
].copy()


result = result.merge(
    locked_small,
    on="encounter_id",
    how="left"
)


if result[
    "calibrated_probability"
].isna().any():

    raise ValueError(
        "Some locked predictions "
        "did not merge correctly."
    )


# ============================================================
# 10. CREATE CASE TYPES
# ============================================================

def get_case_type(row):

    actual = int(
        row[
            "actual_30d"
        ]
    )

    predicted = int(
        row[
            "predicted_30d"
        ]
    )

    if actual == 1 and predicted == 1:
        return "TP"

    if actual == 0 and predicted == 0:
        return "TN"

    if actual == 0 and predicted == 1:
        return "FP"

    return "FN"


result[
    "case_type"
] = result.apply(
    get_case_type,
    axis=1
)


# ============================================================
# 11. SUMMARY BY CASE TYPE
# ============================================================

summary = (
    result.groupby(
        "case_type"
    )[
        [
            "model_disagreement_std",
            "model_disagreement_range"
        ]
    ]
    .agg(
        [
            "count",
            "mean",
            "median"
        ]
    )
)


print()
print(
    "MODEL DISAGREEMENT BY CASE TYPE"
)

print(
    "-------------------------"
)

print(summary)


# ============================================================
# 12. TOTAL ERRORS
# ============================================================

total_fp = int(
    (
        result[
            "case_type"
        ]
        == "FP"
    ).sum()
)

total_fn = int(
    (
        result[
            "case_type"
        ]
        == "FN"
    ).sum()
)

total_errors = (
    total_fp
    + total_fn
)


# ============================================================
# 13. REVIEW BUDGETS
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


# ============================================================
# 14. RANK MOST DISAGREED CASES FIRST
# ============================================================

ranked = (
    result
    .sort_values(
        "model_disagreement_std",
        ascending=False
    )
    .reset_index(
        drop=True
    )
)


rows = []


# ============================================================
# 15. EVALUATE ROUTING
# ============================================================

for budget in review_budgets:

    n_review = int(
        np.ceil(
            len(ranked)
            * budget
        )
    )


    reviewed = ranked.iloc[
        :n_review
    ]


    fp_captured = int(
        (
            reviewed[
                "case_type"
            ]
            == "FP"
        ).sum()
    )


    fn_captured = int(
        (
            reviewed[
                "case_type"
            ]
            == "FN"
        ).sum()
    )


    errors_captured = (
        fp_captured
        + fn_captured
    )


    fp_capture_rate = (
        fp_captured
        / total_fp
    )


    fn_capture_rate = (
        fn_captured
        / total_fn
    )


    all_error_capture_rate = (
        errors_captured
        / total_errors
    )


    review_error_rate = (
        errors_captured
        / n_review
    )


    minimum_disagreement = (
        reviewed[
            "model_disagreement_std"
        ].min()
    )


    rows.append({

        "review_budget":
            budget,

        "patients_reviewed":
            n_review,

        "minimum_disagreement":
            minimum_disagreement,

        "fp_captured":
            fp_captured,

        "fp_capture_rate":
            fp_capture_rate,

        "fn_captured":
            fn_captured,

        "fn_capture_rate":
            fn_capture_rate,

        "all_errors_captured":
            errors_captured,

        "all_error_capture_rate":
            all_error_capture_rate,

        "review_error_rate":
            review_error_rate
    })


analysis = pd.DataFrame(
    rows
)


# ============================================================
# 16. PRINT REVIEW RESULTS
# ============================================================

print()
print(
    "REVIEW-BUDGET COMPARISON"
)

print(
    "-------------------------"
)

print(
    analysis.to_string(
        index=False
    )
)


# ============================================================
# 17. FALSE NEGATIVE DISAGREEMENT
# ============================================================

fn = result[
    result[
        "case_type"
    ]
    == "FN"
]


print()
print(
    "FALSE NEGATIVE MODEL DISAGREEMENT"
)

print(
    "-------------------------"
)

print(
    fn[
        "model_disagreement_std"
    ].describe()
)


# ============================================================
# 18. CORRELATION WITH LOCKED RISK
# ============================================================

correlation = (
    result[
        [
            "calibrated_probability",
            "model_disagreement_std"
        ]
    ]
    .corr()
    .iloc[0, 1]
)


print()
print(
    "RISK / DISAGREEMENT CORRELATION"
)

print(
    "-------------------------"
)

print(
    correlation
)


# ============================================================
# 19. SAVE
# ============================================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)


result.to_csv(
    OUTPUT_PATH,
    index=False
)


analysis.to_csv(
    SUMMARY_PATH,
    index=False
)


print()
print(
    "FILES SAVED"
)

print(
    "-------------------------"
)

print(
    os.path.exists(
        OUTPUT_PATH
    )
)

print(
    os.path.exists(
        SUMMARY_PATH
    )
)


print()

