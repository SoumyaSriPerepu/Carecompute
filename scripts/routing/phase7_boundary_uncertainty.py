import pandas as pd
import numpy as np
import os


# ============================================================
# PHASE 7.4 — DECISION-BOUNDARY UNCERTAINTY
#
# Instead of measuring distance from p = 0.50,
# measure distance from our LOCKED operating threshold.
# ============================================================


# ============================================================
# SETTINGS
# ============================================================

INPUT_PATH = (
    "results/eligible/test_predictions.csv"
)

OUTPUT_PATH = (
    "results/eligible/"
    "boundary_uncertainty_analysis.csv"
)

RISK_THRESHOLD = 0.115


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_csv(
    INPUT_PATH
)


print()
print("=" * 70)
print("PHASE 7.4 — DECISION-BOUNDARY UNCERTAINTY")
print("=" * 70)

print(
    "Total encounters:",
    len(df)
)


# ============================================================
# 2. CREATE CASE TYPES
# ============================================================

def get_case_type(row):

    actual = row["actual_30d"]
    predicted = row["predicted_30d"]

    if actual == 1 and predicted == 1:
        return "TP"

    if actual == 0 and predicted == 0:
        return "TN"

    if actual == 0 and predicted == 1:
        return "FP"

    return "FN"


df["case_type"] = df.apply(
    get_case_type,
    axis=1
)


# ============================================================
# 3. DISTANCE FROM LOCKED DECISION BOUNDARY
# ============================================================

df["boundary_distance"] = np.abs(
    df["calibrated_probability"]
    - RISK_THRESHOLD
)


# Smaller distance = more uncertain.
#
# Convert to a score where larger = more uncertain.
# This is mainly for easy interpretation.

df["boundary_uncertainty"] = (
    1
    / (
        1
        + df["boundary_distance"]
    )
)


# ============================================================
# 4. SHOW EXAMPLES
# ============================================================

print()
print("EXAMPLE SCORES")
print("-------------------------")

example = df[
    [
        "calibrated_probability",
        "boundary_distance",
        "boundary_uncertainty",
        "case_type"
    ]
].head(10)

print(
    example.to_string(
        index=False
    )
)


# ============================================================
# 5. DISTANCE BY CASE TYPE
# ============================================================

summary = (
    df.groupby(
        "case_type"
    )["boundary_distance"]
    .agg(
        [
            "count",
            "mean",
            "median",
            "min",
            "max"
        ]
    )
)


print()
print("BOUNDARY DISTANCE BY CASE TYPE")
print("-------------------------")

print(summary)


# ============================================================
# 6. DEFINE REVIEW BUDGETS
#
# Instead of arbitrarily choosing a score threshold,
# ask:
#
# "If we can review the closest X% of cases to the
# decision boundary, how many errors do we catch?"
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


total_fp = int(
    (
        df["case_type"]
        == "FP"
    ).sum()
)

total_fn = int(
    (
        df["case_type"]
        == "FN"
    ).sum()
)

total_errors = (
    total_fp
    + total_fn
)


# ============================================================
# 7. SORT MOST UNCERTAIN FIRST
# ============================================================

ranked = (
    df.sort_values(
        "boundary_distance",
        ascending=True
    )
    .reset_index(
        drop=True
    )
)


results = []


# ============================================================
# 8. EVALUATE EACH REVIEW BUDGET
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
            reviewed["case_type"]
            == "FP"
        ).sum()
    )

    fn_captured = int(
        (
            reviewed["case_type"]
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

    error_capture_rate = (
        errors_captured
        / total_errors
    )


    review_error_rate = (
        errors_captured
        / n_review
    )


    max_boundary_distance = (
        reviewed[
            "boundary_distance"
        ].max()
    )


    results.append({

        "review_budget":
            budget,

        "patients_reviewed":
            n_review,

        "max_boundary_distance":
            max_boundary_distance,

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
            error_capture_rate,

        "review_error_rate":
            review_error_rate
    })


results_df = pd.DataFrame(
    results
)


# ============================================================
# 9. PRINT RESULTS
# ============================================================

print()
print("REVIEW-BUDGET COMPARISON")
print("-------------------------")

print(
    results_df.to_string(
        index=False
    )
)


# ============================================================
# 10. FALSE NEGATIVE DISTANCE
# ============================================================

fn_df = df[
    df["case_type"]
    == "FN"
]


print()
print("FALSE NEGATIVE BOUNDARY DISTANCE")
print("-------------------------")

print(
    fn_df[
        "boundary_distance"
    ].describe()
)


# ============================================================
# 11. FALSE POSITIVE DISTANCE
# ============================================================

fp_df = df[
    df["case_type"]
    == "FP"
]


print()
print("FALSE POSITIVE BOUNDARY DISTANCE")
print("-------------------------")

print(
    fp_df[
        "boundary_distance"
    ].describe()
)


# ============================================================
# 12. CORRELATION CHECK
# ============================================================

correlation = (
    df[
        [
            "calibrated_probability",
            "boundary_uncertainty"
        ]
    ]
    .corr()
    .iloc[0, 1]
)


print()
print("RISK / BOUNDARY-UNCERTAINTY CORRELATION")
print("-------------------------")

print(
    correlation
)


# ============================================================
# 13. SAVE PATIENT-LEVEL SCORES
# ============================================================

patient_output = df[
    [
        "encounter_id",
        "actual_30d",
        "predicted_30d",
        "calibrated_probability",
        "case_type",
        "boundary_distance",
        "boundary_uncertainty"
    ]
].copy()


patient_output.to_csv(
    "results/eligible/"
    "boundary_uncertainty_predictions.csv",
    index=False
)


# ============================================================
# 14. SAVE EXPERIMENT TABLE
# ============================================================

os.makedirs(
    "results/eligible",
    exist_ok=True
)


results_df.to_csv(
    OUTPUT_PATH,
    index=False
)


print()
print("FILES SAVED")
print("-------------------------")

print(
    os.path.exists(
        OUTPUT_PATH
    )
)

print(
    os.path.exists(
        "results/eligible/"
        "boundary_uncertainty_predictions.csv"
    )
)


print()
print("=" * 70)
print("PHASE 7.4 COMPLETE")
print("=" * 70)
